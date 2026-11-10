"""Allow ``python -m todo_scan`` to invoke the same CLI as the console script."""

from todo_scan.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
