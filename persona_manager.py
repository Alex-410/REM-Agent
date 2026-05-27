import os
import re

PERSONAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent-skills", "agents")


class Persona:
    def __init__(self, name: str, description: str, role: str, content: str, filepath: str):
        self.name = name
        self.description = description
        self.role = role
        self.content = content
        self.filepath = filepath

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "role": self.role,
        }


# Built-in personas (always available)
BUILT_IN_PERSONAS = {
    "general": Persona(
        name="general",
        description="REM — Reforge, Evolvere, Mimir. Self-evolving AI agent with broad skills across the development lifecycle.",
        role="REM — Self-Evolving Agent",
        content="""You are REM (Reforge, Evolvere, Mimir) — a self-evolving AI agent with broad expertise across the full development lifecycle.
Your strengths include:
- Full-stack development (frontend, backend, infrastructure)
- System design and architecture
- Code quality, testing, and review
- Problem decomposition and planning
- Technical communication

You approach problems pragmatically: prefer simple solutions, validate assumptions early,
and maintain high standards for code quality and reliability.""",
        filepath="",
    ),
}

# Map agent-skills persona names to their file paths
AGENT_SKILLS_PERSONAS = {
    "code-reviewer": os.path.join(PERSONAS_DIR, "code-reviewer.md"),
    "security-auditor": os.path.join(PERSONAS_DIR, "security-auditor.md"),
    "test-engineer": os.path.join(PERSONAS_DIR, "test-engineer.md"),
}


class PersonaManager:
    def __init__(self):
        self.personas: dict[str, Persona] = dict(BUILT_IN_PERSONAS)
        self.current: str = "general"
        self._load_agent_skills_personas()

    def _load_agent_skills_personas(self):
        for name, filepath in AGENT_SKILLS_PERSONAS.items():
            if not os.path.isfile(filepath):
                continue
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()

            description = ""
            content = raw

            # Parse frontmatter
            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
            if fm_match:
                fm_text = fm_match.group(1)
                for line in fm_text.split("\n"):
                    m = re.match(r"^description:\s*(.+)$", line)
                    if m:
                        description = m.group(1).strip()
                        break
                content = raw[fm_match.end():]

            role = self._extract_role(content)
            self.personas[name] = Persona(
                name=name,
                description=description,
                role=role,
                content=content.strip(),
                filepath=filepath,
            )

    @staticmethod
    def _extract_role(content: str) -> str:
        """Extract role from persona content."""
        lines = content.strip().split("\n")
        for line in lines[:5]:
            line = line.strip()
            if line.startswith("#"):
                return line.lstrip("#").strip()
            if "you are" in line.lower():
                return line.strip()
        return "Specialist"

    def get_persona(self, name: str) -> Persona | None:
        return self.personas.get(name)

    def switch_to(self, name: str) -> Persona | None:
        persona = self.personas.get(name)
        if persona:
            self.current = name
        return persona

    def get_current(self) -> Persona:
        return self.personas.get(self.current, self.personas["general"])

    def get_all_personas(self) -> list[Persona]:
        return list(self.personas.values())

    def get_persona_prompt(self, name: str | None = None) -> str:
        """Get the system prompt for a persona."""
        persona = self.personas.get(name or self.current)
        if not persona or persona.name == "general":
            return ""
        return persona.content
