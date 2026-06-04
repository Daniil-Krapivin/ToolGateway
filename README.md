# MCP tool context reduction with mcpproxy

Connecting a lot of of MCP servers to a client like opencode results in descriptions overloading the model's context before any work even begins.

mcpproxy gets around it: your client talks to one proxy that keeps all the tools
behind a single `retrieve_tools` search. The model only goes looking when it
actually needs a tool.

## What I've measured

| Setup | Tools the client loads | Tool-def tokens |
|---|---|---|
| Direct (9 servers, 756 tools) | 756 | **92,828** |
| Via mcpproxy `--disable-management` | 6 | **1,854** |
| | | **98% smaller** |

That ~1,850-token cost is fixed; it doesn't grow as you add servers. A
`retrieve_tools` call pulls back ~2,000 tokens, and only when the model searches.

## Set-up

1. Install.
   <https://github.com/smart-mcp-proxy/mcpproxy-go/releases> 
   and put `mcpproxy` on your PATH.

2. Add servers:
   ```bash
   mcpproxy upstream add github -- npx -y @modelcontextprotocol/server-github
   mcpproxy upstream add notion https://mcp.notion.com/sse
   ```

3. Run with `--disable-management`:
   ```bash
   mcpproxy serve -l 127.0.0.1:8080 --disable-management
   ```
   ! Leave --disable-management flag off and it exposes about ten of its own tools, which cancels most
   of the saving !

4. Approve the tools once:
   ```bash
   mcpproxy upstream approve <server>      # run for each server
   ```

5. Point your client at the proxy, then delete the direct servers (leave them in and
   you load both):
   - opencode: run `mcpproxy connect opencode`, then remove the old `mcp` entries
     from `~/.config/opencode/opencode.json`. Use `http://127.0.0.1:8080/mcp'
   - Cline: Didn't test Cline, so check its docs.

## Check the improvement

`verify_improvement.py` reads your `~/.mcpproxy/mcp_config.json`, connects to every
server directly (baseline) and to the proxy (gateway), and prints the saving.

```bash
python verify_improvement.py
```

Example output:
```
RESULT: 92828 -> 1854 tokens  (saved 90974, 98.0% reduction)
```

## Stress test (optional)

`bloat_server.py` is a fake MCP server that exposes N tools, handy for recreating the
"too many tools" situation:

```bash
mcpproxy upstream add crm --no-quarantine -- python bloat_server.py 120 crm
# add, restart mcpproxy, then run verify_improvement.py
```

## Good to know

- `--disable-management` is the flag that actually matters (step 3).
- Approving tools (step 4) is a separate thing from quarantine, and you always have
  to do it. Run it again whenever a server gains new tools.
- Behind a corporate proxy, set `NO_PROXY=127.0.0.1,localhost` so your client's
  call to the proxy doesn't get routed through it.
