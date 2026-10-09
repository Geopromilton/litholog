"""Geotechnical soil and rock classification utilities (USCS, SPT N60, RQD).

Implements ASTM D2487 Unified Soil Classification System (USCS),
ASTM D1586 / D6066 SPT N-value energy correction (N60), and
Deere (1968) Rock Quality Designation (RQD) rock mass rating.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class USCSResult:
    code: str
    name: str
    category: str
    description: str

    def __iter__(self):
        return iter((self.code, self.name))


def classify_uscs(
    gravel_pct: float,
    sand_pct: float,
    fines_pct: float,
    ll: Optional[float] = None,
    pl: Optional[float] = None,
    pi: Optional[float] = None,
    cu: Optional[float] = None,
    cc: Optional[float] = None,
    organic: bool = False,
) -> USCSResult:
    """Classify soil using ASTM D2487 Unified Soil Classification System (USCS).

    Parameters
    ----------
    gravel_pct : float
        Percentage retained on 4.75 mm (No. 4) sieve (0-100).
    sand_pct : float
        Percentage passing 4.75 mm and retained on 75 µm (No. 200) sieve (0-100).
    fines_pct : float
        Percentage passing 75 µm (No. 200) sieve (0-100).
    ll : float, optional
        Liquid limit (%).
    pl : float, optional
        Plastic limit (%).
    pi : float, optional
        Plasticity index (%) [calculated as LL - PL if omitted].
    cu : float, optional
        Uniformity coefficient (D60 / D10).
    cc : float, optional
        Coefficient of curvature (D30^2 / (D10 * D60)).
    organic : bool, default False
        True if soil contains organic matter.
    """
    total = gravel_pct + sand_pct + fines_pct
    if total > 0 and not math.isclose(total, 100.0, rel_tol=1e-2):
        factor = 100.0 / total
        gravel_pct *= factor
        sand_pct *= factor
        fines_pct *= factor

    if pi is None and ll is not None and pl is not None:
        pi = ll - pl
    elif pi is not None and ll is not None and pl is None:
        pl = ll - pi

    # A-line equation on Casagrande plasticity chart
    # A-line: PI = 0.73 * (LL - 20)
    a_line = (0.73 * (ll - 20)) if ll is not None else None

    # 1. Fine-grained soils: 50% or more passes No. 200 sieve
    if fines_pct >= 50.0:
        if organic:
            if ll is not None and ll >= 50:
                return USCSResult("OH", "Organic clay / silt of high plasticity", "Fine-grained", "Organic clay / silt (LL >= 50)")
            return USCSResult("OL", "Organic silt / clay of low plasticity", "Fine-grained", "Organic silt / clay (LL < 50)")

        if ll is not None and pi is not None:
            if ll >= 50:
                if a_line is not None and pi >= a_line:
                    return USCSResult("CH", "Fat clay", "Fine-grained", "Inorganic clay of high plasticity")
                return USCSResult("MH", "Elastic silt", "Fine-grained", "Inorganic silt of high plasticity")
            else:
                # LL < 50
                # Hatch zone on Casagrande chart (CL-ML): 4 <= PI <= 7 and above A-line
                if 4.0 <= pi <= 7.0 and a_line is not None and pi >= a_line:
                    return USCSResult("CL-ML", "Silty clay", "Fine-grained", "Inorganic clay-silt transition")
                if a_line is not None and pi >= a_line and pi > 7.0:
                    return USCSResult("CL", "Lean clay", "Fine-grained", "Inorganic clay of low-to-medium plasticity")
                return USCSResult("ML", "Silt", "Fine-grained", "Inorganic silt of low plasticity")
        return USCSResult("FINE", "Fine-grained soil (unspecified plasticity)", "Fine-grained", "Fines >= 50%")

    # 2. Coarse-grained soils: more than 50% retained on No. 200 sieve
    coarse = gravel_pct + sand_pct
    is_gravel = gravel_pct > sand_pct

    # Grading criteria
    well_graded = False
    if is_gravel:
        if cu is not None and cc is not None:
            well_graded = cu >= 4.0 and (1.0 <= cc <= 3.0)
    else:
        if cu is not None and cc is not None:
            well_graded = cu >= 6.0 and (1.0 <= cc <= 3.0)

    # Plasticity of fines
    fines_clay = False
    fines_dual = False
    if ll is not None and pi is not None and a_line is not None:
        if 4.0 <= pi <= 7.0 and pi >= a_line:
            fines_dual = True
        elif pi >= a_line and pi > 7.0:
            fines_clay = True

    if is_gravel:
        # GRAVELS
        if fines_pct < 5.0:
            return USCSResult("GW", "Well-graded gravel", "Coarse-grained", "Gravel with < 5% fines, Cu >= 4 and 1 <= Cc <= 3") if well_graded else \
                   USCSResult("GP", "Poorly-graded gravel", "Coarse-grained", "Gravel with < 5% fines")
        elif fines_pct > 12.0:
            if fines_dual:
                return USCSResult("GC-GM", "Silty, clayey gravel", "Coarse-grained", "Gravel with > 12% CL-ML fines")
            return USCSResult("GC", "Clayey gravel", "Coarse-grained", "Gravel with > 12% clayey fines") if fines_clay else \
                   USCSResult("GM", "Silty gravel", "Coarse-grained", "Gravel with > 12% silty fines")
        else:
            # 5% to 12% fines (dual symbol)
            prefix = "GW" if well_graded else "GP"
            suffix = "GC" if fines_clay else "GM"
            return USCSResult(f"{prefix}-{suffix}", f"Dual gravel ({prefix}-{suffix})", "Coarse-grained", f"Gravel with {fines_pct:.1f}% fines")
    else:
        # SANDS
        if fines_pct < 5.0:
            return USCSResult("SW", "Well-graded sand", "Coarse-grained", "Sand with < 5% fines, Cu >= 6 and 1 <= Cc <= 3") if well_graded else \
                   USCSResult("SP", "Poorly-graded sand", "Coarse-grained", "Sand with < 5% fines")
        elif fines_pct > 12.0:
            if fines_dual:
                return USCSResult("SC-SM", "Silty, clayey sand", "Coarse-grained", "Sand with > 12% CL-ML fines")
            return USCSResult("SC", "Clayey sand", "Coarse-grained", "Sand with > 12% clayey fines") if fines_clay else \
                   USCSResult("SM", "Silty sand", "Coarse-grained", "Sand with > 12% silty fines")
        else:
            # 5% to 12% fines (dual symbol)
            prefix = "SW" if well_graded else "SP"
            suffix = "SC" if fines_clay else "SM"
            return USCSResult(f"{prefix}-{suffix}", f"Dual sand ({prefix}-{suffix})", "Coarse-grained", f"Sand with {fines_pct:.1f}% fines")


class SPTResult(float):
    def __new__(cls, val, n_60, n1_60, sigma_v_kpa):
        obj = super().__new__(cls, val)
        obj.n_60 = n_60
        obj.n1_60 = n1_60
        obj.sigma_v_kpa = sigma_v_kpa
        return obj

    def __getitem__(self, item):
        if item in ("n_60", "n60"):
            return self.n_60
        if item in ("n1_60", "n160"):
            return self.n1_60
        if item == "sigma_v_kpa":
            return self.sigma_v_kpa
        raise KeyError(item)


def correct_spt_n(
    raw_n: float,
    energy_ratio: float = 60.0,
    rod_length_m: float = 10.0,
    borehole_dia_mm: float = 150.0,
    sampler: str = "standard",
    effective_overburden_kpa: Optional[float] = None,
) -> SPTResult:
    """Energy-corrected SPT blow count N60 and overburden-normalised (N1)60.

    N60 = N * (ER / 60) * C_B * C_S * C_R          (Skempton 1986; Youd et al. 2001)
    (N1)60 = C_N * N60,  C_N = sqrt(Pa / sigma'v), capped at 2   (Liao and Whitman 1986)

    Parameters
    ----------
    energy_ratio : hammer energy ratio ER in percent (60 = the N60 reference).
    rod_length_m : length of the rods below the hammer (m); also the depth used for
        sigma'v when ``effective_overburden_kpa`` is not given.
    borehole_dia_mm : C_B = 1.00 up to 115 mm, 1.05 up to 150 mm, 1.15 above.
    sampler : "standard" (with liner, C_S = 1.0) or "no_liner" (C_S = 1.2).
    effective_overburden_kpa : sigma'v in kPa. If omitted, 18 kN/m3 x depth is used
        (dry soil, no water table).

    The result is a float equal to N60 that also exposes ``n_60``, ``n1_60`` and
    ``sigma_v_kpa`` (and the same keys by item access).
    """
    # C_B: borehole diameter
    if borehole_dia_mm <= 115:
        cb = 1.00
    elif borehole_dia_mm <= 150:
        cb = 1.05
    else:
        cb = 1.15

    # C_S: sampler without a liner reads low-density, so its blow count is increased
    kind = sampler.lower().replace("-", "_").replace(" ", "_")
    cs = 1.20 if ("no_liner" in kind or "without" in kind) else 1.00

    # C_R: short rods return energy early and give lower blow counts
    if rod_length_m >= 10.0:
        cr = 1.00
    elif rod_length_m >= 6.0:
        cr = 0.95
    elif rod_length_m >= 4.0:
        cr = 0.85
    else:
        cr = 0.75

    n60 = raw_n * (energy_ratio / 60.0) * cb * cs * cr

    sigma_v = effective_overburden_kpa if effective_overburden_kpa else rod_length_m * 18.0
    pa = 100.0
    cn = min(2.0, math.sqrt(pa / max(10.0, sigma_v)))
    n1_60 = n60 * cn

    return SPTResult(round(n60, 1), round(n60, 1), round(n1_60, 1), round(sigma_v, 1))


def rqd_quality(rqd_pct: float) -> tuple[str, str]:
    """Return Deere (1968) rock mass quality description and color for an RQD value."""
    if rqd_pct < 25:
        return "Very Poor", "#D9534F"
    elif rqd_pct < 50:
        return "Poor", "#F0AD4E"
    elif rqd_pct < 75:
        return "Fair", "#FFEEAA"
    elif rqd_pct < 90:
        return "Good", "#5CB85C"
    else:
        return "Excellent", "#449D44"
