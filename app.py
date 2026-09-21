"""
app.py
======

Most między przeglądarką a niezmienionym `core.py`.

Przeglądarka (JavaScript) odpowiada wyłącznie za interfejs i za szybki podgląd
na zgrubnej siatce. Wynik, który wychodzi z aplikacji — obwiednia odtworzona
i plik CSV — pochodzi zawsze stąd, czyli z prawdziwego `core.run()` na pełnej
siatce N = 261 569 punktów, z `scipy.signal.savgol_filter` i całą resztą.

Dwie ingerencje w środowisko, żadna nie dotyka `core.py` ani wyników:

  (1) `pandas` jest podmieniany na pusty moduł, jeśli nie da się go
      zaimportować. `core.py` importuje pandas, ale nigdzie go nie używa,
      a pobranie prawdziwego pakietu kosztowałoby kilkanaście megabajtów.

  (2) `plt.tight_layout` jest na czas przebiegu zamieniany na pustą funkcję.
      tight_layout wymusza pełne renderowanie rysunku 2x5 z krzywymi po
      261 569 punktów, co w przeglądarce trwa kilkadziesiąt sekund. Rysunku
      i tak nie pokazujemy — wykresy rysuje interfejs z tablic liczbowych.
      Operacja dotyczy wyłącznie układu graficznego, żadna liczba się nie
      zmienia. Ustaw `skip_layout=False`, aby to wyłączyć.
"""

import contextlib
import io
import json
import sys
import time
import types

# ---- (1) atrapa pandas -------------------------------------------------------
if "pandas" not in sys.modules:
    try:
        import pandas  # noqa: F401
    except Exception:
        sys.modules["pandas"] = types.ModuleType("pandas")

import numpy as np
import matplotlib.pyplot as plt

import builders
import core

_ORIG_TIGHT = plt.tight_layout

# ostatni przebieg w pełnej rozdzielczości — do zbudowania CSV
_LAST = {}


# ----------------------------------------------------------------- POMOCNICZE
def _line(fig, axis, index):
    """Dane z krzywej rysunku produkowanego przez core.run(), albo None."""
    try:
        return np.asarray(fig.axes[axis].lines[index].get_ydata(), dtype=float)
    except Exception:
        return None


def _line_x(fig, axis, index):
    try:
        return np.asarray(fig.axes[axis].lines[index].get_xdata(), dtype=float)
    except Exception:
        return None


def _thin(a, n=4000):
    """Równomierne przerzedzenie — do przebiegów czasowych."""
    if a is None:
        return None
    a = np.asarray(a, dtype=float)
    if a.size <= n:
        return a
    idx = np.linspace(0, a.size - 1, n).astype(int)
    return a[idx]


