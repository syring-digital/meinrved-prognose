"""Stufe 3: Seebilanz mit Niederschlag-Abfluss-Modellen.
  Zufluss     = GR4J Edergebiet (DWD-Gebietsniederschlag/-temperatur)
  Stützbedarf = 55 m³/s − Restabfluss Hann. Münden (GR4J Fulda/Werra), Mai–Oktober
  Abgabe      = Regeln aus sim.py (Mindestabgaben, Winter-Leitlinie, Hochwasser), Stützbedarf statt Spurjahr-Abgabe;
                für die ersten Tage optional der WSA-Abgabeplan.
Ensemble: Modellzustand aus den beobachteten DWD-Daten bis zum Start, danach Wetter aus ICON-EPS (Tage 1–7)
und den historischen Wetterjahren (ab Tag 8 bzw. ab Tag 1 ohne Prognose)."""
import os, sys, json, copy, math, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, MODEL, FULL, K, load
from climate import load_climate
import rr
import sim

PARS = json.load(open(os.path.join(MODEL, 'rr_parameter.json')))
F = {'eder': PARS['eder']['area'] / 86.4, 'weser': PARS['weser']['area'] / 86.4}
TARGET = PARS['weser'].get('target', 55.0)
D = sim.D
C = load_climate()
CLIM_START = dt.date(1985, 1, 1)
BASE3 = {1: 4, 2: 4, 3: 6, 4: 10, 5: 8, 6: 6, 7: 6, 8: 6, 9: 6, 10: 6, 11: 5, 12: 4}  # Grundabgabe ohne Stützbedarf
SUPPORT = range(5, 11)


def clim(d, key):
    c = C.get(d)
    return (c.get(key) if c else None)


def _full_pass():
    """Einmal durch die beobachteten Daten: Modellzustand zu Beginn jedes Tages und simulierter Abfluss (m³/s)."""
    state, sims = {}, {}
    last = max(d for d in C if C[d].get('P_eder') is not None and C[d].get('P_weser') is not None)
    for area in ('eder', 'weser'):
        par = PARS[area]['par']; s = rr.init_state(par); d = CLIM_START
        state[area], sims[area] = {}, {}
        while d <= last:
            state[area][d] = s
            q, s = rr.run(par, [clim(d, 'P_' + area)], [clim(d, 'T_' + area)], [d], s)
            sims[area][d] = q[0] * F[area]
            d += dt.timedelta(1)
        state[area][d] = s  # Zustand am Morgen nach dem letzten Messtag
    return state, sims, last


STATE, SIMS, LAST_CLIM = _full_pass()


def states_at(dates):
    return {d: {a: STATE[a][d] for a in STATE} for d in dates}, SIMS


def _rest_bias():
    """Monatsfaktor beobachtet/simuliert für den Weser-Restabfluss aus den Stütztagen (beobachtet = 55 − Abgabe Vortag)."""
    f = {}
    for m in range(5, 11):
        pairs = []
        for d, v in D.items():
            if d.year < 2003 or d.month != m or d not in SIMS['weser']: continue
            prev = D.get(d - dt.timedelta(1))
            if prev and prev['O'] is not None and v['V'] and 45 < v['V'] < 190 and prev['O'] >= 9:
                pairs.append((TARGET - prev['O'], SIMS['weser'][d]))
        f[m] = st.mean(o for o, _ in pairs) / st.mean(s for _, s in pairs) if len(pairs) > 30 else 1.0
    return f


REST_BIAS = _rest_bias()


def run_area(area, state, P, T, days):
    q, _ = rr.run(PARS[area]['par'], P, T, days, copy.deepcopy(state))
    return [x * F[area] for x in q]


def trace_weather(area, start, ty, H):
    """Wetter des Jahres ty, kalendertreu ab dem Starttag."""
    P, T = [], []
    for k in range(H):
        d = start + dt.timedelta(k)
        try: td = d.replace(year=ty + (d.year - start.year))
        except ValueError: td = (d - dt.timedelta(1)).replace(year=ty + (d.year - start.year))
        P.append(clim(td, 'P_' + area)); T.append(clim(td, 'T_' + area))
    return P, T


def release3(V, d, rest, reduced=True):
    if reduced and V < 29: return 3.0
    m = d.month
    if V < 40: return 4.0 if m in sim.WINTER_MIN else 6.0
    o = BASE3[m]
    if m in SUPPORT and rest is not None: o = max(o, min(TARGET - rest, 40.0))
    return o


def simulate3(V0, start, qin, rest, reduced=True, plan=None, rule125=False, cap_summer=None, target=None):
    """Seebilanz. qin, rest: Listen (m³/s). plan: {Tag-Index: Abgabe} (WSA-Abgabeplan).
    rule125: Haltelinie 125 (unter 125 Mio. von Mai bis August höchstens 6 m³/s).
    cap_summer: höchstens so viel Stützung (m³/s). target: anderes Stützungsziel in Hann. Münden."""
    V = V0; out = []
    tg = target or TARGET
    for k in range(len(qin)):
        d = start + dt.timedelta(k); q = qin[k]
        if plan and k in plan: o = plan[k]
        else:
            o = release3(V, d, None if rest is None else rest[k] + (TARGET - tg), reduced)
            if cap_summer is not None and d.month in SUPPORT and V >= 40: o = min(o, max(cap_summer, BASE3[d.month]))
            if rule125 and V < 125 and 5 <= d.month <= 8: o = min(o, 6.0)
        Vn = V + (q - o) * K
        lim = sim.upper(d + dt.timedelta(1))
        if Vn > FULL:
            o += (Vn - FULL) / K; Vn = FULL
        elif Vn > lim:
            target_v = max(lim, V - (V - lim) / 5.0) if V > lim else lim
            o = max(o, min(q + (V - target_v) / K, sim.CAP)); Vn = V + (q - o) * K
            if Vn > FULL: o += (Vn - FULL) / K; Vn = FULL
        Vn = max(Vn, 0.5)
        out.append((d, V, q, o)); V = Vn
    return out


