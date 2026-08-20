"""The headline guarantee: every tabulated NIST point, within table rounding.

The reference tables print EMF to 0.001 mV, so a correct implementation may
differ from a printed value by at most half that rounding step. The dataset
was verified at this tolerance when first parsed (maximum observed deviation
0.000500 mV); this suite re-proves it on every run, all 12,026 points.
"""

from __future__ import annotations

from thermocouple_its90 import TYPES

from .conftest import EXPECTED_POINTS

HALF_ROUNDING_MV = 0.0005 + 1e-9


def test_point_counts(nist_tables):
    for letter, expected in EXPECTED_POINTS.items():
        assert len(nist_tables[letter]) == expected, letter
    assert sum(EXPECTED_POINTS.values()) == 12026


def test_every_tabulated_point(nist_tables):
    worst = {}
    for letter, table in nist_tables.items():
        tc = TYPES[letter]
        max_dev = 0.0
        for t, mv in table.items():
            dev = abs(tc.emf(t) - mv)
            if dev > max_dev:
                max_dev = dev
            assert dev <= HALF_ROUNDING_MV, (
                f"type {letter} at {t} C: computed {tc.emf(t):.6f}, "
                f"table {mv:.3f}, deviation {dev:.6f} mV")
        worst[letter] = max_dev
    # Belt and braces: the worst deviation per type stays at rounding level.
    assert max(worst.values()) <= HALF_ROUNDING_MV
