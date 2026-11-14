# todo-scan

Scan a project tree for `TODO`, `FIXME`, `HACK`, `XXX`, and `NOTE` comments and
print them as a readable report in text, JSON, or Markdown.

todo-scan is a small, dependency-free Python CLI. It is a heuristic comment
scanner, not a full language parser: that keeps it fast and easy to read, at
the cost of occasional false positives inside strings or unusual comment
dialects (see [What it does and does not do](#what-it-does-and-does-not-do)).

## Motivation

Reminder comments pile up quietly. `grep -rn TODO` finds them, but it also
matches URLs, string literals, `node_modules`, build output, and binary files,
and its output is hard to feed into other tools. todo-scan only looks inside
real comment delimiters, skips tool directories by default, and can emit JSON
for scripts, Markdown for a tracking issue, a per-tag summary, or a non-zero
exit status for CI.

## Features

- Finds `TODO`, `FIXME`, `HACK`, `XXX`, and `NOTE` (or any tags you choose)
  case-insensitively as whole words, with an optional colon.
- Understands `#`, `//`, `/* */`, `<!-- -->`, `--`, Haskell `{- -}`, Erlang `%`,
  and `;` comments, chosen by file suffix; `https://` is not mistaken for a `//` comment.
- Skips `.git`, `node_modules`, virtualenvs, caches, and build output; never
  follows symlinks; skips binary, oversized (>1 MiB), and non-UTF-8 files.
- Honors the project's top-level `.gitignore` (names, `*.ext`, `dir/`,
  anchored `/path`, and `!` negation); opt out with `--no-gitignore`.
- Filters by tag (`--tag`), file suffix (`--suffix`), and extra directory
  names (`--exclude-dir`).
- Text, JSON, and Markdown reports, optionally written to a file.
- `--sort file|tag|count` to read results by location, grouped by tag, or
  busiest files first.
- `--stats` per-tag summary, a `--check` mode that fails CI when tags are found,
  a `--max-count N` budget for projects with an existing baseline, and
  `--quiet` for silent exit-status-only gates.
- No runtime dependencies; Python 3.9+.

## Install

```bash
git clone https://github.com/PjDailey11/todo-scan.git
cd todo-scan
pip install .
```

Or install straight from GitHub:

```bash
pip install git+https://github.com/PjDailey11/todo-scan.git
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

# Only scan Python and JavaScript files
todo-scan --suffix py,js

# Skip extra directories on top of the built-in list (.git, node_modules, ...)
todo-scan --exclude-dir fixtures --exclude-dir generated

# Group all FIXMEs together, or list the files with the most reminders first
todo-scan --sort tag
todo-scan --sort count

# Include files that the project's .gitignore would normally hide
todo-scan --no-gitignore

# Print a per-tag count summary (to stderr) after the report
todo-scan --stats

# Fail with exit status 1 if any FIXME is left (for CI)
todo-scan --check --tag FIXME

# Fail only if the project grows past 37 tags, without printing the report
todo-scan --max-count 37 --quiet

# Write a machine-readable or Markdown report
todo-scan --format json --output todos.json
todo-scan --format markdown --output todos.md
```

### Sample output

Text (the default) uses `path:line: TAG message` lines, which most terminals
and editors treat as clickable locations:

```
$ todo-scan --stats
src/app.py:2: TODO handle empty input
src/app.py:5: FIXME off-by-one on the last page
src/client.js:1: NOTE keep in sync with app.py
tests/test_app.py:1: TODO cover unicode names
TODO   2
FIXME  1
NOTE   1
total  4
```

JSON is always an array, even when empty:

```
$ todo-scan --format json --tag FIXME
[
  {
    "path": "src/app.py",
    "line": 5,
    "tag": "FIXME",
    "message": "off-by-one on the last page",
    "comment_style": "hash"
  }
]
```

Markdown groups matches by file:

```
$ todo-scan --format markdown --suffix py
# Tagged comments

## src/app.py

- Line 2: `TODO` — handle empty input
- Line 5: `FIXME` — off-by-one on the last page

## tests/test_app.py

- Line 1: `TODO` — cover unicode names
```

## Options

| Option | Default | Description |
| --- | --- | --- |
| `PROJECT_PATH` | `.` | Directory to walk, or a single file. |
| `--tag TAG` | `TODO,FIXME,HACK,XXX,NOTE` | Tags to report; repeatable, comma lists allowed. |
| `--suffix SUFFIX` | every recognized file | Only scan these suffixes; leading dot optional. |
| `--exclude-dir NAME` | built-in list | Extra directory basenames to skip, added to the defaults. |
| `--no-gitignore` | off | Do not apply the top-level `.gitignore` while walking. |
| `--sort ORDER` | `file` | `file` (path, line), `tag` (by tag name), or `count` (busiest files first). |
| `--format FORMAT` | `text` | `text`, `json`, or `markdown`. |
| `--stats` | off | Per-tag counts on standard error after the report. |
| `--check` | off | Exit 1 when any matching tag is found. |
| `--max-count N` | off | Exit 1 only when more than `N` tags are found (overrides `--check`). |
| `-q`, `--quiet` | off | Do not print the report to stdout; `--output` and `--stats` still work. |
| `--output FILE` | stdout | Write the report to a file. |
| `--version` | | Print the version. |

Exit status: `0` when the scan ran (and, with `--check`, found nothing), `1`
when `--check` found tags, `--max-count N` found more than `N`, or `--output`
could not be written, `2` for usage errors such as a missing path, an empty
`--tag` / `--suffix`, or a negative `--max-count`. Full details
are in [docs/options.md](docs/options.md) and [docs/ci.md](docs/ci.md).

## Project structure

```
todo-scan/
├── src/todo_scan/
│   ├── cli.py               argument parsing, flag normalization, exit codes
│   ├── project_scan.py      library entry point: walk + filter + scan
│   ├── directory_walker.py  sorted tree walk, skip list, suffix filter
│   ├── gitignore_rules.py   simplified .gitignore parser and matcher
│   ├── scanner.py           per-file checks and comment/tag detection
│   ├── comment_styles.py    comment delimiters per file suffix
│   ├── tag_pattern.py       compiled regex for the tag allow-list
│   ├── recognized_tags.py   default tags and normalization
│   ├── tagged_comment.py    the TaggedComment record
│   ├── result_ordering.py   --sort orders (file, tag, count)
│   └── report.py            text/JSON/Markdown formatters and tag summary
├── tests/                   pytest suite, one module per source module,
│                            plus a version-consistency check
├── docs/                    design and usage guides
└── CHANGELOG.md             release notes per version
```

## How it works

The scan is a short pipeline: walk the tree (skipping tool directories,
gitignored paths, and symlinks), optionally filter by suffix, scan each file's comments with one
compiled tag regex, put the matches in the `--sort` order, and format the resulting `TaggedComment` records. Each
stage is a plain function in its own module so it can be tested alone. The
full walkthrough is in [docs/how-it-works.md](docs/how-it-works.md).

## What it does and does not do

The scanner is a heuristic. It looks for tags inside comment delimiters chosen
from the file suffix (`#` for Python and shell, `//` and `/* */` for C-like
languages, `<!-- -->` for HTML, `--` for SQL and Lua, `--` and `{- -}` for
Haskell, `%` for Erlang, `;` for Lisp-family files; the full table is in
[docs/how-it-works.md](docs/how-it-works.md#3-scanning-one-file)). It is not a full language parser, so a tag inside a string can still
match if a comment delimiter also appears in that string.

Block comments do not nest, so a nested Haskell `{- {- -} -}` block ends at
the first `-}`.

A few deliberate rules keep the noise down:

- `https://` is not treated as a `//` comment, so URLs that contain a tag name
  are not reported.
- Binary files (a NUL in the first 8 KiB), files larger than 1 MiB, and files
  that are not valid UTF-8 are skipped.
- Well-known tool directories such as `.git`, `node_modules`, and `.venv` are
  not walked. The walker does not follow symlinks, so a scan cannot escape the
  tree you passed in.
- The `.gitignore` at the project root is honored by default. A practical
  subset is supported: plain names and globs (`*.log`), directory-only rules
  (`generated/`), root-anchored rules (`/local.cfg`, `docs/drafts`), comments,
  and `!` negation. Nested `.gitignore` files, `.git/info/exclude`, global
  excludes, and git's special `**` rules are not modeled. Use
  `--no-gitignore` to scan ignored files anyway; a file passed directly on the
  command line is always scanned.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

The suite uses pytest's `tmp_path` fixture to build small throwaway project
trees, so tests never depend on files outside the repository. CLI tests call
`todo_scan.cli.main(argv)` directly and check its return value and captured
output instead of spawning a subprocess. `tests/test_version.py` fails if
`__version__`, `pyproject.toml`, the CHANGELOG, and `--version` disagree, so
a half-finished release bump is caught before it is pushed.

There is no hosted CI workflow yet; run `pytest` locally before pushing.

## Roadmap

- Read nested `.gitignore` files and `.git/info/exclude`.
- Optional `git blame` author/date per match.
- More comment dialects (for example Lua `--[[ ]]` blocks, OCaml `(* *)`, and
  nested Haskell blocks).

## Changelog

The current release is **0.2.0**. Every release and the flags it added are
listed in [CHANGELOG.md](CHANGELOG.md).

## Contributing

Issues and pull requests are welcome. Please keep changes small and focused:
one behavior per pull request, with a test for it and an update to the README
or the matching guide in [docs/](docs/README.md). Run `pytest` before opening a
pull request, and add a line under **Unreleased** in the CHANGELOG for any
user-visible change. Public functions need a docstring that covers parameters, return
value, and edge cases.

## License

MIT. See [LICENSE](LICENSE).
