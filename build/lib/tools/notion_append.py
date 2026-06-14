"""Append content blocks to an existing Notion page."""

import os
import requests

TOOL_NAME = "notion_append"

_check = lambda: bool(os.environ.get("NOTION_API_KEY", ""))

HEADERS = {"Notion-Version": "2022-06-28"}


def execute(page_id: str, content: str) -> str:
    """Append text blocks to an existing Notion page."""
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key:
        return "Notion 未配置，请先运行 notion_setup"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **HEADERS,
    }

    # Build rich text blocks from content lines
    children = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": line}}]
            },
        })

    if not children:
        return "内容为空，没有写入"

    payload = {"children": children}

    try:
        resp = requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            json=payload,
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            return f"已追加 {len(children)} 个内容块到页面 {page_id}"
        return f"追加失败 (HTTP {resp.status_code}): {resp.text[:200]}"
    except requests.exceptions.RequestException as e:
        return f"连接失败: {str(e)}"


TOOL_FUNC = execute
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "向已有的 Notion 页面追加内容块。需要页面的 ID（可以从 notion_search 结果获取）。",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Notion 页面 ID（32位 UUID，可从 URL 或搜索结果获取）"},
                "content": {"type": "string", "description": "要追加的内容（每行一个段落）"},
            },
            "required": ["page_id", "content"],
        },
    },
}


def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA, check_fn=_check)
