"""Read the full plain-text content of a Notion page."""

import os
import requests

TOOL_NAME = "notion_read_page"

_check = lambda: bool(os.environ.get("NOTION_API_KEY", ""))

HEADERS = {"Notion-Version": "2022-06-28"}


def execute(page_id: str) -> str:
    """Read a Notion page's content as plain text."""
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key:
        return "Notion 未配置，请先运行 notion_setup"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **HEADERS,
    }

    try:
        # Get page metadata (title)
        page_resp = requests.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=headers,
            timeout=10,
        )
        if page_resp.status_code != 200:
            return f"读取页面失败 (HTTP {page_resp.status_code})"

        page_data = page_resp.json()
        title = "未命名"
        props = page_data.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                parts = prop.get("title", [])
                if parts:
                    title = "".join(t.get("plain_text", "") for t in parts)
                break

        # Get page blocks (content)
        blocks_resp = requests.get(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=headers,
            timeout=10,
        )
        if blocks_resp.status_code != 200:
            return f"读取内容失败 (HTTP {blocks_resp.status_code})"

        blocks = blocks_resp.json().get("results", [])

        # Extract plain text from blocks
        lines = [f"# {title}", ""]
        for block in blocks:
            text = _extract_block_text(block)
            if text:
                lines.append(text)

        return "\n".join(lines)

    except requests.exceptions.RequestException as e:
        return f"连接失败: {str(e)}"


def _extract_block_text(block: dict) -> str:
    """Extract plain text from a Notion block."""
    btype = block.get("type", "")
    block_data = block.get(btype, {})

    rich_text = block_data.get("rich_text", [])
    text = "".join(t.get("plain_text", "") for t in rich_text)
    if not text:
        return ""

    if btype == "heading_1":
        return f"# {text}"
    elif btype == "heading_2":
        return f"## {text}"
    elif btype == "heading_3":
        return f"### {text}"
    elif btype == "bulleted_list_item":
        return f"- {text}"
    elif btype == "numbered_list_item":
        return f"1. {text}"
    elif btype == "to_do":
        checked = block_data.get("checked", False)
        prefix = "[x]" if checked else "[ ]"
        return f"{prefix} {text}"
    elif btype == "code":
        lang = block_data.get("language", "")
        return f"```{lang}\n{text}\n```"
    elif btype == "quote":
        return f"> {text}"
    elif btype == "callout":
        return f"> {text}"
    elif btype == "divider":
        return "---"
    else:
        return text


TOOL_FUNC = execute
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "读取 Notion 页面的完整内容（纯文本格式）。需要页面 ID，可从 notion_search 结果获取。",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Notion 页面 ID（32位 UUID）"}
            },
            "required": ["page_id"]
        }
    }
}

def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA, check_fn=_check)
