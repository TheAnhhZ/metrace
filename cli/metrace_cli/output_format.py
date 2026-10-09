# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Plain-text tables or JSON, so the CLI works in scripts and on stage."""

import json
from collections.abc import Iterable, Sequence
from typing import Any

import typer


def emit_json(data: Any) -> None:
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    rows = [["" if cell is None else str(cell) for cell in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(headers)]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True))
    typer.echo(line)
    typer.echo("  ".join("-" * w for w in widths))
    for row in rows:
        typer.echo("  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True)))
    if not rows:
        typer.echo("(none)")
