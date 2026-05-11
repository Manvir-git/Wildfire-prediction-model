"""
Canadian Forest Fire Weather Index (FWI) System Calculator
Based on: Van Wagner, C.E. (1987). Development and Structure of the Canadian
Forest Fire Weather Index System. Can. For. Serv. Tech. Rep. 35, Ottawa.

Inputs per day: temperature (°C), relative humidity (%), wind (km/h), rain (mm)
Previous-day moisture codes as state (use defaults for startup).
"""

import math

# ── Startup defaults (spring, low danger) ───────────────────────────────────
DEFAULT_FFMC = 85.0
DEFAULT_DMC  = 6.0
DEFAULT_DC   = 15.0


def _safe_log(x):
    return math.log(max(x, 1e-10))


def calc_ffmc(temp, rh, wind, rain, ffmc_prev=DEFAULT_FFMC):
    """Fine Fuel Moisture Code. Returns new FFMC."""
    mo = 147.2 * (101.0 - ffmc_prev) / (59.5 + ffmc_prev)

    # Rain effect on fine fuel moisture
    if rain > 0.5:
        rf = rain - 0.5
        if mo <= 150.0:
            mr = mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf))
        else:
            mr = mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf)) \
                 + 0.0015 * (mo - 150.0) ** 2 * math.sqrt(rf)
        mo = min(mr, 250.0)

    # Equilibrium moisture content (drying / wetting)
    ed = 0.942 * rh ** 0.679 + 11.0 * math.exp((rh - 100.0) / 10.0) + \
         0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))
    ew = 0.618 * rh ** 0.753 + 10.0 * math.exp((rh - 100.0) / 10.0) + \
         0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))

    if mo > ed:
        kd = 0.424 * (1.0 - (rh / 100.0) ** 1.7) + 0.0694 * math.sqrt(wind) * (1.0 - (rh / 100.0) ** 8)
        kdo = kd * 0.581 * math.exp(0.0365 * temp)
        m = ed + (mo - ed) * 10.0 ** (-kdo)
    elif mo < ew:
        kw = 0.424 * (1.0 - ((100.0 - rh) / 100.0) ** 1.7) + \
             0.0694 * math.sqrt(wind) * (1.0 - ((100.0 - rh) / 100.0) ** 8)
        kwo = kw * 0.581 * math.exp(0.0365 * temp)
        m = ew - (ew - mo) * 10.0 ** (-kwo)
    else:
        m = mo

    ffmc = 59.5 * (250.0 - m) / (147.2 + m)
    return max(0.0, min(ffmc, 101.0))


def calc_dmc(temp, rh, rain, month, dmc_prev=DEFAULT_DMC):
    """Duff Moisture Code. month: 1-12. Returns new DMC."""
    # Day-length adjustment factor Le by month
    le_table = [6.5, 7.5, 9.0, 12.8, 13.9, 13.9, 12.4, 10.9, 9.4, 8.0, 7.0, 6.0]
    le = le_table[month - 1]

    # Rain effect on DMC
    if rain > 1.5:
        re = 0.92 * rain - 1.27
        mo = 20.0 + math.exp(5.6348 - dmc_prev / 43.43)
        if dmc_prev <= 33.0:
            b = 100.0 / (0.5 + 0.3 * dmc_prev)
        elif dmc_prev <= 65.0:
            b = 14.0 - 1.3 * _safe_log(dmc_prev)
        else:
            b = 6.2 * _safe_log(dmc_prev) - 17.2
        mr = mo + 1000.0 * re / (48.77 + b * re)
        pr = 244.72 - 43.43 * _safe_log(mr - 20.0)
        dmc_prev = max(pr, 0.0)

    # Drying phase
    if temp > -1.1:
        k = 1.894 * (temp + 1.1) * (100.0 - rh) * le * 1e-6
    else:
        k = 0.0
    dmc = dmc_prev + 100.0 * k
    return max(0.0, dmc)


def calc_dc(temp, rain, month, dc_prev=DEFAULT_DC):
    """Drought Code. month: 1-12. Returns new DC."""
    # Daylength factor Lf by month (Southern Asia adjustment: positive all year)
    lf_table = [-1.6, -1.6, -1.6, 0.9, 3.8, 5.8, 6.4, 5.0, 2.4, 0.4, -1.6, -1.6]
    lf = lf_table[month - 1]

    # Rain effect
    if rain > 2.8:
        rw = 0.83 * rain - 1.27
        smi = 800.0 * math.exp(-dc_prev / 400.0)
        dr = dc_prev - 400.0 * _safe_log(1.0 + 3.937 * rw / smi)
        dc_prev = max(dr, 0.0)

    # Drying phase
    if temp > -2.8:
        v = 0.36 * (temp + 2.8) + lf
    else:
        v = lf
    v = max(v, 0.0)
    dc = dc_prev + 0.5 * v
    return max(0.0, dc)


def calc_isi(wind, ffmc):
    """Initial Spread Index."""
    fm = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
    sf = 19.115 * math.exp(-0.1386 * fm) * (1.0 + fm ** 5.31 / 4.93e7)
    isi = sf * math.exp(0.05039 * wind)
    return max(0.0, isi)


def calc_bui(dmc, dc):
    """Build-Up Index."""
    if dmc <= 0.4 * dc:
        bui = 0.8 * dmc * dc / (dmc + 0.4 * dc)
    else:
        bui = dmc - (1.0 - 0.8 * dc / (dmc + 0.4 * dc)) * (0.92 + (0.0114 * dmc) ** 1.7)
    return max(0.0, bui)


def calc_fwi(isi, bui):
    """Fire Weather Index."""
    if bui <= 80.0:
        bb = 0.1 * isi * (0.626 * bui ** 0.809 + 2.0)
    else:
        bb = 0.1 * isi * (1000.0 / (25.0 + 108.64 * math.exp(-0.023 * bui)))
    fwi = math.exp(2.72 * (0.434 * _safe_log(bb)) ** 0.647) if bb > 1.0 else bb
    return max(0.0, fwi)


def compute_fwi_components(temp, rh, wind, rain, month,
                            ffmc_prev=DEFAULT_FFMC,
                            dmc_prev=DEFAULT_DMC,
                            dc_prev=DEFAULT_DC):
    """
    Compute all 6 FWI system components for one day.

    Args:
        temp   : Air temperature (°C), noon
        rh     : Relative humidity (%), noon
        wind   : Wind speed (km/h), noon
        rain   : 24-hour rainfall (mm), from previous noon
        month  : Calendar month (1-12)
        ffmc_prev, dmc_prev, dc_prev : Previous day codes (defaults = spring startup)

    Returns dict with keys: FFMC, DMC, DC, ISI, BUI, FWI
    """
    rh = max(0.0, min(rh, 100.0))
    wind = max(0.0, wind)
    rain = max(0.0, rain)
    temp = max(-40.0, temp)

    ffmc = calc_ffmc(temp, rh, wind, rain, ffmc_prev)
    dmc  = calc_dmc(temp, rh, rain, month, dmc_prev)
    dc   = calc_dc(temp, rain, month, dc_prev)
    isi  = calc_isi(wind, ffmc)
    bui  = calc_bui(dmc, dc)
    fwi  = calc_fwi(isi, bui)

    return {
        "FFMC": round(ffmc, 2),
        "DMC":  round(dmc, 2),
        "DC":   round(dc, 2),
        "ISI":  round(isi, 2),
        "BUI":  round(bui, 2),
        "FWI":  round(fwi, 2),
    }
