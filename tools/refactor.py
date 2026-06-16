"""批量重构工具 - 搜索关键词 → 读取文件 → 生成修改 → 批量写入"""

import os
import re
from pathlib import Path

TOOL_NAME = "refactor"

# 默认搜索目录（项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 跳过不需要搜索的目录
SKIP_DIRS = {"__pycache__", ".git", ".vscode", "node_modules", "projects"}
SKIP_EXTS = {".pyc", ".pyo", ".bak", ".backup"}


def _should_skip(path: str) -> bool:
    name = os.path.basename(path)
    if name in SKIP_DIRS:
        return True
    if name.startswith('.'):
        return True
    ext = os.path.splitext(name)[1].lower()
    if ext in SKIP_EXTS:
        return True
    return False


def _search_files(keyword: str, directory: str, file_pattern: str, max_results: int) -> list:
    """搜索文件，返回 (filepath, line_no, line) 列表"""
    pattern_re = file_pattern.replace(".", "\\.").replace("*", ".*") + "$"
    try:
        regex = re.compile(keyword, re.IGNORECASE)
    except re.error:
        return []

    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not _should_skip(os.path.join(root, d))]
        for filename in files:
            if _should_skip(filename):
                continue
            if not re.match(pattern_re, filename):
                continue
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_no, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append((filepath, line_no, line.strip()))
                            if len(results) >= max_results:
                                break
                    if len(results) >= max_results:
                        break
            except Exception:
                continue
        if len(results) >= max_results:
            break
    return results


def _read_file_content(filepath: str) -> str:
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ""


