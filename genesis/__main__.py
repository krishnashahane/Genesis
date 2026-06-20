"""Genesis CLI.

Usage:
    genesis serve                 # start the REST API + Web UI
    genesis run "<goal>"          # run the full execution loop once, print result
    genesis health                # print runtime health as JSON
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from genesis.config import get_settings
from genesis.core.runtime import Runtime


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="genesis", description="Genesis agent OS")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("serve", help="Run the API server and Web UI")
    sub.add_parser("health", help="Print runtime health")

    run = sub.add_parser("run", help="Execute the loop for a goal")
    run.add_argument("goal", help="The goal to accomplish")
    return p


async def _run_goal(goal: str) -> int:
    rt = Runtime()
    await rt.start()
    try:
        result = await rt.run_goal(goal)
        print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))
    finally:
        await rt.stop()
    return 0


async def _health() -> int:
    rt = Runtime()
    await rt.start()
    try:
        print(json.dumps(rt.health(), indent=2, default=str))
    finally:
        await rt.stop()
    return 0


def _serve() -> int:
    import uvicorn

    s = get_settings()
    uvicorn.run("genesis.api.app:app", host=s.api_host, port=s.api_port, reload=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "serve":
        return _serve()
    if args.command == "run":
        return asyncio.run(_run_goal(args.goal))
    if args.command == "health":
        return asyncio.run(_health())
    return 1


if __name__ == "__main__":
    sys.exit(main())
