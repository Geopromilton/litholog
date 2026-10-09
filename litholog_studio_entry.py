"""Entry point for the packaged LithoLog Studio (PyInstaller) and for `python litholog_studio_entry.py`."""
import sys

if __name__ == "__main__":
    if "--self-check" in sys.argv:
        # Writes a PASS/FAIL report and exits; used to test a fresh build.
        i = sys.argv.index("--self-check")
        report = sys.argv[i + 1] if len(sys.argv) > i + 1 else "litholog_check.txt"
        from litholog.studio.smoke import check
        raise SystemExit(check(report))
    from litholog.studio.app import main
    raise SystemExit(main())
