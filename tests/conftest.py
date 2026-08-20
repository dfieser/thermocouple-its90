"""Shared fixtures: the NIST reference tables, parsed once per session.

The .tab files are the full ITS-90 reference tables as distributed by the
NIST ITS-90 Thermocouple Database (SRD 60), reproducing NIST Monograph 175,
a United States government publication not subject to copyright. They are
checked in so the verification suite is hermetic: no network, no flakes.
"""

from __future__ import annotations

import pathlib

import pytest

NIST_DIR = pathlib.Path(__file__).parent / "data" / "nist"

# Tabulated one-degree points per type, established when the dataset was
# first machine-parsed and verified. The parser must reproduce these counts
# exactly; a change means the parse, not the physics, broke.
EXPECTED_POINTS = {
    "B": 1821, "E": 1271, "J": 1411, "K": 1643,
    "N": 1571, "R": 1819, "S": 1819, "T": 671,
}


def parse_table(letter: str) -> dict:
    """Parse a NIST type_<x>.tab reference table into {t_celsius: emf_mv}.

    Rows are '<base> v0 v1 ... v9' where column i is the value at
    base + i degrees for non-negative bases and base - i for negative
    bases (the negative table counts away from zero).
    """
    text = (NIST_DIR / f"type_{letter.lower()}.tab").read_text(
        encoding="utf-8", errors="replace")
    points: dict = {}
    in_table = False
    direction = 1
    for line in text.splitlines():
        parts = line.split()
        # Each table page declares its own column direction in the header
        # ("C 0 1 2 ..." ascending, "C 0 -1 -2 ..." descending). Reading it
        # structurally matters: type B's EMF dips negative just above 0 C,
        # so guessing direction from the values themselves misparses its
        # first row.
        if len(parts) >= 3 and parts[1] == "0" and parts[2] in ("1", "-1"):
            direction = 1 if parts[2] == "1" else -1
            continue
        # Only rows between a "Thermoelectric Voltage" banner and the next
        # asterisk divider are table data; coefficient listings follow.
        if "Thermoelectric Voltage" in line:
            in_table = True
            continue
        if line.lstrip().startswith("*"):
            in_table = False
            continue
        if not in_table or len(parts) < 2:
            continue
        try:
            values = [float(p) for p in parts]
        except ValueError:
            continue
        base = values[0]
        if base != int(base):
            continue
        # Eleven columns per full row; column 10 deliberately repeats the
        # next row's column 0, which doubles as a consistency check here.
        for i, mv in enumerate(values[1:]):
            t = base + direction * i
            if t in points and abs(points[t] - mv) > 1e-9:
                raise AssertionError(
                    f"type {letter}: conflicting table values at {t} C: "
                    f"{points[t]} vs {mv}")
            points[t] = mv
    return points


@pytest.fixture(scope="session")
def nist_tables() -> dict:
    return {letter: parse_table(letter) for letter in EXPECTED_POINTS}
