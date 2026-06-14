"""Search across all configured platforms (Obsidian, Notion, email) for a keyword."""

TOOL_NAME = "cross_search"

TOOL_FUNC = None  # handled by engine

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "在一个查询中搜索所有已配置的知识平台（Obsidian、Notion、邮件）。"
            "自动搜索已连接的每个平台，并返回带标签的合并结果。"
            "适用场景：你想知道某个主题的所有相关信息，不局限于单个平台。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"]
        }
    }
}

def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA)
