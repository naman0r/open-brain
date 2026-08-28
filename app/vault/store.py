from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Iterator

from app.vault import notes
from app.vault.notes import Note

QUARANTINE_ROOTS = ("_inbox",)
GENERATED_DIR = "generated"
PROJECTS_DIR = "projects"
PROJECT_MARKER = "_project.md"

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#.-]*")
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have how i if in is it its of on or "
    "that the this to was what when where which who why with you your".split()
)


class VaultError(Exception):
    pass


class PathEscapesVault(VaultError):
    pass


class CuratedPathError(VaultError):
    pass


class NoteExists(VaultError):
    pass


class NoteNotFound(VaultError):
    pass


@dataclass(frozen=True, slots=True)
class SearchHit:
    path: str
    title: str
    score: float
    snippets: list[str]
    type: str | None = None
    project: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    name: str
    description: str
    notes: list[str]


class Vault:
    """Filesystem-backed markdown vault.

    Every path crossing this boundary is vault-relative and validated. Callers
    outside this module never see a `pathlib.Path`, which is what keeps traversal
    contained to `_resolve`.
    """

    def __init__(self, root: Path | str, auto_commit: bool = False) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise VaultError(f"vault root does not exist: {self.root}")
        self.auto_commit = auto_commit

    # --- path handling ---------------------------------------------------

    def _resolve(self, rel: str) -> Path:
        if not rel or PurePosixPath(rel).is_absolute() or Path(rel).is_absolute():
            raise PathEscapesVault(f"path must be vault-relative: {rel!r}")
        resolved = (self.root / rel).resolve()
        # `.resolve()` collapses `..` and follows symlinks, so this single check
        # covers traversal, symlink escape, and absolute-path injection.
        if not resolved.is_relative_to(self.root):
            raise PathEscapesVault(f"path escapes vault: {rel!r}")
        if resolved.suffix != ".md":
            raise VaultError(f"not a markdown path: {rel!r}")
        return resolved

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    @staticmethod
    def is_quarantined(rel: str) -> bool:
        parts = PurePosixPath(rel).parts
        return bool(parts) and (parts[0] in QUARANTINE_ROOTS or GENERATED_DIR in parts)

    # --- reading ---------------------------------------------------------

    def iter_notes(self) -> Iterator[Note]:
        for path in sorted(self.root.rglob("*.md")):
            if any(part.startswith(".") for part in path.relative_to(self.root).parts):
                continue
            yield notes.parse(self._relative(path), path.read_text(encoding="utf-8"))

    def read_note(self, path: str) -> Note:
        target = self._resolve(path)
        if not target.is_file():
            raise NoteNotFound(f"note not found: {self._relative(target)}")
        return notes.parse(self._relative(target), target.read_text(encoding="utf-8"))

    def list_projects(self) -> list[ProjectSummary]:
        root = self.root / PROJECTS_DIR
        if not root.is_dir():
            return []
        summaries = []
        for directory in sorted(p for p in root.iterdir() if p.is_dir()):
            members = [
                self._relative(f)
                for f in sorted(directory.rglob("*.md"))
                if f.name != PROJECT_MARKER
            ]
            marker = directory / PROJECT_MARKER
            description = ""
            if marker.is_file():
                note = notes.parse(self._relative(marker), marker.read_text(encoding="utf-8"))
                description = _first_prose_line(note.body)
            summaries.append(
                ProjectSummary(name=directory.name, description=description, notes=members)
            )
        return summaries

    # --- search ----------------------------------------------------------

    def search(
        self,
        query: str,
        project: str | None = None,
        type: str | None = None,
        limit: int = 10,
    ) -> list[SearchHit]:
        terms = _terms(query)
        if not terms:
            return []

        hits = []
        for note in self.iter_notes():
            if project and note.project != project:
                continue
            if type and note.type != type:
                continue
            score, snippets = _score(note, terms)
            if score > 0:
                hits.append(
                    SearchHit(
                        path=note.path,
                        title=note.title,
                        score=round(score, 2),
                        snippets=snippets,
                        type=note.type,
                        project=note.project,
                    )
                )
        hits.sort(key=lambda h: (-h.score, h.path))
        return hits[:limit]

    # --- writing ---------------------------------------------------------

    def write_note(self, path: str, content: str, mode: str = "create") -> str:
        """Write to a quarantined path. Curated paths are refused.

        Agent-facing writes come through here. `write_curated` is the deliberate,
        non-agent-facing escape hatch.
        """
        target = self._resolve(path)
        # Quarantine must be judged on the resolved path, not the caller's string:
        # `_inbox/../profile/resume.md` looks quarantined by its first segment but
        # lands on a curated note.
        rel = self._relative(target)
        if not self.is_quarantined(rel):
            raise CuratedPathError(
                f"{rel!r} is curated and cannot be written through this tool; "
                f"write under a 'generated/' directory or '_inbox/' instead"
            )
        return self._write(target, content, mode)

    def write_curated(self, path: str, content: str, mode: str = "create") -> str:
        return self._write(self._resolve(path), content, mode)

    def _write(self, target: Path, content: str, mode: str) -> str:
        if mode not in ("create", "append", "overwrite"):
            raise VaultError(f"unknown write mode: {mode!r}")
        rel = self._relative(target)
        exists = target.is_file()

        if mode == "create" and exists:
            raise NoteExists(f"{rel} already exists; use mode='append' or mode='overwrite'")
        if mode == "append" and not exists:
            raise NoteNotFound(f"{rel} does not exist; use mode='create'")

        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            target.write_text(
                target.read_text(encoding="utf-8").rstrip() + "\n\n" + content.strip() + "\n",
                encoding="utf-8",
            )
        else:
            target.write_text(_with_frontmatter(rel, content), encoding="utf-8")

        self._commit(rel, mode)
        return rel

    def _commit(self, rel: str, mode: str) -> None:
        if not self.auto_commit:
            return
        try:
            subprocess.run(
                ["git", "-C", str(self.root), "add", "--", rel],
                check=True, capture_output=True, timeout=15,
            )
            subprocess.run(
                ["git", "-C", str(self.root), "commit", "-m", f"agent {mode}: {rel}"],
                check=True, capture_output=True, timeout=15,
            )
        except (subprocess.SubprocessError, OSError):
            # A vault that is not a git repo, or a commit that finds nothing
            # staged, must not fail the write the caller already succeeded at.
            pass


