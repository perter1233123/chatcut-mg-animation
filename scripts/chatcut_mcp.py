#!/usr/bin/env python3
"""Minimal stdio client for the ChatCut Desktop MCP server.

Use this when ChatCut's MCP tools are not loaded into the session. Every run is
a new MCP session, so bind the project with --project before project-scoped work.

    python3 chatcut_mcp.py list-tools --filter motion
    python3 chatcut_mcp.py schema create_motion_graphic_from_code
    python3 chatcut_mcp.py call read_project --project b6b76095
    python3 chatcut_mcp.py call preview_timeline --project b6b76095 \
        --json '{"views":["viewer"],"viewerFrames":[240,620]}' --save-images /tmp/frames
    python3 chatcut_mcp.py batch calls.json
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys

DEFAULT_SHIM = os.path.expanduser(
    "~/Library/Application Support/ChatCut/chatcut-mcp"
)


class ChatCut:
    """One MCP session against the ChatCut Desktop shim."""

    def __init__(self, shim: str = DEFAULT_SHIM, project: str | None = None) -> None:
        env = dict(os.environ)
        env["CHATCUT_MCP_CLIENT"] = "codex_app"
        self.proc = subprocess.Popen(
            [shim],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            text=True,
            bufsize=1,
        )
        self._id = 0
        self.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "chatcut-mg-animation", "version": "1.0"},
            },
        )
        self.notify("notifications/initialized", {})
        if project:
            result = self.call("target_project", {"projectId": project})
            print(_text(result), file=sys.stderr, flush=True)

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _read(self, want_id: int) -> dict:
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("ChatCut MCP server closed the connection")
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == want_id:
                if "error" in message:
                    raise RuntimeError(json.dumps(message["error"], ensure_ascii=False))
                return message

    def request(self, method: str, params: dict) -> dict:
        request_id = self._next_id()
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        return self._read(request_id)

    def notify(self, method: str, params: dict) -> None:
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def call(self, tool: str, args: dict | None = None) -> dict:
        return self.request(
            "tools/call", {"name": tool, "arguments": args or {}}
        ).get("result", {})

    def list_tools(self) -> list[dict]:
        return self.request("tools/list", {}).get("result", {}).get("tools", [])

    def close(self) -> None:
        try:
            self.proc.kill()
        except Exception:
            pass


def _text(result: dict) -> str:
    if not isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)
    blocks = result.get("content")
    if blocks:
        return "\n".join(
            block.get("text", "") for block in blocks if block.get("type") == "text"
        )
    return json.dumps(result, ensure_ascii=False)


def _save_images(result: dict, directory: str, stem: str) -> list[str]:
    blocks = result.get("content") if isinstance(result, dict) else None
    saved = []
    if not blocks:
        return saved
    os.makedirs(directory, exist_ok=True)
    for index, block in enumerate(b for b in blocks if b.get("type") == "image"):
        path = os.path.join(directory, f"{stem}_{index + 1}.png")
        with open(path, "wb") as handle:
            handle.write(base64.b64decode(block["data"]))
        saved.append(path)
    return saved


def _load_args(raw: str | None, path: str | None) -> dict:
    if path:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    if not raw:
        return {}
    if raw.startswith("@"):
        with open(raw[1:], encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(raw)


def main() -> int:
    # Shared options use SUPPRESS defaults so they can be given before or after
    # the subcommand without the subparser overwriting an earlier value.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default=argparse.SUPPRESS,
                        help="project id/prefix to target first")
    common.add_argument("--save-images", default=argparse.SUPPRESS,
                        help="directory for image result blocks")

    parser = argparse.ArgumentParser(description="ChatCut Desktop MCP stdio client")
    parser.add_argument("--shim", default=DEFAULT_SHIM)
    parser.add_argument("--project", default=None, help="project id/prefix to target first")
    parser.add_argument("--save-images", default=None, help="directory for image result blocks")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list-tools", help="list tool names and descriptions",
                                 parents=[common])
    list_parser.add_argument("--filter", default="", help="substring filter")

    schema_parser = sub.add_parser("schema", help="print one tool's input schema",
                                   parents=[common])
    schema_parser.add_argument("tool")

    call_parser = sub.add_parser("call", help="call one tool", parents=[common])
    call_parser.add_argument("tool")
    call_parser.add_argument("--json", help="arguments as JSON, or @path/to.json")
    call_parser.add_argument("--json-file", help="arguments loaded from a JSON file")

    batch_parser = sub.add_parser("batch", help="run several tool calls in one session",
                                  parents=[common])
    batch_parser.add_argument("file", help="JSON list, or {project, calls}")

    args = parser.parse_args()
    project = getattr(args, "project", None)
    save_images = getattr(args, "save_images", None)

    if args.command == "schema":
        client = ChatCut(args.shim)
        try:
            for tool in client.list_tools():
                if tool["name"] == args.tool:
                    print(json.dumps(tool, ensure_ascii=False, indent=2))
                    break
            else:
                print(f"unknown tool: {args.tool}", file=sys.stderr)
                return 1
        finally:
            client.close()
        return 0

    if args.command == "list-tools":
        client = ChatCut(args.shim)
        try:
            needle = args.filter.lower()
            for tool in client.list_tools():
                name = tool["name"]
                description = (tool.get("description") or "").split("\n")[0]
                if needle and needle not in name.lower() and needle not in description.lower():
                    continue
                print(f"{name} | {description[:110]}")
        finally:
            client.close()
        return 0

    if args.command == "call":
        client = ChatCut(args.shim, project)
        try:
            result = client.call(args.tool, _load_args(args.json, args.json_file))
            print(_text(result))
            if save_images:
                for path in _save_images(result, save_images, args.tool):
                    print(f"saved image: {path}", file=sys.stderr)
        finally:
            client.close()
        return 0

    with open(args.file, encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        project = project or payload.get("project")
        calls = payload.get("calls", [])
    else:
        calls = payload

    client = ChatCut(args.shim, project)
    try:
        for index, entry in enumerate(calls):
            tool = entry["tool"]
            result = client.call(tool, entry.get("args", {}))
            print(f"=== [{index}] {tool} ===")
            print(_text(result))
            if save_images:
                for path in _save_images(result, save_images, f"{index}_{tool}"):
                    print(f"saved image: {path}", file=sys.stderr)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
