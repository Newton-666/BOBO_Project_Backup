# Bobo Agent

A personal AI agent that lives across your knowledge — Obsidian, Notion, email, GitHub, Jira, and any custom API. One agent, one chat, all your tools.

```bash
pip install bobo-agent
# Or from source: git clone ... && pip install -e .
mkdir -p ~/.bobo
echo "DEEPSEEK_API_KEY=***" > ~/.bobo/.env
bobo
```

## What Makes Bobo Unique

### Cross-Platform Knowledge

Bobo is the only agent that can search, read, write, and link across Obsidian, Notion, email, and GitHub simultaneously:

- `cross_search("API redesign")` — searches Obsidian + Notion + email at once, returns labeled results
- `copy_to_obsidian(page_id)` — copies a Notion page into your Obsidian vault as markdown
- `copy_to_notion(filepath)` — copies an Obsidian note into Notion
- `append_obsidian("note", "See also: [[Other Note]]")` — links notes within Obsidian
- `notion_append(page_id, content)` — links pages within Notion

### Connect Any Service Without Writing Code

Register any REST API in one command — no Python needed:

```
api_register(name="jira", base_url="https://company.atlassian.net/rest/api/3",
             auth_type="bearer", auth_key="xxx",
             endpoints='[{"name":"search","method":"GET","path":"/search?jql={query}"}]')
```

Then `api_call(api="jira", endpoint="search", params='{"query":"tasks"}')` — same as any built-in tool. Bobo automatically discovers and advertises registered APIs to the LLM on every call.

### Built-in tools (60+)

| Category | Tools |
|----------|-------|
| Knowledge | `cross_search`, `search_obsidian`, `notion_search`, `search_emails`, `save_memory` |
| Code | `code_execution`, `file_writer`, `execute_terminal`, `search_code`, `github_create_repo`, `github_create_pr`, `github_pr_diff`, `git_status` |
| Files | `read_local_file`, `list_directory`, `file_operation` |
| Web | `web_search`, `web_fetch`, `web_extract` |
| macOS | `send_notification`, `read_clipboard`, `write_clipboard`, `set_reminder`, `create_calendar_event` |
| GitHub | `github_setup`, `github_check_auth`, `github_create_repo`, `github_create_pr`, `github_pr_diff`, `github_pr_comment` |
| Custom API | `api_register`, `api_call` — connect any REST service dynamically |
| Rollback | `restore_checkpoint` — undo file writes |

### Autonomous Coding

- **Auto-run**: After writing a `.py` file, Bobo runs it automatically and reports output/errors
- **Error enrichment**: Tracebacks are summarized as `[TypeError] file.py:42` before the LLM sees them
- **Auto-diff**: Git diff is captured after every file write and injected into the next LLM call
- **Parallel execution**: Independent tools run simultaneously, not sequentially

### Privacy & Security

- **Secret redaction**: API keys, tokens, passwords are replaced with `[REDACTED]` before reaching the LLM
- **Tool gating**: Tools with unmet prerequisites are invisible to the LLM — no Obsidian tools if no vault configured
- **Blocked folders**: Obsidian `Private/`, `Archive/` folders are never read, written, or searched
- **Atomic session writes**: `tmp → rename → bak` — session files never corrupt on crash
- **No telemetry**: Zero data leaves your machine except the LLM API calls you configure

### Performance

- **Tool filtering**: Only relevant tools (~10-20) are sent per query instead of all 60
- **Grep-based search**: Obsidian search is 50x faster using `grep -ril` instead of Python `os.walk`
- **Context compression**: 1400-message sessions compress to ~10 messages before the first API call
- **Streaming**: Tokens arrive word-by-word, not as a single block after 20 seconds
- **Parallel execution**: Multiple independent tools run simultaneously

### Architecture

```
bobo (CLI entry point)
  └── ui-tui/              Hermes TUI frontend (React/Ink/TypeScript)
        └── spawns python -m bobo_tui_gateway.entry
              └── bobo_tui_gateway/    JSON-RPC gateway (stdin/stdout)
                    ├── entry.py       Main loop + signal handling + setup wizard
                    ├── server.py      RPC method handlers + engine dispatch
                    └── transport.py   Thread-safe stdout writer
              └── core/     Agent engine (modular ~340 LOC each)
                    ├── engine.py      Conversation loop, state machine
                    ├── context.py     History compression, query classification
                    ├── tool_runner.py Tool execution, error enrichment, rollback
                    ├── llm_caller.py  API caller with streaming + retry
                    ├── provider.py    7 built-in providers (DeepSeek, OpenAI, Anthropic...)
                    └── session_manager.py  Atomic session persistence
              └── tools/    60 tool plugins (auto-discovered)
                    └── __init__.py    Auto-discovery with prerequisite gating
```

### Multi-Provider

Supports DeepSeek, OpenAI, Anthropic, OpenRouter, Google, Ollama, and custom endpoints. Switch by setting `BOBO_PROVIDER` in `.env`.

## Adding a Tool

Drop a new file in `tools/` with a `register()` function. To gate behind a prerequisite, add `check_fn`:

```python
_check = lambda: bool(os.environ.get("MY_CONFIG", ""))

def register(reg):
    reg("my_tool", execute_func, schema, check_fn=_check)
```

## License

MIT
