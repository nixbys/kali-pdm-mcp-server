#!/usr/bin/env python3
"""Gate on govulncheck's JSON output, but only fail for vulnerabilities not
on the accepted allowlist (.github/govulncheck-allowlist.txt).

Why this exists: govulncheck has no built-in ignore-list, and this project
has a handful of known, currently-unfixable vulnerabilities in transitive
dependencies (see the allowlist file's own comments for each one's
justification). Without this, the govulncheck CI job would be permanently
red for reasons nobody can act on, which trains everyone to ignore it --
exactly what an "only fail on something new" gate is meant to prevent.

Usage: check-govulncheck.py <govulncheck-json-output-file> <allowlist-file>

govulncheck's `-json` mode writes a stream of pretty-printed JSON objects
concatenated with no separator (not one-object-per-line, so a naive
line-by-line json.loads will not work) -- decode with a raw_decode loop
instead. Only findings with at least one trace frame that names a
"function" are treated as real, call-graph-reachable vulnerabilities,
matching govulncheck's own text-mode "Vulnerability #N" list (its exit
code -- 3 if any such finding exists -- reflects the same distinction:
a vulnerability that's merely imported or required, with no traced call
into it, does not fail the build).
"""

import json
import sys


def load_findings(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    decoder = json.JSONDecoder()
    idx, n = 0, len(content)
    findings = []
    while idx < n:
        while idx < n and content[idx] in " \n\t\r":
            idx += 1
        if idx >= n:
            break
        obj, end = decoder.raw_decode(content, idx)
        idx = end
        if "finding" in obj:
            findings.append(obj["finding"])
    return findings


def load_allowlist(path):
    ids = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.add(line)
    return ids


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <govulncheck-json-file> <allowlist-file>", file=sys.stderr)
        return 2

    findings = load_findings(sys.argv[1])
    allowed = load_allowlist(sys.argv[2])

    reachable_ids = set()
    for finding in findings:
        if any("function" in frame for frame in finding.get("trace", [])):
            reachable_ids.add(finding["osv"])

    unexpected = sorted(reachable_ids - allowed)
    accepted = sorted(reachable_ids & allowed)

    if accepted:
        print("Reachable vulnerabilities on the accepted allowlist (see .github/govulncheck-allowlist.txt):")
        for osv in accepted:
            print(f"  - {osv}: https://pkg.go.dev/vuln/{osv}")

    if unexpected:
        print("\n::error::govulncheck found reachable vulnerabilities not on the accepted allowlist:")
        for osv in unexpected:
            print(f"  - {osv}: https://pkg.go.dev/vuln/{osv}")
        print(
            "\nEither this is fixable now (bump the affected dependency) or it "
            "needs a reviewed addition to .github/govulncheck-allowlist.txt with "
            "a justification -- see that file's own header comment."
        )
        return 1

    print("\nNo new reachable vulnerabilities outside the accepted allowlist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
