# Command-line options

```
todo-scan [PROJECT_PATH] [--tag TAG] [--suffix SUFFIX] [--exclude-dir NAME]
          [--no-gitignore]
          [--sort {file,tag,count}]
          [--format {text,json,markdown,csv}] [--stats] [--check]
          [--max-count N] [-q] [--output FILE]
          [--list-styles] [--version]
```

| Option | Default | Description |
| --- | --- | --- |
| `PROJECT_PATH` | `.` | Directory to walk, or a single file to scan. |
| `--tag TAG` | `TODO,FIXME,HACK,XXX,NOTE` | Only report these tags. Case-insensitive, repeatable, comma lists allowed. |
| `--suffix SUFFIX` | every recognized file | Only scan files with these suffixes. Repeatable, comma lists allowed, leading dot optional. |
| `--exclude-dir NAME` | built-in list | Skip directories with this exact name **in addition to** the built-in list. Repeatable. |
| `--no-gitignore` | off (gitignore honored) | Do not apply the project's top-level `.gitignore`. |
| `--sort ORDER` | `file` | `file`, `tag`, or `count`. See below. |
| `--format FORMAT` | `text` | `text`, `json`, `markdown`, or `csv`. |
| `--stats` | off | Print a per-tag count summary to standard error after the report. |
| `--check` | off | Exit with status 1 when any matching tag is found. See [ci.md](ci.md). |
| `--max-count N` | off | Exit with status 1 only when more than `N` tags are found. Overrides `--check`. See [ci.md](ci.md#allow-a-baseline-with---max-count). |
| `-q`, `--quiet` | off | Do not print the report to standard output. `--output` and `--stats` still work. |
| `--output FILE` | standard output | Write the report to a file instead of printing it. |
| `--list-styles` | off | Print the suffix to comment style table and exit 0 without scanning. See below. |
| `--version` | | Print the version and exit. |

## `--tag`

```bash
todo-scan --tag FIXME            # only FIXME
todo-scan --tag todo,fixme       # comma list, case does not matter
todo-scan --tag TODO --tag HACK  # repeated flag
```

Passing only empty values (`--tag ,`) is a usage error (exit status 2), because
an empty allow-list would otherwise match nothing and look like a clean scan.

## `--suffix`

```bash
todo-scan --suffix py           # same as --suffix .py
todo-scan --suffix .py,.js
todo-scan --suffix PY           # suffixes are compared case-insensitively
```

Files without a suffix (`Makefile`, `Dockerfile`) are dropped when a suffix
filter is active, because comment styles are chosen by suffix. As with
`--tag`, an all-empty value is a usage error.

## `--exclude-dir`

```bash
todo-scan --exclude-dir fixtures
todo-scan --exclude-dir fixtures --exclude-dir generated
```

Names match a directory's **basename exactly**, anywhere in the tree; they are
not glob patterns or paths. A trailing slash from shell tab completion
(`fixtures/`) is stripped. The built-in list always stays active:

`.git`, `.hg`, `.svn`, `.idea`, `.vscode`, `.venv`, `venv`, `env`,
`node_modules`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`,
`.tox`, `.eggs`, `dist`, `build`, `htmlcov`, `target`, `vendor`.

## `--no-gitignore`

By default the `.gitignore` at the top of `PROJECT_PATH` is applied while
walking, so generated code, local scratch files, and anything else the project
already ignores stay out of the report:

```bash
todo-scan                 # skips paths matched by ./.gitignore
todo-scan --no-gitignore  # audit everything, including ignored files
```

`--no-gitignore` only turns off the `.gitignore` rules; the built-in directory
list above still applies. When `PROJECT_PATH` is a single file it is always
scanned, even if `.gitignore` matches it. Supported pattern syntax and known
gaps are described in [how-it-works.md](how-it-works.md#gitignore-support).

## `--sort`

```
$ todo-scan --sort file      # default: path, then line
alpha.py:1: TODO alpha task
beta.py:1: FIXME beta bug
beta.py:2: TODO beta task

$ todo-scan --sort tag       # tag name A-Z, then path and line
beta.py:1: FIXME beta bug
alpha.py:1: TODO alpha task
beta.py:2: TODO beta task

$ todo-scan --sort count     # files with the most matches first
beta.py:1: FIXME beta bug
beta.py:2: TODO beta task
alpha.py:1: TODO alpha task
```

Ties always fall back to path and line, so output is deterministic. The order
applies to every format, including JSON. The Markdown report starts a new file
heading whenever the file changes, so `--sort tag --format markdown` can show
the same file heading more than once; `file` or `count` give one heading per
file. `--stats` is unaffected (it always lists tags by descending count). An
unknown value is a usage error (exit status 2).

## `--format` and `--output`

```bash
todo-scan --format json --output todos.json
todo-scan --format markdown > TODOS.md
```

The JSON report is always an array, including when it is empty. If the output
file cannot be written the tool prints an error and exits with status 1.

### CSV

```bash
todo-scan --format csv --output todos.csv
```

The CSV report starts with the header row
`path,line,tag,message,comment_style` (the same field names as the JSON
objects) and then has one row per match in the selected `--sort` order. Details
worth knowing:

- The header row is written even when nothing is found, so a spreadsheet
  import or `csv.DictReader` always sees the same columns.
- Quoting is done by Python's `csv` module: a message such as
  `handle "a, b" input` becomes `"handle ""a, b"" input"`, and an empty message
  is an empty field.
- Rows end in `\r\n` (RFC 4180), which Excel, LibreOffice, and Python's `csv`
  reader all expect. `--output` writes those bytes unchanged on every
  platform. When piping standard output on Windows, prefer `--output`, because
  the console's text mode can add an extra `\r`.
- `--quiet` and `--stats` behave the same as for the other formats; the stats
  summary goes to standard error, so it never ends up inside the CSV file.

## `--stats`

```bash
$ todo-scan --stats
src/app.py:3: TODO handle empty input
src/app.py:9: FIXME off-by-one on the last page
tests/test_app.py:4: TODO cover unicode names
TODO   2
FIXME  1
total  3
```

Tags are listed by descending count, ties alphabetically, and only tags with
at least one match appear. A `total` line is always printed, even for an
empty scan (`total  0`).

The summary is written to **standard error**, not standard output. That keeps
`todo-scan --format json --stats > todos.json` a valid JSON file while still
showing the counts in the terminal or CI log. Redirect it with `2> stats.txt`
if you want to keep it.

## `--quiet`

```bash
todo-scan --check --quiet                 # silent gate: only the exit status
todo-scan -q --format json --output todos.json --stats
```

`--quiet` only affects the report on standard output. A report requested with
`--output FILE` is still written, and the `--stats` summary still goes to
standard error, so a CI job can keep a quiet log and still upload the report
as an artifact.

## `--max-count`

```bash
todo-scan --max-count 25 --quiet   # fail only if the project grows past 25 tags
```

`N` is a budget: the run exits with status 1 when **more than** `N` matching
tags are found, and 0 otherwise. `--check` is the same as `--max-count 0`.
When both are given, the explicit `--max-count` wins. The count is taken after
`--tag`, `--suffix`, `--exclude-dir`, and `.gitignore` filtering, so
`--tag FIXME --max-count 3` budgets FIXMEs only. A negative or non-integer
value is a usage error (exit status 2).

## `--list-styles`

```bash
$ todo-scan --list-styles
.bash      hash         line '#'
.c         c-style      line '//', block '/*' ... '*/'
.cc        c-style      line '//', block '/*' ... '*/'
...
.hs        haskell      line '--', block '{-' ... '-}'
...
.sql       dash-dash    line '--'
...
```

Prints one row per file suffix that todo-scan reads: the suffix, the comment
style name (the same value stored as `comment_style` in JSON reports), and the
delimiters that style recognizes. Delimiters are quoted so short markers such
as `--` and `;` are easy to read. Rows are sorted by suffix, ignoring case, so
`.R` and `.r` appear next to each other and the output is stable enough to
diff between versions.

The table is generated from the same mapping the scanner uses, so it is always
accurate for the installed version, unlike a hand-written docs table. Files
whose suffix is not listed are skipped entirely; `--suffix` can narrow the list
but cannot add new suffixes.

The flag is handled before anything else: no scan runs, other filters are
ignored, and the positional path is not checked, so `todo-scan --list-styles`
works from any directory and always exits with status 0.

## Exit status

| Status | Meaning |
| --- | --- |
| 0 | The scan ran (or `--list-styles` printed the table). Without `--check`, tags may or may not have been found; with `--check`, none were found. |
| 1 | `--check` was given and tags were found, `--max-count N` was given and more than `N` were found, or the report could not be written to `--output`. |
| 2 | Usage error: missing path, an empty `--tag` / `--suffix` value, or a bad `--max-count`. |
