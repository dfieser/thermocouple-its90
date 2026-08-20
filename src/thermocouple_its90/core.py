"""ITS-90 thermocouple conversions for the eight letter-designated types.

The reference functions and inverse polynomials are those of NIST Monograph
175 (Burns, Scroger, Strouse, Croarkin, and Guthrie, 1993), as distributed in
the NIST ITS-90 Thermocouple Database (SRD 60). The coefficients in
``_data.py`` were machine-parsed from the NIST files, never typed by hand, and
this implementation is verified against every one of the 12,026 tabulated
one-degree reference points in the test suite.

Conventions
-----------
- Temperatures are degrees Celsius, EMF is millivolts.
- ``emf(t)`` with the default ``reference=0.0`` returns the table value
  E(t), defined against a 0 degree Celsius reference junction.
- ``temperature(e, reference=25.0)`` performs cold-junction compensation the
  way a bench measurement needs it: the measured EMF plus E(reference) is
  inverted through the exact reference function.
- Inversion seeds with the published ITS-90 inverse polynomials and is then
  refined by Newton iteration on the exact forward function, so round trips
  agree with the reference tables to well inside their 0.001 mV rounding
  rather than carrying the inverse polynomials' 0.02 to 0.06 degree bands.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ._data import DATA_SOURCE, LIBRARY_DATA_VERSION
from ._data import TYPES as _RAW

__all__ = [
    "Thermocouple",
    "RangeError",
    "TYPES",
    "get",
    "DATA_SOURCE",
    "LIBRARY_DATA_VERSION",
]


class RangeError(ValueError):
    """Raised when a temperature or EMF lies outside a type's defined range."""


@dataclass(frozen=True)
class _ForwardRange:
    t_min: float
    t_max: float
    coeffs: tuple[float, ...]
    # Type K carries a0 * exp(a1 * (t - a2)**2) above 0 C; None elsewhere.
    exponential: tuple[float, float, float] | None


@dataclass(frozen=True)
class _InverseRange:
    e_min: float
    e_max: float
    coeffs: tuple[float, ...]
    error_band_c: str


