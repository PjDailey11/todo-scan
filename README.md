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
