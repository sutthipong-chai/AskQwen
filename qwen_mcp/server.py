"""
Qwen Coder MCP Server
=====================
MCP Server connects Claude Desktop → Local Qwen via OpenAI-compatible API.
One interface, two brains — use Claude for thinking, Qwen for coding.

Compatible with: MCP Python SDK v2
API format:     OpenAI-compatible (/v1/chat/completions)

Features:
  • Model Selection — switch Qwen models on the fly with smart recommendations
  • Streaming Response — real-time output via progress notifications
"""

import os
import json
from mcp.server.mcpserver import MCPServer, Context
import httpx

# ============================================================
# Configuration
# ============================================================
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "http://localhost:11434/v1")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "no-key")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen2.5-coder:14b")
TIMEOUT_SECONDS = int(os.getenv("QWEN_TIMEOUT", "300"))

# ============================================================
# Runtime State — active model (mutable)
# ============================================================
_active_model: str = QWEN_MODEL

# ============================================================
# Model Recommendation Registry
# ============================================================
MODEL_PROFILES: dict[str, dict] = {
    "code-generation": {
        "recommended": ["qwen2.5-coder:14b", "qwen2.5-coder:7b", "qwen2.5-coder:32b"],
        "description": "Best for writing new code, CRUD, boilerplate, utilities",
        "temperature": 0.2,
    },
    "code-review": {
        "recommended": ["qwen2.5-coder:14b", "qwen2.5-coder:32b", "qwen2.5:14b"],
        "description": "Best for reviewing code, finding bugs, security audit",
        "temperature": 0.3,
    },
    "code-explanation": {
        "recommended": ["qwen2.5:14b", "qwen2.5:7b", "qwen2.5-coder:14b"],
        "description": "Best for explaining code, documentation, teaching",
        "temperature": 0.3,
    },
    "general-qa": {
        "recommended": ["qwen2.5:14b", "qwen2.5:7b", "qwen2.5:32b"],
        "description": "Best for general questions, brainstorming, discussion",
        "temperature": 0.5,
    },
    "refactoring": {
        "recommended": ["qwen2.5-coder:14b", "qwen2.5-coder:32b"],
        "description": "Best for refactoring, optimization, architectural changes",
        "temperature": 0.1,
    },
    "testing": {
        "recommended": ["qwen2.5-coder:14b", "qwen2.5-coder:7b"],
        "description": "Best for writing unit tests, integration tests",
        "temperature": 0.2,
    },
    "fast-draft": {
        "recommended": ["qwen2.5-coder:7b", "qwen2.5-coder:3b", "qwen2.5:7b"],
        "description": "Fast responses for quick drafts, simple tasks",
        "temperature": 0.3,
    },
    "complex-reasoning": {
        "recommended": ["qwen2.5-coder:32b", "qwen2.5:32b", "qwen2.5:14b"],
        "description": "Complex problems requiring deep reasoning",
        "temperature": 0.2,
    },
}


