"""Skill 管理器 — 加载和执行技能"""

import os
import json
import yaml
from pathlib import Path
from typing import Optional


class SkillManager:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(exist_ok=True)
        self._yaml_skills: dict = {}
        self._index_skills: list = []
        self._load_all()

    def _load_all(self):
        # Load .yaml skills
        self._yaml_skills = {}
        for yaml_file in self.skills_dir.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    skill = yaml.safe_load(f)
                if skill and skill.get("name"):
                    self._yaml_skills[skill["name"]] = skill
            except Exception:
                pass

        # Load index.json skills (legacy support)
        idx_path = self.skills_dir / "index.json"
        if idx_path.exists():
            try:
                with open(idx_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._index_skills = data.get("skills", [])
            except Exception:
                self._index_skills = []

    def list_skills(self):
        return list(self._yaml_skills.keys())

    def get_skill(self, name: str) -> Optional[dict]:
        return self._yaml_skills.get(name)

    def match_skill(self, user_input: str) -> Optional[dict]:
        """Match user input against skill triggers. Returns the first matching skill."""
        text = user_input.lower().replace(" ", "")  # ignore spaces for matching

        # Check index.json triggers first
        for entry in self._index_skills:
            for kw in entry.get("trigger", []):
                if kw.lower().replace(" ", "") in text:
                    skill = self.get_skill(entry["name"])
                    if skill:
                        return skill
                    return entry

        # Check yaml skill names directly
        for name, skill in self._yaml_skills.items():
            if name.lower().replace(" ", "") in text:
                return skill

        return None

    def execute_skill(self, skill: dict, context: dict = None) -> str:
        """Execute a skill's steps. Returns a summary string."""
        from core.tool_executor import execute_tool

        steps = skill.get("steps", [])
        results = []
        context = context or {}

        for i, step in enumerate(steps):
            step_type = step.get("type") or step.get("action", "tool_call")

            if step_type == "tool_call":
                tool_name = step.get("tool") or step.get("name", "")
                args = step.get("args", {})
                resolved_args = self._resolve_vars(args, context)
                try:
                    result = execute_tool(tool_name, resolved_args)
                    preview = (result or "")[:100].replace("\n", " ")
                    results.append(f"[{tool_name}] {preview}")
                    context["last_result"] = result
                except Exception as e:
                    results.append(f"[{tool_name}] 失败: {str(e)}")

            elif step_type in ("user_input", "assistant_output"):
                content = step.get("content", "")
                label = "用户" if step_type == "user_input" else "Bobo"
                results.append(f"[{label}] {content[:100]}")

            elif step_type == "display":
                results.append(step.get("description", ""))

            elif step_type == "generate_code":
                # This step type was used in the old coding_master skill
                results.append("[生成代码] 由 LLM 处理具体代码生成")

        return "\n".join(results) if results else "Skill 执行完成"

    def _resolve_vars(self, value, context: dict):
        if isinstance(value, str):
            for k, v in context.items():
                value = value.replace(f"{{{k}}}", str(v))
            return value
        elif isinstance(value, dict):
            return {k: self._resolve_vars(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_vars(v, context) for v in value]
        return value


_skill_manager = None


def get_skill_manager():
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager
