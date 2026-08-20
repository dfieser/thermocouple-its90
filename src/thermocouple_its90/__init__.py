"""NIST ITS-90 thermocouple conversions: voltage to temperature and back.

Types B, E, J, K, N, R, S and T, with cold-junction compensation, Seebeck
coefficients, and an inversion verified against every tabulated point of the
NIST reference tables. Pure standard library, no dependencies.

Quickstart::

    from thermocouple_its90 import TypeK

    TypeK.emf(300.0)                        # 12.209 mV, table value
    TypeK.temperature(12.209)               # 300.0 C (ice-bath reference)
    TypeK.temperature(4.096, reference=25.0)  # 124.3 C, meter at room temp
    TypeK.seebeck(300.0)                    # 0.0416 mV/C
"""

from .core import (
    DATA_SOURCE,
    LIBRARY_DATA_VERSION,
    TYPES,
    RangeError,
    Thermocouple,
    get,
    letters,
)

__version__ = "1.0.0"

TypeB = TYPES["B"]
TypeE = TYPES["E"]
TypeJ = TYPES["J"]
TypeK = TYPES["K"]
TypeN = TYPES["N"]
TypeR = TYPES["R"]
TypeS = TYPES["S"]
TypeT = TYPES["T"]

__all__ = [
    "Thermocouple",
    "RangeError",
    "TYPES",
    "get",
    "letters",
    "DATA_SOURCE",
    "LIBRARY_DATA_VERSION",
    "TypeB",
    "TypeE",
    "TypeJ",
    "TypeK",
    "TypeN",
    "TypeR",
    "TypeS",
    "TypeT",
    "__version__",
]
