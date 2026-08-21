"""Generate the repository's banner and figures from the library itself.

Every curve is computed by thermocouple_its90 at run time, so the images can
never drift from the shipped data. Light and dark variants of everything;
the README switches them with <picture> media queries. Regenerate with:

    python docs/make_figures.py
"""

from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "docs"

from thermocouple_its90 import TYPES, TypeB, __version__  # noqa: E402

# The dfieser.com "typeset monograph" palette, shared with the live calculator.
LIGHT = {
    "paper": "#edeff2", "panel": "#f6f8fb", "ink": "#13171e", "ink2": "#464f5e",
    "ink3": "#586170", "rule": "#d3d9e1", "ultra": "#22349c", "signal": "#b83c0e",
}
DARK = {
    "paper": "#0d1016", "panel": "#141922", "ink": "#e6eaf1", "ink2": "#a6afbd",
    "ink3": "#767e8b", "rule": "#262d38", "ultra": "#86a6ff", "signal": "#ff9155",
}

# Line colors per type: platinum types in warm tones, base-metal types in
# cool ones, distinguishable in both themes.
SERIES = {
    "light": {"K": "#22349c", "J": "#0e7490", "E": "#047857", "T": "#5b21b6",
              "N": "#334155", "S": "#b83c0e", "R": "#92400e", "B": "#a16207"},
    "dark": {"K": "#86a6ff", "J": "#3fbfdf", "E": "#34d399", "T": "#b79bff",
             "N": "#94a3b8", "S": "#ff9155", "R": "#e8a24a", "B": "#d9b13b"},
}


def curve(tc, n=400):
    lo, hi = tc.range
    ts = [lo + (hi - lo) * i / n for i in range(n + 1)]
    return ts, [tc.emf(t) for t in ts]


def style_axes(ax, pal):
    ax.set_facecolor(pal["paper"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(pal["ink3"])
    ax.tick_params(colors=pal["ink2"], labelsize=9)
    ax.grid(True, color=pal["rule"], linewidth=0.6, alpha=0.9)
    ax.set_axisbelow(True)


def reference_functions(theme: str, pal: dict) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=200)
    fig.patch.set_facecolor(pal["paper"])
    style_axes(ax, pal)
    for letter in ["E", "J", "K", "N", "T", "S", "R", "B"]:
        ts, es = curve(TYPES[letter])
        ax.plot(ts, es, color=SERIES[theme][letter], linewidth=1.7)
        ax.annotate(letter, (ts[-1], es[-1]), xytext=(5, 0),
                    textcoords="offset points", color=SERIES[theme][letter],
                    fontsize=10, fontweight="bold", va="center",
                    family="serif")
    ax.set_xlim(-290, 1930)
    ax.set_xlabel("temperature (\N{DEGREE SIGN}C)", color=pal["ink2"], fontsize=10, family="serif")
    ax.set_ylabel("EMF (mV, 0 \N{DEGREE SIGN}C reference)", color=pal["ink2"], fontsize=10, family="serif")
    ax.set_title("The eight ITS-90 reference functions, computed by this library",
                 color=pal["ink"], fontsize=12, family="serif", pad=12)
    fig.text(0.905, 0.02, f"thermocouple-its90 v{__version__}",
             color=pal["ink3"], fontsize=7, ha="right", family="monospace")
    fig.tight_layout()
    fig.savefig(OUT / f"reference-functions-{theme}.png",
                facecolor=pal["paper"], bbox_inches="tight")
    plt.close(fig)


def type_b_dip(theme: str, pal: dict) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 3.4), dpi=200)
    fig.patch.set_facecolor(pal["paper"])
    style_axes(ax, pal)
    ts, es = [], []
    n = 600
    for i in range(n + 1):
        t = 0 + 400 * i / n
        ts.append(t)
        es.append(TypeB.emf(t))
    ax.plot(ts, es, color=SERIES[theme]["B"], linewidth=2.0)
    inv_lo, _ = TypeB.invertible_emf_range
    ax.axhline(inv_lo, color=pal["ultra"], linewidth=1.1, linestyle=(0, (5, 3)))
    ax.axhline(0.0, color=pal["ink3"], linewidth=0.8)
    ax.annotate("0.291 mV: inversion starts here",
                (395, inv_lo), xytext=(-8, 8), textcoords="offset points",
                ha="right", color=pal["ultra"], fontsize=9, family="serif")
    tmin = min(range(len(es)), key=lambda i: es[i])
    ax.annotate("the dip: one EMF, two temperatures",
                (ts[tmin], es[tmin]), xytext=(26, 14),
                textcoords="offset points", color=pal["signal"], fontsize=9,
                family="serif",
                arrowprops={"arrowstyle": "-", "color": pal["signal"], "lw": 0.8})
    ax.set_xlabel("temperature (\N{DEGREE SIGN}C)", color=pal["ink2"], fontsize=10, family="serif")
    ax.set_ylabel("EMF (mV)", color=pal["ink2"], fontsize=10, family="serif")
    ax.set_title("Type B below 400 \N{DEGREE SIGN}C: why the library refuses to guess",
                 color=pal["ink"], fontsize=12, family="serif", pad=12)
    fig.tight_layout()
    fig.savefig(OUT / f"type-b-dip-{theme}.png",
                facecolor=pal["paper"], bbox_inches="tight")
    plt.close(fig)


