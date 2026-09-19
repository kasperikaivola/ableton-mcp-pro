"""Verify that provider skill directories contain identical SKILL.md files."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_ROOT = REPO_ROOT / ".claude" / "skills"
AGENTS_ROOT = REPO_ROOT / ".agents" / "skills"


def skill_files(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("SKILL.md")
        if path.is_file()
    }


def main() -> int:
    errors: list[str] = []
    for root in (CLAUDE_ROOT, AGENTS_ROOT):
        if not root.is_dir():
            errors.append(f"missing skill root: {root.relative_to(REPO_ROOT)}")

    claude = skill_files(CLAUDE_ROOT)
    agents = skill_files(AGENTS_ROOT)

    missing_in_agents = sorted(set(claude) - set(agents))
    extra_in_agents = sorted(set(agents) - set(claude))
    different = sorted(
        relative
        for relative in set(claude) & set(agents)
        if claude[relative].read_bytes() != agents[relative].read_bytes()
    )

    if missing_in_agents:
        errors.append("missing in .agents/skills: " + ", ".join(missing_in_agents))
    if extra_in_agents:
        errors.append("extra in .agents/skills: " + ", ".join(extra_in_agents))
    if different:
        errors.append("content differs: " + ", ".join(different))

    if errors:
        print("Skill mirrors do not match.")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Skill mirrors match: {len(claude)} SKILL.md files checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())