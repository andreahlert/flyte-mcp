<p align="center">
  <img src="https://raw.githubusercontent.com/flyteorg/static-resources/main/common/flyte_circle_gradient_1_primary.svg" width="80" alt="Flyte" />
</p>

<h1 align="center">flyte-mcp</h1>

<p align="center">
  <strong>Flyte V2 knowledge, patterns, plugins, and runtime &mdash; exposed to every AI coding assistant via the Model Context Protocol.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/flyte-mcp/"><img src="https://img.shields.io/pypi/v/flyte-mcp?color=6f2aef&label=PyPI&logo=pypi&logoColor=white" alt="PyPI"/></a>
  <a href="https://pypi.org/project/flyte-mcp/"><img src="https://img.shields.io/pypi/pyversions/flyte-mcp?color=3776ab&logo=python&logoColor=white" alt="Python"/></a>
  <a href="https://pypi.org/project/flyte-mcp/"><img src="https://img.shields.io/pypi/dm/flyte-mcp?color=22c55e&label=downloads" alt="Downloads"/></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-compatible-7c3aed?logo=anthropic&logoColor=white" alt="MCP"/></a>
  <a href="https://github.com/andreahlert/flyte-mcp/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="License"/></a>
  <a href="https://github.com/andreahlert/flyte-mcp/stargazers"><img src="https://img.shields.io/github/stars/andreahlert/flyte-mcp?style=flat&color=f59e0b" alt="Stars"/></a>
</p>

<p align="center">
  <img src="assets/demo.svg" alt="Claude Code using flyte-mcp" width="820" />
</p>

<h2 align="center">Install in one click</h2>

<p align="center">
  <a href="https://cursor.com/install-mcp?name=flyte&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJmbHl0ZS1tY3AiXX0%3D">
    <img src="https://img.shields.io/badge/Install_in-Cursor-000000?style=for-the-badge&logo=cursor&logoColor=white" alt="Install in Cursor"/>
  </a>
  &nbsp;
  <a href="vscode:mcp/install?%7B%22name%22%3A%22flyte%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22flyte-mcp%22%5D%7D">
    <img src="https://img.shields.io/badge/Install_in-VS_Code-007ACC?style=for-the-badge&logo=visualstudiocode&logoColor=white" alt="Install in VS Code"/>
  </a>
  &nbsp;
  <a href="vscode-insiders:mcp/install?%7B%22name%22%3A%22flyte%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22flyte-mcp%22%5D%7D">
    <img src="https://img.shields.io/badge/Install_in-VS_Code_Insiders-24bfa5?style=for-the-badge&logo=visualstudiocode&logoColor=white" alt="Install in VS Code Insiders"/>
  </a>
</p>

<p align="center">
  <strong>Claude Code</strong>
</p>

```bash
claude mcp add flyte -- uvx flyte-mcp
```

<p align="center">
  <strong>Claude Desktop / any MCP client</strong>
</p>

```json
{
  "mcpServers": {
    "flyte": {
      "command": "uvx",
      "args": ["flyte-mcp"]
    }
  }
}
```

Add this to `~/.claude.json`, `~/.cursor/mcp.json`, or your client's config file.

---

## Why it exists

Ask any AI assistant "write a Flyte V2 task with caching and 4 GPUs" and you get confidently wrong code: V1 imports, invented decorators, hallucinated resource kwargs. The assistant has no reliable channel into the Flyte ecosystem, so it fills the gap with training-data guesses.

`flyte-mcp` is that channel. It ships a versioned knowledge pack built directly from the `flyte-sdk` source tree and the [Flyte Plugin Registry](https://github.com/andreahlert/flyte-plugin-registry), plus a thin runtime bridge for executing tasks when a cluster is configured. The assistant stops guessing and starts answering.

## What your assistant can do

| Capability | Tools |
|---|---|
| **Learn the V2 API** | `get_flyte_symbol` &middot; `search_flyte_api` &middot; `list_flyte_symbols` |
| **Find canonical examples** | `find_flyte_example_for` &middot; `get_flyte_pattern` &middot; `list_flyte_patterns` |
| **Pick the right plugin** | `suggest_flyte_plugin_for` &middot; `list_flyte_plugins` &middot; `get_flyte_plugin` |
| **Port V1 code to V2** | `migrate_v1_to_v2` |
| **Get oriented** | `get_flyte_overview` &middot; `get_flyte_features` &middot; `get_flyte_install_guide` &middot; `get_flyte_version` |
| **Run on a cluster** | `run_flyte_task` &middot; `get_flyte_execution_status` &middot; `list_flyte_recent_runs` |

All tools are pure Python, stdio transport, zero network calls unless you explicitly use the runtime bridge.

## Example prompts that just work

- *How do I cache a task and invalidate on input change?*
- *Show me a distributed PyTorch training example with A100s.*
- *Which Flyte plugin do I use for Snowflake, and what's the import?*
- *Migrate this flytekit V1 workflow to V2.*
- *What's the signature of `TaskEnvironment`?*

Your assistant picks the right tools and assembles accurate answers.

## Rebuilding the knowledge pack

Contributors and release automation can regenerate the pack from source:

```bash
python scripts/build_knowledge.py \
  --sdk-path /path/to/flyte-sdk \
  --registry /path/to/flyte-plugin-registry/src/data/plugins.json \
  --out src/flyte_mcp/data/flyte-v2-knowledge.json
```

Sources used:
- `flyte-sdk/src/flyte/__init__.py` &mdash; public symbols via AST
- `flyte-sdk/examples/*` &mdash; canonical patterns by theme
- `flyte-sdk/README.md`, `FEATURES.md`, `CONTRIBUTING.md` &mdash; meta docs
- `flyte-plugin-registry` &mdash; curated plugin catalog

`flytesnacks` is intentionally excluded: V2 consolidated examples in-tree.

## Relationship to other Flyte MCP projects

- **[wherobots/flyte-mcp](https://github.com/wherobots/flyte-mcp)** &mdash; runtime-only. Discovers and executes tasks on a deployed Flyte instance via API key. Complementary, not competing.
- **[unionai/claude-agents-public](https://github.com/unionai/claude-agents-public)** &mdash; Claude Code custom agents (system prompts, not an MCP server). Compose freely.

This project focuses on **authoring**: the moment a developer types a prompt asking about Flyte.

## Roadmap

- GitHub Action to auto-rebuild the knowledge pack on every `flyte-sdk` release
- Listing in the official [MCP Registry](https://registry.modelcontextprotocol.io)
- Local semantic search via small sentence-transformer model
- AST-based migration codemod (replacing the current regex pass)
- Log streaming tool (`get_flyte_execution_logs`) with tail support

## License

Apache-2.0 &mdash; same license as Flyte itself.

## Disclaimer

Independent community project. Not officially affiliated with or endorsed by [Flyte](https://github.com/flyteorg/flyte) or [Union.ai](https://union.ai). The Flyte name and logo are trademarks of their respective owners.