def banner(theme: str, pal: dict) -> None:
    """SVG banner: monograph crop marks, the registration square, real type K
    and type S curves as the motif. 1280x320."""
    w, h = 1280, 320
    # The recognizable image of the field: all eight reference functions on
    # one COMMON temperature and EMF scale, fanning out from the origin.
    x0, x1, y0, y1 = 560, 1195, 42, 278
    t_lo, t_hi = -270.0, 1820.0
    e_lo, e_hi = -10.5, 77.0

    def path_for(tc):
        ts, es = curve(tc, 220)
        pts = []
        for t, e in zip(ts, es):
            x = x0 + (t - t_lo) / (t_hi - t_lo) * (x1 - x0)
            y = y1 - (e - e_lo) / (e_hi - e_lo) * (y1 - y0)
            pts.append(f"{x:.1f},{y:.1f}")
        return "M" + " L".join(pts)

    fan = []
    for letter in ["E", "J", "N", "T", "R", "B"]:
        fan.append(f'<path d="{path_for(TYPES[letter])}" fill="none" '
                   f'stroke="{pal["ink3"]}" stroke-width="1.2" opacity="0.5"/>')
    fan.append(f'<path d="{path_for(TYPES["S"])}" fill="none" '
               f'stroke="{pal["signal"]}" stroke-width="1.8" opacity="0.75"/>')
    fan.append(f'<path d="{path_for(TYPES["K"])}" fill="none" '
               f'stroke="{pal["ultra"]}" stroke-width="2.5"/>')
    fan_svg = "\n  ".join(fan)
    cm = pal["ink3"]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="thermocouple-its90: NIST ITS-90 thermocouple conversion for Python">
  <rect width="{w}" height="{h}" fill="{pal['paper']}"/>
  <!-- crop marks, the site's signature; top-left is the registration mark -->
  <path d="M18 34 V18 H34" fill="none" stroke="{pal['signal']}" stroke-width="2"/>
  <path d="M{w - 34} 18 H{w - 18} V34" fill="none" stroke="{cm}" stroke-width="2"/>
  <path d="M18 {h - 34} V{h - 18} H34" fill="none" stroke="{cm}" stroke-width="2"/>
  <path d="M{w - 34} {h - 18} H{w - 18} V{h - 34}" fill="none" stroke="{cm}" stroke-width="2"/>
  <!-- motif: the eight reference functions on one common scale -->
  {fan_svg}
  <!-- wordmark -->
  <rect x="64" y="92" width="13" height="13" fill="{pal['signal']}"/>
  <text x="92" y="105" font-family="Charter, 'Iowan Old Style', Georgia, serif" font-size="42" font-weight="bold" fill="{pal['ink']}">thermocouple-its90</text>
  <text x="64" y="152" font-family="Charter, Georgia, serif" font-size="19" fill="{pal['ink2']}">NIST ITS-90 thermocouple conversion for Python</text>
  <text x="64" y="196" font-family="ui-monospace, Consolas, monospace" font-size="14" fill="{pal['ink3']}">types B E J K N R S T &#183; cold-junction compensation &#183; MCP server</text>
  <text x="64" y="222" font-family="ui-monospace, Consolas, monospace" font-size="14" fill="{pal['ink3']}">verified against all 12,026 NIST reference points</text>
</svg>
"""
    (OUT / f"banner-{theme}.svg").write_text(svg, encoding="utf-8")


for theme, pal in (("light", LIGHT), ("dark", DARK)):
    banner(theme, pal)
    reference_functions(theme, pal)
    type_b_dip(theme, pal)
    print(f"{theme}: banner + 2 figures")
print("done ->", OUT)