# ============================================================
# OpenAI-compatible API caller (non-streaming, legacy)
# ============================================================
async def _call_qwen(
    messages: list[dict],
    model: str = "",
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """Call Qwen via OpenAI-compatible /v1/chat/completions (non-streaming)."""
    use_model = model if model else _active_model
    url = f"{QWEN_BASE_URL.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {QWEN_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


# ============================================================
# Streaming API caller — sends progress notifications
# ============================================================
async def _call_qwen_stream(
    messages: list[dict],
    ctx: Context,
    model: str = "",
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """
    Call Qwen with streaming enabled.
    Sends each chunk via ctx.report_progress() so Claude Desktop
    can display the answer in real-time.
    Returns the full concatenated response.
    """
    use_model = model if model else _active_model
    url = f"{QWEN_BASE_URL.rstrip('/')}/chat/completions"

    collected_chunks: list[str] = []
    chunk_count = 0

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        async with client.stream(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {QWEN_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]  # strip "data: "
                if data.strip() == "[DONE]":
                    break

                try:
                    chunk_json = json.loads(data)
                    delta = chunk_json["choices"][0].get("delta", {})
                    content = delta.get("content", "")

                    if content:
                        collected_chunks.append(content)
                        chunk_count += 1
                        full_so_far = "".join(collected_chunks)

                        # Send progress notification with accumulated text
                        await ctx.report_progress(
                            progress=chunk_count,
                            total=None,  # unknown total
                            message=full_so_far,
                        )
                except (json.JSONDecodeError, KeyError, IndexError):
                    # Skip malformed chunks silently
                    continue

    return "".join(collected_chunks)


# ============================================================
# MCP Server + Tools
# ============================================================
mcp = MCPServer(
    name="qwen-coder",
    description="Route coding tasks to local Qwen — save Claude tokens. "
    "Supports model selection and streaming responses.",
    instructions=(
        "You have access to a local Qwen model via these MCP tools. "
        "To significantly save Claude tokens and optimize costs, ALWAYS prioritize delegating "
        "code generation, boilerplate, CRUD implementations, refactoring, and unit test writing "
        "to Qwen using the appropriate tool (such as qwen_generate_code, qwen_edit_code, "
        "ask_qwen, or qwen_write_tests) instead of writing the code yourself. "
        "Use Claude's intelligence primarily for architectural planning, high-level design, "
        "reasoning, and reviewing Qwen's generated code, unless the user explicitly requests "
        "Claude to write the code directly."
    ),
)


# ────────────────────────────────────────────────────────────
# Model Selection Tools
# ────────────────────────────────────────────────────────────
@mcp.tool()
async def select_qwen_model(model_name: str) -> str:
    """
    Switch the active Qwen model at runtime.
    All subsequent tool calls will use the newly selected model
    until changed again.

    Args:
        model_name: Full model name, e.g. "qwen2.5-coder:14b", "qwen2.5:7b".
    """
    global _active_model
    previous = _active_model
    _active_model = model_name
    return (
        f"✅ Model switched successfully\n"
        f"   Previous: {previous}\n"
        f"   Active:   {_active_model}\n\n"
        f"All tools will now use **{_active_model}**."
    )


@mcp.tool()
async def recommend_qwen_model(
    task_type: str = "",
) -> str:
    """
    Get model recommendations for a specific task type.
    Also shows the currently active model.

    Args:
        task_type: Type of task. Options: code-generation, code-review,
                   code-explanation, general-qa, refactoring, testing,
                   fast-draft, complex-reasoning.
                   Leave empty to see all profiles.
    """
    lines = [
        f"🎯 Active model: **{_active_model}**",
        f"📡 Endpoint: {QWEN_BASE_URL}\n",
    ]

    if task_type and task_type in MODEL_PROFILES:
        profile = MODEL_PROFILES[task_type]
        lines.append(f"## Recommendation for: {task_type}")
        lines.append(f"📋 {profile['description']}")
        lines.append(f"🌡️ Suggested temperature: {profile['temperature']}")
        lines.append("\n📦 Recommended models (best → good):")
        for i, m in enumerate(profile["recommended"], 1):
            marker = " ← active" if m == _active_model else ""
            lines.append(f"  {i}. `{m}`{marker}")
        lines.append(
            f"\n💡 Use `select_qwen_model` to switch, e.g.:\n"
            f'   select_qwen_model(model_name="{profile["recommended"][0]}")'
        )
    else:
        lines.append("## Available Task Profiles\n")
        for key, profile in MODEL_PROFILES.items():
            top_model = profile["recommended"][0]
            active_marker = " ✅" if top_model == _active_model else ""
            lines.append(f"  • **{key}**: {profile['description']}")
            lines.append(f"    Top pick: `{top_model}`{active_marker}")
        lines.append(
            "\n💡 Call with a task_type to get detailed recommendations.\n"
            "   Example: recommend_qwen_model(task_type=\"code-generation\")"
        )

    return "\n".join(lines)


@mcp.tool()
async def get_active_model() -> str:
    """
    Check which Qwen model is currently active.
    Returns the model name and endpoint info.
    """
    return (
        f"🎯 Active model: **{_active_model}**\n"
        f"📡 Endpoint: {QWEN_BASE_URL}\n"
        f"⏱️ Timeout: {TIMEOUT_SECONDS}s\n"
        f"🔑 API Key: {'configured' if QWEN_API_KEY != 'no-key' else 'not set (using no-key)'}"
    )


# ────────────────────────────────────────────────────────────
# Core Tools (with streaming support)
# ────────────────────────────────────────────────────────────
@mcp.tool()
async def ask_qwen(prompt: str, model: str = "", stream: bool = True, ctx: Context = None) -> str:
    """
    Send any prompt to Qwen — general questions, code generation, explanations.
    Supports streaming for real-time responses.

    Args:
        prompt: The question or instruction for Qwen.
        model: (optional) Override default model name.
        stream: (optional) Enable streaming response (default: True).
    """
    messages = [
        {"role": "system", "content": "You are an expert programmer. Be concise and precise."},
        {"role": "user", "content": prompt},
    ]

    if stream and ctx is not None:
        return await _call_qwen_stream(messages=messages, ctx=ctx, model=model)
    else:
        return await _call_qwen(messages=messages, model=model)


@mcp.tool()
async def qwen_edit_code(
    code: str,
    instruction: str,
    language: str = "",
    model: str = "",
    stream: bool = True,
    ctx: Context = None,
) -> str:
    """
    Send code to Qwen for editing — refactor, fix bugs, add features.
    Supports streaming for real-time responses.

    Args:
        code: The original source code to edit.
        instruction: What changes to make.
        language: (optional) Programming language, e.g. python, typescript.
        model: (optional) Override default model name.
        stream: (optional) Enable streaming response (default: True).
    """
    lang_hint = f" ({language})" if language else ""
    messages = [
        {
            "role": "system",
            "content": f"You are an expert programmer. Edit code{lang_hint} according to instructions. "
            "Return ONLY the modified code inside a code block. Do not explain.",
        },
        {
            "role": "user",
            "content": f"## Instruction\n{instruction}\n\n## Original Code\n```{language}\n{code}\n```",
        },
    ]

    if stream and ctx is not None:
        return await _call_qwen_stream(
            messages=messages, ctx=ctx, model=model, temperature=0.1, max_tokens=8192
        )
    else:
        return await _call_qwen(
            messages=messages, model=model, temperature=0.1, max_tokens=8192
        )


@mcp.tool()
async def qwen_generate_code(
    description: str,
    language: str = "python",
    model: str = "",
    stream: bool = True,
    ctx: Context = None,
) -> str:
    """
    Have Qwen generate new code from a description — boilerplate, CRUD, utilities.
    Supports streaming for real-time responses.

    Args:
        description: What code to generate.
        language: Programming language (default: python).
        model: (optional) Override default model name.
        stream: (optional) Enable streaming response (default: True).
    """
    messages = [
        {
            "role": "system",
            "content": f"You are an expert {language} programmer. Generate production-ready code with "
            "proper error handling, type hints, and docstrings. Return ONLY the code inside a code block.",
        },
        {"role": "user", "content": description},
    ]

    if stream and ctx is not None:
        return await _call_qwen_stream(
            messages=messages, ctx=ctx, model=model, max_tokens=8192
        )
    else:
        return await _call_qwen(messages=messages, model=model, max_tokens=8192)


@mcp.tool()
async def qwen_review_code(
    code: str,
    language: str = "",
    focus: str = "",
    stream: bool = True,
    ctx: Context = None,
) -> str:
    """
    Have Qwen review code — find bugs, suggest improvements, check security.
    Supports streaming for real-time responses.

    Args:
        code: The code to review.
        language: (optional) Programming language.
        focus: (optional) Review focus, e.g. "security", "performance", "readability".
        stream: (optional) Enable streaming response (default: True).
    """
    focus_hint = f"\nFocus especially on: {focus}" if focus else ""
    messages = [
        {
            "role": "system",
            "content": f"You are a senior code reviewer. Be concise and actionable.{focus_hint}",
        },
        {
            "role": "user",
            "content": (
                f"Review this {language} code:\n\n```{language}\n{code}\n```\n\n"
                "Provide:\n1. 🐛 Bugs or potential issues\n2. 🔒 Security concerns\n"
                "3. ⚡ Performance improvements\n4. 📝 Code quality suggestions\n5. ✅ What's done well"
            ),
        },
    ]

    if stream and ctx is not None:
        return await _call_qwen_stream(
            messages=messages, ctx=ctx, model="", temperature=0.3
        )
    else:
        return await _call_qwen(messages=messages, temperature=0.3)


@mcp.tool()
async def qwen_explain_code(
    code: str,
    language: str = "",
    stream: bool = True,
    ctx: Context = None,
) -> str:
    """
    Have Qwen explain code — understand unfamiliar codebases.
    Supports streaming for real-time responses.

    Args:
        code: The code to explain.
        language: (optional) Programming language.
        stream: (optional) Enable streaming response (default: True).
    """
    messages = [
        {
            "role": "system",
            "content": "Explain code clearly and concisely. Include: what it does (overview), "
            "how it works (step by step), key patterns or techniques used.",
        },
        {"role": "user", "content": f"```{language}\n{code}\n```"},
    ]

    if stream and ctx is not None:
        return await _call_qwen_stream(
            messages=messages, ctx=ctx, model="", temperature=0.3
        )
    else:
        return await _call_qwen(messages=messages, temperature=0.3)


@mcp.tool()
async def qwen_write_tests(
    code: str,
    language: str = "python",
    framework: str = "",
    stream: bool = True,
    ctx: Context = None,
) -> str:
    """
    Have Qwen write unit tests — save Claude tokens on routine work.
    Supports streaming for real-time responses.

    Args:
        code: The code to write tests for.
        language: Programming language (default: python).
        framework: (optional) Test framework, e.g. pytest, jest, vitest.
        stream: (optional) Enable streaming response (default: True).
    """
    fw_hint = f" using {framework}" if framework else ""
    messages = [
        {
            "role": "system",
            "content": f"You are an expert at writing tests. Write comprehensive unit tests{fw_hint}. "
            "Include happy path, edge cases, and error cases. Return ONLY the test code inside a code block.",
        },
        {
            "role": "user",
            "content": f"Write {language} tests for:\n\n```{language}\n{code}\n```",
        },
    ]

    if stream and ctx is not None:
        return await _call_qwen_stream(
            messages=messages, ctx=ctx, model="", max_tokens=8192
        )
    else:
        return await _call_qwen(messages=messages, max_tokens=8192)


# ────────────────────────────────────────────────────────────
# Utility Tools
# ────────────────────────────────────────────────────────────
@mcp.tool()
async def list_qwen_models() -> str:
    """Check Qwen API connectivity and list available models."""
    url = f"{QWEN_BASE_URL.rstrip('/')}/models"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {QWEN_API_KEY}"},
            )
            response.raise_for_status()
            result = response.json()
            models = result.get("data", [])
            if not models:
                return (
                    f"✅ Connected to {QWEN_BASE_URL}\n"
                    f"🎯 Active model: {_active_model}\n"
                    f"📦 Default model: {QWEN_MODEL}"
                )
            lines = [
                f"✅ Connected: {QWEN_BASE_URL}\n",
                f"🎯 Active model: {_active_model}",
                f"📦 Default model (from env): {QWEN_MODEL}\n",
                "📦 Available models:",
            ]
            for m in models:
                model_id = m.get("id", "unknown")
                marker = " ← active" if model_id == _active_model else ""
                lines.append(f"  • {model_id}{marker}")
            lines.append(
                "\n💡 Use `select_qwen_model` to switch models.\n"
                "   Use `recommend_qwen_model` for task-based recommendations."
            )
            return "\n".join(lines)
    except Exception as e:
        return f"❌ Connection failed: {e}\n\nURL: {QWEN_BASE_URL}\nCheck QWEN_BASE_URL and QWEN_API_KEY"


# ============================================================
# Entrypoint
# ============================================================
def main():
    mcp.run()


if __name__ == "__main__":
    main()
