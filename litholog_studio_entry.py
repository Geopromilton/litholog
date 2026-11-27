"""Entry point for the packaged LithoLog Studio (PyInstaller) and for `python litholog_studio_entry.py`."""
import sys

if __name__ == "__main__":
    if "--self-check" in sys.argv:
        # Writes a PASS/FAIL report and exits; used to test a fresh build.
        i = sys.argv.index("--self-check")
        report = sys.argv[i + 1] if len(sys.argv) > i + 1 else "litholog_check.txt"
        try:
            from litholog.studio.smoke import check
            code = check(report)
        except BaseException:  # start-up/import failure: write it down instead of a hidden error dialog
            import traceback
            from pathlib import Path
            Path(report).write_text("LithoLog Studio Self-Check Report\n" + "=" * 40 + "\nFAIL: start-up error\n"
                                    + traceback.format_exc() + "\nRESULT: FAIL\n", encoding="utf-8")
            code = 1
        raise SystemExit(code)
    from litholog.studio.app import main
    raise SystemExit(main())
