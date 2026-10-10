# Job Postings MCP Server + Gemini Frontend

A complete, production-minded example of a **Model Context Protocol (MCP)** server built with the official Python SDK, exposing useful tools over a sample job-postings dataset, plus a **Next.js visual frontend** that lets any user chat with Gemini while calling the same tools.

**Public repo:** https://github.com/andylaique/job-mcp-gemini-frontend

---

## What’s included

### MCP Server (`mcp-server/`)

Built with the official [`mcp`](https://github.com/modelcontextprotocol/python-sdk) Python SDK (v2).

| Tool | Description |
|------|-------------|
| `search_postings_by_skill` | Search postings by skill (case-insensitive). Optional `remote_only` and `limit`. |
| `count_postings_by_company` | Count postings per company (optionally filter by name). |
| `get_job_details` | Full details for a single job by numeric ID. |
| `list_companies` | Sorted list of all unique companies. |

- **Typed inputs** via Pydantic / type hints → automatic JSON Schema for clients.
- **Clear tool descriptions** from docstrings (what the model reads).
- **Input validation** with helpful `ValueError` messages for empty strings, unknown IDs, etc.
- Dataset: 12 realistic job postings in `data/jobs.json`.

### Frontend (`frontend/`)

- Next.js (App Router) + Tailwind dark UI.
- Chat interface powered by **Gemini** (function calling).
- Same four tools re-implemented in TypeScript so the web UI works without requiring a live MCP process.
- Paste a Gemini API key in the UI or set `GEMINI_API_KEY` in `.env.local`.

---

## Quick start – MCP server

```bash
cd mcp-server
# Python 3.10+
pip install "mcp[cli]"
# or: uv add "mcp[cli]"

# Run over stdio (for Claude Desktop / MCP Inspector)
python server.py
# or: uv run mcp run server.py

# Run over Streamable HTTP (stretch goal)
uv run mcp run server.py --transport streamable-http
# → http://localhost:8000/mcp
```

### Test it works (in-memory client)

```bash
cd mcp-server
pip install mcp anyio
python test_client.py
```

You should see tool listings and successful calls for Python search, company counts, and job details, plus expected errors for bad input.

### MCP Inspector

```bash
uv run mcp dev server.py
```

Open the printed URL, go to the **Tools** tab, and call `search_postings_by_skill` with `skill=Python`.

### Claude Desktop / Cursor config example

```json
{
  "mcpServers": {
    "job-postings": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-server/server.py"]
    }
  }
}
```

---

## Quick start – Frontend

```bash
cd frontend
cp .env.example .env.local
# Edit .env.local and add:
# GEMINI_API_KEY=your_key_from_https://aistudio.google.com/apikey

npm install
npm run dev
```

Open http://localhost:3000. You can also paste a key in the UI without restarting.

Example questions:

- “Find me Python jobs that are remote”
- “How many postings does TechNova Inc have?”
- “Show details for job ID 6”
- “List all companies”

Tool calls and their results are shown under the assistant’s reply.

---

## Proof that the MCP server works

1. **Automated:** `python mcp-server/test_client.py` exercises every tool and validates error paths.
2. **Interactive:** `uv run mcp dev server.py` → MCP Inspector UI (screenshot the Tools tab after a successful call).
3. **HTTP:** `uv run mcp run server.py --transport streamable-http` then point any MCP client (or the Python `Client("http://localhost:8000/mcp")`) at it.

(Replace this paragraph with an actual screenshot/video of the Inspector or Claude Desktop calling the tools when you record one.)

---

## How we would protect the server with OAuth 2.0

This section describes the security design we would implement for a production deployment of the HTTP transport. It is **not** fully coded in this repo (the local/demo path stays open for ease of testing), but the design follows the current MCP authorization specification and OAuth 2.1.

### Chosen flow

**Authorization Code flow with PKCE** (public or confidential clients).

- Required by the MCP authorization spec for interactive clients (Claude Desktop, IDEs, web apps, agents acting on behalf of a user).
- PKCE protects against authorization-code interception.
- For pure machine-to-machine (no human) we would additionally support the **Client Credentials** grant (or JWT Bearer assertions) with a restricted scope set.

The MCP server acts purely as an **OAuth 2.1 Resource Server**. Token issuance, user login, and consent live on a separate **Authorization Server** (Auth0, Keycloak, Cognito, or a self-hosted OIDC provider).

### Where tokens are checked

On **every** HTTP request to the MCP endpoint (`/mcp` or the Streamable HTTP surface):

1. Extract `Authorization: Bearer <access_token>`.
2. If missing or malformed → `401 Unauthorized` + `WWW-Authenticate` header pointing at the Protected Resource Metadata endpoint (`/.well-known/oauth-protected-resource`).
3. Validate the JWT (or introspect the opaque token):
   - Signature against the AS JWKS.
   - `iss` matches the expected Authorization Server.
   - `aud` (audience) contains this MCP server’s resource identifier (RFC 8707 Resource Indicators). Reject tokens that were issued for a different API.
   - `exp` has not passed.
   - Optional: `nbf`, `jti` replay checks.
4. Extract scopes from the token (`scope` claim or equivalent).
5. Map the requested MCP operation (tool call, resource read, …) to the required scope(s). If the token lacks the needed scope → `403` with `insufficient_scope`.

The official Python SDK already ships helpers under `mcp.server.auth` and client-side `OAuthClientProvider` for the Streamable HTTP transport; we would wire the resource-server validation middleware into the ASGI/Starlette stack that serves the MCP endpoint.

### Scopes we would define

| Scope | Purpose |
|-------|---------|
| `mcp:tools:list` | List available tools (read-only discovery). |
| `mcp:tools:call` | Invoke any tool (`search_postings_by_skill`, `count_…`, etc.). |
| `mcp:tools:call:search` | Optionally finer-grained: only the search tool. |
| `mcp:tools:call:count` | Only the count tool. |
| `mcp:resources:read` | Read resources (if we later expose the raw dataset as a resource). |
| `offline_access` | Standard refresh-token scope. |

A typical interactive client would request `mcp:tools:list mcp:tools:call offline_access`. Machine clients using client-credentials would be issued only the scopes they need and with short TTLs.

### Additional hardening

- Advertise Protected Resource Metadata (RFC 9728) so clients can discover the correct Authorization Server.
- Require `resource` parameter (RFC 8707) on authorization/token requests so tokens are audience-bound.
- Never accept tokens that were issued for a different resource (token-passthrough prevention).
- Rate-limit per client / per user.
- Log authentication failures without leaking token material.
- For the stretch “check a token on every request” path we would add the validation middleware shown above and run the server exclusively over Streamable HTTP behind TLS.

---

## Project layout

```
.
├── data/
│   └── jobs.json              # Sample dataset (12 postings)
├── mcp-server/
│   ├── server.py              # MCPServer + 4 tools
│   ├── test_client.py         # In-memory proof
│   └── pyproject.toml
├── frontend/
│   ├── src/app/               # Next.js App Router
│   │   ├── page.tsx           # Chat UI
│   │   └── api/chat/route.ts  # Gemini + tool execution
│   ├── src/lib/tools.ts       # TypeScript mirror of the MCP tools
│   └── .env.example
└── README.md
```

---

## Stretch goals status

- [x] Run the server over HTTP (`--transport streamable-http`).
- [ ] Full OAuth token check on every request (design documented above; can be added with the SDK’s auth helpers).
- [ ] Small Rust program that reads the same `jobs.json` (left as a future exercise; the dataset is plain JSON so any language can consume it).

---

## License

MIT
