"""
HermesBot v2.8-TUNED — MEXC Futures Scalper (TRADING-LOGIC TUNED COPY)
Multi-trade · Hedging · Persistent positions bar · Clean UI
Live WebSocket price feeds · MEXC Futures API

Run:      python hermesbot_v1_5.py
Requires: pip install anthropic matplotlib websocket-client pyyaml

================================================================================
VERSIONING CONVENTION
================================================================================
This file is the official v1.0 baseline. All future upgrades increment by 0.1:

  v2.6  → previous file (pacbot_v2_6.py)
  v2.7  → current file  (pacbot_v2_7.py)
  v1.2  → upgrade after that
  ...and so on.

RULES:
  • Every new file gets a new version number in BOTH the filename AND this header.
  • Each release adds a changelog block at the TOP of the CHANGELOG section below,
    following the same format: version — short title, then bullet points for each
    change with a short tag (#TAG) and a plain-English description.
  • Never edit a released version in place — always copy to the new filename first,
    make changes, then update the version string and changelog.
  • The CHANGELOG is append-only: old entries are never deleted, only new ones added
    above them. This gives a full audit trail of every change ever made.

================================================================================
CHANGELOG
================================================================================
v2.8-TUNED — TRADING-LOGIC TUNING PASS (this file is a fork of v2.7.5)
================================================================================
  All v2.8 knobs live in the "v2.8-TUNED CONFIG" block near the top of the file.

  #TUNED-EXIT-RR  CLOSER TP (the real fix for "rarely hits TP, mostly SL").
              _open_position() now pins TP to a reachable multiple of net risk
              (TUNED_RR_TARGET = 1.6:1) instead of the old ~2.6-3:1 table that
              price rarely travelled far enough to reach. This both tightens TP
              when it was too far AND widens it when fees made it too tight.

  #TUNED-EXIT-SL  WIDER ATR-BASED SL. The SL floor is now TUNED_ATR_SL_MULT
              (2.0) × ATR instead of 1.5×, so ordinary wick noise — especially
              on low-volatility pairs like TRX — can't stop the trade out before
              it has room to work.

  #TUNED-PARTIAL-TP  PARTIAL TAKE-PROFIT + BREAKEVEN. New _partial_take_profit()
              closes TUNED_PARTIAL_TP_FRACTION (50%) of the position once it is
              TUNED_PARTIAL_TP_PROGRESS (50%) of the way to TP, banks that PnL
              (reduce-only order in live, simulated in paper), shrinks the
              tracked position, and moves the stop to breakeven. A trade that
              moves your way now locks in real profit instead of round-tripping
              back to the stop. Fires once per position; never on hedge legs or
              the force_close path. Cleaned up with the other per-pid state.

  #TUNED-ENTRY-TOGGLE  The entry-selectivity changes below are now behind a UI
              checkbox ("Selective entry") and the selective_entry= parameter on
              compute_signals(). ON  = fewer, higher-conviction trades; OFF =
              original v2.7.5 behaviour (more, lower-quality trades). Default
              from TUNED_SELECTIVE_ENTRY_DEFAULT. The conviction gap was also
              softened to TUNED_CONVICTION_GAP (0.6, was 0.8) so it trims chop
              without choking trade flow.

  #TUNED-CONFLUENCE  Added a confluence "stacking" bonus (+1.0) to compute_signals()
              for both LONG and SHORT: fires only when a real trigger (EMA/MACD
              cross or genuine RSI extreme) AND an oscillator extreme (StochRSI
              or Bollinger %B) AND above-average volume all agree on the same
              direction. Problem this fixes: genuinely strong setups had their
              points spread thin across many indicators and often hovered just
              under the score threshold — the bot "struggled to pick trades"
              even when a good one was right in front of it. High-conviction
              confluence now scores noticeably higher and clears the bar.

  #TUNED-TRIGGER-GATE  A direction's score can no longer qualify if it was built
              entirely from soft/neutral contributions (trend bias, mid-range
              RSI, small volume bumps, price-action notes) with no real catalyst.
              Each side now requires at least one bona-fide trigger — a fresh
              EMA/MACD cross, building MACD momentum, or a genuine oversold/
              overbought extreme — before its score is allowed to reach the
              threshold (capped at thresh-0.5 otherwise). Problem this fixes:
              "noise" scores that limped across the threshold from accumulated
              weak factors with no actual catalyst — these were the trades that
              got taken and then immediately faded ("takes bad ones").

  #TUNED-CONVICTION-GAP  Direction selection now requires the winning side to
              beat the other side by at least MIN_CONVICTION_GAP = 0.8 points
              (previously any ls > ss, even by 0.1, qualified). Problem this
              fixes: choppy/contested markets where LONG and SHORT scored
              near-equally near the threshold produced low-conviction entries
              that reversed almost immediately — the classic "bad pick".

  All three changes only make entry conditions MORE selective — they cannot
  cause the bot to enter a trade it wouldn't have entered before. Net effect:
  fewer, higher-conviction entries; HOLD is returned more often for ambiguous
  reads, and genuinely strong setups score higher and fire more reliably.
================================================================================
v2.7.5 — AI-TAB-STALE: GHOST POSITION IN AI PANEL FIXED (BUGFIX)
================================================================================
  #AI-TAB-STALE  Fixed AI tab continuing to show a closed position's card after
              MEXC closes the trade. Root cause: _cleanup_memory() (which prunes
              _ai_trade_log of closed pids) only runs every 60 cycles (~20 min).
              When _sync_positions() detected and removed a stale position from
              state.positions, it did NOT immediately clean the corresponding
              _ai_trade_log entry, so the AI panel kept showing the position card
              (with its last MONITOR state) until the next cleanup sweep.

              Fix: _sync_positions() now immediately pops the pid from
              _ai_trade_log under _ai_log_lock when it removes a stale position,
              and invalidates the AI tab throttle cache so the next refresh
              redraws without the ghost card. The AI panel now clears within one
              sync cycle (~40s in live mode) instead of up to 20 minutes.

================================================================================
v2.7.4 — LEV-CAP: ACTUALLY ENFORCED (BUGFIX)
================================================================================
  #PREFLIGHT-WARN  Fixed preflight check blocking bot start when margin >
              available balance, even when open positions already occupy most
              slots. The bot must be allowed to start so it can monitor and
              manage existing positions — blocking start entirely abandons open
              trades. Fix: "margin > available" demoted from error to warning.
              New trades are still skipped individually in _open_position() when
              balance is insufficient. Empty wallet is only a hard error when
              there are zero open positions to manage.

  #CLOSE-GATE  Fixed _market_close_position() sending a market order to MEXC
              on every scan cycle for every open position, even when price had
              not reached SL/TP/liq. MEXC was returning "Balance insufficient"
              (their rejection for unnecessary close orders), logged as a warning
              every 30s per position — spamming the log and causing UI lag from
              extra API round-trips. Fix: hsl/htp/hliq gate check moved to the
              top of the function, before the market order. Order only fires when
              actually needed, or when force_close=True (AI CLOSE / AI TAKE paths).

  #LEV-CAP-FIX  v2.7.3 changelog claimed SAFE_LEV_CAP=25 was implemented but
              the constant was never added to code. Synced positions inherited
              whatever leverage MEXC reported (e.g. 100x for XRP/TRX, 50x for
              BNB), completely ignoring the UI leverage setting. This caused the
              bot to open and track positions at exchange leverage rather than
              the user's chosen leverage, wiping margin on tiny moves.

              Fix: _sync_positions() now caps imported leverage to self._lev()
              (the current UI setting) on import:
                lev = min(ep["leverage"], self._lev())

              PAIR_MAX_LEV is restored to exchange maximums — it is an
              informational ceiling only. The UI setting is the enforced cap.

================================================================================
v2.7.3 — SYNC-POSITION SL/TP: ATR-SCALED + LEVERAGE-AWARE (BUGFIX)
================================================================================
  #DYN-TRAIL  Dynamic ATR-scaled trailing stops with three tiers:
              1. BREAKEVEN LOCK at 30% TP progress — SL moves to entry+fee
                 the moment the trade is clearly profitable. Fires once per
                 position. Replaces old partial-TP breakeven at 55% which was
                 too late for fast-moving positions.
              2. STANDARD TRAIL at 60% SL distance in profit — gap is now
                 ATR-scaled (1.5 × current ATR in price units) rather than a
                 fixed fraction of original SL distance. Clamped: never looser
                 than original SL, never tighter than 30% of original SL.
                 Tightens to 50% of gap once profit exceeds original SL dist.
              3. FAST-SPIKE TRAIL — triggers when ≥90% to TP OR gain-per-candle
                 ≥2% margin. Uses 25% of original SL as gap (very tight).
                 Also bypasses the 5-min AI trail cooldown so Claude gets
                 called immediately on rapid moves.
              Log labels: 🔒 Breakeven lock / 📈 Trail / ⚡ Fast-spike.
              Each shows the new SL, gap %, and current ATR %.

  #MORE-TRADES  Relaxed overnight filters to fix 6-hour trade drought:
              • Dead zone 04-07 GMT removed entirely. 3hrs of every overnight
                session were hard-blocked. Vol gate already handles thin volume.
              • Overnight vol gate: 0.55 → 0.45. Pairs at 0.46-0.54x were
                being blocked despite real momentum.
              • Overnight doji filter: 12% → 8% body ratio. Overnight ATR is
                naturally lower, candle bodies are thinner — 12% was too strict.
              • Overnight H4 score floor: threshold+0.5 → threshold. The extra
                +0.5 on top of an already-elevated overnight threshold was making
                H4 counter-trend signals nearly unreachable.
              • MACD fading filter: tightened from "not building" (fires on any
                single wobble) to "2-bar confirmed fade" (requires 3 consecutive
                bars shrinking in the wrong direction). Previously any pause in
                MACD momentum would block the trade even mid-trend.

  #LEV-CAP  Capped PAIR_MAX_LEV at 25x for all pairs (was 100-500x).
              validate_contract_specs() was patching PAIR_MAX_LEV upward from
              live MEXC data at startup (e.g. LINK→300x, DOT→200x), silently
              widening the leverage ceiling the bot could recommend/use.
              All pairs now hard-capped at 25x in both the static table and
              the live-patch path (SAFE_LEV_CAP = 25).

  #PREFLIGHT-OPEN-POS  Fixed "Cannot start" error blocking bot when synced
              positions already occupy all trade slots. Preflight margin check
              was comparing margin × max_trades against available balance without
              accounting for already-open positions. If 2 positions are open and
              max_trades=2, free_slots=0 — no new margin is needed at all.
              Fix: subtract current open position count from max_trades to get
              free_slots, then only check/warn if free_slots > 0. Error and
              warning thresholds now use free_slots × margin instead of
              max_trades × margin.

  #GHOST-POSITION  Fixed MEXC ghost positions being re-synced after close.
              MEXC's /open_positions endpoint returns recently-closed positions
              for several minutes after close, with closeVol == holdVol. The
              bot was importing these as new positions, attaching Claude monitors,
              placing TP/SL orders, then immediately hitting "Market close
              rejected: Position is nonexistent or closed" on every subsequent
              sync. Fix: skip any position where closeVol >= holdVol in
              fetch_open_positions — it's already gone on the exchange.

  #FIXED-MARGIN  Removed all automatic margin reduction. Previously three
              separate systems silently reduced the user-set margin:
                • Volume scaling: 0.5× at vr<0.8, 0.75× at vr<1.1
                • Kelly Criterion: scaled by win-rate formula (0.50–1.50×)
                • Pullback/OB-scalp: halved margin for counter-trend entries
              All three are removed. actual_mg = mg always. The user sets the
              margin they want and that is exactly what gets traded. The TP/SL
              tightening for pullback/OB-scalp entries is preserved — only the
              margin reduction is removed.

  #AI-CLOSE-TRADE-MISSING  Fixed AI CLOSE / AI TAKE trades not appearing in
              trade history. Root cause: _market_close_position() has a gate
              that checks whether price has crossed SL/TP/liq before recording
              the trade. The AI CLOSE path moves stop_loss to cur_px ± 0.01%
              then spawns a thread — by the time the thread runs, price may
              have moved a tick, making hsl=False, and the function returns
              early (return False, None, 0) without recording the trade or
              removing the position from state. The market order had already
              been sent to MEXC, so the position was closed on the exchange
              but the bot showed it as still open with no trade entry.

              Fix: added force_close=False parameter to _market_close_position.
              AI CLOSE and AI TAKE callers pass force_close=True via kwargs=,
              bypassing the htp/hsl/hliq gate entirely. PnL is still computed
              correctly from current px. Trade is tagged "WIN (AI close)" /
              "LOSS (AI close)" in the status column for auditability.

              Also added _persist_orders() + _refresh_trades_tab() +
              _refresh_metrics() at the end of _market_close_position so the
              trade log and metrics update immediately on close regardless of
              which path triggered the close (scan-loop already had these via
              its own caller; AI close path was missing them).

  #SYNC-SL-TP  Fixed _sync_positions() using hardcoded fallback SL=0.8% /
              TP=2.0% for imported exchange positions — values calibrated for
              crypto volatility at an arbitrary UI leverage (often wrong).

              Root cause: when sl_pct / tp_pct were not passed in (scan-loop
              path), the function fell back to 0.008 / 0.02 regardless of
              the actual exchange leverage of the synced position OR the pair's
              per-candle ATR. For SPX_USDT at 2x, this produced an SL only
              ~$1.20 from entry on a ~$6,000 token — hit immediately by normal
              wick noise.

              Fix: compute SL/TP using the same two-step logic as _auto_sl_tp:
                1. Look up base SL/TP from the actual exchange leverage (lev)
                   via the same tier table as _auto_sl_tp.
                2. Scale by (PAIR_ATR_MIN[sym] / 0.15), clamped to 0.20 min,
                   so low-volatility pairs (SPX 0.03%, EUR 0.02%) get tighter
                   absolute distances matching their actual candle movement.

              Per-position local vars (_sl_use, _tp_use) are used instead of
              mutating sl_pct / tp_pct so each position in a multi-position
              sync gets independently computed values (no first-position bleed).

              UI-override path preserved: when the manual Sync button passes
              both sl_pct and tp_pct explicitly, they are used as-is.

              Log line updated to display the computed SL%/TP% for each
              imported position so it's immediately auditable in the event log.

================================================================================
v2.7 — MARGIN-DRIVEN LEVERAGE RECOMMENDATION + BUGFIXES
================================================================================
  #MARKET-CLOSE-403  Fixed HTTP 403 Forbidden on all market-close orders.
              _market_close_position() was building its own raw urllib request
              to the wrong endpoint (/order/create) with manually constructed
              HMAC auth — causing 403 Forbidden on every pair including SPX.
              Every other order in the bot uses mexc_private() + /order/submit.
              Fixed by replacing the entire raw-request block with a standard
              mexc_private() call using /api/v1/private/order/submit, side 3
              (close LONG) or 4 (close SHORT), type 5 (market), openType 2
              (reduce-only). Also added 510 rate-limit retry to match the
              same resilience pattern used in _open_position. Side values were
              also inverted in the old code (4 for LONG, 3 for SHORT — wrong;
              MEXC: 3=sell/close-long, 4=buy/close-short).


              The UI widget correctly initialises to 4.5/9 (matching
              DEFAULT_CONFIG["signal_threshold"] = 4.5 and the documented
              default throughout the changelog), but _reset_defaults() was
              hardcoding "5.0/9" — so clicking "↺ Reset Defaults" silently
              raised the threshold, suppressing valid signals. Changed to
              "4.5/9" to match every other reference to the default.

  #LEV-REC-FIX  Fixed _recommended_lev() using nonsensically small margin
              floors. Original formula (MIN_NOTIONAL/lev)*rec_mult produced
              a floor of $0.15 at 200x, so even $1.50 was "recommended" 200x.
              Replaced with explicit USDT floors per tier:
                $2+→2x  $5+→5x  $8+→10x  $15+→20x  $25+→30x
                $50+→50x  $150+→100x  $500+→200x

  #LEV-REC    Added automatic leverage recommendation based on margin input.
              New method _recommended_lev(margin) maps margin USDT to the
              highest leverage tier the margin safely supports using the
              standard industry margin-requirement table:

                Leverage  Min-Margin  Min USDT Floor  Markets
                2x        50%         $2              High-vol stocks
                5x        20%         $5              Shares / EM
                10x       10%         $8              Minor indices / commodities
                20x       5%          $15             Major indices / gold
                30x       3.33%       $25             Major currency pairs
                50x       2%          $50             Forex majors
                100x      1%          $150            Short-term Forex
                200x      0.5%        $500            Scalping / very high-risk

              Result is capped to PAIR_MAX_LEV for the selected pair.
              New method _on_margin_change() fires on <FocusOut> and <Return>
              on the Margin USDT entry — sets leverage, calls _on_lev() and
              _auto_sl_tp(), and updates a new cyan lev_rec_lbl label:
                "Margin $50 → recommended 50x  (Forex majors)"

================================================================================
v2.5 — 10 NEW HIGH-LIQUIDITY PAIRS (CRYPTO + FOREX + INDEX)
================================================================================
  #NEW-PAIRS  Added 10 new MEXC futures pairs, chosen for high liquidity,
              strong 24h volume on MEXC, and diverse asset-class coverage:

              CRYPTO:
                ADA_USDT   — Cardano, top-10 by market cap, 100x lev
                AVAX_USDT  — Avalanche, high beta L1, 100x lev
                BNB_USDT   — Binance Coin, second-largest by volume, 100x lev
                LINK_USDT  — Chainlink, leading oracle, 100x lev
                TON_USDT   — Toncoin, Q2 2025 volume surge leader on MEXC, 100x lev
                TRX_USDT   — TRON, high on-chain activity / stablecoin flows, 100x lev
                DOT_USDT   — Polkadot, historically liquid on MEXC, 100x lev
                LTC_USDT   — Litecoin, deep OB, consistently top-5 futures vol, 100x lev

              FOREX:
                GBP_USDT   — Sterling, second-most-traded forex pair on MEXC, 100x lev

              INDEX:
                US30_USDT  — Dow Jones (already in legacy dicts; now promoted to
                             active PAIRS list), 20x max lev

              Each pair received entries in ALL config dicts:
                PAIR_ATR_MIN, PAIR_RSI_BIAS, PAIR_COL, PAIR_DISPLAY,
                PAIR_VOL_PRECISION, PAIR_CONTRACT_SIZE, PAIR_VOL_MIN_USDT,
                PAIR_MIN_MARGIN, PAIR_PRICE_PRECISION, PAIR_MAX_LEV.
              Default config["pairs"] list updated to include all 20 pairs.
              PAIR_RSI_BIAS: crypto=0, GBP=8 (trending forex), US30=8 (index).
              PAIR_ATR_MIN: crypto alts at 0.06-0.08%, GBP=0.02%, US30=0.04%.
              Colors chosen to be visually distinct from the existing 10 pairs.

  #OVERNIGHT  Fixed overnight mode threshold logic. The old code only acted when
              the threshold was exactly 5.5/9 → 5.0/9, which meant it did nothing
              at the default 4.5/9 setting (the most common use case). The new
              logic steps down by exactly one option regardless of starting value
              (e.g. 4.5→4.0, 5.0→4.5, 5.5→5.0) and stores the original value in
              _overnight_pre_thr so it is restored exactly on deactivation, with
              no risk of drift from repeated on/off cycles. The UI label was also
              corrected from the hardcoded "5→4.5" to "e.g. 4.5→4.0".

  #TAB-IDX   Fixed tab index off-by-one: _select_tab's all_labels list was
              missing "Events", so clicking Events showed Trades, clicking
              Trades showed AI, and AI had no target. Added "Events" back to
              the list to match the 4-entry extra_labels in _build_tabs.

  #LH-RELAX  Per-pair lower-highs filter relaxation for high-beta alts.
              High-beta alts (TON, DOGE, SOL, AVAX, DOT, LINK, ADA, XRP)
              naturally form lower highs during pullbacks within broader uptrends
              — the same structure that looks like "distribution" on stable pairs.
              Previously the lower-highs LONG block was a hard veto for all pairs,
              causing repeated false blocks on alts (e.g. TON blocked every cycle
              while StRSI showed 17 — deeply oversold, a clear bounce setup).

              New behaviour: pairs in PAIR_LH_RELAXED bypass the lower-highs
              LONG block when StochRSI ≤ 20 (deeply oversold). The combination
              of lower highs + StRSI deeply oversold on a high-beta alt signals
              a pullback to support, not distribution. All other pairs (BTC, ETH,
              EUR, GOLD, indices, stocks) keep the hard block unchanged, since
              lower highs in those assets genuinely signals weakening momentum.

  #510-RETRY  Fixed MEXC error code 510 ("Requests are too frequent") causing
              orders to fail silently and then triggering a spurious precision
              retry. Code 510 is returned in the JSON body of a 200 response,
              not as an HTTP error, so the existing HTTP-layer retry never caught
              it. Added explicit 510 handling in _open_position: on a 510 from
              a market order, the bot now waits 3 s and retries once before
              giving up; on a limit order 510, it falls back to the market path
              with a 2 s pause. The precision-retry (code 2015) path is now
              unreachable from a 510 result, so the spurious 4dp→3dp reduction
              no longer fires. Rate-limiter burst also reduced from 20 → 10
  #TON-SYM   Fixed TON_USDT ticker/klines always returning "unavailable".
              MEXC kept the legacy futures contract name TONCOIN_USDT after the
              2022 ticker rebrand (spot = TONUSDT, futures API = TONCOIN_USDT).
              Added "TON_USDT": "TONCOIN_USDT" to MEXC_API_SYMBOL so futures
              requests use the correct contract name. Also fixed the spot
              fallback in get_ticker and get_klines: both were building spot_sym
              from api_mapped (which for TON gives TONCOINUSDT — wrong) instead
              of the original bot symbol (TON_USDT → TONUSDT — correct). The
              spot path now always strips _USDT from sym, not api_mapped.

================================================================================
v2.0 — PULLBACK SCALP MODE (COUNTER-TREND H1/H4 OVERRIDE)
================================================================================
  #PULLBACK   Counter-trend "pullback scalp" mode. Previously H1 BULL blocked
              all SHORT signals (and H1 BEAR blocked all LONGs), even when a
              sharp Min5 retracement produced a genuinely strong signal. These
              pullbacks inside a larger trend are real scalp opportunities but
              require tighter management since the trend can resume at any time.

              A signal now qualifies as a pullback scalp — bypassing the H1/H4
              hard block — when ALL of the following are true:
                • Score ≥ 5.0/9  (high conviction on Min5, not just marginal)
                • Upper wick (SHORT) or lower wick (LONG) on last closed candle
                  exceeds 40% of total candle range — price was rejected at the
                  level, confirming the pullback is real and not a continuation
                • RSI not extreme against the scalp: SHORT needs RSI > 45
                  (some bearish momentum on Min5), LONG needs RSI < 55
                • No RSI divergence flagged against the trade direction
                  (divergence means the pullback may already be exhausted)
                • H4 is checked separately: if H4 also conflicts, the score
                  threshold is raised further to 5.5 (both H1 and H4 bullish
                  while trying to SHORT = much riskier, need stronger signal)

              When a pullback scalp fires:
                • TP is tightened to 40% of the configured TP (quick exit —
                  don't hold into the larger trend)
                • SL is tightened to 60% of configured SL (less room given —
                  if the trend resumes immediately, cut fast)
                • Margin is halved (smaller size = less damage if wrong)
                • Trade is tagged [PULLBACK] in the log so it's easy to spot
                • The BEST SIGNAL log line shows "PULLBACK SCALP" in amber

================================================================================
v1.9 — ALL PAIRS USE USDT-NOTIONAL VOL (MEXC UNIVERSAL)
================================================================================
  #USDT-ALL   BTC UI confirms: "Minimum order quantity is 6.0516 USDT" with
              Quantity field labelled "(USDT)". MEXC futures use USDT notional
              vol universally — not just for stock perps. The v1.8 fix only
              moved stock perps into PAIR_VOL_IN_USDT; crypto and index pairs
              were still using the old contract-count formula which happened to
              produce reasonable integers at very high leverage (BTC 100x gave
              ~24 contracts ≈ OK by accident) but was wrong at lower leverage
              and wrong in absolute terms (24 ≠ 150 USDT).

              This version moves ALL pairs to USDT-notional vol:
                vol = margin * leverage   (USDT)   for every pair

              PAIR_VOL_IN_USDT, PAIR_CONTRACT_SIZE and the branch logic are
              removed. The vol formula is now a single unconditional line.
              PAIR_VOL_PRECISION is updated to 4dp for all pairs (MEXC accepts
              fractional USDT). PAIR_VOL_MIN_USDT covers all active pairs with
              conservative minimums (crypto ~6 USDT observed on BTC, stock
              perps ~2 USDT). The precision-retry path and TP/SL vol fallback
              are also simplified to match.

================================================================================
v1.8 — STOCK PERP USDT-NOTIONAL VOL FIX
================================================================================
  #USDT-VOL   MEXC stock perpetuals (NVDA, AAPL, MSFT, TESLA, SPCX) accept
              vol as USDT notional, NOT as a contract count. The UI confirms
              this: NVDA shows "Minimum order quantity is 2.0592 USDT" and
              the Quantity field is labelled "(USDT)". The old formula:
                vol = (margin * leverage) / price / contract_size
              produced fractional contracts (e.g. 0.057) that rounded to 0,
              causing every NVDA order to be skipped.

              Fix: a new PAIR_VOL_IN_USDT set identifies the affected pairs.
              For those pairs the vol formula becomes:
                vol = margin * leverage          (USDT notional, no /price/cs)
              and PAIR_VOL_PRECISION is updated to 4dp to allow sub-cent USDT
              values (minimum on MEXC is ~2 USDT so 4dp is more than enough).

              All four vol calculation sites are updated:
                • _open_position()          — opening new trades
                • _check_exit_force()       — manual / forced close
                • _close_position()         — monitor SL/TP/liq close
                • _set_mexc_tpsl()          — TP/SL stop-order vol fallback

              The PAIR_MIN_MARGIN entries for stock perps are also corrected:
              minimum is ~2.06 USDT (exchange minimum), not the old ~$25-$80
              estimates based on the wrong contract-count formula.

================================================================================
v1.7 — NVDA MIN-MARGIN AUTO-SCALE + MIN1 PURE MODE FILTERS
================================================================================
  #NVDA-MARGIN  NVDA (and other high-price stock contracts) require a full
              integer contract, but at low margin settings the computed vol
              rounds to 0. Previously the order was silently skipped with
              "margin too small for one contract". Now, when vol==0, the bot
              calculates the minimum margin required for exactly 1 contract
              (price / leverage) and logs a clear warning showing what margin
              is actually needed. A PAIR_MIN_MARGIN dict is provided for
              reference. The trade is still skipped — the user must increase
              the margin slider — but the message now tells them exactly how
              much to set it to, rather than leaving them to guess.

  #MIN1-PURE  Min1 pure mode (dual TF OFF, TF set to Min1) now applies a set
              of tighter filters to compensate for Min1 candle noise:
              • Candle body ratio raised 0.20 → 0.30 (tighter doji filter)
              • Multi-candle confirmation: 2 of last 3 Min1 candles must
                agree with the signal direction
              • Wick rejection: blocks if the opposing wick exceeds 60% of
                the total candle range (price was rejected at that level)
              • Tighter RSI gate: no LONG above RSI 72 (was 78), no SHORT
                below RSI 28 (was 22)
              • EMA gap minimum raised 0.02% → 0.04% (Min1 EMAs cross
                constantly; flat gaps are meaningless noise)
              • Consecutive candle limit tightened: block after 3 same-colour
                candles instead of 4
              • Score threshold nudge: +0.5 added to effective threshold in
                Min1 pure mode to compensate for the noisier timeframe
              All Min1 pure filters are applied inside _passes_filters and
              the scan loop; they are completely bypassed when dual TF is
              enabled or when any other TF is selected.

================================================================================
v1.6 — H4 MACRO FILTER + VOLUME GATE + CLAUDE CONFIDENCE GATE +
        CANDLE BODY FILTER + TIME-OF-DAY BONUS + PAIR WIN/LOSS TRACKING
================================================================================
  #H4-FILTER  H4 trend filter added as a second macro-alignment layer.
              The H1 filter catches hourly counter-trend trades; H4 catches
              4-hour counter-trend entries that H1 misses (H1 can be bullish
              while H4 is in a clear downtrend). Implementation mirrors H1:
              EMA9/EMA21 cross on 30-bar Hour4 candles, stored in
              `_h4_trends` dict, refreshed every 40 cycles (~13 min) in a
              background thread. `_passes_filters` blocks on H4 conflict in
              normal hours; overnight mode allows high-score (≥ 5.5) overrides
              to match the existing H1 overnight policy.

  #VOL-GATE   Minimum volume soft gate added. `vr < 0.7` now blocks trade
              entry entirely (returns False from `_passes_filters`) rather
              than just halving position size. The 0.5x size scaling at
              vr < 0.8 is preserved — the new gate only removes the case
              where a trade fires into genuinely dead volume. Comment updated
              from "Volume is NOT a hard block" to accurately reflect the
              new behaviour.

  #CLAUDE-CONF  Claude confidence gate: `claude_decision` responses with
              confidence < 55 are now treated as HOLD even if action is
              TRADE. The call already happened and the token cost is sunk;
              gating on confidence is free signal quality improvement.
              A log line is emitted so the gate is visible in the session
              log. The function was previously defined but never called in
              the scan loop; it is now wired in immediately after the
              position opens (async Claude review that can veto and close
              within the same cycle if fired before the next monitor pass).

  #CANDLE-BODY  Candle body quality filter. Checks last completed candle
              (candles[-2], not the forming [-1]) body ratio:
              abs(close - open) / (high - low). If ratio < 0.20 and
              high - low > 0, the candle is a doji/spinning-top — strong
              indecision — and the trade is blocked. Applied in
              `_passes_filters` for both LONG and SHORT. Handles zero-range
              edge case (high == low) by skipping the check.

  #TOD-BONUS  Time-of-day scoring bonus. Signals firing in peak liquidity
              windows receive a +0.3 score bonus applied BEFORE threshold
              comparison:
                08:00–11:59 GMT  European open  (EUR, XAU, indices)
                13:30–16:59 GMT  US open        (all pairs)
              The bonus makes the effective threshold harder to reach in
              off-hours without a hard block. Signals outside these windows
              must score higher on their own merits to open a trade.

  #PAIR-LOG   Per-pair win/loss tracking added to BotState (`pair_wins` and
              `pair_losses` dicts). Populated in the close-position path
              alongside the existing Kelly win/loss update. Logged to the
              file logger at INFO level on each close. The data is persisted
              with BotState so win rates survive restarts, enabling future
              automated pair-weighting.

================================================================================
v1.5 — 10-PAIR FOCUS + PER-PAIR ATR BASELINES + PER-PAIR RSI CALIBRATION
================================================================================
  #PAIRS      Scan list reduced from 19 to 10 high-liquidity pairs:
              BTC, ETH, SOL, XRP, DOGE, XAU (gold), NAS100, SPX, EUR, NVDA.
              Reasoning: all 10 are high-volume contracts with tight spreads
              on MEXC. The 9 removed pairs (PEPE, SUI, TESLA, SPCX, GBP, JPY,
              US30, AAPL, MSFT) had lower liquidity, wider spreads, and more
              false signals — especially the stock CFDs and micro-caps during
              quiet sessions. The remaining 10 are uncorrelated enough to still
              benefit from universe-scanning (BTC/ETH/SOL/XRP/DOGE = crypto,
              XAU = gold, NAS100/SPX = indices, EUR = forex, NVDA = stock).
              10 pairs also cuts REST API calls in half during WS outages.

  #ATR-PAIRS  Per-pair ATR minimum thresholds (PAIR_ATR_MIN dict) replace the
              flat 0.06% gate applied to all assets equally.
              Each pair's minimum is set from its observed quiet-session ATR:
                BTC:    0.04% (deep market, moves slowly on Min5)
                ETH:    0.05%
                SOL:    0.07%
                XRP:    0.06%
                DOGE:   0.07%
                XAU:    0.03% (gold is very low volatility per candle)
                NAS100: 0.04% (index, slow moves)
                SPX:    0.03%
                EUR:    0.02% (forex, tiny candles)
                NVDA:   0.05%
              compute_signals() now accepts an optional atr_min kwarg and uses
              PAIR_ATR_MIN.get(sym, 0.06) when called from the scan loop.

  #RSI-PAIRS  Per-pair RSI scoring calibration (PAIR_RSI_BIAS dict).
              Some assets (gold, indices, EUR) trend for long periods and
              rarely hit RSI < 30 — the old scoring rewarded those levels
              that almost never fire. Instead, each pair now has an rsi_bias
              that shifts what counts as "oversold/overbought" for scoring:
                BTC/ETH/SOL/XRP/DOGE: 0  (no shift — crypto is mean-reverting)
                XAU/NAS100/SPX/EUR:   +8 (shifted up — these trend; 38/62 range)
                NVDA:                 +5 (semi-trending stock)
              compute_signals() accepts rsi_bias kwarg; LONG score awards
              1.5 pts at rv < (30 + bias), 1.0 pt at rv < (40 + bias).

================================================================================
v1.4 — BREAKDOWN LOG THRESHOLD 3.0 → 3.5
================================================================================
  #BREAKDOWN  Per-indicator breakdown log threshold raised from 3.0 to 3.5.
              Pairs scoring < 3.5 no longer get the full EMA/RSI/MACD/etc
              breakdown line, reducing log noise from weak signals that
              would never trigger a trade anyway (default threshold 4.5/9).

================================================================================
v1.3 — DUAL TF SCAN INTERVALS + SIDEBAR LABEL FIX
================================================================================
  #INTERVALS  Dual TF scan intervals changed:
              Min5 trend scan: 45s → 20s
              Min1 entry check reference: 15s → 10s
              Updated in DEFAULT_CONFIG, __init__ defaults, and _ivl() fallback.

  #SIDEBAR    Sidebar dual TF hint label corrected. Previously showed
              "Entry check 15s (Min1)" which implied a separate 15s timer
              for the Min1 check — but _entry_scan_interval was only used
              in the label, never in actual loop timing. The Min1 check
              fires inside each trend scan cycle, not on its own timer.
              Label now reads: "Trend scan 20s (Min5), Min1 check within
              each cycle" which is accurate.

  #BREAKDOWN  Per-indicator breakdown log threshold noted: pairs scoring
              < 3.0 are silently skipped (existing behaviour, documented).

================================================================================
v1.2 — CHART WARNING FIX + SCORES LOG WRAPPING
================================================================================
  #LEGEND   matplotlib "No artists with labels" UserWarning silenced.
            Both ax_p.legend() and ax_m.legend() now check
            get_legend_handles_labels() first and only call legend()
            when labelled artists actually exist. This warning was
            firing every chart redraw cycle, spamming the console and
            masking real errors in the output.

  #SCORES   Scan summary log now wraps into rows of 10 pairs instead
            of a single long line. With 19 pairs the old single-line
            format ran off the right edge of the log box, making the
            last 6-7 pairs invisible without horizontal scrolling.
            New format: "Scores → " for row 1, "         " indent
            for row 2, so the log stays clean and all pairs show.

================================================================================
v1.1 — ATR CACHE: WARM THRESHOLD ACROSS RESTARTS
================================================================================
Previously the AdaptiveTriggerEngine wiped all ATR history on every bot start,
requiring ~10 minutes of scan cycles before the volatility-adjusted threshold
could influence trade entry. Frequent restarts (crashes, config tweaks) each
burned a new warmup window, leaving the bot effectively running on a flat
threshold with no ATR context.

  #ATR-CACHE  AdaptiveTriggerEngine gains save_atr_cache() and
              restore_atr_from_cache() methods. ATR history is written to
              hermesbot_atr_cache.json every 10 scan cycles (~5 min). On
              bot start, cache data younger than 4 hours is loaded back,
              skipping the warmup entirely. Data older than 4 h is discarded
              so a stale overnight cache never poisons a fresh session.

  #RESET      reset_session() no longer clears ATR history — it only clears
              recent_trades and hold_streak (session-specific data). ATR
              context is cross-session and intentionally preserved.

  #PATH       ATR_CACHE_FILE path constant added alongside STATE_FILE.
              Cache is stored at ~/HermesBot/hermesbot_atr_cache.json.

================================================================================
v1.0 — OFFICIAL BASELINE (consolidated from legacy v2.6.x patch series)
================================================================================
This is the first official versioned release. It consolidates all changes from
the legacy v2.6.2.x / v2.6.3.0 internal patch series into a clean baseline.

  #ATR  ATR gate relaxed 0.10% → 0.06% per candle.
        The 0.10 threshold was silencing the bot during normal low-volatility
        sessions (e.g. quiet crypto evenings, post-US-close hours). BTC on Min5
        routinely moves 0.07-0.09% per candle in calm markets — well under the
        old gate. 0.06% is enough to exclude genuinely flat/dead markets while
        allowing normal scalp conditions through.

  #FILT Full filter-reason logging: _passes_filters now returns all blocking
        reasons joined with " | " instead of only the first. This makes it
        immediately clear in the live log when multiple gates fire at once,
        enabling rapid diagnosis without reading source code.

  #P07  Bare except+pass blocks (42 sites): every silently-swallowing
        `except Exception: pass` replaced with
        `except Exception as _exc: _file_logger.debug("suppressed error: %s", _exc)`.
        Errors are still suppressed (no behaviour change) but are now visible
        in hermesbot.log at DEBUG level — previously invisible failures are
        now diagnosable.

  #P08  @retry_on_error decorator wired onto mexc_public(). The decorator was
        defined in the v2.6.2.x series but never applied to any function.
        mexc_public now retries automatically on TimeoutError / ConnectionError
        / OSError with exponential backoff (0.5s, 1s, 2s). The inner
        HTTP-level retry loop is kept as a secondary defence for 429/5xx.

  #P10  PAIRS global no longer shadows config["pairs"].
        PAIRS (full UI list) is used only for display/tabs.
        SCAN_PAIRS is derived at startup from config["pairs"] when present,
        falling back to PAIRS. _active_pairs() and the scanner use SCAN_PAIRS,
        so user-configured pair lists are now respected end-to-end.

  #P06  Thread-safe UI scheduling helper (ui_schedule / start_ui_queue_drain)
        added. Existing root.after(0, ...) call sites are unchanged in this
        release; migration is recommended incrementally going forward.

  #P05  WS._restart_connection() joins old thread before spawning new one —
        prevents duplicate price callbacks on reconnect.

  #P04  WebSocket health monitor: only inbound frames update _last_data.
        Outbound pings no longer mask a dead feed.

  #P03  round_vol() returns 0 for sub-tick volumes instead of silently
        rounding up, preventing unintended minimum-size live orders.

  #P02  Claude prompt f-strings: all example JSON blocks escaped with {{...}}
        so Python does not evaluate them as dict literals. Fixes silent AI
        layer failures in claude_decision, claude_near_tp_check,
        claude_stale_trade_check.

  #P01  _RateLimiter.acquire() now loops until a token is granted. Previously
        a single sleep without re-checking led to 429 storms under contention.

  #DUP  Duplicate import block removed — all stdlib imports appear once.

================================================================================
v2.4 — SCALE-UP PERFORMANCE: THREADPOOL + BATCHED UI + STAGGERED H1/H4
================================================================================
Four changes that allow scaling from 10 to 25-30 pairs without UI lag or
rate-limit hammering. All annotated `SCALE v2.4-#N`.

  #1  THREADPOOLEXECUTOR — replaces per-cycle thread creation
      Previously each scan cycle created one threading.Thread per pair and
      destroyed it on join. At 30+ pairs this means 30+ thread create/destroy
      operations every 30 seconds. Python threads are OS threads (~1MB stack
      each) so this is expensive and wastes GC time.

      A single ThreadPoolExecutor(max_workers=12) is created once at __init__
      and reused for every cycle. Workers are idle-waiting between cycles, not
      recreated. Max 12 workers regardless of pair count — extra pairs queue
      behind available workers rather than all launching simultaneously.
      concurrent.futures.as_completed replaces the manual join loop.

  #2  BATCHED UI PRICE UPDATES — eliminates per-pair root.after spam
      Previously _scan_pair fired root.after(0, self._set_price) once per pair
      per cycle — up to 30 individual Tkinter event-queue entries. Tkinter
      processes these serially on the main thread; at high pair counts this
      causes visible UI stutter between each entry.

      All price updates are now collected into a dict during the scan, then
      flushed in a single root.after(0, ...) call at the end of the cycle.
      The Tkinter event queue gets 1 entry per cycle instead of N.

  #3  BATCHED UI CHART REDRAWS — same pattern for chart panels
      Chart redraws were also fired individually from _scan_pair. They are now
      collected into a pending_chart_updates dict and flushed in one root.after
      call. The existing 8-second per-panel throttle is preserved.

  #4  STAGGERED H1/H4 TREND FETCHES — avoids REST burst on refresh cycle
      Previously when H1 or H4 refresh triggered (every 10 / 40 cycles), it
      launched one thread per pair simultaneously — 30 REST calls in a burst,
      risking MEXC 429 rate-limit errors.

      H1 and H4 fetches are now staggered: pairs are spread across the next
      N cycles (1 pair per cycle per timeframe) rather than all at once.
      A round-robin index tracks which pair fetches next. This keeps the rate
      at 1-2 extra REST calls per cycle rather than 30 in a single cycle.
      The existing per-pair executor is reused for staggered fetches.

  Log threshold raised from 3.5 → 4.0 for per-indicator breakdown lines.
  At 30 pairs this halves the number of log callbacks fired per cycle.

================================================================================
v2.3 — OVERSOLD BOUNCE SCALP MODE
================================================================================
  #OB-SCALP   New "oversold bounce" entry mode — a sibling of pullback scalp
              designed for exhaustion reversals where no wick rejection exists.

              The pullback scalp requires a wick > 40% of candle range as proof
              that price was rejected. Genuine oversold exhaustion bounces often
              have no wick at all — price simply stops making new lows and a
              solid green candle appears. Those were previously blocked by the
              H1/H4 conflict filter and missed entirely.

              An oversold bounce scalp qualifies when ALL of the following are
              true on the Min5 chart:

                LONG (bounce from bottom):
                • RSI < 32  (genuinely oversold — lower bar than pullback's 55)
                • StochRSI < 25  (momentum deeply oversold)
                • MACD histogram red bars shrinking: last bar less negative than
                  the one before (momentum slowing — the key exhausion signal)
                • Price did NOT make a new 10-bar low on the current candle
                  (bounce candidate, not free-fall)
                • No bearish RSI divergence (price lower low + RSI higher low is
                  BULLISH divergence — that's fine and even preferred)
                • Score >= 3.5/9  (lower bar than pullback's 5.0 — most indicators
                  will be bearish so a high score is impossible by definition)

                SHORT (bounce from top) — mirror conditions:
                • RSI > 68, StochRSI > 75, MACD histogram shrinking upward,
                  no new 10-bar high, no bullish RSI divergence, score >= 3.5

              When an oversold bounce fires:
                • TP tightened to 30% of configured TP  (even quicker exit than
                  pullback scalp's 40% — these are pure scalps, not swings)
                • SL tightened to 50% of configured SL  (cut immediately if wrong)
                • Margin halved (same as pullback scalp)
                • Tagged [OB-SCALP] in the log
                • Does NOT require score >= 5.0 — score is structurally limited
                  when most indicators are still bearish at a bottom

              Distinction from pullback scalp:
                Pullback scalp: wick rejection proof + score >= 5.0 + RSI not extreme
                OB scalp:       exhaustion proof (shrinking histogram) + RSI extreme
                                + no wick requirement + lower score threshold

              Both bypass H1/H4 conflict with tighter risk parameters.

================================================================================
v2.2 — AI SL/TP BUG FIX PATCH
================================================================================
Five bugs in the AI trade-management layer (SL tightening, AI CLOSE, AI TAKE,
trail check, partial TP) are fixed. All changes are annotated `FIX v2.2-#N`.

  #1  WRONG API KEY ATTRIBUTES — SILENT SL UPDATE FAILURE
      _update_sl_on_mexc was called with self.api_key_entry / self.api_secret_entry
      in the TIGHTEN, AI CLOSE, and TAKE paths (lines previously ~6449–6499).
      Those attributes do not exist; the correct names are self.mexc_key_e /
      self.mexc_sec_e (defined at UI build time, used correctly everywhere else).
      Result: every AI-triggered SL update silently raised an AttributeError
      inside the daemon thread and never reached MEXC in live mode.
      Fix: all three wrong call sites now use self.mexc_key_e / self.mexc_sec_e.

  #2  AI CLOSE / TAKE DO NOT ACTUALLY CLOSE POSITION
      The CLOSE and TAKE paths set stop_loss = cur_px ± 0.01% then fired
      _update_sl_on_mexc. MEXC stop orders are conditional orders — they trigger
      only when price reaches the stop level, not immediately. If price ticked
      away between the update and the next fill check the position stayed open
      indefinitely. A market-close order is now placed via _market_close_position()
      immediately after the SL is updated, so the position is closed at market
      price regardless of subsequent price movement. The SL update is retained
      as a safety backstop.

  #3  TRAIL LOG MISSING FROM EVENTS TAB
      The 🚀 AI TRAIL log line used self._log() instead of self._log_event(),
      so the entry appeared only in the main log, not in the Events tab.
      Fix: changed to self._log_event() to match every other AI action log.

  #4  PARTIAL TP SHORT LOG MISSING FROM EVENTS TAB
      In _check_exit_and_close(), the SHORT branch of the partial-TP breakeven
      lock used self._log() while the LONG branch correctly used self._log_event().
      Fix: SHORT branch now uses self._log_event() for consistency.

  #5  profit_pct_margin INFLATED 100×
      raw_profit_pct is already a percentage (e.g. 2.5 for 2.5%).
      The formula `raw_profit_pct * pos.leverage * 100` multiplied by leverage
      AND then by 100 again, sending Claude a number 100× too large (e.g. 5000
      instead of 50 for a 2.5% move at 20× leverage). This caused the AI trail
      logic to see every winning trade as massively more profitable than it was,
      triggering premature trail/TP extension calls.
      Fix: removed the spurious `* 100` — formula is now `raw_profit_pct * pos.leverage`.

================================================================================
v2.6.2.3 — P0 BUG FIX PATCH (applied on top of v2.6.2.2)
================================================================================
The following bugs from the high-value review have been fixed IN PLACE.
Every change is annotated with `FIX P0-#N` near the modified code.

  #1  _RateLimiter.acquire() now LOOPS until a token is granted instead of
      returning after a single sleep. Previously, under contention, the limit
      was effectively unenforced and produced 429 storms.

  #2  Claude prompts had literal `{...}` example JSON inside f-strings. Python
      evaluated those as dict expressions, so the model saw Python repr
      (`{'action': 'TRADE', ...}` with single quotes) which is invalid JSON,
      causing `json.loads` to fail silently and the AI layer to be effectively
      disabled. All such JSON examples are now properly escaped with `{{...}}`.
      (Affected: claude_decision, claude_near_tp_check, claude_stale_trade_check.
      The other prompts were already correctly escaped.)

  #3  round_vol() previously FLOORED a sub-tick volume up to the smallest tick,
      silently sending a real-money order at the minimum size. It now returns 0
      so the caller can detect and skip.

  #4  WebSocket health monitor: outbound pings no longer count as inbound
      activity. Previously a dead market-data feed could be masked because
      pings still sent successfully. Only frames received in _on_message
      update _last_data now.

  #5  WS.update_pairs / update_interval now join the OLD run_forever thread
      (with timeout) via _restart_connection() before spawning a new one.
      Previously the old connection could still be alive when the new one
      subscribed, causing duplicate price callbacks.

  #9  Fee constants in the Claude prompt now reference MAKER_FEE_PCT /
      TAKER_FEE_PCT instead of drifting hardcoded 0.001 / 0.0012 literals.

Helper added below: `ui_schedule(root, fn, *args)` — a thread-safe wrapper
around `root.after(0, ...)` that uses a queue.Queue drain on the UI thread.
The existing many `self.root.after(0, ...)` call sites are left untouched in
this minimal patch (mechanical rewrite of >50 sites without a test harness
was judged too risky); migrating them incrementally is recommended.

P0 #7 (bare `except: pass` swallowing errors in ~80 sites) and P0 #8
(`retry_on_error` decorator defined but unused) were NOT mass-rewritten in
this patch for the same reason — see the review document for the recommended
incremental approach.
================================================================================
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading, time, json, os, hmac, hashlib, uuid, math, csv
import urllib.request, urllib.parse
import urllib.error
from http.client import IncompleteRead
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Callable, Any
from collections import deque
import queue as _queue
import re as _re
import pathlib
import struct
import logging
import logging.handlers
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed  # SCALE v2.4-#1


# ── FIX P0-#6 helper: thread-safe Tk scheduling via a Queue ──────────────────
# Tk is not thread-safe; `root.after(0, ...)` from a worker thread is not
# portably safe (works on CPython/Linux, can crash on macOS/Windows under
# load). Prefer routing UI updates through this queue and draining it on the
# UI thread. Adopt incrementally: replace `self.root.after(0, lambda: foo())`
# with `ui_schedule(self.root, foo)` then start the drain loop once per app
# via `start_ui_queue_drain(root)`.
_ui_queue: "_queue.Queue[Callable[[], Any]]" = _queue.Queue()

def ui_schedule(root, fn, *args, **kwargs):
    """Schedule `fn(*args, **kwargs)` to run on the Tk main thread."""
    _ui_queue.put(lambda: fn(*args, **kwargs))
    # nudge the drain loop in case it is idle
    try:
        root.after_idle(lambda: None)
    except Exception as _exc:
        _file_logger.debug("suppressed error: %s", _exc)

def start_ui_queue_drain(root, interval_ms: int = 25):
    """Call once on the Tk main thread after the root window is built."""
    def _drain():
        try:
            while True:
                cb = _ui_queue.get_nowait()
                try:
                    cb()
                except Exception:
                    logging.getLogger(__name__).exception("ui_schedule callback failed")
        except _queue.Empty:
            pass
        root.after(interval_ms, _drain)
    root.after(interval_ms, _drain)



# ── Optional encryption for stored API keys ───────────────────────────────────
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    _CRYPTO_OK = True
except ImportError:
    _CRYPTO_OK = False

def _machine_key() -> bytes:
    """Derive a stable Fernet key from a machine-specific identifier.
    Uses the machine-id file on Linux/Mac, or the Windows MachineGuid registry key.
    Falls back to a fixed per-installation salt stored alongside the keys file.
    """
    machine_id = ""
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(path) as f:
                machine_id = f.read().strip()
            break
        except OSError:
            pass
    if not machine_id:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Cryptography")
            machine_id = winreg.QueryValueEx(key, "MachineGuid")[0]
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)
    if not machine_id:
        # Last resort: use/create a per-installation random salt file
        salt_path = str(pathlib.Path.home() / "HermesBot" / ".install_salt")
        try:
            with open(salt_path, "r") as f:
                machine_id = f.read().strip()
        except OSError:
            import secrets
            machine_id = secrets.token_hex(32)
            try:
                with open(salt_path, "w") as f:
                    f.write(machine_id)
                os.chmod(salt_path, 0o600)
            except OSError:
                pass
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"HermesBot_v5",
                     iterations=100_000)
    raw = kdf.derive(machine_id.encode())
    return base64.urlsafe_b64encode(raw)

def _encrypt_keys(payload: dict) -> str:
    """Encrypt key payload to a JSON string. Returns plaintext JSON if crypto unavailable."""
    if not _CRYPTO_OK:
        return json.dumps(payload)
    f = Fernet(_machine_key())
    plaintext = json.dumps(payload).encode()
    return json.dumps({"encrypted": True, "data": f.encrypt(plaintext).decode()})

def _decrypt_keys(raw: str) -> dict:
    """Decrypt key file content. Handles both encrypted and legacy plaintext formats."""
    outer = json.loads(raw)
    if not outer.get("encrypted"):
        return outer   # legacy plaintext — return as-is
    if not _CRYPTO_OK:
        raise RuntimeError("Key file is encrypted but cryptography package is not installed. "
                           "Run: pip install cryptography")
    f = Fernet(_machine_key())
    try:
        plaintext = f.decrypt(outer["data"].encode())
        return json.loads(plaintext)
    except InvalidToken:
        raise RuntimeError("Failed to decrypt key file — wrong machine or corrupted file.")

# ── WebSocket support ──────────────────────────────────────────────────────────
try:
    import websocket  # websocket-client (threaded)
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

# ── Async WebSocket (preferred if available) ──────────────────────────────────
try:
    import asyncio
    import websockets as _ws_async
    ASYNC_WS_AVAILABLE = True
except ImportError:
    ASYNC_WS_AVAILABLE = False

# ── YAML config support ───────────────────────────────────────────────────────
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# ── Paths ──────────────────────────────────────────────────────────────────────
BOT_VERSION = "v2.8-TUNED"

_HOME = pathlib.Path.home() / "HermesBot"
_HOME.mkdir(exist_ok=True)
STATE_FILE     = str(_HOME / "hermesbot_state.json")
ATR_CACHE_FILE = str(_HOME / "hermesbot_atr_cache.json")  # warm ATR history — survives restarts
KEYS_FILE      = str(_HOME / "hermesbot_keys.json")
CONFIG_FILE = str(_HOME / "hermesbot_config.yaml")
ORDERS_FILE = str(_HOME / "hermesbot_orders.json")
LOG_FILE    = str(_HOME / "hermesbot.log")

# ── File Logging (rotating, 5 MB x 3 files) ──────────────────────────────────
_file_logger = logging.getLogger("HermesBot")
_file_logger.setLevel(logging.DEBUG)
_log_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"
)
_log_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))
_file_logger.addHandler(_log_handler)

def log_structured(level, event, **kwargs):
    """Log structured event with context for better analysis."""
    import json
    context = " ".join(f"{k}={v}" for k, v in kwargs.items())
    message = f"[{event}] {context}" if context else f"[{event}]"
    if level == "debug":
        _file_logger.debug(message)
    elif level == "info":
        _file_logger.info(message)
    elif level == "warning":
        _file_logger.warning(message)
    elif level == "error":
        _file_logger.error(message)
    elif level == "critical":
        _file_logger.critical(message)

# ── Config file (YAML) ────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "signal_threshold": 4.5,
    "leverage": 10,
    "stop_loss_pct": 0.008,
    "take_profit_pct": 0.02,
    "max_trades": 2,
    "hedge_enabled": True,
    "hedge_drawdown_pct": 0.03,
    "stack_threshold": 6.0,
    "scan_interval_sec": 30,  # For single TF mode
    "trend_scan_interval_sec": 20,  # For Min5 trend confirmation (dual TF)
    "entry_scan_interval_sec": 10,  # For Min1 entry check within each trend cycle (display only)
    "timeframe": "Min5",
    "margin_usd": 50,
    "overnight_mode": True,
    "overnight_start_utc": 22,
    "overnight_end_utc": 6,
    "pairs": [
        "BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "DOGE_USDT",
        "XAU_USDT", "NAS100_USDT", "SPX_USDT", "EUR_USDT", "NVDA_USDT",
        "ADA_USDT", "AVAX_USDT", "BNB_USDT", "LINK_USDT", "TON_USDT",
        "TRX_USDT", "DOT_USDT", "LTC_USDT", "GBP_USDT", "US30_USDT"
    ],
    "ws_enabled": True,
    "ws_reconnect_max": 50,
    "rate_limit_per_sec": 18,
}

# ── Constants ─────────────────────────────────────────────────────────────────────
# Time constants
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
DEFAULT_SCAN_INTERVAL_SEC = 30

# Trading constants
DEFAULT_LEVERAGE = 10
MAX_LEVERAGE = 125
MIN_LEVERAGE = 1
DEFAULT_STOP_LOSS_PCT = 0.008  # 0.8%
DEFAULT_TAKE_PROFIT_PCT = 0.02  # 2%
DEFAULT_HEDGE_DRAWDOWN_PCT = 0.03  # 3%
DEFAULT_MARGIN_USD = 50

# Fee constants (MEXC Futures API, effective May 2026)
MAKER_FEE_PCT = 0.0004  # 0.04%
TAKER_FEE_PCT = 0.0006  # 0.06%
SLIPPAGE_PCT = 0.0005  # 0.05% estimated slippage

# Risk management constants
MIN_NET_RR = 2.0  # Minimum net risk/reward ratio
ATR_SL_MULTIPLIER = 1.5  # SL must be at least 1.5x ATR
MAX_DRAWDOWN_PCT = 0.40  # 40% max drawdown for hedge trigger
STACK_MULTIPLIER = 1.5  # Multiplier for stacking positions

# API constants
MAX_API_RETRIES = 3
API_TIMEOUT_SEC = 12
RATE_LIMIT_PER_SEC = 18
MAX_RECONNECT_ATTEMPTS = 100

# Data constants
DEFAULT_CANDLE_LIMIT = 200
RECENT_TRADES_MAXLEN = 50
PRICE_HISTORY_MAXLEN = 5
CHART_THROTTLE_SEC = 8.0

# AI constants
CLAUDE_MAX_TOKENS = 120
CLAUDE_COOLDOWN_SEC = 30  # Minimum time between Claude calls
NEAR_TP_THRESHOLD_PCT = 0.20  # 20% of remaining TP gap
STALE_TRADE_MINUTES = 60  # Minutes before considering trade stale
CLEANUP_INTERVAL_CYCLES = 60  # Run cleanup every N cycles

# Chart constants
CHART_ZOOM_MIN = 15
CHART_ZOOM_MAX = 200
CHART_ZOOM_DEFAULT = 60

# ── Per-pair minimum ATR thresholds (% per Min5 candle) ──────────────────────
# Replaces the flat 0.06% gate. Each value reflects the asset's typical quiet-
# session ATR on Min5. Pairs moving less than this are genuinely flat/dead.
# Used in compute_signals() via the atr_min kwarg; fallback = 0.06 for unknown pairs.
PAIR_ATR_MIN: dict = {
    "BTC_USDT":    0.04,  # deep liquidity, low Min5 % moves in calm sessions
    "ETH_USDT":    0.05,
    "SOL_USDT":    0.07,  # higher beta alt
    "XRP_USDT":    0.06,
    "DOGE_USDT":   0.07,
    "XAU_USDT":    0.03,  # gold moves slowly per candle in % terms
    "NAS100_USDT": 0.04,  # index, slow %
    "SPX_USDT":    0.03,
    "EUR_USDT":    0.02,  # forex, very small % moves
    "NVDA_USDT":   0.05,
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":    0.06,  # mid-cap crypto, moderate volatility
    "AVAX_USDT":   0.07,  # high-beta L1, similar to SOL
    "BNB_USDT":    0.05,  # large-cap, less volatile than alts
    "LINK_USDT":   0.07,  # oracle token, reactive to news
    "TON_USDT":    0.07,  # high volume surges; treat like mid-beta alt
    "TRX_USDT":    0.05,  # stablecoin-heavy chain, lower % swings
    "DOT_USDT":    0.07,  # historically volatile parachain token
    "LTC_USDT":    0.05,  # deep OB, moves like large-cap
    "GBP_USDT":    0.02,  # forex, similar to EUR
    "US30_USDT":   0.04,  # Dow Jones index, similar to NAS100
}

# ── Per-pair RSI bias (shifts oversold/overbought scoring thresholds) ─────────
# Trending assets (gold, indices, forex) rarely touch RSI < 30. Without a bias
# the RSI score points almost never fire, making those pairs' scores systematically
# lower. A positive bias raises the threshold: LONG scores at rv < (30 + bias).
# 0 = standard crypto  |  +8 = trending macro  |  +5 = semi-trending stock
PAIR_RSI_BIAS: dict = {
    "BTC_USDT":    0,
    "ETH_USDT":    0,
    "SOL_USDT":    0,
    "XRP_USDT":    0,
    "DOGE_USDT":   0,
    "XAU_USDT":    8,   # gold trends; RSI < 38 = genuinely oversold for gold
    "NAS100_USDT": 8,
    "SPX_USDT":    8,
    "EUR_USDT":    8,
    "NVDA_USDT":   5,
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":    0,   # standard crypto behaviour
    "AVAX_USDT":   0,
    "BNB_USDT":    0,
    "LINK_USDT":   0,
    "TON_USDT":    0,
    "TRX_USDT":    0,
    "DOT_USDT":    0,
    "LTC_USDT":    0,
    "GBP_USDT":    8,   # trending forex — same treatment as EUR
    "US30_USDT":   8,   # Dow Jones index — same treatment as NAS100/SPX
}

# ── Per-pair lower-highs filter relaxation ────────────────────────────────────
# High-beta alts naturally form lower highs within broader uptrends (normal
# pullback structure). For these pairs the lower-highs LONG block is bypassed
# when StochRSI is deeply oversold (≤ 20) — that combination means the price
# structure is a pullback, not distribution, and StRSI confirms a bounce is due.
# Pairs NOT in this set get the standard hard block regardless of StRSI.
PAIR_LH_RELAXED: set = {
    "TON_USDT",   # high-beta, frequent pullbacks within uptrend
    "DOGE_USDT",  # meme coin — lower highs during consolidation are normal
    "SOL_USDT",   # high-beta L1, natural retracement structure
    "AVAX_USDT",  # same profile as SOL
    "DOT_USDT",   # historically choppy with deep pullbacks
    "LINK_USDT",  # reactive oracle token — pullbacks look like lower highs
    "ADA_USDT",   # long consolidation periods with lower-highs structure
    "XRP_USDT",   # fast-moving, frequently forms lower highs in bull runs
}


class HermesBotError(Exception):
    """Base exception for HermesBot errors."""
    pass

class ConfigurationError(HermesBotError):
    """Raised when configuration is invalid or missing."""
    pass

class APIError(HermesBotError):
    """Raised when MEXC API call fails."""
    def __init__(self, message, code=None, response=None):
        super().__init__(message)
        self.code = code
        self.response = response

class AuthenticationError(HermesBotError):
    """Raised when API authentication fails."""
    pass

class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    pass

class NetworkError(HermesBotError):
    """Raised when network operation fails."""
    pass

class OrderError(HermesBotError):
    """Raised when order placement or execution fails."""
    pass

class InsufficientFundsError(OrderError):
    """Raised when insufficient funds for order."""
    pass

class PositionError(HermesBotError):
    """Raised when position operation fails."""
    pass

class SignalError(HermesBotError):
    """Raised when signal computation fails."""
    pass

class WebSocketError(HermesBotError):
    """Raised when WebSocket connection fails."""
    pass

# ── Retry Logic ─────────────────────────────────────────────────────────────────
import functools

def retry_on_error(max_retries=MAX_API_RETRIES, backoff_base=0.5, retryable_errors=None):
    """
    Decorator for retrying functions on specific errors with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_base: Base delay in seconds (multiplied by 2^attempt)
        retryable_errors: Tuple of exception types to retry on (default: common network/API errors)
    """
    if retryable_errors is None:
        retryable_errors = (NetworkError, RateLimitError, TimeoutError, ConnectionError)
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable_errors as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = backoff_base * (2 ** attempt)
                        _file_logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        _file_logger.error(
                            f"All {max_retries} attempts failed for {func.__name__}: {e}"
                        )
                except Exception as e:
                    # Don't retry on non-retryable errors
                    _file_logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            # If we exhausted retries, raise the last exception
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Function {func.__name__} failed after {max_retries} attempts")
        return wrapper
    return decorator

# ── Input Validation ────────────────────────────────────────────────────────────
def validate_api_response(response, required_fields=None, field_types=None):
    """
    Validate API response structure and field types.
    
    Args:
        response: The API response dict/list to validate
        required_fields: List of required field names (for dict responses)
        field_types: Dict mapping field names to expected types
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if response is None:
        return False, "Response is None"
    
    if isinstance(response, dict):
        if required_fields:
            missing_fields = [f for f in required_fields if f not in response]
            if missing_fields:
                return False, f"Missing required fields: {missing_fields}"
        
        if field_types:
            for field, expected_type in field_types.items():
                if field in response and not isinstance(response[field], expected_type):
                    return False, f"Field '{field}' has wrong type: expected {expected_type}, got {type(response[field])}"
    
    elif isinstance(response, list):
        if not response:
            return False, "Response list is empty"
    
    return True, ""

def validate_ticker_response(ticker):
    """Validate ticker API response has required fields."""
    if not isinstance(ticker, dict):
        return False, "Ticker response is not a dict"
    
    required_fields = ["last", "funding"]
    is_valid, error = validate_api_response(ticker, required_fields=required_fields)
    if not is_valid:
        return False, error
    
    try:
        price = float(ticker["last"])
        funding = float(ticker.get("funding", 0))
        if price <= 0:
            return False, f"Invalid price: {price}"
    except (ValueError, TypeError) as e:
        return False, f"Invalid ticker data types: {e}"
    
    return True, ""

def validate_kline_response(klines):
    """Validate kline/candlestick API response."""
    if not isinstance(klines, list):
        return False, "Klines response is not a list"
    
    if len(klines) == 0:
        return False, "Klines response is empty"
    
    for i, bar in enumerate(klines[:5]):  # Validate first 5 bars
        if not isinstance(bar, (list, tuple)) or len(bar) < 6:
            return False, f"Bar {i} has invalid format"
        
        try:
            # Validate OHLCV values are numeric
            for j in range(6):
                float(bar[j])
        except (ValueError, TypeError, IndexError):
            return False, f"Bar {i} contains non-numeric values"
    
    return True, ""

def validate_position_response(positions):
    """Validate positions API response."""
    if not isinstance(positions, (list, dict)):
        return False, "Positions response is not a list or dict"
    
    # Handle both list format and dict with 'data' or 'list' key
    pos_list = positions
    if isinstance(positions, dict):
        pos_list = positions.get("data", positions.get("list", []))
    
    if not isinstance(pos_list, list):
        return False, "Positions data is not a list"
    
    required_fields = ["symbol", "positionType", "holdVol", "avgPrice"]
    for i, pos in enumerate(pos_list):
        if not isinstance(pos, dict):
            return False, f"Position {i} is not a dict"
        
        is_valid, error = validate_api_response(pos, required_fields=required_fields)
        if not is_valid:
            return False, f"Position {i}: {error}"
        
        try:
            float(pos.get("holdVol", 0))
            float(pos.get("avgPrice", 0))
        except (ValueError, TypeError):
            return False, f"Position {i} has invalid numeric fields"
    
    return True, ""

def load_config():
    """Load config from YAML file, falling back to defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE) and YAML_AVAILABLE:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
            cfg.update(user_cfg)
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)
    return cfg

def save_config(cfg):
    """Persist config to YAML file."""
    if not YAML_AVAILABLE:
        return
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
    except Exception as _exc:
        _file_logger.debug("suppressed error: %s", _exc)

# ── Order state persistence ───────────────────────────────────────────────────
def _atomic_write(path, text):
    """Write file atomically: write to .tmp then os.replace."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        try:
            f.flush()
            os.fsync(f.fileno())
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)
    os.replace(tmp, path)

def save_open_orders(orders):
    """Persist open order IDs to disk for crash recovery."""
    try:
        _atomic_write(ORDERS_FILE, json.dumps(orders, indent=2))
    except Exception as _exc:
        _file_logger.debug("suppressed error: %s", _exc)

def load_open_orders():
    """Load persisted order IDs from disk."""
    if not os.path.exists(ORDERS_FILE):
        return []
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

# ── Optional deps ──────────────────────────────────────────────────────────────
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

import warnings
warnings.filterwarnings("ignore", message=".*tight_layout.*")

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.gridspec import GridSpec
    MPLOT = True
except ImportError:
    MPLOT = False

# ══════════════════════════════════════════════════════════════════════════════
#  PALETTE
# ══════════════════════════════════════════════════════════════════════════════
BG    = "#080c14"
BG2   = "#0f1520"
BG3   = "#182030"
BG4   = "#06080f"
SEP   = "#1a2840"
SEP2  = "#1f3050"

GREEN  = "#00e5a0"
RED    = "#ff4060"
BLUE   = "#38bdf8"
AMBER  = "#fbbf24"
PURPLE = "#a78bfa"
CYAN   = "#06b6d4"
YELLOW = "#ffd43b"
ORANGE = "#ff922b"
PINK   = "#f783ac"
TEAL   = "#14b8a6"

TEXT    = "#f0f4f8"
SUB     = "#94a3b8"
MUTED   = "#64748b"
DIM     = "#3d5068"

C_UP   = "#00e676"
C_DOWN = "#ff3d57"
C_GRID = "#161d2e"
C_AX   = "#495057"

PAIR_COL = {
    "BTC_USDT":      "#ffa94d",
    "ETH_USDT":      "#4dabf7",
    "SOL_USDT":      "#cc5de8",
    "XRP_USDT":      "#22d3ee",
    "DOGE_USDT":     "#00e676",
    "XAU_USDT":      "#ffd700",
    "NAS100_USDT":   "#fb923c",
    "SPX_USDT":      "#facc15",
    "EUR_USDT":      "#60a5fa",
    "NVDA_USDT":     "#76b900",
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":      "#3b82f6",   # Cardano blue
    "AVAX_USDT":     "#ef4444",   # Avalanche red
    "BNB_USDT":      "#eab308",   # Binance yellow
    "LINK_USDT":     "#2563eb",   # Chainlink deep blue
    "TON_USDT":      "#06b6d4",   # TON cyan
    "TRX_USDT":      "#f43f5e",   # TRON rose
    "DOT_USDT":      "#e879f9",   # Polkadot pink
    "LTC_USDT":      "#94a3b8",   # Litecoin silver
    "GBP_USDT":      "#818cf8",   # GBP indigo
    "US30_USDT":     "#f97316",   # Dow deep orange
}
PAIRS = list(PAIR_COL.keys())

# ── SCAN_PAIRS: what the bot actually scans — respects config["pairs"] ────────
# PAIRS (above) is the full UI/display list and never changes.
# SCAN_PAIRS is what the scanner and signal engine iterate over.
# It is initialised from config["pairs"] if that key is present, otherwise
# falls back to PAIRS so the bot works identically with no config file.
# This fixes the issue where config["pairs"] was loaded but PAIRS (a global)
# was used everywhere in the scan loop, silently ignoring user customisation.
_startup_cfg = load_config() if callable(load_config) else {}
_cfg_pairs   = _startup_cfg.get("pairs", [])
SCAN_PAIRS: list = (
    [p for p in _cfg_pairs if p in PAIR_COL]  # validated: only known pairs
    if _cfg_pairs else list(PAIRS)
)
del _startup_cfg, _cfg_pairs  # don't leave temp vars at module level


# Human-readable short names for display
PAIR_DISPLAY = {
    "BTC_USDT":      "BTC",
    "ETH_USDT":      "ETH",
    "SOL_USDT":      "SOL",
    "XRP_USDT":      "XRP",
    "DOGE_USDT":     "DOGE",
    "XAU_USDT":      "GOLD",
    "NAS100_USDT":   "NAS100",
    "SPX_USDT":      "SPX",
    "EUR_USDT":      "EUR",
    "NVDA_USDT":     "NVDA",
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":      "ADA",
    "AVAX_USDT":     "AVAX",
    "BNB_USDT":      "BNB",
    "LINK_USDT":     "LINK",
    "TON_USDT":      "TON",
    "TRX_USDT":      "TRX",
    "DOT_USDT":      "DOT",
    "LTC_USDT":      "LTC",
    "GBP_USDT":      "GBP",
    "US30_USDT":     "US30",
}

# Pairs excluded from live API trading (price precision / volume issues)
API_EXCLUDED = set()  # PEPE_USDT was excluded due to decimal precision, but may work now

def pair_label(p):
    return PAIR_DISPLAY.get(p, p.replace("_USDT","").replace("1000",""))

# MEXC volume precision (decimal places) per pair
# Determined by MEXC contract specs — wrong precision = code 2015 rejection
# MEXC volume precision (volScale from API docs)
# volScale=0 means integer contracts. Vol is in CONTRACT UNITS not coin units.
# contractSize tells you what 1 contract = in coin terms.
# BTC: volScale=0, contractSize=0.0001 BTC → vol=1 means 0.0001 BTC
# All MEXC futures pairs use USDT notional as vol (confirmed from UI).
# 4 decimal places is sufficient — minimums are ~2-6 USDT so sub-cent precision is fine.
PAIR_VOL_PRECISION = {
    # MEXC API: volScale=0, volUnit=1 for ALL pairs → integer contracts only.
    # vol = int(margin * leverage / (price * contractSize)) — always whole numbers.
    "BTC_USDT":    0,
    "ETH_USDT":    0,
    "SOL_USDT":    0,
    "XRP_USDT":    0,
    "DOGE_USDT":   0,
    "PEPE_USDT":   0,
    "XAU_USDT":    0,
    "SUI_USDT":    0,
    "TESLA_USDT":  0,
    "SPCX_USDT":   0,
    "EUR_USDT":    0,
    "GBP_USDT":    0,
    "JPY_USDT":    0,
    "SPX_USDT":    0,
    "NAS100_USDT": 0,
    "US30_USDT":   0,
    "AAPL_USDT":   0,
    "MSFT_USDT":   0,
    "NVDA_USDT":   0,
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":    0,
    "AVAX_USDT":   0,
    "BNB_USDT":    0,
    "LINK_USDT":   0,
    "TON_USDT":    0,
    "TRX_USDT":    0,
    "DOT_USDT":    0,
    "LTC_USDT":    0,
}

# Contract sizes (how much 1 contract = in coin terms)
# Used to calculate correct number of contracts from margin
PAIR_CONTRACT_SIZE = {
    # All values verified against MEXC API /api/v1/contract/detail (June 2025)
    # vol = int(margin * leverage / (price * contractSize))  — integer contracts always
    "BTC_USDT":      0.0001,    # confirmed: 0.0001 BTC/contract
    "ETH_USDT":      0.01,      # fixed: was 0.001 (MEXC = 0.01)
    "SOL_USDT":      0.1,       # confirmed: 0.1 SOL/contract
    "XRP_USDT":      1,         # fixed: was 10 (MEXC = 1)
    "DOGE_USDT":     100,       # confirmed: 100 DOGE/contract
    "PEPE_USDT":     10000000,  # fixed: was 1M (MEXC = 10M)
    "XAU_USDT":      0.001,     # fixed: was 0.01 (MEXC = 0.001)
    "SUI_USDT":      1,         # fixed: was 10 (MEXC = 1)
    "TESLA_USDT":    0.01,      # confirmed: 0.01 TSLA/contract
    "SPCX_USDT":     0.01,      # fixed: was 1 (MEXC = 0.01, uses SPCXSTOCK_USDT)
    "EUR_USDT":      1,         # confirmed: 1 EUR/contract
    "GBP_USDT":      1,         # confirmed: 1 GBP/contract
    "JPY_USDT":      100,       # confirmed: 100 JPY/contract
    "SPX_USDT":      1,         # fixed: was 0.01 (MEXC = 1 SPX token/contract)
    "NAS100_USDT":   0.00001,   # fixed: was 0.01 (MEXC = 0.00001)
    "US30_USDT":     0.00001,   # fixed: was 0.01 (MEXC = 0.00001)
    "AAPL_USDT":     0.01,      # fixed: was 1 (MEXC AAPLSTOCK_USDT = 0.01)
    "MSFT_USDT":     0.01,      # fixed: was 1 (MEXC MSFTSTOCK_USDT = 0.01)
    "NVDA_USDT":     0.01,      # fixed: was 1 (MEXC NVIDIA_USDT = 0.01)
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":      1,         # fixed: was 10 (MEXC = 1)
    "AVAX_USDT":     0.1,       # confirmed: 0.1 AVAX/contract
    "BNB_USDT":      0.01,      # confirmed: 0.01 BNB/contract
    "LINK_USDT":     0.1,       # fixed: was 1 (MEXC = 0.1)
    "TON_USDT":      1,         # confirmed: 1 TON/contract (TONCOIN_USDT)
    "TRX_USDT":      10,        # fixed: was 100 (MEXC = 10)
    "DOT_USDT":      0.1,       # fixed: was 1 (MEXC = 0.1)
    "LTC_USDT":      0.01,      # confirmed: 0.01 LTC/contract
}

# MEXC futures use USDT notional as vol universally (confirmed BTC + NVDA from UI).
# vol = margin * leverage  for ALL pairs — no division by price or contract size.
# Minimum order vol (USDT) per pair — exchange-enforced floor.
# BTC confirmed ~6.05 USDT; stock perps confirmed ~2.06 USDT.
# For unlisted pairs the fallback is 1.0 USDT (conservative).
PAIR_VOL_MIN_USDT = {
    "BTC_USDT":    6.06,
    "ETH_USDT":    6.06,
    "SOL_USDT":    6.06,
    "XRP_USDT":    6.06,
    "DOGE_USDT":   6.06,
    "PEPE_USDT":   6.06,
    "XAU_USDT":    6.06,
    "SUI_USDT":    6.06,
    "EUR_USDT":    6.06,
    "GBP_USDT":    6.06,
    "JPY_USDT":    6.06,
    "SPX_USDT":    6.06,
    "NAS100_USDT": 6.06,
    "US30_USDT":   6.06,
    "NVDA_USDT":   2.06,   # confirmed from MEXC UI: 2.0592 USDT minimum
    "AAPL_USDT":   2.06,
    "MSFT_USDT":   2.06,
    "TESLA_USDT":  2.06,
    "SPCX_USDT":   2.06,
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":    6.06,
    "AVAX_USDT":   6.06,
    "BNB_USDT":    6.06,
    "LINK_USDT":   6.06,
    "TON_USDT":    6.06,
    "TRX_USDT":    6.06,
    "DOT_USDT":    6.06,
    "LTC_USDT":    6.06,
}

# Minimum margin (USDT) to open a position that meets MEXC vol floor.
# Formula: min_margin = PAIR_VOL_MIN_USDT[sym] / leverage
# At minimum leverage (e.g. 1x): min_margin = vol_min (worst case).
# These are conservative reference values used for the vol==0 log message.
# Bot calculates dynamically: min_mg = vol_min_usdt / lev at trade time.
PAIR_MIN_MARGIN = {
    "BTC_USDT":    0.07,   # 6.06 USDT min vol / 100x typical = $0.06
    "ETH_USDT":    0.07,
    "SOL_USDT":    0.07,
    "XRP_USDT":    0.07,
    "DOGE_USDT":   0.07,
    "XAU_USDT":    0.07,
    "NAS100_USDT": 0.13,   # 6.06 / 50x max lev
    "SPX_USDT":    0.13,
    "EUR_USDT":    0.07,
    "NVDA_USDT":   0.42,   # 2.06 / 5x max lev
    "AAPL_USDT":   0.42,
    "MSFT_USDT":   0.42,
    "TESLA_USDT":  0.42,
    "SPCX_USDT":   0.42,
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":    0.07,   # 6.06 / 100x
    "AVAX_USDT":   0.07,
    "BNB_USDT":    0.07,
    "LINK_USDT":   0.07,
    "TON_USDT":    0.07,
    "TRX_USDT":    0.07,
    "DOT_USDT":    0.07,
    "LTC_USDT":    0.07,
    "GBP_USDT":    0.07,
    "US30_USDT":   0.31,   # 6.06 / 20x max lev
}

# Auto-learn precision: if code 2015, retry with fewer decimals
_learned_precision = {
    # Pairs confirmed to require integer contract-count vol, not USDT notional.
    # Sentinel value -1 means: use floor(margin*lev / price / contract_size).
    # Add pairs here if they consistently reject with code=2015 on USDT vol.
    "DOGE_USDT": -1,
    "TRX_USDT":  -1,
    "XRP_USDT":  -1,   # likely same — 10 contracts per unit, low price
}  # runtime-updated if orders fail or fetched from API

def fetch_contract_precision():
    """
    Query MEXC futures API for exact volume precision per pair.
    Tries contract detail endpoint. Updates PAIR_VOL_PRECISION in place.
    """
    updated = []
    try:
        _rate_limiter.acquire()
        url = MEXC_BASE + "/api/v1/contract/detail/country"
        req = urllib.request.Request(url, headers={"User-Agent": "Pacbot/1.5"})
        with urllib.request.urlopen(req, timeout=12) as r:
            raw = r.read()
        try:
            d = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            d = json.loads(raw.decode("latin-1"))

        contracts = []
        if d.get("success"):
            data = d.get("data", [])
            if isinstance(data, list):
                contracts = data
            elif isinstance(data, dict):
                contracts = data.get("list", data.get("data", []))

        for info in contracts:
            sym = info.get("symbol", "")
            if sym in PAIRS:
                vol_dp = info.get("volDecimalPlace")
                if vol_dp is not None:
                    PAIR_VOL_PRECISION[sym] = int(vol_dp)
                    updated.append(f"{sym.replace('_USDT','')}=vol{vol_dp}dp")
                price_dp = info.get("priceScale")
                if price_dp is not None:
                    PAIR_PRICE_PRECISION[sym] = int(price_dp)
                    updated.append(f"{sym.replace('_USDT','')}=price{price_dp}dp")
    except Exception as _exc:
        _file_logger.debug("suppressed error: %s", _exc)
    return updated

def round_vol(symbol, vol):
    """Round volume to MEXC required precision. Uses learned values if available.

    FIX P0-#3: previously a sub-tick `vol` (e.g. 0.0001 when min is 0.01) was
    silently floored UP to the minimum tick, sending an unintended real-money
    order. Now we return 0 so the caller can detect and skip.
    """
    base_prec = PAIR_VOL_PRECISION.get(symbol, 2)
    learned   = _learned_precision.get(symbol, base_prec)
    prec      = min(base_prec, learned)
    if prec == 0:
        rounded = int(round(vol, 0))
        return rounded if rounded >= 1 else 0
    min_tick = 10 ** (-prec)
    rounded  = round(vol, prec)
    if rounded < min_tick:
        return 0
    return rounded


# MEXC price precision (decimal places) per pair — from priceScale in contract detail.
# Wrong precision causes code=2015 "Price or quantity precision error" on stoporder/place.
# ETH=2 means prices like 1574.99; SOL=2 means 63.31; PEPE=8 means 0.00001234
PAIR_PRICE_PRECISION = {
    "BTC_USDT":    1,   # priceScale=1  e.g. 61281.5
    "ETH_USDT":    2,   # priceScale=2  e.g. 1585.30
    "SOL_USDT":    2,   # priceScale=2  e.g. 63.23
    "XRP_USDT":    4,   # priceScale=4  e.g. 1.0980
    "DOGE_USDT":   5,   # priceScale=5  e.g. 0.08200
    "PEPE_USDT":   10,  # priceScale=10 (MEXC API confirmed — was 8)
    "XAU_USDT":    2,   # priceScale=2 (MEXC API confirmed — was 1)
    "SUI_USDT":    4,   # priceScale=4  e.g. 0.7104
    "TESLA_USDT":  2,   # priceScale=2  e.g. 386.56
    "SPCX_USDT":   2,   # priceScale=2  e.g. 163.69
    "EUR_USDT":    4,   # priceScale=4  e.g. 1.0823
    "GBP_USDT":    4,   # priceScale=4  e.g. 1.2745
    "JPY_USDT":    6,   # priceScale=6  e.g. 0.006523
    "SPX_USDT":    4,   # priceScale=4  e.g. 0.2964 (SPX crypto token, not S&P index)
    "NAS100_USDT":   0,   # priceScale=0  integer prices (MEXC API — was 1)
    "US30_USDT":     2,   # priceScale=2  e.g. 42500.00 (MEXC API — was 1)
    "AAPL_USDT":     2,   # priceScale=2  e.g. 213.45
    "MSFT_USDT":     2,   # priceScale=2  e.g. 415.30
    "NVDA_USDT":     2,   # priceScale=2  e.g. 875.60
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":    4,   # priceScale=4  e.g. 0.4520
    "AVAX_USDT":   3,   # priceScale=3  e.g. 28.450
    "BNB_USDT":    2,   # priceScale=2  e.g. 580.30
    "LINK_USDT":   3,   # priceScale=3  e.g. 14.230
    "TON_USDT":    3,   # priceScale=3  e.g. 5.820
    "TRX_USDT":    5,   # priceScale=5  e.g. 0.08250
    "DOT_USDT":    3,   # priceScale=3  e.g. 6.380
    "LTC_USDT":    2,   # priceScale=2  e.g. 78.50
}
_learned_price_precision = {}  # runtime-updated from API or after 2015 errors


def round_price(symbol, price):
    """Round a TP/SL price to MEXC required tick precision for the given pair."""
    base_prec = PAIR_PRICE_PRECISION.get(symbol, 2)
    prec      = _learned_price_precision.get(symbol, base_prec)
    return round(price, prec)


# Max leverage per pair (MEXC actual limits)
# PAIR_MAX_LEV: exchange maximum leverage per pair (informational upper bound).
# The bot enforces self._lev() (the UI setting) as the actual cap at trade time —
# see _sync_positions() and _open_position(). These values are the exchange ceiling,
# not the trading leverage.
PAIR_MAX_LEV = {
    "BTC_USDT":    500,
    "ETH_USDT":    500,
    "SOL_USDT":    300,
    "XRP_USDT":    300,
    "DOGE_USDT":   300,
    "PEPE_USDT":    50,
    "XAU_USDT":   1000,
    "SUI_USDT":    300,
    "TESLA_USDT":  100,
    "SPCX_USDT":    50,
    "EUR_USDT":    100,
    "GBP_USDT":    100,
    "JPY_USDT":    100,
    "SPX_USDT":    100,
    "NAS100_USDT": 100,
    "US30_USDT":    50,
    "AAPL_USDT":   100,
    "MSFT_USDT":   100,
    "NVDA_USDT":   100,
    # ── v2.5 new pairs ────────────────────────────────────────────────────────
    "ADA_USDT":    300,
    "AVAX_USDT":   200,
    "BNB_USDT":    200,
    "LINK_USDT":   300,
    "TON_USDT":    200,
    "TRX_USDT":    200,
    "DOT_USDT":    300,
    "LTC_USDT":    200,
}

# Confidence threshold to allow stacking extra longs (score out of 5)
STACK_LONG_THRESH = 4.5

# Some MEXC futures contracts have a different API symbol than the display name.
# e.g. SPCX is listed as SPCXSTOCK_USDT in the futures API, TESLA as TESLA_USDT etc.
# Keys are the bot's internal symbol; values are what to send to MEXC API calls.
MEXC_API_SYMBOL = {
    # Stock and index perpetuals — API contract symbols verified from MEXC UI URLs:
    # /futures/TESLA_USDT  → contract symbol TESLA_USDT
    # /futures/NVIDIA_USDT → contract symbol NVIDIA_USDT  (NOT NVDA_USDT)
    # AAPL, MSFT, SPCX use STOCK suffix as before
    "AAPL_USDT":    "AAPLSTOCK_USDT",
    "MSFT_USDT":    "MSFTSTOCK_USDT",
    "NVDA_USDT":    "NVIDIA_USDT",     # MEXC contract is NVIDIA_USDT not NVDA_USDT
    "TESLA_USDT":   "TESLA_USDT",      # confirmed from MEXC UI URL
    "SPCX_USDT":    "SPCXSTOCK_USDT",
    "SPX_USDT":     "SPX_USDT",
    "NAS100_USDT":  "NAS100_USDT",
    "US30_USDT":    "US30_USDT",
    # TON: MEXC futures API still uses TONCOIN_USDT (legacy ticker kept after 2022 rebrand)
    # Spot trades as TONUSDT. Futures ticker/klines must use TONCOIN_USDT.
    "TON_USDT":     "TONCOIN_USDT",
}

# MEXC perpetual futures trade 24/7 — no market-hours restriction needed.
# This set is kept only as a label hint (★ in logs) but never blocks scanning.
MARKET_HOURS_PAIRS: set = set()

def api_sym(symbol: str) -> str:
    """Return the MEXC API symbol for a given internal bot symbol."""
    return MEXC_API_SYMBOL.get(symbol, symbol)

# Reverse map: MEXC WS/API symbol → bot internal symbol
WS_SYM_TO_BOT = {v: k for k, v in MEXC_API_SYMBOL.items()}

# Colour → Tk text-tag lookup shared by _log/_log_event — hoisted out of those
# hot per-message methods so the dict isn't rebuilt on every log call.
_LOG_TAG_MAP = {GREEN: "g", RED: "r", BLUE: "b", AMBER: "a",
                PURPLE: "p", CYAN: "c", TEAL: "t", DIM: "dim", MUTED: "mu"}

# ══════════════════════════════════════════════════════════════════════════════
#  v2.8-TUNED CONFIG — all tuning knobs in one place
# ══════════════════════════════════════════════════════════════════════════════
# Entry-selectivity (the v2.8 confluence bonus / trigger gate / conviction gap)
# is exposed as a UI toggle ("Selective entry" checkbox). This is its DEFAULT
# state. OFF = original v2.7.5 entry behaviour (more trades, less filtering).
# Defaulted OFF: live testing showed the bot was already drought-prone (HOLD
# streaks of 150+ cycles) — extra entry filters would only choke trade flow
# further without addressing the actual symptom (rare TP hits / frequent SL).
# Flip ON only if the lowered threshold floor causes too much chop to come in.
TUNED_SELECTIVE_ENTRY_DEFAULT = False

# Conviction gap: the winning side must out-score the other by at least this
# many points to qualify. Softened from the first-cut 0.8 so it trims genuine
# chop without choking trade flow. Only applied when selective entry is ON.
TUNED_CONVICTION_GAP = 0.6

# ── Exit geometry (the real fix for "rarely hits TP, mostly SL") ──────────────
# Closer TP: pin TP to a reachable multiple of net risk instead of the old wide
# ~2.6-3x table. ~1.6:1 net R/R is far more likely to actually be reached by a
# scalper while still clearing fees with margin to spare.
TUNED_RR_TARGET = 1.6

# Wider SL: require SL to sit at least this many ATRs from entry so normal wick
# noise can't stop you out prematurely (was 1.5x).
TUNED_ATR_SL_MULT = 2.0

# Partial take-profit + breakeven: bank a chunk of the position partway to TP
# and move the stop to breakeven, so a trade that moves your way locks in real
# profit instead of round-tripping back to the stop.
TUNED_PARTIAL_TP_ENABLE   = True
TUNED_PARTIAL_TP_PROGRESS = 0.50   # fire at 50% of the way to TP
TUNED_PARTIAL_TP_FRACTION = 0.50   # close 50% of the position

# ── THRESHOLD TEST ────────────────────────────────────────────────────────────
# The adaptive engine's lower clamp was hard-coded to max(4.0, base-1.5). With
# base_threshold 4.5 that pins the floor at 4.0, yet live logs showed the best
# candidates topping out at 3.0-3.5 — so even after a 150-cycle HOLD streak the
# drought/streak relaxation could never lower the bar enough to fire. This knob
# replaces the hard 4.0 with a configurable floor so the relaxation can actually
# reach reachable scores. Lowered to 3.0 for the test; raise back toward 4.0 if
# this proves to let too much chop through.
TUNED_THRESHOLD_FLOOR = 3.0

FM  = ("Consolas", 10)
FMS = ("Consolas", 9)
FMB = ("Consolas", 10, "bold")
FUI = ("Segoe UI", 10)

# ══════════════════════════════════════════════════════════════════════════════
#  DATA
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Position:
    id:          str
    symbol:      str
    direction:   str        # LONG / SHORT
    entry_price: float
    margin:      float
    leverage:    int
    size_usdt:   float
    stop_loss:   float
    take_profit: float
    liq_price:   float
    opened_at:   str
    hedge_of:        str = ""   # id of parent if this is a hedge leg
    order_id:        str = ""
    open_fee_type:   str = "taker"  # "maker" if limit-filled, "taker" if market order
    exchange_pos_id: str = ""       # MEXC positionId — required for stoporder/place
    exchange_hold_vol: float = 0.0  # MEXC holdVol (actual contract count)

@dataclass
class BotState:
    balance:      float = 1000.0
    total_pnl:    float = 0.0
    wins:         int   = 0
    losses:       int   = 0
    liqs:         int   = 0
    trades:       list  = field(default_factory=list)
    positions:    dict  = field(default_factory=dict)   # id -> Position
    pair_wins:    dict  = field(default_factory=dict)   # #PAIR-LOG symbol -> int win count
    pair_losses:  dict  = field(default_factory=dict)   # #PAIR-LOG symbol -> int loss count


class AdaptiveTriggerEngine:
    """ATR volatility + recent win-rate based dynamic signal threshold."""
    def __init__(self, base_threshold=4.5, window=20):
        self.base_threshold = base_threshold
        self.window = window
        self.recent_trades = deque(maxlen=50)   # 1=win, 0=loss — O(1) append/pop
        self._atr_history = {}    # pair -> deque of atr_pct values
        self.hold_streak  = 0     # consecutive HOLD cycles across all pairs
        self.last_trade_opened_at = time.time()  # epoch; updated on every trade open
        self._lock = threading.Lock()

    def update_atr(self, pair, atr_pct):
        with self._lock:
            h = self._atr_history.setdefault(pair, deque(maxlen=50))
            h.append(atr_pct)

    def reset_session(self):
        """Clear session trade/streak data but NOT ATR history.
        ATR history is preserved across restarts (up to 4 h) via the cache file
        so the threshold warmup period is skipped after a quick restart.
        Call restore_atr_from_cache() separately to reload warm ATR data.
        """
        with self._lock:
            self.recent_trades.clear()
            # _atr_history intentionally NOT cleared here — preserved across restarts
            self.hold_streak = 0
            self.last_trade_opened_at = time.time()

    def save_atr_cache(self, path: str) -> None:
        """Persist ATR history to disk so it survives a bot restart.

        Format: { "saved_at": <epoch float>,
                  "pairs": { "<symbol>": [atr_pct, ...], ... } }
        Uses _atomic_write so a crash mid-save never corrupts the file.
        """
        with self._lock:
            snapshot = {k: list(v) for k, v in self._atr_history.items()}
        payload = {
            "saved_at": time.time(),
            "pairs":    snapshot,
        }
        try:
            _atomic_write(path, json.dumps(payload, indent=2))
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)

    def restore_atr_from_cache(self, path: str, max_age_hours: float = 4.0) -> int:
        """Load ATR history from the cache file, discarding stale data.

        Entries older than max_age_hours are silently ignored so a file left
        over from yesterday's session does not poison today's threshold.

        Returns the number of pairs restored (0 = cache absent / stale / corrupt).
        """
        if not os.path.exists(path):
            return 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            age_secs = time.time() - float(payload.get("saved_at", 0))
            if age_secs > max_age_hours * 3600:
                _file_logger.info(
                    "ATR cache too old (%.1f h > %.1f h limit) — discarding",
                    age_secs / 3600, max_age_hours)
                return 0
            pairs_data = payload.get("pairs", {})
            if not isinstance(pairs_data, dict):
                return 0
            restored = 0
            with self._lock:
                for sym, values in pairs_data.items():
                    if not isinstance(values, list) or not values:
                        continue
                    d = self._atr_history.setdefault(sym, deque(maxlen=50))
                    for v in values:
                        try:
                            d.append(float(v))
                        except (TypeError, ValueError):
                            continue
                    restored += 1
            _file_logger.info(
                "ATR cache restored: %d pair(s), age %.1f min",
                restored, age_secs / 60)
            return restored
        except Exception as _exc:
            _file_logger.warning("ATR cache load failed: %s", _exc)
            return 0

    def log_trade(self, is_win):
        with self._lock:
            self.recent_trades.append(1 if is_win else 0)
            self.hold_streak = 0
            self.last_trade_opened_at = time.time()

    def get_threshold(self, pair, current_atr_pct):
        with self._lock:
            thr = self.base_threshold
            h = list(self._atr_history.get(pair, []))
            recent = list(self.recent_trades)
            hold_streak = self.hold_streak

        # ATR volatility adjustment — only after enough history
        if len(h) >= self.window:
            mean_atr = sum(h[-self.window:]) / self.window
            if current_atr_pct < mean_atr * 0.6:
                thr += 0.5
            elif current_atr_pct > mean_atr * 1.5:
                thr -= 0.5

        # Win-rate adjustment — requires at least 20 session trades to avoid
        # reacting to a small unlucky sample early in the session
        if len(recent) >= 20:
            wr = sum(recent[-20:]) / 20
            if wr < 0.35:
                thr = max(thr, 6.5)
            elif wr > 0.60:
                thr = max(self.base_threshold - 0.5, thr - 0.5)  # reward good runs

        if hold_streak > 30:
            relax = min(1.5, (hold_streak // 30) * 0.5)
            thr -= relax

        # Trade drought easing — if no trade has opened for an extended period,
        # gently ease the threshold to avoid the bot freezing during slow markets.
        # Steps in at 2 h (−0.3), 4 h (−0.6), 6 h (−0.9); capped at −0.9 total.
        # Resets automatically the moment a trade opens (log_trade resets the timer).
        with self._lock:
            drought_secs = time.time() - self.last_trade_opened_at
        drought_hrs = drought_secs / 3600
        if drought_hrs >= 2:
            drought_relax = min(0.9, ((int(drought_hrs) // 2) * 0.3))
            thr -= drought_relax

        lo = max(TUNED_THRESHOLD_FLOOR, self.base_threshold - 1.5)
        hi = self.base_threshold + 2.0
        return max(lo, min(hi, round(thr, 1)))

# ══════════════════════════════════════════════════════════════════════════════
#  MEXC API  (Futures Contract + Spot market data + WebSocket)
# ══════════════════════════════════════════════════════════════════════════════
MEXC_BASE       = "https://contract.mexc.com"    # Futures Contract REST API (signed)
MEXC_MARKET     = "https://contract.mexc.com"    # Futures market data (klines, ticker)
MEXC_WS_URL     = "wss://contract.mexc.com/edge" # Futures WebSocket (confirmed in MEXC WS docs)

# ── Rate limiter (token bucket) ───────────────────────────────────────────────
class _RateLimiter:
    """Simple token-bucket rate limiter for REST API calls."""
    def __init__(self, rate=18, burst=20):
        self._rate = rate       # tokens per second
        self._burst = burst     # max tokens
        self._tokens = burst
        self._last = time.time()
        self._lock = threading.Lock()

    def acquire(self):
        # FIX P0-#1: loop until a token is granted; original returned after
        # a single sleep without re-checking, so under contention the limit
        # was effectively unenforced (-> 429 storms).
        while True:
            with self._lock:
                now = time.time()
                elapsed = now - self._last
                self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
                self._last = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                # Compute exact wait while still holding the lock.
                needed = 1 - self._tokens
                wait = needed / self._rate
            time.sleep(wait)

_rate_limiter = _RateLimiter(rate=18, burst=10)


@retry_on_error(max_retries=3, backoff_base=0.5,
               retryable_errors=(TimeoutError, ConnectionError, OSError))
def mexc_public(path, params=None, timeout=10):
    """MEXC public REST endpoint — market data via api.mexc.com (no auth).
    
    Decorated with @retry_on_error (fix #8) — retries on transient network
    errors. The inner for-loop retry is kept as a secondary defence for
    HTTP-level 5xx / 429 responses which the decorator does not see.
    """
    if params is None:
        params = {}
    url = MEXC_MARKET + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Pacbot/1.5"})

    last_exc = None
    for attempt in range(3):
        _rate_limiter.acquire()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            break
        except urllib.error.HTTPError as e:
            # 4xx/5xx — read body for diagnostics; only retry on 5xx / 429
            try:
                raw = e.read()
            except Exception:
                raw = b""
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(0.5 * (2 ** attempt))
                last_exc = e
                continue
            try:
                return json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                raise
        except (urllib.error.URLError, IncompleteRead, TimeoutError) as e:
            last_exc = e
            if attempt < 2:
                time.sleep(0.5 * (2 ** attempt))
                continue
            raise
    else:
        if last_exc:
            raise last_exc

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return json.loads(raw.decode("latin-1"))


def mexc_private(method, path, params, key, secret, dry, timeout=12):
    """
    MEXC Futures (Contract) SIGNED endpoint.
    Signature = HMAC-SHA256(secret, apiKey + timestamp + body)
    Headers: ApiKey, Request-Time, Signature, Content-Type
    Base: https://contract.mexc.com
    """
    if dry:
        return {"success": True, "data": f"DRY-{int(time.time())}"}

    # Auto-remap internal bot symbols to MEXC API symbols (e.g. SPCX_USDT → SPCXSTOCK_USDT)
    if isinstance(params, dict) and "symbol" in params:
        params = dict(params)
        params["symbol"] = api_sym(params["symbol"])
    elif isinstance(params, list):
        params = [
            dict(p, symbol=api_sym(p["symbol"])) if isinstance(p, dict) and "symbol" in p else p
            for p in params
        ]

    ts   = str(int(time.time() * 1000))
    method_upper = method.upper()

    # MEXC Futures signing rules (from official docs):
    #   POST → sign(apiKey + timestamp + jsonBody), send params as JSON body
    #   GET  → sign(apiKey + timestamp + queryString), send params as URL query string
    #          queryString = dict-sorted key=value pairs joined with &
    if method_upper == "GET":
        if params:
            qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}"
                          for k, v in sorted(params.items()))
        else:
            qs = ""
        sign_str = key + ts + qs
        body = ""
        url = MEXC_BASE + path + ("?" + qs if qs else "")
    else:
        body = json.dumps(params, separators=(",", ":")) if params else ""
        sign_str = key + ts + body
        url = MEXC_BASE + path

    sig = hmac.new(
        secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "ApiKey": key,
        "Request-Time": ts,
        "Signature": sig,
        "Content-Type": "application/json",
        "User-Agent": "Pacbot/1.5",
    }

    req = urllib.request.Request(
        url,
        data=body.encode("utf-8") if body else None,
        headers=headers,
        method=method_upper,
    )

    last_exc = None
    raw = b""
    for attempt in range(3):
        _rate_limiter.acquire()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            break
        except urllib.error.HTTPError as e:
            try:
                raw = e.read()
            except Exception:
                raw = b""
            # Surface MEXC error payload to caller instead of raising
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                try:
                    _file_logger.warning("mexc_private %s %s -> HTTP %s, retrying", method, path, e.code)
                except Exception as _exc:
                    _file_logger.debug("suppressed error: %s", _exc)
                time.sleep(0.5 * (2 ** attempt))
                last_exc = e
                continue
            try:
                return json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                return {"success": False, "code": e.code,
                        "msg": raw.decode("utf-8", errors="replace")[:300]}
        except (urllib.error.URLError, IncompleteRead, TimeoutError) as e:
            last_exc = e
            if attempt < 2:
                time.sleep(0.5 * (2 ** attempt))
                continue
            return {"success": False, "code": -1, "msg": f"network: {e}"}
    else:
        if last_exc:
            return {"success": False, "code": -1, "msg": str(last_exc)}

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return json.loads(raw.decode("latin-1"))


# ══════════════════════════════════════════════════════════════════════════════
#  WebSocket Manager — Live price & kline feeds
# ══════════════════════════════════════════════════════════════════════════════
class MexcWebSocket:
    """
    Manages a persistent WebSocket connection to MEXC Futures for live market data.

    Protocol (confirmed from MEXC docs, updated 2025-11-25 + 2026-01-19):
      URL:       wss://contract.mexc.com/edge
      Format:    JSON text (responses may be gzip-compressed)
      Ping:      {"method":"ping"}  every 15s — server closes after 60s of silence
      Kline sub: {"method":"sub.kline","param":{"symbol":"BTC_USDT","interval":"Min5"}}
      Ticker sub:{"method":"sub.ticker","param":{"symbol":"BTC_USDT"}}
      Kline push channel:  "push.kline"  → data.symbol, data.data.{o,c,h,l,v,t}
      Ticker push channel: "push.ticker" → data.{symbol,lastPrice,fairPrice,fundingRate}
    """

    HEALTH_INTERVAL = 5    # seconds between health checks
    STALE_TIMEOUT   = 30   # seconds without data → force reconnect

    def __init__(self, pairs, interval="Min5", on_price=None, on_kline=None, on_log=None):
        self._pairs    = list(pairs)   # keep original BTC_USDT format
        self._interval = interval
        self._on_price = on_price
        self._on_kline = on_kline
        self._on_log   = on_log
        self._ws       = None
        self._running  = False
        self._lock     = threading.Lock()
        self._prices   = {}   # pair -> float
        self._klines   = {}   # pair -> list of kline dicts
        self._last_data     = time.time()
        self._reconnect_count = 0
        self._max_reconnects  = 100
        self._conn_thread     = None
        self._health_thread   = None
        self._ping_thread     = None
        self._bootstrap_done  = False

    def start(self):
        if not WS_AVAILABLE:
            self._log("websocket-client not installed — falling back to HTTP polling", AMBER)
            return False
        self._running = True
        # Bootstrap kline history from REST first
        threading.Thread(target=self._bootstrap_klines, daemon=True).start()
        # Start connection thread
        self._conn_thread = threading.Thread(target=self._run_forever, daemon=True)
        self._conn_thread.start()
        # Start health monitor
        self._health_thread = threading.Thread(target=self._health_monitor, daemon=True)
        self._health_thread.start()
        return True

    def stop(self):
        self._running = False
        try:
            if self._ws:
                self._ws.close()
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)
        self._ws = None

    def _restart_connection(self):
        """FIX P0-#5: stop existing connection AND join the old thread
        before spawning a new one. Without the join the old run_forever
        was still alive when the new one started, producing duplicate
        subscriptions and double price callbacks."""
        old_thread = self._conn_thread
        self.stop()
        if old_thread and old_thread.is_alive():
            old_thread.join(timeout=5.0)
        self._running = True
        self._conn_thread = threading.Thread(target=self._run_forever, daemon=True)
        self._conn_thread.start()

    def update_pairs(self, pairs):
        self._pairs = list(pairs)
        if self._running:
            self._restart_connection()

    def update_interval(self, interval):
        self._interval = interval
        if self._running:
            self._restart_connection()

    def get_price(self, pair_key):
        return self._prices.get(pair_key)

    def get_klines(self, pair_key):
        return self._klines.get(pair_key, [])

    @property
    def connected(self):
        return self._running and self._ws is not None

    def _log(self, msg, color=None):
        _file_logger.info(msg)
        if self._on_log:
            self._on_log(f"[WS] {msg}", color)

    # ── REST bootstrap ────────────────────────────────────────────────────────
    def _bootstrap_klines(self):
        for pair in list(self._pairs):
            if not self._running:
                break
            try:
                klines = get_klines(pair, self._interval, limit=200)
                if klines:
                    self._klines[pair] = klines
                    last_close = klines[-1].get("close", 0)
                    if last_close > 0:
                        self._prices[pair] = last_close
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)
            time.sleep(0.05)
        self._bootstrap_done = True
        self._log(f"Kline bootstrap complete for {len(self._pairs)} pairs", GREEN)

    # ── Health monitor ────────────────────────────────────────────────────────
    def _health_monitor(self):
        while self._running:
            time.sleep(self.HEALTH_INTERVAL)
            if not self._running:
                break
            elapsed = time.time() - self._last_data
            if elapsed > self.STALE_TIMEOUT:
                self._log(f"No data in {int(elapsed)}s — forcing reconnect", AMBER)
                self._reconnect_count += 1
                if self._reconnect_count >= self._max_reconnects:
                    self._log("Max reconnects exceeded — WS disabled", RED)
                    self._running = False
                    break
                try:
                    if self._ws:
                        self._ws.close()
                except Exception as _exc:
                    _file_logger.debug("suppressed error: %s", _exc)

    # ── Connection loop ───────────────────────────────────────────────────────
    def _run_forever(self):
        while self._running:
            try:
                self._connect_once()
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)
            if self._running:
                time.sleep(3)

    def _connect_once(self):
        import websocket as _wslib
        ws = _wslib.WebSocketApp(
            MEXC_WS_URL,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._ws = ws
        ws.run_forever(ping_interval=0, reconnect=0)  # we handle ping manually
        self._ws = None

    # ── WS event handlers ─────────────────────────────────────────────────────
    def _on_open(self, ws):
        self._reconnect_count = 0
        self._last_data = time.time()
        self._log(f"WS connected ({len(self._pairs)} pairs) [{MEXC_WS_URL}]", GREEN)
        # Subscribe to ticker + kline for each pair
        for pair in self._pairs:
            try:
                ws_pair = api_sym(pair)
                ws.send(json.dumps({"method": "sub.ticker",
                                    "param":  {"symbol": ws_pair}}))
                ws.send(json.dumps({"method": "sub.kline",
                                    "param":  {"symbol": ws_pair,
                                               "interval": self._interval}}))
            except Exception as e:
                self._log(f"WS subscription failed for {pair} ({ws_pair}): {e}", AMBER)
        # Start ping thread
        threading.Thread(target=self._ping_loop, args=(ws,), daemon=True).start()

    def _ping_loop(self, ws):
        """Send ping every 15s to keep connection alive (server closes after 60s).

        FIX P0-#4: do NOT touch self._last_data here. Outbound pings always
        succeed locally even when the market-data feed is dead, which masked
        stale connections. Only inbound frames in _on_message update activity.
        """
        while self._running and self._ws is ws:
            try:
                ws.send(json.dumps({"method": "ping"}))
            except Exception:
                break
            time.sleep(15)

    def _on_message(self, ws, message):
        try:
            # Decompress gzip if needed (MEXC compresses by default since Aug 2025)
            if isinstance(message, (bytes, bytearray)):
                import gzip as _gzip
                try:
                    message = _gzip.decompress(message).decode("utf-8")
                except Exception:
                    message = message.decode("utf-8", errors="replace")

            data = json.loads(message)
            if not isinstance(data, dict):
                return

            channel = data.get("channel", "")
            self._last_data = time.time()

            # ── Pong response ─────────────────────────────────────────────
            if channel == "pong":
                return

            # ── Subscription ack ──────────────────────────────────────────
            if channel == "rs.sub.kline" or channel == "rs.sub.ticker":
                return

            # ── Ticker push — real-time last price ────────────────────────
            if channel == "push.ticker":
                d = data.get("data", {})
                pair = d.get("symbol", data.get("symbol", ""))
                pair = WS_SYM_TO_BOT.get(pair, pair)  # remap API sym → bot sym
                px = float(d.get("lastPrice", d.get("fairPrice", 0)) or 0)
                fn = float(d.get("fundingRate", 0) or 0)
                if pair and px > 0:
                    self._prices[pair] = px
                    if self._on_price:
                        self._on_price(pair, px)
                return

            # ── Kline push ────────────────────────────────────────────────
            if channel == "push.kline":
                d    = data.get("data", {})
                pair = d.get("symbol", data.get("symbol", ""))
                pair = WS_SYM_TO_BOT.get(pair, pair)  # remap API sym → bot sym
                kd   = d.get("data", d)   # inner data object
                try:
                    bar = {
                        "open":   float(kd.get("o", kd.get("open",  0))),
                        "close":  float(kd.get("c", kd.get("close", 0))),
                        "high":   float(kd.get("h", kd.get("high",  0))),
                        "low":    float(kd.get("l", kd.get("low",   0))),
                        "volume": float(kd.get("v", kd.get("vol",   kd.get("volume", 0)))),
                        "time":   int(kd.get("t",   kd.get("time",  0))),
                    }
                except (TypeError, ValueError):
                    return
                if bar["close"] > 0 and pair:
                    klines   = self._klines.get(pair, [])
                    bar_time = bar["time"]
                    if klines and klines[-1].get("time") == bar_time and bar_time > 0:
                        klines[-1] = bar   # update current candle in-place
                    else:
                        klines.append(bar)
                        if len(klines) > 250:
                            klines = klines[-200:]
                    self._klines[pair]  = klines
                    self._prices[pair]  = bar["close"]
                    if self._on_price:
                        self._on_price(pair, bar["close"])
                    if self._on_kline:
                        self._on_kline(pair, bar)
                return

        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)

    def _on_error(self, ws, error):
        err_str = str(error) if error else "unknown"
        if "Connection" not in err_str and "timed out" not in err_str.lower():
            self._log(f"WS error: {err_str[:80]}", RED)

    def _on_close(self, ws, close_status_code, close_msg):
        self._log(f"WS closed (code={close_status_code})", AMBER)
        self._ws = None

def get_live_account(key, secret):
    """
    Fetch MEXC futures account balance.
    Confirmed endpoint: GET /api/v1/private/account/assets
    Response fields (from live docs):
      currency, equity, availableBalance, unrealized, positionMargin, cashBalance
    """
    try:
        r = mexc_private("GET", "/api/v1/private/account/assets", {}, key, secret, False)
        if r.get("success"):
            data = r.get("data", [])
            # Response is a list of currency assets
            if isinstance(data, list):
                usdt = next((a for a in data
                             if str(a.get("currency", "")).upper() == "USDT"), None)
                if usdt:
                    return {
                        "equity":     float(usdt.get("equity", 0)),
                        "available":  float(usdt.get("availableBalance",
                                            usdt.get("availableOpen", 0))),
                        "unrealised": float(usdt.get("unrealized", 0)),
                        "realised":   0.0,   # not returned by this endpoint
                    }
            # Fallback: dict shape
            elif isinstance(data, dict):
                return {
                    "equity":     float(data.get("equity", 0)),
                    "available":  float(data.get("availableBalance",
                                        data.get("availableOpen", 0))),
                    "unrealised": float(data.get("unrealized", 0)),
                    "realised":   0.0,
                }
        msg = r.get("message", r.get("msg", str(r)))
        raise RuntimeError(f"/api/v1/private/account/assets: {msg}")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Account assets fetch failed: {str(e)[:80]}")


def fetch_open_positions(key, secret):
    """
    Fetch all open positions from MEXC futures.
    Field names verified against live MEXC API docs (June 2025):
      GET /api/v1/private/position/open_positions
    Key response fields:
      holdVol        — position size (contracts)
      positionType   — 1=long, 2=short
      openAvgPrice   — average open price (use openAvgPriceFullyScale for precision)
      im             — initial margin (isolated)
      liquidatePrice — liquidation price (isolated)
      realised       — realised PnL (NOT unrealised; MEXC doesn't return unrealised directly)
      holdFee        — accumulated funding fee (positive=received, negative=paid)
      createTime     — position open timestamp (ms)
      leverage       — leverage
    """
    positions = []
    errors = []
    try:
        r = mexc_private("GET", "/api/v1/private/position/open_positions", {}, key, secret, False)
        if not r.get("success"):
            msg = r.get("message", r.get("msg", str(r)))
            raise RuntimeError(f"/api/v1/private/position/open_positions: {msg}")
        data = r.get("data", [])
        if isinstance(data, dict):
            data = data.get("list", data.get("data", []))
        if not isinstance(data, list):
            return positions
        for p in data:
            # holdVol = position size; skip closed/empty positions
            vol = float(p.get("holdVol", 0))
            if vol <= 0:
                continue
            # state: 1=holding, 2=system-held, 3=closed — skip non-holding
            if int(p.get("state", 1)) == 3:
                continue
            # MEXC bug: recently-closed positions linger in /open_positions for
            # a few minutes with closeVol == holdVol. Skip them — they are gone.
            close_vol = float(p.get("closeVol", 0))
            if close_vol >= vol:
                continue
            # positionType: 1=long, 2=short (confirmed in docs)
            pos_type  = int(p.get("positionType", 1))
            direction = "LONG" if pos_type == 1 else "SHORT"
            symbol    = WS_SYM_TO_BOT.get(p.get("symbol", ""), p.get("symbol", ""))
            # Use full-precision price string if available, else numeric field
            entry_str = p.get("openAvgPriceFullyScale") or p.get("openAvgPrice", 0)
            entry     = float(entry_str) if entry_str else 0.0
            lev       = int(p.get("leverage", 10))
            # im = initial margin (isolated mode). oim = original initial margin.
            margin    = float(p.get("im", p.get("oim", 0)))
            # liquidatePrice is the confirmed field name in docs
            liq       = float(p.get("liquidatePrice", 0))
            # holdFee = funding fees (not unrealised PnL — MEXC doesn't expose it directly)
            hold_fee  = float(p.get("holdFee", 0))
            open_time = p.get("createTime", p.get("updateTime", ""))
            positions.append({
                "symbol":        symbol,
                "direction":     direction,
                "vol":           vol,
                "entry_price":   entry,
                "leverage":      lev,
                "margin":        margin,
                "unrealised_pnl": hold_fee,   # best proxy available from this endpoint
                "liq_price":     liq,
                "open_time":     str(open_time),
                "size_usdt":     margin * lev if margin > 0 else vol * entry,
                "position_id":   p.get("positionId", ""),   # needed for stoporder/place
                "hold_vol":      float(p.get("holdVol", 0)),   # exact contract count
                "frozen_vol":    float(p.get("frozenVol", 0)), # already frozen by plan orders
                "close_vol":     close_vol,                    # contracts already being closed
            })
    except RuntimeError:
        raise
    except Exception as e:
        errors.append(str(e)[:120])
        raise RuntimeError("; ".join(errors))
    return positions


def fetch_fee_rate(key, secret):
    """Fetch actual maker/taker fee rates from MEXC futures. Returns (maker, taker) as decimals.

    IMPORTANT: The tiered_fee_rate/v2 endpoint returns web/app rates which reflect
    promotional 0-fee events and discounts. Per MEXC's announcement (effective May 1 2026),
    API trades are charged at a SEPARATE fixed rate that overrides all web/app rates,
    promotions, and MX discounts:
        API maker: 0.04% (0.0004)
        API taker: 0.06% (0.0006)
    We still call the endpoint to detect if the account has a negotiated institutional
    rate ABOVE these minimums (e.g. high-volume tiers), but we always clamp to the
    API floor so promotional web rates never understate our real cost.
    """
    # API fee floors — never charge less than these regardless of what the endpoint returns
    API_MAKER_FLOOR = 0.0004   # 0.04% — MEXC API maker fee from May 1 2026
    API_TAKER_FLOOR = 0.0006   # 0.06% — MEXC API taker fee from May 1 2026

    try:
        r = mexc_private("GET", "/api/v1/private/account/tiered_fee_rate/v2", {}, key, secret, False)
        if r.get("success") and r.get("data"):
            d = r["data"]
            fee_mode = d.get("feeRateMode", "NORMAL")
            if fee_mode == "TIERED":
                tiers    = d.get("tieredFeeRates") or []
                deal_amt = float(d.get("tieredDealAmount", 0))
                applicable = None
                for t in tiers:
                    lo = float(t.get("minTieredDealAmount", 0))
                    hi = t.get("maxTieredDealAmount")
                    if deal_amt >= lo and (hi is None or deal_amt <= float(hi)):
                        applicable = t
                        break
                if applicable is None and tiers:
                    applicable = tiers[0]
                if applicable:
                    maker = float(applicable.get("realMakerFee",
                                  applicable.get("makerFeeRate", API_MAKER_FLOOR)))
                    taker = float(applicable.get("realTakerFee",
                                  applicable.get("takerFeeRate", API_TAKER_FLOOR)))
                    # Clamp: API floor always applies regardless of web promo rates
                    return max(maker, API_MAKER_FLOOR), max(taker, API_TAKER_FLOOR)
            # NORMAL / LEVERAGE mode
            maker = float(d.get("realMakerFee", d.get("originalMakerFee", API_MAKER_FLOOR)))
            taker = float(d.get("realTakerFee", d.get("originalTakerFee", API_TAKER_FLOOR)))
            return max(maker, API_MAKER_FLOOR), max(taker, API_TAKER_FLOOR)
    except Exception as _exc:
        _file_logger.debug("suppressed error: %s", _exc)
    return API_MAKER_FLOOR, API_TAKER_FLOOR


def validate_contract_specs(log_fn=None):
    """Fetch live contract specs from MEXC and auto-patch the global config dicts.

    Calls /api/v1/contract/detail for every active pair and compares against:
      PAIR_CONTRACT_SIZE, PAIR_PRICE_PRECISION, PAIR_MAX_LEV
    Any mismatch is logged and patched in-place so the running session is always
    using MEXC's authoritative values. Runs once at bot startup in a background
    thread — no auth required (public endpoint).
    """
    def _log(msg, col=None):
        if log_fn:
            try:
                log_fn(msg, col)
            except Exception:
                pass

    CONTRACT_URL = "https://contract.mexc.com/api/v1/contract/detail"
    # Internal symbol → API symbol mapping (same as MEXC_API_SYMBOL but we need it here)
    _sym_map = {k: v for k, v in MEXC_API_SYMBOL.items()}

    patched = []
    errors  = []

    for bot_sym in list(PAIR_CONTRACT_SIZE.keys()):
        api_sym_name = _sym_map.get(bot_sym, bot_sym)
        try:
            url = f"{CONTRACT_URL}?symbol={api_sym_name}"
            req = urllib.request.Request(url, headers={"User-Agent": "Pacbot/2.5"})
            with urllib.request.urlopen(req, timeout=8) as r:
                d = json.loads(r.read()).get("data", {})
            if not d:
                continue

            live_cs   = d.get("contractSize")
            live_ps   = d.get("priceScale")
            live_ml   = d.get("maxLeverage")

            changes = []

            if live_cs is not None:
                live_cs = float(live_cs)
                cur_cs  = PAIR_CONTRACT_SIZE.get(bot_sym)
                if cur_cs is not None and abs(live_cs - cur_cs) / max(live_cs, 1e-12) > 0.001:
                    PAIR_CONTRACT_SIZE[bot_sym] = live_cs
                    changes.append(f"contractSize {cur_cs}→{live_cs}")

            if live_ps is not None:
                live_ps = int(live_ps)
                cur_ps  = PAIR_PRICE_PRECISION.get(bot_sym)
                if cur_ps is not None and cur_ps != live_ps:
                    PAIR_PRICE_PRECISION[bot_sym] = live_ps
                    changes.append(f"priceScale {cur_ps}→{live_ps}")

            if live_ml is not None:
                live_ml = int(live_ml)
                cur_ml  = PAIR_MAX_LEV.get(bot_sym)
                if cur_ml is not None and cur_ml != live_ml:
                    PAIR_MAX_LEV[bot_sym] = live_ml
                    changes.append(f"maxLev {cur_ml}→{live_ml}")

            if changes:
                label = bot_sym.replace("_USDT", "")
                _log(f"⚙ Contract spec updated [{label}]: {', '.join(changes)}", AMBER)
                patched.append(bot_sym)

            time.sleep(0.06)   # ~16 pairs/sec — well within MEXC public rate limits

        except Exception as exc:
            errors.append(f"{bot_sym}: {exc}")

    display_col = GREEN if not errors else AMBER
    _log(
        f"✓ Contract specs validated — {len(patched)} patch(es) applied"
        + (f", {len(errors)} error(s)" if errors else ""),
        display_col,
    )
    for e in errors:
        _file_logger.debug("validate_contract_specs error: %s", e)


# Stock perpetuals (NVDA, TSLA, AAPL, MSFT, SPCX) have no spot equivalent on MEXC.
# Hoisted to module scope — get_ticker() runs once per pair per scan cycle and was
# rebuilding this set on every call.
_STOCK_PERPS = {"NVDA_USDT", "TESLA_USDT", "AAPL_USDT", "MSFT_USDT", "SPCX_USDT"}

def get_ticker(sym):
    """Fetch latest price — tries futures contract ticker first, then spot as fallback."""
    api_symbol = api_sym(sym)
    # Try futures contract ticker first (this is a futures bot)
    try:
        _rate_limiter.acquire()
        url = MEXC_BASE + "/api/v1/contract/ticker" + f"?symbol={api_symbol}"
        req = urllib.request.Request(url, headers={"User-Agent": "Pacbot/1.5"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("success") and data.get("data"):
            d = data["data"]
            if isinstance(d, list):
                d = d[0] if d else {}
            last_px = float(d.get("lastPrice", d.get("last", d.get("fairPrice", 0))))
            funding = float(d.get("fundingRate", 0))
            if last_px > 0:
                return {"last": last_px, "funding": funding}
    except Exception as _exc:
        _file_logger.debug("suppressed error: %s", _exc)
    # Identify stock perpetuals by their presence in MEXC_API_SYMBOL regardless of suffix format.
    is_stock_perp = sym in _STOCK_PERPS
    if not is_stock_perp:
        # Fallback to spot ticker — always built from the original bot symbol (sym),
        # NOT api_mapped, so TON_USDT → TONUSDT (not TONCOINUSDT).
        spot_sym = sym.replace("_USDT", "") + "USDT"
        try:
            r = mexc_public("/api/v3/ticker/price", {"symbol": spot_sym})
            if isinstance(r, dict) and "price" in r:
                return {"last": float(r["price"]), "funding": 0.0}
            elif isinstance(r, list):
                for item in r:
                    if item.get("symbol") == spot_sym:
                        return {"last": float(item["price"]), "funding": 0.0}
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)
    # Last resort: pull last close from futures klines (works for stock perpetuals)
    try:
        klines = get_klines(sym, "Min5", 3)
        if klines:
            last_close = float(klines[-1].get("close", 0))
            if last_close > 0:
                return {"last": last_close, "funding": 0.0}
    except Exception as _exc:
        _file_logger.debug("suppressed error: %s", _exc)
    raise RuntimeError(f"Ticker unavailable for {sym}")

# Hoisted to module scope — get_klines() runs many times per scan cycle (every
# pair, plus H1/H4 staggered fetches and dual-TF lookups) and was rebuilding
# these lookup tables from scratch on every single call.
_FUTURES_INTERVAL_MAP = {
    "Min1": "Min1", "Min5": "Min5", "Min15": "Min15", "Min30": "Min30",
    "Min60": "Min60", "Hour1": "Hour1", "Hour4": "Hour4", "Hour8": "Hour8",
    "Day1": "Day1", "Week1": "Week1", "Month1": "Month1",
}
_SPOT_INTERVAL_MAP = {
    "Min1": "1m", "Min5": "5m", "Min15": "15m", "Min30": "30m",
    "Min60": "60m", "Hour1": "60m", "Hour4": "4h", "Hour8": "8h",
    "Day1": "1d", "Week1": "1W", "Month1": "1M",
}

def get_klines(sym, tf="Min5", limit=60, timeout=12):
    """Fetch kline/candlestick data — tries futures contract klines first, spot as fallback."""
    # Try futures contract klines first (this is a futures bot)
    ft_interval = _FUTURES_INTERVAL_MAP.get(tf, "Min5")
    api_symbol = api_sym(sym)
    try:
        _rate_limiter.acquire()
        url = MEXC_BASE + f"/api/v1/contract/kline/{api_symbol}?interval={ft_interval}"
        req = urllib.request.Request(url, headers={"User-Agent": "Pacbot/1.5"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("success") and data.get("data"):
            out = []
            kdata = data["data"]
            # MEXC futures returns columnar format: {time:[...], open:[...], close:[...], ...}
            if isinstance(kdata, dict) and "close" in kdata and isinstance(kdata["close"], list):
                closes = kdata["close"]
                opens  = kdata.get("open", closes)
                highs  = kdata.get("high", closes)
                lows   = kdata.get("low", closes)
                vols   = kdata.get("vol", kdata.get("volume", [0]*len(closes)))
                times  = kdata.get("time", [0]*len(closes))
                for i in range(len(closes)):
                    try:
                        out.append({
                            "open":   float(opens[i]),
                            "high":   float(highs[i]),
                            "low":    float(lows[i]),
                            "close":  float(closes[i]),
                            "volume": float(vols[i]) if i < len(vols) else 0,
                            "time":   int(times[i]) if i < len(times) else 0,
                        })
                    except (ValueError, TypeError, IndexError):
                        continue
            elif isinstance(kdata, dict):
                kdata = kdata.get("data", kdata.get("list", []))
                if isinstance(kdata, list):
                    for bar in kdata:
                        if isinstance(bar, dict):
                            out.append({
                                "open":   float(bar.get("open", 0)),
                                "high":   float(bar.get("high", 0)),
                                "low":    float(bar.get("low", 0)),
                                "close":  float(bar.get("close", 0)),
                                "volume": float(bar.get("vol", bar.get("volume", 0))),
                                "time":   int(bar.get("time", 0)),
                            })
            elif isinstance(kdata, list):
                for bar in kdata:
                    if isinstance(bar, dict):
                        out.append({
                            "open":   float(bar.get("open", 0)),
                            "high":   float(bar.get("high", 0)),
                            "low":    float(bar.get("low", 0)),
                            "close":  float(bar.get("close", 0)),
                            "volume": float(bar.get("vol", bar.get("volume", 0))),
                            "time":   int(bar.get("time", 0)),
                        })
                    elif isinstance(bar, (list, tuple)) and len(bar) >= 5:
                        out.append({
                            "open":   float(bar[1]),
                            "high":   float(bar[3]),
                            "low":    float(bar[4]),
                            "close":  float(bar[2]),
                            "volume": float(bar[5]) if len(bar) > 5 else 0,
                        })
            if out:
                return out[-limit:]
    except Exception as _exc:
        _file_logger.debug("suppressed error: %s", _exc)
    # Fallback to spot klines — always built from the original bot symbol (sym),
    # NOT api_mapped, so TON_USDT → TONUSDT (not TONCOINUSDT).
    spot_sym = sym.replace("_USDT", "") + "USDT"
    api_interval = _SPOT_INTERVAL_MAP.get(tf, "5m")
    try:
        r = mexc_public("/api/v3/klines", {
            "symbol": spot_sym,
            "interval": api_interval,
            "limit": min(limit, 500),
        }, timeout=timeout)
        if isinstance(r, list) and len(r) > 0:
            out = []
            for bar in r:
                if isinstance(bar, (list, tuple)) and len(bar) >= 6:
                    out.append({
                        "open":   float(bar[1]),
                        "high":   float(bar[2]),
                        "low":    float(bar[3]),
                        "close":  float(bar[4]),
                        "volume": float(bar[5]),
                    })
            if out:
                return out[-limit:]
    except Exception as _exc:
        _file_logger.debug("suppressed error: %s", _exc)
    return []

# ══════════════════════════════════════════════════════════════════════════════
#  INDICATORS
# ══════════════════════════════════════════════════════════════════════════════
def ema(vals, p):
    if not vals:
        return []
    k = 2.0 / (p + 1)
    k1 = 1.0 - k
    r = [vals[0]]
    prev = vals[0]
    for v in vals[1:]:
        prev = v * k + prev * k1
        r.append(prev)
    return r

def rsi(closes, p=14):
    if len(closes) < p + 1: return 50.0
    d = [closes[i] - closes[i-1] for i in range(len(closes) - p, len(closes))]
    ag = sum(x for x in d if x > 0) / p
    al = sum(-x for x in d if x < 0) / p
    return 100.0 if al == 0 else round(100 - (100 / (1 + ag / al)), 2)

def rsi_series(closes, p=14):
    """Compute RSI for every bar in O(n) using Wilder smoothing — replaces the
    O(n²) loop [rsi(closes[:i+1]) for i in range(n)] used in chart drawing."""
    n = len(closes)
    if n < p + 1:
        return [50.0] * n
    result = [50.0] * p
    d = [closes[i] - closes[i-1] for i in range(1, n)]
    # Seed averages from first window
    ag = sum(x for x in d[:p] if x > 0) / p
    al = sum(-x for x in d[:p] if x < 0) / p
    result.append(100.0 if al == 0 else round(100 - (100 / (1 + ag / al)), 2))
    # Wilder smoothing for the rest
    k = 1.0 / p
    for i in range(p, len(d)):
        chg = d[i]
        ag = ag * (1 - k) + (chg if chg > 0 else 0.0) * k
        al = al * (1 - k) + (-chg if chg < 0 else 0.0) * k
        result.append(100.0 if al == 0 else round(100 - (100 / (1 + ag / al)), 2))
    return result

def macd_full(closes):
    if len(closes) < 26: return [], [], []
    e12 = ema(closes, 12); e26 = ema(closes, 26)
    ml  = [e12[i] - e26[i] for i in range(len(e26))]
    sig = ema(ml, 9)
    return ml, sig, [ml[i] - sig[i] for i in range(len(sig))]

def bollinger(closes, p=20, dev=2.0):
    """Returns (upper, middle, lower, %B) — %B: 0=lower band, 1=upper band."""
    if len(closes) < p: return None, None, None, 0.5
    sl = closes[-p:]
    mid = sum(sl) / p
    variance = sum((x - mid) ** 2 for x in sl) / p
    std = variance ** 0.5
    if std == 0: return mid, mid, mid, 0.5
    upper = mid + dev * std
    lower = mid - dev * std
    span = upper - lower
    pct_b = (closes[-1] - lower) / span
    return upper, mid, lower, round(pct_b, 4)

def stoch_rsi(closes, rsi_p=14, stoch_p=14):
    """Stochastic RSI — returns value 0-100. <20=oversold, >80=overbought."""
    if len(closes) < rsi_p + stoch_p: return 50.0
    # Only process the tail we need — avoids O(n) work on full 200-bar arrays
    need = rsi_p + stoch_p + 10
    tail = closes[-need:] if len(closes) > need else closes
    rsi_vals = rsi_series(tail, rsi_p)
    if len(rsi_vals) < stoch_p: return 50.0
    recent = rsi_vals[-stoch_p:]
    lo, hi = min(recent), max(recent)
    if hi == lo: return 50.0
    return round((rsi_vals[-1] - lo) / (hi - lo) * 100, 2)

def atr(candles, p=14):
    """Average True Range — measures volatility."""
    if len(candles) < p + 1: return 0
    trs = []
    prev_c = candles[0]["close"]
    for bar in candles[1:]:
        h = bar.get("high",  bar["close"])
        l = bar.get("low",   bar["close"])
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
        prev_c = bar["close"]
    if not trs: return 0
    return sum(trs[-p:]) / min(p, len(trs))

def obv(closes, volumes):
    """On-Balance Volume — cumulative volume pressure."""
    if len(closes) < 2: return 0, 0
    result = [0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:   result.append(result[-1] + volumes[i])
        elif closes[i] < closes[i-1]: result.append(result[-1] - volumes[i])
        else:                          result.append(result[-1])
    # OBV trend: rising = bullish, falling = bearish
    if len(result) < 5: return result[-1], 0
    obv_slope = result[-1] - result[-5]
    return result[-1], obv_slope

def compute_signals(candles, ticker, thresh, atr_min=0.06, rsi_bias=0,
                    selective_entry=True):
    # selective_entry: when True (default), the v2.8 entry-quality changes
    # (confluence bonus, trigger gate, conviction gap) are applied. When False,
    # scoring/direction selection behaves like the original v2.7.5 logic, which
    # takes more (but lower-quality) trades. Wired to the "Selective entry" UI
    # toggle so it can be A/B tested live.
    if len(candles) < 26:
        return None   # not enough candles for indicators
    cl = [c["close"]  for c in candles]
    vo = [c["volume"] for c in candles]

    # ── Existing indicators ───────────────────────────────────────────────────
    e9  = ema(cl, 9);  e21 = ema(cl, 21)
    # Compute RSI series once and use last value for single RSI
    rsi_vals = rsi_series(cl, 14)
    rv = rsi_vals[-1] if rsi_vals else 50.0
    macd_line, macd_sig, hist = macd_full(cl); mh = hist[-1] if hist else 0
    
    # Volume ratio — use median of last 5 closed candles as current volume.
    # Stripping just [-1] isn't enough: at a candle boundary the WS pushes a new
    # forming candle so [-2] becomes the just-opened bar with only its first tick.
    # Median of [-6:-1] is immune to both the forming candle and boundary spikes.
    # Volume ratio — work entirely on the original vo array, using explicit
    # absolute index ranges so the median window is never relative to a
    # previously-sliced sub-array (fixes double-slice offset bug).
    # [-7:-1] gives exactly 6 closed bars (excluding the forming candle at [-1]).
    # [-21:-1] gives exactly 20 closed bars for the rolling average baseline.
    closed_sample = vo[-7:-1] if len(vo) >= 7 else vo[:-1] if len(vo) > 1 else vo
    if len(closed_sample) >= 3:
        cur_vol = sorted(closed_sample)[len(closed_sample) // 2]  # median
    else:
        cur_vol = closed_sample[-1] if len(closed_sample) else 0
    closed_avg = vo[-21:-1] if len(vo) >= 21 else vo[:-1] if len(vo) > 1 else vo
    av  = sum(closed_avg) / len(closed_avg) if closed_avg else 1
    vr  = round(cur_vol / av, 2) if av > 0 and cur_vol > 0 else 1.0
    fn  = ticker.get("funding", 0)
    bull = e9[-1] > e21[-1]

    # EMA gap: how far apart EMA9 and EMA21 are as % of price
    # Tiny gap = flat/ranging market where EMA trend signal is unreliable
    ema_gap_pct = abs(e9[-1] - e21[-1]) / e21[-1] * 100 if e21[-1] > 0 else 0

    # ── New indicators (backtested best performers) ───────────────────────────
    bb_upper, bb_mid, bb_lower, pct_b = bollinger(cl, 20, 2.0)
    srsi  = stoch_rsi(cl, 14, 14)
    atr_v = atr(candles, 14)
    atr_pct = (atr_v / cl[-1] * 100) if cl[-1] > 0 else 0  # ATR as % of price
    # OBV — exclude the forming candle (vo[-1] is partial, distorts slope)
    _, obv_slope = obv(cl[:-1], vo[:-1]) if len(cl) > 1 else (0, 0)

    # ATR filter: avoid entering in extremely low-volatility (flat) markets
    # Low ATR = price not moving = more false signals.
    # atr_min is now per-pair (passed from scan loop via PAIR_ATR_MIN).
    atr_ok = atr_pct > atr_min

    # MACD momentum direction: is the histogram growing or shrinking?
    # Shrinking = fading momentum, not a good entry point
    # macd_building_short: True when histogram is getting more negative (selling pressure building)
    # macd_building_long:  True when histogram is getting more positive (buying pressure building)
    macd_building_short = len(hist) >= 3 and hist[-1] < hist[-2] and hist[-2] < hist[-3]
    macd_building_long  = len(hist) >= 3 and hist[-1] > hist[-2] and hist[-2] > hist[-3]

    # EMA gap strength bonus: wider gap = stronger trend conviction
    # 0.5 bonus when gap > 0.1%, full 1.0 bonus when gap > 0.25%
    ema_gap_bonus = 1.0 if ema_gap_pct > 0.25 else (0.5 if ema_gap_pct > 0.10 else 0)

    # ── Price action: higher lows (bullish) / lower highs (bearish) ──────────
    # Check last 3 candles for structural confirmation — avoids noise signals
    highs = [c.get("high", c["close"]) for c in candles[-4:]]
    lows  = [c.get("low",  c["close"]) for c in candles[-4:]]
    higher_lows  = len(lows)  >= 3 and lows[-1]  > lows[-2]  > lows[-3]
    lower_highs  = len(highs) >= 3 and highs[-1] < highs[-2] < highs[-3]

    # ── MACD zero-line cross bonus — histogram changing sign is strongest signal ─
    macd_cross_up   = len(hist) >= 2 and hist[-2] < 0 and hist[-1] > 0
    macd_cross_down = len(hist) >= 2 and hist[-2] > 0 and hist[-1] < 0

    # ── EMA crossover detection — EMA9 crossing EMA21 is an early trend signal ─
    # Three quality filters to avoid whipsaw false crosses:
    #   1. Gap > 0.05% after cross  — real breakout leaves a gap; choppy flips don't
    #   2. Price closes on correct side of EMA21 — confirms price committed to the move
    #   3. Volume above average (vr > 1.0)  — real crosses happen on meaningful volume
    _last_price = float(ticker.get("last", cl[-1]) or cl[-1])
    _cross_gap_ok  = ema_gap_pct > 0.05
    _vol_ok        = vr > 1.0
    _price_above   = _last_price > e21[-1]
    _price_below   = _last_price < e21[-1]
    ema_cross_up   = (len(e9) >= 2 and len(e21) >= 2
                      and e9[-2] <= e21[-2] and e9[-1] > e21[-1]
                      and _cross_gap_ok and _price_above and _vol_ok)
    ema_cross_down = (len(e9) >= 2 and len(e21) >= 2
                      and e9[-2] >= e21[-2] and e9[-1] < e21[-1]
                      and _cross_gap_ok and _price_below and _vol_ok)

    # ── Score LONG (max 9 points) ─────────────────────────────────────────────
    # ATR is now a gate (checked before entry), not a score point.
    ls = 0.0
    ls += 1.5 if ema_cross_up else (1.0 if bull else 0)        # EMA cross = early entry bonus
    ls += ema_gap_bonus if bull else 0                          # EMA gap strength
    # RSI: reward genuinely oversold only — thresholds shifted by rsi_bias for trending assets
    ls += 1.5 if rv < (30 + rsi_bias) else (1.0 if rv < (40 + rsi_bias) else 0)
    ls += 1.5 if macd_cross_up else (1.0 if (mh > 0 and macd_building_long) else (0.5 if mh > 0 else 0))  # MACD cross is strongest
    ls += 0.5 if vr > 1.5 else 0                                # Volume surge (raised from 1.3x)
    ls += 0.5 if fn < -0.01 else 0                              # Funding (shorts paying)
    ls += 1.0 if pct_b < 0.2 else (0.5 if pct_b < 0.4 else 0)  # Bollinger lower band
    ls += 1.0 if srsi < 20 else (0.5 if srsi < 40 else 0)      # Stoch RSI oversold
    ls += 1.0 if obv_slope > 0 else 0                           # OBV rising
    ls += 0.5 if higher_lows else 0                             # Price action: higher lows

    # ── TUNED: confluence stacking bonus (only when selective_entry is ON) ───
    # The bot was missing genuinely strong setups because their points were
    # spread thin across many indicators and rarely cleared the threshold.
    # When the *strongest* trigger families agree (a real cross/momentum signal
    # + an extreme oscillator reading + above-average volume), that is a much
    # higher-conviction setup than the same point total reached by stacking
    # several weak/neutral readings — reward it explicitly so good setups stand
    # out and clear the bar instead of hovering just under it.
    if selective_entry:
        ls_trigger   = ema_cross_up or macd_cross_up or rv < (30 + rsi_bias)
        ls_extreme   = srsi < 20 or pct_b < 0.2
        ls_confluence = 1.0 if (ls_trigger and ls_extreme and vr > 1.2) else 0.0
        ls += ls_confluence

        # ── TUNED: trigger-quality gate ──────────────────────────────────────
        # A score built entirely from soft/neutral contributions (trend bias,
        # mid-range RSI, small volume bumps, price-action notes) can limp across
        # the threshold without any real catalyst — these are exactly the "bad"
        # entries that get faded immediately. Require at least one bona-fide
        # trigger (a fresh cross, building/crossed MACD momentum, or a genuine
        # oversold extreme) before the LONG side is allowed to qualify at all.
        ls_has_trigger = (ema_cross_up or macd_cross_up or macd_building_long
                          or rv < (35 + rsi_bias) or srsi < 25 or pct_b < 0.25)
        if not ls_has_trigger:
            ls = min(ls, thresh - 0.5)   # cap below threshold — no catalyst, no entry

    # ── Score SHORT (max 9 points) ────────────────────────────────────────────
    ss = 0.0
    ss += 1.5 if ema_cross_down else (1.0 if not bull else 0)   # EMA cross = early entry bonus
    ss += ema_gap_bonus if not bull else 0                       # EMA gap strength
    # RSI: reward genuinely overbought only — thresholds shifted by rsi_bias for trending assets
    ss += 1.5 if rv > (70 - rsi_bias) else (1.0 if rv > (60 - rsi_bias) else 0)
    ss += 1.5 if macd_cross_down else (1.0 if (mh < 0 and macd_building_short) else (0.5 if mh < 0 else 0))  # MACD cross is strongest
    ss += 0.5 if vr > 1.5 else 0                                # Volume surge (raised from 1.3x)
    ss += 0.5 if fn > 0.01 else 0                               # Funding (longs paying)
    ss += 1.0 if pct_b > 0.8 else (0.5 if pct_b > 0.6 else 0)  # Bollinger upper band
    ss += 1.0 if srsi > 80 else (0.5 if srsi > 60 else 0)      # Stoch RSI overbought
    ss += 1.0 if obv_slope < 0 else 0                           # OBV falling
    ss += 0.5 if lower_highs else 0                             # Price action: lower highs

    # ── TUNED: confluence + trigger gate (mirror of LONG; selective_entry only)
    if selective_entry:
        ss_trigger   = ema_cross_down or macd_cross_down or rv > (70 - rsi_bias)
        ss_extreme   = srsi > 80 or pct_b > 0.8
        ss_confluence = 1.0 if (ss_trigger and ss_extreme and vr > 1.2) else 0.0
        ss += ss_confluence

        ss_has_trigger = (ema_cross_down or macd_cross_down or macd_building_short
                          or rv > (65 - rsi_bias) or srsi > 75 or pct_b > 0.75)
        if not ss_has_trigger:
            ss = min(ss, thresh - 0.5)

    ls, ss = round(ls, 1), round(ss, 1)

    # ── TUNED: minimum-conviction gap (selective_entry only) ──────────────────
    # Previously any ls > ss (even by 0.1) qualified as LONG, so choppy/contested
    # markets where both directions score near-equally near the threshold (the
    # classic "fires, then immediately reverses" bad trade) slipped through.
    # Require the winning side to clearly out-score the other before committing.
    gap = abs(ls - ss)
    _conv_gap = TUNED_CONVICTION_GAP if selective_entry else 0.0

    if ls >= thresh and ls > ss and gap >= _conv_gap:   dr, sc = "LONG",  ls
    elif ss >= thresh and ss > ls and gap >= _conv_gap: dr, sc = "SHORT", ss
    else:                                               dr, sc = "HOLD",  max(ls, ss)

    # ── RSI divergence detection ─────────────────────────────────────────────
    # Bearish: price higher high but RSI lower high → fade LONG signal
    # Bullish: price lower low but RSI higher low → fade SHORT signal
    rsi_divergence = None
    if len(cl) >= 10 and len(hist) >= 10 and len(rsi_vals) >= 10:
        rsi_div_vals = rsi_vals[-10:]  # Use pre-computed RSI series
        pr_hi2, pr_hi1 = max(cl[-10:-5]), max(cl[-5:])
        pr_lo2, pr_lo1 = min(cl[-10:-5]), min(cl[-5:])
        ri_hi2, ri_hi1 = max(rsi_div_vals[:5]), max(rsi_div_vals[5:])
        ri_lo2, ri_lo1 = min(rsi_div_vals[:5]), min(rsi_div_vals[5:])
        if pr_hi1 > pr_hi2 and ri_hi1 < ri_hi2 - 2:
            rsi_divergence = "BEARISH"   # price up, RSI down → fade longs
        elif pr_lo1 < pr_lo2 and ri_lo1 > ri_lo2 + 2:
            rsi_divergence = "BULLISH"   # price down, RSI up → fade shorts

    live_price = float(ticker.get("last", cl[-1]) or cl[-1])

    # Candle exhaustion: count consecutive same-colour candles at the tip
    # 3+ green candles in a row before a LONG = chasing; 3+ red before SHORT = same
    consec_green = 0
    consec_red   = 0
    if len(candles) >= 2:
        first_col = "G" if candles[-1]["close"] >= candles[-1]["open"] else "R"
        for i in range(1, min(5, len(candles)) + 1):
            bar = candles[-i]
            col = "G" if bar["close"] >= bar["open"] else "R"
            if col != first_col:
                break
            if first_col == "G":
                consec_green += 1
            else:
                consec_red += 1

    # ── MACD histogram exhaustion: is momentum slowing? ──────────────────────
    # Shrinking bearish (red) bars = bears losing steam = bounce candidate
    # Shrinking bullish (green) bars = bulls losing steam = fade candidate
    macd_hist_shrinking_bearish = False  # red bars getting smaller → LONG exhaustion signal
    macd_hist_shrinking_bullish = False  # green bars getting smaller → SHORT exhaustion signal
    if len(hist) >= 3:
        h1_, h2_, h3_ = hist[-3], hist[-2], hist[-1]
        # All three bars negative and each less negative than the last
        if h3_ < 0 and h2_ < 0 and h1_ < 0 and h3_ < h2_ < h1_:
            macd_hist_shrinking_bearish = True
        # All three bars positive and each less positive than the last
        if h3_ > 0 and h2_ > 0 and h1_ > 0 and h3_ > h2_ > h1_:
            macd_hist_shrinking_bullish = True

    # ── 10-bar high/low for OB bounce exhaustion check ───────────────────────
    price_new_10bar_low  = len(cl) >= 10 and cl[-1] <= min(cl[-10:])
    price_new_10bar_high = len(cl) >= 10 and cl[-1] >= max(cl[-10:])

    return {"direction": dr, "score": sc, "max_score": 9,
            "trend": "BULL" if bull else "BEAR",
            "rsi": rv, "srsi": srsi, "macd_h": round(mh, 6),
            "vol_ratio": vr, "funding": round(fn * 100, 4),
            "pct_b": pct_b, "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_mid": bb_mid,
            "atr_pct": round(atr_pct, 4), "atr_ok": atr_ok,
            "obv_slope": round(obv_slope, 2),
            "ema_gap_pct": round(ema_gap_pct, 4),
            "macd_building_long": macd_building_long,
            "macd_building_short": macd_building_short,
            "macd_cross_up": macd_cross_up,
            "macd_cross_down": macd_cross_down,
            "ema_cross_up": ema_cross_up,
            "ema_cross_down": ema_cross_down,
            "higher_lows": higher_lows,
            "lower_highs": lower_highs,
            "rsi_divergence": rsi_divergence,
            "consec_green": consec_green, "consec_red": consec_red,
            "macd_hist_shrinking_bearish": macd_hist_shrinking_bearish,
            "macd_hist_shrinking_bullish": macd_hist_shrinking_bullish,
            "price_new_10bar_low": price_new_10bar_low,
            "price_new_10bar_high": price_new_10bar_high,
            "price": live_price, "e9": e9, "e21": e21,
            "closes": cl, "macd_hist": hist, "macd_line": macd_line, "macd_signal": macd_sig,
            "candles": candles}

# ══════════════════════════════════════════════════════════════════════════════
#  CLAUDE
# ══════════════════════════════════════════════════════════════════════════════
# Module-level client cache — avoids constructing anthropic.Anthropic() on every call
_anthropic_client_cache: dict = {}  # api_key -> anthropic.Anthropic instance

def _get_anthropic_client(api_key: str):
    """Return a cached Anthropic client for the given key."""
    if api_key not in _anthropic_client_cache:
        _anthropic_client_cache[api_key] = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client_cache[api_key]
def claude_decision(signals, state, symbol, leverage, margin,
                     base_sl, base_tp, api_key, last3="no trades yet"):
    """
    Claude acts as decision engine — returns:
    {
      "action":     "TRADE" | "VETO" | "HOLD",
      "confidence": 0-100,
      "sl_pct":     adjusted stop loss %,
      "tp_pct":     adjusted take profit %,
      "reason":     short rationale string,
      "tokens_used": int
    }
    On any error returns None so bot falls back to indicator-only logic.
    """
    if not ANTHROPIC_AVAILABLE or not api_key:
        return None
    try:
        client = _get_anthropic_client(api_key)
        prompt = f"""You are the decision engine for Pacbot, a MEXC futures scalper.

Market: {symbol} @ ${signals["price"]:,.6g}  |  {leverage}x leverage  |  ${margin} margin
Direction signal: {signals["direction"]}  |  Score: {signals["score"]}/9

Indicators:
- Trend (EMA9/21): {signals["trend"]}
- RSI(14): {signals["rsi"]:.1f}  ({">70 overbought" if signals["rsi"]>70 else "<30 oversold" if signals["rsi"]<30 else "neutral"})
- Stoch RSI: {signals.get("srsi",50):.1f}
- MACD histogram: {signals["macd_h"]:+.6f}
- Bollinger %B: {signals.get("pct_b",0.5):.2f}  (0=lower band, 1=upper band)
- OBV slope: {"rising" if signals.get("obv_slope",0)>0 else "falling"}
- Volume ratio: {signals["vol_ratio"]}x avg
- ATR: {signals.get("atr_pct",0):.3f}% per candle  ({"active" if signals.get("atr_ok") else "too flat"})
- Funding rate: {signals["funding"]:+.4f}%

Session: P&L ${state.total_pnl:+.2f}  |  {state.wins}W / {state.losses}L / {state.liqs} LIQ
Base SL: {base_sl*100:.2f}%  |  Base TP: {base_tp*100:.2f}%
Fees (MEXC API Futures, effective May 2026): maker {MAKER_FEE_PCT*100:.2f}% open + taker {TAKER_FEE_PCT*100:.2f}% close = {(MAKER_FEE_PCT+TAKER_FEE_PCT)*100:.2f}% round-trip.
Estimated fee on this trade: ${margin*leverage*(MAKER_FEE_PCT+TAKER_FEE_PCT):.3f} (limit open) or ${margin*leverage*(TAKER_FEE_PCT*2):.3f} (market open).
TP price move must exceed {(MAKER_FEE_PCT+TAKER_FEE_PCT)*100:.2f}% just to break even — set TP at least {(MAKER_FEE_PCT+TAKER_FEE_PCT)*100+0.05:.2f}%+ above fees.
Last 3 trades: {last3}
{signals.get("_existing_note", "")}

Your job:
1. Decide: TRADE (proceed), VETO (block this trade), or HOLD (no trade signal)
2. Set confidence 0-100
3. Adjust SL and TP based on market quality:
   - Strong confluence + low ATR noise → widen TP (let it run), tighten SL
   - Weak/mixed signals → tighten TP (take profit fast), widen SL slightly
   - Never set SL below 0.03% or above 5%, never set TP below 0.05% or above 10%
4. VETO if: signals clearly contradict each other despite high score, or risk/reward is poor

Respond in EXACTLY this JSON format, nothing else:
{{"action":"TRADE","confidence":82,"sl_pct":0.006,"tp_pct":0.025,"reason":"Strong RSI oversold + MACD cross with rising OBV confirms genuine buying pressure."}}"""

        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}])

        raw  = msg.content[0].text.strip()
        tokens = (msg.usage.input_tokens or 0) + (msg.usage.output_tokens or 0)

        # Parse JSON response
        m = _re.search(r'\{[^{}]+\}', raw, _re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group())

        return {
            "action":     data.get("action", "HOLD"),
            "confidence": int(data.get("confidence", 50)),
            "sl_pct":     float(data.get("sl_pct", base_sl)),
            "tp_pct":     float(data.get("tp_pct", base_tp)),
            "reason":     str(data.get("reason", "")),
            "tokens_used": tokens,
        }
    except Exception as e:
        return None


def claude_near_tp_check(pos, cur_px, pct_to_tp, signals, api_key):
    """
    Called when a profitable trade is within 20% of its TP distance.
    Claude decides: take profit now, or hold for full TP.
    Returns:
      { "action": "TAKE" | "HOLD",
        "reason": str,
        "tokens_used": int }
    or None on error.
    """
    if not ANTHROPIC_AVAILABLE or not api_key:
        return None
    try:
        client = _get_anthropic_client(api_key)
        d = pos.direction
        tp_dist  = abs(pos.take_profit - pos.entry_price)
        sl_dist  = abs(pos.stop_loss   - pos.entry_price)
        cur_dist = abs(cur_px - pos.entry_price)
        profit_pct = cur_dist / pos.entry_price * 100
        rr_if_hold = (pct_to_tp * tp_dist) / sl_dist if sl_dist else 0

        prompt = f"""You are managing an open futures position that is CLOSE TO TAKE PROFIT.
Decide: take profit NOW at current price, or hold for full TP target.

Position:
- Symbol: {pos.symbol}  |  Direction: {d}  |  Leverage: {pos.leverage}x
- Entry: ${pos.entry_price:,.6g}  |  Current: ${cur_px:,.6g}  |  TP: ${pos.take_profit:,.6g}
- Distance to TP: {pct_to_tp:.1f}% of remaining TP gap  ({abs(pos.take_profit-cur_px):,.4g} price units away)
- Locked-in profit so far: {profit_pct:.3f}% price move ({profit_pct*pos.leverage:.1f}% margin return)
- SL at: ${pos.stop_loss:,.6g}  (would lose {sl_dist/pos.entry_price*100:.3f}% price if hit)

Market signals RIGHT NOW:
- Trend (EMA9/21): {signals.get("trend","?")}
- RSI: {signals.get("rsi",50):.1f}  |  Stoch RSI: {signals.get("srsi",50):.1f}
- MACD histogram: {signals.get("macd_h",0):+.6f}
- OBV slope: {"falling" if signals.get("obv_slope",0) < 0 else "rising"}
- Bollinger %B: {signals.get("pct_b",0.5):.2f}
- ATR: {signals.get("atr_pct",0):.3f}% per candle

Take profit early (TAKE) if:
- Momentum is reversing AGAINST the trade (RSI turning, MACD crossing, OBV diverging)
- We are very close (<10% gap left) and momentum is stalling
- Risk of snapback outweighs the small remaining gain

Hold for full TP (HOLD) if:
- Momentum is still WITH the trade
- RSI still has room (not at extreme reversal zone)
- The remaining distance is worth the risk

Respond in EXACTLY this JSON format, nothing else:
{{"action":"HOLD","reason":"MACD still negative and RSI has room — momentum intact, hold for full TP."}}"""

        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}])

        raw    = msg.content[0].text.strip()
        tokens = (msg.usage.input_tokens or 0) + (msg.usage.output_tokens or 0)

        m = _re.search(r'\{[^{}]+\}', raw, _re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group())
        return {
            "action":      data.get("action", "HOLD").upper(),
            "reason":      str(data.get("reason", "")),
            "tokens_used": tokens,
        }
    except Exception:
        return None


def claude_stale_trade_check(pos, cur_px, minutes_open, max_drift_pct, signals, api_key):
    """
    Called when a trade has been open a long time with little movement.
    Claude decides: close to free up margin, or hold longer.
    Returns:
      { "action": "CLOSE" | "HOLD",
        "reason": str,
        "tokens_used": int }
    or None on error.
    """
    if not ANTHROPIC_AVAILABLE or not api_key:
        return None
    try:
        client = _get_anthropic_client(api_key)
        d = pos.direction
        raw_chg = ((cur_px - pos.entry_price)/pos.entry_price if d=="LONG"
                   else (pos.entry_price - cur_px)/pos.entry_price)
        margin_pct = raw_chg * pos.leverage * 100
        dist_to_tp = abs(pos.take_profit - cur_px) / pos.entry_price * 100
        dist_to_sl = abs(pos.stop_loss   - cur_px) / pos.entry_price * 100

        hedge_note = (f"\nNOTE: This is a HEDGE position (opened against pid {pos.hedge_of}). "
                      "Both sides are open, so holding = paying funding on both legs."
                      if pos.hedge_of else "")

        prompt = f"""You are reviewing a stale open futures position that has barely moved.
The trade has been open for {minutes_open:.0f} minutes with only {max_drift_pct:.3f}% max price drift.{hedge_note}

Position:
- Symbol: {pos.symbol}  |  Direction: {d}  |  Leverage: {pos.leverage}x
- Entry: ${pos.entry_price:,.6g}  |  Current: ${cur_px:,.6g}
- Time open: {minutes_open:.0f} minutes
- Max drift from entry: {max_drift_pct:.3f}% price  (very little movement)
- Current P&L: {margin_pct:+.1f}% on margin
- Distance to TP: {dist_to_tp:.3f}%  |  Distance to SL: {dist_to_sl:.3f}%

Market signals RIGHT NOW:
- Trend (EMA9/21): {signals.get("trend","?")}
- RSI: {signals.get("rsi",50):.1f}  |  Stoch RSI: {signals.get("srsi",50):.1f}
- MACD histogram: {signals.get("macd_h",0):+.6f}
- OBV slope: {"falling" if signals.get("obv_slope",0) < 0 else "rising"}
- Bollinger %B: {signals.get("pct_b",0.5):.2f}
- ATR: {signals.get("atr_pct",0):.3f}% per candle  (low ATR = low volatility)
- Funding rate: {signals.get("funding",0):+.4f}%

Close (CLOSE) if:
- No catalyst visible — trend flat, ATR low, all indicators neutral
- Holding is paying ongoing funding costs with no directional conviction
- Margin is better deployed on a fresh signal
- This is a hedge and both sides are bleeding funding with no resolution

Hold (HOLD) if:
- Trend still aligns with position direction
- A catalyst appears imminent (RSI at extreme, MACD about to cross)
- Position is near TP and just needs patience

Respond in EXACTLY this JSON format, nothing else:
{{"action":"CLOSE","reason":"All indicators neutral, ATR flat, funding cost accumulating — no reason to hold stale position."}}"""

        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}])

        raw    = msg.content[0].text.strip()
        tokens = (msg.usage.input_tokens or 0) + (msg.usage.output_tokens or 0)

        m = _re.search(r'\{[^{}]+\}', raw, _re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group())
        return {
            "action":      data.get("action", "HOLD").upper(),
            "reason":      str(data.get("reason", "")),
            "tokens_used": tokens,
        }
    except Exception:
        return None

def claude_sl_update(pos, cur_px, drawdown_pct, velocity_pct, signals, api_key):
    """
    Called when a position is moving against us quickly.
    Claude decides whether to tighten the SL, hold it, or close immediately.
    Returns:
      { "action": "TIGHTEN" | "HOLD" | "CLOSE",
        "new_sl_price": float,   # only if TIGHTEN
        "reason": str,
        "tokens_used": int }
    or None on error.
    """
    if not ANTHROPIC_AVAILABLE or not api_key:
        return None
    try:
        client = _get_anthropic_client(api_key)
        d = pos.direction
        current_sl_pct = abs(cur_px - pos.stop_loss) / pos.entry_price * 100
        current_tp_pct = abs(pos.take_profit - pos.entry_price) / pos.entry_price * 100
        dist_to_sl_pct = abs(cur_px - pos.stop_loss) / pos.entry_price * 100

        prompt = f"""You are monitoring an open futures position that is moving AGAINST us.

Position:
- Symbol: {pos.symbol}  |  Direction: {d}  |  Leverage: {pos.leverage}x
- Entry: ${pos.entry_price:,.6g}  |  Current: ${cur_px:,.6g}
- Drawdown: {drawdown_pct:+.3f}% on margin  ({drawdown_pct/pos.leverage:.3f}% price move)
- Move velocity: {velocity_pct:.4f}% price move per cycle (fast = bad)
- Current SL: ${pos.stop_loss:,.6g}  ({current_sl_pct:.3f}% from entry)
- Current TP: ${pos.take_profit:,.6g}  ({current_tp_pct:.3f}% from entry)
- Distance to SL: {dist_to_sl_pct:.3f}% of entry price

Market context:
- RSI: {signals.get("rsi", 50):.1f}  |  Stoch RSI: {signals.get("srsi", 50):.1f}
- MACD histogram: {signals.get("macd_h", 0):+.6f}
- OBV slope: {"falling" if signals.get("obv_slope", 0) < 0 else "rising"}
- Bollinger %B: {signals.get("pct_b", 0.5):.2f}
- Trend: {signals.get("trend", "?")}

Decide ONE of:
1. TIGHTEN — move SL closer to current price to limit loss (give new_sl_price)
2. HOLD    — leave SL where it is, normal volatility, likely to reverse
3. CLOSE   — momentum is strongly against us, get out now before SL is hit

Rules:
- TIGHTEN: new SL must be between current price and original SL (cannot widen it)
- TIGHTEN: keep at least 0.03% buffer from current price to avoid immediate trigger
- CLOSE only if multiple indicators confirm continuation against us
- HOLD if this looks like normal noise within ATR range

Respond in EXACTLY this JSON format, nothing else:
{{"action":"TIGHTEN","new_sl_price":{pos.stop_loss:.6g},"reason":"RSI collapsing with OBV falling confirms selling pressure accelerating."}}"""

        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}])

        raw    = msg.content[0].text.strip()
        tokens = (msg.usage.input_tokens or 0) + (msg.usage.output_tokens or 0)

        m = _re.search(r'\{[^{}]+\}', raw, _re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group())

        action = data.get("action", "HOLD").upper()
        result = {
            "action":      action,
            "new_sl_price": float(data.get("new_sl_price", pos.stop_loss)),
            "reason":      str(data.get("reason", "")),
            "tokens_used": tokens,
        }

        # Safety: never let Claude widen the SL or set it past current price
        if action == "TIGHTEN":
            min_buffer = cur_px * 0.0003  # 0.03% buffer minimum
            if d == "LONG":
                # New SL must be below current price with buffer, but above original SL
                result["new_sl_price"] = max(
                    pos.stop_loss,
                    min(result["new_sl_price"], cur_px - min_buffer))
            else:
                # SHORT: new SL must be above current price with buffer, below original SL
                result["new_sl_price"] = min(
                    pos.stop_loss,
                    max(result["new_sl_price"], cur_px + min_buffer))

        return result
    except Exception:
        return None



def claude_trail_check(pos, cur_px, profit_pct_margin, signals, api_key,
                       open_fee_usdt=0.0, close_fee_rate=0.0006):
    """
    Called when a trade is meaningfully in profit (>=50% of TP distance reached).
    Claude analyses live market AND fees to decide whether to TRAIL or HOLD.

    Fee-aware logic:
      - open_fee_usdt: already paid at entry (sunk cost — informs net P&L so far)
      - close_fee_rate: will be paid on close regardless (affects TP break-even)
      - Extended TP must clear the close fee cost or it is not worth extending

    TP extension is ATR-based (2x ATR from current price) rather than a fixed
    percentage, so it scales with actual volatility.

    Safety rules enforced after Claude responds:
      LONG:  new_sl above entry, new_tp above current TP
      SHORT: new_sl below entry, new_tp below current TP
      Neither price may cross current price.
    """
    if not ANTHROPIC_AVAILABLE or not api_key:
        return None
    try:
        client = _get_anthropic_client(api_key)
        d         = pos.direction
        tp_dist   = abs(pos.take_profit - pos.entry_price)
        sl_dist   = abs(pos.stop_loss   - pos.entry_price)
        tp_left   = abs(pos.take_profit - cur_px)
        pct_done  = (1 - tp_left / tp_dist) * 100 if tp_dist else 0
        price_move_pct = abs(cur_px - pos.entry_price) / pos.entry_price * 100

        # ── Fee calculations ──────────────────────────────────────────────────
        # Close fee on full position size at current price
        size_usdt      = pos.margin * pos.leverage
        close_fee_usdt = size_usdt * close_fee_rate
        total_fees     = open_fee_usdt + close_fee_usdt
        # Net P&L right now if we closed at cur_px
        if d == "LONG":
            gross_pnl = (cur_px - pos.entry_price) / pos.entry_price * size_usdt
        else:
            gross_pnl = (pos.entry_price - cur_px) / pos.entry_price * size_usdt
        net_pnl_now = gross_pnl - total_fees

        # Break-even price for close fee alone (minimum TP must clear this)
        fee_be_move_pct = close_fee_rate * 100   # % price move needed just to pay close fee
        # Minimum extended TP must net at least as much as closing now
        # i.e. extended TP gross pnl > current gross pnl + close fee (already included)
        min_tp_move_pct = price_move_pct + fee_be_move_pct * 1.5  # 50% buffer over fee cost

        # ── ATR-based TP extension ────────────────────────────────────────────
        atr_pct = signals.get("atr_pct", 0)   # % of price per candle
        atr_abs = cur_px * atr_pct / 100       # absolute price units
        # Extend by 2x ATR from current price — scales with actual volatility
        atr_tp_extension = atr_abs * 2.0
        if d == "LONG":
            suggested_sl = round_price(pos.symbol, pos.entry_price + sl_dist * 0.5)
            atr_tp        = round_price(pos.symbol, cur_px + atr_tp_extension)
            suggested_tp  = max(atr_tp, pos.take_profit)   # never shrink
        else:
            suggested_sl = round_price(pos.symbol, pos.entry_price - sl_dist * 0.5)
            atr_tp        = round_price(pos.symbol, cur_px - atr_tp_extension)
            suggested_tp  = min(atr_tp, pos.take_profit)   # never shrink

        # Move the suggested TP must represent (as % of entry)
        suggested_tp_move_pct = abs(suggested_tp - pos.entry_price) / pos.entry_price * 100

        prompt = f"""You are the risk manager for Pacbot, a MEXC futures scalper.
A trade is IN PROFIT. Decide whether to TRAIL (lock in profit via SL + extend TP) or HOLD.
You must factor in trading fees — extending TP is only worth it if the extra gain clears fees.

Position:
- Symbol: {pos.symbol}  |  Direction: {d}  |  Leverage: {pos.leverage}x
- Entry: ${pos.entry_price:,.6g}  |  Current: ${cur_px:,.6g}
- Current SL: ${pos.stop_loss:,.6g}  |  Current TP: ${pos.take_profit:,.6g}
- Price moved: {price_move_pct:.3f}% from entry  ({profit_pct_margin:+.1f}% on margin)
- TP progress: {pct_done:.0f}% of the way to TP

Fee breakdown (MEXC API, effective May 2026):
- Open fee already paid: ${open_fee_usdt:.4f}
- Close fee if closed now: ${close_fee_usdt:.4f}  ({close_fee_rate*100:.3f}% taker)
- Net P&L if closed NOW: ${net_pnl_now:+.4f}  (after both fees)
- Minimum price move for extended TP to be worthwhile: {min_tp_move_pct:.3f}% from entry
  (must beat current net P&L + fee buffer — do not extend TP if it cannot clear this)

ATR-based suggested levels (2x ATR = proportionate to current volatility):
- ATR per candle: {atr_pct:.4f}% ({atr_abs:,.6g} price units)
- Suggested new SL: ${suggested_sl:,.6g}  (locks in profit above entry)
- Suggested new TP: ${suggested_tp:,.6g}  (2x ATR extension from current price = {suggested_tp_move_pct:.3f}% from entry)
  {'✓ This TP clears the fee threshold' if suggested_tp_move_pct >= min_tp_move_pct else '⚠ This TP does NOT clear fees — do NOT extend TP, only move SL if warranted'}

Live market indicators:
- Trend (EMA9/21): {signals.get("trend","?")}
- RSI(14): {signals.get("rsi",50):.1f}  |  Stoch RSI: {signals.get("srsi",50):.1f}
- MACD histogram: {signals.get("macd_h",0):+.6f}  ({'building' if (d=='LONG' and signals.get('macd_building_long')) or (d=='SHORT' and signals.get('macd_building_short')) else 'fading'})
- OBV slope: {'rising' if signals.get('obv_slope',0) > 0 else 'falling'}
- Bollinger %B: {signals.get("pct_b",0.5):.2f}
- Higher lows: {signals.get("higher_lows", False)}  |  Lower highs: {signals.get("lower_highs", False)}

Decision rules:
- TRAIL (move SL only, keep current TP) if: momentum is with the trade but ATR extension does not clear fees
- TRAIL (move SL + extend TP) if: momentum CLEARLY with trade AND ATR TP clears the fee threshold
- HOLD if: momentum fading, mixed signals, or reversal indicators present
- NEVER extend TP if suggested_tp does not clear the minimum fee threshold above
- NEVER trail if RSI is at reversal extreme ({'>70' if d=='LONG' else '<30'} is danger zone for {d})
- NEVER trail if MACD histogram fading or crossed against the trade direction

Respond in EXACTLY this JSON format, nothing else:
{{"action":"TRAIL","new_sl_price":{suggested_sl:.6g},"new_tp_price":{suggested_tp:.6g},"reason":"MACD building, OBV rising, ATR TP clears fee threshold — locking SL and extending target."}}"""

        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}])

        raw    = msg.content[0].text.strip()
        tokens = (msg.usage.input_tokens or 0) + (msg.usage.output_tokens or 0)

        m = _re.search(r'\{[^{}]+\}', raw, _re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group())

        action       = data.get("action", "HOLD").upper()
        new_sl_price = float(data.get("new_sl_price", pos.stop_loss))
        new_tp_price = float(data.get("new_tp_price", pos.take_profit))
        reason       = str(data.get("reason", ""))

        # ── Safety clamps — enforced in code, not left to Claude ─────────────
        min_buf = cur_px * 0.0003
        if action == "TRAIL":
            if d == "LONG":
                new_sl_price = max(pos.entry_price + min_buf,
                                   min(new_sl_price, cur_px - min_buf))
                new_tp_price = max(new_tp_price, pos.take_profit + min_buf)
                # Hard gate: new TP must represent at least min_tp_move_pct from entry
                min_tp_abs = pos.entry_price * (1 + min_tp_move_pct / 100)
                if new_tp_price < min_tp_abs:
                    new_tp_price = pos.take_profit   # revert — doesn't clear fees
            else:
                new_sl_price = min(pos.entry_price - min_buf,
                                   max(new_sl_price, cur_px + min_buf))
                new_tp_price = min(new_tp_price, pos.take_profit - min_buf)
                min_tp_abs = pos.entry_price * (1 - min_tp_move_pct / 100)
                if new_tp_price > min_tp_abs:
                    new_tp_price = pos.take_profit   # revert

            sl_unchanged = abs(new_sl_price - pos.stop_loss)   < min_buf
            tp_unchanged = abs(new_tp_price - pos.take_profit) < min_buf
            if sl_unchanged and tp_unchanged:
                action = "HOLD"

        return {
            "action":        action,
            "new_sl_price":  new_sl_price,
            "new_tp_price":  new_tp_price,
            "reason":        reason,
            "tokens_used":   tokens,
            "net_pnl_now":   net_pnl_now,
            "fee_total":     total_fees,
        }
    except Exception:
        return None


def claude_hedge_check(pos, cur_px, drawdown_pct, signals, api_key):
    """
    Claude independently decides whether to open a hedge on an existing position.
    Called every cycle for each open non-hedge position, regardless of hedge toggle.
    Returns:
      { "action": "HEDGE" | "HOLD",
        "confidence": 0-100,
        "reason": str,
        "tokens_used": int }
    or None on error.
    """
    if not ANTHROPIC_AVAILABLE or not api_key:
        return None
    try:
        client = _get_anthropic_client(api_key)
        d = pos.direction
        dist_to_sl  = abs(cur_px - pos.stop_loss) / pos.entry_price * 100
        dist_to_tp  = abs(pos.take_profit - cur_px) / pos.entry_price * 100
        dist_to_liq = abs(cur_px - pos.liq_price)  / pos.entry_price * 100
        time_open   = ""
        try:
            opened = datetime.fromisoformat(pos.opened_at.replace("Z", "+00:00"))
            mins   = int((datetime.now(timezone.utc) - opened).total_seconds() / 60)
            time_open = f"{mins} minutes"
        except Exception:
            time_open = "unknown"

        prompt = f"""You are risk manager for Pacbot, a MEXC futures scalper.
An existing position is in drawdown. Decide if opening a HEDGE (opposite direction, half margin) is wise.

Position:
- Symbol: {pos.symbol}  |  Direction: {d}  |  Leverage: {pos.leverage}x
- Entry: ${pos.entry_price:,.6g}  |  Current: ${cur_px:,.6g}
- Drawdown on margin: {drawdown_pct:+.2f}%  ({drawdown_pct/pos.leverage:.3f}% price move)
- Time open: {time_open}
- Distance to SL:  {dist_to_sl:.3f}%  |  Distance to TP: {dist_to_tp:.3f}%
- Distance to LIQ: {dist_to_liq:.3f}%

Market signals now:
- Trend (EMA9/21): {signals.get("trend", "?")}
- RSI: {signals.get("rsi", 50):.1f}  |  Stoch RSI: {signals.get("srsi", 50):.1f}
- MACD histogram: {signals.get("macd_h", 0):+.6f}
- OBV slope: {"falling" if signals.get("obv_slope", 0) < 0 else "rising"}
- Bollinger %B: {signals.get("pct_b", 0.5):.2f}
- ATR: {signals.get("atr_pct", 0):.3f}% per candle
- Funding rate: {signals.get("funding", 0):+.4f}%

Hedge logic: opening opposite direction at half margin locks in partial loss now,
caps further downside, and profits if price continues against original position.
Best when: momentum clearly reversed, ALL major indicators agree, SL still far away.
Avoid when: normal noise dip, any indicator is mixed, or already near SL.

Decide ONE of:
1. HEDGE — open opposite position at half margin to cap losses
2. HOLD  — drawdown is noise or recoverable, leave position alone

Rules — ALL must be true to HEDGE:
- 4+ indicators must confirm the adverse move will continue (trend, RSI, MACD, OBV, BB)
- Drawdown already > -8% on margin (this trade is genuinely in trouble)
- Distance to SL > 0.3% price (room for it to get meaningfully worse)
- No mixed signals — if anything contradicts, choose HOLD
- Default bias is strongly HOLD — hedging locks in losses and costs extra margin

Only return HEDGE if you are highly confident (70%+). Otherwise HOLD.

Respond in EXACTLY this JSON format, nothing else:
{{"action":"HEDGE","confidence":78,"reason":"RSI dropped below 30 with MACD turning negative and OBV falling — reversal unlikely short term."}}"""

        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}])

        raw    = msg.content[0].text.strip()
        tokens = (msg.usage.input_tokens or 0) + (msg.usage.output_tokens or 0)

        m = _re.search(r'\{[^{}]+\}', raw, _re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group())

        return {
            "action":      data.get("action", "HOLD").upper(),
            "confidence":  int(data.get("confidence", 50)),
            "reason":      str(data.get("reason", "")),
            "tokens_used": tokens,
        }
    except Exception:
        return None

# Keep old function name as alias for HOLD reasoning (no decision needed)
def claude_reasoning(signals, state, symbol, leverage, margin, api_key):
    """Used for HOLD cycles — just returns explanatory text, no decision."""
    if not ANTHROPIC_AVAILABLE or not api_key: return None
    try:
        client = _get_anthropic_client(api_key)
        prompt = (f"Pacbot HOLD analysis. {symbol} @ ${signals['price']:,.6g} "
                  f"Score {signals['score']}/9 {signals['direction']}. "
                  f"Trend:{signals['trend']} RSI:{signals['rsi']:.0f} "
                  f"StochRSI:{signals.get('srsi',50):.0f} MACD:{'pos' if signals['macd_h']>0 else 'neg'} "
                  f"BB%B:{signals.get('pct_b',0.5):.2f} OBV:{'up' if signals.get('obv_slope',0)>0 else 'dn'} "
                  f"ATR:{signals.get('atr_pct',0):.3f}% Fund:{signals['funding']:+.4f}%. "
                  f"2 sentences: why hold and what would change your mind.")
        msg = client.messages.create(model="claude-haiku-4-5", max_tokens=100,
                                     messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text
    except Exception:
        return None

def test_claude_key(api_key):
    if not ANTHROPIC_AVAILABLE:
        return False, "Run:  pip install anthropic"
    if not api_key.strip():
        return False, "No key entered"
    try:
        client = anthropic.Anthropic(api_key=api_key.strip())
        client.messages.create(model="claude-haiku-4-5", max_tokens=5,
                                messages=[{"role": "user", "content": "hi"}])
        return True, "✅  Connected"
    except Exception as e:
        raw = str(e)
        if "401" in raw or "authentication" in raw.lower(): return False, "❌  Invalid key"
        if "403" in raw or "credit" in raw.lower():        return False, "❌  Add billing: console.anthropic.com"
        if "connection" in raw.lower():                    return False, "❌  No internet"
        return False, f"❌  {raw[:80]}"

# ══════════════════════════════════════════════════════════════════════════════
#  CHART PANEL
# ══════════════════════════════════════════════════════════════════════════════
class ChartPanel:
    def __init__(self, parent, symbol, colour):
        self.symbol = symbol; self.colour = colour
        self.fig = None; self.canvas = None
        self._build(parent)

    def _build(self, parent):
        if not MPLOT:
            tk.Label(parent, text="pip install matplotlib\nto enable charts",
                     bg=BG4, fg=MUTED, font=FM, justify="center").pack(expand=True)
            return

        # ── Toolbar: TF buttons + zoom controls ──────────────────────────────
        toolbar = tk.Frame(parent, bg=BG3, height=26)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        self._chart_tf     = "Min5"
        self._chart_zoom   = 60   # number of candles visible
        self._chart_offset = 0    # candles from right (0 = live edge)
        self._price_pan    = 0.0  # vertical price pan (fraction of range; 0 = auto-centre)
        self._price_scale  = 1.0  # vertical price zoom (1.0 = auto-fit)
        self._last_candles   = []
        self._last_signals   = None
        self._last_positions = []
        self._on_tf_change   = None  # kept for compat but no longer used
        self._tf_candles     = {}    # per-TF candle cache

        tf_opts = [("1m","Min1"),("5m","Min5"),("15m","Min15"),("30m","Min30"),
                   ("1h","Hour1"),("4h","Hour4"),("1d","Day1")]
        self._tf_values = [tv for _, tv in tf_opts]
        for label, tf_val in tf_opts:
            b = tk.Button(toolbar, text=label,
                          font=("Consolas", 7, "bold"),
                          bg=CYAN if tf_val == "Min5" else BG3,
                          fg=BG if tf_val == "Min5" else MUTED,
                          relief="flat", padx=6, pady=2, cursor="hand2",
                          command=lambda t=tf_val: self._set_tf(t))
            b.pack(side="left", padx=(2,0), pady=2)
            setattr(self, f"_tf_btn_{tf_val}", b)

        tk.Frame(toolbar, bg=SEP, width=1).pack(side="left", fill="y", padx=4, pady=3)

        for txt, cmd in [("🔍+", lambda: self._zoom(-10)),
                          ("🔍−", lambda: self._zoom(+10)),
                          ("◀",   lambda: self._scroll(+10)),
                          ("▶",   lambda: self._scroll(-10)),
                          ("↺",   lambda: self._reset_view())]:
            tk.Button(toolbar, text=txt, font=("Consolas", 8), bg=BG3, fg=MUTED,
                      relief="flat", padx=5, pady=1, cursor="hand2",
                      command=cmd).pack(side="left", padx=(2,0), pady=2)

        self._zoom_lbl = tk.Label(toolbar, text="60 candles", font=("Consolas", 7),
                                   fg=DIM, bg=BG3)
        self._zoom_lbl.pack(side="right", padx=6)
        tk.Label(toolbar, text="wheel: pan · ctrl: zoom · shift: price",
                 font=("Consolas", 7), fg=DIM, bg=BG3).pack(side="right", padx=4)

        plt.style.use("dark_background")
        self.fig = plt.Figure(figsize=(10, 6), dpi=100, facecolor=BG4)
        gs = GridSpec(3, 1, figure=self.fig, hspace=0.04, height_ratios=[3, 1, 1.2],
                       left=0.02, right=0.85, top=0.97, bottom=0.06)
        self.ax_p = self.fig.add_subplot(gs[0])
        self.ax_r = self.fig.add_subplot(gs[1], sharex=self.ax_p)
        self.ax_m = self.fig.add_subplot(gs[2], sharex=self.ax_p)
        for ax in (self.ax_p, self.ax_r, self.ax_m):
            ax.set_facecolor(BG4)
            ax.tick_params(colors=C_AX, labelsize=7.5)
            ax.spines[:].set_color(C_GRID)
            ax.grid(color=C_GRID, linewidth=0.5, alpha=0.8)
        plt.setp(self.ax_p.get_xticklabels(), visible=False)
        plt.setp(self.ax_r.get_xticklabels(), visible=False)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # ── Mouse wheel:  plain = pan through time,  Ctrl = zoom ──────────────
        w = self.canvas.get_tk_widget()

        def _wheel(up, state):
            # Ctrl → time zoom; Shift → price pan; plain → time pan
            if state & 0x0004:        # Ctrl
                self._zoom(-5 if up else 5)
            elif state & 0x0001:      # Shift → vertical price pan
                self._pan_price(+0.08 if up else -0.08)
            else:                     # plain → horizontal time pan
                self._scroll(+5 if up else -5)

        w.bind("<MouseWheel>",  lambda e: _wheel(e.delta > 0, e.state))   # Win / Mac
        w.bind("<Button-4>",    lambda e: _wheel(True,  e.state))         # Linux up
        w.bind("<Button-5>",    lambda e: _wheel(False, e.state))         # Linux down
        # Explicit modifier bindings for platforms that route them separately
        w.bind("<Control-MouseWheel>", lambda e: self._zoom(-5 if e.delta > 0 else 5))
        w.bind("<Control-Button-4>",   lambda e: self._zoom(-5))
        w.bind("<Control-Button-5>",   lambda e: self._zoom(+5))
        w.bind("<Shift-MouseWheel>",   lambda e: self._pan_price(+0.08 if e.delta > 0 else -0.08))
        w.bind("<Shift-Button-4>",     lambda e: self._pan_price(+0.08))
        w.bind("<Shift-Button-5>",     lambda e: self._pan_price(-0.08))
        self._placeholder()

    def _set_tf(self, tf):
        self._chart_tf = tf
        self._chart_offset = 0   # jump to live edge on TF change
        # Update button highlights
        for t in getattr(self, "_tf_values", ["Min1","Min5","Min15","Min30","Hour1","Hour4","Day1"]):
            btn = getattr(self, f"_tf_btn_{t}", None)
            if btn:
                btn.config(bg=CYAN if t == tf else BG3,
                           fg=BG if t == tf else MUTED)
        # Use cached data immediately if available
        if tf in self._tf_candles:
            cached = self._tf_candles[tf]
            self._last_candles = cached.get("candles", self._last_candles)
            self._last_signals = cached.get("signals", self._last_signals)
            self._redraw()
        # Always background-refresh independently of bot loop
        def _bg_fetch():
            try:
                can2 = get_klines(self.symbol, tf, 200)
                tkr2 = get_ticker(self.symbol)
                from dataclasses import asdict
                # compute_signals needs thresh — use 6.0 as reasonable default
                sig2 = compute_signals(can2, tkr2, 6.0)
                self._tf_candles[tf] = {"candles": can2, "signals": sig2}
                # Only update display if this TF is still the active one
                if self._chart_tf == tf:
                    import tkinter as _tk
                    self._last_candles = can2
                    self._last_signals = sig2
                    try:
                        self._redraw()
                    except Exception as _exc:
                        _file_logger.debug("suppressed error: %s", _exc)
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)
        threading.Thread(target=_bg_fetch, daemon=True).start()

    def _zoom(self, delta):
        self._chart_zoom = max(CHART_ZOOM_MIN, min(CHART_ZOOM_MAX, self._chart_zoom + delta))
        try:
            if hasattr(self, '_zoom_lbl'):
                self._zoom_lbl.config(text=f"{self._chart_zoom} candles")
        except (AttributeError, tk.TclError) as e:
            _file_logger.debug(f"Chart zoom label update failed: {e}")
        self._redraw()

    def _scroll(self, delta):
        max_off = max(0, len(self._last_candles) - self._chart_zoom)
        self._chart_offset = max(0, min(max_off, self._chart_offset + delta))
        self._redraw()

    def _pan_price(self, delta_frac):
        """Pan the price (vertical) axis. delta_frac is fraction of visible range."""
        self._price_pan = max(-3.0, min(3.0, getattr(self, "_price_pan", 0.0) + delta_frac))
        self._redraw()

    def _zoom_price(self, factor):
        """Zoom the price (vertical) axis. factor>1 zooms out, <1 zooms in."""
        self._price_scale = max(0.1, min(5.0, getattr(self, "_price_scale", 1.0) * factor))
        self._redraw()

    def _reset_view(self):
        self._chart_offset = 0
        self._chart_zoom   = 60
        self._price_pan    = 0.0
        self._price_scale  = 1.0
        try:
            if hasattr(self, '_zoom_lbl'):
                self._zoom_lbl.config(text=f"{CHART_ZOOM_DEFAULT} candles")
        except (AttributeError, tk.TclError) as e:
            _file_logger.debug(f"Chart reset label update failed: {e}")
        self._redraw()

    def _redraw(self):
        if self._last_candles:
            self._draw(self._last_candles, self._last_signals, self._last_positions)

    def _placeholder(self):
        if not MPLOT: return
        self.ax_p.clear(); self.ax_p.set_facecolor(BG4)
        self.ax_p.text(0.5, 0.5, f"{self.symbol}\nWaiting for data…",
                       transform=self.ax_p.transAxes, ha="center", va="center",
                       color=self.colour, fontsize=13, alpha=0.4)
        self.canvas.draw_idle()

    def update(self, candles, signals=None, positions=None, on_tf_change=None,
               bot_tf="Min5"):
        if not MPLOT or not candles: return
        if on_tf_change:
            self._on_tf_change = on_tf_change
        live_price = signals.get("price") if isinstance(signals, dict) else None
        try:
            live_price = float(live_price) if live_price else 0.0
        except Exception:
            live_price = 0.0
        user_tf = getattr(self, "_chart_tf", "Min5")
        if user_tf == bot_tf:
            # User is on the same TF the bot scans — update candles normally
            display_candles = candles
            if live_price > 0:
                display_candles = [dict(c) for c in candles]
                last = dict(display_candles[-1])
                last["close"] = live_price
                last["high"] = max(float(last.get("high", live_price)), live_price)
                last["low"] = min(float(last.get("low", live_price)), live_price)
                display_candles[-1] = last
            self._last_candles = display_candles
            self._last_signals = signals
        else:
            # User has switched to a different TF — only update the live price
            # on the existing candle data; never overwrite their view
            if live_price > 0 and self._last_candles:
                patched = [dict(c) for c in self._last_candles]
                last = dict(patched[-1])
                last["close"] = live_price
                last["high"] = max(float(last.get("high", live_price)), live_price)
                last["low"] = min(float(last.get("low", live_price)), live_price)
                patched[-1] = last
                self._last_candles = patched
        self._last_positions = positions or []
        # Always go through _redraw so zoom/offset are applied consistently
        self._redraw()

    # ── TF → seconds per candle ───────────────────────────────────────────────
    _TF_SECS = {
        "Min1": 60, "Min5": 300, "Min15": 900, "Min30": 1800,
        "Hour1": 3600, "Min60": 3600, "Hour4": 14400, "Day1": 86400,
    }

    def _candle_timestamps(self, n, tf):
        """Return list of n Unix timestamps (seconds) working back from now."""
        secs = self._TF_SECS.get(tf, 300)
        now  = int(time.time())
        # Snap to candle boundary
        now  = (now // secs) * secs
        return [now - (n - 1 - i) * secs for i in range(n)]

    def _fmt_time(self, ts, tf):
        """Format a Unix timestamp for the x-axis label given the TF."""
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if tf == "Day1":
            return dt.strftime("%d %b")
        if tf in ("Hour4", "Hour1", "Min60"):
            return dt.strftime("%d %b\n%H:%M")
        return dt.strftime("%H:%M")

    def _draw(self, candles, signals, positions):
        # Apply zoom and scroll offset
        zoom   = getattr(self, "_chart_zoom",   60)
        offset = getattr(self, "_chart_offset",  0)
        total  = len(candles)
        end    = total - offset
        start  = max(0, end - zoom)
        candles = candles[start:end] if end > 0 else candles[-zoom:]

        cl = [c["close"] for c in candles]; op = [c["open"]  for c in candles]
        hi = [c["high"]  for c in candles]; lo = [c["low"]   for c in candles]
        n = len(candles); xs = list(range(n))

        # ── Build time axis labels ─────────────────────────────────────────────
        tf = getattr(self, "_chart_tf", "Min5")
        # Reconstruct timestamps for the visible window.
        # We know the full candle array has `total` bars ending at now; the
        # visible slice runs from `start` to `end` (indices into that array).
        secs_per_candle = self._TF_SECS.get(tf, 300)
        now_snapped = (int(time.time()) // secs_per_candle) * secs_per_candle
        # Index 0 of visible slice = total candle at index `start`
        # Its timestamp = now_snapped - (total - 1 - start) * secs_per_candle
        start_ts = now_snapped - (total - 1 - start) * secs_per_candle
        timestamps = [start_ts + i * secs_per_candle for i in range(n)]

        # Choose ~5-8 evenly spaced tick positions
        tick_step = max(1, n // 6)
        tick_xs   = list(range(0, n, tick_step))
        tick_lbls = [self._fmt_time(timestamps[i], tf) for i in tick_xs]

        for ax in (self.ax_p, self.ax_r, self.ax_m):
            ax.clear(); ax.set_facecolor(BG4)
            ax.tick_params(colors=C_AX, labelsize=7.5)
            ax.grid(color=C_GRID, linewidth=0.5, alpha=0.8)
            ax.spines[:].set_color(C_GRID)

        # Candles
        for i, (o, c, h, l) in enumerate(zip(op, cl, hi, lo)):
            col  = C_UP if c >= o else C_DOWN
            bbot = min(o, c)
            bh   = max(abs(c - o), c * 0.0002)
            self.ax_p.bar(i, bh, bottom=bbot, color=col, width=0.7, linewidth=0, alpha=0.9)
            self.ax_p.plot([i, i], [l, h], color=col, linewidth=0.9, alpha=0.85)

        # EMAs — slice to the same window as candles
        if signals and "e9" in signals:
            e9_full  = signals["e9"]
            e21_full = signals["e21"]
            # Use the length of the indicator arrays themselves — they were computed
            # from the same candles passed into _draw(), so this is always in sync
            # regardless of what self._last_candles contains at draw time.
            total_full = len(e9_full)
            zoom   = getattr(self, "_chart_zoom",   60)
            offset = getattr(self, "_chart_offset",  0)
            end_i  = max(0, total_full - offset)
            start_i= max(0, end_i - zoom)
            e9  = e9_full[start_i:end_i]
            e21 = e21_full[start_i:end_i] if len(e21_full) >= total_full else e21_full[-(end_i-start_i):]
            # Pad or trim to exactly n so the plot always aligns with candles
            def _fit(arr, length):
                if len(arr) < length: return [arr[0]] * (length - len(arr)) + list(arr)
                return list(arr[-length:])
            e9  = _fit(e9,  n)
            e21 = _fit(e21, n)
            self.ax_p.plot(xs, e9,  color=YELLOW, linewidth=1.2, alpha=0.9, label="EMA9")
            self.ax_p.plot(xs, e21, color=ORANGE, linewidth=1.2, alpha=0.9, label="EMA21")

        # Position lines — entry, TP, SL, LIQ with price labels
        def _fp(v):
            if v < 0.0001:  return f"${v:.8f}"
            if v < 0.001:   return f"${v:.7f}"
            if v < 0.1:     return f"${v:.5f}"
            if v < 10:      return f"${v:.4f}"
            if v >= 1000:   return f"${v:,.1f}"
            return f"${v:,.2f}"

        for pos in positions:
            if pos.symbol != self.symbol: continue
            is_long = pos.direction == "LONG"
            pc  = GREEN if is_long else RED
            tag = "L" if is_long else "S"
            h_tag = " [H]" if pos.hedge_of else ""

            # Entry line — blue dashed, distinct from TP/SL
            ENTRY_COL = "#4da6ff"  # bright blue, clearly different from green/red
            entry_label_str = f"▶ ENTRY ({'L' if is_long else 'S'}){h_tag}"
            self.ax_p.axhline(pos.entry_price, color=ENTRY_COL, lw=1.5, ls="--", alpha=0.95,
                               label=entry_label_str)
            self.ax_p.annotate(
                f" {entry_label_str} {_fp(pos.entry_price)}",
                xy=(n * 0.01, pos.entry_price),
                color=ENTRY_COL, fontsize=8.5, fontweight="bold",
                va="bottom", ha="left",
                bbox=dict(boxstyle="round,pad=0.15", fc=BG4, ec=ENTRY_COL, alpha=0.85))

            # Take profit — green dashed with filled band between entry and TP
            tp_col = "#00e676"
            self.ax_p.axhline(pos.take_profit, color=tp_col, lw=1.2, ls="--", alpha=0.9,
                               label=f"✓ TP {_fp(pos.take_profit)}")
            self.ax_p.annotate(
                f" ✓ TP  {_fp(pos.take_profit)}",
                xy=(n * 0.01, pos.take_profit),
                color=tp_col, fontsize=8.5, fontweight="bold",
                va="bottom", ha="left",
                bbox=dict(boxstyle="round,pad=0.15", fc=BG4, ec=tp_col, alpha=0.85))
            # Green filled band between entry and TP
            self.ax_p.axhspan(pos.entry_price, pos.take_profit, alpha=0.05, color=tp_col)

            # Stop loss — red dashed with filled band between entry and SL
            sl_col = "#ff3d57"
            self.ax_p.axhline(pos.stop_loss, color=sl_col, lw=1.2, ls="--", alpha=0.9,
                               label=f"✕ SL  {_fp(pos.stop_loss)}")
            self.ax_p.annotate(
                f" ✕ SL  {_fp(pos.stop_loss)}",
                xy=(n * 0.01, pos.stop_loss),
                color=sl_col, fontsize=8.5, fontweight="bold",
                va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.15", fc=BG4, ec=sl_col, alpha=0.85))
            # Red filled band between entry and SL
            self.ax_p.axhspan(pos.stop_loss, pos.entry_price, alpha=0.05, color=sl_col)

            # Liquidation — pink dotted, thinner
            self.ax_p.axhline(pos.liq_price, color="#f783ac", lw=0.9, ls="-.", alpha=0.75,
                               label=f"LIQ {_fp(pos.liq_price)}")
            self.ax_p.annotate(
                f" LIQ {_fp(pos.liq_price)}",
                xy=(n * 0.01, pos.liq_price),
                color="#f783ac", fontsize=8.5, fontweight="bold",
                va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.15", fc=BG4, ec="#f783ac", alpha=0.75))

        # Price label — cl[-1] is already patched with live WS price by update()
        if cl:
            pcol = C_UP if cl[-1] >= op[-1] else C_DOWN
            display_px = cl[-1]
            if display_px < 0.000001: pstr = f"  ${display_px:,.8f}"
            elif display_px < 0.0001: pstr = f"  ${display_px:,.7f}"
            elif display_px < 0.01:   pstr = f"  ${display_px:,.5f}"
            elif display_px < 1:      pstr = f"  ${display_px:,.4f}"
            elif display_px < 10:     pstr = f"  ${display_px:,.3f}"
            elif display_px >= 10000: pstr = f"  ${display_px:,.0f}"
            elif display_px >= 1000:  pstr = f"  ${display_px:,.1f}"
            else:                     pstr = f"  ${display_px:,.2f}"
            self.ax_p.annotate(pstr, xy=(n-1, cl[-1]), color=pcol,
                               fontsize=8.5, fontweight="bold", va="center")

        self.ax_p.text(0.01, 0.97, pair_label(self.symbol),
                       transform=self.ax_p.transAxes,
                       color=self.colour, fontsize=10, fontweight="bold", va="top")
        # TF label top-right
        tf_display = getattr(self, "_chart_tf", "Min5").replace("Min","").replace("Hour","h").replace("Day","d")
        self.ax_p.text(0.99, 0.97, tf_display,
                       transform=self.ax_p.transAxes,
                       color=MUTED, fontsize=9, fontweight="bold", va="top", ha="right")
        if hi and lo:
            base_pad = (max(hi) - min(lo)) * 0.08 or 1
            lo_auto  = min(lo) - base_pad
            hi_auto  = max(hi) + base_pad
            mid      = (lo_auto + hi_auto) / 2
            rng      = (hi_auto - lo_auto) / 2
            scale    = getattr(self, "_price_scale", 1.0)
            pan      = getattr(self, "_price_pan", 0.0)
            # scale<1 zooms in (smaller range), pan shifts the centre by fraction of range
            half     = rng * scale
            centre   = mid + pan * rng
            self.ax_p.set_ylim(centre - half, centre + half)
        self.ax_p.yaxis.tick_right(); self.ax_p.yaxis.set_label_position("right")

        # ── Price y-axis: auto-spaced ticks within the visible range ──────────
        if hi and lo:
            y_lo, y_hi = self.ax_p.get_ylim()
            price_range = y_hi - y_lo
            # Pick a round step so we get ~5 ticks
            raw_step = price_range / 5
            magnitude = 10 ** int(math.log10(raw_step)) if raw_step > 0 else 1
            for divisor in (1, 2, 2.5, 5, 10):
                candidate = magnitude * divisor
                if raw_step / candidate <= 1.0:
                    tick_step_price = candidate
                    break
            else:
                tick_step_price = raw_step
            first_tick = math.ceil(y_lo / tick_step_price) * tick_step_price
            price_ticks = []
            v = first_tick
            while v <= y_hi:
                price_ticks.append(v)
                v += tick_step_price
            self.ax_p.set_yticks(price_ticks)
            # Format: no decimals for large prices, more for small
            if cl:
                last = cl[-1]
                if last >= 1000:    fmt = "{:,.0f}"
                elif last >= 10:    fmt = "{:,.2f}"
                elif last >= 1:     fmt = "{:,.3f}"
                elif last >= 0.1:   fmt = "{:,.4f}"
                elif last >= 0.01:  fmt = "{:,.5f}"
                elif last >= 0.001: fmt = "{:,.6f}"
                else:               fmt = "{:,.8f}"
                # Shrink font for very long tick labels (e.g. PEPE 0.00001234)
                tick_fs = 6.5 if last < 0.001 else 7.5
                self.ax_p.set_yticklabels([fmt.format(t) for t in price_ticks],
                                           fontsize=tick_fs, color=C_AX)

        # Only call legend() when labelled artists exist — avoids "No artists
        # with labels" UserWarning that spams the console every chart redraw.
        _p_handles, _p_labels = self.ax_p.get_legend_handles_labels()
        if _p_handles:
            self.ax_p.legend(loc="upper left", fontsize=7.5, facecolor=BG2,
                             edgecolor=SEP, labelcolor=C_AX, framealpha=0.92,
                             ncol=2, handlelength=1.8, borderpad=0.5)

        # RSI — single-pass O(n) via rsi_series(), then slice to visible window
        if self._last_candles:
            full_cl  = [c["close"] for c in self._last_candles]
            zoom_    = getattr(self, "_chart_zoom",  60)
            offset_  = getattr(self, "_chart_offset", 0)
            total_   = len(full_cl)
            end_     = total_ - offset_
            start_   = max(0, end_ - zoom_)
            rsi_full = rsi_series(full_cl)   # O(n) — replaces O(n²) loop
            rsi_v    = rsi_full[start_:end_]
            if len(rsi_v) != n:
                rsi_v = rsi_series(cl)[-n:]  # fallback
        else:
            rsi_v = rsi_series(cl)[-n:]
        self.ax_r.plot(xs, rsi_v, color=self.colour, linewidth=1.2)
        self.ax_r.axhline(70, color=RED,   lw=0.7, ls="--", alpha=0.7)
        self.ax_r.axhline(50, color=MUTED, lw=0.4, ls="-",  alpha=0.35)
        self.ax_r.axhline(30, color=GREEN, lw=0.7, ls="--", alpha=0.7)
        self.ax_r.fill_between(xs, rsi_v, 70, where=[v > 70 for v in rsi_v], color=RED,   alpha=0.1)
        self.ax_r.fill_between(xs, rsi_v, 30, where=[v < 30 for v in rsi_v], color=GREEN, alpha=0.1)
        self.ax_r.set_ylim(0, 100); self.ax_r.set_yticks([30, 50, 70])
        self.ax_r.yaxis.tick_right()
        if rsi_v:
            rv = rsi_v[-1]
            rc = RED if rv > 70 else (GREEN if rv < 30 else C_AX)
            self.ax_r.text(0.99, 0.82, f"RSI  {rv:.1f}", transform=self.ax_r.transAxes,
                           color=rc, fontsize=8, ha="right", fontweight="bold")

        # MACD — histogram bars + fast/slow lines + crossover markers
        if signals and signals.get("macd_hist"):
            mh_full  = list(signals["macd_hist"])
            ml_full  = list(signals.get("macd_line",   []))
            ms_full  = list(signals.get("macd_signal", []))
            # Derive window from the histogram array itself (same candles as _draw input)
            total_full = len(mh_full)
            zoom   = getattr(self, "_chart_zoom",   60)
            offset = getattr(self, "_chart_offset",  0)
            end_i  = max(0, total_full - offset)
            start_i= max(0, end_i - zoom)

            def _slice_series(s):
                if len(s) >= total_full:
                    sliced = s[start_i:end_i]
                else:
                    sliced = s
                if len(sliced) < n: sliced = [0] * (n - len(sliced)) + sliced
                elif len(sliced) > n: sliced = sliced[-n:]
                return sliced

            mh = _slice_series(mh_full)
            ml = _slice_series(ml_full)
            ms = _slice_series(ms_full)

            # Histogram bars (dimmed so lines stand out)
            self.ax_m.bar(xs, mh, color=[C_UP if v >= 0 else C_DOWN for v in mh],
                          width=0.7, alpha=0.45)
            self.ax_m.axhline(0, color=SEP2, lw=0.6)

            # MACD line (fast) and Signal line (slow)
            if any(v != 0 for v in ml):
                self.ax_m.plot(xs, ml, color=CYAN,   linewidth=1.3, alpha=0.95, label="MACD")
            if any(v != 0 for v in ms):
                self.ax_m.plot(xs, ms, color=ORANGE, linewidth=1.3, alpha=0.95, label="Signal")

            # Crossover markers — circles where MACD crosses the signal line
            for i in range(1, len(ml)):
                prev_diff = ml[i-1] - ms[i-1]
                curr_diff = ml[i]   - ms[i]
                if prev_diff <= 0 < curr_diff:   # bullish cross (MACD crosses above signal)
                    self.ax_m.scatter(i, ml[i], color=GREEN, s=28, zorder=5, alpha=0.95)
                elif prev_diff >= 0 > curr_diff: # bearish cross (MACD crosses below signal)
                    self.ax_m.scatter(i, ml[i], color=RED,   s=28, zorder=5, alpha=0.95)

            # Live MACD value label
            if ml and ms:
                mv_now = ml[-1]; sv_now = ms[-1]
                mc = CYAN if mv_now >= sv_now else ORANGE
                macd_str = (f"{mv_now:+.2e}" if abs(mv_now) < 0.0001 and mv_now != 0
                            else f"{mv_now:+.4f}")
                self.ax_m.text(0.99, 0.82, f"MACD  {macd_str}",
                               transform=self.ax_m.transAxes,
                               color=mc, fontsize=7.5, ha="right", fontweight="bold")

        # MACD panel label + TF on the left
        tf_label = getattr(self, "_chart_tf", "Min5")
        tf_short = tf_label.replace("Min","").replace("Hour","h").replace("Day","d")
        self.ax_m.text(0.01, 0.82, f"MACD · {tf_short}",
                       transform=self.ax_m.transAxes, color=C_AX, fontsize=7)
        # Guard: only show legend when labelled MACD artists exist
        _m_handles, _m_labels = self.ax_m.get_legend_handles_labels()
        if _m_handles:
            self.ax_m.legend(loc="upper left", fontsize=6.5, facecolor=BG2,
                             edgecolor=SEP, labelcolor=C_AX, framealpha=0.85,
                             handlelength=1.4, borderpad=0.4, ncol=2)
        self.ax_m.yaxis.tick_right(); self.ax_m.set_xticks([])

        # ── Time axis: show on MACD panel (bottom), hide on price + RSI ───────
        plt.setp(self.ax_p.get_xticklabels(), visible=False)
        plt.setp(self.ax_r.get_xticklabels(), visible=False)
        self.ax_m.set_xticks(tick_xs)
        self.ax_m.set_xticklabels(tick_lbls, fontsize=7, color=C_AX,
                                   rotation=0, ha="center", multialignment="center")
        self.ax_m.tick_params(axis="x", length=3, color=C_GRID)
        try:
            self.canvas.draw_idle()
        except (AttributeError, RuntimeError) as e:
            _file_logger.debug(f"Canvas draw failed (likely destroyed): {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  OPEN POSITIONS DOCK  — persistent bar shown on every tab
# ══════════════════════════════════════════════════════════════════════════════
class PositionsDock:
    """Slim bar at the bottom of the window showing all open positions."""

    def __init__(self, parent, state: BotState, on_close=None, on_hedge=None):
        self.state    = state
        self.fee_taker = 0.0006   # updated by HermesBotApp when live fee is fetched
        self.fee_maker = 0.0004   # updated by HermesBotApp when live fee is fetched
        self.frames   = {}   # pos_id -> frame widget
        self.on_close = on_close   # callback(pid) to manually close a position
        self.on_hedge = on_hedge   # callback(pid) to manually open hedge

        self.outer = tk.Frame(parent, bg=BG2, height=155)
        self.outer.pack(fill="x", side="bottom")
        self.outer.pack_propagate(False)
        tk.Frame(self.outer, bg=CYAN, height=1).pack(fill="x")

        # Header strip
        hdr = tk.Frame(self.outer, bg=BG3, height=20)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  OPEN POSITIONS", font=("Consolas", 8, "bold"),
                 fg=MUTED, bg=BG3, anchor="w").pack(side="left")
        self.count_lbl = tk.Label(hdr, text="0 open", font=("Consolas", 8, "bold"),
                                   fg=DIM, bg=BG3)
        self.count_lbl.pack(side="right", padx=8)

        # Scrollable row of position cards
        self.scroll_frame = tk.Frame(self.outer, bg=BG2)
        self.scroll_frame.pack(fill="both", expand=True, padx=4, pady=1)

        self.no_pos_lbl = tk.Label(self.scroll_frame,
                                    text="No open positions",
                                    font=("Consolas", 9), fg=DIM, bg=BG2)
        self.no_pos_lbl.pack(side="left", padx=12, pady=4)

    def refresh(self, current_prices: dict):
        # Remove closed positions
        for pid in list(self.frames.keys()):
            if pid not in self.state.positions:
                self.frames[pid].destroy()
                del self.frames[pid]

        positions = self.state.positions
        if not positions:
            self.no_pos_lbl.pack(side="left", padx=12, pady=4)
            self.count_lbl.config(text="0 open")
            return
        self.no_pos_lbl.pack_forget()
        self.count_lbl.config(text=f"{len(positions)} open")

        def _fp(v):
            """Format price — more decimals for small values."""
            if v < 0.0001:  return f"${v:.8f}"
            if v < 0.001:   return f"${v:.7f}"
            if v < 0.1:     return f"${v:.5f}"
            if v < 10:      return f"${v:.4f}"
            if v >= 1000:   return f"${v:,.1f}"
            return f"${v:,.2f}"

        for pid, pos in positions.items():
            px = current_prices.get(pos.symbol, pos.entry_price)
            if pos.direction == "LONG":
                raw_chg = (px - pos.entry_price) / pos.entry_price
            else:
                raw_chg = (pos.entry_price - px) / pos.entry_price
            price_pct  = raw_chg * 100                      # actual price move %
            margin_pct = raw_chg * pos.leverage * 100       # leveraged margin return %
            unr        = raw_chg * pos.leverage * pos.margin # $ PnL on margin
            sym  = pair_label(pos.symbol)
            dcol = GREEN if pos.direction == "LONG" else RED
            pct  = margin_pct  # keep compat ref
            pcol = GREEN if unr >= 0 else RED
            hedge_tag = " [H]" if pos.hedge_of else ""

            if pid not in self.frames:
                f = tk.Frame(self.scroll_frame, bg=BG3, padx=8, pady=2,
                             highlightthickness=1, highlightbackground=SEP)
                f.pack(side="left", padx=(0, 6))

                # Row 0 — symbol | direction | unrealised pnl
                f._sym = tk.Label(f, font=("Consolas", 9, "bold"), bg=BG3)
                f._dir = tk.Label(f, font=("Consolas", 9, "bold"), bg=BG3)
                f._unr = tk.Label(f, font=("Consolas", 10, "bold"), bg=BG3)
                f._sym.grid(row=0, column=0, sticky="w")
                f._dir.grid(row=0, column=1, padx=(6,0), sticky="w")
                f._unr.grid(row=0, column=2, rowspan=2, padx=(14,0), sticky="e")

                # Row 1 — entry price (margin shown inline)
                f._epx_lbl = tk.Label(f, text="Entry", font=("Consolas", 7),
                                       fg=MUTED, bg=BG3)
                f._epx = tk.Label(f, font=("Consolas", 8, "bold"), fg=SUB, bg=BG3)
                f._epx_lbl.grid(row=1, column=0, sticky="w")
                f._epx.grid(row=1, column=1, padx=(6,0), sticky="w")

                # Row 2 — margin
                f._mg_lbl = tk.Label(f, text="Margin", font=("Consolas", 7), fg=MUTED, bg=BG3)
                f._mg     = tk.Label(f, font=("Consolas", 7, "bold"), fg=MUTED, bg=BG3)
                f._mg_lbl.grid(row=2, column=0, sticky="w")
                f._mg.grid(row=2, column=1, padx=(6,0), sticky="w")

                # Row 3 — current price + time open
                f._cur_lbl = tk.Label(f, font=("Consolas", 7), fg=CYAN, bg=BG3, justify="left")
                f._cur_lbl.grid(row=3, column=0, columnspan=2, sticky="w")
                # fee label on right
                f._fee_lbl = tk.Label(f, font=("Consolas", 7), fg=AMBER, bg=BG3)
                f._fee_lbl.grid(row=3, column=2, sticky="e")

                # Row 4 — TP | SL | LIQ
                f._levels = tk.Label(f, font=("Consolas", 7), bg=BG3, justify="left")
                f._levels.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0,0))

                # Row 4 — Close and Hedge buttons
                btn_frame = tk.Frame(f, bg=BG3)
                btn_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(3,0))

                _pid = pid  # capture for lambda
                close_btn = tk.Button(
                    btn_frame, text="✕ Close",
                    font=("Consolas", 8, "bold"),
                    bg="#3d0a0a", fg=RED,
                    activebackground="#5a1010", activeforeground=RED,
                    relief="flat", padx=8, pady=2, cursor="hand2",
                    command=lambda p=_pid: self._manual_close(p))
                close_btn.pack(side="left", padx=(0,4))

                hedge_btn = tk.Button(
                    btn_frame, text="⇄ Hedge",
                    font=("Consolas", 8, "bold"),
                    bg="#1a2a0a", fg=AMBER,
                    activebackground="#2a3d10", activeforeground=AMBER,
                    relief="flat", padx=8, pady=2, cursor="hand2",
                    command=lambda p=_pid: self._manual_hedge(p))
                hedge_btn.pack(side="left")

                self.frames[pid] = f

            frm = self.frames[pid]
            frm._sym.config(text=f"{sym}{hedge_tag}",
                             fg=PAIR_COL.get(pos.symbol, CYAN))
            frm._dir.config(text=f"{pos.direction} {pos.leverage}x", fg=dcol)
            frm._unr.config(
                text=(f"{'+'if unr>=0 else '-'}${abs(unr):.2f}  {margin_pct:+.1f}%"),
                fg=pcol, justify="right")
            frm._epx.config(text=_fp(pos.entry_price))
            frm._mg.config(text=f"${pos.margin:.2f}")

            # Current price + time open
            try:
                opened = datetime.fromisoformat(pos.opened_at.replace("Z","+00:00"))
                secs   = int((datetime.now(timezone.utc) - opened).total_seconds())
                if secs < 3600:
                    dur_str = f"{secs//60}m {secs%60}s"
                else:
                    dur_str = f"{secs//3600}h {(secs%3600)//60}m"
            except Exception:
                dur_str = "—"
            fee_cost = round(pos.size_usdt * (getattr(self, "_fee_maker", 0.0004) + getattr(self, "_fee_taker", 0.0006)), 4)  # open leg maker + close leg taker
            if hasattr(frm, "_cur_lbl"):
                frm._cur_lbl.config(text=f"Now {_fp(px)}  {dur_str}")
            if hasattr(frm, "_fee_lbl"):
                frm._fee_lbl.config(text=f"fee≈${fee_cost:.3f}")
            # Colour-coded TP / SL / LIQ on one line
            frm._levels.config(
                text=f"TP {_fp(pos.take_profit)}   SL {_fp(pos.stop_loss)}   LIQ {_fp(pos.liq_price)}",
                fg=SUB)

    def _manual_close(self, pid):
        if self.on_close:
            self.on_close(pid)

    def _manual_hedge(self, pid):
        if self.on_hedge:
            self.on_hedge(pid)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
class HermesBotApp:
    def __init__(self, root):
        self.root = root
        root.title(f"Pacbot  {BOT_VERSION}  —  MEXC Futures  [TUNED SIGNALS]")
        root.configure(bg=BG)
        # Use 85% of screen size on first launch, but allow smaller
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w = max(1000, min(1400, int(sw * 0.85)))
        h = max(650,  min(900,  int(sh * 0.85)))
        root.geometry(f"{w}x{h}")
        root.minsize(900, 600)

        self.bot_running   = False
        self.bot_thread    = None
        self.state         = BotState()
        self._stop_event   = threading.Event()
        self._positions_lock = threading.RLock()  # guards all state.positions reads/writes
        self.chart_panels  = {}
        self._last_claude_call  = 0
        self._claude_tokens     = 0   # total tokens used this session
        self._claude_cost       = 0.0 # estimated $ cost this session
        self._claude_calls      = 0   # number of calls this session
        self._bot_start_time    = None
        self._cycles_run        = 0
        self._last_signal_time  = None
        self._last_signal_pair  = None
        self._last_signal_dir   = None
        self._hold_streak       = 0   # consecutive HOLD cycles (kept for compat)
        self._adaptive_thr      = None  # None = use config value (kept for compat)
        self._adaptive_engine   = AdaptiveTriggerEngine()
        self._fee_maker         = MAKER_FEE_PCT   # MEXC Futures API maker fee (0.04%, effective May 1 2026)
        self._fee_taker         = TAKER_FEE_PCT   # MEXC Futures taker fee
        # ── Per-session trade CSV (for A/B testing — see TUNED_THRESHOLD_FLOOR test) ──
        _sessions_dir = _HOME / "sessions"
        try:
            _sessions_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self._session_csv_path = str(_sessions_dir / (
            f"session_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{BOT_VERSION}.csv"))
        self._session_csv_header_written = False
        self._dead_pairs     = set()
        self._live_balance   = None   # cached MEXC account data
        self._balance_fetch  = 0      # timestamp of last fetch  # pairs that returned code 1001
        self._ws_manager     = None   # WebSocket manager instance
        self._price_history  = {}     # pid -> list of (timestamp, price) for velocity tracking
        self._price_peak     = {}     # pid -> best price seen (for near-TP and stale checks)
        self._ai_trade_log   = {}     # pid -> list of {time, event, reason, col} dicts
        self._stale_checked  = set()  # pids already sent to stale check this hour
        self._pair_cooldown  = {}     # pair -> timestamp of last loss (cooldown tracking)
        self._h1_trends      = {}     # pair -> "BULL"/"BEAR" from hourly TF
        self._h1_last_fetch  = 0      # last time h1 trends were refreshed
        self._h4_trends      = {}     # pair -> "BULL"/"BEAR" from 4-hour TF  #H4-FILTER
        self._h4_last_fetch  = 0      # last time h4 trends were refreshed    #H4-FILTER
        self._losing_streak  = 0      # consecutive losses this session
        self._peak_leverage  = None   # original leverage before streak reduction
        # ── Indicator cache: avoids re-computing signals when candles unchanged ───
        self._sig_cache      = {}     # pair -> {"hash": int, "sig": dict}
        # ── Config cache: avoid repeated disk I/O for config access ─────────────────
        self._load_config    = load_config  # cache the function reference
        config = self._load_config()
        self._trend_scan_interval = config.get("trend_scan_interval_sec", 20)
        self._entry_scan_interval = config.get("entry_scan_interval_sec", 10)
        # ── Chart throttle: track last redraw time per panel ──────────────────────
        self._chart_last_draw = {}    # pair -> float (epoch of last cp.update call)
        # ── Thread safety locks ───────────────────────────────────────────────────
        self._state_lock = threading.RLock()    # Protects state.positions, state.balance, etc.
        self._price_lock = threading.RLock()    # Protects current_prices, pair_signals, pair_candles
        self._history_lock = threading.RLock()  # Protects _price_history, _price_peak
        self._ai_log_lock = threading.RLock()   # Protects _ai_trade_log
        self._cooldown_lock = threading.RLock() # Protects _pair_cooldown, _stale_checked
        self._cache_lock = threading.RLock()    # Protects _sig_cache, _chart_last_draw
        # ── Kelly sizing state ────────────────────────────────────────────────────
        self._kelly_wins     = 0      # running win count for Kelly edge estimate
        self._kelly_losses   = 0      # running loss count
        self._kelly_avg_win  = 0.0    # running average win in $
        self._kelly_avg_loss = 0.0    # running average loss in $
        # ── Position monitor batching: serialise Claude calls across all monitors ──
        # Prevents N positions firing N simultaneous API calls on the same cycle.
        self._claude_gate    = threading.Semaphore(1)  # only 1 Claude call at a time
        self._claude_gate_ts = 0.0                     # time of last release
        # ── SCALE v2.4-#1: fixed thread pool for pair scanning ────────────────────
        # Created once, reused every cycle — avoids per-cycle thread create/destroy.
        # 12 workers: enough for 30 pairs without overwhelming MEXC REST or the GIL.
        self._scan_executor  = ThreadPoolExecutor(max_workers=12,
                                                   thread_name_prefix="scan")
        # ── SCALE v2.4-#4: staggered H1/H4 fetch round-robin indices ─────────────
        self._h1_fetch_idx   = 0   # which pair fetches H1 this cycle
        self._h4_fetch_idx   = 0   # which pair fetches H4 this cycle
        self.pair_candles  = {p: [] for p in PAIRS}
        self.pair_signals  = {p: None for p in PAIRS}
        self._chart_timer  = None
        self._dock_timer   = None
        self.current_prices= {p: 0.0 for p in PAIRS}

        self._style()
        self._build_ui()
        self._load_keys()
        self._log_event(f"Pacbot {BOT_VERSION}  ·  MEXC Futures  ·  WebSocket ready.  Press START BOT to begin.", CYAN)
        self._log("Select ● Paper or ⚡ Live! in the MODE section above.", DIM)
        # Set initial overnight icon state
        self.root.after(100, lambda: self._apply_overnight_ui(self.overnight_var.get(), forced=False))
        self._log("─" * 55, DIM)
        self._log("Optimised defaults loaded:", CYAN)
        self._log("  Signal threshold : 4.5/9  (clear majority of 9 indicators must agree)", DIM)
        self._log("  Leverage         : 10x    (survives 10% adverse move)", DIM)
        self._log("  Stop loss        : 0.8%   |  Take profit: 2.0%  (1:2.5 R/R)", DIM)
        self._log("  Max trades       : 2      |  Hedge at: -3.0% drawdown", DIM)
        self._log("  Stack longs at   : 6.0/9  (only on high-confidence signals)", DIM)
        self._log("  Candle TF        : Min5 trend + Min1 entry (dual TF)  |  Scan: every 30s", DIM)
        self._log("  Scans all 10 pairs — trades the best signal each cycle", DIM)
        self._log("  Pairs: BTC ETH SOL XRP DOGE XAU NAS100 SPX EUR NVDA", DIM)
        self._log("─" * 55, DIM)
        self._log("⚠  Paper mode — adjust leverage/margin before going live", AMBER)
        # Delay first chart load by 1.5s to let UI fully render
        self.root.after(1500, self._initial_load)
        self._chart_cycle()
        self._dock_cycle()

    # ── STYLE ──────────────────────────────────────────────────────────────────
    def _style(self):
        s = ttk.Style(); s.theme_use("clam")
        s.configure("D.TCombobox", fieldbackground=BG3, background=BG3,
                    foreground=TEXT, selectbackground=BG3, selectforeground=TEXT,
                    bordercolor=SEP, arrowcolor=CYAN, font=FM, padding=4)
        s.map("D.TCombobox", fieldbackground=[("readonly", BG3)],
              foreground=[("readonly", TEXT)])
        s.configure("Vertical.TScrollbar", background=BG3, troughcolor=BG,
                    bordercolor=SEP, arrowcolor=CYAN)

    # ── TOP-LEVEL LAYOUT ───────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG2)
        hdr.pack(fill="x")
        # Thicker gradient-like top accent bar: 2px CYAN + 1px darker
        tk.Frame(hdr, bg=CYAN,  height=2).pack(fill="x")
        tk.Frame(hdr, bg="#0e7490", height=1).pack(fill="x")
        hi = tk.Frame(hdr, bg=BG2, pady=7)
        hi.pack(fill="x", padx=14)

        # ── Pacbot icon: Pac-Man emoji rendered on a tiny canvas ──────────────
        icon_cv = tk.Canvas(hi, width=28, height=28, bg=BG2,
                            highlightthickness=0)
        icon_cv.pack(side="left", padx=(0, 8))
        # Outer glow ring
        icon_cv.create_oval(1, 1, 27, 27, fill="#0e1e2f", outline="#164e63", width=1)
        # Pac-Man body (yellow arc, pie slice for mouth)
        icon_cv.create_arc(3, 3, 25, 25, start=30, extent=300,
                           fill="#fbbf24", outline="#f59e0b", width=1, style="pieslice")
        # Eye
        icon_cv.create_oval(13, 6, 17, 10, fill=BG2, outline="")

        # ── Brand wordmark ────────────────────────────────────────────────────
        tk.Label(hi, text="PAC", font=("Consolas", 15, "bold"),
                 fg=CYAN,  bg=BG2).pack(side="left")
        tk.Label(hi, text="BOT", font=("Consolas", 15, "bold"),
                 fg=TEXT,  bg=BG2).pack(side="left")

        # Version + subtitle pill
        pill = tk.Frame(hi, bg="#0e2233", padx=6, pady=2,
                        highlightthickness=1, highlightbackground="#164e63")
        pill.pack(side="left", padx=(8, 0))
        tk.Label(pill, text=f"{BOT_VERSION}  ·  MEXC Futures",
                 font=("Consolas", 8), fg=CYAN, bg="#0e2233").pack()
        # Multi-pair price ticker — horizontal scrollable so it fits any window width
        ticker_outer = tk.Frame(hi, bg=BG2)
        ticker_outer.pack(side="left", padx=6, fill="x", expand=True)
        ticker_canvas = tk.Canvas(ticker_outer, bg=BG2, highlightthickness=0, height=22)
        ticker_canvas.pack(fill="x", expand=True)
        ticker_frame = tk.Frame(ticker_canvas, bg=BG2)
        ticker_frame_id = ticker_canvas.create_window((0, 0), window=ticker_frame, anchor="nw")
        def _on_ticker_resize(e):
            ticker_canvas.configure(scrollregion=ticker_canvas.bbox("all"))
        ticker_frame.bind("<Configure>", _on_ticker_resize)
        self.price_lbls = {}
        for _p in PAIRS:
            _sym = pair_label(_p)
            _col = PAIR_COL[_p]
            _lf  = tk.Frame(ticker_frame, bg=BG2)
            _lf.pack(side="left", padx=(0, 8))
            tk.Label(_lf, text=_sym, font=("Consolas", 7, "bold"), fg=_col, bg=BG2).pack(side="left")
            lbl = tk.Label(_lf, text=" —", font=("Consolas", 7), fg=SUB, bg=BG2)
            lbl.pack(side="left")
            self.price_lbls[_p] = lbl
        self.price_lbl = tk.Label(hi, text="", font=FM, fg=CYAN, bg=BG2)  # compat
        self.mode_lbl = tk.Label(hi, text="● PAPER MODE — no real orders",
                                   font=("Consolas", 10, "bold"), fg=AMBER, bg=BG2,
                                   padx=10)
        self.mode_lbl.pack(side="right", padx=4)
        self.overnight_lbl = tk.Label(hi, text="", font=("Consolas", 9, "bold"),
                                       fg=TEAL, bg=BG2, padx=6)
        self.overnight_lbl.pack(side="right", padx=2)
        self.status_dot = tk.Label(hi, text="●", font=FMB, fg=DIM, bg=BG2)
        self.status_dot.pack(side="right", padx=4)

        # Positions dock — persistent across all views
        self.dock = PositionsDock(self.root, self.state,
                                   on_close=self._manual_close_position,
                                   on_hedge=self._manual_hedge_position)

        # Body
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=BG, width=290)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.pack_propagate(False); left.grid_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(2, weight=1); right.columnconfigure(0, weight=1)

        self._build_sidebar(left)
        self._build_metrics(right)
        self._build_tabs(right)

    # ── MOUSE-WHEEL SCROLL HELPER ──────────────────────────────────────────────
    def _bind_mousewheel(self, canvas, widget):
        """Recursively bind mouse-wheel on *widget* and all descendants to scroll *canvas*.
        Skips widgets already bound to this canvas to avoid redundant bind accumulation."""
        tag = f"_mw_bound_{id(canvas)}"
        def _scroll(e):
            if e.num == 4:
                canvas.yview_scroll(-1, "units")
            elif e.num == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        for w in [widget] + list(self._all_children(widget)):
            if getattr(w, tag, False):
                continue  # already bound to this canvas
            try:
                w.bind("<MouseWheel>", _scroll, add="+")
                w.bind("<Button-4>",   _scroll, add="+")
                w.bind("<Button-5>",   _scroll, add="+")
                setattr(w, tag, True)
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)

    def _all_children(self, widget):
        """Yield all descendant widgets recursively."""
        for child in widget.winfo_children():
            yield child
            yield from self._all_children(child)

    def _rebind_mousewheel(self, canvas, widget):
        """Re-bind after new children are added — only binds new untagged widgets."""
        self._bind_mousewheel(canvas, widget)

    # ── SIDEBAR ────────────────────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        cv = tk.Canvas(parent, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(fill="both", expand=True)
        inner = tk.Frame(cv, bg=BG)
        wid = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: (cv.configure(scrollregion=cv.bbox("all")),
                                              cv.itemconfig(wid, width=e.width),
                                              self._rebind_mousewheel(cv, inner)))
        cv.bind("<Configure>", lambda e: cv.itemconfig(wid, width=e.width))
        self._sidebar_cv = cv
        self._sidebar_inner = inner
        self._sidebar_content(inner)
        self._bind_mousewheel(cv, inner)

    def _section(self, p, title, accent=CYAN):
        o = tk.Frame(p, bg=BG2, highlightthickness=1, highlightbackground=SEP)
        o.pack(fill="x", pady=(0, 7))
        hrow = tk.Frame(o, bg=BG2)
        hrow.pack(fill="x")
        tk.Frame(hrow, bg=accent, width=3).pack(side="left", fill="y")
        tk.Label(hrow, text=f" {title}", font=("Consolas", 8, "bold"), fg=accent,
                 bg=BG2, anchor="w", padx=8, pady=6).pack(side="left", fill="x")
        inn = tk.Frame(o, bg=BG2, padx=10, pady=6)
        inn.pack(fill="x")
        return inn

    def _lrow(self, p, label, w=13):
        r = tk.Frame(p, bg=BG2); r.pack(fill="x", pady=2)
        tk.Label(r, text=label, font=("Consolas", 8), fg=SUB, bg=BG2,
                 width=w, anchor="w").pack(side="left", padx=(2,0))
        return r

    def _combo(self, p, vals, default):
        cb = ttk.Combobox(p, values=vals, state="readonly", width=16,
                          style="D.TCombobox", font=FM)
        cb.set(default); cb.pack(side="left", fill="x", expand=True)
        return cb

    def _entry(self, p, default="", show=None):
        e = tk.Entry(p, bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat",
                     font=FM, width=16, highlightthickness=1,
                     highlightbackground=SEP, highlightcolor=CYAN)
        if show: e.config(show=show)
        e.insert(0, default); e.pack(side="left", fill="x", expand=True)
        return e

    def _sidebar_content(self, p):
        # ── Mode ──────────────────────────────────────────────────────────────
        s0 = self._section(p, "MODE", AMBER)
        self.dry_var = tk.BooleanVar(value=True)
        rf = self._lrow(s0, "Mode")
        tk.Radiobutton(rf, text="● Paper", variable=self.dry_var, value=True,
                       bg=BG2, fg=GREEN, selectcolor=BG3, activebackground=BG2,
                       font=FMS, command=self._on_mode).pack(side="left")
        tk.Radiobutton(rf, text="⚡ Live!", variable=self.dry_var, value=False,
                       bg=BG2, fg=RED, selectcolor=BG3, activebackground=BG2,
                       font=FMS, command=self._on_mode).pack(side="left", padx=8)

        # ── Claude ────────────────────────────────────────────────────────────
        claude_outer = tk.Frame(p, bg=PURPLE, padx=2, pady=2)
        claude_outer.pack(fill="x", pady=(0, 8))
        ci = tk.Frame(claude_outer, bg=BG2)
        ci.pack(fill="x")
        tk.Frame(ci, bg=PURPLE, height=2).pack(fill="x")
        th = tk.Frame(ci, bg="#120a22")
        th.pack(fill="x")
        tk.Label(th, text="  🤖  CLAUDE AI", font=("Consolas", 9, "bold"),
                 fg=PURPLE, bg="#120a22", pady=6, anchor="w").pack(side="left")
        tk.Label(th, text="optional", font=FMS, fg=MUTED, bg="#120a22").pack(side="right", padx=8)
        ci2 = tk.Frame(ci, bg=BG2, padx=10, pady=6)
        ci2.pack(fill="x")

        self.claude_enabled = tk.BooleanVar(value=False)
        self.claude_toggle  = tk.Button(ci2,
            text="  OFF  —  click to enable",
            font=("Consolas", 9, "bold"), bg=BG3, fg=MUTED,
            relief="flat", cursor="hand2", pady=5, anchor="w",
            command=self._toggle_claude)
        self.claude_toggle.pack(fill="x", pady=(0, 3))

        # Claude role badges
        role_frame = tk.Frame(ci2, bg=BG2)
        role_frame.pack(fill="x", pady=(0, 4))
        for role, col in [("VETO", RED), ("BOOST", CYAN), ("DYN SL/TP", PURPLE)]:
            tk.Label(role_frame, text=role, font=("Consolas", 7, "bold"),
                     fg=col, bg="#0d0a14", padx=5, pady=2,
                     relief="flat").pack(side="left", padx=(0, 3))

        # Cost tracker
        cost_frame = tk.Frame(ci2, bg=BG2)
        cost_frame.pack(fill="x", pady=(0, 4))
        tk.Label(cost_frame, text="Session cost:",
                 font=("Consolas", 8), fg=MUTED, bg=BG2).pack(side="left")
        self._cost_lbl = tk.Label(cost_frame, text="$0.0000",
                                   font=("Consolas", 8, "bold"), fg=DIM, bg=BG2)
        self._cost_lbl.pack(side="left", padx=(4, 0))
        self._calls_lbl = tk.Label(cost_frame, text="0 calls",
                                    font=("Consolas", 8), fg=DIM, bg=BG2)
        self._calls_lbl.pack(side="right")

        def _open_console(_=None):
            import webbrowser
            webbrowser.open("https://console.anthropic.com/settings/keys")
        lnk = tk.Label(ci2, text="→ console.anthropic.com/settings/keys",
                       font=("Consolas", 8), fg=CYAN, bg=BG2, cursor="hand2", anchor="w")
        lnk.pack(fill="x")
        lnk.bind("<Button-1>", _open_console)
        lnk.bind("<Enter>", lambda e: lnk.config(fg=TEXT))
        lnk.bind("<Leave>", lambda e: lnk.config(fg=CYAN))

        tk.Label(ci2, text="Requires $5 credit to activate API",
                 font=("Consolas", 8), fg=DIM, bg=BG2, anchor="w").pack(fill="x", pady=(0, 6))

        kr = tk.Frame(ci2, bg=BG2); kr.pack(fill="x", pady=(0, 4))
        self.claude_entry = tk.Entry(kr, bg="#0d0818", fg=PURPLE, insertbackground=PURPLE,
                                      relief="flat", font=FM, show="*",
                                      highlightthickness=1, highlightbackground=PURPLE,
                                      highlightcolor="#c084fc", state="disabled")
        self.claude_entry.pack(side="left", fill="x", expand=True, ipady=5)

        self._claude_show = False
        def _tog_show():
            self._claude_show = not self._claude_show
            self.claude_entry.config(show="" if self._claude_show else "*")
            self._show_btn.config(text="🙈" if self._claude_show else "👁")
        self._show_btn = tk.Button(kr, text="👁", command=_tog_show,
                                    bg="#120a22", fg=PURPLE, relief="flat",
                                    font=FM, cursor="hand2", padx=6,
                                    state="disabled", activebackground=BG3)
        self._show_btn.pack(side="left", padx=(3, 0), ipady=5)

        tr = tk.Frame(ci2, bg=BG2); tr.pack(fill="x")
        self.claude_status = tk.Label(tr, text="OFF — local signals only",
                                       font=FMS, fg=MUTED, bg=BG2, anchor="w")
        self.claude_status.pack(side="left", fill="x", expand=True)
        self._test_btn = tk.Button(tr, text="Test ▶", command=self._test_claude,
                                    bg=BG3, fg=MUTED, relief="flat", font=FMS,
                                    cursor="hand2", padx=8, pady=3,
                                    state="disabled", activebackground=BG3)
        self._test_btn.pack(side="right")

        # ── MEXC Keys ─────────────────────────────────────────────────────────
        s2 = self._section(p, "MEXC API KEYS  (live trading only)", CYAN)
        tk.Label(s2, text="mexc.com → Profile → API Management\nEnable Contract Trading — NO withdrawals",
                 font=("Consolas", 8), fg=DIM, bg=BG2, justify="left",
                 wraplength=250).pack(fill="x", pady=(0, 6))
        self.mexc_key_e = self._entry(self._lrow(s2, "API key"), "")
        self.mexc_sec_e = self._entry(self._lrow(s2, "Secret"),  "", show="*")

        # ── Trade Config ──────────────────────────────────────────────────────
        s3 = self._section(p, "TRADE CONFIG", CYAN)
        self.pair_cb = self._combo(self._lrow(s3, "Pair"), PAIRS, "BTC_USDT")
        self.pair_cb.bind("<<ComboboxSelected>>", self._on_pair)

        self.lev_cb  = self._combo(self._lrow(s3, "Leverage"),
            self._lev_opts("BTC_USDT"), "10x")
        self.lev_cb.bind("<<ComboboxSelected>>", self._on_lev)
        self.lev_warn_inline = tk.Label(s3, text="10x: 10% move = 100% loss",
            font=("Consolas", 8), fg=AMBER, bg=BG2, anchor="w", wraplength=240)
        self.lev_warn_inline.pack(fill="x", pady=(0, 3))

        self.margin_e= self._entry(self._lrow(s3, "Margin USDT"), "50")
        self.margin_e.bind("<FocusOut>", self._on_margin_change)
        self.margin_e.bind("<Return>",   self._on_margin_change)
        # Recommendation label — updated whenever margin changes
        self.lev_rec_lbl = tk.Label(s3, text="Enter margin to get leverage recommendation",
            font=("Consolas", 8), fg=CYAN, bg=BG2, anchor="w", wraplength=240)
        self.lev_rec_lbl.pack(fill="x", pady=(0, 3))
        self._tf_lbl_var = tk.StringVar(value="Trend TF")
        self.tf_cb   = self._combo(self._lrow(s3, "Trend TF"),
            ["Min1","Min5","Min15","Min30","Min60","Hour4","Day1"], "Min5")
        self.tf_cb.bind("<<ComboboxSelected>>", lambda _: self._on_dual_tf())

        # Dual timeframe toggle
        dtf_row = tk.Frame(s3, bg=BG2); dtf_row.pack(fill="x", pady=(2,4))
        self.dual_tf_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dtf_row, text="Dual TF  (Min5 trend + Min1 entry)",
                       variable=self.dual_tf_var,
                       bg=BG2, fg=CYAN, selectcolor=BG3,
                       activebackground=BG2, font=("Consolas",8,"bold"),
                       command=self._on_dual_tf).pack(side="left")
        self._dtf_lbl = tk.Label(dtf_row, text="ON",
                                  font=("Consolas",8,"bold"), fg=CYAN, bg=BG2)
        self._dtf_lbl.pack(side="left", padx=(6,0))
        # Initialize dual TF UI state
        self.root.after(100, self._on_dual_tf)

        # ── v2.8-TUNED: Selective entry toggle ───────────────────────────────
        # ON  = apply the v2.8 entry-quality filters (confluence bonus, trigger
        #       gate, conviction gap) → fewer, higher-conviction trades.
        # OFF = original v2.7.5 entry behaviour → more (lower-quality) trades.
        sel_row = tk.Frame(s3, bg=BG2); sel_row.pack(fill="x", pady=(2,4))
        self._tuned_entry_var = tk.BooleanVar(value=TUNED_SELECTIVE_ENTRY_DEFAULT)
        tk.Checkbutton(sel_row, text="Selective entry  (v2.8 quality filters)",
                       variable=self._tuned_entry_var,
                       bg=BG2, fg=AMBER, selectcolor=BG3,
                       activebackground=BG2, font=("Consolas",8,"bold")
                       ).pack(side="left")
        self.int_cb  = self._combo(self._lrow(s3, "Scan interval"),
            ["1s","2s","3s","4s","5s","6s","7s","8s","9s",
             "10s","15s","20s","25s","30s","35s","40s","45s",
             "60s","90s","2 min","3 min","5 min","10 min"], "30s")
        self.int_cb.bind("<<ComboboxSelected>>", self._on_interval)
        self._ivl_hint = tk.Label(s3, text="",
            font=("Consolas", 8), fg=CYAN, bg=BG2, anchor="w", wraplength=240)
        self._ivl_hint.pack(fill="x", pady=(0, 3))
        self.sl_cb   = self._combo(self._lrow(s3, "Stop loss"),
            ["0.05%","0.08%","0.10%","0.12%","0.15%","0.18%","0.20%",
             "0.25%","0.30%","0.35%","0.40%","0.50%","0.60%","0.70%",
             "0.80%","0.90%","1.0%","1.5%","2.0%","2.5%","3.0%",
             "4.0%","5.0%","7.5%","10.0%","15.0%","20.0%"], "0.8%")
        self.tp_cb   = self._combo(self._lrow(s3, "Take profit"),
            ["0.05%","0.08%","0.10%","0.12%","0.15%","0.18%","0.20%",
             "0.25%","0.30%","0.35%","0.40%","0.50%","0.60%","0.70%",
             "0.80%","0.90%","1.0%","1.2%","1.5%","2.0%","2.5%","3.0%",
             "4.0%","5.0%","7.5%","10.0%","15.0%","20.0%","30.0%","50.0%"], "2.0%")
        self.thr_cb  = self._combo(self._lrow(s3, "Min signal"),
            ["2.0/9","3.0/9","3.5/9","4.0/9","4.5/9","5.0/9","5.5/9","6.0/9","7.0/9","8.0/9"], "4.5/9")

        # ── Multi-trade / Hedge ───────────────────────────────────────────────
        # ── Scan Pairs ───────────────────────────────────────────────────────────
        sp = self._section(p, "SCAN PAIRS", CYAN)
        tk.Label(sp, text="Toggle pairs to scan. Fewer = faster cycles.",
                 font=("Consolas", 8), fg=DIM, bg=BG2,
                 wraplength=250, justify="left").pack(fill="x", pady=(0, 6))

        self._pair_vars = {}
        grid = tk.Frame(sp, bg=BG2)
        grid.pack(fill="x")
        for i, pair in enumerate(PAIRS):
            sym = pair_label(pair)
            col = PAIR_COL.get(pair, CYAN)
            var = tk.BooleanVar(value=True)
            self._pair_vars[pair] = var
            cb = tk.Checkbutton(grid, text=sym, variable=var,
                                bg=BG2, fg=col, selectcolor=BG3,
                                activebackground=BG2, activeforeground=col,
                                font=("Consolas", 8, "bold"),
                                command=self._on_pair_toggle)
            cb.grid(row=i//3, column=i%3, sticky="w", padx=(0,6), pady=1)

        # Select all / none buttons
        btn_row = tk.Frame(sp, bg=BG2)
        btn_row.pack(fill="x", pady=(4,0))
        tk.Button(btn_row, text="All", font=("Consolas", 8),
                  bg=BG3, fg=CYAN, relief="flat", cursor="hand2",
                  command=lambda: self._set_all_pairs(True)).pack(side="left", padx=(0,4))
        tk.Button(btn_row, text="None", font=("Consolas", 8),
                  bg=BG3, fg=MUTED, relief="flat", cursor="hand2",
                  command=lambda: self._set_all_pairs(False)).pack(side="left", padx=(0,4))
        tk.Button(btn_row, text="Crypto only", font=("Consolas", 8),
                  bg=BG3, fg=AMBER, relief="flat", cursor="hand2",
                  command=lambda: self._set_preset(["BTC_USDT","ETH_USDT","SOL_USDT",
                                                     "XRP_USDT","DOGE_USDT","PEPE_USDT",
                                                     "SUI_USDT"])).pack(side="left", padx=(0,4))
        tk.Button(btn_row, text="Majors", font=("Consolas", 8),
                  bg=BG3, fg=GREEN, relief="flat", cursor="hand2",
                  command=lambda: self._set_preset(["BTC_USDT","ETH_USDT",
                                                     "SOL_USDT","XRP_USDT"])).pack(side="left")

        s4 = self._section(p, "MULTI-TRADE & HEDGING", AMBER)

        mr = self._lrow(s4, "Max trades")
        self.max_trades_cb = self._combo(mr,
            ["1 (single)","2","3","5","10","Unlimited"], "2")

        # Multi-long stacking (extra contracts on high confidence)
        sr = self._lrow(s4, "Stack longs")
        self.stack_var = tk.BooleanVar(value=False)
        tk.Checkbutton(sr, text="Enable", variable=self.stack_var,
                       bg=BG2, fg=CYAN, selectcolor=BG3,
                       activebackground=BG2, font=FMS).pack(side="left")

        self.stack_thresh_cb = self._combo(self._lrow(s4, "Stack at"),
            ["5.0/9","5.5/9","6.0/9","6.5/9","7.0/9","7.5/9","8.0/9"], "6.0/9")
        self.stack_max_cb = self._combo(self._lrow(s4, "Max stack"),
            ["2x","3x","4x","5x"], "2x")

        tk.Label(s4,
            text="Stacking opens extra LONG contracts\nwhen score exceeds threshold,\nimitating buying multiple contracts.",
            font=("Consolas", 8), fg=DIM, bg=BG2,
            justify="left", wraplength=250).pack(fill="x", pady=(2, 6))

        tk.Frame(s4, bg=SEP, height=1).pack(fill="x", pady=(0,6))

        hr2 = self._lrow(s4, "Hedging")
        self.hedge_var = tk.BooleanVar(value=False)
        tk.Checkbutton(hr2, text="Enable", variable=self.hedge_var,
                       bg=BG2, fg=AMBER, selectcolor=BG3,
                       activebackground=BG2, font=FMS).pack(side="left")

        tk.Label(s4,
            text="Opens opposite position to lock\nprofits when in drawdown.",
            font=("Consolas", 8), fg=DIM, bg=BG2,
            justify="left", wraplength=250).pack(fill="x", pady=(2, 0))

        self.hedge_thresh_cb = self._combo(self._lrow(s4, "Hedge at"),
            ["-0.5%","-1.0%","-1.5%","-2.0%","-2.5%","-3.0%","-5.0%"], "-3.0%")

        # ── Adaptive Threshold ────────────────────────────────────────────────
        adp_outer = tk.Frame(p, bg=CYAN, padx=2, pady=2)
        adp_outer.pack(fill="x", pady=(0, 7))
        adp_i = tk.Frame(adp_outer, bg=BG2)
        adp_i.pack(fill="x")
        tk.Frame(adp_i, bg=CYAN, height=2).pack(fill="x")
        adp_th = tk.Frame(adp_i, bg="#050e14")
        adp_th.pack(fill="x")
        tk.Label(adp_th, text="  ⚡  ADAPTIVE THRESHOLD", font=("Consolas", 9, "bold"),
                 fg=CYAN, bg="#050e14", pady=6, anchor="w").pack(side="left")
        adp_i2 = tk.Frame(adp_i, bg=BG2, padx=10, pady=6)
        adp_i2.pack(fill="x")

        self.adaptive_var = tk.BooleanVar(value=True)
        self._adaptive_toggle_btn = tk.Button(adp_i2,
            text="  ON  ⚡  —  click to disable",
            font=("Consolas", 9, "bold"), bg="#050e14", fg=CYAN,
            relief="flat", cursor="hand2", pady=5, anchor="w",
            command=self._on_adaptive_toggle)
        self._adaptive_toggle_btn.pack(fill="x", pady=(0, 3))

        self._adaptive_status_lbl = tk.Label(adp_i2,
            text="Engine adjusts threshold by ATR volatility + win rate",
            font=("Consolas", 8), fg=DIM, bg=BG2, anchor="w")
        self._adaptive_status_lbl.pack(fill="x")

        self._adaptive_info = tk.Label(adp_i2,
            text="  • Dead market (low ATR) → +1.0\n"
                 "  • Strong breakout (high ATR) → −0.5\n"
                 "  • Win rate < 40% → floor raised to 6.5",
            font=("Consolas", 8), fg=MUTED, bg=BG2, justify="left")
        self._adaptive_info.pack(fill="x", pady=(2, 0))

        # ── Overnight Mode ────────────────────────────────────────────────
        night_outer = tk.Frame(p, bg=TEAL, padx=2, pady=2)
        night_outer.pack(fill="x", pady=(0, 7))
        ni = tk.Frame(night_outer, bg=BG2)
        ni.pack(fill="x")
        tk.Frame(ni, bg=TEAL, height=2).pack(fill="x")
        nth = tk.Frame(ni, bg="#06131a")
        nth.pack(fill="x")
        tk.Label(nth, text="  🌙  OVERNIGHT MODE", font=("Consolas", 9, "bold"),
                 fg=TEAL, bg="#06131a", pady=6, anchor="w").pack(side="left")
        ni2 = tk.Frame(ni, bg=BG2, padx=10, pady=6)
        ni2.pack(fill="x")

        self.overnight_var = tk.BooleanVar(value=False)

        # Online/offline status row
        night_status_row = tk.Frame(ni2, bg=BG2)
        night_status_row.pack(fill="x", pady=(0, 4))
        self._overnight_conn_dot = tk.Label(night_status_row, text="●",
            font=("Consolas", 9, "bold"), fg=DIM, bg=BG2)
        self._overnight_conn_dot.pack(side="left")
        self._overnight_status_lbl = tk.Label(night_status_row,
            text="  OFFLINE — auto-managed by UTC time",
            font=("Consolas", 8), fg=DIM, bg=BG2, anchor="w")
        self._overnight_status_lbl.pack(side="left", fill="x", expand=True)

        self.overnight_btn = tk.Button(ni2,
            text="  OFF  —  click to force ON",
            font=("Consolas", 9, "bold"), bg=BG3, fg=MUTED,
            relief="flat", cursor="hand2", pady=5, anchor="w",
            command=self._toggle_overnight)
        self.overnight_btn.pack(fill="x", pady=(0, 3))

        tk.Label(ni2,
            text="Relaxes score, RSI & volume filters\nfor overnight sessions:",
            font=("Consolas", 8), fg=DIM, bg=BG2,
            justify="left", wraplength=250).pack(fill="x", pady=(0, 3))

        self._overnight_detail = tk.Label(ni2,
            text="  • Adaptive base −0.5 (e.g. 4.5→4.0)\n"
                 "  • Floor: base−1.5 (min 4.0)\n"
                 "  • Dual-TF RSI gate 65 → 75\n"
                 "  • Volume gate relaxed 0.70 → 0.55\n"
                 "  • Auto on/off by UTC time",
            font=("Consolas", 8), fg=MUTED, bg=BG2, justify="left")
        self._overnight_detail.pack(fill="x")

        self.lev_warn = tk.Label(p, text="", font=FMS, fg=AMBER, bg=BG,
                                  wraplength=270, justify="left", padx=2, pady=2)
        self.lev_warn.pack(fill="x")

        # ── Buttons ────────────────────────────────────────────────────────────
        self.start_btn = tk.Button(
            p, text="▶  START BOT",
            font=("Consolas", 11, "bold"), bg=GREEN, fg=BG,
            activebackground="#00c484", relief="flat", pady=12,
            cursor="hand2", command=self.toggle_bot)
        self.start_btn.pack(fill="x", pady=(6, 3))

        tk.Button(p, text="⟳  Sync Positions", command=lambda: self._start_sync_positions(),
                  bg=BG3, fg=GREEN, relief="flat", font=FMS,
                  cursor="hand2", pady=5).pack(fill="x", pady=(0,3))

        tk.Button(p, text="📋  Import Trade History", command=self._import_trade_history,
                  bg=BG3, fg=AMBER, relief="flat", font=FMS,
                  cursor="hand2", pady=5).pack(fill="x", pady=(0,3))

        tk.Button(p, text="↺  Reset Defaults", command=self._reset_defaults,
                  bg=BG3, fg=CYAN, relief="flat", font=FMS,
                  cursor="hand2").pack(fill="x", pady=(0,3))

        tk.Button(p, text="💾  Save Keys", command=self._save_keys,
                  bg=BG3, fg=SUB, relief="flat", font=FMS,
                  cursor="hand2", pady=5).pack(fill="x", pady=(0, 8))

    def _build_metrics(self, parent):
        mf = tk.Frame(parent, bg=BG)
        mf.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        for i in range(8): mf.columnconfigure(i, weight=1)

        specs = [
            ("SESSION P&L",  "$0.00",    "+0.00%",           TEXT),
            ("WIN RATE",     "—",        "— W / — L",        TEXT),
            ("TRADES",       "0",        "avg  $—",          TEXT),
            ("BALANCE",      "1,000 USDT", "starting capital", TEXT),
            ("OPEN POS",     "0",        "0 hedged",         MUTED),
            ("LIQS",         "0",        "0.0% of trades",   MUTED),
            ("UPTIME",       "—",        "0 cycles",         MUTED),
            ("LAST SIGNAL",  "—",        "waiting…",         MUTED),
        ]
        self.mv = []; self.ms = []
        for i, (lbl, val, sub, col) in enumerate(specs):
            c = tk.Frame(mf, bg=BG2, highlightthickness=1, highlightbackground=SEP)
            c.grid(row=0, column=i, sticky="ew", padx=(0, 4 if i < 7 else 0))
            tk.Label(c, text=lbl, font=("Consolas", 6, "bold"), fg=MUTED, bg=BG2, pady=3).pack()
            v = tk.Label(c, text=val, font=("Consolas", 10, "bold"), fg=col, bg=BG2); v.pack()
            s = tk.Label(c, text=sub, font=("Consolas", 7), fg=DIM, bg=BG2, pady=3); s.pack()
            self.mv.append(v); self.ms.append(s)

    # ── TABS ──────────────────────────────────────────────────────────────────
    def _build_tabs(self, parent):
        # ── Custom 2-row tab button bar ───────────────────────────────────────
        tab_bar_frame = tk.Frame(parent, bg=BG2)
        tab_bar_frame.grid(row=2, column=0, sticky="ew")
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=0)
        parent.rowconfigure(3, weight=1)

        extra_labels = ["Log", "Events", "Trades", "🤖 AI"]
        all_labels = [pair_label(p) for p in PAIRS] + extra_labels
        n_tabs = len(all_labels)
        row1_end = (n_tabs + 1) // 2
        rows_labels = [all_labels[:row1_end], all_labels[row1_end:]]

        self._tab_btns = {}
        self._tab_index = {}

        for ri, row_labels in enumerate(rows_labels):
            row_frame = tk.Frame(tab_bar_frame, bg=BG2)
            row_frame.pack(fill="x", side="top")
            for label in row_labels:
                idx = all_labels.index(label)
                btn = tk.Button(
                    row_frame, text=label,
                    font=("Consolas", 8, "bold"),
                    bg=BG2, fg=MUTED,
                    activebackground=BG3, activeforeground="#ffffff",
                    relief="flat", bd=0,
                    padx=7, pady=3,
                    cursor="hand2",
                    command=lambda i=idx: self._select_tab(i)
                )
                btn.pack(side="left", padx=1, pady=(2 if ri == 0 else 0, 2))
                self._tab_btns[label] = btn
                self._tab_index[label] = idx

        # ── Simple frame container for tab content (no ttk.Notebook) ───────────
        self.nb = tk.Frame(parent, bg=BG4)
        self.nb.grid(row=3, column=0, sticky="nsew")
        self.nb.columnconfigure(0, weight=1)
        self.nb.rowconfigure(0, weight=1)
        self._tab_frames = {}  # Store tab content frames
        self._current_tab_idx = 0

        for pair in PAIRS:
            tab = tk.Frame(self.nb, bg=BG4)
            tab.grid(row=0, column=0, sticky="nsew")
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)
            sym_label = pair_label(pair)
            cp = ChartPanel(tab, pair, PAIR_COL[pair]) if MPLOT else None
            if not MPLOT:
                tk.Label(tab, text="pip install matplotlib  to enable charts",
                         bg=BG4, fg=MUTED, font=FM).pack(expand=True, fill="both")
            self.chart_panels[pair] = cp
            self._tab_frames[sym_label] = tab
            tab.grid_remove()  # Hide initially

        log_tab = tk.Frame(self.nb, bg=BG)
        log_tab.grid(row=0, column=0, sticky="nsew")
        log_tab.columnconfigure(0, weight=1)
        log_tab.rowconfigure(0, weight=1)
        self._build_log(log_tab)
        self._tab_frames["Log"] = log_tab
        log_tab.grid_remove()  # Hide initially

        events_tab = tk.Frame(self.nb, bg=BG)
        events_tab.grid(row=0, column=0, sticky="nsew")
        events_tab.columnconfigure(0, weight=1)
        events_tab.rowconfigure(0, weight=1)
        self._build_events_log(events_tab)
        self._tab_frames["Events"] = events_tab
        events_tab.grid_remove()  # Hide initially

        trades_tab = tk.Frame(self.nb, bg=BG)
        trades_tab.grid(row=0, column=0, sticky="nsew")
        trades_tab.columnconfigure(0, weight=1)
        trades_tab.rowconfigure(0, weight=1)
        self._build_trades_tab(trades_tab)
        self._tab_frames["Trades"] = trades_tab
        trades_tab.grid_remove()  # Hide initially

        ai_tab = tk.Frame(self.nb, bg=BG)
        ai_tab.grid(row=0, column=0, sticky="nsew")
        ai_tab.columnconfigure(0, weight=1)
        ai_tab.rowconfigure(0, weight=1)
        self._build_ai_tab(ai_tab)
        self._tab_frames["🤖 AI"] = ai_tab
        ai_tab.grid_remove()  # Hide initially

        self._select_tab(0)

    def _select_tab(self, idx):
        """Switch to tab by index and update button highlight colours."""
        # Debounce tab switching to prevent redundant updates
        now = time.time()
        last_tab_switch = getattr(self, "_last_tab_switch_time", 0)
        if now - last_tab_switch < 0.2:  # Ignore rapid tab switches within 200ms
            return
        self._last_tab_switch_time = now

        all_labels = [pair_label(p) for p in PAIRS] + ["Log", "Events", "Trades", "🤖 AI"]
        if idx < 0 or idx >= len(all_labels):
            return

        active_label = all_labels[idx]
        self._current_tab_idx = idx

        # Hide all tab frames
        for frame in self._tab_frames.values():
            frame.grid_remove()

        # Show the selected tab frame
        if active_label in self._tab_frames:
            self._tab_frames[active_label].grid()

        # Update button highlight colours
        for label, btn in self._tab_btns.items():
            if label == active_label:
                btn.config(bg=BG3, fg="#ffffff")
            else:
                btn.config(bg=BG2, fg=MUTED)

        # Refresh visible tab content
        # If switching to AI tab, invalidate throttle cache so it always renders fresh
        if active_label == "🤖 AI":
            self._ai_tab_last_count  = -1
            self._ai_tab_last_events = -1
        self._refresh_visible()

    def _build_claude_panel(self, parent):
        """Persistent Claude AI reasoning + live signal scores bar."""
        self._claude_panel = tk.Frame(parent, bg=BG2,
                                       highlightthickness=1,
                                       highlightbackground=SEP)
        self._claude_panel.grid(row=1, column=0, sticky="ew",
                                 pady=(0, 6), ipady=0)

        # Left accent bar
        tk.Frame(self._claude_panel, bg=PURPLE, width=3).pack(side="left", fill="y")

        # Claude reasoning text block (full width now — signal scores moved to charts)
        right_block = tk.Frame(self._claude_panel, bg=BG2)
        right_block.pack(side="left", fill="both", expand=True,
                         padx=10, pady=5)

        hrow = tk.Frame(right_block, bg=BG2)
        hrow.pack(fill="x")
        tk.Label(hrow, text="🤖  CLAUDE REASONING",
                 font=("Consolas", 7, "bold"), fg=PURPLE,
                 bg=BG2).pack(side="left")
        self._claude_panel_status = tk.Label(
            hrow, text="● OFF — enable Claude in sidebar",
            font=("Consolas", 7), fg=DIM, bg=BG2)
        self._claude_panel_status.pack(side="right")

        self._claude_reason_lbl = tk.Label(
            right_block,
            text="Start the bot — Claude will analyse every signal and explain HOLD decisions.",
            font=("Consolas", 9), fg=MUTED, bg=BG2,
            anchor="w", justify="left", wraplength=700)
        self._claude_reason_lbl.pack(fill="x", pady=(2, 0))

    def _update_claude_panel(self, signals, reasoning=None):
        """No-op — Claude panel removed; Claude runs async post-entry only."""
        pass



    def _ai_log_event(self, pid, event, reason, col):
        """Record an AI decision event for a position — shown in the AI tab."""
        if pid not in self._ai_trade_log:
            self._ai_trade_log[pid] = []
        self._ai_trade_log[pid].append({
            "time":   datetime.now().strftime("%H:%M:%S"),
            "event":  event,
            "reason": reason,
            "col":    col,
        })
        # Keep last 30 events per position
        self._ai_trade_log[pid] = self._ai_trade_log[pid][-30:]
        # Debounce: only schedule one rebuild per 500ms burst
        if not getattr(self, "_ai_tab_refresh_pending", False):
            self._ai_tab_refresh_pending = True
            def _do():
                self._ai_tab_refresh_pending = False
                # Reset guard so the rebuild actually runs
                self._ai_tab_last_count = -1
                self._refresh_ai_tab()
            self.root.after(500, _do)

    def _build_ai_tab(self, parent):
        """AI reasoning tab — one card per open position showing Claude's logic."""
        # Outer scrollable container
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=BG3)
        header.pack(fill="x")
        tk.Frame(header, bg=PURPLE, width=3).pack(side="left", fill="y")
        tk.Label(header, text="  🤖  AI TRADE ANALYSIS",
                 font=("Consolas", 9, "bold"), fg=PURPLE, bg=BG3,
                 pady=7).pack(side="left")
        self._ai_tab_status = tk.Label(header,
            text="No open positions", font=("Consolas", 8),
            fg=DIM, bg=BG3)
        self._ai_tab_status.pack(side="right", padx=10)

        tk.Frame(outer, bg=SEP, height=1).pack(fill="x")

        # Scrollable body
        scroll_outer = tk.Frame(outer, bg=BG)
        scroll_outer.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(scroll_outer, orient="vertical")
        sb.pack(side="right", fill="y")
        cv = tk.Canvas(scroll_outer, bg=BG, yscrollcommand=sb.set,
                       highlightthickness=0)
        cv.pack(fill="both", expand=True)
        sb.config(command=cv.yview)
        self._ai_tab_frame = tk.Frame(cv, bg=BG)
        self._ai_tab_win   = cv.create_window((0,0), window=self._ai_tab_frame,
                                               anchor="nw")
        cv.bind("<Configure>",
            lambda e: cv.itemconfig(self._ai_tab_win, width=e.width))
        self._ai_tab_frame.bind("<Configure>",
            lambda e: (cv.configure(scrollregion=cv.bbox("all")),
                       self._rebind_mousewheel(cv, self._ai_tab_frame)))
        self._ai_tab_canvas = cv

        # Bind mousewheel on canvas itself and all children
        def _mw(e):
            cv.yview_scroll(-1 if e.delta > 0 else 1, "units")
        cv.bind("<MouseWheel>", _mw)
        cv.bind("<Button-4>", lambda e: cv.yview_scroll(-1, "units"))
        cv.bind("<Button-5>", lambda e: cv.yview_scroll( 1, "units"))
        self._bind_mousewheel(cv, self._ai_tab_frame)

        self._refresh_ai_tab()

    def _refresh_ai_tab(self):
        """Rebuild the AI tab — one card per open position."""
        if not hasattr(self, "_ai_tab_frame"):
            return
        # Skip rebuild if AI tab is not currently visible — invalidated on tab switch
        try:
            if not self._ai_tab_frame.winfo_ismapped():
                return
        except Exception:
            pass
        # Throttle: skip if position count AND total event count unchanged
        n_pos = len(self.state.positions) if hasattr(self, "state") else 0
        n_events = sum(len(v) for v in self._ai_trade_log.values())
        if (getattr(self, "_ai_tab_last_count", -1) == n_pos and
                getattr(self, "_ai_tab_last_events", -1) == n_events):
            return
        self._ai_tab_last_count = n_pos
        self._ai_tab_last_events = n_events

        for w in self._ai_tab_frame.winfo_children():
            w.destroy()

        positions = self.state.positions
        if not positions:
            tk.Label(self._ai_tab_frame,
                     text="No open positions — AI analysis will appear here when trades are open.",
                     font=("Consolas", 10), fg=MUTED, bg=BG,
                     pady=30, padx=20, justify="left").pack(anchor="w")
            try:
                if hasattr(self, '_ai_tab_status'):
                    self._ai_tab_status.config(text="No open positions")
            except (AttributeError, tk.TclError) as e:
                _file_logger.debug(f"AI tab status update failed: {e}")
            return

        try:
            self._ai_tab_status.config(
                text=f"{len(positions)} open position{'s' if len(positions)>1 else ''}")
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)

        def _fp(v):
            if v < 0.0001:  return f"${v:.8f}"
            if v < 0.001:   return f"${v:.7f}"
            if v < 0.1:     return f"${v:.5f}"
            if v < 10:      return f"${v:.4f}"
            if v >= 1000:   return f"${v:,.1f}"
            return f"${v:,.2f}"

        for pid, pos in positions.items():
            cur_px   = self.current_prices.get(pos.symbol, pos.entry_price)
            sig      = self.pair_signals.get(pos.symbol) or {}
            events   = self._ai_trade_log.get(pid, [])
            d        = pos.direction
            dcol     = GREEN if d == "LONG" else RED
            pair_col = PAIR_COL.get(pos.symbol, CYAN)

            raw_chg  = ((cur_px - pos.entry_price)/pos.entry_price if d=="LONG"
                        else (pos.entry_price - cur_px)/pos.entry_price)
            margin_pct = raw_chg * pos.leverage * 100
            price_pct  = raw_chg * 100
            pnl_usd    = raw_chg * pos.leverage * pos.margin
            pnl_col    = GREEN if pnl_usd >= 0 else RED

            tp_total = abs(pos.take_profit - pos.entry_price)
            tp_left  = abs(pos.take_profit - cur_px)
            tp_progress = max(0, min(100, (1 - tp_left/tp_total)*100)) if tp_total else 0

            sl_total = abs(pos.stop_loss - pos.entry_price)
            sl_left  = abs(cur_px - pos.stop_loss)
            sl_progress = max(0, min(100, (1 - sl_left/sl_total)*100)) if sl_total else 0

            try:
                opened = datetime.fromisoformat(pos.opened_at.replace("Z","+00:00"))
                secs   = int((datetime.now(timezone.utc) - opened).total_seconds())
                dur    = f"{secs//3600}h {(secs%3600)//60}m" if secs>=3600 else f"{secs//60}m {secs%60}s"
            except Exception:
                dur = "—"

            fee_cost = round(pos.size_usdt * (self._fee_maker + self._fee_taker), 4)  # maker open + taker close

            # ── Card ─────────────────────────────────────────────────────────
            card = tk.Frame(self._ai_tab_frame, bg=BG2,
                            highlightthickness=1, highlightbackground=SEP)
            card.pack(fill="x", padx=10, pady=(8,0))

            # Card header bar
            hdr = tk.Frame(card, bg=BG3)
            hdr.pack(fill="x")
            tk.Frame(hdr, bg=pair_col, width=4).pack(side="left", fill="y")
            tk.Label(hdr, text=f"  {pair_label(pos.symbol)}",
                     font=("Consolas", 11, "bold"), fg=pair_col, bg=BG3,
                     pady=6).pack(side="left")
            tk.Label(hdr, text=f"{d}  {pos.leverage}x",
                     font=("Consolas", 10, "bold"), fg=dcol, bg=BG3,
                     padx=10).pack(side="left")
            tk.Label(hdr,
                     text=f"{'+'if pnl_usd>=0 else ''}${pnl_usd:.2f}  ({margin_pct:+.1f}% margin)",
                     font=("Consolas", 10, "bold"), fg=pnl_col, bg=BG3,
                     padx=10).pack(side="left")
            tk.Label(hdr, text=f"open {dur}",
                     font=("Consolas", 8), fg=DIM, bg=BG3).pack(side="right", padx=10)

            # Body: two columns — left=stats, right=AI event log
            body = tk.Frame(card, bg=BG2)
            body.pack(fill="both", expand=True, padx=1)
            body.columnconfigure(0, weight=2)
            body.columnconfigure(1, weight=3)

            # ── Left column: position stats + indicators ──────────────────
            left_col = tk.Frame(body, bg=BG2)
            left_col.grid(row=0, column=0, sticky="nsew", padx=(10,4), pady=8)

            def _stat(parent, label, val, vcol=None):
                r = tk.Frame(parent, bg=BG2)
                r.pack(fill="x", pady=1)
                tk.Label(r, text=label, font=("Consolas", 8), fg=MUTED,
                         bg=BG2, width=16, anchor="w").pack(side="left")
                tk.Label(r, text=val, font=("Consolas", 8, "bold"),
                         fg=vcol or TEXT, bg=BG2).pack(side="left")

            _stat(left_col, "Entry",       _fp(pos.entry_price))
            _stat(left_col, "Current",     _fp(cur_px),
                  GREEN if pnl_usd>=0 else RED)
            _stat(left_col, "Margin",      f"${pos.margin:.2f} USDT", MUTED)
            _stat(left_col, "Take Profit", _fp(pos.take_profit), "#00e676")
            _stat(left_col, "Stop Loss",   _fp(pos.stop_loss),   "#ff3d57")
            _stat(left_col, "Liq Price",   _fp(pos.liq_price),   "#f783ac")
            _stat(left_col, "P&L",
                  f"{'+'if pnl_usd>=0 else ''}${pnl_usd:.3f}  ({price_pct:+.3f}% price)",
                  pnl_col)
            _stat(left_col, "Round-trip fee", f"≈${fee_cost:.3f}", AMBER)

            # TP progress bar
            bar_frame = tk.Frame(left_col, bg=BG2)
            bar_frame.pack(fill="x", pady=(6,2))
            tk.Label(bar_frame, text="TP progress", font=("Consolas", 7),
                     fg=MUTED, bg=BG2).pack(anchor="w")
            bar_bg = tk.Frame(bar_frame, bg=BG3, height=6)
            bar_bg.pack(fill="x")
            bar_bg.update_idletasks()
            bar_w  = bar_bg.winfo_width() or 200
            fill_w = max(2, int(bar_w * tp_progress / 100))
            bar_fill = tk.Frame(bar_bg,
                bg=GREEN if tp_progress > 60 else (AMBER if tp_progress > 30 else MUTED),
                height=6, width=fill_w)
            bar_fill.place(x=0, y=0)
            tk.Label(bar_frame, text=f"{tp_progress:.0f}% to TP",
                     font=("Consolas", 7), fg=DIM, bg=BG2).pack(anchor="e")

            # SL danger bar
            bar_frame2 = tk.Frame(left_col, bg=BG2)
            bar_frame2.pack(fill="x", pady=(2,6))
            tk.Label(bar_frame2, text="SL proximity", font=("Consolas", 7),
                     fg=MUTED, bg=BG2).pack(anchor="w")
            bar_bg2 = tk.Frame(bar_frame2, bg=BG3, height=6)
            bar_bg2.pack(fill="x")
            fill_w2 = max(2, int((bar_bg.winfo_width() or 200) * sl_progress / 100))
            bar_fill2 = tk.Frame(bar_bg2,
                bg=RED if sl_progress > 70 else (AMBER if sl_progress > 40 else DIM),
                height=6, width=fill_w2)
            bar_fill2.place(x=0, y=0)
            tk.Label(bar_frame2, text=f"{sl_progress:.0f}% toward SL",
                     font=("Consolas", 7), fg=DIM, bg=BG2).pack(anchor="e")

            # Current indicators
            if sig:
                tk.Frame(left_col, bg=SEP, height=1).pack(fill="x", pady=4)
                tk.Label(left_col, text="CURRENT INDICATORS",
                         font=("Consolas", 7, "bold"), fg=MUTED, bg=BG2).pack(anchor="w")
                ind_grid = tk.Frame(left_col, bg=BG2)
                ind_grid.pack(fill="x", pady=2)
                ind_data = [
                    ("Trend",    sig.get("trend","—"),
                     GREEN if sig.get("trend")=="BULL" else RED),
                    ("RSI",      f"{sig.get('rsi',0):.0f}",
                     RED if sig.get("rsi",50)>70 else (GREEN if sig.get("rsi",50)<30 else SUB)),
                    ("StochRSI", f"{sig.get('srsi',0):.0f}",
                     RED if sig.get("srsi",50)>80 else (GREEN if sig.get("srsi",50)<20 else SUB)),
                    ("MACD",     "▲" if sig.get("macd_h",0)>0 else "▼",
                     GREEN if sig.get("macd_h",0)>0 else RED),
                    ("OBV",      "▲" if sig.get("obv_slope",0)>0 else "▼",
                     GREEN if sig.get("obv_slope",0)>0 else RED),
                    ("BB%B",     f"{sig.get('pct_b',0.5):.2f}", SUB),
                    ("ATR",      f"{sig.get('atr_pct',0):.3f}%",
                     GREEN if sig.get("atr_ok") else RED),
                    ("Score",    f"{sig.get('score',0)}/9  {sig.get('direction','—')}",
                     CYAN if sig.get("score",0)>=7 else (
                         GREEN if sig.get("direction")=="LONG" else
                         RED if sig.get("direction")=="SHORT" else MUTED)),
                ]
                for row_i, (name, val, col) in enumerate(ind_data):
                    r = row_i // 2
                    c = (row_i % 2) * 2
                    tk.Label(ind_grid, text=name, font=("Consolas", 7),
                             fg=MUTED, bg=BG2).grid(row=r, column=c, sticky="w", padx=(0,4))
                    tk.Label(ind_grid, text=val, font=("Consolas", 7, "bold"),
                             fg=col, bg=BG2).grid(row=r, column=c+1, sticky="w", padx=(0,12))

            # ── Right column: AI event log ────────────────────────────────
            tk.Frame(body, bg=SEP, width=1).grid(row=0, column=0, sticky="ns",
                                                   padx=(0,0), pady=4)
            right_col = tk.Frame(body, bg=BG2)
            right_col.grid(row=0, column=1, sticky="nsew", padx=(10,10), pady=8)

            # Collapsible AI decision log header
            log_collapsed_key = f"_ai_log_collapsed_{pid}"
            if not hasattr(self, log_collapsed_key):
                setattr(self, log_collapsed_key, False)
            is_collapsed = getattr(self, log_collapsed_key)

            log_hdr = tk.Frame(right_col, bg=BG2)
            log_hdr.pack(fill="x")
            toggle_btn = tk.Label(
                log_hdr,
                text=f"{'▶' if is_collapsed else '▼'}  AI DECISION LOG"
                     + (f"  ({len(events)} events)" if events else ""),
                font=("Consolas", 8, "bold"), fg=PURPLE, bg=BG2,
                cursor="hand2")
            toggle_btn.pack(side="left")
            if events:
                latest_col = events[-1]["col"] if events else DIM
                tk.Label(log_hdr,
                         text=f"Latest: {events[-1]['event']}",
                         font=("Consolas", 7), fg=latest_col, bg=BG2,
                         padx=8).pack(side="left")
            tk.Frame(right_col, bg=SEP, height=1).pack(fill="x", pady=(2,6))

            # Collapsible log body
            log_body = tk.Frame(right_col, bg=BG2)
            log_body.pack(fill="x")
            if is_collapsed:
                log_body.pack_forget()

            def _make_toggle(lkey, lbody, tbtn, pid_=pid, evts=events):
                def _toggle(e=None):
                    cur = getattr(self, lkey, False)
                    setattr(self, lkey, not cur)
                    self._refresh_ai_tab()
                tbtn.bind("<Button-1>", _toggle)
            _make_toggle(log_collapsed_key, log_body, toggle_btn)

            if not events:
                tk.Label(log_body,
                         text=("No AI decisions yet for this position.\n"
                               "Claude will analyse on: near-TP, fast adverse moves,\n"
                               "stale trade timeout, and every 5-cycle monitoring check."),
                         font=("Consolas", 8), fg=DIM, bg=BG2,
                         justify="left", wraplength=380).pack(anchor="w")
            else:
                # Show events newest-first
                for ev in reversed(events):
                    ev_frame = tk.Frame(log_body, bg=BG3,
                                        highlightthickness=1,
                                        highlightbackground=SEP)
                    ev_frame.pack(fill="x", pady=(0,4))
                    tk.Frame(ev_frame, bg=ev["col"], width=3).pack(
                        side="left", fill="y")
                    ev_body = tk.Frame(ev_frame, bg=BG3)
                    ev_body.pack(side="left", fill="x", expand=True,
                                 padx=6, pady=4)
                    hrow = tk.Frame(ev_body, bg=BG3)
                    hrow.pack(fill="x")
                    tk.Label(hrow, text=ev["event"],
                             font=("Consolas", 8, "bold"),
                             fg=ev["col"], bg=BG3).pack(side="left")
                    tk.Label(hrow, text=ev["time"],
                             font=("Consolas", 7), fg=DIM,
                             bg=BG3).pack(side="right")
                    tk.Label(ev_body, text=ev["reason"],
                             font=("Consolas", 8), fg=SUB, bg=BG3,
                             anchor="w", justify="left",
                             wraplength=380).pack(fill="x", pady=(1,0))

        # Re-bind mousewheel: canvas Configure event already handles this
        pass

    def _build_trades_tab(self, parent):
        """Full trade history with P&L, entry/exit, duration. Sortable columns."""
        wrap = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=SEP)
        wrap.pack(fill="both", expand=True, padx=6, pady=6)

        # Header bar
        hdr = tk.Frame(wrap, bg=BG3)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=CYAN, width=3).pack(side="left", fill="y")
        tk.Label(hdr, text="  TRADE HISTORY", font=("Consolas", 10, "bold"),
                 fg=CYAN, bg=BG3, pady=8).pack(side="left")
        tk.Label(hdr, text="click column headers to sort",
                 font=("Consolas", 8), fg=DIM, bg=BG3, padx=8).pack(side="right")

        # Summary bar
        self._tlog_summary = tk.Label(wrap, text="No trades yet",
                                       font=("Consolas", 10), fg=MUTED, bg=BG2,
                                       anchor="w", padx=14, pady=6)
        self._tlog_summary.pack(fill="x")
        tk.Frame(wrap, bg=SEP, height=1).pack(fill="x")

        # Sort state: col 0 = DATE descending (most recent first) by default
        self._trades_sort_col = 0
        self._trades_sort_asc = False

        # Column definitions: (label, width_chars)
        self._trade_cols = [
            ("DATE",    10),
            ("TIME",     9),
            ("PAIR",     8),
            ("DIR",      6),
            ("LEV",      5),
            ("ENTRY",   11),
            ("EXIT",    11),
            ("SIZE",     7),
            ("P&L $",    9),
            ("P&L %",    8),
            ("STATUS",  14),
        ]

        # Sort key functions per column index
        self._trades_sort_keys = [
            lambda t: t.get("closed_at", ""),                                   # 0 DATE
            lambda t: t.get("closed_at", "")[11:19],                            # 1 TIME
            lambda t: pair_label(t.get("symbol", "")),                          # 2 PAIR
            lambda t: t.get("direction", ""),                                   # 3 DIR
            lambda t: t.get("leverage", 0),                                     # 4 LEV
            lambda t: t.get("entry_price") or 0,                                # 5 ENTRY
            lambda t: t.get("exit_price") or 0,                                 # 6 EXIT
            lambda t: (t.get("margin") or 0) * (t.get("leverage") or 1),       # 7 SIZE
            lambda t: t.get("pnl_usdt", 0),                                     # 8 P&L $
            lambda t: (t.get("pnl_usdt", 0) / max(t.get("margin") or 1, 0.001)),# 9 P&L %
            lambda t: t.get("status", ""),                                      # 10 STATUS
        ]

        # Clickable column headers
        col_hdr = tk.Frame(wrap, bg=BG4)
        col_hdr.pack(fill="x")
        self._trade_col_lbls = []
        tk.Frame(col_hdr, bg=BG4, width=6).pack(side="left")  # left accent indent
        for i, (txt, w) in enumerate(self._trade_cols):
            # DATE col gets initial sort indicator
            disp = f"{txt} ▼" if i == 0 else txt
            lbl = tk.Label(col_hdr, text=disp, font=("Consolas", 9, "bold"),
                           fg=CYAN if i == 0 else DIM, bg=BG4, width=w, anchor="w",
                           padx=4, pady=5, cursor="hand2")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, idx=i: self._trades_sort_by(idx))
            lbl.bind("<Enter>",    lambda e, l=lbl: l.config(fg=TEXT))
            lbl.bind("<Leave>",    lambda e, l=lbl, idx=i:
                l.config(fg=CYAN if idx == self._trades_sort_col else DIM))
            self._trade_col_lbls.append(lbl)
        tk.Frame(wrap, bg=SEP2, height=1).pack(fill="x")

        # Scrollable trade rows
        outer = tk.Frame(wrap, bg=BG)
        outer.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(outer, orient="vertical")
        sb.pack(side="right", fill="y")
        cv = tk.Canvas(outer, bg=BG, yscrollcommand=sb.set,
                       highlightthickness=0)
        cv.pack(fill="both", expand=True)
        sb.config(command=cv.yview)
        self._trades_frame = tk.Frame(cv, bg=BG)
        self._trades_win   = cv.create_window((0, 0), window=self._trades_frame,
                                               anchor="nw")
        def _on_resize(e):
            cv.itemconfig(self._trades_win, width=e.width)
        cv.bind("<Configure>", _on_resize)
        self._trades_frame.bind(
            "<Configure>",
            lambda e: (cv.configure(scrollregion=cv.bbox("all")),
                       self._rebind_mousewheel(cv, self._trades_frame)))
        self._trades_cv = cv
        self._bind_mousewheel(cv, self._trades_frame)

    def _trades_sort_by(self, col_idx):
        """Sort trades by column. Same column toggles asc/desc."""
        if self._trades_sort_col == col_idx:
            self._trades_sort_asc = not self._trades_sort_asc
        else:
            self._trades_sort_col = col_idx
            # DATE defaults desc (newest first); everything else asc
            self._trades_sort_asc = col_idx != 0
        # Update header labels with sort arrow
        for i, lbl in enumerate(self._trade_col_lbls):
            base = self._trade_cols[i][0]
            if i == col_idx:
                arrow = " ▲" if self._trades_sort_asc else " ▼"
                lbl.config(text=base + arrow, fg=CYAN)
            else:
                lbl.config(text=base, fg=DIM)
        # Force full rebuild
        self._trades_tab_last_count = -1
        self._refresh_trades_tab()

    def _refresh_trades_tab(self):
        """Rebuild the trades tab rows from state.trades (max 30 shown)."""
        if not hasattr(self, "_trades_frame"): return

        # Debounce: coalesce multiple rapid calls into one deferred execution
        if not getattr(self, "_trades_refresh_pending", False):
            self._trades_refresh_pending = True
            self.root.after(80, self._do_refresh_trades_tab)

    def _do_refresh_trades_tab(self):
        """Actual rebuild — called once after debounce delay."""
        self._trades_refresh_pending = False
        if not hasattr(self, "_trades_frame"): return

        sort_col = getattr(self, "_trades_sort_col", 0)
        sort_asc = getattr(self, "_trades_sort_asc", False)

        # Guard: skip rebuild if nothing meaningful changed
        n_now   = len(self.state.trades)
        state_key = (n_now, sort_col, sort_asc)
        if getattr(self, "_trades_tab_state_key", None) == state_key:
            return
        self._trades_tab_state_key  = state_key
        self._trades_tab_last_count = n_now  # keep compat

        # Clear existing rows
        for w in self._trades_frame.winfo_children():
            w.destroy()

        # Sort trades using current sort column/direction
        sort_keys = getattr(self, "_trades_sort_keys", [lambda t: t.get("closed_at", "")])
        key_fn = sort_keys[sort_col] if sort_col < len(sort_keys) else sort_keys[0]
        trades = sorted(self.state.trades, key=key_fn, reverse=not sort_asc)

        # Cap display at 30 rows to keep the UI snappy
        MAX_DISPLAY = 30
        total_count = len(trades)
        trades = trades[:MAX_DISPLAY]

        if not trades:
            tk.Label(self._trades_frame, text="No closed trades yet",
                     font=("Consolas", 10), fg=MUTED, bg=BG,
                     pady=20).pack()
            self._tlog_summary.config(text="No trades yet")
            return

        # Summary (always computed from full list, not just displayed slice)
        all_trades = self.state.trades
        total   = sum(t.get("pnl_usdt", 0) for t in all_trades)
        wins    = sum(1 for t in all_trades if t.get("pnl_usdt", 0) >= 0)
        losses  = len(all_trades) - wins
        wr      = wins / len(all_trades) * 100 if all_trades else 0
        sc      = GREEN if total >= 0 else RED
        sign    = "+" if total >= 0 else ""
        shown_note = f"  (showing {len(trades)} of {total_count})" if total_count > MAX_DISPLAY else ""
        self._tlog_summary.config(
            text=f"  {total_count} trades   W:{wins}  L:{losses}  WR:{wr:.1f}%   "
                 f"Total P&L: {sign}${total:.2f}{shown_note}",
            fg=sc)

        def _fp(v):
            if v is None: return "—"
            av = abs(v)
            if av == 0:      return "$0.00"
            if av < 0.0001:  return f"${v:.8f}"
            if av < 0.001:   return f"${v:.6f}"
            if av < 0.1:     return f"${v:.4f}"
            if av < 10:      return f"${v:.3f}"
            if av >= 10000:  return f"${v:,.0f}"
            if av >= 1000:   return f"${v:,.1f}"
            return f"${v:,.2f}"

        cols = getattr(self, "_trade_cols", [
            ("DATE",10),("TIME",9),("PAIR",8),("DIR",6),("LEV",5),("ENTRY",11),
            ("EXIT",11),("SIZE",7),("P&L $",9),("P&L %",8),("STATUS",14),
        ])

        for i, t in enumerate(trades):
            is_even = i % 2 == 0
            bg = BG2 if is_even else BG3

            pnl      = t.get("pnl_usdt", 0)
            margin   = t.get("margin", 0) or 1
            lev      = t.get("leverage", 1)
            margin_r = pnl / margin * 100 if margin else 0
            status   = t.get("status", "—")
            entry    = t.get("entry_price")
            exit_    = t.get("exit_price")
            dirn     = t.get("direction", "—")
            sym      = pair_label(t.get("symbol", "—"))
            hedge    = t.get("hedge", False)
            closed_at = t.get("closed_at", "")
            date_str = ""
            time_str = ""
            if closed_at:
                try:
                    date_str = closed_at[:10]   # YYYY-MM-DD
                    time_str = closed_at[11:19]  # HH:MM:SS
                except Exception:
                    date_str = closed_at[:10] if len(closed_at) >= 10 else closed_at
                    time_str = ""

            pnl_col = GREEN if pnl >= 0 else (PURPLE if "LIQ" in status else RED)
            dir_col = GREEN if dirn == "LONG" else RED
            sym_col = PAIR_COL.get(t.get("symbol", ""), CYAN)
            sta_col = (GREEN  if "WIN"    in status else
                       PURPLE if "LIQ"    in status else
                       AMBER  if "MANUAL" in status else RED)

            # Outer row frame with a thin left accent bar
            row = tk.Frame(self._trades_frame, bg=bg)
            row.pack(fill="x", pady=0)
            accent_col = pnl_col
            tk.Frame(row, bg=accent_col, width=3).pack(side="left", fill="y")

            # Status label: shorten "imported" to keep it readable
            status_short = (status.replace(" (imported)", "★")
                                  .replace("WIN", "WIN")
                                  .replace("LOSS", "LOSS"))

            size_str = f"${margin * lev:.0f}" if margin * lev >= 1 else f"${margin:.2f}"
            pnl_str  = f"{'+'if pnl>=0 else ''}${abs(pnl):.2f}"
            pct_str  = f"{'+'if margin_r>=0 else ''}{margin_r:.1f}%"

            cell_data = [
                (date_str,                             cols[0][1], DIM,      "Consolas 9"),
                (time_str,                             cols[1][1], MUTED,    "Consolas 10"),
                (f"{sym}{'[H]' if hedge else ''}",     cols[2][1], sym_col,  "Consolas 10 bold"),
                (dirn,                                 cols[3][1], dir_col,  "Consolas 10 bold"),
                (f"{lev}x",                            cols[4][1], BLUE,     "Consolas 10"),
                (_fp(entry),                           cols[5][1], SUB,      "Consolas 10"),
                (_fp(exit_),                           cols[6][1], SUB,      "Consolas 10"),
                (size_str,                             cols[7][1], MUTED,    "Consolas 10"),
                (pnl_str,                              cols[8][1], pnl_col,  "Consolas 10 bold"),
                (pct_str,                              cols[9][1], pnl_col,  "Consolas 10"),
                (status_short,                         cols[10][1], sta_col,  "Consolas 10"),
            ]

            for txt, w, fg, fnt in cell_data:
                tk.Label(row, text=txt, font=fnt,
                         fg=fg, bg=bg, width=w, anchor="w",
                         padx=4, pady=7).pack(side="left")

            # Thin separator between rows
            tk.Frame(self._trades_frame, bg=SEP, height=1).pack(fill="x")

        self._trades_cv.yview_moveto(0)
        # Note: mousewheel binding is handled by the canvas Configure event — no rebind needed

    def _build_log(self, parent):
        head = tk.Frame(parent, bg=BG2); head.pack(fill="x")
        tk.Frame(head, bg=BLUE, height=2).pack(fill="x")
        hr = tk.Frame(head, bg=BG2, pady=6); hr.pack(fill="x", padx=12)
        tk.Label(hr, text="LIVE LOG", font=("Consolas", 9, "bold"),
                 fg=MUTED, bg=BG2).pack(side="left")
        tk.Button(hr, text="Clear", font=FMS, bg=BG3, fg=MUTED,
                  relief="flat", cursor="hand2",
                  command=lambda: (self.log_box.config(state="normal"),
                                   self.log_box.delete("1.0", "end"),
                                   self.log_box.config(state="disabled"))).pack(side="right")
        self.log_box = scrolledtext.ScrolledText(
            parent, bg="#070a10", fg=SUB, font=("Consolas", 10),
            relief="flat", wrap="word", state="disabled",
            insertbackground=TEXT, padx=14, pady=10,
            selectbackground=BG3, selectforeground=TEXT)
        self.log_box.pack(fill="both", expand=True)
        for tag, col in [("g", GREEN), ("r", RED), ("b", BLUE), ("a", AMBER),
                          ("p", PURPLE), ("c", CYAN), ("t", TEAL), ("dim", DIM),
                          ("mu", MUTED), ("w", TEXT)]:
            self.log_box.tag_config(tag, foreground=col)

    def _build_events_log(self, parent):
        """Events log — trade decisions, blocks, threshold changes, AI actions."""
        head = tk.Frame(parent, bg=BG2); head.pack(fill="x")
        tk.Frame(head, bg=AMBER, height=2).pack(fill="x")
        hr = tk.Frame(head, bg=BG2, pady=6); hr.pack(fill="x", padx=12)
        tk.Label(hr, text="EVENTS", font=("Consolas", 9, "bold"),
                 fg=MUTED, bg=BG2).pack(side="left")
        tk.Label(hr, text="trade decisions · blocks · threshold changes · AI actions",
                 font=("Consolas", 8), fg=DIM, bg=BG2).pack(side="left", padx=8)
        tk.Button(hr, text="Clear", font=FMS, bg=BG3, fg=MUTED,
                  relief="flat", cursor="hand2",
                  command=lambda: (self.event_box.config(state="normal"),
                                   self.event_box.delete("1.0", "end"),
                                   self.event_box.config(state="disabled"))).pack(side="right")
        self.event_box = scrolledtext.ScrolledText(
            parent, bg="#070a10", fg=SUB, font=("Consolas", 10),
            relief="flat", wrap="word", state="disabled",
            insertbackground=TEXT, padx=14, pady=10,
            selectbackground=BG3, selectforeground=TEXT)
        self.event_box.pack(fill="both", expand=True)
        for tag, col in [("g", GREEN), ("r", RED), ("b", BLUE), ("a", AMBER),
                          ("p", PURPLE), ("c", CYAN), ("t", TEAL), ("dim", DIM),
                          ("mu", MUTED), ("w", TEXT)]:
            self.event_box.tag_config(tag, foreground=col)

    # ── CHART REFRESH ─────────────────────────────────────────────────────────
    def _initial_load(self):
        """Fetch all pairs on startup so charts and prices load immediately."""
        self._log("Loading market data for all pairs…", DIM)
        def _go():
            # Fetch exact precision from MEXC API first
            try:
                updated = fetch_contract_precision()
                if updated:
                    self._log(f"Precision loaded from MEXC: {' '.join(updated)}", CYAN)
                else:
                    self._log("Using default precisions (MEXC API unavailable)", MUTED)
            except Exception as e:
                self._log(f"Precision fetch failed: {e}", MUTED)

            loaded = 0
            for pair in (self._active_pairs() if hasattr(self, "_pair_vars") else PAIRS):
                try:
                    tf  = self.tf_cb.get() if hasattr(self, 'tf_cb') else "Min5"
                    can = get_klines(pair, tf, 200)
                    tkr = get_ticker(pair)
                    sig = compute_signals(can, tkr, self._thresh())
                    if sig is None: continue
                    self.pair_candles[pair]   = can
                    self.pair_signals[pair]   = sig
                    self.current_prices[pair] = sig["price"]
                    px = sig["price"]
                    self.root.after(0, lambda p=pair, v=px: self._set_price(p, v))
                    cp = self.chart_panels.get(pair)
                    if cp:
                        open_pos = [p for p in self.state.positions.values() if p.symbol == pair]
                        self.root.after(0, lambda c=can, s=sig, p=cp, op=open_pos: p.update(c, s, op))
                    loaded += 1
                    time.sleep(0.5)
                except Exception as e:
                    self.root.after(0, lambda p=pair, err=str(e)[:80]: self._log(f"Failed to load {p}: {err}", AMBER))
            self.root.after(0, lambda: self._log(
                f"Market data loaded for {loaded}/{len(PAIRS)} pairs", CYAN))
            # Update claude panel with best available signal
            valid_sigs = {p: s for p, s in self.pair_signals.items() if s is not None}
            if valid_sigs:
                best = max(valid_sigs.values(), key=lambda s: s.get("score", 0))
                self.root.after(0, lambda s=best: self._update_claude_panel(s))
        threading.Thread(target=_go, daemon=True).start()

    def _chart_cycle(self):
        self._refresh_visible()
        # Only poll REST prices when WS is not connected — WS keeps prices current
        if not (self._ws_manager and self._ws_manager.connected):
            self._refresh_all_prices()
        self._chart_timer = self.root.after(6000, self._chart_cycle)

    def _refresh_all_prices(self):
        """Fetch ticker prices for all pairs to keep header strip updated."""
        def _go():
            for pair in (self._active_pairs() if hasattr(self, "_pair_vars") else PAIRS):
                try:
                    tkr = get_ticker(pair)
                    px  = tkr["last"]
                    if px > 0:
                        self.current_prices[pair] = px
                        if pair in self.pair_signals and isinstance(self.pair_signals[pair], dict):
                            self.pair_signals[pair]["price"] = px
                        self.root.after(0, lambda p=pair, v=px: self._set_price(p, v))
                except Exception as _exc:
                    _file_logger.debug("suppressed error: %s", _exc)
        threading.Thread(target=_go, daemon=True).start()

    def _refresh_visible(self):
        try:
            idx = self._current_tab_idx
            if idx < len(PAIRS):
                pair = PAIRS[idx]
                # Skip refresh if this pair was updated recently (within 2 seconds)
                now = time.time()
                last_fetch = getattr(self, "_last_pair_fetch_time", {})
                if now - last_fetch.get(pair, 0) < 2.0:
                    return  # Use cached data
                self._fetch_pair(pair)
                self._last_pair_fetch_time = last_fetch
                self._last_pair_fetch_time[pair] = now
        except (AttributeError, tk.TclError, IndexError) as e:
            _file_logger.debug(f"Failed to refresh visible tab: {e}")

    def _refresh_position_chart(self, pair):
        """Refresh one chart so synced/imported positions draw entry, TP, SL and LIQ lines."""
        cp = self.chart_panels.get(pair)
        if not cp:
            return
        open_pos = [p for p in self.state.positions.values() if p.symbol == pair]
        can = self.pair_candles.get(pair)
        sig = self.pair_signals.get(pair)
        if can and sig:
            cp.update(can, sig, open_pos)
        else:
            self._fetch_pair(pair)
    def _fetch_pair(self, pair):
        def _go():
            try:
                tf   = self.tf_cb.get()
                ws_k = self._ws_manager.get_klines(pair) if self._ws_manager else []
                can  = ws_k[-200:] if ws_k and len(ws_k) >= 20 else get_klines(pair, tf, 200)
                ws_px = self._ws_manager.get_price(pair) if self._ws_manager else None
                tkr  = {"last": ws_px, "funding": 0.0} if ws_px else get_ticker(pair)
                sig = compute_signals(can, tkr, self._thresh())
                self.pair_candles[pair] = can
                self.pair_signals[pair] = sig
                self.current_prices[pair] = sig["price"]
                self.root.after(0, lambda: self._set_price(pair, sig["price"]))
                self.root.after(0, lambda s={**sig,"symbol":pair}: self._update_claude_panel(s))
                cp = self.chart_panels.get(pair)
                if cp:
                    open_pos = [p for p in self.state.positions.values()
                                if p.symbol == pair]
                    def _on_tf_change(sym, tf, _cp=cp):
                        """Called by chart TF buttons to re-fetch with new timeframe."""
                        def _go():
                            try:
                                can2 = get_klines(sym, tf, 200)
                                tkr2 = get_ticker(sym)
                                sig2 = compute_signals(can2, tkr2, self._thresh())
                                ops2 = [p for p in self.state.positions.values()
                                        if p.symbol == sym]
                                self.root.after(0, lambda: _cp.update(can2, sig2, ops2))
                            except Exception as e:
                                _file_logger.warning(f"Chart timeframe change failed for {sym}: {e}")
                        threading.Thread(target=_go, daemon=True).start()
                    self.root.after(0, lambda c=can, s=sig, o=open_pos, _tf=tf: cp.update(c, s, o, on_tf_change=_on_tf_change, bot_tf=_tf))
                # Update cache timestamp after successful fetch
                last_fetch = getattr(self, "_last_pair_fetch_time", {})
                last_fetch[pair] = time.time()
                self._last_pair_fetch_time = last_fetch
            except Exception as e:
                _file_logger.warning(f"Chart update failed for {pair}: {e}")
        threading.Thread(target=_go, daemon=True).start()

    def _set_price(self, pair, px):
        col = PAIR_COL.get(pair, CYAN)
        sym = pair.replace("_USDT", "")
        # Unified smart formatter — same rules used everywhere (chart, ticker, dock)
        if px == 0:
            txt = " —"
        elif px < 0.0001: txt = f" ${px:,.7f}"
        elif px < 0.01:   txt = f" ${px:,.5f}"
        elif px < 1:      txt = f" ${px:,.4f}"
        elif px < 10:     txt = f" ${px:,.3f}"
        elif px >= 10000: txt = f" ${px:,.0f}"
        elif px >= 1000:  txt = f" ${px:,.1f}"
        else:             txt = f" ${px:,.2f}"
        # Update per-pair ticker label
        lbl = self.price_lbls.get(pair)
        if lbl:
            lbl.config(text=txt, fg=col)
        # Also keep compat label updated for selected pair
        self.price_lbl.config(text=f"{sym}{txt}", fg=col)

    def _on_tab(self, _=None):
        # This method is no longer needed since we use custom tab buttons
        # Tab switching is handled directly by button commands in _select_tab
        pass
    def _on_pair(self, _=None):
        pair = self.pair_cb.get()
        if pair in PAIRS: self._select_tab(PAIRS.index(pair))
        # Update leverage options to match pair max
        opts = self._lev_opts(pair)
        self.lev_cb.config(values=opts)
        cur = self.lev_cb.get()
        if cur not in opts: self.lev_cb.set(opts[min(3, len(opts)-1)])  # default 10x
        self._on_lev()
        self._fetch_pair(pair)

    # ── DOCK CYCLE ────────────────────────────────────────────────────────────
    def _dock_cycle(self):
        self.dock.state = self.state
        self.dock.refresh(self.current_prices)
        if not self.dry_var.get():
            self._fetch_live_balance()
        self._dock_timer = self.root.after(1000, self._dock_cycle)

    # ── HELPERS ───────────────────────────────────────────────────────────────
    def _log(self, msg, col=None):
        # File log (always)
        if col == RED:
            _file_logger.error(msg)
        elif col == AMBER:
            _file_logger.warning(msg)
        else:
            _file_logger.info(msg)
        # UI log — buffer messages and flush in one batch to avoid flooding Tk event queue
        tag = _LOG_TAG_MAP.get(col, "w")
        ts = datetime.now().strftime("%H:%M:%S")
        if not hasattr(self, "_log_buffer"):
            self._log_buffer = []
            self._log_flush_pending = False
        self._log_buffer.append((ts, msg, tag))
        if not self._log_flush_pending:
            self._log_flush_pending = True
            self.root.after(50, self._flush_log)

    def _flush_log(self):
        self._log_flush_pending = False
        if not self._log_buffer:
            return
        buf, self._log_buffer = self._log_buffer, []
        try:
            _top, bottom = self.log_box.yview()
            at_bottom = bottom >= 0.999
        except Exception:
            at_bottom = True
        self.log_box.config(state="normal")
        for ts, msg, tag in buf:
            self.log_box.insert("end", f"[{ts}]  ", "dim")
            self.log_box.insert("end", msg + "\n", tag)
        # Trim log to last 600 lines to prevent Tk slowdown over long sessions
        try:
            line_count = int(self.log_box.index("end-1c").split(".")[0])
            if line_count > 700:
                self.log_box.delete("1.0", f"{line_count - 600}.0")
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)
        if at_bottom:
            self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _log_event(self, msg, col=None):
        """Log to both the main log and the Events tab.
        Use for anything that affects trade decisions: opens, closes, blocks,
        threshold changes, overnight/drought mode, AI actions, leverage changes.
        """
        self._log(msg, col)  # always appears in main log too
        tag = _LOG_TAG_MAP.get(col, "w")
        ts = datetime.now().strftime("%H:%M:%S")
        if not hasattr(self, "_event_buffer"):
            self._event_buffer = []
            self._event_flush_pending = False
        self._event_buffer.append((ts, msg, tag))
        if not self._event_flush_pending:
            self._event_flush_pending = True
            self.root.after(50, self._flush_event_log)

    def _flush_event_log(self):
        self._event_flush_pending = False
        if not self._event_buffer:
            return
        buf, self._event_buffer = self._event_buffer, []
        if not hasattr(self, "event_box"):
            return
        try:
            _top, bottom = self.event_box.yview()
            at_bottom = bottom >= 0.999
        except Exception:
            at_bottom = True
        self.event_box.config(state="normal")
        for ts, msg, tag in buf:
            self.event_box.insert("end", f"[{ts}]  ", "dim")
            self.event_box.insert("end", msg + "\n", tag)
        try:
            line_count = int(self.event_box.index("end-1c").split(".")[0])
            if line_count > 700:
                self.event_box.delete("1.0", f"{line_count - 600}.0")
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)
        if at_bottom:
            self.event_box.see("end")
        self.event_box.config(state="disabled")

    def _tick_uptime(self):
        """1-second timer that updates the uptime display in real time."""
        if not self.bot_running or not self._bot_start_time:
            return
        elapsed = time.time() - self._bot_start_time
        h   = int(elapsed // 3600)
        m   = int((elapsed % 3600) // 60)
        sec = int(elapsed % 60)
        uptime_str = f"{h:02d}:{m:02d}:{sec:02d}"
        thr_now = self._adaptive_thr or self._thresh()
        cyc_sub = (f"{self._cycles_run} cycles  thr:{thr_now}/9"
                   + (" ↓adaptive" if self._adaptive_thr else ""))
        adp_on  = self.adaptive_var.get() if hasattr(self, "adaptive_var") else True
        thr_col = AMBER if self._adaptive_thr else (CYAN if adp_on else MUTED)
        self._met(6, uptime_str, cyc_sub, thr_col)
        self._uptime_timer = self.root.after(1000, self._tick_uptime)

    def _met(self, i, val, sub=None, col=None):
        """Buffer metric updates and flush them all in a single after(0) call."""
        if not hasattr(self, "_met_buf"):
            self._met_buf = {}
            self._met_flush_pending = False
        self._met_buf[i] = (val, sub, col)
        if not self._met_flush_pending:
            self._met_flush_pending = True
            def _flush():
                self._met_flush_pending = False
                for idx, (v, s, c) in self._met_buf.items():
                    try:
                        self.mv[idx].config(text=v, fg=c or TEXT)
                        if s is not None:
                            self.ms[idx].config(text=s)
                    except Exception as _exc:
                        _file_logger.debug("suppressed error: %s", _exc)
                self._met_buf.clear()
            self.root.after(0, _flush)

    def _on_mode(self):
        if self.dry_var.get():
            self.mode_lbl.config(text="● PAPER MODE — no real orders", fg=AMBER, bg=BG2)
            self._live_balance = None
            self._refresh_metrics()
        else:
            self.mode_lbl.config(text="⚡ LIVE TRADING — real money", fg="#ffffff", bg="#8b0000")
            ak = self.mexc_key_e.get().strip() if hasattr(self, "mexc_key_e") else ""
            sc = self.mexc_sec_e.get().strip() if hasattr(self, "mexc_sec_e") else ""
            if ak and sc:
                self._met(3, "fetching…", "MEXC futures USDT", MUTED)
                self._met(0, "fetching…", "live P&L", MUTED)
                self._balance_fetch = 0
                self._fetch_live_balance()
            else:
                self._met(3, "no API keys", "add keys in sidebar", RED)
                self._met(0, "—", "live P&L", MUTED)

    def _active_pairs(self):
        """Returns list of currently enabled pairs.
        Falls back to SCAN_PAIRS (config-aware) rather than the full PAIRS UI list,
        so that config["pairs"] customisation is respected even before the UI initialises.
        """
        return [p for p, v in self._pair_vars.items() if v.get()] if hasattr(self, "_pair_vars") else list(SCAN_PAIRS)

    def _set_all_pairs(self, state):
        for v in self._pair_vars.values(): v.set(state)
        self._on_pair_toggle()

    def _set_preset(self, pairs):
        for p, v in self._pair_vars.items(): v.set(p in pairs)
        self._on_pair_toggle()

    def _on_pair_toggle(self, _=None):
        """Update scan interval hint when pairs change."""
        n = len(self._active_pairs())
        # Each pair needs: 0.45s stagger + ~3s avg API response = ~3.45s per pair
        # Add 5s safety buffer so cycle completes before next one starts
        min_secs = round(n * 3.45 + 5)
        # Round up to nearest available interval
        if   min_secs <= 10: rec = "10s"
        elif min_secs <= 15: rec = "15s"
        elif min_secs <= 20: rec = "20s"
        elif min_secs <= 25: rec = "25s"
        elif min_secs <= 30: rec = "30s"
        elif min_secs <= 35: rec = "35s"
        elif min_secs <= 40: rec = "40s"
        elif min_secs <= 45: rec = "45s"
        elif min_secs <= 60: rec = "60s"
        elif min_secs <= 90: rec = "90s"
        elif min_secs <= 120: rec = "2 min"
        else:                 rec = "3 min"
        if hasattr(self, "_ivl_hint"):
            self._ivl_hint.config(
                text=f"{n} pairs active · min recommended: {rec}",
                fg=CYAN if self._ivl_satisfies_min(n) else RED)
        # Note: we just show the hint — never auto-change the user's setting

    def _ivl_satisfies_min(self, n=None):
        if n is None: n = len(self._active_pairs())
        min_secs = max(10, round(n * 0.45 + 2))
        return self._ivl() >= min_secs

    def _on_interval(self, _=None):
        """Update hint colour when interval is changed."""
        self._on_pair_toggle()

    def _on_dual_tf(self, _=None):
        enabled = self.dual_tf_var.get()
        self._dtf_lbl.config(
            text="ON" if enabled else "OFF",
            fg=CYAN if enabled else MUTED)
        if enabled:
            # Dual TF: force trend TF to Min5 if currently set to Min1
            if self.tf_cb.get() == "Min1":
                self.tf_cb.set("Min5")
            # Update interval hint for dual TF mode (use cached values)
            trend_ivl = self._trend_scan_interval
            entry_ivl = self._entry_scan_interval
            self._ivl_hint.config(
                text=f"Dual TF: Trend scan {trend_ivl}s (Min5), Min1 check within each cycle",
                fg=CYAN)
            # Disable interval dropdown in dual TF mode
            self.int_cb.config(state="disabled")
        else:
            # Reset hint for single TF mode — if Min1 is selected, note pure mode
            if hasattr(self, "tf_cb") and self.tf_cb.get() == "Min1":
                self._ivl_hint.config(
                    text="Min1 pure mode — tighter body/wick/RSI/EMA/score filters active",
                    fg=AMBER)
            else:
                self._ivl_hint.config(text="", fg=CYAN)
            # Enable interval dropdown
            self.int_cb.config(state="readonly")
        try:
            lbl_widget = self.tf_cb.master.winfo_children()[0]
            if enabled:
                lbl_widget.config(text="Trend TF", fg=CYAN)
            else:
                lbl_widget.config(text="Candle TF", fg=SUB)
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)

    def _on_lev(self, _=None):
        lv = self._lev()
        if lv == 0: return
        wipe_pct = round(100 / lv, 1)
        msg = f"{lv}x: {wipe_pct}% adverse move wipes margin"
        col = AMBER if lv <= 20 else RED
        try: self.lev_warn_inline.config(text=msg, fg=col)
        except: pass
        try: self.lev_warn.config(text=msg, fg=col)
        except: pass
        # Auto-set optimal SL/TP for leverage — user can still change after
        self._auto_sl_tp(lv)

    def _auto_sl_tp(self, lv):
        """
        Set SL/TP based on PRICE MOVE needed to survive candle noise, not margin %.
        Key insight: at 50x the old values (SL 0.12% / TP 0.25%) are within normal
        wick range — trades get stopped out before having any chance to work.

        SL must be at least 2-3x a typical 5-min candle ATR (~0.15-0.25% for crypto).
        TP = 2.2x SL for 1:2.2 R/R (profitable at 32%+ win rate).

        These are PRICE MOVE %s, not margin return %s:
          50x + SL 0.40% price = 20% margin loss if stopped — survivable and realistic
          50x + old SL 0.12% price = 6% margin loss — hit by normal wicks constantly
        User can always adjust after selecting leverage.
        """
        # sl/tp are price-move percentages (market move, not margin return)
        # TP is set wide enough that after round-trip fees (~0.12%) + slippage (~0.05%),
        # a net R/R of ≥ 1.5 is preserved even if the ATR-widener expands SL slightly.
        if   lv >= 150: sl, tp = "0.20%", "0.55%"
        elif lv >= 100: sl, tp = "0.25%", "0.65%"
        elif lv >= 75:  sl, tp = "0.30%", "0.75%"
        elif lv >= 50:  sl, tp = "0.40%", "1.00%"
        elif lv >= 40:  sl, tp = "0.50%", "1.30%"
        elif lv >= 25:  sl, tp = "0.60%", "1.60%"
        elif lv >= 20:  sl, tp = "0.70%", "2.00%"  # widened: 0.17% fee+slip eats ~8.5% of 2.0% TP
        elif lv >= 15:  sl, tp = "0.80%", "2.50%"  # widened: net reward 2.33% vs net risk 0.97% → R/R 2.4
        elif lv >= 10:  sl, tp = "0.90%", "2.80%"  # widened: 0.17% fee+slip leaves 2.63% net; real headroom
        elif lv >= 5:   sl, tp = "1.5%",  "3.50%"
        elif lv >= 3:   sl, tp = "2.0%",  "4.50%"
        else:           sl, tp = "2.5%",  "5.50%"
        try:
            self.sl_cb.set(sl)
            self.tp_cb.set(tp)
            # Brief hint showing what changed and why
            liq_pct  = round(100 / lv, 1)
            sl_f     = float(sl.replace("%",""))
            tp_f     = float(tp.replace("%",""))
            sl_margin = round(sl_f * lv, 1)
            tp_margin = round(tp_f * lv, 1)
            hint = (f"Auto-set for {lv}x:  SL {sl} price ({sl_margin}% margin)  "
                    f"TP {tp} price ({tp_margin}% margin)  |  LIQ at {liq_pct}%")
            try:
                self.lev_warn.config(text=hint, fg=CYAN)
                self.root.after(5000, lambda: self.lev_warn.config(
                    text=f"{lv}x: {liq_pct}% adverse move wipes margin",
                    fg=AMBER if lv <= 20 else RED))
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)

    def _lev_opts(self, pair):
        max_lev = PAIR_MAX_LEV.get(pair, 100)
        steps = [1,2,3,5,10,15,20,25,30,40,50,75,100,125,150,200,250,300,400,500]
        return [f"{l}x" for l in steps if l <= max_lev]

    def _recommended_lev(self, margin: float) -> tuple:
        """
        Return (recommended_leverage, description) based on the user's margin input
        and standard margin-requirement table.

        Each tier has an explicit minimum_margin_usdt floor derived from the
        "Recommended Usable Margin ≥ N× requirement" column:

          Leverage  Min-Margin-Req  Rec Usable   Min USDT floor  Markets
          --------  --------------  -----------  --------------  -------
          200x      0.5%            ≥5× req      ≥ 500 USDT      Scalping / very high-risk
          100x      1%              ≥3× req      ≥ 150 USDT      Short-term Forex
          50x       2%              ≥2× req      ≥  50 USDT      Forex majors
          30x       3.33%           ≥2× req      ≥  25 USDT      Major currency pairs
          20x       5%              ≥2× req      ≥  15 USDT      Major indices / gold
          10x       10%             ≥2× req      ≥   8 USDT      Minor indices / commodities
          5x        20%             ≥2× req      ≥   5 USDT      Individual shares / EM
          2x        50%             ≥2× req      ≥   2 USDT      High-volatility stocks

        Floor derivation (example 200x):
          Exchange min notional on MEXC ≈ $6  →  min margin = $6/200 = $0.03
          Rec usable = 5× that = $0.15  — far too small to be meaningful.
          Instead we anchor to a practical minimum position size of $100 USDT
          notional and apply the rec_mult:
            200x: ($100/200) × 5 = $2.50 → still tiny, so use $500 hard floor
            (at 200x even a $500 margin is only $100k notional — reasonable for scalping)
          Lower tiers are anchored to $50 notional × rec_mult, giving the table above.
        """
        # (leverage, min_margin_usdt_floor, label)
        # Floors chosen so each tier requires a margin that actually makes sense
        # for the leverage level and target market, not just clearing MEXC's $6 minimum.
        tiers = [
            (200, 500.0, "Scalping / very high-risk"),
            (100, 150.0, "Short-term Forex"),
            ( 50,  50.0, "Forex majors"),
            ( 30,  25.0, "Major currency pairs"),
            ( 20,  15.0, "Major indices / gold"),
            ( 10,   8.0, "Minor indices / commodities"),
            (  5,   5.0, "Individual shares / EM"),
            (  2,   2.0, "High-volatility stocks"),
        ]
        best_lev, best_desc = 2, "High-volatility stocks"
        for lev, min_margin, label in tiers:
            if margin >= min_margin:
                best_lev, best_desc = lev, label
                break
        # Cap to what the selected pair actually allows
        pair = self.pair_cb.get() if hasattr(self, "pair_cb") else "BTC_USDT"
        max_lev = PAIR_MAX_LEV.get(pair, 100)
        best_lev = min(best_lev, max_lev)
        # Find closest available option (round down)
        steps = [1,2,3,5,10,15,20,25,30,40,50,75,100,125,150,200,250,300,400,500]
        available = [l for l in steps if l <= max_lev]
        chosen = max((l for l in available if l <= best_lev), default=available[0])
        return chosen, best_desc

    def _on_margin_change(self, _=None):
        """Called whenever the margin entry loses focus or Enter is pressed.
        Computes the recommended leverage, applies it, and shows a hint."""
        try:
            mg = float(self.margin_e.get() or 0)
        except ValueError:
            return
        if mg <= 0:
            return
        rec_lev, rec_desc = self._recommended_lev(mg)
        rec_str = f"{rec_lev}x"
        opts = self._lev_opts(self.pair_cb.get() if hasattr(self, "pair_cb") else "BTC_USDT")
        if rec_str in opts:
            self.lev_cb.set(rec_str)
            self._on_lev()
        hint = (f"Margin ${mg:.0f} → recommended {rec_lev}x  ({rec_desc})")
        try:
            self.lev_rec_lbl.config(text=hint, fg=CYAN)
        except Exception:
            pass

    def _lev(self):
        try: return int(self.lev_cb.get().replace("x","").strip())
        except: return 10

    def _thresh(self): return float(self.thr_cb.get().split("/")[0])
    def _sl(self):    return float(self.sl_cb.get().replace("%","")) / 100
    def _tp(self):    return float(self.tp_cb.get().replace("%","")) / 100
    def _ivl(self):
        # For dual TF mode, use trend scan interval (slower for Min5)
        # For single TF mode, use the configured interval from dropdown
        dual_mode = self.dual_tf_var.get() if hasattr(self,"dual_tf_var") else False
        if dual_mode:
            # In dual mode, we're primarily scanning Min5 for trend confirmation
            # so use the slower trend scan interval (cached to avoid disk I/O)
            return getattr(self, "_trend_scan_interval", 20)
        else:
            return {"1s":1,"2s":2,"3s":3,"4s":4,"5s":5,"6s":6,"7s":7,"8s":8,"9s":9,"10s":10,"15s":15,"20s":20,"25s":25,"30s":30,"35s":35,"40s":40,"45s":45,"60s":60,"90s":90,"2 min":120,"3 min":180,"5 min":300,"10 min":600}.get(self.int_cb.get(),30)
    def _max_trades(self):
        v = self.max_trades_cb.get()
        return 999 if "Unlimited" in v else int(v.split(" ")[0])
    def _stack_max(self):
        return int(self.stack_max_cb.get().replace("x",""))
    def _stack_thresh(self):
        return float(self.stack_thresh_cb.get().split("/")[0])

    def _toggle_claude(self):
        enabled = not self.claude_enabled.get()
        self.claude_enabled.set(enabled)
        if enabled:
            self.claude_toggle.config(text="  ON  ✅  —  click to disable", bg="#0d2818", fg=GREEN)
            self.claude_entry.config(state="normal")
            self._show_btn.config(state="normal")
            self._test_btn.config(state="normal", bg=PURPLE, fg=TEXT)
            self.claude_status.config(text="Paste key and click Test ▶", fg=AMBER)
        else:
            self.claude_toggle.config(text="  OFF  —  click to enable", bg=BG3, fg=MUTED)
            self.claude_entry.config(state="disabled")
            self._show_btn.config(state="disabled")
            self._test_btn.config(state="disabled", bg=BG3, fg=MUTED)
            self.claude_status.config(text="OFF — local signals only", fg=MUTED)

    def _test_claude(self):
        key = self.claude_entry.get().strip()
        if not key:
            self.claude_status.config(text="⚠ Paste your key first", fg=AMBER); return
        self.claude_status.config(text="Testing…", fg=AMBER)
        self.root.update()
        def _go():
            ok, msg = test_claude_key(key)
            col = GREEN if ok else RED
            self.root.after(0, lambda: self.claude_status.config(text=msg, fg=col))
            if ok: self._log("Claude API key verified.", GREEN)
        threading.Thread(target=_go, daemon=True).start()

    def _save_keys(self):
        payload = {"mexc_api_key":    self.mexc_key_e.get().strip(),
                   "mexc_api_secret": self.mexc_sec_e.get().strip(),
                   "anthropic_key":   self.claude_entry.get().strip()}
        _atomic_write(KEYS_FILE, _encrypt_keys(payload))
        try:
            os.chmod(KEYS_FILE, 0o600)  # owner read/write only
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)
        enc_note = " (encrypted)" if _CRYPTO_OK else " (plaintext — install cryptography to encrypt)"
        self._log(f"Keys saved{enc_note} → {KEYS_FILE}", GREEN)

    def _load_keys(self):
        if not os.path.exists(KEYS_FILE): return
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                raw = f.read()
            k = _decrypt_keys(raw)
            self.mexc_key_e.delete(0,"end"); self.mexc_key_e.insert(0, k.get("mexc_api_key",""))
            self.mexc_sec_e.delete(0,"end"); self.mexc_sec_e.insert(0, k.get("mexc_api_secret",""))
            ck = k.get("anthropic_key","")
            self.claude_entry.delete(0,"end"); self.claude_entry.insert(0, ck)
            if ck: self.claude_status.config(text="Key loaded — click Test to verify", fg=MUTED)
        except Exception as e:
            self._log(f"Failed to load saved keys: {e}", AMBER)

    def _refresh_metrics(self):
        if getattr(self, "_metrics_refresh_pending", False):
            return
        self._metrics_refresh_pending = True
        self.root.after(150, self._do_refresh_metrics)

    def _do_refresh_metrics(self):
        self._metrics_refresh_pending = False
        s    = self.state
        dry  = self.dry_var.get()
        # Use len(trades) as the single source of truth for trade count —
        # wins/losses counters can drift if a sync closes a position.
        n    = len(s.trades)
        wins = sum(1 for t in s.trades if t.get("pnl_usdt", 0) >= 0)
        losses = n - wins
        np_  = len(s.positions)
        nh   = sum(1 for p in s.positions.values() if p.hedge_of)
        pc   = GREEN if s.total_pnl >= 0 else RED

        # ── Session P&L — always from state.total_pnl (tracks this session) ──
        pnl_sign = "+" if s.total_pnl >= 0 else ""
        if not dry and self._live_balance:
            urp = self._live_balance.get("unrealised", 0)
            urp_str = f"  open {urp:+.2f}" if abs(urp) > 0.0001 else ""
            sub_pnl = f"session{urp_str}"
        else:
            sub_pnl = f"session"
        self._met(0, f"{pnl_sign}${abs(s.total_pnl):.2f}", sub_pnl, pc)

        # ── Win rate ──────────────────────────────────────────────────────────
        wr  = f"{wins/n*100:.1f}%" if n > 0 else "—"
        avg = f"${s.total_pnl/n:+.2f} avg" if n > 0 else "avg  $—"
        self._met(1, wr, f"{wins}W / {losses}L")
        self._met(2, str(n), avg)

        # ── Balance — paper vs live ───────────────────────────────────────────
        if dry:
            bal_val = f"{s.balance:,.2f} USDT"
            bal_sub = "paper balance"
            bal_col = GREEN if s.balance >= 1000 else RED
        else:
            lb = self._live_balance
            if lb:
                actual_used = sum(p.margin for p in self.state.positions.values())
                equity    = lb["equity"]
                available = lb["available"]
                unrealised = lb.get("unrealised", 0)
                bal_val = f"{equity:,.2f} USDT"
                if actual_used > 0.001:
                    # Trades open — show margin in use
                    bal_sub = f"avail {available:,.2f}  in use {actual_used:,.2f}"
                elif abs(unrealised) > 0.001:
                    # No trades but unrealised PnL affecting balance
                    bal_sub = f"avail {available:,.2f}  upnl {unrealised:+.2f}"
                else:
                    bal_sub = f"{available:,.2f} available"
                bal_col = GREEN if equity > 0 else RED
            else:
                bal_val = "fetching…"
                bal_sub = "MEXC balance"
                bal_col = MUTED
        self._met(3, bal_val, bal_sub, bal_col)

        # ── Open positions & liqs ─────────────────────────────────────────────
        self._met(4, str(np_), f"{nh} hedged", CYAN if np_ > 0 else MUTED)
        liq_count = sum(1 for t in s.trades if "LIQUIDAT" in t.get("status","").upper())
        lp = f"{liq_count/n*100:.1f}% of trades" if n > 0 else "0.0% of trades"
        self._met(5, str(liq_count), lp, RED if liq_count > 0 else MUTED)

        # ── Runtime — updated every second by _tick_uptime() ─────────────────
        # Only update here if the bot was just stopped (tick timer is cancelled).
        if not self.bot_running:
            self._met(6, "—", "bot stopped", MUTED)

        # ── Last signal ───────────────────────────────────────────────────────
        if self._last_signal_pair:
            ago = int(time.time() - self._last_signal_time) if self._last_signal_time else 0
            ago_str = f"{ago//60}m {ago%60}s ago" if ago >= 60 else f"{ago}s ago"
            sig_col = GREEN if self._last_signal_dir == "LONG" else (
                      RED if self._last_signal_dir == "SHORT" else MUTED)
            self._met(7, pair_label(self._last_signal_pair),
                      f"{self._last_signal_dir} · {ago_str}", sig_col)
        else:
            self._met(7, "—", "no signal yet", MUTED)

    def _fetch_live_balance(self):
        """Background fetch of live MEXC account balance every 10s."""
        if self.dry_var.get(): return
        ak = self.mexc_key_e.get().strip()
        sc = self.mexc_sec_e.get().strip()
        if not ak or not sc: return
        # Refresh faster when positions are open
        has_open = len(self.state.positions) > 0 if hasattr(self, "state") else False
        min_interval = 3 if has_open else 12
        if time.time() - self._balance_fetch < min_interval: return
        self._balance_fetch = time.time()
        def _go():
            try:
                data = get_live_account(ak, sc)
                self._live_balance = data
                self.root.after(0, self._refresh_metrics)
            except Exception as e:
                err = str(e)[:80]
                self._log(f"Balance fetch error: {err}", RED)
                self.root.after(0, lambda: self._met(3, "API error", err[:22], RED))
                self.root.after(0, lambda: self._met(0, "API error", "check keys", RED))
        threading.Thread(target=_go, daemon=True).start()

    def _save(self):
        s = self.state
        pos_list = [asdict(p) for p in s.positions.values()]
        payload = {"balance": s.balance, "total_pnl": s.total_pnl,
                   "wins": s.wins, "losses": s.losses, "liqs": s.liqs,
                   "trades": s.trades, "positions": pos_list}
        try:
            _atomic_write(STATE_FILE, json.dumps(payload, indent=2))
        except Exception as e:
            try: _file_logger.error("State save failed: %s", e)
            except Exception as log_e:
                # Last resort: if logging fails, at least print to stderr
                import sys
                print(f"CRITICAL: State save failed and logging also failed: {e}", file=sys.stderr)
                print(f"Logging error: {log_e}", file=sys.stderr)

    # ── BOT CONTROL ───────────────────────────────────────────────────────────
    # ── MANUAL POSITION CONTROLS ─────────────────────────────────────────────
    def _manual_close_position(self, pid):
        """Manually close a position at market price."""
        if pid not in self.state.positions:
            return
        pos = self.state.positions[pid]
        px  = self.current_prices.get(pos.symbol, pos.entry_price)
        dry = self.dry_var.get()
        ak  = self.mexc_key_e.get().strip()
        asc = self.mexc_sec_e.get().strip()
        lev = pos.leverage

        def _do():
            closed, status, pnl = self._check_exit_force(pos, px, lev, dry, ak, asc)
            if closed:
                col = GREEN if status == "WIN" else (PURPLE if status == "LIQUIDATED" else RED)
                self._log_event(f"MANUAL CLOSE [{status}] {pos.direction} "
                          f"{pos.symbol} @ ${px:,.4f}  PnL ${pnl:+.2f}", col)
                self._price_history.pop(pid, None)
                self._price_peak.pop(pid, None)
                self._stale_checked.discard(pid)
                self._refresh_metrics()
                self._save()
                self.root.after(0, self._refresh_trades_tab)
        threading.Thread(target=_do, daemon=True).start()

    def _manual_hedge_position(self, pid):
        """Manually open a hedge for a position."""
        if pid not in self.state.positions:
            return
        pos = self.state.positions[pid]
        px  = self.current_prices.get(pos.symbol, pos.entry_price)
        dry = self.dry_var.get()
        ak  = self.mexc_key_e.get().strip()
        asc = self.mexc_sec_e.get().strip()
        sl  = self._sl(); tp = self._tp()
        lev = pos.leverage

        # Check not already hedged
        already = any(p.hedge_of == pid for p in self.state.positions.values())
        if already:
            self._log(f"Position {pid[:6]} already has a hedge", AMBER)
            return

        hedge_dir = "SHORT" if pos.direction == "LONG" else "LONG"

        def _do():
            hid = self._open_position(pos.symbol, hedge_dir, px,
                                       pos.margin * 0.5, lev, sl, tp,
                                       dry, ak, asc, hedge_of=pid)
            if hid:
                self._log_event(f"MANUAL HEDGE: {hedge_dir} {pos.symbol} "
                          f"@ ${px:,.4f}  (hedging {pos.direction})", AMBER)
                self._refresh_metrics()
                self._save()
        threading.Thread(target=_do, daemon=True).start()

    def _check_exit_force(self, pos, px, lev, dry, ak, asc):
        """Force-close a position at current market price regardless of SL/TP."""
        d = pos.direction
        raw = (px - pos.entry_price) / pos.entry_price if d == "LONG"               else (pos.entry_price - px) / pos.entry_price
        gross_pnl = raw * pos.leverage * pos.margin
        fee    = pos.size_usdt * (self._fee_taker * 2)   # round-trip taker fees
        pnl    = round(gross_pnl - fee, 4)
        status = "WIN" if pnl >= 0 else "LOSS"

        if not dry:
            side = 4 if d == "LONG" else 2   # Futures: 4=close long, 2=close short
            cs   = PAIR_CONTRACT_SIZE.get(pos.symbol, 1.0)
            # Prefer exchange holdVol for accurate contract count
            exch_vol = getattr(pos, "exchange_hold_vol", 0.0) or 0.0
            if exch_vol > 0:
                vol = int(round(exch_vol))  # exchange holdVol is already integer contracts
            else:
                # Fallback: compute integer contracts from position USDT size
                cs_  = PAIR_CONTRACT_SIZE.get(pos.symbol, 1.0)
                px__ = self.current_prices.get(pos.symbol, pos.entry_price)
                vol  = max(1, int(pos.size_usdt / (px__ * cs_))) if cs_ > 0 and px__ > 0 else 1
            if vol <= 0:
                self._log_event(f"⛔ Manual close aborted — vol=0 for {pos.symbol}", RED)
                return False, None, 0
            close_ok = False
            try:
                resp = mexc_private("POST", "/api/v1/private/order/submit",
                                    {"symbol": pos.symbol, "price": 0, "vol": vol,
                                     "side": side, "type": 5, "openType": 1},
                                    ak, asc, dry)
                if resp and resp.get("success"):
                    close_ok = True
                else:
                    err_code = resp.get("code", "?") if resp else "no response"
                    err_msg  = resp.get("message", resp.get("msg", "")) if resp else ""
                    self._log(f"⚠ Manual close REJECTED [{err_code}] {pos.symbol}: {err_msg}", RED)
                    # Retry with fresh holdVol
                    try:
                        r2 = mexc_private("GET", "/api/v1/private/position/open_positions",
                                          {}, ak, asc, False)
                        raw2 = r2.get("data", [])
                        if isinstance(raw2, dict):
                            raw2 = raw2.get("list", raw2.get("data", []))
                        for ep2 in raw2:
                            pt2  = int(ep2.get("positionType", 0))
                            dir2 = "LONG" if pt2 == 1 else "SHORT"
                            if ep2.get("symbol") == pos.symbol and dir2 == d:
                                fresh_vol = float(ep2.get("holdVol", 0))
                                if fresh_vol > 0:
                                    resp2 = mexc_private(
                                        "POST", "/api/v1/private/order/submit",
                                        {"symbol": pos.symbol, "price": 0,
                                         "vol": round_vol(pos.symbol, fresh_vol),
                                         "side": side, "type": 5, "openType": 1},
                                        ak, asc, dry)
                                    if resp2 and resp2.get("success"):
                                        close_ok = True
                                        self._log(f"✓ Manual close retry OK: {pos.symbol}", CYAN)
                                    else:
                                        self._log_event(f"⛔ Manual close retry FAILED: {pos.symbol} "
                                                  f"→ {resp2.get('message','?') if resp2 else 'no response'}", RED)
                                break
                    except Exception as retry_err:
                        self._log_event(f"⛔ Manual close retry error: {retry_err}", RED)
            except Exception as e:
                self._log_event(f"⛔ Manual close exception: {e}", RED)
                return False, None, 0

            if not close_ok:
                self._log_event(f"⛔ MANUAL CLOSE FAILED — {pos.symbol} still open on MEXC! "
                          f"Close manually on the exchange.", RED)
                return False, None, 0

        self.state.total_pnl  = round(self.state.total_pnl + pnl, 4)
        if self.dry_var.get():
            self.state.balance = round(self.state.balance + pos.margin + pnl, 4)
        else:
            self.state.balance = round(self.state.balance + pnl, 4)
        if pnl >= 0: self.state.wins  += 1
        else:        self.state.losses += 1
        self._adaptive_engine.log_trade(pnl >= 0)

        self.state.trades.append({
            "symbol": pos.symbol, "direction": d,
            "entry_price": pos.entry_price, "exit_price": px,
            "margin": pos.margin, "leverage": pos.leverage,
            "pnl_usdt": pnl, "status": f"MANUAL {status}",
            "hedge": bool(pos.hedge_of),
            "opened_at": pos.opened_at,
            "closed_at": datetime.now(timezone.utc).isoformat()})

        with self._positions_lock:
            self.state.positions.pop(pos.id, None)
        return True, status, pnl

    def _on_adaptive_toggle(self, _=None):
        # Called by button click — toggle the var, then apply
        if hasattr(self, "_adaptive_toggle_btn"):
            self.adaptive_var.set(not self.adaptive_var.get())
        enabled = self.adaptive_var.get()
        if enabled:
            if hasattr(self, "_adaptive_toggle_btn"):
                self._adaptive_toggle_btn.config(
                    text="  ON  ⚡  —  click to disable",
                    bg="#081a1a", fg=CYAN)
            self._adaptive_status_lbl.config(
                text="Engine adjusts threshold by ATR volatility + win rate",
                fg=DIM)
            self._adaptive_info.config(
                text="  • Dead market (low ATR) → +1.0\n"
                     "  • Strong breakout (high ATR) → −0.5\n"
                     "  • Win rate < 40% → floor raised to 6.5",
                fg=MUTED)
        else:
            if hasattr(self, "_adaptive_toggle_btn"):
                self._adaptive_toggle_btn.config(
                    text="  OFF  —  click to enable",
                    bg=BG3, fg=MUTED)
            self._adaptive_status_lbl.config(
                text="Fixed threshold only — no auto-adjustment",
                fg=MUTED)
            self._adaptive_info.config(
                text="  • Uses Min signal setting as-is\n"
                     "  • No ATR or win rate corrections",
                fg=DIM)
            self._adaptive_thr = None   # clear any active adaptation
            self._hold_streak  = 0

    def _toggle_overnight(self):
        enabled = not self.overnight_var.get()
        self.overnight_var.set(enabled)
        # Mark as manually overridden so _check_overnight_mode won't clobber it
        self._overnight_manual_override = True
        self._apply_overnight_ui(enabled, forced=True)

    def _apply_overnight_ui(self, enabled, forced=False):
        """Update overnight mode UI elements and apply threshold changes."""
        source = "forced" if forced else "auto"
        if enabled:
            if hasattr(self, "overnight_btn"):
                self.overnight_btn.config(
                    text="  ON  🌙  —  click to disable",
                    bg="#0a2a2a", fg=TEAL)
            if hasattr(self, "_overnight_detail"):
                self._overnight_detail.config(fg=TEAL)
            if hasattr(self, "_overnight_conn_dot"):
                self._overnight_conn_dot.config(fg=TEAL)
            if hasattr(self, "_overnight_status_lbl"):
                lbl = "  ONLINE — active now" if forced else "  ONLINE — auto-activated (UTC 22:00–08:00)"
                self._overnight_status_lbl.config(text=lbl, fg=TEAL)
            # Update header icon
            if hasattr(self, "overnight_lbl"):
                self.overnight_lbl.config(text="🌙 ONLINE", fg=TEAL)
            # Relax threshold: step down by 0.5 from current value, store original
            try:
                _OPT = ["2.0/9","3.0/9","3.5/9","4.0/9","4.5/9","5.0/9","5.5/9","6.0/9","7.0/9","8.0/9"]
                cur = self.thr_cb.get()
                if cur in _OPT:
                    cur_idx = _OPT.index(cur)
                    if cur_idx > 0:
                        relaxed = _OPT[cur_idx - 1]
                        self._overnight_pre_thr = cur   # remember so we can restore exactly
                        self.thr_cb.set(relaxed)
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)
            if forced:
                self._log_event("🌙 Overnight mode ON — threshold relaxed, dual TF filter loosened", TEAL)
            else:
                self._log_event("🌙 Overnight mode auto-activated (GMT hour: {}) — ONLINE".format(
                    datetime.now(timezone.utc).hour), TEAL)
        else:
            if hasattr(self, "overnight_btn"):
                self.overnight_btn.config(
                    text="  OFF  —  click to force ON",
                    bg=BG3, fg=MUTED)
            if hasattr(self, "_overnight_detail"):
                self._overnight_detail.config(fg=MUTED)
            if hasattr(self, "_overnight_conn_dot"):
                self._overnight_conn_dot.config(fg=DIM)
            if hasattr(self, "_overnight_status_lbl"):
                lbl = "  OFFLINE — inactive" if forced else "  OFFLINE — auto-managed by UTC time"
                self._overnight_status_lbl.config(text=lbl, fg=DIM)
            # Update header icon
            if hasattr(self, "overnight_lbl"):
                self.overnight_lbl.config(text="🌙 OFFLINE", fg=MUTED)
            # Restore threshold: use stored pre-overnight value if available
            try:
                pre = getattr(self, "_overnight_pre_thr", None)
                if pre and self.thr_cb.get() != pre:
                    self.thr_cb.set(pre)
                    self._overnight_pre_thr = None
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)
            if forced:
                self._log_event("☀ Overnight mode OFF — normal daytime filters restored", CYAN)
            else:
                self._log_event("☀ Overnight mode auto-deactivated (GMT hour: {}) — OFFLINE".format(
                    datetime.now(timezone.utc).hour), CYAN)

    def _rsi_limit_for_dual_tf(self):
        """RSI limit for dual-TF entry filter. Loosened in overnight mode."""
        return 75 if (hasattr(self, "overnight_var") and self.overnight_var.get()) else 65

    def _check_overnight_mode(self):
        """Auto-detect overnight mode based on UTC hour (22:00-08:00 = overnight).
        Manual override (button) is respected but only protects against being turned
        OFF early — the schedule can still end overnight mode at 08:00 UTC as normal.
        If the schedule says it should be ON, clear the override (schedule caught up)."""
        hour = datetime.now(timezone.utc).hour
        is_night = hour >= 22 or hour < 8
        if getattr(self, "_overnight_manual_override", False):
            if is_night:
                # Schedule now agrees we should be ON — clear override, auto resumes
                self._overnight_manual_override = False
            else:
                # Still outside scheduled hours; honour the manual early-ON and skip
                return
        if is_night != self.overnight_var.get():
            self.overnight_var.set(is_night)
            self.root.after(0, lambda n=is_night: self._apply_overnight_ui(n, forced=False))

    def _claude_position_monitor(self, pid, claude_key=None):
        """
        Background thread: monitors an open position every 30s.
        Runs claude_sl_update, claude_near_tp_check, claude_stale_trade_check,
        claude_hedge_check as appropriate. Exits when position closes.
        """
        while not self._stop_event.is_set():
            time.sleep(30)
            if pid not in self.state.positions:
                return  # position closed

            pos    = self.state.positions[pid]
            ck     = claude_key if claude_key is not None else (self.claude_entry.get().strip() if self.claude_enabled.get() else "")
            if claude_key is not None:
                if not ck:
                    continue
            elif not ck or not self.claude_enabled.get():
                continue

            cur_px = self.current_prices.get(pos.symbol, pos.entry_price)
            sig    = self.pair_signals.get(pos.symbol) or {}
            dry    = self.dry_var.get()
            ak     = self.mexc_key_e.get().strip()
            asc    = self.mexc_sec_e.get().strip()
            sl     = self._sl(); tp = self._tp()
            mg     = float(self.margin_e.get())
            lev    = pos.leverage
            hedge_on = self.hedge_var.get()

            if pos.direction == "LONG":
                raw_chg = (cur_px - pos.entry_price) / pos.entry_price
            else:
                raw_chg = (pos.entry_price - cur_px) / pos.entry_price
            drawdown_pct = raw_chg * pos.leverage * 100

            # Track price history
            hist = self._price_history.setdefault(pid, [])
            hist.append((time.time(), cur_px))
            if len(hist) > 5: hist.pop(0)

            # Track price peak (furthest favourable excursion from entry)
            if pos.direction == "LONG":
                self._price_peak[pid] = max(self._price_peak.get(pid, pos.entry_price), cur_px)
            else:
                self._price_peak[pid] = min(self._price_peak.get(pid, pos.entry_price), cur_px)

            velocity_pct = 0.0
            if len(hist) >= 3:
                oldest_px = hist[-3][1]
                if pos.direction == "LONG":
                    velocity_pct = (cur_px - oldest_px) / pos.entry_price * 100
                else:
                    velocity_pct = (oldest_px - cur_px) / pos.entry_price * 100

            def _track_cost(tok):
                cost = tok * 0.000001 * 1.5
                self._claude_tokens += tok
                self._claude_cost    = round(self._claude_cost + cost, 6)
                self._claude_calls  += 1
                self.root.after(0, lambda: (
                    self._cost_lbl.config(text=f"${self._claude_cost:.4f}",
                        fg=AMBER if self._claude_cost > 0.01 else DIM),
                    self._calls_lbl.config(text=f"{self._claude_calls} calls")
                ) if hasattr(self, "_cost_lbl") else None)

            # SL update: if losing and moving against us
            if drawdown_pct < -1.0 and velocity_pct < -0.05:
                with self._claude_gate:
                    self._claude_gate_ts = time.time()
                    result = claude_sl_update(pos, cur_px, drawdown_pct, velocity_pct, sig, ck)
                if result:
                    _track_cost(result.get("tokens_used", 0))
                    action = result["action"]
                    reason = result["reason"]
                    if action == "TIGHTEN" and pid in self.state.positions:
                        new_sl = result["new_sl_price"]
                        old_sl = pos.stop_loss
                        self.state.positions[pid].stop_loss = new_sl
                        self._log_event(f"AI SL TIGHTENED: {pos.direction} {pair_label(pos.symbol)} "
                                  f"SL ${old_sl:,.4f} → ${new_sl:,.4f}  ({reason})", AMBER)
                        self._ai_log_event(pid, "🔒 SL TIGHTENED",
                            f"${old_sl:,.4f} → ${new_sl:,.4f}\n{reason}", AMBER)
                        self._save()
                        _ak = self.mexc_key_e.get().strip()   # FIX v2.2-#1
                        _asc = self.mexc_sec_e.get().strip()  # FIX v2.2-#1
                        threading.Thread(target=self._update_sl_on_mexc,
                                         args=(self.state.positions[pid], _ak, _asc),
                                         daemon=True).start()
                    elif action == "CLOSE" and pid in self.state.positions:
                        self._log_event(f"AI CLOSE SIGNAL: {pos.direction} {pair_label(pos.symbol)} — {reason}", RED)
                        self._ai_log_event(pid, "🚨 AI CLOSE",
                            f"Adverse momentum — closing now @ ${cur_px:,.4f}\n{reason}", RED)
                        if pos.direction == "LONG":
                            self.state.positions[pid].stop_loss = cur_px * 1.0001
                        else:
                            self.state.positions[pid].stop_loss = cur_px * 0.9999
                        _ak = self.mexc_key_e.get().strip()   # FIX v2.2-#1
                        _asc = self.mexc_sec_e.get().strip()  # FIX v2.2-#1
                        threading.Thread(target=self._update_sl_on_mexc,
                                         args=(self.state.positions[pid], _ak, _asc),
                                         daemon=True).start()
                        # FIX v2.2-#2: SL update alone is not an immediate close —
                        # MEXC stop orders only trigger when price reaches the level.
                        # Fire a market close so the position exits regardless.
                        # force_close=True: bypass the htp/hsl/hliq gate so the trade
                        # is always recorded in history even if price moves a tick
                        # between this thread spawn and execution.
                        threading.Thread(target=self._market_close_position,
                                         args=(self.state.positions[pid], _ak, _asc),
                                         kwargs={"force_close": True},
                                         daemon=True).start()
            if not pos.hedge_of:
                tp_total = abs(pos.take_profit - pos.entry_price)
                tp_left  = abs(pos.take_profit - cur_px)
                pct_to_tp = (tp_left / tp_total * 100) if tp_total else 100
                in_profit = ((cur_px > pos.entry_price) if pos.direction=="LONG"
                             else (cur_px < pos.entry_price))
                near_tp_key = f"near_tp_{pid}"
                already_checked = getattr(self, near_tp_key, 0)
                if in_profit and pct_to_tp <= 20.0 and time.time() - already_checked > 120:
                    setattr(self, near_tp_key, time.time())
                    with self._claude_gate:
                        self._claude_gate_ts = time.time()
                        result = claude_near_tp_check(pos, cur_px, pct_to_tp, sig, ck)
                    if result:
                        _track_cost(result.get("tokens_used", 0))
                        action = result["action"]
                        reason = result["reason"]
                        if action == "TAKE" and pid in self.state.positions:
                            self._log_event(f"AI TAKE PROFIT: {pos.direction} {pair_label(pos.symbol)} "
                                      f"@ ${cur_px:,.4f} ({pct_to_tp:.0f}% from TP) — {reason}", GREEN)
                            self._ai_log_event(pid, "💰 TAKE PROFIT EARLY",
                                f"{pct_to_tp:.0f}% gap remaining — taking profit now @ ${cur_px:,.4f}\n{reason}", GREEN)
                            if pos.direction == "LONG":
                                self.state.positions[pid].stop_loss = cur_px * 0.9999
                            else:
                                self.state.positions[pid].stop_loss = cur_px * 1.0001
                            _ak = self.mexc_key_e.get().strip()   # FIX v2.2-#1
                            _asc = self.mexc_sec_e.get().strip()  # FIX v2.2-#1
                            threading.Thread(target=self._update_sl_on_mexc,
                                             args=(self.state.positions[pid], _ak, _asc),
                                             daemon=True).start()
                            # FIX v2.2-#2: SL update alone is not an immediate close —
                            # MEXC stop orders only trigger when price reaches the level.
                            # Fire a market close so the position exits regardless.
                            # force_close=True: bypass the htp/hsl/hliq gate so the trade
                            # is always recorded in history even if price moves a tick
                            # between this thread spawn and execution.
                            threading.Thread(target=self._market_close_position,
                                             args=(self.state.positions[pid], _ak, _asc),
                                             kwargs={"force_close": True},
                                             daemon=True).start()
                        else:
                            self._ai_log_event(pid, "⏳ NEAR-TP HOLD",
                                f"{pct_to_tp:.0f}% gap remaining — holding\n{reason}", CYAN)

            if pid not in self.state.positions:
                return

            # ── AI Trail check: raise SL / extend TP when trade is winning ────
            # Triggers at 50% of TP distance reached, then again at 75%.
            # Never fires on hedge legs — only primary positions.
            if not pos.hedge_of and pid in self.state.positions:
                tp_total  = abs(pos.take_profit - pos.entry_price)
                tp_left   = abs(pos.take_profit - cur_px)
                pct_done  = (1 - tp_left / tp_total) * 100 if tp_total else 0
                in_profit = ((cur_px > pos.entry_price) if pos.direction == "LONG"
                             else (cur_px < pos.entry_price))
                raw_profit_pct = abs(cur_px - pos.entry_price) / pos.entry_price * 100
                profit_pct_margin = raw_profit_pct * pos.leverage  # FIX v2.2-#5: removed spurious *100 (raw_profit_pct is already a percentage)

                # Fire at ~50% and ~75% of TP progress (cooldown 5 min between calls)
                trail_key       = f"_trail_{pid}"
                trail_last      = getattr(self, trail_key, 0)
                trail_milestone = getattr(self, f"_trail_ms_{pid}", 0)

                # Fast-spike detection: bypass 5-min cooldown if gaining fast
                _raw_p = abs(cur_px - pos.entry_price) / pos.entry_price * 100
                _mins_open_t = 0
                try:
                    _op_t = datetime.fromisoformat(pos.opened_at.replace("Z", "+00:00"))
                    _mins_open_t = (datetime.now(timezone.utc) - _op_t).total_seconds() / 60
                except Exception:
                    pass
                _gain_per_candle_t = (_raw_p * pos.leverage) / max(1, _mins_open_t / 5)
                _sym_atr_t = self.pair_signals.get(pos.symbol, {}).get("atr_pct",
                             PAIR_ATR_MIN.get(pos.symbol, 0.06))
                _price_gain_per_candle_t = _raw_p / max(1, _mins_open_t / 5)
                _fast_spike_t = (_sym_atr_t > 0.05 and
                                 (_price_gain_per_candle_t >= _sym_atr_t * 3.0
                                  or pct_done >= 90.0))

                should_trail = (
                    in_profit
                    and pct_done >= 50.0
                    and pct_done < 95.0
                    and (time.time() - trail_last > 300 or _fast_spike_t)
                    and (trail_milestone == 0
                         or (pct_done >= 75.0 and trail_milestone < 75)
                         or _fast_spike_t)
                )

                if should_trail:
                    setattr(self, trail_key, time.time())
                    setattr(self, f"_trail_ms_{pid}",
                            75 if pct_done >= 75.0 else 50)
                    # Fee data for trail check
                    _open_fee_rate  = getattr(pos, "open_fee_rate",
                                              0.0004 if getattr(pos, "open_fee_type", "taker") == "maker"
                                              else 0.0006)
                    _open_fee_usdt  = pos.margin * pos.leverage * _open_fee_rate
                    _close_fee_rate = 0.0006   # MEXC API taker close fee (May 2026)
                    with self._claude_gate:
                        self._claude_gate_ts = time.time()
                        result = claude_trail_check(pos, cur_px, profit_pct_margin, sig, ck,
                                                    open_fee_usdt=_open_fee_usdt,
                                                    close_fee_rate=_close_fee_rate)
                    if result:
                        _track_cost(result.get("tokens_used", 0))
                        action = result["action"]
                        reason = result["reason"]
                        if action == "TRAIL" and pid in self.state.positions:
                            new_sl = result["new_sl_price"]
                            new_tp = result["new_tp_price"]
                            old_sl = pos.stop_loss
                            old_tp = pos.take_profit
                            sl_moved = abs(new_sl - old_sl) > cur_px * 0.0001
                            tp_moved = abs(new_tp - old_tp) > cur_px * 0.0001
                            if sl_moved or tp_moved:
                                self.state.positions[pid].stop_loss   = new_sl
                                self.state.positions[pid].take_profit = new_tp
                                sl_txt = f"SL ${old_sl:,.4g}→${new_sl:,.4g}" if sl_moved else ""
                                tp_txt = f"TP ${old_tp:,.4g}→${new_tp:,.4g}" if tp_moved else ""
                                change_txt = "  ".join(filter(None, [sl_txt, tp_txt]))
                                net_now  = result.get("net_pnl_now", 0)
                                fee_tot  = result.get("fee_total", 0)
                                self._log_event(                          # FIX v2.2-#3: was self._log — missing from Events tab
                                    f"🚀 AI TRAIL [{pct_done:.0f}% done]: "
                                    f"{pos.direction} {pair_label(pos.symbol)}  "
                                    f"{change_txt}  net=${net_now:+.3f} fees=${fee_tot:.3f}  ({reason})", GREEN)
                                self._ai_log_event(pid, f"🚀 TRAIL [{pct_done:.0f}%]",
                                    f"{change_txt}\nNet P&L now: ${net_now:+.3f}  Fees paid: ${fee_tot:.3f}\n{reason}", GREEN)
                                self._save()
                                _ak  = self.mexc_key_e.get().strip()
                                _asc = self.mexc_sec_e.get().strip()
                                threading.Thread(
                                    target=self._update_sl_on_mexc,
                                    args=(self.state.positions[pid], _ak, _asc),
                                    daemon=True).start()
                        else:
                            self._ai_log_event(pid, f"📈 TRAIL HOLD [{pct_done:.0f}%]",
                                f"Momentum not strong enough to trail\n{reason}", DIM)

            if pid not in self.state.positions:
                return

            # Stale trade check (45+ minutes open, including hedges)
            try:
                opened = datetime.fromisoformat(pos.opened_at.replace("Z", "+00:00"))
                mins_open = (datetime.now(timezone.utc) - opened).total_seconds() / 60
            except Exception:
                mins_open = 0
            peak = self._price_peak.get(pid, pos.entry_price)
            max_drift = abs(peak - pos.entry_price) / pos.entry_price * 100
            stale_key = f"stale_{pid}"
            already_stale = getattr(self, stale_key, 0)
            if (mins_open >= 45 and max_drift < 0.5
                    and pid not in self._stale_checked
                    and time.time() - already_stale > 1800):
                setattr(self, stale_key, time.time())
                self._stale_checked.add(pid)
                with self._claude_gate:
                    self._claude_gate_ts = time.time()
                    result = claude_stale_trade_check(pos, cur_px, mins_open, max_drift, sig, ck)
                if result:
                    _track_cost(result.get("tokens_used", 0))
                    action = result["action"]
                    reason = result["reason"]
                    if action == "CLOSE" and pid in self.state.positions:
                        self._log_event(f"AI STALE CLOSE: {pos.direction} {pair_label(pos.symbol)} "
                                  f"open {mins_open:.0f}min drift {max_drift:.3f}% — {reason}", AMBER)
                        self._ai_log_event(pid, "⌛ STALE — CLOSING",
                            f"Open {mins_open:.0f}min, only {max_drift:.3f}% drift\n{reason}", AMBER)
                        if pos.direction == "LONG":
                            self.state.positions[pid].stop_loss = cur_px * 0.9999
                        else:
                            self.state.positions[pid].stop_loss = cur_px * 1.0001
                    else:
                        self._ai_log_event(pid, "⌛ STALE HOLD",
                            f"Open {mins_open:.0f}min — holding\n{reason}", DIM)

            if pid not in self.state.positions:
                return

            # AI hedge check — only fires when drawdown is meaningful
            if not pos.hedge_of and not hedge_on:
                if raw_chg * lev * 100 <= -8.0:   # -8% margin = ~0.4% price at 20x
                    already_hedged = any(p.hedge_of == pid for p in self.state.positions.values())
                    hedge_cooldown_key = f"_hedge_cd_{pid}"
                    hedge_cd = getattr(self, hedge_cooldown_key, 0)
                    if (not already_hedged
                            and time.time() - hedge_cd > 3600):  # max once per hour per position
                        dd = raw_chg * lev * 100
                        with self._claude_gate:
                            self._claude_gate_ts = time.time()
                            result = claude_hedge_check(pos, cur_px, dd, sig, ck)
                        if result:
                            _track_cost(result.get("tokens_used", 0))
                            setattr(self, hedge_cooldown_key, time.time())
                            conf = result.get("confidence", 0)
                            if (result["action"] == "HEDGE"
                                    and conf >= 70           # require high confidence
                                    and pid in self.state.positions):
                                still_hedged = any(x.hedge_of == pid
                                                   for x in self.state.positions.values())
                                if not still_hedged:
                                    hedge_dir = "SHORT" if pos.direction == "LONG" else "LONG"
                                    hid = self._open_position(
                                        pos.symbol, hedge_dir, cur_px, mg * 0.5, lev,
                                        sl, tp, dry, ak, asc, hedge_of=pid)
                                    if hid:
                                        reason = result["reason"]
                                        self._log(f"AI HEDGE [{conf}%]: {hedge_dir} "
                                                  f"{pair_label(pos.symbol)} — {reason}", AMBER)
                                        self._ai_log_event(pid, f"⇄ AI HEDGE [{conf}%]",
                                            f"Opened {hedge_dir} hedge @ ${cur_px:,.4f}\n{reason}", AMBER)
                                        self._refresh_metrics(); self._save()
                            else:
                                reason = result.get("reason", "")
                                self._ai_log_event(pid, f"⇄ HEDGE PASS [{conf}%]",
                                    f"Drawdown {dd:.1f}% — not hedging: {reason}", DIM)

            # Monitor log entry
            if pid in self.state.positions:
                col = GREEN if drawdown_pct >= 0 else RED
                self._ai_log_event(pid, "📊 MONITOR",
                    f"Price ${cur_px:,.4f}  margin {drawdown_pct:+.1f}%  "
                    f"SL ${pos.stop_loss:,.4f}  TP ${pos.take_profit:,.4f}  "
                    f"RSI {sig.get('rsi',0):.0f}  {sig.get('trend','—')}",
                    col)

    def _reset_defaults(self):
        """Reset all config to optimised defaults and delete saved config."""
        import tkinter.messagebox as mb
        msg = "Reset all settings to optimised defaults? API keys kept."
        if not mb.askyesno("Reset defaults", msg): return
        # Delete saved config file
        cfg_path = os.path.join(str(pathlib.Path.home()), "HermesBot", "hermesbot_cfg.json")
        try: os.remove(cfg_path)
        except: pass
        # Re-apply UI defaults
        try:
            self.lev_cb.set("10x");           self._on_lev()
            # _on_lev calls _auto_sl_tp which sets SL/TP correctly for the leverage
            # so don't override them with hardcoded values here
            self.thr_cb.set("4.5/9")
            self.int_cb.set("10s")
            self.tf_cb.set("Min5")
            self.margin_e.delete(0, "end");   self.margin_e.insert(0, "50")
            self.max_trades_cb.set("2")
            self.hedge_var.set(False)
            self.stack_var.set(False)
            self.adaptive_var.set(False);      self._on_adaptive_toggle()  # flips to True internally
            # Keep current mode — only reset config, not live/paper selection
            self._on_mode()
        except Exception as e:
            self._log(f"Reset error: {e}", RED)
        self._log("✓ Settings reset to optimised defaults", CYAN)

    def _preflight_check(self):
        """Check balance, margin, and order size before going live."""
        warnings_ = []
        errors_   = []
        margin   = float(self.margin_e.get() or 0)
        lev      = self._lev()
        notional = margin * lev

        # 1. Margin must be positive
        if margin <= 0:
            errors_.append("Margin USDT must be greater than 0")

        # 2. No API keys
        ak = self.mexc_key_e.get().strip()
        sc = self.mexc_sec_e.get().strip()
        if not ak or not sc:
            errors_.append("MEXC API key and secret are required for live trading")

        # 3. Check live balance vs margin (only if balance fetched)
        if self._live_balance:
            avail = self._live_balance.get("available", 0)

            # How many new positions could the bot actually open?
            # Already-open positions consume slots — don't require margin for those.
            try:
                maxt = int(str(self.max_trades_cb.get()).split()[0])
            except Exception:
                maxt = 1
            with self._positions_lock:
                open_count = len(self.state.positions)
            free_slots = max(0, maxt - open_count)

            if avail <= 0 and free_slots > 0 and open_count == 0:
                errors_.append(
                    f"Futures wallet is empty ({avail:.4f} USDT)\n"
                    "Go to MEXC → Assets → Transfer USDT to Futures wallet first")
            elif avail <= 0 and free_slots > 0 and open_count > 0:
                warnings_.append(
                    f"Futures wallet is empty ({avail:.4f} USDT) — new trades will be skipped\n"
                    "Bot will continue managing {open_count} existing position(s)")
            elif free_slots > 0 and margin > avail:
                # Warn but don't block — bot still needs to run to manage existing positions.
                # New opens will be skipped individually when balance is insufficient.
                warnings_.append(
                    f"Margin {margin} USDT > available {avail:.4f} USDT\n"
                    "Reduce margin or transfer more USDT — new trades will be skipped until balance is sufficient")
            elif free_slots > 0 and margin > avail * 0.8:
                warnings_.append(
                    f"Margin uses {margin/avail*100:.0f}% of available balance "
                    f"({avail:.4f} USDT) — leaves little room for multiple trades")

            # 4. Max trades vs balance — only count slots not already filled
            total_needed = margin * free_slots
            if free_slots > 0 and total_needed > avail:
                warnings_.append(
                    f"{free_slots} open slot(s) × {margin} USDT = {total_needed:.2f} USDT needed "
                    f"but only {avail:.4f} USDT available — reduce max trades or margin")
        else:
            # Balance not fetched yet — warn but don't block
            warnings_.append(
                "Could not verify MEXC balance — make sure you have USDT "
                "in your Futures wallet before trading")

        # 5. High leverage warnings
        if lev >= 100:
            warnings_.append(
                f"{lev}x: a {100/lev:.1f}% price move = 100% margin loss. "
                "Recommended: 10-25x until win rate is proven above 55%")
        elif lev >= 50:
            warnings_.append(
                f"{lev}x: a {100/lev:.1f}% price move = 100% margin loss")

        return errors_, warnings_

    def toggle_bot(self):
        if not self.bot_running:
            if not self.dry_var.get():
                errors_, warnings_ = self._preflight_check()

                # Build warning message
                msg_parts = []
                if errors_:
                    msg_parts.append("❌ ERRORS (must fix):\n" + "\n".join(f"  • {e}" for e in errors_))
                if warnings_:
                    msg_parts.append("⚠ WARNINGS:\n" + "\n".join(f"  • {w}" for w in warnings_))
                msg_parts.append(f"\nMode     : LIVE TRADING")
                msg_parts.append(f"Leverage : {self._lev()}x")
                msg_parts.append(f"Margin   : {self.margin_e.get()} USDT per trade")
                if self._live_balance:
                    msg_parts.append(f"Available: {self._live_balance.get('available',0):.2f} USDT")

                if errors_:
                    messagebox.showerror("Cannot start — fix errors", "\n\n".join(msg_parts))
                    return

                if not messagebox.askyesno("⚠ Start LIVE trading?", "\n".join(msg_parts)
                                            + "\n\nStart live trading?"): return
            self._start()
        else: self._stop()

    def _start(self):
        self.bot_running = True; self._stop_event.clear(); self.state = BotState(); self.dock.state = self.state
        self._bot_start_time  = time.time()
        self._uptime_timer    = None
        self._cycles_run      = 0
        self._hold_streak     = 0
        self._adaptive_thr    = None
        if not hasattr(self, "_adaptive_engine"):
            self._adaptive_engine = AdaptiveTriggerEngine(base_threshold=self._thresh())
        else:
            # Reset session trade/streak data only — ATR history is preserved
            # below via the cache file so we skip the ~10 min warmup after restarts.
            self._adaptive_engine.base_threshold = self._thresh()
            self._adaptive_engine.reset_session()

        # ── Restore warm ATR history from cache (survives restarts up to 4 h) ──
        restored = self._adaptive_engine.restore_atr_from_cache(ATR_CACHE_FILE)
        if restored:
            self._log_event(
                f"ATR cache restored: {restored} pair(s) — threshold warmup skipped", CYAN)
        else:
            self._log("ATR cache absent or stale — threshold warms up over ~10 cycles", DIM)
        self._last_signal_pair= None
        self._last_signal_time= None
        self._last_signal_dir = None
        self._claude_tokens  = 0
        self._claude_cost    = 0.0
        self._claude_calls   = 0
        if hasattr(self, "_cost_lbl"):
            self._cost_lbl.config(text="$0.0000", fg=DIM)
            self._calls_lbl.config(text="0 calls")
        self.root.after(200, self._refresh_trades_tab)
        self._tick_uptime()
        self.start_btn.config(text="■  STOP BOT", bg=RED, fg=TEXT, activebackground="#c0392b")
        self.status_dot.config(fg=GREEN)
        dry = self.dry_var.get()
        mode_str = "PAPER (no real orders)" if dry else "⚡ LIVE TRADING ⚡"
        mode_col = AMBER if dry else RED
        self._log_event(f"Bot started — {mode_str}", mode_col)
        dual = self.dual_tf_var.get() if hasattr(self,"dual_tf_var") else False
        tf_desc = f"Min5→Min1 (dual)" if dual else self.tf_cb.get()
        self._log_event(f"Scanning {len(self._active_pairs())} pairs  |  Leverage: {self._lev()}x  TF: {tf_desc}", GREEN)
        self._log_event(f"Margin ${self.margin_e.get()}  SL {self.sl_cb.get()}  TP {self.tp_cb.get()}"
                  f"  MaxTrades {self.max_trades_cb.get()}"
                  f"  Hedge {'ON' if self.hedge_var.get() else 'OFF'}", BLUE)
        self._select_tab(len(PAIRS))

        # ── Start WebSocket for live price feeds ──────────────────────────────
        self._start_websocket()

        # ── Recover orphaned orders + sync existing positions ─────────────────
        if not self.dry_var.get():
            threading.Thread(target=self._recover_orders, daemon=True).start()
            self._start_sync_positions()

        self.bot_thread = threading.Thread(target=self._loop, daemon=True)
        self.bot_thread.start()
        # Fetch actual fee rates in background (live mode only)
        if not self.dry_var.get():
            def _ff():
                mk, tk = fetch_fee_rate(self.mexc_key_e.get().strip(), self.mexc_sec_e.get().strip())
                self._fee_maker, self._fee_taker = mk, tk
                self.dock.fee_maker = mk   # keep dock card display in sync
                self.dock.fee_taker = tk   # keep dock card display in sync
                self._log(f"Fees: maker {mk*100:.3f}% taker {tk*100:.3f}%", CYAN)
            threading.Thread(target=_ff, daemon=True).start()

        # Validate contract specs against MEXC live API (public endpoint — no auth needed).
        # Auto-patches PAIR_CONTRACT_SIZE, PAIR_PRICE_PRECISION, PAIR_MAX_LEV if MEXC changed
        # anything since the last bot release. Runs in background; logs any updates in cyan.
        def _validate_specs():
            self._log("⚙ Validating contract specs against MEXC API…", DIM)
            validate_contract_specs(log_fn=self._log)
        threading.Thread(target=_validate_specs, daemon=True).start()

    def _start_websocket(self):
        """Initialize and start the WebSocket manager for live price feeds."""
        if self._ws_manager:
            self._ws_manager.stop()
        tf = self.tf_cb.get()
        active = self._active_pairs()
        self._ws_manager = MexcWebSocket(
            pairs=active,
            interval=tf,
            on_price=self._ws_on_price,
            on_kline=self._ws_on_kline,
            on_log=self._log,
        )
        started = self._ws_manager.start()
        if started:
            self._log(f"WebSocket connecting to {MEXC_WS_URL} ...", CYAN)
        else:
            self._log("WebSocket unavailable — using HTTP polling fallback", AMBER)

    def _ws_on_price(self, pair_key, price):
        """Callback when WebSocket delivers a new price."""
        self.current_prices[pair_key] = price
        if pair_key in self.pair_signals and isinstance(self.pair_signals[pair_key], dict):
            self.pair_signals[pair_key]["price"] = price
        # Keep chart panel's cached last-candle close in sync so next redraw shows correct price
        cp = self.chart_panels.get(pair_key)
        if cp and cp._last_candles:
            try:
                last = dict(cp._last_candles[-1])
                last["close"] = price
                last["high"]  = max(float(last.get("high", price)), price)
                last["low"]   = min(float(last.get("low",  price)), price)
                cp._last_candles[-1] = last
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)
        # Throttle price label updates to ~20 fps — WebSocket can fire many times per second
        # per pair which floods the Tk event queue and causes lag.
        now_price = time.time()
        _price_ts = getattr(self, "_last_price_label_ts", {})
        if now_price - _price_ts.get(pair_key, 0) >= 0.05:
            _price_ts[pair_key] = now_price
            self._last_price_label_ts = _price_ts
            self.root.after(0, lambda _p=pair_key, _px=price: self._set_price(_p, _px))
        try:
            now = time.time()
            last_map = getattr(self, "_last_ws_chart_redraw", {})
            # Only redraw the currently visible tab, throttled to once every 2s
            try:
                visible_idx = self._current_tab_idx
                visible_pair = PAIRS[visible_idx] if visible_idx < len(PAIRS) else None
            except Exception:
                visible_pair = None
            if pair_key == visible_pair and (now - last_map.get(pair_key, 0) >= 2.0):
                last_map[pair_key] = now
                self._last_ws_chart_redraw = last_map
                self.root.after(0, lambda _p=pair_key: self._refresh_position_chart(_p))
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)

    def _ws_on_kline(self, pair_key, bar):
        """Callback when WebSocket delivers a new kline bar."""
        # Append to pair_candles cache (used by signal computation)
        candles = self.pair_candles.get(pair_key, [])
        if candles and candles[-1].get("time") == bar.get("time"):
            candles[-1] = bar
        else:
            candles.append(bar)
            if len(candles) > 250:
                self.pair_candles[pair_key] = candles[-200:]
            else:
                self.pair_candles[pair_key] = candles

    # ── Order State Persistence ─────────────────────────────────────────────
    def _persist_orders(self):
        """Save current open positions to disk for crash recovery."""
        orders = []
        for pid, pos in self.state.positions.items():
            orders.append({
                "id": pid,
                "symbol": pos.symbol,
                "direction": pos.direction,
                "entry_price": pos.entry_price,
                "order_id": pos.order_id,
                "opened_at": pos.opened_at,
                "margin": pos.margin,
                "leverage": pos.leverage,
            })
        save_open_orders(orders)

    def _recover_orders(self):
        """On startup, check for orphaned orders from a previous crash."""
        saved = load_open_orders()
        if not saved:
            return
        ak  = self.mexc_key_e.get().strip()
        asc = self.mexc_sec_e.get().strip()
        if not ak or not asc:
            return
        self._log(f"Recovering {len(saved)} orphaned order(s) from previous session...", AMBER)
        for o in saved:
            sym = o.get("symbol", "")
            oid = o.get("order_id", "")
            if not sym or not oid or oid.startswith("DRY"):
                continue
            try:
                chk = mexc_private("GET", "/api/v1/private/order/get/" + oid,
                                   {"symbol": sym}, ak, asc, False)
                state = (chk or {}).get("data", {}).get("state")
                if state in (2, 3):  # filled or partially filled
                    self._log(f"  ✓ Order {oid[:8]} ({sym}) still active on exchange", GREEN)
                elif state in (4, 5):  # cancelled
                    self._log(f"  × Order {oid[:8]} ({sym}) was cancelled", DIM)
            except Exception as e:
                self._log(f"  ? Order {oid[:8]} ({sym}) check failed: {e}", AMBER)
        # Clear persisted orders (they've been checked)
        save_open_orders([])

    def _import_trade_history(self):
        """Fetch last 20 closed trades from MEXC and add any new ones to the trades tab."""
        ak  = self.mexc_key_e.get().strip()
        asc = self.mexc_sec_e.get().strip()
        if not ak or not asc:
            self._log("Import history: no API keys entered", AMBER)
            return
        if self.dry_var.get():
            self._log("Import history: only available in Live mode", AMBER)
            return
        self._log("Fetching trade history from MEXC...", DIM)

        def _go():
            try:
                # close_orders requires a symbol — loop over all active pairs
                # side values per MEXC docs:
                #   1=open long, 2=close short, 3=open short, 4=close long
                # We want close-side orders: side 2 (closed a SHORT) or 4 (closed a LONG)
                all_items = []
                pairs_to_check = self._active_pairs() if hasattr(self, "_active_pairs") else PAIRS
                for sym in pairs_to_check:
                    try:
                        r = mexc_private("GET", "/api/v1/private/order/list/close_orders",
                                         {"symbol": api_sym(sym), "page_num": 1, "page_size": 50},
                                         ak, asc, False)
                        if not r or not r.get("success"):
                            continue
                        raw = r.get("data", [])
                        # Response may be paginated dict or direct list
                        if isinstance(raw, dict):
                            raw = raw.get("resultList", raw.get("list", raw.get("data", [])))
                        if isinstance(raw, list):
                            # Attach canonical bot symbol to each item
                            for item in raw:
                                item["_bot_sym"] = sym
                            all_items.extend(raw)
                    except Exception as sym_err:
                        _file_logger.debug(f"History fetch error for {sym}: {sym_err}")
                        continue

                if not all_items:
                    self._log("No trade history returned from MEXC", DIM)
                    return

                # Build dedup set from existing trades
                existing = set()
                for t in self.state.trades:
                    ts_min = t.get("closed_at", "")[:16]
                    existing.add((t.get("symbol", ""), t.get("direction", ""), ts_min))

                imported = 0
                for item in all_items:
                    try:
                        sym      = item.get("_bot_sym", item.get("symbol", ""))
                        side     = int(item.get("side", 0))
                        # Only import close-side orders
                        # side 2 = close short (we were SHORT, now closing → position was SHORT)
                        # side 4 = close long  (we were LONG,  now closing → position was LONG)
                        if side not in (2, 4):
                            continue
                        direction = "LONG" if side == 4 else "SHORT"

                        state_val = int(item.get("state", 0))
                        # state 2=filled, 3=partially filled
                        if state_val not in (2, 3):
                            continue

                        exit_px  = float(item.get("dealAvgPrice", 0) or 0)
                        if exit_px == 0:
                            continue  # unfilled, skip

                        lev      = int(item.get("leverage", 1) or 1)
                        # Use usedMargin (actual margin used) — falls back to orderMargin
                        margin   = float(item.get("usedMargin", 0) or
                                         item.get("orderMargin", 0) or 0)
                        if margin == 0:
                            # Compute from vol × contractSize × price / leverage as last resort
                            deal_vol = float(item.get("dealVol", 0) or 0)
                            # cs kept for display/reference only — vol uses USDT notional
                            cs       = PAIR_CONTRACT_SIZE.get(sym, 1)
                            size_usdt = deal_vol * cs * exit_px
                            margin   = size_usdt / lev if lev > 0 else size_usdt

                        # Timestamps
                        create_ts = item.get("createTime", 0) or 0
                        update_ts = item.get("updateTime", create_ts) or create_ts
                        def _ts_to_iso(ms):
                            try:
                                return datetime.fromtimestamp(
                                    int(ms) / 1000, tz=timezone.utc).isoformat()
                            except Exception:
                                return ""
                        opened_at  = _ts_to_iso(create_ts)
                        closed_at  = _ts_to_iso(update_ts)
                        closed_min = closed_at[:16]

                        # Dedup
                        fp = (sym, direction, closed_min)
                        if fp in existing:
                            continue

                        pnl    = float(item.get("profit", 0) or 0)
                        fee    = float(item.get("takerFee", 0) or item.get("totalFee", 0) or 0)
                        status = "WIN (imported)" if pnl >= 0 else "LOSS (imported)"

                        # entry_price is unknown from close_orders alone — use exit as placeholder
                        # (the display shows ENTRY/EXIT; both will be exit_px for imported trades)
                        self.state.trades.append({
                            "symbol":        sym,
                            "direction":     direction,
                            "entry_price":   exit_px,   # best we have — close_orders has no open price
                            "exit_price":    exit_px,
                            "margin":        round(margin, 4),
                            "leverage":      lev,
                            "pnl_usdt":      round(pnl, 4),
                            "status":        status,
                            "hedge":         False,
                            "opened_at":     opened_at,
                            "closed_at":     closed_at,
                            "open_fee_type": "taker",
                            "open_fee_rate": self._fee_taker,
                            "close_fee_rate": self._fee_taker,
                            "total_fee_usdt": round(fee, 6),
                        })
                        existing.add(fp)
                        imported += 1
                    except Exception as row_err:
                        _file_logger.debug(f"History row parse error: {row_err}")
                        continue

                if imported:
                    self._log(f"✓ Imported {imported} trade(s) from MEXC history", GREEN)
                    self.root.after(0, self._refresh_trades_tab)
                    self.root.after(0, self._refresh_metrics)
                    self._save()
                else:
                    self._log("History import: no new trades to add (all already present)", DIM)

            except Exception as e:
                self._log(f"Trade history import failed: {e}", RED)

        threading.Thread(target=_go, daemon=True).start()

    def _start_sync_positions(self):
        """Start position sync after reading Tk widgets on the UI thread."""
        ak  = self.mexc_key_e.get().strip()
        asc = self.mexc_sec_e.get().strip()
        sl_pct = self._sl() if hasattr(self, "sl_cb") else 0.008
        tp_pct = self._tp() if hasattr(self, "tp_cb") else 0.02
        claude_enabled = bool(self.claude_enabled.get()) if hasattr(self, "claude_enabled") else False
        claude_key = self.claude_entry.get().strip() if claude_enabled and hasattr(self, "claude_entry") else ""
        threading.Thread(
            target=self._sync_positions,
            args=(ak, asc, sl_pct, tp_pct, claude_key, claude_enabled),
            daemon=True,
        ).start()

    def _sync_positions(self, ak=None, asc=None, sl_pct=None, tp_pct=None,
                        claude_key="", claude_enabled=False):
        """Fetch open positions from MEXC and import any not already tracked."""
        if ak is None or asc is None:
            try:
                ak  = self.mexc_key_e.get().strip()
                asc = self.mexc_sec_e.get().strip()
            except Exception as e:
                self._log(f"Position sync failed before request: {e}", AMBER)
                return
        if not ak or not asc:
            self._log("Position sync: no API keys entered", AMBER)
            return
        self._log("Position sync: fetching from MEXC...", DIM)
        try:
            exchange_positions = fetch_open_positions(ak, asc)
        except Exception as e:
            self._log(f"Position sync failed: {e}", AMBER)
            return
        # ── Reconcile: remove locally-tracked positions closed on the exchange ──
        # Runs even when exchange_positions is empty (all positions closed remotely)
        exchange_keys = {(ep["symbol"], ep["direction"]) for ep in exchange_positions}
        stale_pids = [
            pid for pid, pos in list(self.state.positions.items())
            if (pos.symbol, pos.direction) not in exchange_keys
               and not getattr(pos, "hedge_of", "")   # leave hedge legs to their own close path
        ]
        for pid in stale_pids:
            with self._positions_lock:
                pos = self.state.positions.pop(pid, None)
            if not pos:
                continue
            # Immediately remove AI log entry so the AI tab stops showing this position.
            # (_cleanup_memory only runs every 60 cycles — too slow for closed positions.)
            with self._ai_log_lock:
                self._ai_trade_log.pop(pid, None)
            # Invalidate AI tab throttle cache so next refresh redraws without the card.
            self._ai_tab_last_count = -1
            self._ai_tab_last_events = -1

            # ── Estimate exit price + PnL so this close is recorded properly ──
            # The exchange already closed the position; fetch current price as the
            # best available proxy for the actual exit price.
            exit_px = pos.entry_price   # safe fallback
            try:
                t = get_ticker(pos.symbol)
                if t and t.get("last", 0) > 0:
                    exit_px = float(t["last"])
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)

            d = pos.direction
            raw = ((exit_px - pos.entry_price) / pos.entry_price if d == "LONG"
                   else (pos.entry_price - exit_px) / pos.entry_price)
            gross_pnl = raw * pos.leverage * pos.margin
            open_fee_rate  = self._fee_maker if getattr(pos, "open_fee_type", "taker") == "maker"                              else self._fee_taker
            close_fee_rate = self._fee_taker
            fee   = pos.size_usdt * (open_fee_rate + close_fee_rate)
            pnl   = round(gross_pnl - fee, 4)
            status = "WIN" if pnl >= 0 else "LOSS"

            # Update session stats
            self.state.total_pnl = round(self.state.total_pnl + pnl, 4)
            if not self.dry_var.get():
                self.state.balance = round(self.state.balance + pnl, 4)
            if pnl >= 0:
                self.state.wins   += 1
                self._kelly_wins  += 1
            else:
                self.state.losses += 1
                self._kelly_losses += 1
                self._pair_cooldown[pos.symbol] = time.time()
                self._losing_streak = getattr(self, "_losing_streak", 0) + 1

            # Append to trade history (shows in Trades tab)
            self.state.trades.append({
                "symbol":        pos.symbol,
                "direction":     d,
                "entry_price":   pos.entry_price,
                "exit_price":    exit_px,
                "margin":        pos.margin,
                "leverage":      pos.leverage,
                "pnl_usdt":      pnl,
                "status":        f"{status} (synced close)",
                "hedge":         bool(pos.hedge_of),
                "opened_at":     pos.opened_at,
                "closed_at":     datetime.now(timezone.utc).isoformat(),
                "open_fee_type": getattr(pos, "open_fee_type", "taker"),
                "open_fee_rate": open_fee_rate,
                "close_fee_rate": close_fee_rate,
                "total_fee_usdt": round(fee, 6),
            })

            # Adaptive engine + Kelly update
            self._adaptive_engine.log_trade(pnl >= 0)
            alpha = 0.15
            if pnl >= 0:
                self._kelly_avg_win = (alpha * abs(pnl) + (1 - alpha) * self._kelly_avg_win)                                       if self._kelly_avg_win > 0 else abs(pnl)
            else:
                self._kelly_avg_loss = (alpha * abs(pnl) + (1 - alpha) * self._kelly_avg_loss)                                        if self._kelly_avg_loss > 0 else abs(pnl)

            self._log(
                f"\u21b3 Position closed on exchange \u2014 {pos.symbol} {d} "
                f"entry=${pos.entry_price:,.4f}  exit\u2248${exit_px:,.4f}  "
                f"PnL {'+' if pnl >= 0 else ''}{pnl:.4f} USDT  [{status}]", AMBER)
            self._ai_log_event(pid, f"CLOSED ON EXCHANGE ({status})",
                f"{d} {pos.symbol} entry=${pos.entry_price:,.4f} exit\u2248${exit_px:,.4f} "
                f"PnL={'+' if pnl>=0 else ''}{pnl:.4f} USDT (estimated from market price)",
                GREEN if pnl >= 0 else RED)

            # Clean up position-scoped attributes
            for attr in [f"near_tp_{pid}", f"stale_{pid}", f"_partial_tp_{pid}",
                         f"_be_lock_{pid}", f"_trail_{pid}", f"_trail_ms_{pid}"]:
                try: delattr(self, attr)
                except AttributeError: pass
            self._stale_checked.discard(pid)

        if stale_pids:
            self._persist_orders()
            self.root.after(0, self._refresh_metrics)
            self.root.after(100, self._refresh_trades_tab)

        if not exchange_positions:
            if not stale_pids:
                self._log("Position sync: no open positions on exchange", DIM)
            return
        self._log(f"Position sync: found {len(exchange_positions)} position(s) on exchange", CYAN)

        imported = 0
        imported_symbols = set()
        for ep in exchange_positions:
            sym = ep["symbol"]
            direction = ep["direction"]
            # Check if we already track this position (by symbol + direction)
            already_tracked = any(
                pos.symbol == sym and pos.direction == direction
                for pos in self.state.positions.values()
            )
            if already_tracked:
                continue
            # Import as a tracked position
            pid = f"SYNC-{str(uuid.uuid4())[:6]}"
            entry = ep["entry_price"]
            lev   = min(ep["leverage"], self._lev())  # #LEV-CAP: cap synced leverage to UI setting
            mg    = ep["margin"]
            size  = ep["size_usdt"] if ep["size_usdt"] > 0 else mg * lev
            liq   = ep["liq_price"]
            # Calculate SL/TP using actual exchange leverage + per-pair ATR scaling.
            # Mirrors _auto_sl_tp logic so synced positions get the same calibration
            # as bot-opened positions — regardless of what the UI leverage slider says.
            # sl_pct / tp_pct from the function signature are optional overrides
            # (e.g. from the manual "Sync" button which reads the UI sliders).
            # When not provided (scan-loop path), compute fresh per-position values.
            if sl_pct is not None and tp_pct is not None:
                # UI-override: use as-is (caller explicitly set both)
                _sl_use, _tp_use = sl_pct, tp_pct
            else:
                # Step 1: base SL/TP from actual exchange leverage (same table as _auto_sl_tp)
                _lv = lev
                if   _lv >= 150: _sl_base, _tp_base = 0.0020, 0.0055
                elif _lv >= 100: _sl_base, _tp_base = 0.0025, 0.0065
                elif _lv >= 75:  _sl_base, _tp_base = 0.0030, 0.0075
                elif _lv >= 50:  _sl_base, _tp_base = 0.0040, 0.0100
                elif _lv >= 40:  _sl_base, _tp_base = 0.0050, 0.0130
                elif _lv >= 25:  _sl_base, _tp_base = 0.0060, 0.0160
                elif _lv >= 20:  _sl_base, _tp_base = 0.0070, 0.0200
                elif _lv >= 15:  _sl_base, _tp_base = 0.0080, 0.0250
                elif _lv >= 10:  _sl_base, _tp_base = 0.0090, 0.0280
                elif _lv >= 5:   _sl_base, _tp_base = 0.0150, 0.0350
                elif _lv >= 3:   _sl_base, _tp_base = 0.0200, 0.0450
                else:            _sl_base, _tp_base = 0.0250, 0.0550
                # Step 2: ATR scale factor — calibrated for crypto baseline of 0.15%/candle.
                # Low-volatility pairs (SPX 0.03%, EUR 0.02%, XAU 0.03%) need tighter
                # absolute distances so TP is reachable in a reasonable number of candles.
                _pair_atr  = PAIR_ATR_MIN.get(sym, 0.06)           # % per Min5 candle
                _atr_scale = max(0.20, _pair_atr / 0.15)           # clamp: never below 0.20
                _sl_use    = _sl_base * _atr_scale if sl_pct is None else sl_pct
                _tp_use    = _tp_base * _atr_scale if tp_pct is None else tp_pct
            if direction == "LONG":
                SL  = round_price(sym, entry * (1 - _sl_use))
                TP  = round_price(sym, entry * (1 + _tp_use))
            else:
                SL  = round_price(sym, entry * (1 + _sl_use))
                TP  = round_price(sym, entry * (1 - _tp_use))
            pos = Position(
                id=pid, symbol=sym, direction=direction,
                entry_price=entry, margin=mg, leverage=lev,
                size_usdt=size, stop_loss=SL, take_profit=TP,
                liq_price=liq if liq > 0 else 0,
                opened_at=ep.get("open_time", datetime.now(timezone.utc).isoformat()),
                order_id=f"EXCHANGE-{sym}",
                open_fee_type="taker",
                exchange_pos_id=str(ep.get("position_id", "")),
                exchange_hold_vol=float(ep.get("hold_vol", 0)),
            )
            pos.exchange_frozen_vol = float(ep.get("frozen_vol", 0))
            with self._positions_lock:
                self.state.positions[pid] = pos
            imported += 1
            imported_symbols.add(sym)
            self._log_event(f"⟳ Synced position: {sym} {direction} {lev}x "
                      f"entry=${entry:,.4f} margin=${mg:.2f}  "
                      f"SL {_sl_use*100:.3f}%  TP {_tp_use*100:.3f}%", GREEN)
            # Place TP/SL as server-side plan orders on MEXC for synced positions
            threading.Thread(target=self._place_mexc_tpsl,
                             args=(pos, ak, asc), daemon=True).start()
            self._ai_log_event(
                pid,
                "TRADE SYNCED",
                f"Imported from MEXC @ ${entry:,.4f}. "
                + ("Claude monitor attached." if claude_enabled and claude_key else "Enable Claude to analyse this trade."),
                PURPLE if claude_enabled and claude_key else CYAN,
            )
            if claude_enabled and claude_key:
                threading.Thread(target=self._claude_position_monitor,
                                 args=(pid, claude_key), daemon=True).start()
                self._log_event(f"Claude monitor attached: {sym} {direction}", PURPLE)

        if imported > 0:
            self._persist_orders()
            self._log(f"Position sync complete: {imported} position(s) imported", GREEN)
            # Refresh UI and affected charts so entry/TP/SL lines appear immediately.
            self.root.after(100, self._refresh_trades_tab)
            for sym in imported_symbols:
                self.root.after(150, lambda s=sym: self._refresh_position_chart(s))
        else:
            self._log("Position sync: all exchange positions already tracked", DIM)

    def _stop(self):
        self.bot_running = False; self._stop_event.set()
        # Cancel uptime tick timer
        if getattr(self, "_uptime_timer", None):
            self.root.after_cancel(self._uptime_timer)
            self._uptime_timer = None
        # Stop WebSocket connection
        if self._ws_manager:
            self._ws_manager.stop()
            self._ws_manager = None
        # Persist remaining open orders
        self._persist_orders()
        self.start_btn.config(text="▶  START BOT", bg=GREEN, fg=BG, activebackground="#00b85a")
        self.status_dot.config(fg=DIM)
        self._log("Bot stopped.", AMBER)
        self._save()

    def _cleanup_memory(self):
        """Periodic cleanup of data structures to prevent memory leaks."""
        now = time.time()
        
        # Clean up old cooldown entries (older than 24 hours)
        with self._cooldown_lock:
            cutoff = now - SECONDS_PER_DAY  # 24 hours
            self._pair_cooldown = {k: v for k, v in self._pair_cooldown.items() if v > cutoff}
        
        # Clean up stale checked set (reset every hour)
        with self._cooldown_lock:
            if now % SECONDS_PER_HOUR < 30:  # Approximately once per hour
                self._stale_checked.clear()
        
        # Clean up signal cache entries for pairs not in active pairs
        with self._cache_lock:
            active = set(self._active_pairs())
            self._sig_cache = {k: v for k, v in self._sig_cache.items() if k in active}
            self._chart_last_draw = {k: v for k, v in self._chart_last_draw.items() if k in active}
        
        # Clean up AI trade logs for closed positions
        with self._ai_log_lock:
            with self._state_lock:
                open_pids = set(self.state.positions.keys())
            self._ai_trade_log = {k: v for k, v in self._ai_trade_log.items() if k in open_pids}
        
        # Clean up H1/H4 trends for inactive pairs (reuse `active` set computed above
        # instead of re-querying every pair checkbox Tk variable two more times)
        with self._state_lock:
            self._h1_trends = {k: v for k, v in self._h1_trends.items() if k in active}
            self._h4_trends = {k: v for k, v in self._h4_trends.items() if k in active}  # #H4-FILTER

    # ── BOT LOOP ──────────────────────────────────────────────────────────────
    def _close_position_by_id(self, pid, dry, ak, asc, reason_tag="VETO"):
        """Close a position by pid — used by Claude confidence veto (#CLAUDE-CONF).
        Thread-safe: can be called from a background worker thread.
        """
        if pid not in self.state.positions:
            return
        pos = self.state.positions[pid]
        px  = self.current_prices.get(pos.symbol, pos.entry_price)
        lev = pos.leverage
        try:
            closed, status, pnl = self._check_exit_force(pos, px, lev, dry, ak, asc)
            if closed:
                col = GREEN if status == "WIN" else RED
                self._log(
                    f"{reason_tag} CLOSE [{status}] {pos.direction} "
                    f"{pos.symbol.replace('_USDT','')} @ ${px:,.4f}  PnL ${pnl:+.2f}", col)
                self._price_history.pop(pid, None)
                self._price_peak.pop(pid, None)
                self._stale_checked.discard(pid)
                self.root.after(0, self._refresh_metrics)
                self.root.after(0, self._refresh_trades_tab)
        except Exception as _exc:
            _file_logger.debug("_close_position_by_id error: %s", _exc)

    def _loop(self):
        cycle = 0
        while self.bot_running and not self._stop_event.is_set():
            cycle += 1
            try:
                # Periodic memory cleanup (every CLEANUP_INTERVAL_CYCLES cycles)
                if cycle % CLEANUP_INTERVAL_CYCLES == 0:
                    self._cleanup_memory()
                self._check_overnight_mode()
                lev  = self._lev()
                mg   = float(self.margin_e.get())
                sl   = self._sl(); tp = self._tp()
                thr  = self._thresh()
                dry  = self.dry_var.get()
                dual_mode = self.dual_tf_var.get() if hasattr(self,"dual_tf_var") else False
                tf = self.tf_cb.get()
                if dual_mode and tf == "Min1":
                    tf = "Min5"
                    self.root.after(0, lambda: self.tf_cb.set("Min5"))
                ak   = self.mexc_key_e.get().strip()
                asc  = self.mexc_sec_e.get().strip()
                ck   = self.claude_entry.get().strip() if self.claude_enabled.get() else ""
                maxt       = self._max_trades()
                hedge_on   = self.hedge_var.get()
                hedge_thr  = float(self.hedge_thresh_cb.get().replace("%","")) / 100
                stack_on   = self.stack_var.get()
                stack_thr  = self._stack_thresh()
                stack_max  = self._stack_max()
                overnight  = self.overnight_var.get() if hasattr(self, "overnight_var") else False
                # v2.8-TUNED: read the Selective-entry toggle once per cycle
                _selective = (self._tuned_entry_var.get()
                              if hasattr(self, "_tuned_entry_var")
                              else TUNED_SELECTIVE_ENTRY_DEFAULT)

                # ── Periodic position sync (every 2 cycles in live mode) ─────
                # Pass sl=None, tp=None so _sync_positions always computes
                # ATR-scaled values from actual exchange leverage. Passing raw
                # UI sl/tp bypassed the scaling path even for fresh syncs.
                if not dry and cycle % 2 == 0:
                    threading.Thread(target=self._sync_positions, args=(ak, asc, None, None, ck, bool(ck)), daemon=True).start()

                # ── Scan ALL pairs in parallel, pick best signal ──────────
                self._cycles_run += 1
                _scan_pairs = self._active_pairs()
                self._log(f"Cycle {cycle} — scanning {len(_scan_pairs)} pairs ({tf})…", DIM)

                all_sigs = {}   # pair -> sig dict
                scan_errors = []
                # SCALE v2.4-#2/#3: batch UI updates — collect during scan, flush once after
                _pending_price_updates = {}   # pair -> new_price  (flushed in one root.after)
                _pending_chart_updates = {}   # pair -> (can_, sig_, op, tf)  (same)

                def _scan_pair(p):
                    if p in self._dead_pairs:
                        return
                    try:
                        # Prefer WebSocket cached data; fall back to HTTP REST
                        ws_price = self._ws_manager.get_price(p) if self._ws_manager else None
                        ws_klines = self._ws_manager.get_klines(p) if self._ws_manager else []
                        if ws_price and ws_price > 0:
                            tkr_ = {"last": ws_price, "funding": 0.0}
                        else:
                            tkr_ = get_ticker(p)
                        if ws_klines and len(ws_klines) >= 20:
                            can_ = ws_klines[-200:]
                        else:
                            can_ = get_klines(p, tf, 200)

                        # ── Per-pair ATR/RSI calibration ──────────────────────────────────
                        _atr_min  = PAIR_ATR_MIN.get(p, 0.06)
                        _rsi_bias = PAIR_RSI_BIAS.get(p, 0)

                        # ── Indicator cache: skip recompute if candles haven't changed ──
                        # Hash the last 3 close prices + current price — cheap and stable
                        if can_:
                            _cache_hash = hash((
                                can_[-1].get("close", 0),
                                can_[-1].get("time",  0),
                                round(tkr_.get("last", 0), 6),
                            ))
                        else:
                            _cache_hash = 0
                        _cached = self._sig_cache.get(p)
                        if _cached and _cached["hash"] == _cache_hash and not dual_mode:
                            sig_ = _cached["sig"]
                            # Still update price in case tick moved
                            sig_["price"] = float(tkr_.get("last", sig_["price"]))
                        elif dual_mode and tf != "Min1":
                            # ── Sequential dual TF (only when Dual TF enabled) ──────
                            # Step 1: Min5 trend confirmation
                            sig5_ = compute_signals(can_, tkr_, _thr_eff,
                                                    atr_min=_atr_min, rsi_bias=_rsi_bias,
                                                    selective_entry=_selective)
                            if sig5_ is None:
                                scan_errors.append((f"{pair_label(p)}: not enough candles (Min5)", MUTED))
                                return

                            # Early exit: only fetch Min1 if Min5 shows strong signal (score >= 4.0)
                            # This avoids unnecessary API calls for weak Min5 signals
                            if sig5_["direction"] in ("LONG", "SHORT") and sig5_["score"] >= 4.0:
                                # Step 2: Min1 entry timing confirmation
                                try:
                                    can1_ = get_klines(p, "Min1", 30)
                                    sig1_ = compute_signals(can1_, tkr_, _thr_eff,
                                                            atr_min=_atr_min, rsi_bias=_rsi_bias,
                                                            selective_entry=_selective)
                                    if sig1_ is None: sig1_ = sig5_

                                    # Entry confirmed only if Min1 agrees with Min5 direction
                                    # AND Min1 is not overbought/oversold against the trade
                                    d5 = sig5_["direction"]
                                    rsi1 = sig1_["rsi"]
                                    sr1  = sig1_.get("srsi", 50)

                                    entry_ok = False
                                    if d5 == "LONG":
                                        # For LONG: want Min1 RSI not overbought (room to run up)
                                        rsi_limit = self._rsi_limit_for_dual_tf()
                                        entry_ok = (rsi1 < rsi_limit and sr1 < rsi_limit + 5)
                                    else:
                                        # For SHORT: Min1 RSI must be at least neutral-bearish (>50)
                                        short_rsi_min = 50
                                        entry_ok = (rsi1 > short_rsi_min and sr1 > 45)

                                    if entry_ok:
                                        sig_ = {
                                            **sig5_,
                                            "price":    sig1_["price"],
                                            "rsi":      sig1_["rsi"],
                                            "srsi":     sig1_.get("srsi", sig5_.get("srsi", 50)),
                                            "macd_h":   sig1_["macd_h"],
                                            "pct_b":    sig1_.get("pct_b",  sig5_.get("pct_b",  0.5)),
                                            "atr_pct":  sig1_.get("atr_pct",sig5_.get("atr_pct",0)),
                                            "obv_slope":sig1_.get("obv_slope",sig5_.get("obv_slope",0)),
                                            "dual_confirmed": True,
                                        }
                                    else:
                                        sig_ = {**sig5_, "direction": "HOLD",
                                                "dual_waiting": True,
                                                "price": sig1_["price"]}
                                except Exception:
                                    sig_ = sig5_
                            else:
                                sig_ = sig5_
                        else:
                            # Single TF mode — compute normally
                            sig_ = compute_signals(can_, tkr_, _thr_eff,
                                                   atr_min=_atr_min, rsi_bias=_rsi_bias,
                                                   selective_entry=_selective)
                            if sig_ is None:
                                scan_errors.append((f"{pair_label(p)}: not enough candles", MUTED))
                                return
                            # Tag Min1 pure mode so _passes_filters can apply tighter rules
                            if tf == "Min1" and not dual_mode:
                                sig_["min1_pure"] = True
                                sig_["candles_raw"] = can_  # pass raw candles for multi-candle check
                            # Store in cache (single-TF only — dual-TF is inherently stateful)
                            if _cache_hash:
                                self._sig_cache[p] = {"hash": _cache_hash, "sig": sig_}

                        all_sigs[p] = sig_
                        self.current_prices[p] = sig_["price"]
                        self.pair_candles[p]   = can_
                        self.pair_signals[p]   = sig_
                        _prev_px = self.current_prices.get(p, 0)
                        _new_px  = sig_["price"]
                        # SCALE v2.4-#2: collect price update for batch flush after scan
                        if _prev_px == 0 or abs(_new_px - _prev_px) / _prev_px > 0.0001:
                            _pending_price_updates[p] = _new_px
                        cp = self.chart_panels.get(p)
                        if cp:
                            # ── Chart redraw throttle: max 1 redraw per 8s per panel ──
                            _now = time.time()
                            _last_draw = self._chart_last_draw.get(p, 0)
                            if _now - _last_draw >= 8.0:
                                self._chart_last_draw[p] = _now
                                op = [pos for pos in self.state.positions.values() if pos.symbol == p]
                                # SCALE v2.4-#3: collect chart update for batch flush after scan
                                _pending_chart_updates[p] = (can_, sig_, op, tf)
                    except Exception as e:
                        err_str = str(e)
                        # Code 1001 = contract doesn't exist on MEXC — skip permanently
                        if "1001" in err_str or "Contract does not exist" in err_str:
                            if p not in self._dead_pairs:
                                self._dead_pairs.add(p)
                                lbl = pair_label(p)
                                # Try alternate symbol formats
                                alt = None
                                if p == "PEPE_USDT": alt = "PEPEUSDT"
                                elif p == "XAU_USDT":   alt = "XAU_USDT"
                                hint = f" — try symbol '{alt}'" if alt else " — removing from scan"
                                scan_errors.append((f"⚠ {lbl} not found on MEXC{hint}", AMBER))
                        else:
                            err_msg = err_str[:60]
                            scan_errors.append((f"{pair_label(p)}: {err_msg}", AMBER))

                # Update adaptive engine base threshold and compute effective threshold.
                # Overnight (low-volume) sessions lower the base by 0.5; the engine's
                # hard 5.0 floor still applies, so we never drop below 5/9.
                self._adaptive_engine.base_threshold = (thr - 0.5) if overnight else thr
                _thr_eff = thr  # default; adaptive engine used per-pair below

                # Drought easing — log a notice each time a new 2-hour boundary is crossed
                _drought_secs = time.time() - self._adaptive_engine.last_trade_opened_at
                _drought_hrs  = _drought_secs / 3600
                _drought_step = int(_drought_hrs) // 2  # increments at 2 h, 4 h, 6 h
                if _drought_step > 0 and _drought_step != getattr(self, "_last_drought_step", 0):
                    self._last_drought_step = _drought_step
                    _relax = min(0.9, _drought_step * 0.3)
                    self._log_event(
                        f"⏳ No trade for {_drought_hrs:.1f}h — drought easing −{_relax:.1f} "
                        f"(threshold base now effectively {((thr - 0.5 if overnight else thr) - _relax):.1f}/9)",
                        AMBER)
                elif _drought_step == 0:
                    self._last_drought_step = 0
                # SCALE v2.4-#1: submit to fixed pool instead of spawning per-cycle threads.
                # WS-down stagger is preserved via a short sleep inside _scan_pair when needed.
                ws_live = bool(self._ws_manager and self._ws_manager.connected)
                futures = {}
                for p in _scan_pairs:
                    if not ws_live:
                        time.sleep(0.05)  # light stagger only when hitting REST
                    futures[self._scan_executor.submit(_scan_pair, p)] = p
                for f in as_completed(futures, timeout=10):
                    pass  # errors already handled inside _scan_pair

                # SCALE v2.4-#2/#3: flush all price + chart updates in a single UI callback
                if _pending_price_updates or _pending_chart_updates:
                    _pu = dict(_pending_price_updates)
                    _cu = dict(_pending_chart_updates)
                    _panels = self.chart_panels
                    def _flush_ui(_pu=_pu, _cu=_cu, _panels=_panels):
                        for _p, _px in _pu.items():
                            self._set_price(_p, _px)
                        for _p, (_c, _s, _op, _tf) in _cu.items():
                            cp_ = _panels.get(_p)
                            if cp_:
                                cp_.update(_c, _s, _op, bot_tf=_tf)
                    self.root.after(0, _flush_ui)

                if scan_errors:
                    for err in scan_errors:
                        if isinstance(err, tuple):
                            self._log(err[0], err[1])
                        else:
                            self._log(err, AMBER)

                # Update ATR history for adaptive engine
                for p, s in all_sigs.items():
                    if s.get("atr_pct"):
                        self._adaptive_engine.update_atr(p, s["atr_pct"])

                # Persist ATR cache every 10 cycles (~5 min at default interval)
                # so a restart never loses more than 5 min of warmup data.
                if cycle % 10 == 0:
                    self._adaptive_engine.save_atr_cache(ATR_CACHE_FILE)

                if not all_sigs:
                    self._log("No data from any pair — skipping cycle", RED)
                else:
                    # Log scan summary — split into rows of 10 so all 10 pairs
                    # are visible without horizontal scrolling in the log box.
                    sorted_sigs = sorted(all_sigs.items(),
                                         key=lambda x: x[1]['score'], reverse=True)
                    _tokens = [
                        (f"{pair_label(p)}: {s['direction'][0]}{s['score']}"
                         + ("~" if s.get("dual_waiting") else "+" if s.get("dual_confirmed") else ""))
                        for p, s in sorted_sigs
                    ]
                    _row_size = 10
                    for _i in range(0, len(_tokens), _row_size):
                        _row = "  ".join(_tokens[_i:_i + _row_size])
                        _prefix = "Scores →" if _i == 0 else "        "
                        self._log(f"{_prefix} {_row}", DIM)

                    # Per-indicator breakdown — only log pairs scoring >= 4.0 to reduce UI noise
                    # SCALE v2.4: raised from 3.5 → 4.0 to halve log callbacks at 30 pairs
                    # Reuse sorted_sigs (same data, same key/order) instead of re-sorting
                    for p, s in sorted_sigs:
                        if s.get("score", 0) < 4.0:
                            continue
                        bull = s.get("trend") == "BULL"
                        rv   = s.get("rsi", 50)
                        mh   = s.get("macd_h", 0)
                        vr   = s.get("vol_ratio", 1)
                        fn   = s.get("funding", 0)
                        pb   = s.get("pct_b", 0.5)
                        sr   = s.get("srsi", 50)
                        obv  = s.get("obv_slope", 0)
                        egp  = s.get("ema_gap_pct", 0)
                        mbl  = s.get("macd_building_long", False)
                        mbs  = s.get("macd_building_short", False)
                        mcu  = s.get("macd_cross_up", False)
                        mcd  = s.get("macd_cross_down", False)
                        ecu  = s.get("ema_cross_up", False)
                        ecd  = s.get("ema_cross_down", False)
                        hl   = s.get("higher_lows", False)
                        lh   = s.get("lower_highs", False)
                        d    = s.get("direction", "HOLD")
                        mx   = s.get("max_score", 9)
                        # Show which indicators fired for the dominant direction
                        if d == "LONG" or (d == "HOLD" and bull):
                            gap_b = 1.0 if egp > 0.25 else (0.5 if egp > 0.10 else 0)
                            breakdown = (
                                f"EMA:{'⚡' if ecu else '✓' if bull else '✗'}({gap_b:.1f})  "
                                f"RSI:{rv:.0f}({'✓' if rv<35 else '½' if rv<50 else '✗'})  "
                                f"MACD:{'⚡' if mcu else '✓' if mh>0 and mbl else '½' if mh>0 else '✗'}  "
                                f"Vol:{'✓' if vr>1.3 else '✗'}({vr:.1f}x)  "
                                f"Fund:{'✓' if fn<-0.01 else '✗'}  "
                                f"BB:{'✓' if pb<0.2 else '✗'}({pb:.2f})  "
                                f"StRSI:{'✓' if sr<20 else '½' if sr<40 else '✗'}({sr:.0f})  "
                                f"OBV:{'✓' if obv>0 else '✗'}  "
                                f"PA:{'✓' if hl else '✗'}"
                            )
                        else:
                            gap_b = 1.0 if egp > 0.25 else (0.5 if egp > 0.10 else 0)
                            breakdown = (
                                f"EMA:{'⚡' if ecd else '✓' if not bull else '✗'}({gap_b:.1f})  "
                                f"RSI:{rv:.0f}({'✓' if rv>65 else '½' if rv>50 else '✗'})  "
                                f"MACD:{'⚡' if mcd else '✓' if mh<0 and mbs else '½' if mh<0 else '✗'}  "
                                f"Vol:{'✓' if vr>1.3 else '✗'}({vr:.1f}x)  "
                                f"Fund:{'✓' if fn>0.01 else '✗'}  "
                                f"BB:{'✓' if pb>0.8 else '✗'}({pb:.2f})  "
                                f"StRSI:{'✓' if sr>80 else '½' if sr>60 else '✗'}({sr:.0f})  "
                                f"OBV:{'✓' if obv<0 else '✗'}  "
                                f"PA:{'✓' if lh else '✗'}"
                            )
                        self._log(f"  {pair_label(p)} {d[0]} {s['score']}/{mx} | {breakdown}", DIM)

                # ── Refresh prices for any open positions whose pair may have errored
                open_syms = set(p.symbol for p in self.state.positions.values())
                for osym in open_syms:
                    if osym not in all_sigs:  # wasn't scanned successfully
                        try:
                            _tkr = get_ticker(osym)
                            if _tkr["last"] > 0:
                                self.current_prices[osym] = _tkr["last"]
                        except Exception as _exc:
                            _file_logger.debug("suppressed error: %s", _exc)

                # ── Check exits on all open positions (use latest price) ───────
                for pid in list(self.state.positions.keys()):
                    if pid not in self.state.positions: continue
                    pos = self.state.positions[pid]
                    cur_px = self.current_prices.get(pos.symbol, pos.entry_price)
                    closed, status, pnl = self._market_close_position(pos, ak, asc, px=cur_px)
                    if closed:
                        col = GREEN if status == "WIN" else (PURPLE if status == "LIQUIDATED" else RED)
                        self._log_event(f"CLOSED [{status}] {pos.direction} {pos.symbol} "
                                  f"@ ${cur_px:,.4f}  PnL ${pnl:+.2f}", col)
                        self._refresh_metrics(); self._save()
                        # Force balance refresh after closing position
                        self._balance_fetch = 0
                        self._fetch_live_balance(); self.root.after(0, self._refresh_trades_tab)
                        self.root.after(0, self._refresh_ai_tab)
                        self._price_history.pop(pid, None)  # clean up history
                        self._price_peak.pop(pid, None)
                        self._stale_checked.discard(pid)
                        for attr in [f"near_tp_{pid}", f"stale_{pid}",
                                     f"_partial_tp_{pid}", f"_be_lock_{pid}",
                                     f"_trail_{pid}", f"_trail_ms_{pid}"]:
                            try: delattr(self, attr)
                            except AttributeError: pass

                # ── Rule-based hedge checks ──────────────────────────────────
                # (AI hedge logic now runs in _claude_position_monitor)
                for pid, pos in list(self.state.positions.items()):
                    if pos.hedge_of: continue
                    cur_px = self.current_prices.get(pos.symbol, pos.entry_price)
                    d = pos.direction
                    raw = (cur_px - pos.entry_price) / pos.entry_price
                    if d == "SHORT": raw = -raw
                    lev_chg = raw * pos.leverage
                    already_hedged = any(p.hedge_of == pid
                                          for p in self.state.positions.values())
                    if already_hedged:
                        continue

                    # ── Rule-based hedge (toggle must be ON) ──────────────────
                    if hedge_on and lev_chg <= hedge_thr:
                        hedge_dir = "SHORT" if d == "LONG" else "LONG"
                        hid = self._open_position(
                            pos.symbol, hedge_dir, cur_px, mg * 0.5, lev,
                            sl, tp, dry, ak, asc, hedge_of=pid)
                        if hid:
                            self._log_event(f"HEDGE opened: {hedge_dir} {pos.symbol} "
                                      f"(rule-based  drawdown {lev_chg*100:.1f}%)", AMBER)
                            self._refresh_metrics(); self._save()
                            self.root.after(0, self._refresh_trades_tab)

                # ── Refresh H1 trend every 10 cycles ─────────────────────────
                # SCALE v2.4-#4: staggered H1 fetch — 1 pair per cycle instead of all at once.
                # Previously all pairs fetched simultaneously every 10 cycles → REST burst.
                # Now one pair advances each cycle; full refresh takes N cycles (N = pair count).
                # Reuse _scan_pairs (same active-pair list, computed once at top of cycle)
                # instead of re-querying every pair checkbox Tk variable again.
                _h1_pairs = _scan_pairs
                if _h1_pairs:
                    _h1_idx = self._h1_fetch_idx % len(_h1_pairs)
                    self._h1_fetch_idx = _h1_idx + 1
                    _h1_pair = _h1_pairs[_h1_idx]
                    def _fetch_h1_one(pair=_h1_pair):
                        try:
                            h1c = get_klines(pair, "Hour1", 30)
                            if h1c:
                                h1_cl = [c["close"] for c in h1c]
                                h1_e9  = ema(h1_cl, 9)
                                h1_e21 = ema(h1_cl, 21)
                                self._h1_trends[pair] = "BULL" if h1_e9[-1] > h1_e21[-1] else "BEAR"
                        except Exception as _exc:
                            _file_logger.debug("suppressed H1 fetch error: %s", _exc)
                    self._scan_executor.submit(_fetch_h1_one)

                # SCALE v2.4-#4: staggered H4 fetch — same pattern as H1 above.
                # H4 changes rarely so fetching 1 pair/cycle is more than adequate.
                _h4_pairs = _scan_pairs
                if _h4_pairs:
                    _h4_idx = self._h4_fetch_idx % len(_h4_pairs)
                    self._h4_fetch_idx = _h4_idx + 1
                    _h4_pair = _h4_pairs[_h4_idx]
                    def _fetch_h4_one(pair=_h4_pair):
                        try:
                            h4c = get_klines(pair, "Hour4", 30)
                            if h4c:
                                h4_cl = [c["close"] for c in h4c]
                                h4_e9  = ema(h4_cl, 9)
                                h4_e21 = ema(h4_cl, 21)
                                self._h4_trends[pair] = "BULL" if h4_e9[-1] > h4_e21[-1] else "BEAR"
                        except Exception as _exc:
                            _file_logger.debug("suppressed H4 fetch error: %s", _exc)
                    self._scan_executor.submit(_fetch_h4_one)

                # ── Pick best signal across all scanned pairs ─────────────────
                n_open = len(self.state.positions)
                now = time.time()
                COOLDOWN_SECS = 180  # 6 cycles — give the pair time to reset after a loss

                # Apply filters to candidates before scoring:
                # 1. H1 trend alignment  2. Pair cooldown  3. RSI divergence
                # 4. Volume hard filter  5. Funding rate block  6. Time-of-day
                gmt_hour = datetime.now(timezone.utc).hour
                # dead_zone removed: 04-07 GMT was blocking 3 hrs every session.
                # Low liquidity is already handled by the vol gate (0.55 overnight).
                # #TOD-BONUS: peak liquidity windows get +0.3 score bonus
                _tod_bonus = 0.3 if (8 <= gmt_hour < 12 or 13 <= gmt_hour < 17) else 0.0

                def _passes_filters(pair, sig):
                    d = sig["direction"]
                    reasons = []
                    # Reuse `overnight` computed once at the top of _loop() — was
                    # re-querying the Tk overnight_var for every scanned candidate.

                    # ── Hard RSI gates — never enter into extreme exhaustion ──
                    rv_  = sig.get("rsi", 50)
                    sr_  = sig.get("srsi", 50)
                    pb_  = sig.get("pct_b", 0.5)
                    cg_  = sig.get("consec_green", 0)
                    cr_  = sig.get("consec_red",   0)

                    # Consecutive candle chasing limit: overnight low-vol grinds
                    # produce same-direction runs without real momentum — raised 4→6.
                    _consec_limit = 6 if overnight else 4
                    if d == "LONG":
                        if rv_ > 78:
                            reasons.append(f"RSI {rv_:.0f} overbought — no LONG")
                        if sr_ > 88:
                            reasons.append(f"StRSI {sr_:.0f} overbought — no LONG")
                        if pb_ > 0.88:
                            reasons.append(f"BB %B {pb_:.2f} — price at/above upper band")
                        if cg_ >= _consec_limit:
                            reasons.append(f"{cg_} consecutive green candles — chasing{'  (overnight limit: 6)' if overnight else ''}")
                    if d == "SHORT":
                        if rv_ < 22:
                            reasons.append(f"RSI {rv_:.0f} oversold — no SHORT")
                        if sr_ < 12:
                            reasons.append(f"StRSI {sr_:.0f} oversold — no SHORT")
                        if pb_ < 0.12:
                            reasons.append(f"BB %B {pb_:.2f} — price at/below lower band")
                        if cr_ >= _consec_limit:
                            reasons.append(f"{cr_} consecutive red candles — chasing{'  (overnight limit: 6)' if overnight else ''}")

                    # ── H1 + H4 trend alignment with pullback scalp override ──────
                    # #PULLBACK: instead of a hard block on counter-trend signals,
                    # high-conviction pullbacks are allowed through with tighter
                    # TP/SL/margin (tagged via sig["pullback_scalp"]).
                    h1 = self._h1_trends.get(pair)
                    h4 = self._h4_trends.get(pair)
                    score = sig.get("score", 0)

                    h1_conflicts = (
                        (d == "LONG"  and h1 == "BEAR") or
                        (d == "SHORT" and h1 == "BULL")
                    ) if h1 else False
                    h4_conflicts = (
                        (d == "LONG"  and h4 == "BEAR") or
                        (d == "SHORT" and h4 == "BULL")
                    ) if h4 else False

                    if h1_conflicts or h4_conflicts:
                        if overnight:
                            # Overnight: same pullback-scalp + OB-scalp bypass routes as
                            # daytime — previously these were unreachable overnight.
                            # Falls back to a score-floor block only if both bypasses fail.
                            _overnight_htf_min = self._thresh()

                            # ── Pullback scalp (overnight) ───────────────────────────
                            _pb_score_min_on = 5.5 if (h1_conflicts and h4_conflicts) else 5.0
                            _pb_candles_on = sig.get("candles", [])
                            _pb_wick_ok_on = False
                            if len(_pb_candles_on) >= 2:
                                _lc_on = _pb_candles_on[-2]
                                _rng_on = _lc_on.get("high", 0) - _lc_on.get("low", 0)
                                if _rng_on > 0:
                                    _op_on = _lc_on.get("open", 0); _cl_on = _lc_on.get("close", 0)
                                    _bt_on = max(_op_on, _cl_on); _bb_on = min(_op_on, _cl_on)
                                    if d == "SHORT":
                                        _pb_wick_ok_on = ((_lc_on.get("high", 0) - _bt_on) / _rng_on) >= 0.40
                                    else:
                                        _pb_wick_ok_on = ((_bb_on - _lc_on.get("low", 0)) / _rng_on) >= 0.40
                            rv_on  = sig.get("rsi", 50)
                            _div_on = sig.get("rsi_divergence")
                            _pb_rsi_ok_on = (rv_on < 55) if d == "LONG" else (rv_on > 45)
                            _pb_div_ok_on = not (
                                (_div_on == "BEARISH" and d == "LONG") or
                                (_div_on == "BULLISH" and d == "SHORT")
                            )
                            if (score >= _pb_score_min_on and _pb_wick_ok_on
                                    and _pb_rsi_ok_on and _pb_div_ok_on):
                                sig["pullback_scalp"] = True
                                sig["pullback_h1"] = h1_conflicts
                                sig["pullback_h4"] = h4_conflicts
                            else:
                                # ── OB exhaustion scalp (overnight) ─────────────────
                                _ob_rsi_ok_on  = (rv_on < 32) if d == "LONG" else (rv_on > 68)
                                _ob_srsi_ok_on = (sig.get("srsi", 50) < 25) if d == "LONG" else (sig.get("srsi", 50) > 75)
                                _ob_hist_ok_on = sig.get("macd_hist_shrinking_bearish") if d == "LONG" else sig.get("macd_hist_shrinking_bullish")
                                _ob_noext_on   = (not sig.get("price_new_10bar_low")) if d == "LONG" else (not sig.get("price_new_10bar_high"))
                                _ob_div_ok_on  = not (
                                    (_div_on == "BEARISH" and d == "LONG") or
                                    (_div_on == "BULLISH" and d == "SHORT")
                                )
                                _ob_score_ok_on = score >= 3.5
                                if (_ob_rsi_ok_on and _ob_srsi_ok_on and _ob_hist_ok_on
                                        and _ob_noext_on and _ob_div_ok_on and _ob_score_ok_on):
                                    sig["ob_scalp"]    = True
                                    sig["ob_scalp_h1"] = h1_conflicts
                                    sig["ob_scalp_h4"] = h4_conflicts
                                elif score < _overnight_htf_min:
                                    # Neither bypass qualifies — fall back to score floor
                                    if h1_conflicts: reasons.append(f"H1 {'BEAR' if d=='LONG' else 'BULL'} vs {d} (overnight, score too low)")
                                    if h4_conflicts: reasons.append(f"H4 {'BEAR' if d=='LONG' else 'BULL'} vs {d} (overnight, score too low)")
                        else:
                            # Normal hours: check pullback scalp qualification
                            # Raise score floor further if both H1 AND H4 conflict
                            _pb_score_min = 5.5 if (h1_conflicts and h4_conflicts) else 5.0

                            # Wick rejection check on last closed candle
                            _pb_candles = sig.get("candles", [])
                            _pb_wick_ok = False
                            if len(_pb_candles) >= 2:
                                _lc = _pb_candles[-2]
                                _rng = _lc.get("high", 0) - _lc.get("low", 0)
                                if _rng > 0:
                                    _op = _lc.get("open", 0); _cl = _lc.get("close", 0)
                                    _body_top = max(_op, _cl); _body_bot = min(_op, _cl)
                                    if d == "SHORT":
                                        # Upper wick > 40% of range = rejection at top
                                        _upper_wick = _lc.get("high", 0) - _body_top
                                        _pb_wick_ok = (_upper_wick / _rng) >= 0.40
                                    else:
                                        # Lower wick > 40% of range = rejection at bottom
                                        _lower_wick = _body_bot - _lc.get("low", 0)
                                        _pb_wick_ok = (_lower_wick / _rng) >= 0.40

                            # RSI must show some Min5 momentum in the scalp direction
                            rv_ = sig.get("rsi", 50)
                            _pb_rsi_ok = (rv_ < 55) if d == "LONG" else (rv_ > 45)

                            # No divergence against the trade (already-exhausted pullback)
                            _div = sig.get("rsi_divergence")
                            _pb_div_ok = not (
                                (_div == "BEARISH" and d == "LONG") or
                                (_div == "BULLISH" and d == "SHORT")
                            )

                            if (score >= _pb_score_min and _pb_wick_ok
                                    and _pb_rsi_ok and _pb_div_ok):
                                # Qualifies — tag as pullback scalp, don't block
                                sig["pullback_scalp"] = True
                                sig["pullback_h1"] = h1_conflicts
                                sig["pullback_h4"] = h4_conflicts
                            else:
                                # ── #OB-SCALP: oversold/overbought exhaustion bounce ──
                                # No wick required — uses MACD histogram shrinking as
                                # exhaustion proof instead. Lower score threshold (3.5)
                                # because most indicators are structurally against the trade.
                                _ob_rsi_ok     = (rv_ < 32) if d == "LONG" else (rv_ > 68)
                                _ob_srsi_ok    = (sig.get("srsi", 50) < 25) if d == "LONG" else (sig.get("srsi", 50) > 75)
                                _ob_hist_ok    = sig.get("macd_hist_shrinking_bearish") if d == "LONG" else sig.get("macd_hist_shrinking_bullish")
                                _ob_no_new_ext = (not sig.get("price_new_10bar_low")) if d == "LONG" else (not sig.get("price_new_10bar_high"))
                                _ob_div_ok     = not (
                                    (_div == "BEARISH" and d == "LONG") or
                                    (_div == "BULLISH" and d == "SHORT")
                                )
                                _ob_score_ok   = score >= 3.5

                                if (_ob_rsi_ok and _ob_srsi_ok and _ob_hist_ok
                                        and _ob_no_new_ext and _ob_div_ok and _ob_score_ok):
                                    # Qualifies as OB exhaustion scalp — bypass H1/H4 block
                                    sig["ob_scalp"]    = True
                                    sig["ob_scalp_h1"] = h1_conflicts
                                    sig["ob_scalp_h4"] = h4_conflicts
                                else:
                                    # Neither pullback nor OB scalp — hard block as before
                                    _pb_fail = []
                                    if score < _pb_score_min:  _pb_fail.append(f"score {score:.1f} < {_pb_score_min}")
                                    if not _pb_wick_ok:        _pb_fail.append("no wick rejection")
                                    if not _pb_rsi_ok:         _pb_fail.append(f"RSI {rv_:.0f} wrong side")
                                    if not _pb_div_ok:         _pb_fail.append("divergence")
                                    _ob_fail = []
                                    if not _ob_rsi_ok:         _ob_fail.append(f"RSI {rv_:.0f} (need <32/>68)")
                                    if not _ob_srsi_ok:        _ob_fail.append(f"StRSI {sig.get('srsi',50):.0f} (need <25/>75)")
                                    if not _ob_hist_ok:        _ob_fail.append("MACD hist not shrinking")
                                    if not _ob_no_new_ext:     _ob_fail.append("new 10-bar extreme — still in freefall")
                                    if not _ob_score_ok:       _ob_fail.append(f"score {score:.1f} < 3.5")
                                    _combined = f"pullback({', '.join(_pb_fail)})  ob-scalp({', '.join(_ob_fail)})"
                                    if h1_conflicts: reasons.append(f"H1 {'BEAR' if d=='LONG' else 'BULL'} vs {d} ({_combined})")
                                    if h4_conflicts: reasons.append(f"H4 {'BEAR' if d=='LONG' else 'BULL'} vs {d} ({_combined})")
                    # Pair cooldown after loss
                    last_loss = self._pair_cooldown.get(pair, 0)
                    if now - last_loss < COOLDOWN_SECS:
                        remaining = int(COOLDOWN_SECS - (now - last_loss))
                        reasons.append(f"cooldown {remaining}s")
                    # ── Divergence veto — hard block when indicators conflict with price action ──
                    # RSI divergence: bearish → fade longs; bullish → fade shorts
                    div = sig.get("rsi_divergence")
                    if div == "BEARISH" and d == "LONG":
                        reasons.append("bearish RSI divergence — LONG vetoed")
                    if div == "BULLISH" and d == "SHORT":
                        reasons.append("bullish RSI divergence — SHORT vetoed")
                    # Price action divergence: lower highs during LONG = distribution; higher lows during SHORT = accumulation
                    # Exception: high-beta alts in PAIR_LH_RELAXED bypass the lower-highs LONG block
                    # when StochRSI is deeply oversold (≤ 20) — that combination means a pullback
                    # within a broader uptrend, not distribution, and StRSI confirms a bounce setup.
                    if d == "LONG" and sig.get("lower_highs"):
                        sr_lh = sig.get("srsi", 50)
                        if pair in PAIR_LH_RELAXED and sr_lh <= 20:
                            pass   # StRSI deeply oversold on a known pullback alt — allow through
                        else:
                            reasons.append("lower highs (distribution) vs LONG — whipsaw risk")
                    if d == "SHORT" and sig.get("higher_lows"):
                        reasons.append("higher lows (accumulation) vs SHORT — whipsaw risk")
                    # MACD cross divergence: if MACD just crossed against the trade direction, veto
                    if d == "LONG"  and sig.get("macd_cross_down"):
                        reasons.append("MACD bearish zero-cross vs LONG — momentum reversal")
                    if d == "SHORT" and sig.get("macd_cross_up"):
                        reasons.append("MACD bullish zero-cross vs SHORT — momentum reversal")
                    # Volume gate — #VOL-GATE: vr < 0.7 is a hard block during normal hours
                    # (genuinely dead volume; position size halving at vr < 0.8 still applies).
                    # Overnight mode relaxes this to 0.55 — lower volume is expected and normal
                    # during overnight sessions, so a stricter gate would block most signals.
                    vr_check = sig.get("vol_ratio", 1.0)
                    _vol_gate = 0.45 if overnight else 0.70
                    if vr_check < _vol_gate:
                        reasons.append(f"vol {vr_check:.2f}x < {_vol_gate:.2f} min — dead volume gate{'  (overnight)' if overnight else ''}")
                    # Funding rate block
                    fn = sig.get("funding", 0)
                    if d == "LONG"  and fn >  5.0: reasons.append(f"funding {fn:+.2f}% vs LONG")
                    if d == "SHORT" and fn < -5.0: reasons.append(f"funding {fn:+.2f}% vs SHORT")
                    # Flat market: EMA9 and EMA21 too close = no real trend = unreliable signal.
                    # Overnight: EMAs compress naturally with lower ATR — relax to 0.01%.
                    # Also skip entirely if the ATR gate already passed (market isn't truly flat).
                    ema_gap = sig.get("ema_gap_pct", 1.0)
                    _ema_gap_min = 0.01 if overnight else 0.02
                    _atr_passed = sig.get("atr_ok", True)
                    if ema_gap < _ema_gap_min and not (overnight and _atr_passed):
                        reasons.append(f"flat market EMA gap {ema_gap:.3f}%{'  (overnight limit: 0.01%)' if overnight else ''}")
                    # ATR gate: hard block on dead markets — score is irrelevant if price isn't moving
                    if not sig.get("atr_ok", True):
                        _atr_min_this = PAIR_ATR_MIN.get(pair, 0.06)
                        reasons.append(f"ATR too low ({sig.get('atr_pct',0):.3f}% < {_atr_min_this:.2f}%) — market flat")
                    # MACD momentum check: only block when histogram has been
                    # shrinking for 2+ consecutive bars. A single flat/reversal
                    # bar after a strong run was firing this too often, killing
                    # valid continuation signals. macd_building requires 3 bars
                    # of consecutive growth — the inverse (not building) fires on
                    # any single wobble. Tightened: require 2-bar confirmed fade.
                    mh = sig.get("macd_h", 0)
                    _macd_scalp_exempt = sig.get("ob_scalp") or sig.get("pullback_scalp")
                    if not _macd_scalp_exempt:
                        _hist = sig.get("macd_hist", [])   # raw histogram series
                        _fading_short = (len(_hist) >= 3 and mh < 0
                                         and _hist[-1] > _hist[-2] > _hist[-3])  # bars getting less negative = fading sell
                        _fading_long  = (len(_hist) >= 3 and mh > 0
                                         and _hist[-1] < _hist[-2] < _hist[-3])  # bars getting less positive = fading buy
                        if d == "SHORT" and _fading_short:
                            reasons.append("MACD momentum fading (2-bar confirmed)")
                        if d == "LONG"  and _fading_long:
                            reasons.append("MACD momentum fading (2-bar confirmed)")
                    # Candle body quality — #CANDLE-BODY: doji/spinning-top right before
                    # entry is a strong indecision signal. Check last COMPLETED candle
                    # (candles[-2]); candles[-1] is still forming.
                    # Overnight: lower ATR produces naturally thin bodies — relax 0.20 → 0.12.
                    _candles = sig.get("candles", [])
                    _doji_min = 0.08 if overnight else 0.20
                    if len(_candles) >= 2:
                        _last_done = _candles[-2]
                        _wick = _last_done.get("high", 0) - _last_done.get("low", 0)
                        if _wick > 0:
                            _body = abs(_last_done.get("close", 0) - _last_done.get("open", 0))
                            if _body / _wick < _doji_min:
                                reasons.append(
                                    f"doji candle (body {_body/_wick:.0%} of range) — indecision{'  (overnight limit: 12%)' if overnight else ''}")

                    # ── #MIN1-PURE: tighter filters for Min1 single-TF mode ───
                    # Only applies when dual TF is OFF and TF is set to Min1.
                    # Min1 candles are noisier — dojis, partial moves, wick traps
                    # are far more common. These extra gates compensate.
                    if sig.get("min1_pure"):
                        m1_candles = sig.get("candles_raw") or sig.get("candles", [])

                        # 1. Tighter body ratio: raise 0.20 → 0.30
                        if len(m1_candles) >= 2:
                            _lc = m1_candles[-2]
                            _wick_m1 = _lc.get("high", 0) - _lc.get("low", 0)
                            if _wick_m1 > 0:
                                _body_m1 = abs(_lc.get("close", 0) - _lc.get("open", 0))
                                if _body_m1 / _wick_m1 < 0.30:
                                    # Remove existing 0.20 doji reason if already added, replace
                                    reasons = [r for r in reasons if "doji candle" not in r]
                                    reasons.append(
                                        f"Min1 doji (body {_body_m1/_wick_m1:.0%} < 30%) — noise filter")

                        # 2. Multi-candle confirmation: 2 of last 3 candles must agree
                        if len(m1_candles) >= 3 and d in ("LONG", "SHORT"):
                            agree = 0
                            for _bar in m1_candles[-3:]:
                                _bull = _bar.get("close", 0) >= _bar.get("open", 0)
                                if d == "LONG"  and _bull:  agree += 1
                                if d == "SHORT" and not _bull: agree += 1
                            if agree < 2:
                                reasons.append(
                                    f"Min1 multi-candle: only {agree}/3 candles confirm {d}")

                        # 3. Wick rejection: opposing wick > 60% of total range blocks entry
                        if len(m1_candles) >= 1:
                            _lc2 = m1_candles[-2] if len(m1_candles) >= 2 else m1_candles[-1]
                            _rng = _lc2.get("high", 0) - _lc2.get("low", 0)
                            if _rng > 0:
                                _op2 = _lc2.get("open", 0)
                                _cl2 = _lc2.get("close", 0)
                                _body_top = max(_op2, _cl2)
                                _body_bot = min(_op2, _cl2)
                                if d == "LONG":
                                    _upper_wick = _lc2.get("high", 0) - _body_top
                                    if _upper_wick / _rng > 0.60:
                                        reasons.append(
                                            f"Min1 upper wick {_upper_wick/_rng:.0%} > 60% — rejection vs LONG")
                                elif d == "SHORT":
                                    _lower_wick = _body_bot - _lc2.get("low", 0)
                                    if _lower_wick / _rng > 0.60:
                                        reasons.append(
                                            f"Min1 lower wick {_lower_wick/_rng:.0%} > 60% — rejection vs SHORT")

                        # 4. Tighter RSI gate: no LONG above 72, no SHORT below 28
                        if d == "LONG"  and rv_ > 72:
                            reasons = [r for r in reasons if "RSI" not in r or "overbought" not in r]
                            reasons.append(f"Min1 RSI {rv_:.0f} > 72 overbought — tighter gate")
                        if d == "SHORT" and rv_ < 28:
                            reasons = [r for r in reasons if "RSI" not in r or "oversold" not in r]
                            reasons.append(f"Min1 RSI {rv_:.0f} < 28 oversold — tighter gate")

                        # 5. Tighter EMA gap: require 0.04% (double the normal 0.02%)
                        if ema_gap < 0.04:
                            reasons = [r for r in reasons if "flat market EMA gap" not in r]
                            reasons.append(f"Min1 EMA gap {ema_gap:.3f}% < 0.04% — crosses too frequent")

                        # 6. Consecutive candle limit: block after 3 same-colour (not 4)
                        if d == "LONG"  and cg_ >= 3:
                            reasons = [r for r in reasons if "consecutive green" not in r]
                            reasons.append(f"Min1: {cg_} consecutive green candles — chasing (Min1 limit 3)")
                        if d == "SHORT" and cr_ >= 3:
                            reasons = [r for r in reasons if "consecutive red" not in r]
                            reasons.append(f"Min1: {cr_} consecutive red candles — chasing (Min1 limit 3)")

                    if reasons:
                        return False, " | ".join(reasons)
                    return True, None

                # Rank: prefer LONG/SHORT over HOLD, then by score descending
                raw_candidates = [(p, s) for p, s in all_sigs.items()
                                   if s["direction"] in ("LONG", "SHORT")]
                raw_candidates.sort(key=lambda x: x[1]["score"], reverse=True)

                # Apply filters
                candidates = []
                for p, s in raw_candidates:
                    # #MIN1-PURE: require 0.5 extra score in Min1 pure mode
                    # Compensates for noisier timeframe — only high-conviction signals get through
                    if s.get("min1_pure"):
                        min1_thr = _thr_eff + 0.5
                        if s["score"] < min1_thr:
                            self._log(
                                f"  ↷ {pair_label(p)} {s['direction']} Min1 score {s['score']:.1f} "
                                f"< {min1_thr:.1f} threshold (Min1 pure +0.5 nudge)", DIM)
                            continue
                    ok, reason = _passes_filters(p, s)
                    if ok:
                        candidates.append((p, s))
                    else:
                        self._log_event(f"  ↷ {pair_label(p)} {s['direction']} filtered: {reason}", DIM)

                # Top signal for display
                if candidates:
                    top_pair, top_sig = candidates[0]
                elif all_sigs:
                    # Only the single highest-scoring pair is needed here — max() is
                    # O(n) vs. sorting the whole dict just to take element [0].
                    top_pair, top_sig = max(all_sigs.items(), key=lambda x: x[1]["score"])
                else:
                    top_pair, top_sig = None, {}

                if n_open >= maxt:
                    self._log_event(f"Max trades ({maxt}) reached — monitoring only", DIM)

                elif candidates:
                    # Signal found
                    best_pair, best_sig = candidates[0]
                    self._last_signal_pair = best_pair
                    self._last_signal_time = time.time()
                    self._last_signal_dir  = best_sig["direction"]
                    self._hold_streak      = 0
                    best_px = self.current_prices.get(best_pair, 0)

                    # ── Adaptive threshold check ─────────────────────────────
                    entry_thr = self._adaptive_engine.get_threshold(
                        best_pair, best_sig.get("atr_pct", 0))
                    # #TOD-BONUS: peak-liquidity window bonus widens effective margin
                    effective_score = best_sig["score"] + _tod_bonus
                    if _tod_bonus > 0:
                        self._log(f"  TOD bonus +{_tod_bonus} (peak liquidity window) → "
                                  f"effective score {effective_score:.1f}/9", DIM)
                    # Low volume: log it but don't raise threshold — score already
                    # accounts for volume via the vol_ratio indicator point
                    vr = best_sig.get("vol_ratio", 1.0)
                    if vr < 0.5:
                        entry_thr += 0.5  # only penalise extremely dead volume

                    if effective_score < entry_thr:
                        self._log_event(f"Score {best_sig['score']}/9 (eff {effective_score:.1f}) < adaptive threshold "
                                  f"{entry_thr}/9 — skipping", DIM)
                        best_pair = None  # treat as HOLD

                    if best_pair:
                        # Block pairs excluded from live API trading
                        if not dry and best_pair in API_EXCLUDED:
                            self._log(
                                f"⚠ {best_pair.replace('_USDT','')} excluded from live API "
                                f"trading — signal skipped", AMBER)
                            best_pair = None
                    if best_pair:
                        # Check we don't already have this pair+direction (unless stacking)
                        existing_same = [p for p in self.state.positions.values()
                                         if p.symbol == best_pair
                                         and p.direction == best_sig["direction"]
                                         and not p.hedge_of]
                        is_long   = best_sig["direction"] == "LONG"
                        # ── Improved stacking guards ──────────────────────────────
                        # 1. Score must clear threshold by a margin (not just squeak over)
                        stack_score_gap = best_sig["score"] - stack_thr
                        # 2. H1 trend must align with stack direction (no counter-trend stacks)
                        h1_aligned = (self._h1_trends.get(best_pair) == "BULL") if is_long else \
                                     (self._h1_trends.get(best_pair) == "BEAR")
                        # 3. No existing position in a loss > 10% margin (don't average down into losers)
                        any_losing = any(
                            ((cur_px - p.entry_price) / p.entry_price * p.leverage * 100 < -10
                             if p.direction == "LONG"
                             else (p.entry_price - cur_px) / p.entry_price * p.leverage * 100 < -10)
                            for p in existing_same
                            if (cur_px := self.current_prices.get(best_pair, p.entry_price))
                        )
                        # 4. MACD cross is a strong confirmation for stacking
                        macd_confirms = best_sig.get("macd_cross_up") if is_long else best_sig.get("macd_cross_down")
                        can_stack = (stack_on and is_long
                                     and best_sig["score"] >= stack_thr
                                     and stack_score_gap >= 0.5       # must beat threshold by 0.5+
                                     and h1_aligned                    # H1 must agree
                                     and not any_losing                # no averaging down into losses
                                     and len(existing_same) < stack_max)

                        if not existing_same or can_stack:
                            contract_n = len(existing_same) + 1
                            stack_tag  = f" [#{contract_n}]" if contract_n > 1 else ""
                            conf_tag   = f"  ⚡ HIGH CONF" if can_stack else ""
                            pair_lev   = min(lev, PAIR_MAX_LEV.get(best_pair, lev))

                            # ── Use margin exactly as set by user ────────────
                            # No volume scaling, no Kelly sizing, no pullback
                            # halving — the user sets the margin they want.
                            actual_mg = mg

                            # ── Contract-count minimum floor ─────────────────────────
                            # For pairs using integer contracts (DOGE, TRX, XRP etc.),
                            # if margin halving/Kelly pushes below 1-contract minimum,
                            # raise actual_mg to exactly the minimum needed rather than
                            # letting the order fail silently with vol=0.
                            if _learned_precision.get(best_pair) == -1:
                                _cs  = PAIR_CONTRACT_SIZE.get(best_pair, 1.0)
                                _px  = self.current_prices.get(best_pair, 0)
                                if _cs > 0 and _px > 0:
                                    _min_mg = round((_px * _cs) / pair_lev, 4)
                                    if actual_mg < _min_mg:
                                        self._log_event(
                                            f"Margin floored to 1-contract minimum "
                                            f"${_min_mg:.4f} (was ${actual_mg:.2f} after scaling)", DIM)
                                        actual_mg = _min_mg

                            _pb_tag = (" [PULLBACK]" if best_sig.get("pullback_scalp")
                                       else " [OB-SCALP]" if best_sig.get("ob_scalp")
                                       else "")
                            self._log_event(
                                f"BEST SIGNAL: {best_sig['direction']}{stack_tag}{_pb_tag} "
                                f"{best_pair.replace('_USDT','')}  "
                                f"score {best_sig['score']}/9  RSI {best_sig['rsi']:.1f}  "
                                f"{best_sig['trend']}{conf_tag}  thr:{entry_thr}/9",
                                AMBER if best_sig.get("pullback_scalp") else (
                                CYAN  if best_sig.get("ob_scalp") else (
                                BLUE  if not can_stack else CYAN)))

                            if len(candidates) > 1:
                                ru_p, ru_s = candidates[1]
                                self._log(
                                    f"Runner-up: {ru_s['direction']} "
                                    f"{ru_p.replace('_USDT','')} {ru_s['score']}/9", DIM)

                            final_sl, final_tp = sl, tp

                            # ── #PULLBACK: tighten TP/SL/margin for counter-trend scalps ──
                            # These trades go against H1/H4 so we take profit fast and cut
                            # losses faster — the larger trend can resume at any moment.
                            if best_sig.get("pullback_scalp"):
                                pb_h1 = best_sig.get("pullback_h1", False)
                                pb_h4 = best_sig.get("pullback_h4", False)
                                pb_tag = "H1+H4" if (pb_h1 and pb_h4) else ("H1" if pb_h1 else "H4")
                                final_tp = round(tp * 0.40, 6)   # TP = 40% of normal TP (quick exit)
                                final_sl = round(sl * 0.60, 6)   # SL = 60% of normal SL (cut fast)
                                self._log(
                                    f"  ⚡ PULLBACK SCALP ({pb_tag} counter-trend) — "
                                    f"TP→{final_tp*100:.2f}% SL→{final_sl*100:.2f}% "
                                    f"size→${actual_mg:.2f}", AMBER)

                            # ── #OB-SCALP: even tighter params — pure exhaustion scalp ──
                            # RSI/StochRSI extreme + MACD histogram shrinking but no wick.
                            # TP is tighter (30%) because we're entering before any
                            # confirmation candle — just grabbing the first bounce tick.
                            elif best_sig.get("ob_scalp"):
                                ob_h1 = best_sig.get("ob_scalp_h1", False)
                                ob_h4 = best_sig.get("ob_scalp_h4", False)
                                ob_tag = "H1+H4" if (ob_h1 and ob_h4) else ("H1" if ob_h1 else "H4")
                                final_tp = round(tp * 0.30, 6)   # TP = 30% of normal TP (faster exit)
                                final_sl = round(sl * 0.50, 6)   # SL = 50% of normal SL (tightest cut)
                                self._log(
                                    f"  🔄 OB EXHAUSTION SCALP ({ob_tag} counter-trend) — "
                                    f"RSI extreme + MACD hist shrinking — "
                                    f"TP→{final_tp*100:.2f}% SL→{final_sl*100:.2f}% "
                                    f"size→${actual_mg:.2f}", CYAN)

                            # Open position immediately based on indicators
                            pid = self._open_position(best_pair, best_sig["direction"],
                                                       best_px, actual_mg, pair_lev,
                                                       final_sl, final_tp, dry, ak, asc)
                            if pid:
                                pos = self.state.positions[pid]
                                pc  = GREEN if pos.direction == "LONG" else RED
                                self._log(
                                    f"OPENED {pos.direction}{stack_tag} "
                                    f"{pair_label(best_pair)} {pair_lev}x  "
                                    f"@ ${best_px:,.4f}  "
                                    f"LIQ ${pos.liq_price:,.4f}", pc)
                                open_reason = (f"Score {best_sig['score']}/9  "
                                               f"RSI {best_sig['rsi']:.0f}  "
                                               f"{best_sig['trend']}  thr:{entry_thr}/9  "
                                               f"vol:{vr:.1f}x  size:{actual_mg}$"
                                               + ("  [PULLBACK]" if best_sig.get("pullback_scalp") else
                                                  "  [OB-SCALP]" if best_sig.get("ob_scalp") else ""))
                                sl_used = f"SL {final_sl*100:.2f}%  TP {final_tp*100:.2f}%"
                                self._ai_log_event(pid, "TRADE OPENED",
                                    f"{pos.direction} {pair_label(best_pair)} @ ${best_px:,.4f}  "
                                    f"{sl_used}\n{open_reason}",
                                    GREEN if pos.direction=="LONG" else RED)
                                self._refresh_metrics(); self._save()
                                self._balance_fetch = 0
                                self._fetch_live_balance()
                                self.root.after(0, self._refresh_trades_tab)

                                # ── #CLAUDE-CONF: async Claude veto review ────
                                # Fire claude_decision in a background thread immediately
                                # after opening. If Claude returns confidence < 55 the
                                # position is closed before the next monitor pass.
                                if ck and ANTHROPIC_AVAILABLE:
                                    _last3 = ", ".join(
                                        f"{t['symbol'].replace('_USDT','')} "
                                        f"{t['direction']} "
                                        f"{'W' if t.get('pnl_usdt',0)>=0 else 'L'}"
                                        for t in self.state.trades[-3:]
                                    ) or "no trades yet"
                                    def _bg_veto(
                                            _pid=pid, _sig=best_sig, _st=self.state,
                                            _sym=best_pair, _lv=pair_lev, _mg=actual_mg,
                                            _sl=final_sl, _tp=final_tp, _ck=ck, _l3=_last3,
                                            _dry=dry, _ak=ak, _asc=asc):
                                        try:
                                            cd = claude_decision(
                                                _sig, _st, _sym, _lv, _mg,
                                                _sl, _tp, _ck, _l3)
                                            if cd is None:
                                                return
                                            conf = cd.get("confidence", 100)
                                            action = cd.get("action", "TRADE").upper()
                                            reason = cd.get("reason", "")
                                            if action == "VETO" or conf < 55:
                                                # Veto: close position immediately
                                                if _pid in self.state.positions:
                                                    self._log(
                                                        f"⚠ Claude VETO (conf={conf}) "
                                                        f"{_sym.replace('_USDT','')} — closing: "
                                                        f"{reason[:80]}", AMBER)
                                                    self._ai_log_event(
                                                        _pid, "CLAUDE VETO",
                                                        f"conf={conf} action={action} | {reason}",
                                                        AMBER)
                                                    self._close_position_by_id(
                                                        _pid, _dry, _ak, _asc, "VETO")
                                            else:
                                                self._log(
                                                    f"Claude TRADE conf={conf} "
                                                    f"{_sym.replace('_USDT','')} — {reason[:60]}",
                                                    DIM)
                                        except Exception as _exc:
                                            _file_logger.debug(
                                                "Claude veto check error: %s", _exc)
                                    threading.Thread(target=_bg_veto, daemon=True).start()
                        else:
                            self._log(
                                f"Already in {best_sig['direction']} {best_pair.replace('_USDT','')} "
                                f"— waiting for exit or different pair", DIM)

                else:
                    # All pairs HOLD
                    self._hold_streak += 1
                    self._adaptive_engine.hold_streak = self._hold_streak
                    _pre_thr = getattr(self, "_overnight_pre_thr", None)
                    _thr_note = (f"  🌙 overnight relaxed from {_pre_thr}"
                                 if _pre_thr else "")
                    _eff_thr = self._adaptive_engine.get_threshold(
                        top_pair, self.pair_signals.get(top_pair, {}).get("atr_pct", 0.1)
                    ) if top_pair else thr
                    _adapt_note = (f" (adaptive: {_eff_thr:.1f})" if abs(_eff_thr - thr) >= 0.1 else "")
                    self._log_event(f"All pairs HOLD — no signal above threshold {thr}/9{_adapt_note}{_thr_note}  "
                              f"(streak: {self._hold_streak})", DIM)
                    if ck and (time.time() - self._last_claude_call) > 60 and top_pair:
                        def _bg_claude(s=top_sig, c=ck, st=self.state,
                                       sy=top_pair, lv=lev, mg_=mg):
                            reason = claude_reasoning(s, st, sy, lv, mg_, c)
                            if reason:
                                self._log_event(f"AI (all HOLD): {reason}", PURPLE)
                            self._last_claude_call = time.time()
                        threading.Thread(target=_bg_claude, daemon=True).start()

            except Exception as e:
                self._log(f"ERROR: {e}", RED)

            for _ in range(self._ivl()):
                if self._stop_event.is_set(): break
                time.sleep(1)

    def _kelly_size(self, base_margin: float) -> float:
        """
        Kelly Criterion position sizing.

        Kelly fraction f* = (p*b - q) / b
          where:  p = win probability,  q = 1-p,
                  b = avg_win / avg_loss  (win/loss ratio)

        We use a fractional Kelly (25% Kelly) to reduce variance.
        Floors at 50% of base margin (never bet too small) and
        caps at 150% (never over-size). Falls back to base_margin when
        there is insufficient history (<10 closed trades) or degenerate stats.
        """
        try:
            total = self._kelly_wins + self._kelly_losses
            if total < 10 or self._kelly_avg_loss <= 0 or self._kelly_avg_win <= 0:
                return base_margin   # not enough history — use configured margin

            p = self._kelly_wins / total          # win rate
            q = 1.0 - p
            b = self._kelly_avg_win / self._kelly_avg_loss   # win/loss ratio

            kelly_f = (p * b - q) / b             # full Kelly fraction
            frac_kelly = kelly_f * 0.25            # 25% fractional Kelly

            # Clamp: never go below 50% or above 150% of the configured margin
            frac_kelly = max(0.50, min(1.50, frac_kelly))
            sized = round(base_margin * frac_kelly, 2)

            if abs(frac_kelly - 1.0) > 0.05:
                self._log(
                    f"Kelly sizing: p={p:.2f} b={b:.2f} f*={kelly_f:.3f} "
                    f"frac={frac_kelly:.2f} → ${sized:.2f} (base ${base_margin:.2f})", DIM)
            return sized
        except Exception:
            return base_margin

    def _open_position(self, sym, direction, px, mg, lev, sl_pct, tp_pct,
                        dry, ak, asc, hedge_of=""):
        # Always re-read dry_var to ensure live/paper is respected
        dry = self.dry_var.get()

        # Safety net: never place live orders for API-excluded pairs
        if not dry and sym in API_EXCLUDED:
            self._log_event(f"⚠ {sym} blocked — excluded from live API trading", AMBER)
            return None

        # ── ATR-based SL minimum: SL must be outside normal wick noise ────────
        # If the configured SL is tighter than 1.5x ATR, widen it to 1.5x ATR.
        # This prevents SL landing inside the range of normal candle wicks —
        # which causes premature stop-outs before price has a chance to move.
        try:
            candles_for_atr = self.pair_candles.get(sym, [])
            if candles_for_atr:
                atr_raw = atr(candles_for_atr, 14)
                atr_as_pct = atr_raw / px if px > 0 else 0
                # v2.8-TUNED: wider ATR-based SL floor (was 1.5x) so normal wick
                # noise can't stop the trade out before it has room to work.
                atr_min_sl = atr_as_pct * TUNED_ATR_SL_MULT
                if sl_pct < atr_min_sl:
                    self._log(
                        f"SL widened {sl_pct*100:.3f}% → {atr_min_sl*100:.3f}% "
                        f"(1.5x ATR {atr_as_pct*100:.3f}%) to clear wick noise", AMBER)
                    sl_pct = atr_min_sl
        except Exception:
            pass  # ATR check is advisory only; never block a trade over it

        # ── Smart leverage-aware SL/TP scaling ───────────────────────────────────
        # High leverage = small price move = large margin swing.
        # At 50x, a 0.8% SL = 40% margin loss — too wide. Scale linearly.
        # At 5x,  a 0.8% SL = 4% margin loss  — reasonable.
        # Reference leverage for neutral scaling: 10x
        # Adjust: SL and TP both scale by sqrt(10 / lev) — preserves R/R ratio,
        # tightens stops at high leverage to limit absolute dollar risk.
        try:
            LEV_REF = 10.0
            if lev != LEV_REF and lev > 0:
                lev_scale = (LEV_REF / lev) ** 0.5   # √(10/lev): <1 at high lev, >1 at low lev
                # Only tighten (high leverage) — never widen beyond configured values
                # This preserves user intent at low leverage while protecting high-lev trades
                if lev > LEV_REF:
                    new_sl = round(sl_pct * lev_scale, 6)
                    new_tp = round(tp_pct * lev_scale, 6)
                    self._log(
                        f"Lev-scale ({lev}x): SL {sl_pct*100:.3f}%→{new_sl*100:.3f}%  "
                        f"TP {tp_pct*100:.3f}%→{new_tp*100:.3f}%  "
                        f"(√{LEV_REF}/{lev}={lev_scale:.3f})", DIM)
                    sl_pct = new_sl
                    tp_pct = new_tp
        except Exception as _exc:
            _file_logger.debug("suppressed error: %s", _exc)

        # ── Fee + slippage + R/R enforcement ─────────────────────────────────────
        # Open leg uses limit order (maker fee 0.04%); close leg is always market
        # (taker fee 0.06%). Round-trip = maker + taker, not taker * 2.
        # Slippage is near-zero for limit fills; use 0.01% as a small allowance
        # for the rare market-fallback case when the limit doesn't fill.
        # Rule 1: TP must deliver net profit above fees + slippage.
        # Rule 2: Net R/R must be ≥ 1.5 (net reward ÷ net risk after fees on both legs).
        FEE_PCT      = self._fee_maker + self._fee_taker  # open(maker) + close(taker)
        SLIP_PCT     = 0.0001                              # 0.01% allowance for market fallback
        TOTAL_COST   = FEE_PCT + SLIP_PCT                  # total price-move eaten before profit
        MIN_NET_PROF = 0.0015                              # minimum 0.15% net profit above costs
        MIN_TP       = TOTAL_COST + MIN_NET_PROF           # absolute TP floor

        if tp_pct < MIN_TP:
            old_tp = tp_pct
            tp_pct = MIN_TP
            self._log(
                f"TP raised {old_tp*100:.3f}% → {tp_pct*100:.3f}% "
                f"(maker {self._fee_maker*100:.3f}% + taker {self._fee_taker*100:.3f}%"
                f" + slip {SLIP_PCT*100:.2f}% + min profit {MIN_NET_PROF*100:.2f}%)",
                AMBER)

        # Net R/R: open cost (maker+slip) on entry, close cost (taker) on exit
        open_cost    = self._fee_maker + SLIP_PCT   # paid when entering
        close_cost   = self._fee_taker              # paid when exiting
        net_risk     = sl_pct + open_cost + close_cost
        # v2.8-TUNED: pin TP to a *reachable* multiple of net risk instead of the
        # old wide ~2.6-3x table that price rarely reached. This both widens TP
        # when it was too tight (fees) AND tightens it when it was too far —
        # directly fixing the "rarely hits TP" problem. Partial-TP (below) banks
        # profit even earlier, so the final TP being closer is doubly safe.
        target_tp = net_risk * TUNED_RR_TARGET + open_cost + close_cost
        old_tp = tp_pct
        tp_pct = max(MIN_TP, target_tp)
        if abs(tp_pct - old_tp) > 1e-9:
            _dir = "tightened" if tp_pct < old_tp else "widened"
            self._log_event(
                f"TP {_dir} {old_tp*100:.3f}% → {tp_pct*100:.3f}% "
                f"(v2.8 target net R/R {TUNED_RR_TARGET:.2f}, "
                f"net risk {net_risk*100:.3f}%)",
                AMBER)
        # Log the effective net R/R so it's always visible in the trade log
        eff_net_reward = tp_pct - open_cost - close_cost
        eff_net_risk   = sl_pct + open_cost + close_cost
        eff_net_rr = eff_net_reward / eff_net_risk if eff_net_risk > 0 else 0
        self._log(
            f"Fee check: maker {self._fee_maker*100:.3f}% + taker {self._fee_taker*100:.3f}%"
            f" + slip ~{SLIP_PCT*100:.2f}%"
            f"  → net R/R {eff_net_rr:.2f}  (TP {tp_pct*100:.3f}% / SL {sl_pct*100:.3f}%)",
            CYAN)

        if direction == "LONG":
            SL  = round_price(sym, px * (1 - sl_pct))
            TP  = round_price(sym, px * (1 + tp_pct))
            LIQ = round(px * (1 - 1 / lev), 6)
        else:
            SL  = round_price(sym, px * (1 + sl_pct))
            TP  = round_price(sym, px * (1 - tp_pct))
            LIQ = round(px * (1 + 1 / lev), 6)

        oid = f"DRY-{int(time.time())}"
        open_fee_type = "taker"   # default; overridden to "maker" if limit order fills
        if not dry:
            # Refresh live balance synchronously before order so "available" is never stale.
            # _fetch_live_balance() spawns a background thread; call get_live_account directly
            # here to guarantee the balance reflects any margin already locked by open positions.
            try:
                fresh = get_live_account(ak, asc)
                if fresh:
                    self._live_balance = fresh
                    self._balance_fetch = time.time()
            except Exception as _exc:
                _file_logger.debug("suppressed error: %s", _exc)
            avail = (self._live_balance or {}).get("available", 0)
            if avail > 0 and mg > avail:
                self._log(
                    f"⚠ Order skipped: margin ${mg:.2f} > available ${avail:.2f} USDT — "
                    f"reduce margin or free up balance", RED)
                return None

            side = 1 if direction == "LONG" else 3   # Futures: 1=open long, 3=open short
            # Vol calculation: USDT notional for most pairs (confirmed BTC + NVDA).
            # If a previous order for this pair got 2015 and succeeded on contract-count
            # retry, _learned_precision[sym] == -1 (sentinel) — use contracts directly.
            if _learned_precision.get(sym) == -1:
                cs_   = PAIR_CONTRACT_SIZE.get(sym, 1.0)
                px__  = self.current_prices.get(sym, 0)
                if cs_ > 0 and px__ > 0:
                    vol = int((mg * lev) / (px__ * cs_))
                    if vol < 1:
                        # Margin too small for even 1 contract — calculate minimum needed
                        min_mg_needed = (px__ * cs_) / lev
                        self._log_event(
                            f"⚠ {sym} skipped: margin ${mg:.2f} too small for 1 contract "
                            f"(need ≥ ${min_mg_needed:.2f} at {lev}x  |  "
                            f"1 contract = {cs_} units × ${px__:.4f})", AMBER)
                        return None
                    self._log(f"Vol (contract-count mode): {vol} contracts for {sym}", DIM)
                else:
                    vol = round_vol(sym, mg * lev)
            else:
                # Integer contract-count: vol = int(margin * leverage / (price * contractSize))
                # MEXC API confirms volScale=0, volUnit=1 for ALL pairs — integers only.
                cs_  = PAIR_CONTRACT_SIZE.get(sym, 1.0)
                px__ = self.current_prices.get(sym, px)
                if cs_ > 0 and px__ > 0:
                    vol = max(1, int((mg * lev) / (px__ * cs_)))
                else:
                    vol = max(1, int(mg * lev))
                self._log(f"Vol (contracts): {vol} [{sym} cs={cs_} px={px__:.4f} notional={mg*lev:.2f}]", DIM)
            # Minimum is 1 contract — already enforced by max(1, int(...)) above

            # Sanity check — MEXC rejects absurdly large volumes
            if vol > 100_000_000:
                self._log_event(f"Order skipped: {sym} vol={vol:,.0f} is too large "
                          f"(price too small for margin size)", AMBER)
                return None
            if vol == 0:
                # Calculate the exact minimum margin needed for 1 contract at live price.
                # Formula: min_margin = contract_size * price / leverage
                # This gives the user a concrete number to set the margin slider to.
                vol_min_usdt = PAIR_VOL_MIN_USDT.get(sym, 1.0)
                min_mg_dynamic = round(vol_min_usdt / lev, 4) if lev > 0 else None
                min_mg_ref     = PAIR_MIN_MARGIN.get(sym)
                if min_mg_dynamic:
                    self._log(
                        f"⚠ Order skipped: {sym} vol=0 — margin ${mg:.2f} is too small "
                        f"for 1 contract at ${px:.2f} with {lev}x leverage. "
                        f"Minimum needed: ${min_mg_dynamic:.2f} USDT "
                        f"(= 1 contract × ${px:.2f} ÷ {lev}x). "
                        f"Increase your margin slider to at least ${math.ceil(min_mg_dynamic) + 1}.",
                        AMBER)
                else:
                    self._log_event(f"Order skipped: {sym} vol=0 after rounding "
                              f"(margin too small for one contract)", AMBER)
                return None

            self._log(f"Sending order: {sym} {direction} vol={vol} side={side} "
                      f"type=5 openType=1 px={px:.4f}", DIM)

            # ── Try limit order first (dynamic ATR-based offset) ─────────────
            atr_p = self.pair_signals.get(sym, {}).get("atr_pct", 0.03)
            LIMIT_OFFSET = max(0.0001, min(0.0005, atr_p / 100 * 0.5))
            limit_px = round(px * (1 - LIMIT_OFFSET) if direction == "LONG"
                             else px * (1 + LIMIT_OFFSET), 6)
            try:
                lresp = mexc_private("POST", "/api/v1/private/order/submit",
                                     {"symbol": sym, "price": limit_px, "vol": vol,
                                      "side": side, "type": 1, "openType": 1,
                                      "leverage": lev}, ak, asc, dry)
                # Treat 510 rate-limit on limit order as a soft failure → fall through to market
                if not lresp.get("success") and lresp.get("code") == 510:
                    self._log(f"⏳ Limit order rate-limited (510) — falling back to market", AMBER)
                    time.sleep(2)
                    limit_oid = None
                else:
                    limit_oid = str(lresp.get("data","")) if lresp.get("success") else None
            except Exception:
                limit_oid = None

            if limit_oid:
                self._log(f"Limit order placed @ ${limit_px:,.6g} — waiting up to 20s", CYAN)
                filled = False
                for _ in range(4):
                    time.sleep(5)
                    try:
                        chk = mexc_private("GET", "/api/v1/private/order/get/" + limit_oid,
                                           {"symbol": sym}, ak, asc, dry)
                        st  = (chk or {}).get("data", {}).get("state")
                        if st == 2:
                            filled = True
                            fill_px = (chk.get("data",{}).get("dealAvgPrice") or limit_px)
                            px = float(fill_px)
                            break
                        elif st in (4, 5):
                            break
                    except Exception:
                        break
                if filled:
                    oid = limit_oid
                    open_fee_type = "maker"
                    self._log(f"\u2713 Limit filled @ ${px:,.6g} (maker fee {self._fee_maker*100:.3f}%)", GREEN)
                    if direction == "LONG":
                        SL  = round_price(sym, px * (1 - sl_pct))
                        TP  = round_price(sym, px * (1 + tp_pct))
                        LIQ = round(px * (1 - 1/lev),  6)
                    else:
                        SL  = round_price(sym, px * (1 + sl_pct))
                        TP  = round_price(sym, px * (1 - tp_pct))
                        LIQ = round(px * (1 + 1/lev),  6)
                else:
                    # Cancel and fall back to market
                    try:
                        mexc_private("POST", "/api/v1/private/order/cancel",
                                     {"symbol": sym, "orderId": limit_oid}, ak, asc, dry)
                    except Exception as _exc:
                        _file_logger.debug("suppressed error: %s", _exc)
                    self._log(f"Limit unfilled \u2014 falling back to market", AMBER)
                    limit_oid = None

            if not limit_oid:
                # Market order (original logic with retry)
                pass

            if not limit_oid:
              try:
                resp = mexc_private("POST", "/api/v1/private/order/submit",
                                    {"symbol": sym, "price": 0, "vol": vol,
                                     "side": side, "type": 5,
                                     "openType": 1, "leverage": lev},
                                    ak, asc, dry)
                # Code 510 = exchange-level rate limit ("Requests are too frequent").
                # Back off and retry once — do NOT fall through to precision retry.
                if not resp.get("success") and resp.get("code") == 510:
                    self._log(f"⏳ Order rate-limited (510) — waiting 3s then retrying once", AMBER)
                    time.sleep(3)
                    resp = mexc_private("POST", "/api/v1/private/order/submit",
                                        {"symbol": sym, "price": 0, "vol": vol,
                                         "side": side, "type": 5,
                                         "openType": 1, "leverage": lev},
                                        ak, asc, dry)
                if resp.get("success"):
                    oid = str(resp.get("data", oid))
                    self._log(f"Order accepted: {oid}", GREEN)
                else:
                    code = resp.get("code", "?")
                    msg  = resp.get("message", resp.get("msg", str(resp)))
                    if code == 2015:
                        # First retry: reduce decimal precision (handles rounding issues)
                        cur_prec = _learned_precision.get(sym, PAIR_VOL_PRECISION.get(sym, 2))
                        new_prec = max(0, cur_prec - 1)
                        _learned_precision[sym] = new_prec
                        vol2 = round_vol(sym, mg * lev)
                        self._log_event(f"Precision retry: {sym} {cur_prec}dp \u2192 {new_prec}dp  vol={vol2}", AMBER)
                        time.sleep(2)  # avoid 510 rate-limit cascade after limit+market attempts
                        resp2 = mexc_private("POST", "/api/v1/private/order/submit",
                                            {"symbol": sym, "price": 0, "vol": vol2,
                                             "side": side, "type": 5,
                                             "openType": 1, "leverage": lev},
                                            ak, asc, dry)
                        if resp2.get("success"):
                            oid = str(resp2.get("data", oid))
                            self._log(f"Order accepted on retry: {oid}", GREEN)
                        else:
                            code2 = resp2.get("code","?")
                            msg2  = resp2.get("message", resp2.get("msg", str(resp2)))
                            # Second retry: USDT notional rejected — try integer contract count.
                            # Some pairs (e.g. DOGE, TRX, XRP) may require contracts not USDT.
                            # vol = floor(margin * leverage / (price * contract_size))
                            if code2 == 2015:
                                cs   = PAIR_CONTRACT_SIZE.get(sym, 1.0)
                                px_  = self.current_prices.get(sym, 0)
                                if cs > 0 and px_ > 0:
                                    raw_contracts = (mg * lev) / (px_ * cs)
                                    vol3 = int(raw_contracts)  # floor to whole contracts
                                    if vol3 >= 1:
                                        self._log_event(
                                            f"Contract-count retry: {sym} "
                                            f"vol={vol3} contracts "
                                            f"({mg*lev:.2f} USDT / {px_:.4f} / cs={cs})", AMBER)
                                        resp3 = mexc_private(
                                            "POST", "/api/v1/private/order/submit",
                                            {"symbol": sym, "price": 0, "vol": vol3,
                                             "side": side, "type": 5,
                                             "openType": 1, "leverage": lev},
                                            ak, asc, dry)
                                        if resp3.get("success"):
                                            oid = str(resp3.get("data", oid))
                                            self._log(f"Order accepted (contract-count): {oid}", GREEN)
                                            # Remember this pair needs contract-count vol
                                            _learned_precision[sym] = -1  # sentinel: use contracts
                                        else:
                                            code3 = resp3.get("code","?")
                                            msg3  = resp3.get("message", resp3.get("msg", str(resp3)))
                                            self._log(f"Order REJECTED again: code={code3} msg={msg3}", RED)
                                            return None
                                    else:
                                        self._log(f"Order REJECTED again: code={code2} msg={msg2}", RED)
                                        return None
                                else:
                                    self._log(f"Order REJECTED again: code={code2} msg={msg2}", RED)
                                    return None
                            elif code2 == 510:
                                # Rate-limited on the precision retry — wait and try once more
                                self._log(f"⏳ Precision-retry rate-limited (510) — waiting 3s, retrying once", AMBER)
                                time.sleep(3)
                                resp2b = mexc_private("POST", "/api/v1/private/order/submit",
                                                      {"symbol": sym, "price": 0, "vol": vol2,
                                                       "side": side, "type": 5,
                                                       "openType": 1, "leverage": lev},
                                                      ak, asc, dry)
                                if resp2b.get("success"):
                                    oid = str(resp2b.get("data", oid))
                                    self._log(f"Order accepted on 510-retry: {oid}", GREEN)
                                else:
                                    code2b = resp2b.get("code","?")
                                    msg2b  = resp2b.get("message", resp2b.get("msg", str(resp2b)))
                                    self._log(f"Order REJECTED again: code={code2b} msg={msg2b}", RED)
                                    return None
                            else:
                                self._log(f"Order REJECTED again: code={code2} msg={msg2}", RED)
                                return None
                    elif code == 510:
                        self._log(f"Order REJECTED (still rate-limited after retry): {msg}", RED)
                        return None
                    else:
                        self._log(f"Order REJECTED: code={code} msg={msg}", RED)
                        self._log(f"  vol={vol} sym={sym} side={side}", RED)
                        return None
              except Exception as e:
                self._log(f"Order exception: {e}", RED)
                return None

        pid = str(uuid.uuid4())[:8]
        pos = Position(id=pid, symbol=sym, direction=direction,
                       entry_price=px, margin=mg, leverage=lev,
                       size_usdt=mg * lev, stop_loss=SL,
                       take_profit=TP, liq_price=LIQ,
                       opened_at=datetime.now(timezone.utc).isoformat(),
                       hedge_of=hedge_of, order_id=oid,
                       open_fee_type=open_fee_type)
        with self._positions_lock:
            self.state.positions[pid] = pos
        # Place TP/SL as server-side plan orders on MEXC (protects position
        # even if bot disconnects). Runs in background to avoid blocking.
        if not dry:
            threading.Thread(
                target=self._place_mexc_tpsl,
                args=(pos, ak, asc),
                daemon=True
            ).start()
        # Persist open orders for crash recovery
        self._persist_orders()
        # Deduct margin + open-leg fee from paper balance on open
        open_fee_rate = self._fee_maker if open_fee_type == "maker" else self._fee_taker
        open_fee_cost = round(pos.size_usdt * open_fee_rate, 6)
        if dry:
            self.state.balance = round(self.state.balance - mg - open_fee_cost, 4)
        self._log(
            f"Open fee ({open_fee_type}): ${open_fee_cost:.4f}  "
            f"({open_fee_rate*100:.3f}% × ${pos.size_usdt:.2f} notional)",
            DIM)
        # Start Claude monitor for every position (including hedges)
        ck = self.claude_entry.get().strip() if self.claude_enabled.get() else ""
        if ck and self.claude_enabled.get():
            threading.Thread(target=self._claude_position_monitor,
                             args=(pid,), daemon=True).start()
        return pid

    def _place_mexc_tpsl(self, pos, ak, asc):
        """
        Place TP/SL on MEXC using the position-based stop order endpoint.
        POST /api/v1/private/stoporder/place
        positionId is the MEXC internal long ID from open_positions (field: positionId).
        vol must equal holdVol (the actual contract count from the position).
        """
        if self.dry_var.get():
            self._log(f"TP/SL skipped — paper mode (switch to Live Trading to place on MEXC)", DIM)
            return

        pos_id   = getattr(pos, "exchange_pos_id", "")
        hold_vol = getattr(pos, "exchange_hold_vol", None)

        # Always fetch fresh holdVol + frozenVol — cached values go stale between calls
        try:
            r = mexc_private("GET", "/api/v1/private/position/open_positions",
                             {}, ak, asc, False)
            raw_list = r.get("data", [])
            if isinstance(raw_list, dict):
                raw_list = raw_list.get("list", raw_list.get("data", []))
            for p in raw_list:
                sym_p = p.get("symbol", "")
                pt    = int(p.get("positionType", 0))
                dir_p = "LONG" if pt == 1 else "SHORT"
                if sym_p == pos.symbol and dir_p == pos.direction:
                    pos_id     = str(p.get("positionId", ""))
                    hold_vol   = float(p.get("holdVol", 0))
                    frozen_vol = float(p.get("frozenVol", 0))
                    close_vol  = float(p.get("closeVol", 0))
                    pos.exchange_pos_id     = pos_id
                    pos.exchange_hold_vol   = hold_vol
                    pos.exchange_frozen_vol = frozen_vol
                    pos.exchange_close_vol  = close_vol
                    self._log(
                        f"Position data: {pos.symbol} positionId={pos_id} "
                        f"holdVol={hold_vol} frozenVol={frozen_vol} closeVol={close_vol}", DIM)
                    break
        except Exception as e:
            self._log(f"⚠ Could not fetch position data for {pos.symbol}: {e}", AMBER)

        if not pos_id:
            self._log(f"⚠ MEXC TP/SL skipped — no positionId for {pos.symbol} {pos.direction}", RED)
            return

        # Closable vol = holdVol - frozenVol - closeVol
        frozen_vol = getattr(pos, "exchange_frozen_vol", 0.0) or 0.0
        close_vol  = getattr(pos, "exchange_close_vol",  0.0) or 0.0
        if hold_vol:
            closable = max(0.0, hold_vol - frozen_vol - close_vol)
            if closable <= 0:
                self._log(
                    f"✓ TP/SL already fully set on MEXC for {pos.symbol} "
                    f"(holdVol={hold_vol} frozenVol={frozen_vol} closeVol={close_vol})", DIM)
                return
            vol = closable
        else:
            # Fallback: compute integer contracts from position USDT size
            cs_  = PAIR_CONTRACT_SIZE.get(pos.symbol, 1.0)
            px__ = self.current_prices.get(pos.symbol, pos.entry_price)
            vol  = max(1, int(pos.size_usdt / (px__ * cs_))) if cs_ > 0 and px__ > 0 else 1

        payload = {
            "positionId":      int(pos_id),
            "vol":             vol,
            "volType":         2,   # 2=position TP/SL (cover whole remaining position)
            "takeProfitPrice": round_price(pos.symbol, pos.take_profit),
            "stopLossPrice":   round_price(pos.symbol, pos.stop_loss),
            "profitTrend":     1,   # 1=latest price, 2=fair price, 3=index price
            "lossTrend":       1,   # 1=latest price, 2=fair price, 3=index price
            "takeProfitType":  0,   # 0=market TP (docs require takeProfitOrderPrice for type=1)
            "stopLossType":    0,   # 0=market SL
        }
        self._log(f"Placing MEXC TP/SL stoporder: {payload}", DIM)
        tpsl_ids = []
        try:
            resp = mexc_private("POST", "/api/v1/private/stoporder/place",
                                payload, ak, asc, False)
            self._log(f"MEXC TP/SL stoporder response: {resp}", DIM)
            if resp.get("success"):
                orders = resp.get("data", [])
                if isinstance(orders, list):
                    tpsl_ids = [str(o.get("id", "")) for o in orders if o.get("id")]
                else:
                    tpsl_ids = [str(orders)] if orders else []
                pos.tpsl_plan_ids = tpsl_ids
                self._log(
                    f"✓ MEXC TP ${pos.take_profit:,.4f} / SL ${pos.stop_loss:,.4f} set "
                    f"for {pos.symbol} [{', '.join(tpsl_ids)}]", GREEN)
            else:
                err_code = resp.get("code", resp.get("errorCode", "?"))
                err_msg  = resp.get("message", resp.get("msg", str(resp)))
                if str(err_code) == "5005":
                    # "already a position TP/SL order" — MEXC already has orders, nothing to do
                    self._log(
                        f"ℹ TP/SL already exists on MEXC for {pos.symbol} — skipping (code 5005)",
                        DIM)
                else:
                    self._log(
                        f"⚠ MEXC TP/SL REJECTED — "
                        f"code={err_code} "
                        f"msg={err_msg}", RED)
        except Exception as e:
            self._log(f"⚠ MEXC TP/SL exception: {e}", RED)

        # Store plan order IDs on the position so we can cancel them on close
        if tpsl_ids:
            pos.tpsl_plan_ids = tpsl_ids

    def _cancel_mexc_tpsl(self, pos, ak, asc):
        """
        Cancel outstanding MEXC TP/SL stop orders for this position.
        POST /api/v1/private/stoporder/cancel
        Body must be a JSON list: [{"stopPlanOrderId": id}, ...]
        """
        if self.dry_var.get():
            return
        plan_ids = getattr(pos, "tpsl_plan_ids", [])
        if not plan_ids:
            return
        try:
            body = [{"stopPlanOrderId": int(oid)} for oid in plan_ids if oid]
            if not body:
                return
            resp = mexc_private("POST", "/api/v1/private/stoporder/cancel",
                                body, ak, asc, False)
            if resp.get("success"):
                self._log(f"✓ Cancelled MEXC TP/SL orders {plan_ids}", DIM)
            else:
                self._log(
                    f"ℹ MEXC TP/SL cancel: "
                    f"{resp.get('message', resp.get('msg', str(resp)))}", DIM)
        except Exception as e:
            self._log(f"⚠ MEXC TP/SL cancel exception: {e}", AMBER)

    def _update_sl_on_mexc(self, pos, ak, asc):
        """
        Update the SL (and keep the TP) on MEXC by re-placing via _place_mexc_tpsl,
        then cancelling the old orders. Place-before-cancel avoids the "Balance
        insufficient" error caused by MEXC releasing margin from the old order
        only after the new one is placed — if we cancel first, there is a window
        where no stop order exists and the margin is temporarily unavailable.
        """
        if self.dry_var.get():
            return
        # Guard: don't update SL for a position that's already closed.
        with self._positions_lock:
            if pos.id not in self.state.positions:
                return
        # Place new TP/SL first, then cancel old ones
        self._place_mexc_tpsl(pos, ak, asc)
        self._cancel_mexc_tpsl(pos, ak, asc)
        self._log_event(f"↕ MEXC SL synced → ${pos.stop_loss:,.4f}", CYAN)

    def _write_trade_csv(self, pos, status, pnl, exit_price, r_multiple=None):
        """Append a closed/partial trade to this session's CSV for A/B analysis.
        Pure observability — failures here must never affect trading."""
        try:
            row = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pair": pos.symbol,
                "dir": pos.direction,
                "lev": pos.leverage,
                "entry": pos.entry_price,
                "exit": exit_price,
                "size_usdt": pos.size_usdt,
                "pnl_usd": pnl,
                "pnl_pct": round((pnl / pos.margin) * 100, 4) if pos.margin else 0,
                "r_multiple": r_multiple if r_multiple is not None else "",
                "exit_reason": status,
                "selective_entry_on": (self._tuned_entry_var.get()
                                       if hasattr(self, "_tuned_entry_var") else ""),
                "threshold_floor": TUNED_THRESHOLD_FLOOR,
            }
            is_new = self._session_csv_header_written is False
            with open(self._session_csv_path, "a", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(row.keys()))
                if is_new:
                    w.writeheader()
                    self._session_csv_header_written = True
                w.writerow(row)
        except Exception:
            pass

    def _partial_take_profit(self, pos, px, dry, ak, asc):
        """v2.8-TUNED: close a fraction of `pos` at the current price to bank
        profit partway to TP, then move the stop to breakeven. Fires once per
        position (guarded by a per-pid flag). Safe in both paper and live mode.

        State accounting mirrors a full close, scaled by the closed fraction:
          • realise PnL on the closed fraction (net of round-trip fees)
          • credit balance + record a 'PARTIAL TP' trade-history row
          • shrink the live position (margin / size_usdt / exchange_hold_vol)
            by the same fraction so the remaining position tracks correctly
          • move SL to breakeven so the runner can't become a loss
        """
        pid = pos.id
        guard = f"_partial_tp_{pid}"
        if getattr(self, guard, False):
            return
        frac = TUNED_PARTIAL_TP_FRACTION
        if frac <= 0 or frac >= 1:
            return
        d = pos.direction

        # Only take partial profit when actually in profit at px
        raw = ((px - pos.entry_price) / pos.entry_price if d == "LONG"
               else (pos.entry_price - px) / pos.entry_price)
        if raw <= 0:
            return

        setattr(self, guard, True)   # set before any I/O so it can't double-fire

        close_size   = pos.size_usdt * frac
        close_margin = pos.margin * frac
        gross_pnl    = raw * pos.leverage * close_margin
        open_fee_rate  = (self._fee_maker if getattr(pos, "open_fee_type", "taker") == "maker"
                          else self._fee_taker)
        close_fee_rate = self._fee_taker
        fee = close_size * (open_fee_rate + close_fee_rate)
        pnl = round(gross_pnl - fee, 4)

        # ── Live: send a reduce-only market order for the closed fraction ──────
        if not dry:
            side = 4 if d == "LONG" else 2   # 4=close long, 2=close short
            cs   = PAIR_CONTRACT_SIZE.get(pos.symbol, 1.0)
            exch_vol = getattr(pos, "exchange_hold_vol", 0.0) or 0.0
            if exch_vol > 0:
                vol = int(round(exch_vol * frac))
            elif cs > 0 and px > 0:
                vol = max(1, int((pos.size_usdt * frac) / (px * cs)))
            else:
                vol = 0
            if vol <= 0:
                self._log_event(f"⚠ Partial TP skipped — vol=0 for {pos.symbol}", AMBER)
                return
            try:
                resp = mexc_private("POST", "/api/v1/private/order/submit",
                                    {"symbol": pos.symbol, "price": 0, "vol": vol,
                                     "side": side, "type": 5, "openType": 1},
                                    ak, asc, dry)
                if not (resp and resp.get("success")):
                    self._log_event(
                        f"⚠ Partial TP order rejected ({pos.symbol}): "
                        f"{resp.get('message', resp) if resp else 'no response'} "
                        f"— leaving full position open", AMBER)
                    return
            except Exception as e:
                self._log_event(f"⚠ Partial TP exception ({pos.symbol}): {e}", AMBER)
                return
            # Shrink tracked exchange contract count by the closed fraction
            if exch_vol > 0:
                pos.exchange_hold_vol = max(0.0, exch_vol - vol)

        # ── Book the realised partial PnL (paper + live) ─────────────────────
        self.state.total_pnl = round(self.state.total_pnl + pnl, 4)
        if dry:
            # Paper: return the freed margin + its share of PnL to balance
            self.state.balance = round(self.state.balance + close_margin + pnl, 4)
        else:
            self.state.balance = round(self.state.balance + pnl, 4)

        self.state.trades.append({
            "symbol": pos.symbol, "direction": d,
            "entry_price": pos.entry_price, "exit_price": px,
            "margin": round(close_margin, 4), "leverage": pos.leverage,
            "pnl_usdt": pnl, "status": "PARTIAL TP", "hedge": bool(pos.hedge_of),
            "opened_at": pos.opened_at,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        })
        self._write_trade_csv(pos, "PARTIAL TP", pnl, px)

        # ── Shrink the live position to the remaining fraction ───────────────
        pos.margin    = round(pos.margin * (1 - frac), 6)
        pos.size_usdt = round(pos.size_usdt * (1 - frac), 6)

        # ── Move SL to breakeven so the runner can't turn into a loss ────────
        fee_buffer = pos.entry_price * 0.0025
        if d == "LONG":
            be = pos.entry_price + fee_buffer
            if be > pos.stop_loss:
                pos.stop_loss = round_price(pos.symbol, be)
        else:
            be = pos.entry_price - fee_buffer
            if be < pos.stop_loss:
                pos.stop_loss = round_price(pos.symbol, be)
        setattr(self, f"_be_lock_{pid}", True)   # don't let Tier-1 fire again

        self._log_event(
            f"💰 Partial TP {pair_label(pos.symbol)} {d}: closed {frac*100:.0f}% "
            f"@ ${px:,.4f}  PnL ${pnl:+.2f}  → SL to breakeven ${pos.stop_loss:,.4f}",
            GREEN)
        self._refresh_metrics(); self._save()
        self.root.after(0, self._refresh_trades_tab)
        if not dry:
            threading.Thread(target=self._update_sl_on_mexc,
                             args=(pos, ak, asc), daemon=True).start()

    def _market_close_position(self, pos, ak, asc, px=None, force_close=False):
        if px is None:
            px = self.current_prices.get(pos.symbol, pos.entry_price)
        """
        FIX v2.2-#2: Immediately close a position with a market order.
        Used by AI CLOSE and AI TAKE paths because MEXC SL stop orders only
        trigger when price reaches the stop level — they do not close immediately.
        This fires a market reduce-only order to guarantee the position exits.

        force_close=True: skip the htp/hsl/hliq price gate and always record the
        trade + remove from state. Used by AI CLOSE / AI TAKE paths where the
        market order has already been sent intentionally — the gate check is
        irrelevant and would silently drop the trade from history if price moved
        a tick between the thread spawn and execution.

        FIX v2.7: Was using raw urllib to a hardcoded /order/create endpoint
        with manually constructed auth — caused HTTP 403 Forbidden on all pairs.
        Now uses mexc_private() with /order/submit (same as all other orders),
        which handles symbol remapping, correct HMAC signing, and retries.
        side 3 = close LONG (sell), side 4 = close SHORT (buy), type 5 = market,
        openType 2 = close/reduce-only.

        FIX v2.7.4: Gate check moved to BEFORE the market order. Previously the
        market order was sent unconditionally on every scan cycle for every open
        position, causing MEXC to return "Balance insufficient" (position not at
        SL/TP yet) every 30s per position — spamming the log and causing UI lag
        from the extra API round-trips. Now the hsl/htp/hliq check runs first and
        the market order only fires when actually needed (or force_close=True).
        """
        # ── Early gate: only send market order if SL/TP/liq is actually hit ──
        # (force_close bypasses this — used by AI CLOSE / AI TAKE paths)
        d = pos.direction
        htp  = (px >= pos.take_profit) if d == "LONG" else (px <= pos.take_profit)
        hsl  = (px <= pos.stop_loss)   if d == "LONG" else (px >= pos.stop_loss)
        hliq = (px <= pos.liq_price)   if d == "LONG" else (px >= pos.liq_price)
        if not force_close and not (htp or hsl or hliq):
            # Price hasn't hit any exit level — run trailing/monitor logic only,
            # skip the market order entirely.
            pass  # falls through to trailing-stop block below
        elif self.dry_var.get():
            self._log_event(f"[DRY] Market close skipped for {pos.symbol}", DIM)
            # Fall through — trailing-stop / SL/TP monitor still runs in dry mode
        else:
            try:
                # side 3 = close LONG (open side was 1=buy, close is 3=sell)
                # side 4 = close SHORT (open side was 2=sell, close is 4=buy)
                side = 3 if pos.direction == "LONG" else 4
                _cs  = PAIR_CONTRACT_SIZE.get(pos.symbol, 1.0)
                _px  = self.current_prices.get(pos.symbol, pos.entry_price)
                _hv  = getattr(pos, "exchange_hold_vol", 0.0) or 0.0
                if _hv > 0:
                    vol = round(_hv, 4)
                elif _cs > 0 and _px > 0:
                    vol = round(pos.size_usdt / (_px * _cs), 4)
                else:
                    vol = round(pos.margin * pos.leverage, 4)
                vol = max(vol, 0.0001)
                resp = mexc_private(
                    "POST", "/api/v1/private/order/submit",
                    {"symbol": pos.symbol, "price": 0, "vol": vol,
                     "side": side, "type": 5, "openType": 2},
                    ak, asc, False)
                # Retry once on rate-limit (code 510)
                if not resp.get("success") and resp.get("code") == 510:
                    self._log_event("⏳ Market close rate-limited (510) — retrying in 3s", AMBER)
                    time.sleep(3)
                    resp = mexc_private(
                        "POST", "/api/v1/private/order/submit",
                        {"symbol": pos.symbol, "price": 0, "vol": vol,
                         "side": side, "type": 5, "openType": 2},
                        ak, asc, False)
                if resp.get("success"):
                    self._log_event(
                        f"✅ Market close sent for {pos.symbol} {pos.direction} vol={vol}", GREEN)
                else:
                    self._log_event(
                        f"⚠ Market close rejected: {resp.get('message', resp)}", AMBER)
            except Exception as e:
                self._log_event(f"⚠ Market close exception ({pos.symbol}): {e}", AMBER)


        dry = self.dry_var.get()

        # ── Trailing stop: dynamic, ATR-scaled, with breakeven lock ──────────
        #
        # Three tiers:
        #
        #  1. BREAKEVEN LOCK  (≥30% of TP distance)
        #     Move SL to entry + fee buffer the moment the trade is clearly
        #     profitable. Prevents a winning trade from turning into a loss on
        #     a sudden reversal. Fires once per position.
        #
        #  2. STANDARD TRAIL  (≥60% of SL distance in profit)
        #     ATR-scaled gap: gap = ATR_price × ATR_TRAIL_MULT, clamped so it
        #     never exceeds the original SL distance (no looser than entry SL)
        #     and never goes below 30% of original SL (no nonsensically tight
        #     stops on ultra-low-ATR pairs).
        #     Tightens further to 50% of gap once profit_dist ≥ sl_dist.
        #
        #  3. FAST-SPIKE TRAIL  (≥90% of TP distance OR ≥2% margin gain/candle)
        #     Bypass the normal gap calculation entirely and trail at 25% of
        #     original SL distance. High-volatility moves can cover the entire
        #     TP range in 2-3 candles — this locks in most of the profit without
        #     waiting for the standard trail to catch up.

        sl_dist    = abs(pos.entry_price - pos.stop_loss)   # original SL distance
        tp_total   = abs(pos.take_profit - pos.entry_price) # total TP distance
        tp_progress = ((px - pos.entry_price) / tp_total
                       if d == "LONG" else
                       (pos.entry_price - px) / tp_total) if tp_total > 0 else 0

        # Live ATR in price units for this pair
        _sym_atr_pct = self.pair_signals.get(pos.symbol, {}).get("atr_pct",
                       PAIR_ATR_MIN.get(pos.symbol, 0.06))
        _atr_price   = pos.entry_price * (_sym_atr_pct / 100.0)
        ATR_TRAIL_MULT = 1.5   # trail gap = 1.5 × ATR — wide enough to breathe, tight enough to protect

        # ── v2.8-TUNED Tier 0 — Partial take-profit + breakeven ───────────────
        # Bank part of the position partway to TP and move the stop to breakeven,
        # so a trade that moves your way locks in real profit instead of round-
        # tripping back to the stop. Fires once per position, only for primary
        # (non-hedge) positions, and never in the force_close path.
        if (TUNED_PARTIAL_TP_ENABLE and not force_close and not pos.hedge_of
                and tp_progress >= TUNED_PARTIAL_TP_PROGRESS):
            self._partial_take_profit(pos, px, dry, ak, asc)

        # Tier 1 — Breakeven lock (fires once at 30% TP progress)
        _be_key = f"_be_lock_{pos.id}"
        if tp_progress >= 0.30 and not getattr(self, _be_key, False):
            setattr(self, _be_key, True)
            fee_buffer = pos.entry_price * 0.0025   # cover round-trip fee
            if d == "LONG":
                new_be_sl = pos.entry_price + fee_buffer
                if new_be_sl > pos.stop_loss:
                    pos.stop_loss = round_price(pos.symbol, new_be_sl)
                    self._log_event(
                        f"🔒 Breakeven lock {pair_label(pos.symbol)}: "
                        f"SL → ${pos.stop_loss:,.4f}  ({tp_progress*100:.0f}% to TP)", CYAN)
                    if not dry:
                        threading.Thread(target=self._update_sl_on_mexc,
                                         args=(pos, ak, asc), daemon=True).start()
            else:
                new_be_sl = pos.entry_price - fee_buffer
                if new_be_sl < pos.stop_loss:
                    pos.stop_loss = round_price(pos.symbol, new_be_sl)
                    self._log_event(
                        f"🔒 Breakeven lock {pair_label(pos.symbol)}: "
                        f"SL → ${pos.stop_loss:,.4f}  ({tp_progress*100:.0f}% to TP)", CYAN)
                    if not dry:
                        threading.Thread(target=self._update_sl_on_mexc,
                                         args=(pos, ak, asc), daemon=True).start()

        # Compute ATR-scaled gap (shared by Tier 2 and 3)
        _atr_gap = _atr_price * ATR_TRAIL_MULT
        _atr_gap = max(_atr_gap, sl_dist * 0.30)   # floor: never tighter than 30% of original SL
        _atr_gap = min(_atr_gap, sl_dist)           # ceiling: never looser than original SL

        # Tier 3 — Fast-spike trail (deep in TP or rapid margin gain)
        _minutes_open = 0
        try:
            _opened = datetime.fromisoformat(pos.opened_at.replace("Z", "+00:00"))
            _minutes_open = (datetime.now(timezone.utc) - _opened).total_seconds() / 60
        except Exception:
            pass
        _margin_gain_pct = (abs(px - pos.entry_price) / pos.entry_price
                            * pos.leverage * 100)   # margin % gain
        _candles_open    = max(1, _minutes_open / 5)
        _gain_per_candle = _margin_gain_pct / _candles_open
        # Fast-spike: requires meaningful ATR (>0.05% — excludes indices/forex)
        # AND rapid margin gain (≥3% per candle). Low-ATR pairs like NAS100
        # (0.047% ATR) hitting 2% gain/candle is normal price action, not a spike.
        _fast_spike_atr_ok = _sym_atr_pct > 0.05
        # Fast-spike: price must move ≥3× normal ATR in a single candle period.
        # Using price% not margin% — at 50x even a 0.06% move = 3% margin gain,
        # which is normal, not a spike. 3×ATR means genuinely exceptional movement.
        _price_gain_pct_per_candle = (abs(px - pos.entry_price) / pos.entry_price * 100
                                      / _candles_open)
        _fast_spike      = _fast_spike_atr_ok and (tp_progress >= 0.90
                           or _price_gain_pct_per_candle >= _sym_atr_pct * 3.0)

        if _fast_spike:
            gap = sl_dist * 0.25   # very tight — 25% of original SL distance
        else:
            gap = _atr_gap

        if d == "LONG":
            profit_dist = px - pos.entry_price
            if profit_dist >= sl_dist * 0.6 or _fast_spike:
                if profit_dist >= sl_dist and not _fast_spike:
                    gap = gap * 0.5   # tighten further once fully past original SL distance
                new_trail_sl = px - gap
                if new_trail_sl > pos.stop_loss:
                    old_sl = pos.stop_loss
                    pos.stop_loss = round_price(pos.symbol, new_trail_sl)
                    _tag = "⚡ Fast-spike" if _fast_spike else "📈 Trail"
                    self._log_event(
                        f"{_tag} {pair_label(pos.symbol)}: "
                        f"SL ${old_sl:,.4f}→${pos.stop_loss:,.4f}  "
                        f"gap={gap/pos.entry_price*100:.3f}%  ATR={_sym_atr_pct:.3f}%", CYAN)
                    if not dry and pos.id in self.state.positions:
                        threading.Thread(target=self._update_sl_on_mexc,
                                         args=(pos, ak, asc), daemon=True).start()
        else:  # SHORT
            profit_dist = pos.entry_price - px
            if profit_dist >= sl_dist * 0.6 or _fast_spike:
                if profit_dist >= sl_dist and not _fast_spike:
                    gap = gap * 0.5
                new_trail_sl = px + gap
                if new_trail_sl < pos.stop_loss:
                    old_sl = pos.stop_loss
                    pos.stop_loss = round_price(pos.symbol, new_trail_sl)
                    _tag = "⚡ Fast-spike" if _fast_spike else "📈 Trail"
                    self._log_event(
                        f"{_tag} {pair_label(pos.symbol)}: "
                        f"SL ${old_sl:,.4f}→${pos.stop_loss:,.4f}  "
                        f"gap={gap/pos.entry_price*100:.3f}%  ATR={_sym_atr_pct:.3f}%", CYAN)
                    if not dry and pos.id in self.state.positions:
                        threading.Thread(target=self._update_sl_on_mexc,
                                         args=(pos, ak, asc), daemon=True).start()

        # htp/hsl/hliq already computed at top of function (early gate).
        # If we reached here without force_close, at least one is True.
        if not force_close and not (htp or hsl or hliq): return False, None, 0

        if hliq:
            pnl = -pos.margin; status = "LIQUIDATED"; ep = pos.liq_price
            self.state.liqs += 1
        else:
            raw = (px - pos.entry_price) / pos.entry_price if d == "LONG" \
                  else (pos.entry_price - px) / pos.entry_price
            gross_pnl = raw * pos.leverage * pos.margin
            # Open leg fee depends on whether it was filled as maker or taker
            open_fee_rate  = self._fee_maker if getattr(pos, "open_fee_type", "taker") == "maker" \
                             else self._fee_taker
            close_fee_rate = self._fee_taker   # close is always market (taker)
            fee = pos.size_usdt * (open_fee_rate + close_fee_rate)
            pnl = round(gross_pnl - fee, 4); ep = px
            status = "WIN" if pnl >= 0 else "LOSS"
            if pnl >= 0: self.state.wins   += 1
            else:        self.state.losses += 1

        if not dry:
            side = 4 if d == "LONG" else 2
            cs   = PAIR_CONTRACT_SIZE.get(pos.symbol, 1.0)
            # ── Use actual exchange holdVol when available (synced positions).
            # Calculating from size_usdt/entry_price can give wrong vol if the
            # position was synced at a different price or with a different margin.
            exch_vol = getattr(pos, "exchange_hold_vol", 0.0) or 0.0
            if exch_vol > 0:
                vol = int(round(exch_vol))  # exchange holdVol is already integer contracts
            else:
                # Fallback: compute integer contracts from position USDT size
                cs_  = PAIR_CONTRACT_SIZE.get(pos.symbol, 1.0)
                px__ = self.current_prices.get(pos.symbol, pos.entry_price)
                vol  = max(1, int(pos.size_usdt / (px__ * cs_))) if cs_ > 0 and px__ > 0 else 1
            if vol <= 0:
                self._log_event(f"⛔ Close order aborted — vol=0 for {pos.symbol} "
                          f"(size_usdt={pos.size_usdt:.4f} entry={pos.entry_price:.4f} "
                          f"exchange_hold_vol={exch_vol})", RED)
                return False, None, 0
            close_ok = False
            try:
                resp = mexc_private("POST", "/api/v1/private/order/submit",
                                    {"symbol": pos.symbol, "price": 0, "vol": vol,
                                     "side": side, "type": 5, "openType": 1},
                                    ak, asc, dry)
                if resp and resp.get("success"):
                    close_ok = True
                    self._log_event(f"✓ Close order sent: {pos.symbol} {d} vol={vol} "
                              f"orderId={resp.get('data','?')}", DIM)
                else:
                    err_code = resp.get("code", "?") if resp else "no response"
                    err_msg  = resp.get("message", resp.get("msg", "")) if resp else ""
                    self._log(f"⚠ Close order REJECTED [{err_code}] {pos.symbol} {d} "
                              f"vol={vol}: {err_msg}", RED)
                    # Retry once with holdVol fetched fresh from exchange
                    try:
                        r2 = mexc_private("GET", "/api/v1/private/position/open_positions",
                                          {}, ak, asc, False)
                        raw2 = r2.get("data", [])
                        if isinstance(raw2, dict):
                            raw2 = raw2.get("list", raw2.get("data", []))
                        for ep2 in raw2:
                            pt2  = int(ep2.get("positionType", 0))
                            dir2 = "LONG" if pt2 == 1 else "SHORT"
                            if ep2.get("symbol") == pos.symbol and dir2 == d:
                                fresh_vol = float(ep2.get("holdVol", 0))
                                if fresh_vol > 0:
                                    vol2 = round_vol(pos.symbol, fresh_vol)
                                    resp2 = mexc_private(
                                        "POST", "/api/v1/private/order/submit",
                                        {"symbol": pos.symbol, "price": 0, "vol": vol2,
                                         "side": side, "type": 5, "openType": 1},
                                        ak, asc, dry)
                                    if resp2 and resp2.get("success"):
                                        close_ok = True
                                        self._log_event(f"✓ Close order retry OK: {pos.symbol} "
                                                  f"vol={vol2} → {resp2.get('data','?')}", CYAN)
                                    else:
                                        self._log_event(f"⛔ Close order retry also FAILED: "
                                                  f"{pos.symbol} vol={vol2} → "
                                                  f"{resp2.get('message', resp2.get('msg','?')) if resp2 else 'no response'}", RED)
                                break
                    except Exception as retry_err:
                        self._log_event(f"⛔ Close order retry error: {retry_err}", RED)
            except Exception as exc:
                self._log_event(f"⛔ Close order exception: {pos.symbol} {d}: {exc}", RED)

            if not close_ok:
                # Do NOT remove from bot state — position is still open on exchange.
                # Log clearly so the user knows to act manually.
                self._log_event(f"⛔ POSITION NOT CLOSED ON MEXC — {pos.symbol} {d} still open! "
                          f"Close manually on MEXC or click Close in the bot.", RED)
                return False, None, 0

            # Cancel any outstanding MEXC plan (TP/SL) orders for this position
            # so they don't fire after the bot has already closed the trade.
            threading.Thread(
                target=self._cancel_mexc_tpsl,
                args=(pos, ak, asc),
                daemon=True
            ).start()

        self.state.total_pnl  = round(self.state.total_pnl + pnl, 4)
        # Return margin + pnl to balance.
        # In paper mode: margin was deducted at open (open fee already deducted separately).
        # pnl is already net of open+close fees.
        # In live mode: MEXC handles balance; we track pnl for display only.
        if self.dry_var.get():
            self.state.balance = round(self.state.balance + pos.margin + pnl, 4)
        else:
            self.state.balance = round(self.state.balance + pnl, 4)
        _status_label = f"{status} (AI close)" if force_close else status
        self.state.trades.append({
            "symbol": pos.symbol, "direction": d,
            "entry_price": pos.entry_price, "exit_price": ep,
            "margin": pos.margin, "leverage": pos.leverage,
            "pnl_usdt": pnl, "status": _status_label, "hedge": bool(pos.hedge_of),
            "opened_at": pos.opened_at,
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "open_fee_type": getattr(pos, "open_fee_type", "taker"),
            "open_fee_rate": open_fee_rate,
            "close_fee_rate": close_fee_rate,
            "total_fee_usdt": round(fee, 6)})
        try:
            _risk = abs(pos.entry_price - pos.stop_loss)
            _r_mult = round(((ep - pos.entry_price) if d == "LONG" else (pos.entry_price - ep))
                            / _risk, 3) if _risk else None
        except Exception:
            _r_mult = None
        self._write_trade_csv(pos, _status_label, pnl, ep, _r_mult)

        # ── Adaptive engine: log trade outcome ───────────────────────────────
        self._adaptive_engine.log_trade(pnl >= 0)

        # ── Kelly sizing: update running win/loss stats ───────────────────────
        if not hliq and status in ("WIN", "LOSS"):
            alpha = 0.15   # exponential moving average weight — reacts to last ~7 trades
            if pnl >= 0:
                self._kelly_wins += 1
                self._kelly_avg_win = (alpha * abs(pnl)
                                       + (1 - alpha) * self._kelly_avg_win) \
                                       if self._kelly_avg_win > 0 else abs(pnl)
                # #PAIR-LOG: per-pair win tracking
                self.state.pair_wins[pos.symbol] = self.state.pair_wins.get(pos.symbol, 0) + 1
            else:
                self._kelly_losses += 1
                self._kelly_avg_loss = (alpha * abs(pnl)
                                        + (1 - alpha) * self._kelly_avg_loss) \
                                        if self._kelly_avg_loss > 0 else abs(pnl)
                # #PAIR-LOG: per-pair loss tracking
                self.state.pair_losses[pos.symbol] = self.state.pair_losses.get(pos.symbol, 0) + 1
            # Log per-pair running win rate on each close
            pw = self.state.pair_wins.get(pos.symbol, 0)
            pl = self.state.pair_losses.get(pos.symbol, 0)
            tot = pw + pl
            wr_pct = pw / tot * 100 if tot > 0 else 0
            _file_logger.info(
                "[PAIR_WR] %s  W=%d L=%d WR=%.1f%% (session)",
                pos.symbol, pw, pl, wr_pct)

        # ── Pair cooldown + losing streak tracking ───────────────────────────
        if pnl < 0:
            self._pair_cooldown[pos.symbol] = time.time()
            self._losing_streak = getattr(self, "_losing_streak", 0) + 1
            # Reduce leverage after 3 consecutive losses
            if self._losing_streak == 3:
                try:
                    cur_lev = self._lev()
                    if self._peak_leverage is None:
                        self._peak_leverage = cur_lev
                    opts = self._lev_opts(self.pair_cb.get())
                    cur_idx = next((i for i,o in enumerate(opts) if o == f"{cur_lev}x"), -1)
                    if cur_idx > 0:
                        new_lev = opts[cur_idx - 1]
                        self.root.after(0, lambda l=new_lev: (
                            self.lev_cb.set(l), self._on_lev()))
                        self._log_event(f"⚠ 3 consecutive losses — leverage reduced to {new_lev}", AMBER)
                except Exception as _exc:
                    _file_logger.debug("suppressed error: %s", _exc)
        else:
            prev_streak = getattr(self, "_losing_streak", 0)
            self._losing_streak = 0
            # Restore leverage after 3 consecutive wins following a reduction
            if prev_streak == 0 and self._peak_leverage is not None:
                wins_since = sum(1 for t in self.state.trades[-3:] if t.get("pnl_usdt",0) >= 0)
                if wins_since >= 3:
                    try:
                        self.root.after(0, lambda l=f"{self._peak_leverage}x": (
                            self.lev_cb.set(l), self._on_lev()))
                        self._log_event(f"✓ 3 wins — leverage restored to {self._peak_leverage}x", GREEN)
                        self._peak_leverage = None
                    except Exception as _exc:
                        _file_logger.debug("suppressed error: %s", _exc)

        del self.state.positions[pos.id]
        self._persist_orders()
        self.root.after(0, self._refresh_trades_tab)
        self.root.after(0, self._refresh_metrics)
        return True, status, pnl

# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY
# ══════════════════════════════════════════════════════════════════════════════
def main():
    import subprocess, sys
    for pkg in ["anthropic", "matplotlib"]:
        try: __import__(pkg)
        except ImportError:
            print(f"Installing {pkg}…")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

    root = tk.Tk()
    try:
        from ctypes import windll, c_int, byref, sizeof
        windll.dwmapi.DwmSetWindowAttribute(
            windll.user32.GetParent(root.winfo_id()), 20, byref(c_int(1)), sizeof(c_int))
    except (ImportError, AttributeError, OSError) as e:
        _file_logger.debug(f"Window decoration setup failed (non-Windows or unsupported): {e}")

    app = HermesBotApp(root)

    def _close():
        if app.bot_running:
            if not messagebox.askyesno("Bot running", "Stop bot and exit?"): return
            app._stop()
        for t in [app._chart_timer, app._dock_timer]:
            if t: root.after_cancel(t)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _close)
    root.mainloop()

if __name__ == "__main__":
    main()







