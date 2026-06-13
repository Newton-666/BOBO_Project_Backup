"""Skill 保存 — 从教学模式录制并保存技能"""

import yaml
from pathlib import Path
from typing import List, Dict


class SkillExecutor:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(exist_ok=True)

    def save_from_recording(self, skill_name: str, messages: List[Dict], description: str = "") -> str:
        """Save a skill from recorded conversation messages."""
        if not messages:
            return "没有记录到任何对话"

        steps = []
        for msg in messages:
            role = msg.get("role")
            if role == "user":
                steps.append({"type": "user_input", "content": msg.get("content", "")})
            elif role == "assistant":
                steps.append({"type": "assistant_output", "content": msg.get("content", "")})
            elif role == "tool_call":
                steps.append({
                    "type": "tool_call",
                    "tool": msg.get("name", ""),
                    "args": msg.get("args", {}),
                })

        skill = {
            "name": skill_name,
            "description": description or f"从教学录制，{len(steps)} 个步骤",
            "steps": steps,
        }

        filepath = self.skills_dir / f"{skill_name}.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(skill, f, allow_unicode=True, default_flow_style=False)

        # Also update index.json for keyword-triggered matching
        idx_path = self.skills_dir / "index.json"
        import json
        if idx_path.exists():
            with open(idx_path, encoding="utf-8") as f:
                idx = json.load(f)
        else:
            idx = {"skills": []}
        idx["skills"].append({
            "name": skill_name,
            "trigger": [skill_name],
            "description": description or f"教学录制技能",
        })
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)

        return f"Skill '{skill_name}' 已保存，{len(steps)} 个步骤"

    def load_skill(self, skill_name: str) -> dict:
        filepath = self.skills_dir / f"{skill_name}.yaml"
        if not filepath.exists():
            return None
        with open(filepath, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def execute_skill(self, skill: dict, context: dict = None) -> str:
        """Legacy: delegate to skill_manager's execute_skill for consistency."""
        from core.skill_manager import get_skill_manager
        return get_skill_manager().execute_skill(skill, context)


_skill_executor = None


def get_skill_executor():
    global _skill_executor
    if _skill_executor is None:
        _skill_executor = SkillExecutor()
    return _skill_executor
