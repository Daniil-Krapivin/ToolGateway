# Slimming MCP tool context with mcpproxy

Connect a handful of MCP servers to a client like opencode or Cline and every tool
description lands in the model's context before you've typed anything. With a big
toolset, that alone can eat most of your context window.

mcpproxy gets around it: your client talks to one proxy that keeps all the tools
behind a single `retrieve_tools` search. The model only goes looking when it
actually needs a tool.

## What we measured

| Setup | Tools the client loads | Tool-def tokens |
|---|---|---|
| Direct (9 servers, 756 tools) | 756 | **92,828** |
| Via mcpproxy `--disable-management` | 6 | **1,854** |
| | | **98% smaller** |

That ~1,850-token cost is fixed; it doesn't grow as you add servers. A
`retrieve_tools` call pulls back ~2,000 tokens, and only when the model searches.
So instead of paying for every tool up front, you pay a little, and only when it's
relevant.

## Set up mcpproxy

1. Install it. Grab a build from
   <https://github.com/smart-mcp-proxy/mcpproxy-go/releases> (or `brew`/`apt`/`dnf`)
   and put `mcpproxy` on your PATH.

2. Add your servers:
   ```bash
   mcpproxy upstream add github -- npx -y @modelcontextprotocol/server-github
   mcpproxy upstream add notion https://mcp.notion.com/sse
   ```

3. Run it with `--disable-management`:
   ```bash
   mcpproxy serve -l 127.0.0.1:8080 --disable-management
   ```
   Leave that flag off and it exposes about ten of its own tools, which cancels most
   of the saving.

4. Approve the tools once. They start out blocked:
   ```bash
   mcpproxy upstream approve <server>      # run for each server
   ```

5. Point your client at the proxy, then delete the direct servers (leave them in and
   you load both):
   - opencode: run `mcpproxy connect opencode`, then remove the old `mcp` entries
     from `~/.config/opencode/opencode.json`. Use `http://127.0.0.1:8080/mcp`, with
     no trailing slash.
   - Cline: add a remote (streamable HTTP) server pointing at
     `http://127.0.0.1:8080/mcp?apikey=<key>` (run `mcpproxy status` for the key),
     then remove the direct servers. We didn't test Cline, so check its docs.

## Check the improvement yourself

`verify_improvement.py` reads your `~/.mcpproxy/mcp_config.json`, connects to every
server directly (baseline) and to the proxy (gateway), and prints the saving. You
don't need an API key.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python verify_improvement.py
```

Example output:
```
RESULT: 92828 -> 1854 tokens  (saved 90974, 98.0% reduction)
```

## Reproduce the stress test (optional)

`bloat_server.py` is a fake MCP server that exposes N tools, handy for recreating the
"too many tools" situation:

```bash
mcpproxy upstream add crm --no-quarantine -- python bloat_server.py 120 crm
# add a few more (billing, support, ...), restart mcpproxy, then run verify_improvement.py
```

## Good to know

- `--disable-management` is the flag that actually matters (step 3).
- Approving tools (step 4) is a separate thing from quarantine, and you always have
  to do it. Run it again whenever a server gains new tools.
- Behind a corporate HTTP proxy, set `NO_PROXY=127.0.0.1,localhost` so your client's
  call to the proxy doesn't get routed through it.
