# Changelog

All notable changes to todo-scan are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/). While the version is below 1.0,
new flags bump the minor version and fixes bump the patch version; existing
flags and exit statuses are not changed without a note under **Changed**.

## Unreleased

Nothing yet.

## 0.2.0 - 2026-11-13

### Added

- `-q` / `--quiet` drops the report from standard output while keeping
  `--output` and `--stats` (#11, #12).
- `--max-count N` exits with status 1 only when more than `N` tags are found,
  so an existing project can gate on a baseline; `--check` is the `N = 0`
  case (#11, #12).
- Haskell `{- -}` block comments alongside `--` line comments for `.hs`, and
  Erlang `%` comments for `.erl`, `.hrl`, and `.escript` (#13, #14).
- The top-level `.gitignore` is honored while walking (names, globs,
  directory-only and anchored rules, `!` negation), with `--no-gitignore` to
  opt out (#7, #9).
- `--sort file|tag|count` applies one order to every report format (#8, #10).
- `--suffix` and `--exclude-dir` filters (#1, #4).
- `--stats` per-tag summary on standard error (#2, #5).
- `--check` exits with status 1 when tags are found, for CI (#3, #6).
- A `docs/` folder with how-it-works, options, and CI guides.

### Changed

- `.hs` files now use the `haskell` comment style instead of `dash-dash`, so
  the `comment_style` field in JSON reports for Haskell matches changes value.

## 0.1.0 - 2026-11-10

### Added

- Initial release: a dependency-free scanner for `TODO`, `FIXME`, `HACK`,
  `XXX`, and `NOTE` inside `#`, `//`, `/* */`, `<!-- -->`, `--`, and `;`
  comments, chosen by file suffix.
- A project walker that skips tool directories, never follows symlinks, and
  ignores binary, oversized, and non-UTF-8 files.
- Text, JSON, and Markdown reports, `--tag`, `--format`, `--output`, and
  `--version` flags, and `python -m todo_scan` support.
