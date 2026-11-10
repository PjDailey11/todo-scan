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

## What it does and does not do

The scanner is a heuristic. It looks for tags inside comment delimiters chosen
from the file suffix (`#` for Python and shell, `//` and `/* */` for C-like
languages, `<!-- -->` for HTML, `--` for SQL and Lua, `;` for Lisp-family
files). It is not a full language parser, so a tag inside a string can still
match if a comment delimiter also appears in that string.

A few deliberate rules keep the noise down:

- `https://` is not treated as a `//` comment, so URLs that contain a tag name
  are not reported.
- Binary files (a NUL in the first 8 KiB), files larger than 1 MiB, and files
  that are not valid UTF-8 are skipped.
- Well-known tool directories such as `.git`, `node_modules`, and `.venv` are
  not walked. The walker does not follow symlinks, so a scan cannot escape the
  tree you passed in.
- `.gitignore` is not honored yet; that is a planned improvement.

Default tags are `TODO`, `FIXME`, `HACK`, `XXX`, and `NOTE`. They are matched
case-insensitively as whole words, with an optional colon before the message.

## License

MIT. See [LICENSE](LICENSE).
