"""Golden vectors: hand-picked NIST table anchors and the worked CJC case.

The inverse tolerance is physics, not hand-waving: a table value rounded to
0.001 mV can move the inverted temperature by up to (0.0005 mV / Seebeck).
Type T at -150 C, with 22 uV/C, is the canonical case: the table's own
rounding is worth 0.022 C there and the implementation must not be blamed
for it.
"""

from __future__ import annotations

import json
import pathlib

from thermocouple_its90 import TypeK, get

VECTORS = json.loads(
    (pathlib.Path(__file__).parents[1] / "data" / "golden_vectors.json")
    .read_text(encoding="utf-8"))


def test_forward_anchors():
    for v in VECTORS:
        tc = get(v["type"])
        assert abs(tc.emf(v["t_c"]) - v["mv"]) <= 0.0005 + 1e-9, v


def test_inverse_anchors_within_rounding_physics():
    for v in VECTORS:
        tc = get(v["type"])
        tol = 0.0005 / abs(tc.seebeck(v["t_c"])) + 1e-6
        assert abs(tc.temperature(v["mv"]) - v["t_c"]) <= tol, (v, tol)


def test_cold_junction_worked_example():
    # The live calculator's worked example: 4.096 mV measured, meter at 25 C.
    assert abs(TypeK.emf(25.0) - 1.000) <= 0.0005
    t = TypeK.temperature(4.096, reference=25.0)
    assert abs(t - 124.31) <= 0.02
    # And the trap the example teaches: the naive lookup lands near 100 C.
    assert abs(TypeK.temperature(4.096) - 100.0) <= 0.02
