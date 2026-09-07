import pytest

from app.vault import (
    CuratedPathError,
    NoteExists,
    NoteNotFound,
    PathEscapesVault,
    Vault,
    VaultError,
)


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile/resume.md").write_text(
        "---\ntype: resume\ntags: [swift, healthcare]\n---\n\n"
        "# Resume\n\n## Auribus Labs\n\nBuilt an FDA-compliant app in Swift.\n",
        encoding="utf-8",
    )
    (tmp_path / "projects/interview-prep/generated").mkdir(parents=True)
    (tmp_path / "projects/interview-prep/_project.md").write_text(
        "---\ntype: project\nproject: interview-prep\n---\n\n"
        "# Interview Prep\n\nContext for job applications.\n",
        encoding="utf-8",
    )
    (tmp_path / "_inbox").mkdir()
    return Vault(tmp_path)


class TestContainment:
    @pytest.mark.parametrize(
        "path",
        [
            "../outside.md",
            "profile/../../outside.md",
            "/etc/passwd.md",
            "profile/../../../tmp/evil.md",
        ],
    )
    def test_traversal_is_refused(self, vault, path):
        with pytest.raises(PathEscapesVault):
            vault.read_note(path)

    def test_symlink_escape_is_refused(self, vault, tmp_path):
        outside = tmp_path.parent / "outside.md"
        outside.write_text("secret", encoding="utf-8")
        (tmp_path / "link.md").symlink_to(outside)
        with pytest.raises(PathEscapesVault):
            vault.read_note("link.md")

    def test_non_markdown_is_refused(self, vault):
        with pytest.raises(VaultError):
            vault.read_note("profile/secrets.env")

    def test_missing_note_raises(self, vault):
        with pytest.raises(NoteNotFound):
            vault.read_note("profile/nope.md")


class TestQuarantine:
    @pytest.mark.parametrize(
        "path", ["profile/resume.md", "projects/interview-prep/_project.md", "notes.md"]
    )
    def test_curated_paths_refuse_agent_writes(self, vault, path):
        with pytest.raises(CuratedPathError):
            vault.write_note(path, "# nope")

    @pytest.mark.parametrize(
        "path", ["_inbox/draft.md", "projects/interview-prep/generated/letter.md"]
    )
    def test_quarantined_paths_accept_writes(self, vault, path):
        assert vault.write_note(path, "# Draft\n\nbody") == path

    @pytest.mark.parametrize(
        "path",
        [
            "_inbox/../profile/resume.md",
            "projects/interview-prep/generated/../_project.md",
        ],
    )
    def test_quarantine_is_judged_on_resolved_path(self, vault, path):
        """A path that looks quarantined by its first segment but resolves onto a
        curated note must still be refused."""
        with pytest.raises(CuratedPathError):
            vault.write_note(path, "# clobbered")
        assert "clobbered" not in vault.read_note("profile/resume.md").body

    def test_write_curated_bypasses_quarantine(self, vault):
        assert vault.write_curated("profile/new.md", "# New") == "profile/new.md"

    def test_create_refuses_existing(self, vault):
        vault.write_note("_inbox/a.md", "# A")
        with pytest.raises(NoteExists):
            vault.write_note("_inbox/a.md", "# A again")

    def test_append_requires_existing(self, vault):
        with pytest.raises(NoteNotFound):
            vault.write_note("_inbox/missing.md", "more", mode="append")

    def test_append_preserves_prior_content(self, vault):
        vault.write_note("_inbox/a.md", "# A\n\nfirst")
        vault.write_note("_inbox/a.md", "second", mode="append")
        body = vault.read_note("_inbox/a.md").body
        assert "first" in body and "second" in body

    def test_unknown_mode_refused(self, vault):
        with pytest.raises(VaultError):
            vault.write_note("_inbox/a.md", "x", mode="clobber")


