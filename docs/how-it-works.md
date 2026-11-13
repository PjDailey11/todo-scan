# How todo-scan works

todo-scan is a small pipeline of plain functions. Each stage lives in its own
module so it can be tested alone and replaced without touching the others.

```
project path
   │
   ▼
directory_walker.iter_source_files      sorted list of files, tool dirs and
   │                                    gitignored paths skipped
   │
   ▼
directory_walker.filter_files_by_suffix optional suffix allow-list
   │
   ▼
scanner.scan_source_file                per file: size/binary/UTF-8 checks,
   │                                    comment detection, tag matching
   ▼
report.format_*_report                  text, JSON, or Markdown
```

`project_scan.scan_project_tree` wires the first three stages together and is
the library entry point the CLI calls.

## 1. Walking the tree

`iter_source_files` does an explicit stack-based walk instead of `os.walk` so
the skip rules are easy to read in one place:

- Directories whose **basename** is in `DEFAULT_EXCLUDED_DIRECTORY_NAMES`
  (`.git`, `node_modules`, `.venv`, `dist`, and so on) are never entered.
  Names are compared exactly, not as glob patterns.
- **Symlinks are never followed.** A link can point outside the project or
  back to a parent and cause a loop; a comment scanner should stay inside the
  tree it was given.
- Unreadable directories are skipped rather than aborting the whole scan.
- The result is **sorted**, so reports are stable across filesystems that
  return directory entries in different orders.

If the path is a single file, it is returned on its own and neither the
exclude list nor `.gitignore` applies.

### .gitignore support

`gitignore_rules.load_gitignore_rules` reads the `.gitignore` at the project
root and `parse_gitignore_lines` turns each line into a `GitignoreRule`. The
walker asks `is_path_ignored` about every directory and file, using a
root-relative path with `/` separators. Supported syntax:

| Pattern | Meaning |
| --- | --- |
| `# comment`, blank line | ignored |
| `*.log`, `secrets.txt` | basename match at any depth (`fnmatch` wildcards) |
| `generated/` | directories only; files named `generated` are kept |
| `/local.cfg`, `docs/drafts` | anchored to the project root (any slash except a trailing one) |
| `!keep.log` | re-include; the **last** matching rule wins |
| `\#file`, `\!file` | literal leading `#` or `!` |

An ignored directory is pruned, so a later `!` rule cannot re-include a file
inside it; git behaves the same way. Matching is case-sensitive.

Not supported (by design, to keep the module small): nested `.gitignore`
files in subdirectories, `.git/info/exclude` and the global excludes file,
git's `**` semantics (anchored `*` may cross `/`, which is slightly looser
than git), and escaped trailing spaces. A missing, unreadable, or non-UTF-8
`.gitignore` is treated as empty rather than failing the scan. Pass
`--no-gitignore` to skip this stage entirely.

## 2. Filtering by suffix

`filter_files_by_suffix` is optional. With no allow-list every discovered file
moves on and the scanner itself ignores suffixes it has no comment style for.
With an allow-list, comparison is case-insensitive so `.PY` and `.py` behave
the same.

## 3. Scanning one file

`scan_source_file` rejects files that are not worth reading before decoding
them:

- larger than 1 MiB (minified bundles, lockfiles),
- a NUL byte in the first 8 KiB (images, compiled objects),
- not valid UTF-8.

The comment style is picked from the file suffix (`#`, `//` and `/* */`,
`<!-- -->`, `--`, `;`). Only text inside a comment is searched for tags. The
`//` detector ignores `://` so URLs such as `https://example.com/TODO` are not
reported.

## 4. Matching tags

`tag_pattern.build_tag_search_pattern` compiles one regular expression for the
whole tag allow-list. Tags match case-insensitively as whole words, with an
optional colon, and the rest of the comment becomes the message. Matches are
normalized to uppercase in the `TaggedComment` record so reports can group
them without re-normalizing.

## 5. Reporting

`report.py` turns the list of `TaggedComment` values into:

- **text**: `path:line: TAG message`, the grep/compiler shape most editors make
  clickable;
- **json**: always an array (empty when there are no matches) so other tools
  never need a special case;
- **markdown**: one `##` heading per file with a bullet per match.

Paths are shown relative to the project root when possible.

## Known limitations

The scanner is a heuristic, not a parser. A tag inside a string literal can
match when that string also contains a comment delimiter, and languages with
unusual comment syntax are not recognized yet.
