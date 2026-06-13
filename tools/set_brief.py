"""Set a conversation brief — a note that guides Bobo's behavior for this session."""

import os

TOOL_NAME = "set_brief"

TOOL_FUNC = None  # handled by engine

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "设置当前会话的简报。提供笔记路径或直接输入文本内容，Bobo 会在本次会话中始终参考此简报。",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "笔记路径（如 'Projects/meeting-notes.md'）或直接输入文本内容"
                },
                "from_obsidian": {
                    "type": "boolean",
                    "description": "如果为 true，则从 Obsidian 笔记库读取 source 指定的文件"
                }
            },
            "required": ["source"]
        }
    }
}


def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA)
