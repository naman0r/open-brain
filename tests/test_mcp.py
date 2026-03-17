from app.mcp.server import list_tools


def test_mcp_tools_have_core_actions() -> None:
    names = [tool.name for tool in list_tools()]
    assert "remember" in names
    assert "recall" in names
