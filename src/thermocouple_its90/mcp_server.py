"""MCP server exposing the ITS-90 conversions as tools for AI agents.

Install the extra and register the command with your agent runtime::

    pip install "thermocouple-its90[mcp]"
    thermocouple-its90-mcp          # stdio transport

For Claude Code: ``claude mcp add thermocouple -- thermocouple-its90-mcp``

The tools exist because language models reliably mis-remember thermocouple
polynomials; a verified lookup beats a confident guess.
"""

from __future__ import annotations

from . import __version__, get, letters


def _build_server():
    # mcp 2.0 renamed FastMCP to MCPServer and moved the module. Both are
    # supported here: the constructor, the tool decorator and run() take the
    # same arguments either way, and ToolAnnotations accepts the camelCase
    # wire names on both, so only the import differs.
    try:
        from mcp.server.mcpserver import MCPServer as _Server  # mcp >= 2.0

        # 2.x lets the server report its own version, which is what a host
        # shows the user. 1.x reports the SDK version and takes no override.
        extra = {"version": __version__}
    except ModuleNotFoundError:
        from mcp.server.fastmcp import FastMCP as _Server  # mcp 1.x

        extra = {}

    from mcp.types import ToolAnnotations

    mcp = _Server(
        "thermocouple-its90",
        instructions=(
            "ITS-90 thermocouple conversions (NIST Monograph 175), types "
            "B, E, J, K, N, R, S, T. Temperatures in Celsius, EMF in mV. "
            "All conversions include explicit cold-junction handling."
        ),
        **extra,
    )

    def _pure(title: str) -> ToolAnnotations:
        """Hints for a tool that only reads the built-in polynomial data.

        Every tool here is a pure function: nothing is written, nothing is
        fetched over the network, and the same arguments always give the same
        answer. Hosts read these to decide what to tell a user before a call.
        """
        return ToolAnnotations(
            title=title,
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )

    @mcp.tool(annotations=_pure("Thermocouple EMF to temperature"))
    def thermocouple_to_temperature(
        type_letter: str, emf_mv: float, reference_c: float = 0.0
    ) -> dict:
        """Convert a measured thermocouple EMF (mV) to hot-junction temperature (C).

        reference_c is the cold-junction temperature; 0.0 means an ice bath
        or an instrument that already compensates.
        """
        tc = get(type_letter)
        t = tc.temperature(emf_mv, reference=reference_c)
        return {
            "temperature_c": round(t, 3),
            "temperature_f": round(t * 9 / 5 + 32, 3),
            "temperature_k": round(t + 273.15, 3),
            "seebeck_uv_per_c": round(tc.seebeck(t) * 1000, 2),
            "type": tc.letter,
        }

    @mcp.tool(annotations=_pure("Temperature to thermocouple EMF"))
    def thermocouple_to_emf(
        type_letter: str, temperature_c: float, reference_c: float = 0.0
    ) -> dict:
        """Expected meter reading (mV) for a hot-junction temperature (C)."""
        tc = get(type_letter)
        return {
            "emf_mv": round(tc.emf(temperature_c, reference=reference_c), 4),
            "emf_vs_0c_mv": round(tc.emf(temperature_c), 4),
            "type": tc.letter,
        }

    @mcp.tool(annotations=_pure("List the thermocouple types"))
    def thermocouple_types() -> list:
        """The eight letter-designated types with ranges and EMF spans."""
        out = []
        for letter in letters():
            tc = get(letter)
            lo, hi = tc.range
            e_lo, e_hi = tc.emf_range
            out.append({
                "type": letter,
                "range_c": [lo, hi],
                "emf_span_mv": [round(e_lo, 3), round(e_hi, 3)],
            })
        return out

    return mcp


def main() -> None:
    try:
        server = _build_server()
    except ImportError as exc:
        import importlib.util

        if importlib.util.find_spec("mcp") is None:
            raise SystemExit(
                "The MCP extra is not installed. Run: "
                'pip install "thermocouple-its90[mcp]"'
            ) from exc
        # mcp is installed but does not expose what this server expects, so
        # do not send the reader off to reinstall something they already have.
        raise SystemExit(
            f"The installed mcp SDK is missing an expected API: {exc}. "
            "thermocouple-its90 supports mcp 1.7 and later, including 2.x. "
            "Please report this at "
            "https://github.com/dfieser/thermocouple-its90/issues"
        ) from exc
    server.run()


if __name__ == "__main__":  # pragma: no cover
    main()