class Thermocouple:
    """One letter-designated thermocouple type on the ITS-90 scale.

    Instances are exposed as module attributes (``TypeK``, ``TypeJ``, ...)
    and through :func:`get`; there is no reason to construct your own.
    """

    def __init__(self, letter: str, spec: Mapping[str, object]) -> None:
        self.letter = letter
        self._forward: list[_ForwardRange] = [
            _ForwardRange(
                t_min=r["t_min_c"],
                t_max=r["t_max_c"],
                coeffs=tuple(r["coeffs"]),
                exponential=(
                    (r["exponential"]["a0"], r["exponential"]["a1"],
                     r["exponential"]["a2"])
                    if r.get("exponential") else None
                ),
            )
            for r in spec["forward"]  # type: ignore[index]
        ]
        self._inverse: list[_InverseRange] = [
            _InverseRange(
                e_min=r["mv_min"],
                e_max=r["mv_max"],
                coeffs=tuple(r["coeffs"]),
                error_band_c=str(r.get("error_band_c", "")),
            )
            for r in spec["inverse"]  # type: ignore[index]
        ]

    # ---- public metadata -------------------------------------------------

    @property
    def range(self) -> tuple[float, float]:
        """Defined temperature range in degrees Celsius, (low, high)."""
        return (self._forward[0].t_min, self._forward[-1].t_max)

    @property
    def emf_range(self) -> tuple[float, float]:
        """EMF at the range endpoints, in millivolts versus a 0 C reference."""
        lo, hi = self.range
        return (self._emf_at(lo), self._emf_at(hi))

    def _survey(self) -> None:
        """Sample the reference function once to learn its true shape.

        Type B is the reason this exists: its EMF dips below zero near 21 C
        and only becomes single-valued above the start of its published
        inverse range (0.291 mV, about 250 C), which is the physical reason
        type B is never used at low temperature. The survey finds the true
        EMF extrema and whether the function is monotonic; for a
        non-monotonic type the invertible domain is the published inverse
        hull, where the function is single-valued.
        """
        if hasattr(self, "_emf_min"):
            return
        lo, hi = self.range
        steps = max(int((hi - lo) * 4), 8)  # 0.25 C sampling
        e_prev = self._emf_at(lo)
        e_min = e_max = e_prev
        monotonic_up = monotonic_down = True
        for i in range(1, steps + 1):
            e = self._emf_at(lo + (hi - lo) * i / steps)
            if e < e_prev:
                monotonic_up = False
            if e > e_prev:
                monotonic_down = False
            e_min = min(e_min, e)
            e_max = max(e_max, e)
            e_prev = e
        self._emf_min = e_min
        self._emf_max = e_max
        self._monotonic = monotonic_up or monotonic_down
        if self._monotonic:
            self._inv_min = e_min
            self._inv_max = e_max
        else:
            self._inv_min = min(r.e_min for r in self._inverse)
            self._inv_max = max(r.e_max for r in self._inverse)

    @property
    def invertible_emf_range(self) -> tuple[float, float]:
        """The EMF span (mV) on which ``temperature`` is defined.

        Equal to the true EMF extrema for the seven monotonic types; for
        type B it is the published inverse hull, because below 0.291 mV the
        same EMF corresponds to two temperatures.
        """
        self._survey()
        return (self._inv_min, self._inv_max)

    # ---- forward: temperature -> EMF --------------------------------------

    def _find_forward(self, t: float) -> _ForwardRange:
        for r in self._forward:
            if r.t_min <= t <= r.t_max:
                return r
        lo, hi = self.range
        raise RangeError(
            f"type {self.letter} is defined from {lo:g} to {hi:g} C; "
            f"got {t:g} C"
        )

    def _emf_at(self, t: float) -> float:
        r = self._find_forward(t)
        e = 0.0
        for c in reversed(r.coeffs):
            e = e * t + c
        if r.exponential is not None:
            a0, a1, a2 = r.exponential
            e += a0 * math.exp(a1 * (t - a2) ** 2)
        return e

    def emf(self, t: float, reference: float = 0.0) -> float:
        """EMF in millivolts at hot-junction temperature ``t``.

        With the default ``reference=0.0`` this is the table value E(t).
        A nonzero ``reference`` returns what a meter at that cold-junction
        temperature actually reads: E(t) - E(reference).
        """
        if reference == 0.0:
            return self._emf_at(t)
        return self._emf_at(t) - self._emf_at(reference)

    def seebeck(self, t: float) -> float:
        """Seebeck coefficient dE/dt in millivolts per degree Celsius."""
        r = self._find_forward(t)
        d = 0.0
        for i in range(len(r.coeffs) - 1, 0, -1):
            d = d * t + i * r.coeffs[i]
        if r.exponential is not None:
            a0, a1, a2 = r.exponential
            d += a0 * math.exp(a1 * (t - a2) ** 2) * 2.0 * a1 * (t - a2)
        return d

    # ---- inverse: EMF -> temperature --------------------------------------

    def _seed(self, e: float) -> float:
        for r in self._inverse:
            if r.e_min <= e <= r.e_max:
                t = 0.0
                for c in reversed(r.coeffs):
                    t = t * e + c
                return t
        # The published inverse ranges can be a hair narrower than the full
        # EMF span; fall back to a linear seed, Newton does the rest.
        lo, hi = self.range
        e_lo, e_hi = self.emf_range
        if e_hi == e_lo:  # pragma: no cover - cannot happen for real types
            return lo
        return lo + (e - e_lo) * (hi - lo) / (e_hi - e_lo)

    def temperature(self, emf: float, reference: float = 0.0) -> float:
        """Hot-junction temperature in Celsius for a measured ``emf`` in mV.

        ``reference`` is the cold-junction temperature in Celsius; the
        measured EMF plus E(reference) is inverted through the exact
        reference function (published inverse polynomial seed, Newton
        refinement).
        """
        e_hot = emf + (self._emf_at(reference) if reference != 0.0 else 0.0)
        self._survey()
        if not (self._inv_min <= e_hot <= self._inv_max):
            detail = ""
            if not self._monotonic and e_hot >= self._emf_min:
                detail = (
                    " (the reference function is non-monotonic there, so the "
                    "EMF maps to two temperatures; this is why type B is not "
                    "used at low temperature)"
                )
            raise RangeError(
                f"E = {e_hot:.3f} mV (measured {emf:.3f} plus reference "
                f"junction) is outside type {self.letter}'s invertible span "
                f"{self._inv_min:.3f} to {self._inv_max:.3f} mV{detail}"
            )
        t_lo, t_hi = self.range
        t = min(max(self._seed(e_hot), t_lo), t_hi)
        for _ in range(12):
            f = self._emf_at(t)
            s = self.seebeck(t)
            if s == 0.0:  # pragma: no cover - defensive
                break
            step = (f - e_hot) / s
            t = min(max(t - step, t_lo), t_hi)
            if abs(step) < 1e-10:
                break
        return t

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        lo, hi = self.range
        return f"Thermocouple(type {self.letter}, {lo:g} to {hi:g} C)"


TYPES: dict[str, Thermocouple] = {
    letter: Thermocouple(letter, spec) for letter, spec in _RAW.items()
}


def get(letter: str) -> Thermocouple:
    """Look up a type by letter, case-insensitively: ``get("k")``."""
    key = letter.strip().upper()
    if key not in TYPES:
        raise KeyError(
            f"unknown thermocouple type {letter!r}; "
            f"choose from {', '.join(sorted(TYPES))}"
        )
    return TYPES[key]


def letters() -> Sequence[str]:
    """The eight letter designations, sorted."""
    return sorted(TYPES)