def _thin_log(f, y, n=2200, mode="max"):
    """Przerzedzenie widma po koszykach logarytmicznych.

    W każdym koszyku zostaje wartość skrajna, więc szczyty i zera nie giną —
    inaczej niż przy zwykłym co n-tym punkcie.
    """
    if f is None or y is None:
        return None, None
    f = np.asarray(f, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = f > 0
    f, y = f[ok], y[ok]
    if f.size <= n:
        return f, y
    edges = np.logspace(np.log10(f[0]), np.log10(f[-1]), n + 1)
    pos = np.searchsorted(edges, f, side="right") - 1
    pos = np.clip(pos, 0, n - 1)
    of, oy = [], []
    start = 0
    for b in range(n):
        end = start
        while end < pos.size and pos[end] == b:
            end += 1
        if end > start:
            seg = y[start:end]
            j = start + (int(np.argmax(np.abs(seg))) if mode == "abs" else int(np.argmax(seg)))
            of.append(f[j])
            oy.append(y[j])
        start = end
    return np.asarray(of), np.asarray(oy)


def _l(a):
    """numpy -> lista JSON-owalna, bez NaN i nieskończoności."""
    if a is None:
        return []
    a = np.asarray(a, dtype=float)
    a = np.where(np.isfinite(a), a, 0.0)
    return [float(v) for v in a]


# ------------------------------------------------------------------ PRZEBIEG
def run_config(cfg_json, skip_layout=True):
    """Pełny przebieg core.run() dla konfiguracji z interfejsu.

    cfg_json: tekst JSON postaci
        {"envelope": {...}, "filter": {"kind":"spline","method":"pchip",
                                       "knots_f":[...], "knots_v":[...]}}

    Zwraca tekst JSON z metadanymi i przerzedzonymi krzywymi do rysowania.
    Pełne tablice zostają po stronie Pythona — pobiera się je przez
    get_xrec() i get_t().
    """
    cfg = json.loads(cfg_json)

    x = builders.build_envelope(cfg.get("envelope", {"kind": "rect"}))
    mult = builders.build_filter(cfg.get("filter", {"kind": "original"}), builders.FREQ)

    buf = io.StringIO()
    t0 = time.time()
    if skip_layout:
        plt.tight_layout = lambda *a, **k: None
    try:
        with contextlib.redirect_stdout(buf):
            fig = core.run(x, mult)
    finally:
        plt.tight_layout = _ORIG_TIGHT
    elapsed = time.time() - t0

    # --- odczyt tablic z krzywych rysunku (bez dotykania core.py)
    t = np.asarray(core.t, dtype=float)
    x_in = _line(fig, 0, 0)
    cdf_in = _line(fig, 1, 0)
    sin_in = _line(fig, 2, 0)
    Fi = _line(fig, 3, 0)
    Fr = _line(fig, 3, 1)
    f_pos = _line_x(fig, 4, 0)
    P_in = _line(fig, 4, 0)
    x_rec = _line(fig, 5, 0)
    phase = _line(fig, 6, 0)
    f_rec = _line(fig, 7, 0)
    sin_rec = _line(fig, 7, 1)
    P_out = _line(fig, 9, 0)
    P_rec = _line(fig, 9, 1)
    cdf_rec = _line(fig, 6, 2)

    plt.close(fig)

    # Im p(f) po nałożeniu splajnu — dokładnie ta tablica, którą core.run()
    # podaje dalej jako część urojoną scaled_F
    Fi_mult = None if Fi is None else Fi * mult

    _LAST["t"] = t
    _LAST["x_rec"] = x_rec if x_rec is not None else np.zeros_like(t)

    peak = float(np.max(np.abs(_LAST["x_rec"]))) or 1.0
    area = float(np.sum(x) * builders.DT)

    fP, P_in_d = _thin_log(f_pos, P_in)
    _, P_out_d = _thin_log(f_pos, P_out)
    _, P_rec_d = _thin_log(f_pos, P_rec)

    # części Re/Im na tej samej siatce log, wartość o największym module
    half = None if Fi is None else builders.FREQ > 0
    fF = None if half is None else builders.FREQ[half]
    fI, Fi_d = _thin_log(fF, None if Fi is None else Fi[half], mode="abs")
    _, Fr_d = _thin_log(fF, None if Fr is None else Fr[half], mode="abs")
    _, Fim_d = _thin_log(fF, None if Fi_mult is None else Fi_mult[half], mode="abs")

    out = {
        "meta": {
            "N": int(core.N),
            "dt": builders.DT,
            "df": builders.DF,
            "nyq": builders.NYQUIST,
            "elapsed": elapsed,
            "stdout": buf.getvalue(),
            "peak": peak,
            "area": area,
            "max_before": float(np.max(P_in)) if P_in is not None else 0.0,
            "max_after": float(np.max(P_out)) if P_out is not None else 0.0,
        },
        "plots": {
            "t": _l(_thin(t)),
            "x_in": _l(_thin(x_in)),
            "x_rec": _l(_thin(x_rec)),
            "cdf_in": _l(_thin(cdf_in)),
            "sin_in": _l(_thin(sin_in)),
            "phase": _l(_thin(phase)),
            "f_rec": _l(_thin(f_rec)),
            "cdf_rec": _l(_thin(cdf_rec)),
            "sin_rec": _l(_thin(sin_rec)),
            "f": _l(fP),
            "P_in": _l(P_in_d),
            "P_out": _l(P_out_d),
            "P_rec": _l(P_rec_d),
            "fF": _l(fI),
            "Fi": _l(Fi_d),
            "Fr": _l(Fr_d),
            "Fi_mult": _l(Fim_d),
        },
    }
    return json.dumps(out)


def get_xrec():
    """Pełna, nieprzerzedzona obwiednia odtworzona — bajty float64."""
    a = _LAST.get("x_rec")
    if a is None:
        return b""
    return np.ascontiguousarray(a, dtype="<f8").tobytes()


def get_t():
    """Pełna oś czasu — bajty float64."""
    a = _LAST.get("t")
    if a is None:
        return b""
    return np.ascontiguousarray(a, dtype="<f8").tobytes()


def selftest():
    """Sanity check: domyślna konfiguracja musi dać te same liczby co oryginał."""
    cfg = json.dumps({"envelope": {"kind": "rect"},
                      "filter": {"kind": "original", "factor": 44.0}})
    res = json.loads(run_config(cfg))
    ref = builders.original_multiplier(builders.FREQ, 44.0)
    same = bool(np.array_equal(ref, builders.build_filter(
        {"kind": "original", "factor": 44.0}, builders.FREQ)))
    return json.dumps({"multiplier_bit_identical": same,
                       "max_before": res["meta"]["max_before"],
                       "max_after": res["meta"]["max_after"],
                       "elapsed": res["meta"]["elapsed"]})
