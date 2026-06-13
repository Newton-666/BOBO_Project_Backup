"""Check if GitHub CLI is installed and authenticated."""

import subprocess

TOOL_NAME = "github_check_auth"

def execute() -> str:
    """Check GitHub CLI setup."""
    try:
        # Check if gh is installed
        version = subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=5)
        if version.returncode != 0:
            return "❌ GitHub CLI (gh) 未安装。请运行: brew install gh"
        
        # Check if authenticated
        auth = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=5)
        if auth.returncode == 0:
            return "✅ GitHub CLI 已安装并登录"
        
        # Extract username hint from error
        return (
            "⚠️ GitHub CLI 已安装但未登录。请运行:\n"
            "  gh auth login\n\n"
            "然后授权浏览器访问。完成后 Bobo 就可以创建仓库、推送代码和审查 PR。"
        )
    except FileNotFoundError:
        return "❌ GitHub CLI (gh) 未安装。请运行:\n  brew install gh\n  gh auth login"
    except Exception as e:
        return f"❌ 检查失败: {str(e)}"


TOOL_FUNC = execute
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "检查 GitHub CLI 是否已安装并登录。在尝试任何 GitHub 操作前调用此工具。",
        "parameters": {"type": "object", "properties": {}}
    }
}

def register(reg):
    reg(TOOL_NAME, TOOL_FUNC, TOOL_SCHEMA)