def _first_prose_line(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", ">", "-", "|", "---")):
            return stripped
    return ""


def _terms(query: str) -> list[str]:
    seen = []
    for match in _TOKEN.findall(query.lower()):
        if len(match) > 1 and match not in _STOPWORDS and match not in seen:
            seen.append(match)
    return seen


def _score(note: Note, terms: list[str]) -> tuple[float, list[str]]:
    matched: set[str] = set()
    score = 0.0

    heading = f"{note.title} {note.path}".lower()
    tags = " ".join(note.tags).lower()
    for term in terms:
        if term in heading:
            score += 3.0
            matched.add(term)
        if term in tags:
            score += 2.0
            matched.add(term)

    snippets: list[str] = []
    for line in note.body.splitlines():
        lowered = line.lower()
        present = [t for t in terms if t in lowered]
        if not present:
            continue
        matched.update(present)
        score += (2.0 if line.lstrip().startswith("#") else 1.0) * len(present)
        stripped = line.strip()
        if len(snippets) < 3 and len(stripped) > 3:
            snippets.append(stripped)

    if not matched:
        return 0.0, []
    # Notes matching more of the query outrank notes repeating one term.
    return score * (len(matched) / len(terms)), snippets


def _with_frontmatter(rel: str, content: str) -> str:
    note = notes.parse(rel, content)
    if note.frontmatter:
        return notes.dump(note)
    parts = PurePosixPath(rel).parts
    stamped = {"type": "generated", "updated": date.today().isoformat()}
    if len(parts) > 2 and parts[0] == PROJECTS_DIR:
        stamped["project"] = parts[1]
    return notes.dump(Note(path=rel, frontmatter=stamped, body=note.body))
