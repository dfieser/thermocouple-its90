#!/usr/bin/env python3
"""Emit the vendored engine-and-data block for the dfieser.com calculator.

The website page https://dfieser.com/ThermocoupleConverter/index.html keeps
this block between ITS90:BEGIN / ITS90:END markers. The library is the only
place the engine and data are edited; the sync-website workflow regenerates
the block on changes and pushes it to the website repository, whose deploy
pipeline then takes over.

The numeric limits (EMF spans, invertible domains, monotonicity) are computed
HERE by the Python library, so the page's validation and the library can
never disagree.

    python codegen/emit_site_block.py --out block.html [--commit abc1234]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from thermocouple_its90 import TYPES, __version__  # noqa: E402
from thermocouple_its90._data import TYPES as RAW  # noqa: E402

ENGINE_JS = r"""
      // Forward reference function: temperature in C -> EMF in mV.
      function emfOf(type, t) {
        const spec = ITS90[type];
        let range = null;
        for (const r of spec.forward) {
          if (t >= r.t_min_c && t <= r.t_max_c) { range = r; break; }
        }
        if (!range) return null;
        let e = 0;
        for (let i = range.coeffs.length - 1; i >= 0; i--) e = e * t + range.coeffs[i];
        if (range.exponential) {
          const x = range.exponential;
          e += x.a0 * Math.exp(x.a1 * (t - x.a2) * (t - x.a2));
        }
        return e;
      }

      // Seebeck coefficient dE/dt in mV/C via the analytic derivative.
      function seebeck(type, t) {
        const spec = ITS90[type];
        let range = null;
        for (const r of spec.forward) {
          if (t >= r.t_min_c && t <= r.t_max_c) { range = r; break; }
        }
        if (!range) return null;
        let d = 0;
        for (let i = range.coeffs.length - 1; i >= 1; i--) d = d * t + i * range.coeffs[i];
        if (range.exponential) {
          const x = range.exponential;
          d += x.a0 * Math.exp(x.a1 * (t - x.a2) * (t - x.a2)) * 2 * x.a1 * (t - x.a2);
        }
        return d;
      }

      // Inverse: EMF in mV -> temperature in C. Published inverse polynomial
      // as the seed where one exists, a linear seed below the published
      // ranges (types K, E and T are tabulated to -270 C but their inverse
      // polynomials stop at -200 C), then Newton on the exact forward
      // function. Callers must check ITS90_LIMITS first; type B is not
      // invertible below its published inverse range because its EMF is
      // non-monotonic near room temperature.
      function tOf(type, e) {
        const spec = ITS90[type];
        const lim = ITS90_LIMITS[type];
        const tLo = spec.forward[0].t_min_c;
        const tHi = spec.forward[spec.forward.length - 1].t_max_c;
        let t = null;
        for (const r of spec.inverse) {
          if (e >= r.mv_min && e <= r.mv_max) {
            t = 0;
            for (let i = r.coeffs.length - 1; i >= 0; i--) t = t * e + r.coeffs[i];
            break;
          }
        }
        if (t === null) {
          const span = lim.emfHi - lim.emfLo;
          t = span === 0 ? tLo : tLo + (e - lim.emfLo) * (tHi - tLo) / span;
        }
        t = Math.min(Math.max(t, tLo), tHi);
        for (let k = 0; k < 12; k++) {
          const f = emfOf(type, t);
          const s = seebeck(type, t);
          if (f === null || s === null || s === 0) break;
          const step = (f - e) / s;
          t = Math.min(Math.max(t - step, tLo), tHi);
          if (Math.abs(step) < 1e-10) break;
        }
        return t;
      }
"""


def js_types() -> str:
    lines = []
    for letter in sorted(RAW):
        spec = RAW[letter]
        fparts = []
        for r in spec["forward"]:
            seg = (f'{{ t_min_c: {r["t_min_c"]!r}, t_max_c: {r["t_max_c"]!r}, '
                   f'coeffs: [{", ".join(repr(c) for c in r["coeffs"])}]')
            if r.get("exponential"):
                x = r["exponential"]
                seg += (f', exponential: {{ a0: {x["a0"]!r}, a1: {x["a1"]!r}, '
                        f'a2: {x["a2"]!r} }}')
            seg += " }"
            fparts.append(seg)
        iparts = [
            f'{{ mv_min: {r["mv_min"]!r}, mv_max: {r["mv_max"]!r}, '
            f'coeffs: [{", ".join(repr(c) for c in r["coeffs"])}] }}'
            for r in spec["inverse"]
        ]
        lines.append(
            f"        {letter}: {{\n          forward: [\n            "
            + ",\n            ".join(fparts)
            + " ],\n          inverse: [\n            "
            + ",\n            ".join(iparts) + " ] }")
    return ",\n".join(lines)


def js_limits() -> str:
    entries = []
    for letter in sorted(TYPES):
        tc = TYPES[letter]
        e_lo, e_hi = tc.emf_range
        inv_lo, inv_hi = tc.invertible_emf_range
        tc._survey()
        entries.append(
            f'        {letter}: {{ emfLo: {e_lo!r}, emfHi: {e_hi!r}, '
            f'invMin: {inv_lo!r}, invMax: {inv_hi!r}, '
            f'monotonic: {"true" if tc._monotonic else "false"} }}')
    return ",\n".join(entries)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--commit", default="local")
    args = ap.parse_args()

    meta = {
        "library": "thermocouple-its90",
        "version": __version__,
        "commit": args.commit,
        "url": "https://github.com/dfieser/thermocouple-its90",
    }
    block = f"""<!-- ITS90:BEGIN vendored engine and data from the thermocouple-its90 library.
     Owned by https://github.com/dfieser/thermocouple-its90 : edit there, never
     here. Its sync-website workflow regenerates this block and pushes it; the
     deploy pipeline's checks still gate the result like any other commit. -->
    <script>
      "use strict";
      /* GENERATED by thermocouple-its90 v{__version__} (commit {args.commit}). DO NOT EDIT. */
      const ITS90_META = {json.dumps(meta)};

      // ITS-90 reference-function and inverse coefficients, machine-parsed
      // from the NIST ITS-90 database (values of NIST Monograph 175) and
      // verified against all 12,026 tabulated reference points in the
      // library's test suite.
      const ITS90 = {{
{js_types()}
      }};

      // Limits computed by the Python library itself, so page validation and
      // library behavior cannot disagree. invMin/invMax bound the invertible
      // EMF domain; type B is non-monotonic and not invertible below 0.291 mV.
      const ITS90_LIMITS = {{
{js_limits()}
      }};
{ENGINE_JS}    </script>
    <!-- ITS90:END -->"""
    pathlib.Path(args.out).write_text(block, encoding="utf-8")
    print(f"wrote {args.out} ({len(block)} chars), v{__version__} commit {args.commit}")


if __name__ == "__main__":
    main()
