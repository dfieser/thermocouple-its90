"""Inverse conversions must round-trip through the exact forward function.

Because the inversion Newton-refines on the reference function itself, round
trips are limited only by iteration convergence, not by the published inverse
polynomials' 0.02 to 0.06 C error bands.
"""

from __future__ import annotations

from thermocouple_its90 import TYPES

GRID_STEPS = 211  # odd and coprime-ish so grid points avoid range seams
ROUNDTRIP_C = 1e-5


def test_roundtrip_full_range():
    for letter, tc in TYPES.items():
        lo, hi = tc.range
        inv_lo, inv_hi = tc.invertible_emf_range
        skipped = 0
        for i in range(GRID_STEPS + 1):
            t = lo + (hi - lo) * i / GRID_STEPS
            e = tc.emf(t)
            if not (inv_lo <= e <= inv_hi):
                skipped += 1  # type B's non-invertible low end, by physics
                continue
            back = tc.temperature(e)
            assert abs(back - t) <= ROUNDTRIP_C, (
                f"type {letter}: {t:.4f} C round-trips to {back:.4f} C")
        if letter == "B":
            # Only the region below ~250 C may be skipped, nothing more.
            assert 0 < skipped <= GRID_STEPS * 0.16, skipped
        else:
            assert skipped == 0, (letter, skipped)


def test_roundtrip_with_reference():
    for _letter, tc in TYPES.items():
        lo, hi = tc.range
        if not (lo <= 25.0 <= hi):
            continue
        t = lo + (hi - lo) * 0.7
        reading = tc.emf(t, reference=25.0)
        assert abs(tc.temperature(reading, reference=25.0) - t) <= ROUNDTRIP_C
