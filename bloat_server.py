import asyncio
import sys

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "svc"

VERBS = ["create", "update", "delete", "list", "get", "search", "sync", "export", "import", "validate"]
NOUNS = ["invoice", "customer", "order", "ticket", "report", "dashboard", "webhook", "pipeline", "dataset", "alert", "contact", "campaign"]


def make_tools(n):
    tools = []
    for i in range(n):
        v = VERBS[i % len(VERBS)]
        no = NOUNS[(i // len(VERBS)) % len(NOUNS)]
        tools.append(types.Tool(
            name=f"{PREFIX}_{v}_{no}_{i}",
            description=(f"{v.capitalize()} a {no} in the {PREFIX} service. Accepts an identifier plus "
                        f"optional fields and returns the affected {no} record together with its metadata "
                        f"and timestamps. Use this when the user asks to {v} {no} data in {PREFIX}."),
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": f"Unique identifier of the {no} to {v}."},
                    "fields": {"type": "object", "description": "Optional key/value fields to set on the record."},
                    "limit": {"type": "number", "description": "Maximum number of records to return for list/search."},
                },
                "required": ["id"],
            },
        ))
    return tools


TOOLS = make_tools(N)
app = Server(f"bloat-{PREFIX}")


@app.list_tools()
async def list_tools():
    return TOOLS


@app.call_tool()
async def call_tool(name, arguments):
    return [types.TextContent(type="text", text=f"ok: {name}")]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
