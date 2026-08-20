"""API contract: lookups, validation errors, metadata, generated-data drift."""

from __future__ import annotations

import json
import pathlib

import pytest

from thermocouple_its90 import TYPES, RangeError, TypeB, TypeK, get, letters
from thermocouple_its90._data import TYPES as RAW


def test_letters_and_lookup():
    assert list(letters()) == ["B", "E", "J", "K", "N", "R", "S", "T"]
    assert get("k") is TypeK
    with pytest.raises(KeyError):
        get("Q")


def test_ranges():
    assert TypeK.range == (-270.0, 1372.0)
    assert TypeB.range == (0.0, 1820.0)
    lo, hi = TypeK.emf_range
    assert abs(lo - -6.458) < 0.0005 and abs(hi - 54.886) < 0.0005


def test_range_errors():
    with pytest.raises(RangeError):
        TypeK.emf(1500.0)
    with pytest.raises(RangeError):
        TypeK.temperature(99.0)
    with pytest.raises(RangeError):
        TypeK.temperature(0.0, reference=2000.0)


def test_type_b_invertible_domain():
    """Type B's EMF dips negative near 21 C; inversion must refuse the
    two-valued region and explain itself."""
    inv_lo, inv_hi = TypeB.invertible_emf_range
    assert abs(inv_lo - 0.291) < 0.001 and abs(inv_hi - 13.820) < 0.001
    assert TypeB.emf(21.0) < 0.0  # the dip is real
    with pytest.raises(RangeError, match="non-monotonic"):
        TypeB.temperature(0.05)


def test_cryogenic_inversion_below_published_inverse_ranges():
    """K, E and T are monotonic below -200 C even though the published
    inverse polynomials stop there; Newton on the exact function covers it."""
    for tc, t in ((TYPES["K"], -240.0), (TYPES["E"], -250.0), (TYPES["T"], -230.0)):
        assert abs(tc.temperature(tc.emf(t)) - t) <= 1e-4


def test_seebeck_sanity():
    # The classic type K rule of thumb near room temperature.
    assert abs(TypeK.seebeck(25.0) * 1000 - 40.5) < 0.5


def test_generated_module_matches_canonical_json():
    """_data.py is generated from data/its90.json; they must never drift."""
    canonical = json.loads(
        (pathlib.Path(__file__).parents[1] / "data" / "its90.json")
        .read_text(encoding="utf-8"))["types"]
    assert RAW == canonical


def test_every_type_constructed():
    assert set(TYPES) == {"B", "E", "J", "K", "N", "R", "S", "T"}
