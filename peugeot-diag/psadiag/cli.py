"""Command-line interface.

    psa-diag scan            connect and read fault codes
    psa-diag clear           read codes, then clear them (asks first)
    psa-diag terminal        raw AT/hex terminal for experimenting
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .dtc import describe
from .elm327 import AdapterError, BusError, Elm327
from .profiles import PROFILES, get_profile
from .session import clear_dtcs, connect, read_dtcs


def _status(msg: str) -> None:
    print(msg, file=sys.stderr)


def _open_adapter(args) -> Elm327:
    if args.port:
        elm = Elm327(port=args.port, baudrate=args.baud, verbose=args.verbose)
        elm.open()
    else:
        _status("Looking for the USB interface ...")
        elm = Elm327.autodetect(verbose=args.verbose)
    _status(f"Adapter: {elm.identity} on {elm.port} @ {elm.baudrate} baud")
    return elm


def _connect(args, elm: Elm327):
    profiles = [get_profile(args.profile)] if args.profile else list(PROFILES)
    _status("Connecting to the ECU (this can take a minute — old K-line "
            "inits are slow):")
    return connect(elm, profiles, status=_status)


def _print_codes(dtcs) -> None:
    if not dtcs:
        print("\nNo fault codes stored. ✓")
        return
    print(f"\n{len(dtcs)} fault code(s):\n")
    for d in dtcs:
        flag = ""
        if d.is_active is True:
            flag = "  [PRESENT NOW]"
        elif d.is_active is False:
            flag = "  [stored/historic]"
        print(f"  {d.code}  {describe(d.code)}{flag}")
    print()


def cmd_scan(args) -> int:
    if args.kkl:
        conn = _connect_kkl(args)
        try:
            _status(f"Link up ({conn.describe()}); reading fault codes ...")
            _print_codes(conn.read_dtcs(status=_status))
            return 0
        finally:
            conn.close()
    elm = _open_adapter(args)
    try:
        conn = _connect(args, elm)
        _status(f"Link up ({conn.describe()}); reading fault codes ...")
        _print_codes(read_dtcs(conn, status=_status))
        return 0
    finally:
        elm.close()


def _connect_kkl(args):
    from .kline import connect_kkl
    if not args.port:
        raise AdapterError("raw K-line mode needs an explicit port: "
                           "psa-diag --kkl -p /dev/ttyUSB0 (or COMx) ...")
    _status("Raw K-line mode (KKL cable); connecting to the ECU ...")
    return connect_kkl(args.port, verbose=args.verbose, status=_status)


def cmd_clear(args) -> int:
    if args.kkl:
        conn = _connect_kkl(args)
        try:
            dtcs = conn.read_dtcs(status=_status)
            _print_codes(dtcs)
            if not dtcs and not args.force:
                print("Nothing to clear.")
                return 0
            if not args.yes:
                answer = input("Clear these codes? Freeze-frame data is lost "
                               "and a real fault will come straight back. [y/N] ")
                if answer.strip().lower() not in ("y", "yes"):
                    print("Not cleared.")
                    return 1
            if conn.clear_dtcs(status=_status):
                print("Codes cleared. ✓  (Cycle the ignition, then re-scan.)")
                return 0
            print("The ECU refused the clear request — codes NOT cleared.")
            return 1
        finally:
            conn.close()
    elm = _open_adapter(args)
    try:
        conn = _connect(args, elm)
        dtcs = read_dtcs(conn, status=_status)
        _print_codes(dtcs)
        if not dtcs and not args.force:
            print("Nothing to clear.")
            return 0
        if not args.yes:
            answer = input("Clear these codes? Freeze-frame data is lost and a "
                           "real fault will come straight back. [y/N] ")
            if answer.strip().lower() not in ("y", "yes"):
                print("Not cleared.")
                return 1
        if clear_dtcs(conn, status=_status):
            print("Codes cleared. ✓  (Cycle the ignition, then re-scan to "
                  "confirm nothing returns.)")
            return 0
        print("The ECU refused the clear request — codes NOT cleared.\n"
              "Some PSA ECUs only clear with ignition on / engine off.")
        return 1
    finally:
        elm.close()


def cmd_terminal(args) -> int:
    """Raw terminal: type AT commands or hex requests directly."""
    elm = _open_adapter(args)
    print("Raw terminal. Type AT commands (ATSP5, ATSH 80 10 F1 ...) or hex "
          "requests (1081, 14FF00). Ctrl-D to quit.")
    try:
        while True:
            try:
                line = input("elm> ").strip()
            except EOFError:
                print()
                return 0
            if not line:
                continue
            try:
                for reply in elm.command(line, timeout=15.0):
                    print(f"  {reply}")
            except (AdapterError, BusError) as exc:
                print(f"  ! {exc}")
    finally:
        elm.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="psa-diag",
        description="Read/clear engine fault codes on KWP2000-era Peugeot/"
                    "Citroën through an ELM327 USB interface.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("-p", "--port",
                        help="serial port (e.g. COM3, /dev/ttyUSB0); "
                             "auto-detected if omitted")
    parser.add_argument("-b", "--baud", type=int, default=38400,
                        help="adapter baud rate (default 38400)")
    parser.add_argument("--profile", choices=[p.name for p in PROFILES],
                        help="force one init strategy instead of trying all")
    parser.add_argument("--kkl", action="store_true",
                        help="raw K-line mode for dumb KKL/VAG-409.1 cables "
                             "(no ELM chip; needs -p PORT)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show raw serial traffic")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("scan", help="connect and read fault codes (default)")
    p_clear = sub.add_parser("clear", help="read fault codes, then clear them")
    p_clear.add_argument("-y", "--yes", action="store_true",
                         help="clear without asking")
    p_clear.add_argument("--force", action="store_true",
                         help="send the clear even if no codes were read")
    sub.add_parser("terminal", help="raw AT/hex terminal")
    sub.add_parser("gui", help="open the point-and-click window")

    args = parser.parse_args(argv)
    if args.command == "gui":
        from .gui import main as gui_main
        return gui_main()
    handler = {"clear": cmd_clear, "terminal": cmd_terminal}.get(
        args.command, cmd_scan)
    try:
        return handler(args)
    except AdapterError as exc:
        print(f"\nAdapter problem: {exc}", file=sys.stderr)
        return 2
    except BusError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
