"""On-demand code diff reviewer — fetches full git diff for LLM analysis."""

import subprocess
import os

TOOL_NAME = "review_diff"


def execute(path: str = "", staged: bool = False) -> str:
    """Fetch the current git diff for code review.

    Args:
        path: 限定到特定文件或目录（默认全部变更）
        staged: True 查看暂存区 diff（git diff --staged），默认看未暂存变更
    """
    cwd = path or os.getcwd()

    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        if path:
            # If path is a file, show just that file
            cmd.extend(["--", path] if os.path.isfile(os.path.join(cwd, path)) else [])

        result = subprocess.run(
            cmd,
            capture_output=True, text=True, cwd=cwd, timeout=10
        )
    except FileNotFoundError:
        return "Git 未安装或当前目录不是 git 仓库"
    except subprocess.TimeoutExpired:
        return "获取 diff 超时"
    except Exception as e:
        return f"获取 diff 失败: {e}"

    if result.returncode != 0:
        return f"Git 错误: {result.stderr.strip()[:500]}"

    diff = result.stdout.strip()
    if not diff:
        # Try staged
        try:
            staged_result = subprocess.run(
                ["git", "diff", "--staged"],
                capture_output=True, text=True, cwd=cwd, timeout=10
            )
            if staged_result.stdout.strip():
                diff = staged_result.stdout.strip()
        except Exception:
            pass

    if not diff:
        return "当前没有未提交的代码变更。如果刚做了修改，变更可能已被 engine 自动捕获。"

    # Return full diff for LLM review (truncate at 12K for context safety)
    if len(diff) > 12000:
        diff = diff[:12000] + "\n... (diff 过长，已截断。用 path 参数限定范围查看特定文件)"

    return (
        f"代码变更 (git diff):\n\n"
        f"{diff}\n\n"
        f"⸻\n"
        f"请审查以上变更：\n"
        f"- 是否有逻辑错误或拼写错误？\n"
        f"- 是否有安全风险（注入、密钥泄露、权限问题）？\n"
        f"- 是否有性能可以优化的地方？\n"
        f"- 命名和风格是否与项目其余部分一致？\n"
        f"直接报告发现的问题，不要只说'看起来没问题'。"
    )


TOOL_FUNC = execute
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "获取当前 git diff 用于代码审查。适用场景：修改代码后想检查变更是否正确、安全。"
            "用 path 参数限定特定文件。用 staged=True 查看 git add 后的变更。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "限定到特定文件或目录（默认查看全部变更）"
                },
                "staged": {
                    "type": "boolean",
                    "description": "查看 git add 暂存区的 diff（默认 False = 未暂存变更）"
                }
            },
            "required": []
        }
    }
}


def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA)
