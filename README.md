# flyte-mcp

MCP server exposing Flyte V2 SDK knowledge, plugin registry, and optional runtime control to AI assistants (Claude Desktop, Claude Code, Cursor).

Gives IDE-embedded AI accurate, versioned answers about Flyte V2 without scraping READMEs or hallucinating import paths.

## Tools

### Overview & meta
| Tool | Purpose |
|---|---|
| `get_flyte_version` | Knowledge pack info (SDK version, counts) |
| `get_flyte_overview` | Full flyte-sdk README |
| `get_flyte_features` | FEATURES.md capability list |
| `get_flyte_install_guide` | CLI help + pip install + quickstart snippet |

### Python API
| Tool | Purpose |
|---|---|
| `list_flyte_symbols` | Public API inventory (optional kind filter) |
| `get_flyte_symbol` | Signature, params, docstring, module |
| `search_flyte_api` | Keyword search over symbols |

### Example patterns
| Tool | Purpose |
|---|---|
| `list_flyte_patterns` | Canonical example themes from `flyte-sdk/examples/` |
| `get_flyte_pattern` | README + code snippets for a theme |
| `find_flyte_example_for` | Natural-language match over example themes |

### Plugin registry
| Tool | Purpose |
|---|---|
| `list_flyte_plugins` | All plugins (optional category filter) |
| `get_flyte_plugin` | Plugin detail by slug |
| `suggest_flyte_plugin_for` | Natural-language plugin recommendation, prefers V2 |

### Migration
| Tool | Purpose |
|---|---|
| `migrate_v1_to_v2` | Rewrite flytekit V1 code to flyte-sdk V2 syntax |

### Runtime (requires `flyte` installed + configured)
| Tool | Purpose |
|---|---|
| `run_flyte_task` | Submit task to configured cluster |
| `get_flyte_execution_status` | Fetch run status by id |
| `list_flyte_recent_runs` | Recent runs |

## Install

```bash
pip install flyte-mcp
# or
uvx flyte-mcp
```

## Use with Claude Code / Claude Desktop

`~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "flyte": {
      "type": "stdio",
      "command": "uvx",
      "args": ["flyte-mcp"]
    }
  }
}
```

Cursor `~/.cursor/mcp.json` same shape.

## Rebuilding the knowledge pack

```bash
python scripts/build_knowledge.py \
  --sdk-path /path/to/flyte-sdk \
  --registry /path/to/flyte-plugin-registry/src/data/plugins.json \
  --out src/flyte_mcp/data/flyte-v2-knowledge.json
```

Sources:
- `flyte-sdk/src/flyte/__init__.py` - public symbols
- `flyte-sdk/examples/<theme>/` - canonical patterns
- `flyte-sdk/README.md`, `FEATURES.md`, `CONTRIBUTING.md` - meta docs
- `flyte-sdk/.venv/bin/flyte --help` - CLI surface (if available)
- `flyte-plugin-registry` plugins.json - plugin catalog

`flytesnacks` is intentionally excluded: V2 consolidated examples in-tree.

## Roadmap

- CI: auto-rebuild knowledge pack on each flyte-sdk release
- Semantic search via local embeddings (Transformers.js / small model)
- Richer codemod (AST-based, not just regex)
- Log streaming tool (`get_flyte_execution_logs`)

## License

Apache-2.0
