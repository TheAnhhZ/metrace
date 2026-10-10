# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Build docs/license-declaration.{md,csv} from the real dependency trees and fail
when a license is outside the allow-list (docs/license-policy.md).

Input: JSON from pip-licenses (per Python project) and package-lock.json. npm
packages come from the lock file, not from the installed tree: npm installs only
the native builds for the current OS/CPU, so an installed tree differs between a
laptop and CI, while the lock file names every build that can be installed.
Usage: scripts/generate-license-inventory.sh (wraps the tool calls).
"""

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# OSI-approved identifiers we accept (plus documented equivalents).
ALLOWED = {
    "MIT",
    "MIT-0",
    "MIT-CMU",
    "ISC",
    "0BSD",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Apache-2.0",
    "MPL-2.0",
    "LGPL-2.1-only",
    "LGPL-2.1-or-later",
    "LGPL-3.0-only",
    "LGPL-3.0-or-later",
    "PostgreSQL",
    "Zlib",
    "Python-2.0",
    "PSF-2.0",
    "CC0-1.0",
    "Unlicense",
    "BlueOak-1.0.0",
    "OFL-1.1",
    "EPL-2.0",
    "HPND",
}
DENIED = {"BUSL-1.1", "SSPL-1.0", "Elastic-2.0", "FSL-1.1-MIT", "FSL-1.1-Apache-2.0", "CC-BY-4.0", "Commons-Clause"}
# Classifier-style names from Python metadata -> SPDX.
ALIASES = {
    "MIT License": "MIT",
    "BSD License": "BSD-3-Clause",
    "Apache Software License": "Apache-2.0",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "Python Software Foundation License": "PSF-2.0",
    "Apache Software License; BSD License": "Apache-2.0 OR BSD-3-Clause",
    "ISC License (ISCL)": "ISC",
    "GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0-only",
}
# Reference rows (standalone services and data used at runtime, not shipped in the repo).
REFERENCE = [
    ("Keycloak", "26.8.0", "service", "Apache-2.0", "https://github.com/keycloak/keycloak"),
    ("Apache APISIX", "3.19.0", "service", "Apache-2.0", "https://github.com/apache/apisix"),
    ("PostgreSQL", "17", "service", "PostgreSQL", "https://www.postgresql.org/"),
    ("SeaweedFS", "4.48", "service", "Apache-2.0", "https://github.com/seaweedfs/seaweedfs"),
    ("Flowable REST", "8.0.0", "service", "Apache-2.0", "https://github.com/flowable/flowable-engine"),
    ("nginx", "1.29", "service", "BSD-2-Clause", "https://nginx.org/"),
    ("Ollama (optional)", "latest", "service", "MIT", "https://github.com/ollama/ollama"),
    ("Qwen3-4B weights (optional)", "qwen3:4b", "model", "Apache-2.0", "https://huggingface.co/Qwen/Qwen3-4B"),
    ("Noto Sans", "2022", "font", "OFL-1.1", "https://github.com/notofonts/latin-greek-cyrillic"),
]


def spdx(raw: str) -> str:
    raw = (raw or "UNKNOWN").strip()
    if raw in ALIASES:
        return ALIASES[raw]
    if raw.startswith("(") and raw.endswith(")"):  # npm style "(MIT OR CC0-1.0)"
        raw = raw[1:-1]
    return ALIASES.get(raw, raw)


def allowed(expression: str) -> bool:
    """`A OR B` needs one allowed side; `A AND B` needs both; WITH exceptions keep the base id."""
    if expression in DENIED:
        return False
    alternatives = re.split(r"\s+OR\s+", expression.replace("(", "").replace(")", ""))
    return any(
        all(part.split(" WITH ")[0].strip() in ALLOWED for part in re.split(r"\s+AND\s+", alt)) for alt in alternatives
    )


def python_rows(project: str, payload: list[dict], runtime: set[str]) -> list[dict]:
    return [
        {
            "module": p["Name"],
            "version": p["Version"],
            "kind": "python",
            "scope": "runtime" if p["Name"].lower() in runtime else "dev",
            "license": spdx(p["License"]),
            "source": p.get("URL") or f"https://pypi.org/project/{p['Name']}/",
            "where": project,
        }
        for p in payload
        if p["Name"].lower() not in {"metrace-api", "metrace-cli"}
    ]


def node_rows(lock_file: Path) -> list[dict]:
    rows, seen = [], set()
    marker = "node_modules/"
    for path, entry in sorted(json.loads(lock_file.read_text())["packages"].items()):
        if marker not in path or entry.get("link"):  # root and workspaces are our own code
            continue
        name, version = entry.get("name") or path.rsplit(marker, 1)[1], entry.get("version")
        if not version or (name, version) in seen:
            continue
        seen.add((name, version))
        scope = "dev (build only)" if entry.get("dev") or entry.get("devOptional") else "runtime"
        if entry.get("os") or entry.get("cpu"):
            scope += ", per OS/CPU"
        rows.append(
            {
                "module": name,
                "version": version,
                "kind": "npm",
                "scope": scope,
                "license": spdx(entry.get("license") or "UNKNOWN"),
                "source": f"https://www.npmjs.com/package/{name}",
                "where": "apps/web",
            }
        )
    return rows


def main(python_dir: Path) -> int:
    rows = []
    for payload_file in sorted(python_dir.glob("*.pip.json")):
        project = payload_file.name.removesuffix(".pip.json")
        runtime = set((python_dir / f"{project}.runtime.txt").read_text().lower().split())
        rows += python_rows(project, json.loads(payload_file.read_text()), runtime)
    rows += node_rows(ROOT / "package-lock.json")
    rows += [
        {
            "module": m,
            "version": v,
            "kind": k,
            "scope": "reference (not in repo)",
            "license": lic,
            "source": url,
            "where": "runtime",
        }
        for m, v, k, lic, url in REFERENCE
    ]
    rows.sort(key=lambda r: (r["kind"], r["module"].lower()))
    for row in rows:
        row["osi"] = "yes" if allowed(row["license"]) else "NO"
    with (ROOT / "docs" / "license-declaration.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            lineterminator="\n",
            fieldnames=["module", "version", "kind", "scope", "license", "osi", "source", "where"],
        )
        writer.writeheader()
        writer.writerows(rows)
    # REUSE-IgnoreStart (header text written into the generated file, not this file's license)
    lines = [
        "<!--",
        "SPDX-FileCopyrightText: The metrace Authors",
        "SPDX-License-Identifier: Apache-2.0",
        # REUSE-IgnoreEnd
        "-->",
        "",
        "# License declaration",
        "",
        "Generated by `scripts/generate-license-inventory.sh` from the lock files. Policy: "
        "[license-policy.md](license-policy.md). Machine-readable: `license-declaration.csv`.",
        "",
        "npm rows marked *per OS/CPU* are native builds of one tool (esbuild, rollup, SWC,",
        "Tailwind, Lightning CSS): the lock file names one per platform and npm installs",
        "only the one matching the machine. All of them are checked against the allow-list.",
        "",
        f"{len(rows)} entries; licenses outside the allow-list: {sum(r['osi'] == 'NO' for r in rows)}.",
        "",
        "| Module | Version | Kind | Scope | License (SPDX) | OSI |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {r['module']} | {r['version']} | {r['kind']} | {r['scope']} | {r['license']} | {r['osi']} |" for r in rows
    ]
    (ROOT / "docs" / "license-declaration.md").write_text("\n".join(lines) + "\n")
    bad = [r for r in rows if r["osi"] == "NO"]
    for r in bad:
        print(f"NOT ALLOWED: {r['module']} {r['version']} ({r['license']}) in {r['where']}", file=sys.stderr)
    print(f"{len(rows)} entries written, {len(bad)} not allowed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
