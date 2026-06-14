"""edit_file.py — 精确字符串替换（不改架构，只加一个工具）

用法：
    edit_file(file_path="/path/to/file.py",
              old_string="bug line here",
              new_string="fixed line here")

特点：
    - old_string 必须在文件中恰好出现一次（防止误改）
    - 写入前自动备份到 ~/.bobo/trash/
    - 替换后自动捕获 git diff 注入下一轮 LLM 调用
"""

import os
import time
from pathlib import Path


TRASH_DIR = Path.home() / ".bobo" / "trash"


def _backup(file_path: Path) -> str | None:
    """将文件备份到回收站，返回备份文件名。失败返回 None。"""
    if not file_path.exists():
        return None
    try:
        TRASH_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}_{timestamp}"
        backup_path = TRASH_DIR / backup_name
        backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")
        return backup_name
    except Exception:
        return None


def execute(file_path: str, old_string: str, new_string: str) -> str:
    """精确替换文件中第一次（且唯一一次）出现的 old_string。"""

    path = Path(file_path).expanduser().resolve()

    # ── 存在性检查 ──
    if not path.exists():
        hint = ""
        parent = path.parent
        if parent.exists():
            try:
                siblings = [p.name for p in parent.iterdir() if p.is_file()]
                if siblings:
                    hint = f"\n  目录 {parent} 下的文件: {', '.join(siblings[:10])}"
            except Exception:
                pass
        return f"错误: 文件不存在: {path}{hint}"

    if not path.is_file():
        return f"错误: 路径不是文件: {path}"

    # ── 读取 ──
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"错误: 无法以 UTF-8 编码读取文件: {path}"

    # ── 匹配检查 ──
    count = content.count(old_string)
    if count == 0:
        # 尝试给出调试信息：展示 old_string 前几行，帮助 LLM 比对
        preview = old_string[:80].replace("\n", "\\n")
        return (
            f"错误: 未找到要替换的文本。\n"
            f"  文件: {path} ({len(content)} 字符, {content.count(chr(10)) + 1} 行)\n"
            f"  查找内容: {preview}...\n"
            f"  请检查 old_string 是否与文件内容完全一致（包括缩进和空白字符）。"
        )

    if count > 1:
        return (
            f"错误: old_string 在文件中出现了 {count} 次，不唯一。\n"
            f"  请提供更多上下文（包含前后各 1-2 行），确保只匹配一处。"
        )

    # ── 备份 ──
    backup_name = _backup(path)

    # ── 替换 ──
    new_content = content.replace(old_string, new_string, 1)
    try:
        path.write_text(new_content, encoding="utf-8")
    except Exception as e:
        return f"错误: 写入失败: {e}"

    old_lines = content.count("\n") + 1
    new_lines = new_content.count("\n") + 1
    backup_info = f"\n  备份: ~/.bobo/trash/{backup_name}" if backup_name else ""

    return (
        f"已替换: {path}\n"
        f"  文件大小: {len(content)} → {len(new_content)} 字符\n"
        f"  行数: {old_lines} → {new_lines} 行{backup_info}"
    )


def register(reg):
    reg("edit_file", execute, {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "精确替换文件中的一段文本。old_string 必须在文件中恰好出现一次。"
                "适用于修改函数定义、修复 bug、重构代码等场景。"
                "不要用于创建新文件——创建新文件用 file_writer。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要编辑的文件路径（绝对路径或相对路径）"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "要被替换的文本，必须与文件内容完全一致（含缩进、空格、换行）。文件中必须恰好出现一次。"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "替换后的文本"
                    }
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }
    })
