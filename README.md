# thermocouple-its90

<!-- mcp-name: io.github.dfieser/thermocouple-its90 -->

NIST ITS-90 thermocouple conversion for Python: voltage to temperature and
temperature to voltage for all eight letter-designated types (B, E, J, K, N,
R, S, T), with cold-junction compensation and Seebeck coefficients. The test
suite verifies every one of the 12,026 tabulated points of the NIST reference
tables on every run.

[![Tests](https://github.com/dfieser/thermocouple-its90/actions/workflows/test.yml/badge.svg)](https://github.com/dfieser/thermocouple-its90/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/thermocouple-its90)](https://pypi.org/project/thermocouple-its90/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/thermocouple-its90/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![DOI](https://zenodo.org/badge/1340851774.svg)](https://zenodo.org/badge/latestdoi/1340851774)

Pure standard library, no dependencies, fully typed. A browser version of
this engine runs as a [free online thermocouple
calculator](https://dfieser.com/ThermocoupleConverter/index.html), vendored
from this repository on every release.

## Install

```bash
pip install thermocouple-its90
```

## Convert thermocouple millivolts to temperature

```python
from thermocouple_its90 import TypeK

TypeK.emf(300.0)          # 12.209  (mV at 300 C, 0 C reference: the table value)
TypeK.temperature(12.209) # 300.0   (C, ice-bath reference)
TypeK.seebeck(300.0)      # 0.0416  (mV per C)
TypeK.range               # (-270.0, 1372.0)
```

### Cold-junction compensation

A thermocouple measures the difference between its junctions, and the
reference tables assume the cold junction sits at 0 C. If your meter's
terminals are at room temperature, a direct table lookup is wrong:

```python
from thermocouple_its90 import TypeK

# Meter reads 4.096 mV, terminals at 25 C:
TypeK.temperature(4.096)                  # 100.0 C  <- naive lookup, wrong
TypeK.temperature(4.096, reference=25.0)  # 124.3 C  <- the actual answer
```

All eight types work the same way:

```python
from thermocouple_its90 import get, letters

letters()                       # ['B', 'E', 'J', 'K', 'N', 'R', 'S', 'T']
get("s").emf(1400.0)            # 14.373 mV
get("t").temperature(-4.648)    # -149.98 C (cryogenic ranges included)
```

## Accuracy, verified rather than asserted

- The forward reference functions reproduce **all 12,026 one-degree points**
  of the NIST reference tables within their 0.001 mV print rounding. The
  full comparison runs in CI on every push (`tests/test_full_tables.py`).
- Inversion seeds with the published ITS-90 inverse polynomials and refines
  by Newton iteration on the exact forward function. Round trips agree to
  microdegrees instead of the inverse polynomials' 0.02 to 0.06 C error
  bands.
- Types K, E and T invert over their full cryogenic ranges (to -270 C), below
  where the published inverse polynomials stop.
- Type B is handled with its physics: its EMF is non-monotonic near room
  temperature, so inversion below 0.291 mV (about 250 C) is refused with an
  explanation instead of returning one of two possible answers.

## MCP server for AI agents

Language models mis-remember thermocouple polynomials. The package ships a [Model Context Protocol](https://modelcontextprotocol.io)
server so agents call the verified implementation instead:

```bash
pip install "thermocouple-its90[mcp]"
claude mcp add thermocouple -- thermocouple-its90-mcp
```

Tools: `thermocouple_to_temperature`, `thermocouple_to_emf`,
`thermocouple_types`.

## Data provenance and licensing

Coefficients were machine-parsed, never hand-typed, from the NIST ITS-90
Thermocouple Database (SRD 60, https://its90.nist.gov/). The database reproduces
NIST Monograph 175 (Burns, Scroger, Strouse, Croarkin, and Guthrie, 1993),
a United States government publication not subject to copyright. The
canonical dataset lives in `data/its90.json`; `_data.py` is generated from
it and CI fails if they drift. Code is MIT licensed.

## Related

- [Live calculator](https://dfieser.com/ThermocoupleConverter/index.html),
  this engine in the browser, with worked examples and FAQ
- [More verified engineering calculators](https://dfieser.com/) by the same
  author, including reference-electrode, alloy-composition, diffusion and
  XRD tools
- [lcf-strain-life](https://github.com/dfieser/lcf-strain-life), the same
  library-plus-MCP pattern for low-cycle fatigue analysis

## Citation

If this library is useful in published work, please cite it via the
concept DOI https://doi.org/10.5281/zenodo.22036393, which always resolves to
the latest release (see `CITATION.cff`). Please also cite the underlying reference: Burns, G. W., Scroger, M. G., Strouse, G. F.,
Croarkin, M. C., & Guthrie, W. F. (1993). *Temperature-electromotive force
reference functions and tables for the letter-designated thermocouple types
based on the ITS-90* (NIST Monograph 175). NIST.
