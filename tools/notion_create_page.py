"""Create a new page in Notion."""

import os
import json
import requests

TOOL_NAME = "notion_create_page"

_check = lambda: bool(os.environ.get("NOTION_API_KEY", ""))

HEADERS = {"Notion-Version": "2022-06-28"}


def execute(title: str, content: str = "", parent_page_id: str = "") -> str:
    """Create a new Notion page with optional content."""
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key:
        return "Notion 未配置，请先运行 notion_setup"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **HEADERS,
    }

    # Build the page structure
    children = []
    if content:
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            block = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                },
            }
            children.append(block)

    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id} if parent_page_id else {"type": "workspace"},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": title}}]
            }
        },
    }
    if children:
        payload["children"] = children

    try:
        resp = requests.post(
            "https://api.notion.com/v1/pages",
            json=payload,
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            url = resp.json().get("url", "")
            return f"页面已创建: {title}\n{url}"
        return f"创建失败 (HTTP {resp.status_code}): {resp.text[:200]}"
    except requests.exceptions.RequestException as e:
        return f"连接失败: {str(e)}"


TOOL_FUNC = execute
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "在 Notion 中创建新页面。可以指定标题、内容，也可指定父页面 ID 以创建子页面。需要先配置 notion_setup。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "页面标题"},
                "content": {"type": "string", "description": "页面内容（纯文本，可选）"},
                "parent_page_id": {"type": "string", "description": "父页面 ID（可选，不指定则创建在 workspace 根目录）"},
            },
            "required": ["title"],
        },
    },
}


def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA, check_fn=_check)