def correction(obs, simv, start, days=14):
    """Verhältnis beobachtet/simuliert der letzten Tage (für den Übergang vom heutigen Niveau)."""
    a = [obs.get(start - dt.timedelta(k)) for k in range(1, days + 1)]
    b = [simv.get(start - dt.timedelta(k)) for k in range(1, days + 1)]
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs: return 1.0
    return min(max(max(st.mean(x for x, _ in pairs), 0.3) / max(st.mean(y for _, y in pairs), 0.3), 0.33), 3.0)


def blend(series, r, tau=15):
    return [x * (r + (1 - r) * (1 - math.exp(-k / tau))) for k, x in enumerate(series)]


def observed_rest(d):
    """Restabfluss aus einem Stütztag (55 − Abgabe des Vortags), sonst None."""
    prev = D.get(d - dt.timedelta(1)); v = D.get(d)
    if prev and v and prev['O'] is not None and v['V'] and 45 < v['V'] < 190 and prev['O'] >= 9 and d.month in SUPPORT:
        return TARGET - prev['O']
    return None


def member_inputs(start, ty, H, first_weather=None, rest_now=None):
    """Zufluss und Restabfluss (m³/s) für einen Ensemble-Lauf: Wetter des Jahres ty (die ersten Tage optional aus der
    DWD-Prognose first_weather = {area: (P, T)}), Modell ab dem heutigen Zustand.
    Zufluss: gemessener Zufluss im Spurjahr × Modell(heute)/Modell(damals), am Start an den gemessenen Zufluss angeglichen.
    Rest:    Modell(heute) × Monatsfaktor, am Start an den gemessenen Restabfluss angeglichen."""
    res = {}
    for area in ('eder', 'weser'):
        P, T = trace_weather(area, start, ty, H)
        if first_weather and area in first_weather:
            fp, ft = first_weather[area]
            n = min(len(fp), H); P[:n] = fp[:n]; T[:n] = ft[:n]
        days = [start + dt.timedelta(k) for k in range(H)]
        res[area] = run_area(area, STATE[area][start], P, T, days)
    qin = []
    for k in range(H):
        d = start + dt.timedelta(k)
        try: td = d.replace(year=ty + (d.year - start.year))
        except ValueError: td = (d - dt.timedelta(1)).replace(year=ty + (d.year - start.year))
        obs = sim.inflow(td); st_ = SIMS['eder'].get(td)
        if obs is None or st_ is None: return None
        # Verhältnis über 7 Tage geglättet, damit einzelne Spitzen nicht verzerren
        num = sum(res['eder'][max(0, k - 3):k + 4]); den = sum(SIMS['eder'].get(td + dt.timedelta(j), st_) for j in range(-min(k, 3), min(H - k, 4)))
        qin.append(max(obs, 0.0) * min(max(num / max(den, 0.1), 0.2), 5.0) if obs > 0 else res['eder'][k])
    rest = [res['weser'][k] * REST_BIAS.get((start + dt.timedelta(k)).month, 1.0) for k in range(H)]
    if rest_now is not None and rest:
        r = min(max(rest_now / max(rest[0], 1.0), 0.33), 3.0)
        rest = [x * (r + (1 - r) * (1 - math.exp(-k / 30))) for k, x in enumerate(rest)]
    return qin, rest


def inflow_correction(start):
    """Gemessener / simulierter Zufluss der letzten 14 Tage (Modellzustand gegen Messung)."""
    obs = {start - dt.timedelta(k): sim.inflow(start - dt.timedelta(k)) for k in range(1, 15)}
    return correction({d: v for d, v in obs.items() if v is not None}, SIMS['eder'], start)


def ensemble3(V0, start, H, pool, first_weather=None, rest_now=None, eps_members=None, inflow_fix=True, **simkw):
    """Ensemble aus den Wetterjahren in pool. eps_members: Liste von {area: (P, T)} (DWD-Läufe), zyklisch zugeordnet."""
    runs = []
    cin = inflow_correction(start) if inflow_fix else 1.0
    if rest_now is None:
        # im Rückblick: Restabfluss aus den Stütztagen der letzten Woche (live kommt er von Pegelonline)
        obs = [x for x in (observed_rest(start - dt.timedelta(k)) for k in range(0, 7)) if x is not None]
        if obs: rest_now = st.mean(obs)
    for i, ty in enumerate(pool):
        fw = eps_members[i % len(eps_members)] if eps_members else first_weather
        mi = member_inputs(start, ty, H, fw, rest_now)
        if mi is None: continue
        qin, rest = mi
        if cin != 1.0: qin = blend(qin, cin, 15)
        r = simulate3(V0, start, qin, rest, **simkw)
        runs.append((ty, r))
    return runs
