"""Kalibrierung der Niederschlag-Abfluss-Modelle -> modell/rr_parameter.json
  Eder:   Seezufluss (Bilanzzufluss, 3-Tage-Mittel), kalibriert 1991–2010, geprüft 2011–2026.
  Weser:  Restabfluss Hann. Münden ohne Edersee-Abgabe. Kalibriert an
          (a) BfG-Tageswerten Hann. Münden Nov. 2013–Dez. 2015 minus Edersee-Abgabe des Vortags,
          (b) Stütztagen 2003–2026: Restabfluss ≈ 55 m³/s − Abgabe des Vortags,
          (c) Tagen ohne Stützbedarf im Sommer: Restabfluss mindestens 55 − Abgabe (Ungleichung),
          (d) Monatsmitteln 1941–2015 (BfG) minus mittlerer Edersee-Abgabe.
  python3 calib_rr.py [eder|weser]"""
import os, sys, json, csv, math, time, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, DATA, MODEL, load
from climate import load_climate
import rr

A_EDER, A_REST = 1443.0, 12444.0 - 1443.0   # km²
F_EDER, F_REST = A_EDER / 86.4, A_REST / 86.4  # mm/Tag -> m³/s
TARGET = 55.0                                  # Stützungsziel Hann. Münden (m³/s), WSA-PDF: 55,1
D = load(); C = load_climate()
PAR_FILE = os.path.join(MODEL, 'rr_parameter.json')


def series(a, b, key):
    days = [a + dt.timedelta(k) for k in range((b - a).days + 1)]
    return days, [C.get(d, {}).get('P_' + key) for d in days], [C.get(d, {}).get('T_' + key) for d in days]


def smooth(xs, w=1):
    return [st.mean(v for v in xs[max(0, i - w):i + w + 1] if v is not None) if xs[i] is not None else None for i in range(len(xs))]


def calib_eder():
    a, b = dt.date(1985, 1, 1), dt.date(2026, 10, 17)
    days, P, T = series(a, b, 'eder')
    obs = smooth([D[d]['Ib'] if D.get(d) else None for d in days])
    cal = [i for i, d in enumerate(days) if dt.date(1991, 1, 1) <= d <= dt.date(2010, 12, 31) and obs[i] is not None]
    val = [i for i, d in enumerate(days) if d >= dt.date(2011, 1, 1) and obs[i] is not None]

    def score(idx, q):
        s = [q[i] * F_EDER for i in idx]; o = [obs[i] for i in idx]
        return 0.5 * rr.kge(s, o) + 0.5 * rr.nse([math.sqrt(max(x, 0)) for x in s], [math.sqrt(max(x, 0)) for x in o])

    def f(z):
        q, _ = rr.run(rr.to_par(z), P, T, days)
        return -score(cal, q)
    z0 = rr.from_par([350, 0.0, 90, 2.0, 1.0, 3.0, 0.5])
    t0 = time.time(); best, fv = rr.nelder_mead(f, z0, [0.5, 1.0, 0.5, 0.5, 0.1, 0.4, 1.0], iters=500)
    best, fv = rr.nelder_mead(f, best, [0.2, 0.4, 0.2, 0.2, 0.05, 0.2, 0.5], iters=300)
    par = rr.to_par(best); q, _ = rr.run(par, P, T, days)
    res = dict(par=[round(x, 4) for x in par], area=A_EDER, score_cal=round(score(cal, q), 3), score_val=round(score(val, q), 3),
               nse_cal=round(rr.nse([q[i] * F_EDER for i in cal], [obs[i] for i in cal]), 3), nse_val=round(rr.nse([q[i] * F_EDER for i in val], [obs[i] for i in val]), 3),
               mean_sim_val=round(st.mean(q[i] * F_EDER for i in val), 2), mean_obs_val=round(st.mean(obs[i] for i in val), 2))
    # Monatsvolumen (realistischere Güte für die Seebilanz)
    mon = {}
    for i in val:
        k = days[i].strftime('%Y-%m'); s, o = mon.get(k, (0, 0)); mon[k] = (s + q[i] * F_EDER, o + obs[i])
    res['nse_month_val'] = round(rr.nse([v[0] for v in mon.values()], [v[1] for v in mon.values()]), 3)
    print('Eder', res, f'{time.time() - t0:.0f} s')
    return res


