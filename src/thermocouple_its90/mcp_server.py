"""MCP server exposing the ITS-90 conversions as tools for AI agents.

Install the extra and register the command with your agent runtime::

    pip install "thermocouple-its90[mcp]"
    thermocouple-its90-mcp          # stdio transport

For Claude Code: ``claude mcp add thermocouple -- thermocouple-its90-mcp``

The tools exist because language models reliably mis-remember thermocouple
polynomials; a verified lookup beats a confident guess.
"""

from __future__ import annotations

from . import get, letters


def _build_server():  # pragma: no cover - exercised via the MCP runtime
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "thermocouple-its90",
        instructions=(
            "ITS-90 thermocouple conversions (NIST Monograph 175), types "
            "B, E, J, K, N, R, S, T. Temperatures in Celsius, EMF in mV. "
            "All conversions include explicit cold-junction handling."
        ),
    )

    @mcp.tool()
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

    @mcp.tool()
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

    @mcp.tool()
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
        raise SystemExit(
            "The MCP extra is not installed. Run: "
            'pip install "thermocouple-its90[mcp]"'
        ) from exc
    server.run()


if __name__ == "__main__":  # pragma: no cover
    main()
