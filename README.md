# todo-scan

Scan a project tree for `TODO`, `FIXME`, `HACK`, `XXX`, and `NOTE` comments and
print them as a readable report.

The tool is a heuristic comment scanner, not a full language parser. That keeps
it small and dependency-free, at the cost of occasional false positives inside
strings or unusual comment dialects. Usage, install steps, and those limitations
are documented in the sections below as the project grows.
