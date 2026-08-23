"""The MCP server builds, and its tools carry honest annotations.

These tests exist because the server had no coverage at all and broke
silently: mcp 2.0 moved FastMCP to mcp.server.mcpserver, so every fresh
``pip install "thermocouple-its90[mcp]"`` produced an import error at
startup while CI stayed green. Building the server for real is the only
check that catches an SDK rename.

Skipped when the mcp extra is absent, which is the case on the Python 3.9
job because the SDK requires 3.10 or newer.
"""

import pytest

from thermocouple_its90.mcp_server import _build_server

pytest.importorskip("mcp", reason="the mcp extra is not installed")

EXPECTED_TOOLS = {
    "thermocouple_to_temperature",
    "thermocouple_to_emf",
    "thermocouple_types",
}


def _annotations(tool):
    """Tool annotations, as a plain dict keyed by the camelCase wire names.

    mcp 1.x names the model fields in camelCase and 2.x in snake_case, but
    both serialise to the camelCase names the protocol actually uses.
    """
    ann = tool.annotations
    assert ann is not None, f"{tool.name} has no annotations"
    return ann.model_dump(by_alias=True, exclude_none=True)


def _tools(server):
    listed = server._tool_manager.list_tools()
    return {t.name: t for t in listed}


def test_server_builds():
    """A rename in the SDK breaks this before it reaches a user."""
    assert _build_server() is not None


def test_every_tool_is_present():
    assert set(_tools(_build_server())) == EXPECTED_TOOLS


@pytest.mark.parametrize("name", sorted(EXPECTED_TOOLS))
def test_tool_is_annotated_as_a_pure_read(name):
    """Each tool is a pure function, and says so.

    Hosts use these hints to decide whether to warn before a call. Every
    tool here only evaluates the built-in polynomials, so all four hints
    have one honest answer.
    """
    ann = _annotations(_tools(_build_server())[name])
    assert ann.get("readOnlyHint") is True
    assert ann.get("destructiveHint") is False
    assert ann.get("idempotentHint") is True
    assert ann.get("openWorldHint") is False
    assert ann.get("title"), "a human-readable title helps hosts label the tool"


def test_tools_still_compute_the_right_answers():
    """The decorator must not change what the underlying functions return."""
    tools = _tools(_build_server())
    fn = tools["thermocouple_to_temperature"].fn
    # Type K at 4.096 mV with 25 C terminals is 124.3 C, not the 100.0 C a
    # direct table lookup gives. Same worked example as the README.
    assert fn("K", 4.096, 0.0)["temperature_c"] == pytest.approx(100.0, abs=0.05)
    assert fn("K", 4.096, 25.0)["temperature_c"] == pytest.approx(124.3, abs=0.05)

    emf = tools["thermocouple_to_emf"].fn
    assert emf("K", 300.0)["emf_mv"] == pytest.approx(12.209, abs=0.001)

    types = tools["thermocouple_types"].fn
    assert [t["type"] for t in types()] == ["B", "E", "J", "K", "N", "R", "S", "T"]
