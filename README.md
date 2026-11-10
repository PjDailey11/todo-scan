# todo-scan

Scan a project tree for `TODO`, `FIXME`, `HACK`, `XXX`, and `NOTE` comments and
print them as a readable report.

The tool is a heuristic comment scanner, not a full language parser. That keeps
it small and dependency-free, at the cost of occasional false positives inside
strings or unusual comment dialects. Usage, install steps, and those limitations
are documented in the sections below as the project grows.

## Install

todo-scan requires Python 3.9 or newer and has no runtime dependencies.

```bash
git clone https://github.com/PjDailey11/todo-scan.git
cd todo-scan
pip install .
```

For local development, install the test extra as well:

```bash
pip install -e ".[dev]"
pytest
```

## Usage

Scan the current directory, or pass a project root or a single file:

```bash
todo-scan
todo-scan path/to/project
todo-scan src/app.py
```

Useful flags:

```bash
# Only report FIXME comments (repeat --tag or use a comma list)
todo-scan --tag FIXME
todo-scan --tag TODO,FIXME

# Write a machine-readable or Markdown report
todo-scan --format json --output todos.json
todo-scan --format markdown --output todos.md
```

The process exits with status 0 when the scan succeeds, even if reminders were
found. This is a reporter, not a linter; a non-zero "has findings" status is
left for a future `--check` flag. A missing path exits with status 2.

The default text format uses `path:line: TAG message` lines, which most
terminals and editors treat as clickable locations.
