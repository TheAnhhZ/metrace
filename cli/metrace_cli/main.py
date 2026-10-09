# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""`metrace` command line: login (device flow), whoami, trace, shipments, incidents.

Every command calls the same /api/v1 as the web app, through the gateway.
"""

from enum import StrEnum

import typer

from metrace_cli import auth_device_flow as auth
from metrace_cli.api_client import ApiError, get, post, require_internal
from metrace_cli.output_format import emit_json, table

app = typer.Typer(no_args_is_help=True, help="metrace: trace cooking batches, lots and shipments.")
shipments = typer.Typer(no_args_is_help=True, help="Shipments of cooked food.")
incidents = typer.Typer(no_args_is_help=True, help="Food-safety incidents.")
drill = typer.Typer(no_args_is_help=True, help="Recall drills (dry run: nothing is locked).")
app.add_typer(shipments, name="shipments")
app.add_typer(incidents, name="incidents")
app.add_typer(drill, name="drill")


class NodeType(StrEnum):
    supplier = "supplier"
    lot = "lot"
    batch = "batch"
    shipment = "shipment"
    delivery_point = "delivery_point"
    asset = "asset"


class Direction(StrEnum):
    forward = "forward"
    backward = "backward"
    both = "both"


def _fail(exc: Exception) -> None:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.command()
def login() -> None:
    """Sign in through the browser (device authorization grant). Staff accounts only."""

    def show(url: str, code: str) -> None:
        typer.echo(f"Open {url}\nand confirm the code: {code}")

    try:
        auth.save_tokens(auth.device_login(show))
        me = get("/whoami")
        require_internal(me)
    except (ApiError, RuntimeError) as exc:
        auth.clear_tokens()
        _fail(exc)
    typer.secho(f"Logged in as {me['username']} ({', '.join(me['roles'])})", fg=typer.colors.GREEN)


@app.command()
def logout() -> None:
    """Forget the cached tokens."""
    auth.clear_tokens()
    typer.echo("Logged out.")


@app.command()
def whoami(as_json: bool = typer.Option(False, "--json")) -> None:
    """Who the API thinks you are."""
    try:
        me = get("/whoami")
    except (ApiError, RuntimeError) as exc:
        _fail(exc)
    if as_json:
        return emit_json(me)
    table(
        ["username", "roles", "organizations"], [[me["username"], ",".join(me["roles"]), ",".join(me["organizations"])]]
    )


@app.command()
def trace(
    node_type: NodeType,
    ref: str = typer.Argument(..., help="UUID or business code, e.g. LOT-20261008-XUONG-LON"),
    direction: Direction = typer.Option(Direction.forward, "--direction", "-d"),
    depth: int = typer.Option(8, "--depth", min=1, max=12),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Walk the lineage graph from a node (same endpoint as the web graph)."""
    try:
        result = get(f"/lineage/{node_type.value}/{ref}", direction=direction.value, max_depth=depth)
    except (ApiError, RuntimeError) as exc:
        _fail(exc)
    if as_json:
        return emit_json(result)
    table(
        ["depth", "type", "label", "status", "locked", "portions"],
        [
            [n["depth"], n["type"], n["label"], n.get("status"), "LOCKED" if n["locked"] else "", n.get("portions")]
            for n in result["nodes"]
        ],
    )
    if result["truncated"]:
        typer.secho("Result truncated: walk hit the depth/node cap.", fg=typer.colors.YELLOW)


@shipments.command("list")
def list_shipments(
    status: str | None = typer.Option(None, help="planned | ready | held | dispatched | delivered"),
    day: str | None = typer.Option(None, help="service date YYYY-MM-DD (default today)"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Shipments of a service day, optionally only one status (e.g. --status held)."""
    try:
        rows = [s for s in get("/shipments", day=day) if status is None or s["status"] == status]
    except (ApiError, RuntimeError) as exc:
        _fail(exc)
    if as_json:
        return emit_json(rows)
    table(
        ["code", "point", "slot", "status", "items", "blockers"],
        [
            [
                s["code"],
                s["delivery_point"],
                s["meal_slot"],
                s["status"],
                len(s["items"]),
                ",".join(b["code"] for b in s["blockers"]),
            ]
            for s in rows
        ],
    )


@incidents.command("list")
def list_incidents(as_json: bool = typer.Option(False, "--json")) -> None:
    """Incidents, newest first."""
    try:
        rows = get("/incidents")
    except (ApiError, RuntimeError) as exc:
        _fail(exc)
    if as_json:
        return emit_json(rows)
    table(
        ["code", "status", "escalated", "opened_by", "title"],
        [[i["code"], i["status"], "yes" if i["escalated"] else "", i["opened_by"], i["title"]] for i in rows],
    )


@drill.command("run")
def run_drill(node_type: NodeType, ref: str, as_json: bool = typer.Option(False, "--json")) -> None:
    """How fast could we find and stop everything downstream of this node?"""
    try:
        result = post("/recall-drills", {"type": node_type.value, "ref": ref})
    except (ApiError, RuntimeError) as exc:
        _fail(exc)
    if as_json:
        return emit_json(result)
    preview = result["lock_preview"] or {}
    typer.echo(result["label"])
    table(
        ["total ms", "lots", "batches", "shipments", "points", "would hold", "already out", "coverage %"],
        [
            [
                result["total_ms"],
                *result["forward"].values(),
                preview.get("would_hold"),
                preview.get("already_out"),
                result["coverage"]["coverage_pct"],
            ]
        ],
    )
    typer.echo(f"Audit anchor: #{result['audit_anchor']['seq']} {result['audit_anchor']['hash'][:16]}…")