def weser_targets():
    """Beobachtungen für den Restabfluss (m³/s) samt Gewicht und Art (gleich/mindestens)."""
    obs = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'bfg', 'hmue_q_2013_2015.csv'))):
        d = dt.date.fromisoformat(r['date']); o = D.get(d - dt.timedelta(1), {}).get('O')
        if o is not None: obs[d] = ('eq', float(r['Q']) - o, 3.0)
    # Pegelonline: Bonaforth (Fulda) + Letzter Heller (Werra) der letzten Wochen
    po = os.path.join(DATA, 'bfg', 'pegelonline_rest.csv')
    if os.path.exists(po):
        for r in csv.DictReader(open(po)):
            d = dt.date.fromisoformat(r['date']); o = D.get(d - dt.timedelta(1), {}).get('O')
            if o is not None: obs[d] = ('eq', float(r['Q_hmue']) - o, 3.0)
    for d, v in D.items():
        if d.year < 2003 or d in obs or not (6 <= d.month <= 9): continue
        prev = D.get(d - dt.timedelta(1))
        if not prev or prev['O'] is None or v['V'] is None or v['V'] < 45 or v['V'] > 190: continue
        if prev['O'] >= 9: obs[d] = ('eq', TARGET - prev['O'], 1.0)       # gestützt
        elif prev['O'] <= 6.5: obs[d] = ('ge', TARGET - prev['O'], 1.0)   # keine Stützung nötig
    return obs


MQ_HMUE = {1: 166, 2: 173, 3: 173, 4: 144, 5: 96.1, 6: 86.1, 7: 77.4, 8: 68.5, 9: 65.4, 10: 72.9, 11: 96.5, 12: 141}  # BfG 1941/2015


def calib_weser():
    a, b = dt.date(1985, 1, 1), dt.date(2026, 10, 17)
    days, P, T = series(a, b, 'weser')
    obs = weser_targets()
    idx = [(i, obs[d]) for i, d in enumerate(days) if d in obs]
    # mittlere Edersee-Abgabe je Monat 1951–2015 -> Monatsmittel des Restgebiets
    mo = {m: st.mean(D[d]['O'] for d in D if 1951 <= d.year <= 2015 and d.month == m and D[d]['O'] is not None) for m in range(1, 13)}
    rest_mq = {m: MQ_HMUE[m] - mo[m] for m in mo}
    mi = {m: [i for i, d in enumerate(days) if d.month == m and d.year <= 2015] for m in range(1, 13)}

    def f(z):
        q, _ = rr.run(rr.to_par(z), P, T, days)
        e = 0.0; n = 0
        for i, (kind, val, w) in idx:
            s = math.sqrt(max(q[i] * F_REST, 0)); o = math.sqrt(max(val, 0.1))
            if kind == 'eq' or s < o: e += w * (s - o) ** 2; n += w
        e /= n
        tsn = rr.to_par(z)[6]
        return e + (0 if -2 <= tsn <= 3 else (abs(tsn) - 2.5) ** 2)  # Schneegrenze physikalisch begrenzen
    z0 = rr.from_par([400, 0.0, 120, 3.0, 1.0, 3.0, 0.5])
    # Monatsmittel 1941–2015 nur noch zur Kontrolle (nasser als die Jahre ab 1985, daher nicht in der Zielfunktion)
    t0 = time.time(); best, fv = rr.nelder_mead(f, z0, [0.5, 1.0, 0.5, 0.5, 0.1, 0.4, 1.0], iters=500)
    best, fv = rr.nelder_mead(f, best, [0.2, 0.4, 0.2, 0.2, 0.05, 0.2, 0.5], iters=300)
    par = rr.to_par(best); q, _ = rr.run(par, P, T, days)
    bfg = [(q[i] * F_REST, v[1]) for i, v in idx if v[2] == 3.0]
    sup = [(q[i] * F_REST, v[1]) for i, v in idx if v[2] == 1.0 and v[0] == 'eq']
    ge = [(q[i] * F_REST, v[1]) for i, v in idx if v[0] == 'ge']
    res = dict(par=[round(x, 4) for x in par], area=A_REST, target=TARGET,
               nse_bfg=round(rr.nse([s for s, o in bfg], [o for s, o in bfg]), 3),
               nse_log_bfg=round(rr.nse([math.log(s) for s, o in bfg], [math.log(o) for s, o in bfg]), 3),
               mae_stuetztage=round(st.mean(abs(s - o) for s, o in sup), 2), n_stuetztage=len(sup),
               ungleichung_erfuellt=round(sum(s >= o - 3 for s, o in ge) / len(ge), 3), n_ungleichung=len(ge),
               monat=[[m, round(st.mean(q[i] * F_REST for i in mi[m]), 1), round(rest_mq[m], 1)] for m in mi])
    print('Weser', res, f'{time.time() - t0:.0f} s')
    return res


if __name__ == '__main__':
    os.makedirs(MODEL, exist_ok=True)
    out = json.load(open(PAR_FILE)) if os.path.exists(PAR_FILE) else {}
    which = sys.argv[1:] or ['eder', 'weser']
    if 'eder' in which: out['eder'] = calib_eder()
    if 'weser' in which: out['weser'] = calib_weser()
    json.dump(out, open(PAR_FILE, 'w'), indent=1)
