# 🤖 Qwen Coder MCP Server

> **One interface, two brains** — use Claude Desktop to control both Claude and your local Qwen.

```
Claude Desktop
    │
    ├── "design the architecture"  →  Claude thinks (smart, paid)
    │
    └── "ask Qwen to write CRUD"   →  Qwen codes (fast, free)
            │
            ▼
      MCP Server (this project)
            │  • Model Selection — switch models on the fly
            │  • Streaming — real-time responses
            ▼
      Your Qwen API (OpenAI-compatible)
```

## ✨ Features

- **Model Selection** — switch Qwen models dynamically with task-based recommendations
- **Streaming Response** — real-time output via progress notifications (no more waiting)
- **7+ coding tools** — generate, edit, review, explain, test code through Qwen

## 🚀 Install

```powershell
# Clone/download this project, then:
cd qwen-mcp-server
.\install.ps1
```

Or manually:
```powershell
python -m venv venv
venv\Scripts\pip.exe install -e .
```

## ⚙️ Configure Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "qwen-coder": {
      "command": "C:\\...\\qwen-mcp-server\\venv\\Scripts\\python.exe",
      "args": ["C:\\...\\qwen-mcp-server\\qwen_mcp\\server.py"],
      "env": {
        "QWEN_BASE_URL": "https://your-endpoint.com/v1",
        "QWEN_API_KEY": "sk-your-key",
        "QWEN_MODEL": "qwen2.5-coder",
        "QWEN_TIMEOUT": "300"
      }
    }
  }
}
```

Then **restart Claude Desktop**.

## 🛠️ Tools (10)

### Model Selection Tools

| Tool | Purpose | Example prompt |
|------|---------|----------------|
| `select_qwen_model` | Switch active model at runtime | "switch Qwen to qwen2.5-coder:32b" |
| `recommend_qwen_model` | Get model recommendations by task | "which Qwen model is best for code review?" |
| `get_active_model` | Check which model is active | "what model is Qwen using now?" |

### Coding Tools (with streaming)

| Tool | Purpose | Example prompt |
|------|---------|----------------|
| `ask_qwen` | General Q&A | "ask Qwen how to implement WebSocket in FastAPI" |
| `qwen_generate_code` | Generate new code | "have Qwen write a REST API for user management" |
| `qwen_edit_code` | Edit existing code | "send this code to Qwen, add error handling" |
| `qwen_review_code` | Code review | "have Qwen review this code for security issues" |
| `qwen_explain_code` | Explain code | "ask Qwen to explain this function" |
| `qwen_write_tests` | Write tests | "have Qwen write pytest tests for this class" |

### Utility Tools

| Tool | Purpose | Example prompt |
|------|---------|----------------|
| `list_qwen_models` | Check connection & list models | "what models are available on Qwen?" |

## 🔄 Model Selection

Switch models on the fly — no restart needed:

```
You: "switch Qwen to qwen2.5-coder:32b for this complex refactoring"
You: "recommend a model for writing tests"
You: "what model is Qwen using right now?"
```

### Task Profiles

| Task Type | Top Pick | Use Case |
|-----------|----------|----------|
| `code-generation` | qwen2.5-coder:14b | Writing new code, CRUD, utilities |
| `code-review` | qwen2.5-coder:14b | Reviewing, finding bugs, security |
| `code-explanation` | qwen2.5:14b | Explaining code, documentation |
| `general-qa` | qwen2.5:14b | Questions, brainstorming |
| `refactoring` | qwen2.5-coder:14b | Refactoring, optimization |
| `testing` | qwen2.5-coder:14b | Unit tests, integration tests |
| `fast-draft` | qwen2.5-coder:7b | Quick drafts, simple tasks |
| `complex-reasoning` | qwen2.5-coder:32b | Deep reasoning, architecture |

## ⚡ Streaming Response

All coding tools support **streaming by default**. Claude Desktop receives
progress notifications as Qwen generates each chunk — you see the answer
building up in real-time instead of waiting for the entire response.

- **Enabled by default**: All tools stream unless `stream=false` is passed
- **Graceful fallback**: If streaming fails, falls back to non-streaming
- **Progress updates**: Each chunk sent via MCP progress notifications

## 💡 Usage Patterns

### Let Qwen handle routine coding
> "Have Qwen generate a SQLAlchemy model for users table with email, name, created_at"

### Claude thinks, Qwen implements
> "Design the architecture for a chat app, then have Qwen implement each module"

### Qwen drafts, Claude reviews
> "Ask Qwen to write the authentication middleware, then review what it wrote"

### Smart model selection
> "Switch to the 32b model and have Qwen refactor this entire module"
> "Use a fast model — have Qwen write a quick utility function"

### Cost optimization
> "Have Qwen write tests for all functions in this file"

## 🔌 API Compatibility

Works with any **OpenAI-compatible** API endpoint:

| Provider | Base URL |
|----------|----------|
| Ollama | `http://localhost:11434/v1` |
| LM Studio | `http://localhost:1234/v1` |
| vLLM | `http://localhost:8000/v1` |
| Together AI | `https://api.together.xyz/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Any OpenAI-compat | `https://your-server/v1` |

## 📁 Project Structure

```
qwen-mcp-server/
├── pyproject.toml          # Project config & dependencies
├── install.ps1             # Auto install script
├── .env.example            # Environment variables reference
├── README.md               # This file
└── qwen_mcp/
    ├── __init__.py
    └── server.py           # MCP server (10 tools)
```

## License

MIT
