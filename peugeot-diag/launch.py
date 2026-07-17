"""Entry point for the packaged executable (psa-diag.exe).

Double-click (no arguments) opens the GUI scanner window. Run it from a
terminal with arguments and it behaves as the command-line tool, e.g.
    psa-diag scan
    psa-diag systems
    psa-diag tune

Imports are deferred so the CLI path doesn't require Tk to be present.
"""

import sys


def main() -> int:
    if len(sys.argv) > 1:
        from psadiag.cli import main as cli_main
        return cli_main()
    from psadiag.gui import main as gui_main
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
