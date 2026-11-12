# Using todo-scan in CI

By default todo-scan is a reporter: it exits with status 0 whenever the scan
runs, even if it finds reminders. Add `--check` to turn it into a gate that
fails the build when tags are present.

## Exit statuses with `--check`

| Status | Meaning |
| --- | --- |
| 0 | No matching tags were found. |
| 1 | At least one matching tag was found (or `--output` could not be written). |
| 2 | Usage error: missing path, or an empty `--tag` / `--suffix` value. |

Keeping usage errors at 2 means a typo in the CI command is distinguishable
from "the project still has FIXMEs".

## Gate only on specific tags

Most teams are happy to keep `TODO` notes around but do not want a `FIXME` or
`XXX` to ship. Combine `--check` with `--tag`:

```bash
todo-scan --check --tag FIXME,XXX
```

The report is still printed, so the failing job log lists every offending
line in `path:line: TAG message` form.

## GitHub Actions example

```yaml
name: reminders
on: [push, pull_request]
jobs:
  todo-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install git+https://github.com/PjDailey11/todo-scan.git
      - run: todo-scan --check --tag FIXME,XXX --stats --exclude-dir fixtures
```

`--stats` is optional; it adds a per-tag count to the log on standard error.

## Pre-commit style local check

```bash
todo-scan src --check --tag FIXME || echo "resolve FIXMEs before committing"
```
