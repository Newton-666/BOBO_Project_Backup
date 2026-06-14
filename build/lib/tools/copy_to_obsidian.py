"""Copy a Notion page to Obsidian vault as a markdown file."""

import os

TOOL_NAME = "copy_to_obsidian"


def execute(page_id: str, filename: str = "") -> str:
    """Copy a Notion page to Obsidian."""
    # Read the Notion page
    from tools.notion_read_page import execute as notion_read
    content = notion_read(page_id)

    if content.startswith("读取页面失败") or content.startswith("连接失败"):
        return f"读取 Notion 页面失败: {content}"

    # Determine filename from content title
    if not filename:
        first_line = content.split("\n")[0] if content else "copied-from-notion"
        filename = first_line.lstrip("# ").strip().replace(" ", "-").lower()[:50]

    # Write to Obsidian
    from tools.file_writer import write_obsidian
    result = write_obsidian(filename, content, auto_backup=False)

    if result.startswith("✅"):
        return f"{result}\n内容已从 Notion 复制到 Obsidian: {filename}"
    return result


TOOL_FUNC = execute
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "将 Notion 页面复制到 Obsidian 笔记库，保留标题、章节、列表、代码块等格式。Notion 专有格式（提及、数据库）会降级为纯文本。",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Notion 页面 ID"},
                "filename": {"type": "string", "description": "Obsidian 文件名（可选，默认使用页面标题）"}
            },
            "required": ["page_id"]
        }
    }
}

def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA)
