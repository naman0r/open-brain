"""MCP server exposing the context vault.

Transport is a launch-time choice; the tool bodies below are transport-agnostic
and delegate straight to `app.vault.Vault`.
"""

from __future__ import annotations

import argparse

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from app.core.config import settings
from app.vault import Vault, VaultError
from app.vault import notes

INSTRUCTIONS = """\
This server exposes a curated markdown vault of personal and professional context.

Start with `list_projects` to see what is available, then `search_context` to find
relevant notes, then `read_note` for anything you need in full. Prefer searching over
guessing at paths.

Before producing any outward-facing material (cover letters, applications, bios,
resume edits), read `profile/constraints.md`. It carries confidentiality rules on
non-public work and required writing-style rules. This is not optional.

Every factual claim must come from a note you actually read. If the vault does not
support a claim, say so rather than inventing it. Save drafts with `write_note`.
"""

mcp = MCPServer(name="context-vault", version="1.0.0", instructions=INSTRUCTIONS)
vault = Vault(settings.vault_root, auto_commit=settings.vault_auto_commit)


@mcp.tool()
def list_projects() -> str:
    """List every project in the vault with its description and note paths.

    Call this first to orient yourself before searching.
    """
    projects = vault.list_projects()
    if not projects:
        return "No projects found."
    lines = []
    for project in projects:
        lines.append(f"## {project.name}")
        if project.description:
            lines.append(project.description)
        lines.extend(f"- {path}" for path in project.notes)
        lines.append("")
    return "\n".join(lines).strip()


@mcp.tool()
def search_context(
    query: str,
    project: str | None = None,
    type: str | None = None,
    limit: int = 10,
) -> str:
    """Search vault notes by keyword and return ranked matches with snippets.

    Args:
        query: Keywords to search for. Plain words work best; this is keyword
            matching over titles, tags, headings, and body text, not semantic search.
        project: Restrict to one project name, e.g. "interview-prep".
        type: Restrict to one frontmatter type, e.g. "profile", "resume", "generated".
        limit: Maximum number of notes to return.

    Snippets are excerpts only. Use `read_note` on a path before relying on its content.
    """
    hits = vault.search(query, project=project, type=type, limit=limit)
    if not hits:
        return f"No matches for {query!r}. Try `list_projects` or broader keywords."
    lines = []
    for hit in hits:
        meta = " ".join(filter(None, [hit.type, hit.project]))
        lines.append(f"### {hit.title}  ({hit.path}){f'  [{meta}]' if meta else ''}")
        lines.extend(f"  {snippet}" for snippet in hit.snippets)
        lines.append("")
    return "\n".join(lines).strip()


@mcp.tool()
def read_note(path: str) -> str:
    """Read one note in full, including its frontmatter.

    Args:
        path: Vault-relative path as returned by search or list_projects,
            e.g. "profile/resume.md".
    """
    try:
        note = vault.read_note(path)
    except VaultError as exc:
        raise ToolError(str(exc)) from exc
    return notes.dump(note)


@mcp.tool()
def write_note(path: str, content: str, mode: str = "create") -> str:
    """Save generated content into the vault.

    Args:
        path: Vault-relative path ending in `.md`. Must be inside a `generated/`
            directory or under `_inbox/` — curated notes are read-only through this
            tool. For project output use
            `projects/<project>/generated/<company>-<role>-<date>.md`.
        content: Full markdown body. Include YAML frontmatter if you want to control
            `type`/`tags`; otherwise it is added for you.
        mode: "create" fails if the note exists, "append" adds to an existing note,
            "overwrite" replaces it.

    Returns the path written.
    """
    try:
        written = vault.write_note(path, content, mode=mode)
    except VaultError as exc:
        # ToolError text reaches the model; a bare raise would surface only
        # "error executing tool", leaving it no way to pick a valid path.
        raise ToolError(str(exc)) from exc
    return f"Wrote {written}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the context-vault MCP server")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http", "sse"],
        help="stdio for local clients; streamable-http to expose over the network",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