class TestFrontmatter:
    def test_generated_write_is_stamped(self, vault):
        vault.write_note("projects/interview-prep/generated/x.md", "# X\n\nbody")
        note = vault.read_note("projects/interview-prep/generated/x.md")
        assert note.type == "generated"
        assert note.project == "interview-prep"

    def test_supplied_frontmatter_is_preserved(self, vault):
        vault.write_note("_inbox/y.md", "---\ntype: reference\ntags: [a]\n---\n\n# Y")
        note = vault.read_note("_inbox/y.md")
        assert note.type == "reference"
        assert note.tags == ["a"]

    def test_malformed_frontmatter_still_reads(self, vault, tmp_path):
        (tmp_path / "_inbox/bad.md").write_text(
            "---\n: : not yaml : :\n---\n\n# Bad\n", encoding="utf-8"
        )
        assert "Bad" in vault.read_note("_inbox/bad.md").body


class TestSearch:
    def test_finds_by_body_term(self, vault):
        hits = vault.search("FDA compliant")
        assert [h.path for h in hits] == ["profile/resume.md"]
        assert hits[0].snippets

    def test_finds_by_tag(self, vault):
        assert vault.search("healthcare")[0].path == "profile/resume.md"

    def test_project_filter(self, vault):
        assert vault.search("context", project="interview-prep")
        assert not vault.search("context", project="nonexistent")

    def test_type_filter(self, vault):
        assert not vault.search("Swift", type="project")
        assert vault.search("Swift", type="resume")

    def test_full_query_coverage_outranks_repetition(self, vault, tmp_path):
        (tmp_path / "_inbox/repeat.md").write_text(
            "# Swift\n\nswift swift swift swift swift\n", encoding="utf-8"
        )
        hits = vault.search("swift fda")
        assert hits[0].path == "profile/resume.md"

    def test_stopwords_only_query_returns_nothing(self, vault):
        assert vault.search("the and of") == []


def test_list_projects(vault):
    projects = vault.list_projects()
    assert [p.name for p in projects] == ["interview-prep"]
    assert projects[0].description == "Context for job applications."
    assert "_project.md" not in " ".join(projects[0].notes)


class TestAutoCommit:
    @staticmethod
    def _init_repo(path):
        import subprocess
        # An empty tree has nothing to commit, so seed a file first.
        (path / "seed.md").write_text("# seed", encoding="utf-8")
        for args in (["init", "-q"], ["add", "-A"]):
            subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(path), "-c", "user.name=seed", "-c", "user.email=seed@x.invalid",
             "commit", "-qm", "seed"],
            check=True, capture_output=True,
        )

    def _log(self, path, fmt):
        import subprocess
        return subprocess.run(
            ["git", "-C", str(path), "log", "-1", f"--format={fmt}"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    def test_commit_uses_bot_identity_not_git_config(self, tmp_path):
        self._init_repo(tmp_path)
        vault = Vault(tmp_path, auto_commit=True, commit_identity=("bot", "bot@x.invalid"))
        vault.write_note("_inbox/a.md", "# A")
        assert self._log(tmp_path, "%an <%ae>") == "bot <bot@x.invalid>"
        # Committer matters too: GitHub attributes on both.
        assert self._log(tmp_path, "%cn <%ce>") == "bot <bot@x.invalid>"

    def test_default_identity_is_a_bot(self, tmp_path):
        self._init_repo(tmp_path)
        vault = Vault(tmp_path, auto_commit=True)
        vault.write_note("_inbox/a.md", "# A")
        assert "@open-brain.invalid" in self._log(tmp_path, "%ae")

    def test_write_succeeds_when_not_a_git_repo(self, tmp_path):
        vault = Vault(tmp_path, auto_commit=True)
        assert vault.write_note("_inbox/a.md", "# A") == "_inbox/a.md"


def test_rejects_missing_root(tmp_path):
    with pytest.raises(VaultError):
        Vault(tmp_path / "nope")