def _write_file(filepath: str, content: str) -> str:
    """写入文件"""
    try:
        full_path = os.path.expanduser(filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"已写入: {filepath}"
    except Exception as e:
        return f"写入失败 {filepath}: {e}"


def execute(keyword: str, directory: str = None, file_pattern: str = "*.py",
            max_results: int = 20, new_content: str = None,
            files: list = None,
            changes: list = None,
            dry_run: bool = False) -> str:
    """
    批量重构工具：搜索关键词 → 显示匹配 → 精确替换（old_string→new_string）。

    两种使用方式：
    1. 只搜索：
       refactor("_confirm") → 搜索并显示所有匹配位置
    2. 搜索并精确替换（传 changes）：
       refactor("_confirm", changes=[
           {"path": "core/engine.py", "old_string": "旧代码", "new_string": "新代码"},
           ...
       ])
       dry_run=True 可预览所有替换而不实际写入。

    Args:
        keyword: 要搜索的关键词（支持正则表达式）
        directory: 搜索目录，默认为项目根目录
        file_pattern: 文件匹配模式，默认 *.py
        max_results: 最大返回结果数，默认 20
        files: （已废弃，请用 changes 参数）
        changes: 要执行的替换列表 [{"path": "...", "old_string": "...", "new_string": "..."}]
        dry_run: 为 True 时只检查 old_string 是否都能匹配，不实际写入
    """
    search_dir = directory or PROJECT_ROOT

    if not os.path.exists(search_dir):
        return f"错误: 目录不存在: {search_dir}"

    # ── 第一步：搜索 ──
    results = _search_files(keyword, search_dir, file_pattern, max_results)

    if not results:
        return f"未找到匹配 '{keyword}' 的内容"

    # ── 第二步：如果有 changes，执行精确替换 ──
    if changes:
        from tools.edit_file import execute as edit_one

        # dry_run 模式：逐个检查 old_string 是否匹配，不写入
        if dry_run:
            preview = [f"🔍 预览替换 '{keyword}' — {len(changes)} 处变更:\n"]
            all_ok = True
            for i, ch in enumerate(changes):
                path = ch.get("path", "")
                old = ch.get("old_string", "")
                new = ch.get("new_string", "")
                full_path = os.path.join(search_dir, path) if not os.path.isabs(path) else path
                if not os.path.exists(full_path):
                    preview.append(f"  ❌ #{i+1} 文件不存在: {path}")
                    all_ok = False
                    continue
                content = _read_file_content(full_path)
                count = content.count(old) if content else 0
                if count == 1:
                    preview.append(f"  ✅ #{i+1} {path}: 匹配 1 处")
                elif count == 0:
                    preview.append(f"  ❌ #{i+1} {path}: old_string 未匹配")
                    # 尝试找相似行
                    from tools.edit_file import _find_similar_lines
                    hints = _find_similar_lines(content or "", old)
                    if hints:
                        preview.append(f"      相似行: L{hints[0][0]}: {hints[0][1][:80]}")
                    all_ok = False
                else:
                    preview.append(f"  ⚠️ #{i+1} {path}: old_string 匹配 {count} 次（需更精确的上下文）")
                    all_ok = False
            preview.append(f"\n{'✅ 全部匹配，可以执行' if all_ok else '❌ 存在不匹配，请修正后再试'}")
            return "\n".join(preview)

        # 实际执行模式
        edit_results = []
        for ch in changes:
            path = ch.get("path", "")
            old = ch.get("old_string", "")
            new = ch.get("new_string", "")
            full_path = os.path.join(search_dir, path) if not os.path.isabs(path) else path
            result = edit_one(full_path, old, new)
            edit_results.append(f"  {result}")

        success_count = sum(1 for r in edit_results if "已替换" in r)
        fail_count = len(edit_results) - success_count

        output = []
        output.append(f"搜索 '{keyword}' 找到 {len(results)} 处匹配，替换 {success_count}/{len(changes)} 处")
        if fail_count:
            output.append(f"失败: {fail_count} 处（用 dry_run=True 预览后再试）")
        output.append("")
        output.extend(edit_results)
        return "\n".join(output)

    # ── 只搜索，不修改 ──
    output = []
    output.append(f"搜索 '{keyword}' 找到 {len(results)} 处匹配:")
    output.append("")

    current_file = None
    for filepath, line_no, line in results:
        if filepath != current_file:
            rel_path = os.path.relpath(filepath, search_dir)
            output.append(f"  📄 {rel_path}")
            content = _read_file_content(filepath)
            if content:
                lines = content.split('\n')
                output.append(f"     共 {len(lines)} 行")
            current_file = filepath
        output.append(f"    L{line_no}: {line[:120]}")

    output.append("")
    output.append("提示: 确认后使用 changes 参数批量精确替换")
    output.append('示例: refactor("keyword", changes=[{"path": "a.py", "old_string": "旧", "new_string": "新"}])')
    output.append("用 dry_run=True 可预览所有替换而不实际写入")

    return "\n".join(output)


TOOL_FUNC = execute
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "批量重构工具：先搜索关键词定位，再用 old_string→new_string 精确替换。"
            "推荐流程：1) 只传 keyword 搜索查看匹配 → "
            "2) 传 changes=[{path, old_string, new_string}] 执行替换 → "
            "3) 用 dry_run=True 可先预览。"
            "与 edit_file 不同：refactor 支持跨多文件批量替换，每个文件内 old_string 需唯一。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "要搜索的关键词，支持正则表达式"},
                "directory": {"type": "string", "description": "搜索目录，默认为项目根目录"},
                "file_pattern": {"type": "string", "description": "文件匹配模式（如 *.py, *.js），默认 *.py"},
                "max_results": {"type": "integer", "description": "最大返回结果数，默认 20"},
                "changes": {
                    "type": "array",
                    "description": "要执行的精确替换列表。与 edit_file 规则相同：old_string 在每个文件中必须恰好出现一次。",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "old_string": {"type": "string", "description": "要被替换的文本（必须与文件内容完全一致）"},
                            "new_string": {"type": "string", "description": "替换后的文本"}
                        },
                        "required": ["path", "old_string", "new_string"]
                    }
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "为 true 时只预览替换，检查 old_string 是否都能匹配，不实际写入文件。默认 false。"
                }
            },
            "required": ["keyword"]
        }
    }
}


def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA)
