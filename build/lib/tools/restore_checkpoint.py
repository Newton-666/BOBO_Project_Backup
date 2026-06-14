"""Restore a file from its last checkpoint (before file_writer changed it)."""

TOOL_NAME = "restore_checkpoint"

TOOL_FUNC = None  # wired via engine

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "撤销文件操作。path 为空时列出所有可恢复的文件。\n"
            "支持:\n"
            "- path 留空 → 列出 file_writer 检查点\n"
            "- path=\"__list_trash__\" → 列出回收站中的文件\n"
            "- path=\"trash:filename\" → 从回收站恢复文件\n"
            "删除、移动、重命名操作会自动备份到回收站，可在此恢复。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径，为空则列出检查点"}
            },
            "required": []
        }
    }
}

def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA)
