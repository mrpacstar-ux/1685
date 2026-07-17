"""Tkinter GUI — a scanner-style app: connect once, then browse.

    python -m psadiag gui

Tabs: Fault codes (scan / clear selected / clear all), Live data
(mode-01 readings at ~1 Hz), ECU info (VIN and identification strings).
All bus traffic runs on one worker thread so the window never freezes
during the slow K-line inits; jobs are queued, results posted back.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .dtc import describe
from .elm327 import AdapterError, BusError, Elm327
from .kwp import NegativeResponse, strip_header
from .live import PIDS, read_ecu_info, read_pid, supported_pids
from .session import clear_dtcs, connect, read_dtcs
from .tune import check_tune


class ScannerSession:
    """One open diagnostic session, ELM327 or raw K-line, same interface."""

    def __init__(self, port: str | None, kkl: bool, status):
        self.kkl = kkl
        if kkl:
            from .kline import connect_kkl
            if not port:
                raise AdapterError("Raw K-line mode needs a port selected.")
            status("Raw K-line mode (KKL cable) ...")
            self.conn = connect_kkl(port, status=status)
            self.name = self.conn.describe()
        else:
            if port:
                self.elm = Elm327(port=port)
                self.elm.open()
            else:
                status("Looking for the USB interface ...")
                self.elm = Elm327.autodetect()
            status(f"Adapter: {self.elm.identity} on {self.elm.port}")
            self.conn = connect(self.elm, status=status)
            self.name = self.conn.describe()

    # -- uniform operations -------------------------------------------------

    def request(self, payload: bytes):
        if self.kkl:
            return self.conn.kline.request(payload)
        return self.elm.request(payload)

    def read(self, status):
        if self.kkl:
            return self.conn.read_dtcs(status=status)
        return read_dtcs(self.conn, status=status)

    def scan_systems(self, status):
        """Read codes from every known PSA module (ELM backend only).

        Returns a list of (Module, dtcs_or_None). None = no response, which
        on a pre-BSI car usually means the cable isn't on that pin.
        """
        from .modules import PSA_MODULES, get_module
        if self.kkl:
            return [(get_module("engine"), self.conn.read_dtcs(status=status))]
        results = []
        for module in PSA_MODULES:
            status(f"=== {module.name} (pin {module.pin}) ===")
            try:
                conn = connect(self.elm, targets=module.addresses, status=status)
            except BusError:
                status(f"  no response from {module.name}")
                results.append((module, None))
                continue
            results.append((module, read_dtcs(conn, status=status)))
        return results

    def clear_all(self, status) -> bool:
        if self.kkl:
            return self.conn.clear_dtcs(status=status)
        return clear_dtcs(self.conn, status=status)

    def clear_one(self, code: str, status) -> bool:
        """clearDiagnosticInformation for one specific DTC group.

        Not every ECU honours per-code clearing — the caller falls back to
        clear_all when this fails.
        """
        hi = {"P": 0x00, "C": 0x40, "B": 0x80, "U": 0xC0}[code[0]]
        hi |= (int(code[1]) & 0x03) << 4
        hi |= int(code[2], 16)
        lo = (int(code[3], 16) << 4) | int(code[4], 16)
        try:
            frames = self.request(bytes([0x14, hi, lo]))
        except BusError:
            return False
        for frame in frames:
            try:
                if strip_header(frame, 0x14):
                    status(f"  cleared {code}")
                    return True
            except NegativeResponse:
                return False
        return False

    def close(self):
        if self.kkl:
            self.conn.close()
        else:
            self.elm.close()


class App:
    POLL_MS = 100
    LIVE_MS = 1200

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("psa-diag — Peugeot diagnostic scanner")
        root.geometry("860x640")
        root.minsize(700, 500)

        self.msgq: queue.Queue = queue.Queue()
        self.jobq: queue.Queue = queue.Queue()
        self.session: ScannerSession | None = None
        self.live_on = False
        self.live_pids = list(PIDS)
        self.busy = False

        threading.Thread(target=self._worker, daemon=True).start()
        self._build_ui()
        self.refresh_ports()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        root.after(self.POLL_MS, self._poll)
        root.after(self.LIVE_MS, self._live_timer)

    # ------------------------------------------------------------------- UI

    def _build_ui(self):
        root = self.root
        bar = ttk.Frame(root, padding=8)
        bar.pack(fill="x")

        ttk.Label(bar, text="Port:").pack(side="left")
        self.port_var = tk.StringVar(value="(auto)")
        self.port_box = ttk.Combobox(bar, textvariable=self.port_var, width=16)
        self.port_box.pack(side="left", padx=(4, 6))
        ttk.Button(bar, text="↻", width=3,
                   command=self.refresh_ports).pack(side="left", padx=(0, 10))
        self.kkl_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Raw K-line (KKL cable)",
                        variable=self.kkl_var).pack(side="left", padx=(0, 12))
        self.connect_btn = ttk.Button(bar, text="Connect",
                                      command=self.on_connect)
        self.connect_btn.pack(side="left")
        self.conn_label = ttk.Label(bar, text="not connected",
                                    foreground="#777")
        self.conn_label.pack(side="left", padx=10)

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.notebook = nb

        # ---- Faults tab
        faults = ttk.Frame(nb, padding=6)
        nb.add(faults, text="  Fault codes  ")
        ftb = ttk.Frame(faults)
        ftb.pack(fill="x", pady=(0, 6))
        self.scan_btn = ttk.Button(ftb, text="Scan engine", command=self.on_scan)
        self.scan_btn.pack(side="left")
        self.scan_all_btn = ttk.Button(ftb, text="Scan all systems",
                                       command=self.on_scan_all)
        self.scan_all_btn.pack(side="left", padx=6)
        self.clear_sel_btn = ttk.Button(ftb, text="Clear selected",
                                        command=self.on_clear_selected)
        self.clear_sel_btn.pack(side="left", padx=6)
        self.clear_all_btn = ttk.Button(ftb, text="Clear all",
                                        command=self.on_clear_all)
        self.clear_all_btn.pack(side="left")
        ttk.Label(ftb, text="Engine ECU only — PSA puts ABS (pin 12) and "
                            "airbag (pin 13) on separate wires.",
                  foreground="#777").pack(side="right")

        cols = ("code", "description", "state")
        self.table = ttk.Treeview(faults, columns=cols, show="headings",
                                  selectmode="extended")
        for col, text, width, stretch in (
                ("code", "Code", 90, False),
                ("description", "Description", 520, True),
                ("state", "State", 140, False)):
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="w", stretch=stretch)
        self.table.tag_configure("active", foreground="#b00020")
        self.table.tag_configure("muted", foreground="#888")
        vsb = ttk.Scrollbar(faults, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=vsb.set)
        self.table.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # ---- Live data tab
        live = ttk.Frame(nb, padding=6)
        nb.add(live, text="  Live data  ")
        ltb = ttk.Frame(live)
        ltb.pack(fill="x", pady=(0, 6))
        self.live_btn = ttk.Button(ltb, text="Start", command=self.on_live)
        self.live_btn.pack(side="left")
        self.live_note = ttk.Label(ltb, text="", foreground="#777")
        self.live_note.pack(side="left", padx=10)
        self.live_table = ttk.Treeview(
            live, columns=("name", "value", "unit"), show="headings")
        for col, text, width, stretch in (
                ("name", "Reading", 320, True),
                ("value", "Value", 140, False),
                ("unit", "Unit", 100, False)):
            self.live_table.heading(col, text=text)
            self.live_table.column(col, width=width, anchor="w", stretch=stretch)
        lvs = ttk.Scrollbar(live, orient="vertical",
                            command=self.live_table.yview)
        self.live_table.configure(yscrollcommand=lvs.set)
        self.live_table.pack(side="left", fill="both", expand=True)
        lvs.pack(side="right", fill="y")
        for p in self.live_pids:
            self.live_table.insert("", "end", iid=f"pid{p.pid:02X}",
                                   values=(p.name, "—", p.unit))

        # ---- ECU info tab
        info = ttk.Frame(nb, padding=6)
        nb.add(info, text="  ECU info  ")
        itb = ttk.Frame(info)
        itb.pack(fill="x", pady=(0, 6))
        self.info_btn = ttk.Button(itb, text="Read ECU identification",
                                   command=self.on_info)
        self.info_btn.pack(side="left")
        self.info_table = ttk.Treeview(info, columns=("k", "v"),
                                       show="headings")
        self.info_table.heading("k", text="Field")
        self.info_table.heading("v", text="Value")
        self.info_table.column("k", width=220, anchor="w", stretch=False)
        self.info_table.column("v", width=460, anchor="w")
        self.info_table.pack(fill="both", expand=True)

        # ---- Tune check tab
        tune = ttk.Frame(nb, padding=6)
        nb.add(tune, text="  Tune check  ")
        ttb = ttk.Frame(tune)
        ttb.pack(fill="x", pady=(0, 6))
        self.tune_btn = ttk.Button(ttb, text="Check if remapped",
                                   command=self.on_tune)
        self.tune_btn.pack(side="left")
        ttk.Label(ttb, text="Read-only — reads the ECU's calibration number "
                            "and reflash fingerprint.",
                  foreground="#777").pack(side="left", padx=10)
        self.tune_verdict = ttk.Label(
            tune, text="Connect, then press the button.",
            font=("TkDefaultFont", 12, "bold"), foreground="#777",
            wraplength=760, justify="left")
        self.tune_verdict.pack(fill="x", pady=(2, 6))
        self.tune_reasons = tk.Text(tune, height=5, state="disabled",
                                    wrap="word", relief="flat",
                                    background=root.cget("background"))
        self.tune_reasons.pack(fill="x", pady=(0, 6))
        self.tune_table = ttk.Treeview(tune, columns=("k", "v"),
                                       show="headings", height=8)
        self.tune_table.heading("k", text="ECU field")
        self.tune_table.heading("v", text="Value")
        self.tune_table.column("k", width=220, anchor="w", stretch=False)
        self.tune_table.column("v", width=500, anchor="w")
        self.tune_table.pack(fill="both", expand=True)

        # ---- log + status
        ttk.Label(root, text="Connection log:", padding=(8, 2, 8, 0)
                  ).pack(anchor="w")
        logf = ttk.Frame(root, padding=(8, 0, 8, 6))
        logf.pack(fill="x")
        self.log = tk.Text(logf, height=7, state="disabled",
                           font=("TkFixedFont", 9), wrap="word")
        lsb = ttk.Scrollbar(logf, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=lsb.set)
        self.log.pack(side="left", fill="both", expand=True)
        lsb.pack(side="right", fill="y")

        self.status_var = tk.StringVar(
            value="Ready. Ignition ON, engine off, then press Connect.")
        ttk.Label(root, textvariable=self.status_var, relief="sunken",
                  anchor="w", padding=4).pack(fill="x", side="bottom")

        self._action_buttons = (self.scan_btn, self.scan_all_btn,
                                self.clear_sel_btn, self.clear_all_btn,
                                self.live_btn, self.info_btn, self.tune_btn)
        self._set_connected(False)

    # -------------------------------------------------------------- helpers

    def refresh_ports(self):
        ports = ["(auto)"] + Elm327.candidate_ports()
        self.port_box["values"] = ports
        if self.port_var.get() not in ports:
            self.port_var.set("(auto)")

    def log_line(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", str(text).rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_connected(self, yes: bool, name: str = ""):
        for btn in self._action_buttons:
            btn.configure(state="normal" if yes else "disabled")
        self.connect_btn.configure(text="Disconnect" if yes else "Connect")
        self.conn_label.configure(
            text=name if yes else "not connected",
            foreground="#1a7f37" if yes else "#777")

    def _set_busy(self, busy: bool, note: str = ""):
        self.busy = busy
        if note:
            self.status_var.set(note)

    def show_dtcs(self, dtcs):
        self.table.delete(*self.table.get_children())
        for d in dtcs:
            if d.is_active is True:
                state, tags = "PRESENT NOW", ("active",)
            elif d.is_active is False:
                state, tags = "stored/historic", ()
            else:
                state, tags = "", ()
            self.table.insert("", "end",
                              values=(d.code, describe(d.code), state),
                              tags=tags)

    # -------------------------------------------------------------- actions

    def _submit(self, fn, note: str):
        """Queue one bus job; results come back through msgq."""
        if self.busy and note != "live":
            return
        if note != "live":
            self._set_busy(True, note)
        self.jobq.put(fn)

    def on_connect(self):
        if self.session:
            self._submit(self._job_disconnect, "Disconnecting ...")
            return
        port = self.port_var.get()
        port = None if port in ("", "(auto)") else port
        kkl = self.kkl_var.get()
        self._submit(lambda: self._job_connect(port, kkl),
                     "Connecting — old K-line inits are slow, give it a minute ...")

    def on_scan(self):
        self._submit(self._job_scan, "Reading engine fault codes ...")

    def on_scan_all(self):
        self._submit(self._job_scan_all,
                     "Scanning every system — this walks each ECU, give it "
                     "time ...")

    def on_clear_all(self):
        if messagebox.askyesno(
                "Clear all fault codes",
                "This erases all stored codes and freeze-frame data.\n"
                "Faults still present will come straight back.\n\nClear now?"):
            self._submit(lambda: self._job_clear(None), "Clearing all codes ...")

    def on_clear_selected(self):
        codes = [self.table.item(i)["values"][0]
                 for i in self.table.selection()]
        if not codes:
            messagebox.showinfo("Clear selected",
                                "Select one or more codes in the list first.")
            return
        if messagebox.askyesno("Clear selected codes",
                               "Clear these codes?\n\n" + ", ".join(codes)):
            self._submit(lambda: self._job_clear(codes),
                         f"Clearing {len(codes)} code(s) ...")

    def on_live(self):
        self.live_on = not self.live_on
        self.live_btn.configure(text="Stop" if self.live_on else "Start")
        if self.live_on:
            self.live_note.configure(text="polling ...")
        else:
            self.live_note.configure(text="")

    def on_info(self):
        self._submit(self._job_info, "Reading ECU identification ...")

    def on_tune(self):
        self._submit(self._job_tune, "Checking calibration / reflash "
                                     "fingerprint ...")

    def _live_timer(self):
        if self.live_on and self.session and not self.busy \
                and self.jobq.empty():
            self.jobq.put(self._job_live)
        self.root.after(self.LIVE_MS, self._live_timer)

    def _on_close(self):
        try:
            if self.session:
                self.session.close()
        finally:
            self.root.destroy()

    # ---------------------------------------------------- worker-side jobs

    def _worker(self):
        while True:
            job = self.jobq.get()
            try:
                job()
            except Exception as exc:  # keep the worker alive no matter what
                self.msgq.put(("log", f"{type(exc).__name__}: {exc}"))
                self.msgq.put(("done", "Failed — see the log."))

    def _job_connect(self, port, kkl):
        put = self.msgq.put
        try:
            self.session = ScannerSession(port, kkl,
                                          lambda m: put(("log", m)))
        except (AdapterError, BusError, OSError) as exc:
            put(("log", str(exc)))
            put(("done", "Could not connect — see the log."))
            return
        put(("connected", self.session.name))
        put(("done", f"Connected ({self.session.name}). Scanning ..."))
        self._job_scan()

    def _job_disconnect(self):
        if self.session:
            self.session.close()
            self.session = None
        self.msgq.put(("disconnected", None))
        self.msgq.put(("done", "Disconnected."))

    def _job_scan(self):
        put = self.msgq.put
        dtcs = self.session.read(lambda m: put(("log", m)))
        put(("dtcs", dtcs))
        put(("done", "No fault codes stored ✓" if not dtcs
             else f"{len(dtcs)} fault code(s) found."))

    def _job_scan_all(self):
        put = self.msgq.put
        results = self.session.scan_systems(lambda m: put(("log", m)))
        put(("systems", results))
        total = sum(len(d) for _, d in results if d)
        reached = sum(1 for _, d in results if d is not None)
        put(("done", f"Scanned {len(results)} systems, {reached} responded, "
                     f"{total} code(s) total."))

    def _job_clear(self, codes):
        put = self.msgq.put
        status = lambda m: put(("log", m))
        if codes:
            missed = [c for c in codes if not self.session.clear_one(c, status)]
            if missed:
                status(f"ECU refused per-code clear for {', '.join(missed)} "
                       "(many ECUs only clear everything at once — "
                       "use Clear all).")
        else:
            if not self.session.clear_all(status):
                put(("done", "ECU refused the clear — codes NOT cleared."))
                return
        dtcs = self.session.read(status)
        put(("dtcs", dtcs))
        put(("done", "Cleared ✓ — cycle the ignition and re-scan to confirm."
             if not dtcs else
             f"{len(dtcs)} code(s) remain (still-present faults return "
             "immediately)."))

    def _job_live(self):
        put = self.msgq.put
        got_any = False
        for p in self.live_pids:
            if not self.live_on:
                return
            value = read_pid(self.session.request, p)
            if value is not None:
                got_any = True
            put(("live", (p.pid, value)))
        if not got_any:
            put(("live_dead", None))

    def _job_info(self):
        put = self.msgq.put
        info = read_ecu_info(self.session.request)
        n_std = len(supported_pids(self.session.request))
        if n_std:
            info.append(("Standard OBD PIDs supported", str(n_std)))
        put(("info", info))
        put(("done", "ECU identification read." if info else
             "This ECU offers no identification strings."))

    def _job_tune(self):
        put = self.msgq.put
        report = check_tune(self.session.request, lambda m: put(("log", m)))
        put(("tune", report))
        put(("done", report.headline))

    def _show_systems(self, results):
        self.table.delete(*self.table.get_children())
        for module, dtcs in results:
            if dtcs is None:
                self.table.insert("", "end", tags=("muted",), values=(
                    "—", f"[{module.name}] no response — pin {module.pin} "
                         "wired? module fitted?", ""))
            elif not dtcs:
                self.table.insert("", "end", tags=("muted",), values=(
                    "✓", f"[{module.name}] no fault codes", ""))
            else:
                for d in dtcs:
                    state = ("PRESENT NOW" if d.is_active is True else
                             "stored" if d.is_active is False else "")
                    tag = "active" if d.is_active is True else ""
                    self.table.insert("", "end", tags=(tag,) if tag else (), values=(
                        d.code, f"[{module.name}] {describe(d.code)}", state))

    def _show_tune(self, report):
        colour = {"clean": "#1a7f37", "reflashed": "#b00020",
                  "unknown": "#9a6700"}.get(report.verdict, "#777")
        self.tune_verdict.configure(text=report.headline, foreground=colour)
        self.tune_reasons.configure(state="normal")
        self.tune_reasons.delete("1.0", "end")
        self.tune_reasons.insert("end", "\n".join(f"• {r}"
                                                  for r in report.reasons))
        self.tune_reasons.configure(state="disabled")
        self.tune_table.delete(*self.tune_table.get_children())
        for k, v in report.fields:
            self.tune_table.insert("", "end", values=(k, v))

    # ------------------------------------------------------------- polling

    def _poll(self):
        try:
            while True:
                kind, payload = self.msgq.get_nowait()
                if kind == "log":
                    self.log_line(payload)
                elif kind == "dtcs":
                    self.show_dtcs(payload)
                elif kind == "systems":
                    self._show_systems(payload)
                elif kind == "connected":
                    self._set_connected(True, payload)
                elif kind == "disconnected":
                    self._set_connected(False)
                    self.live_on = False
                    self.live_btn.configure(text="Start")
                elif kind == "live":
                    pid, value = payload
                    iid = f"pid{pid:02X}"
                    vals = list(self.live_table.item(iid)["values"])
                    vals[1] = "—" if value is None else value
                    self.live_table.item(iid, values=vals)
                elif kind == "live_dead":
                    self.live_on = False
                    self.live_btn.configure(text="Start")
                    self.live_note.configure(
                        text="No live data — this ECU doesn't answer the "
                             "standard OBD readings (pre-EOBD unit).")
                elif kind == "info":
                    self.info_table.delete(
                        *self.info_table.get_children())
                    for k, v in payload:
                        self.info_table.insert("", "end", values=(k, v))
                elif kind == "tune":
                    self._show_tune(payload)
                elif kind == "done":
                    self._set_busy(False, payload)
        except queue.Empty:
            pass
        self.root.after(self.POLL_MS, self._poll)


def main() -> int:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
