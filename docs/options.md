# Command-line options

```
todo-scan [PROJECT_PATH] [--tag TAG] [--suffix SUFFIX] [--exclude-dir NAME]
          [--format {text,json,markdown}] [--stats] [--check]
          [--output FILE]
          [--version]
```

| Option | Default | Description |
| --- | --- | --- |
| `PROJECT_PATH` | `.` | Directory to walk, or a single file to scan. |
| `--tag TAG` | `TODO,FIXME,HACK,XXX,NOTE` | Only report these tags. Case-insensitive, repeatable, comma lists allowed. |
| `--suffix SUFFIX` | every recognized file | Only scan files with these suffixes. Repeatable, comma lists allowed, leading dot optional. |
| `--exclude-dir NAME` | built-in list | Skip directories with this exact name **in addition to** the built-in list. Repeatable. |
| `--format FORMAT` | `text` | `text`, `json`, or `markdown`. |
| `--stats` | off | Print a per-tag count summary to standard error after the report. |
| `--check` | off | Exit with status 1 when any matching tag is found. See [ci.md](ci.md). |
| `--output FILE` | standard output | Write the report to a file instead of printing it. |
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

## `--format` and `--output`

```bash
todo-scan --format json --output todos.json
todo-scan --format markdown > TODOS.md
```

The JSON report is always an array, including when it is empty. If the output
file cannot be written the tool prints an error and exits with status 1.

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

## Exit status

| Status | Meaning |
| --- | --- |
| 0 | The scan ran. Without `--check`, tags may or may not have been found; with `--check`, none were found. |
| 1 | `--check` was given and tags were found, or the report could not be written to `--output`. |
| 2 | Usage error: missing path, or an empty `--tag` / `--suffix` value. |
