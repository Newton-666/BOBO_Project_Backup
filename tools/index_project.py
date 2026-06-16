"""Codebase indexer — scan project structure and store in memory.

After indexing, LLM can locate functions/classes instantly without grep_code.
"""

import os
import re
from pathlib import Path
from typing import Optional

TOOL_NAME = "index_project"

# Directories to skip
SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "node_modules",
    "dist", "build", ".next", "coverage", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "projects",
}

# File extensions to index
INDEX_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".sh"}

# ── Extractors ──────────────────────────────────────────────────────────

def _extract_python(content: str) -> list[str]:
    """Extract function and class signatures from Python."""
    items = []
    for line in content.split("\n"):
        line = line.strip()
        # Class definition
        m = re.match(r"^class\s+(\w+)\s*(\(.*\))?\s*:", line)
        if m:
            bases = m.group(2) or ""
            items.append(f"class {m.group(1)}{bases}")
            continue
        # Function definition (including async)
        m = re.match(r"^(async\s+)?def\s+(\w+)\s*\((.*?)\)\s*(->.*)?\s*:", line)
        if m:
            name = m.group(2)
            params = m.group(3)[:80]
            async_prefix = "async " if m.group(1) else ""
            items.append(f"{async_prefix}def {name}({params})")
            continue
    return items


def _extract_javascript(content: str) -> list[str]:
    """Extract function/class signatures from JS/TS."""
    items = []
    for line in content.split("\n"):
        line = line.strip()
        # class
        if re.match(r"^(export\s+)?class\s+\w+", line):
            name = re.search(r"class\s+(\w+)", line).group(1)
            items.append(f"class {name}")
            continue
        # function
        m = re.match(r"^(export\s+)?(async\s+)?function\s+(\w+)\s*\((.*?)\)", line)
        if m:
            name = m.group(3)
            params = m.group(4)[:80] if m.group(4) else ""
            async_prefix = "async " if m.group(2) else ""
            items.append(f"{async_prefix}function {name}({params})")
            continue
        # arrow function assigned to const
        m = re.match(r"^(export\s+)?const\s+(\w+)\s*=\s*(async\s*)?\(.*\)\s*=>", line)
        if m:
            name = m.group(2)
            items.append(f"const {name} = (...) =>")
            continue
    return items


def _extract_go(content: str) -> list[str]:
    """Extract function and type signatures from Go."""
    items = []
    for line in content.split("\n"):
        line = line.strip()
        m = re.match(r"^func\s+(\(.*?\)\s+)?(\w+)\s*\((.*?)\)", line)
        if m:
            receiver = m.group(1) or ""
            name = m.group(2)
            params = m.group(3)[:80] if m.group(3) else ""
            items.append(f"func {receiver.strip()}{name}({params})")
            continue
        m = re.match(r"^type\s+(\w+)\s+(struct|interface)", line)
        if m:
            items.append(f"type {m.group(1)} {m.group(2)}")
            continue
    return items


def _extract_rust(content: str) -> list[str]:
    """Extract function and struct signatures from Rust."""
    items = []
    for line in content.split("\n"):
        line = line.strip()
        m = re.match(r"^(pub\s+)?(async\s+)?fn\s+(\w+)\s*[<(](.*)", line)
        if m:
            name = m.group(3)
            rest = m.group(4)[:80] if m.group(4) else ""
            items.append(f"fn {name}({rest}")
            continue
        m = re.match(r"^(pub\s+)?(struct|enum|trait|impl)\s+(\w+)", line)
        if m:
            items.append(f"{m.group(2)} {m.group(3)}")
            continue
    return items


_EXTRACTORS = {
    ".py": _extract_python,
    ".js": _extract_javascript,
    ".ts": _extract_javascript,
    ".jsx": _extract_javascript,
    ".tsx": _extract_javascript,
    ".go": _extract_go,
    ".rs": _extract_rust,
}


def execute(path: str = ".", save: bool = True) -> str:
    """Scan project directory and build a structural index.

    Args:
        path: 项目根目录（默认当前目录）
        save: 是否保存到长期记忆（默认 True）
    """
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return f"错误: 目录不存在: {root}"

    # ── Scan ──
    file_count = 0
    total_items = 0
    index_lines = [f"# 项目索引: {root.name}", f"路径: {root}", ""]

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden and build directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]

        for fname in sorted(filenames):
            ext = os.path.splitext(fname)[1].lower()
            if ext not in INDEX_EXTS:
                continue
            if fname.startswith("."):
                continue

            filepath = os.path.join(dirpath, fname)
            rel = os.path.relpath(filepath, root)

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(50000)  # first 50K is enough for signatures
            except Exception:
                continue

            extractor = _EXTRACTORS.get(ext)
            if not extractor:
                continue

            items = extractor(content)
            if not items:
                continue

            file_count += 1
            total_items += len(items)

            index_lines.append(f"\n## {rel} ({len(items)} symbols)")
            for item in items[:50]:  # max 50 per file
                index_lines.append(f"  - {item}")

    if file_count == 0:
        return f"在 {root} 下未找到可索引的代码文件"

    index_lines.append(f"\n---")
    index_lines.append(f"总计: {file_count} 个文件, {total_items} 个符号")

    index_text = "\n".join(index_lines)

    # ── Save to memory ──
    saved_msg = ""
    if save:
        try:
            from tools.v5_memory import save_to_knowledge_base
            save_to_knowledge_base(
                f"项目索引 [{root.name}]: {index_text[:80000]}",
                "project_index"
            )
            saved_msg = "\n✅ 已保存到长期记忆，下次对话自动加载"
        except Exception:
            saved_msg = "\n⚠️ 保存到记忆失败（索引仅在本次会话有效）"

    return f"{index_text[:6000]}\n\n... ({file_count} 文件, {total_items} 符号){saved_msg}"


TOOL_FUNC = execute
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "扫描项目目录，提取所有函数、类、接口等代码结构，建立索引。"
            "索引保存到长期记忆，后续对话中无需 grep_code 即可快速定位代码。"
            "支持 Python、JavaScript/TypeScript、Go、Rust。"
            "首次打开项目时使用此工具建立索引。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "项目根目录路径（默认当前工作目录）"
                },
                "save": {
                    "type": "boolean",
                    "description": "是否保存到长期记忆（默认 True）。False 时只返回不保存。"
                }
            },
            "required": []
        }
    }
}


def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA)
