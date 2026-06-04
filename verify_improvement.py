import asyncio
import json
import os
import sys
from pathlib import Path

os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
os.environ["no_proxy"] = "127.0.0.1,localhost,::1"

import tiktoken
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

ENC = tiktoken.get_encoding("cl100k_base")


def tokens_of(tools) -> int:
    total = 0
    for t in tools:
        obj = {"name": t.name, "description": t.description or "", "inputSchema": t.inputSchema or {}}
        total += len(ENC.encode(json.dumps(obj, separators=(",", ":"))))
    return total


async def list_stdio(command, args, env):
    params = StdioServerParameters(command=command, args=args or [], env={**os.environ, **(env or {})})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return (await session.list_tools()).tools


async def list_http(url, headers):
    async with streamablehttp_client(url, headers=headers or None) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return (await session.list_tools()).tools


async def main():
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".mcpproxy" / "mcp_config.json"
    cfg = json.loads(cfg_path.read_text())
    listen = cfg.get("listen", "127.0.0.1:8080")
    proxy_url = f"http://{listen}/mcp/"

    print("BASELINE — what the client would load without the proxy:")
    baseline = []
    for s in cfg.get("mcpServers", []):
        if s.get("enabled") is False:
            continue
        name = s.get("name", "?")
        try:
            if s.get("protocol") == "http" or s.get("url"):
                tools = await list_http(s["url"], s.get("headers"))
            else:
                tools = await list_stdio(s.get("command"), s.get("args"), s.get("env"))
            print(f"  {name:<16} tools={len(tools):>3}  tokens={tokens_of(tools):>6}")
            baseline += tools
        except Exception as e:
            print(f"  {name:<16} SKIPPED ({e})")
    b = tokens_of(baseline)
    print(f"  {'TOTAL':<16} tools={len(baseline):>3}  tokens={b:>6}")

    print(f"\nGATEWAY — what the client loads via mcpproxy ({proxy_url}):")
    gw = await list_http(proxy_url, None)
    g = tokens_of(gw)
    print(f"  exposed tools={len(gw)}  tokens={g}")

    saved = b - g
    pct = (saved / b * 100) if b else 0
    print(f"\nRESULT: {b} -> {g} tokens  (saved {saved}, {pct:.1f}% reduction)")
    if saved <= 0:
        print("NOTE: gateway isn't smaller — too few downstream tools, or you forgot 'serve --disable-management'.")


if __name__ == "__main__":
    asyncio.run(main())
