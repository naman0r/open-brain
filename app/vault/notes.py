from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

FRONTMATTER_FENCE = "---"


@dataclass(frozen=True, slots=True)
class Note:
    path: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def title(self) -> str:
        for line in self.body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return self.path.rsplit("/", 1)[-1].removesuffix(".md")

    @property
    def type(self) -> str | None:
        value = self.frontmatter.get("type")
        return str(value) if value is not None else None

    @property
    def project(self) -> str | None:
        value = self.frontmatter.get("project")
        return str(value) if value is not None else None

    @property
    def tags(self) -> list[str]:
        raw = self.frontmatter.get("tags") or []
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(",") if t.strip()]
        return [str(t) for t in raw]


def parse(path: str, text: str) -> Note:
    if not text.startswith(FRONTMATTER_FENCE + "\n"):
        return Note(path=path, body=text)

    end = text.find("\n" + FRONTMATTER_FENCE, len(FRONTMATTER_FENCE))
    if end == -1:
        return Note(path=path, body=text)

    raw = text[len(FRONTMATTER_FENCE) + 1 : end]
    body_start = text.find("\n", end + 1)
    body = "" if body_start == -1 else text[body_start + 1 :]

    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError:
        # A malformed header must not make the note unreadable — the body is
        # what carries the context, and search still needs to reach it.
        return Note(path=path, body=text)

    return Note(path=path, frontmatter=loaded if isinstance(loaded, dict) else {}, body=body)


def dump(note: Note) -> str:
    if not note.frontmatter:
        return note.body
    header = yaml.safe_dump(note.frontmatter, sort_keys=False, allow_unicode=True).rstrip()
    return f"{FRONTMATTER_FENCE}\n{header}\n{FRONTMATTER_FENCE}\n\n{note.body.lstrip()}"
