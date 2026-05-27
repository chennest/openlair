from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    content: str


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    metadata: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, parts[2].strip()


class SkillRegistry:
    def __init__(self, skills_path: Path | str) -> None:
        self._skills_path = Path(skills_path)
        self._skills = self._scan()

    def catalog(self) -> str:
        if not self._skills:
            return "(no skills found)"
        return "\n".join(f"- **{skill.name}**: {skill.description}" for skill in self._skills.values())

    def load(self, name: str) -> str:
        skill = self._skills.get(name)
        if skill is None:
            return f"Skill not found: {name}"
        return skill.content

    def _scan(self) -> dict[str, Skill]:
        skills: dict[str, Skill] = {}
        if not self._skills_path.exists():
            return skills
        for directory in sorted(self._skills_path.iterdir()):
            if not directory.is_dir():
                continue
            manifest = directory / "SKILL.md"
            if not manifest.exists():
                continue
            raw = manifest.read_text(encoding="utf-8")
            metadata, body = parse_frontmatter(raw)
            name = metadata.get("name", directory.name)
            description = metadata.get("description", body.splitlines()[0].lstrip("# ") if body else "")
            skills[name] = Skill(name=name, description=description, content=raw)
        return skills
