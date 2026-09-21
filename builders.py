"""
builders.py
===========

Dwa jedyne miejsca, w których wolno coś zmieniać:

  * `build_envelope(spec)`        -> tablica `x` podawana do core.run()
  * `build_filter(spec, freq)`    -> tablica `new_filter_multiplier`

Obie funkcje produkują tablice o dokładnie takim samym znaczeniu i takiej samej
normalizacji, jakiej używa oryginał. Nic tu nie dotyka rdzenia obliczeniowego.
"""

import numpy as np
from scipy.interpolate import PchipInterpolator, CubicSpline

import core

T = core.t
DT = float(core.t[1] - core.t[0])
N = int(core.N)

# Identyczna definicja jak w core.run() — liczona tu tylko po to, aby móc
# zbudować tablicę mnożnika ZANIM wywołamy run().
FREQ = np.fft.fftshift(np.fft.fftfreq(N, d=DT))
NYQUIST = float(np.max(FREQ))
DF = float(1.0 / (N * DT))


# --------------------------------------------------------------- OBWIEDNIA
def _spline_values(knot_x, knot_y, grid, method="pchip"):
    knot_x = np.asarray(knot_x, dtype=float)
    knot_y = np.asarray(knot_y, dtype=float)
    order = np.argsort(knot_x)
    knot_x, knot_y = knot_x[order], knot_y[order]
    keep = np.concatenate(([True], np.diff(knot_x) > 0))
    knot_x, knot_y = knot_x[keep], knot_y[keep]
    if knot_x.size < 2:
        raise ValueError("Splajn wymaga co najmniej 2 punktów o różnych odciętych.")
    if method == "cubic":
        spl = CubicSpline(knot_x, knot_y)
    else:
        spl = PchipInterpolator(knot_x, knot_y)
    clipped = np.clip(grid, knot_x[0], knot_x[-1])
    return spl(clipped), knot_x, knot_y


def flat_top(x, dt, width=2.0, edge=0.15):
    """Plateau o gładkich kosinusowych zboczach (okno Tukeya).

    Nie ma odpowiednika w core.py — obwiednia bez ostrych krawędzi, więc bez
    nieskończonych pochodnych prostokąta i bez towarzyszącego im dzwonienia
    w widmie. Normalizacja identyczna jak we wszystkich generatorach: pole 2*pi.
    """
    half = width / 2.0
    edge = min(edge, half)
    a = np.abs(x)
    vals = np.where(
        a <= half - edge,
        1.0,
        np.where(a < half, 0.5 * (1.0 + np.cos(np.pi * (a - (half - edge)) / edge)), 0.0),
    )
    Norm = 2 * np.pi / (np.sum(vals) * dt)
    return vals * Norm


def build_envelope(spec):
    """Zwraca tablicę `x` na siatce core.t."""
    kind = spec.get("kind", "rect")

    if kind == "gauss":
        return core.Gauss(T, float(spec.get("mu", 0.0)), float(spec.get("sigma", 0.2)))
    if kind == "pseudo_beta":
        return core.pseudo_beta(T, DT, float(spec.get("alpha", 15.0)))
    if kind == "rect":
        return core.rect(T, DT)
    if kind == "flat":
        return flat_top(T, DT, float(spec.get("width", 2.0)), float(spec.get("edge", 0.15)))
    if kind == "tri":
        # UWAGA: funkcja `tri` w oryginale używa `vals` przed przypisaniem
        # (NameError). Celowo NIE poprawiamy oryginału — wywołanie się wysypie,
        # a aplikacja pokaże czytelny komunikat.
        return core.tri(T, DT, float(spec.get("width", 2.0)))
    if kind == "semicirc":
        return core.semicirc(T, DT, float(spec.get("width", 2.0)))
    if kind == "catpulse":
        return core.catpulse(T, DT)

    if kind == "spline":
        vals, _, _ = _spline_values(
            spec["knots_t"], spec["knots_v"], T, spec.get("method", "pchip")
        )
        kx = np.sort(np.asarray(spec["knots_t"], dtype=float))
        vals = np.where((T < kx[0]) | (T > kx[-1]), 0.0, vals)
        vals = np.clip(vals, 0.0, None)
        total = np.sum(vals)
        if total <= 0:
            raise ValueError("Obwiednia splajnowa jest wszędzie zerowa.")
        Norm = 2 * np.pi / (total * DT)
        return vals * Norm

    raise ValueError("Nieznany typ obwiedni: %s" % kind)


# ------------------------------------------------------------------- FILTR
def original_multiplier(freq, factor=44.0):
    """Dokładnie to, co liczy oryginał: exp(-|f|**Factor1)."""
    with np.errstate(over="ignore", invalid="ignore"):
        return np.exp(-np.abs(freq) ** float(factor))


def knots_from_factor(factor=44.0, fmin=None, fmax=None):
    """Węzły startowe odwzorowujące exp(-|f|**factor) — zagęszczone przy zboczu."""
    fmin = DF if fmin is None else float(fmin)
    fmax = NYQUIST if fmax is None else float(fmax)
    base = np.array(
        [fmin, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2, 1.5, 3.0, fmax]
    )
    base = np.unique(np.clip(base, fmin, fmax))
    vals = original_multiplier(base, factor)
    return base.tolist(), vals.tolist()


def build_filter(spec, freq=None):
    """Zwraca tablicę `new_filter_multiplier` na siatce freq."""
    freq = FREQ if freq is None else freq
    kind = spec.get("kind", "original")

    if kind == "original":
        return original_multiplier(freq, spec.get("factor", 44.0))

    if kind == "spline":
        kx = np.asarray(spec["knots_f"], dtype=float)
        ky = np.asarray(spec["knots_v"], dtype=float)
        if np.any(kx <= 0):
            raise ValueError("Węzły filtra muszą mieć częstotliwość > 0 (oś log).")
        # interpolacja po log10(f) — filtr jest funkcją |f|, więc wynik jest
        # parzysty, dokładnie jak exp(-|f|**44)
        vals, lkx, _ = _spline_values(
            np.log10(kx), ky, np.log10(np.maximum(np.abs(freq), DF * 1e-3)),
            spec.get("method", "pchip"),
        )
        vals = np.clip(vals, 0.0, 1.0)
        return vals

    raise ValueError("Nieznany typ filtra: %s" % kind)
