"""Prognose Stufe 3 ab dem letzten Tag mit Seeinhalt: Modellzustand aus den DWD-Messungen, erste Woche DWD ICON-EPS,
danach die Wetterjahre 2000–2025 (jedes Jahr zweimal mit verschiedenen EPS-Läufen = 52 Läufe), WSA-Abgabeplan für die
ersten Tage, Restabfluss Hann. Münden am Start an Pegelonline angeglichen.
Vorher: climate.py, dwd_forecast.py, live.py. Ergebnis: ausgabe/prognose3.json (Eingangsreihen je Lauf für die Seite)."""
import os, sys, json, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, pct
import stage3 as s3
from stage3 import D

H = 365
start = max(d for d in D if D[d]['V'] is not None)
V0 = D[start]['V']
eps = json.load(open(os.path.join(OUT, 'dwd_eps.json')))
live = json.load(open(os.path.join(OUT, 'live.json')))

# Wetter vom Starttag an: Lücke zwischen letztem DWD-Messtag und Start aus dem EPS-Kontrolllauf, dann EPS
assert s3.LAST_CLIM + dt.timedelta(1) >= start - dt.timedelta(0), 'Messdaten reichen nicht bis zum Start'
state_day = min(start, s3.LAST_CLIM + dt.timedelta(1))
members = []
for m in range(40):
    fw = {}
    for a in ('eder', 'weser'):
        e = eps[a]; idx = [i for i, d in enumerate(e['days']) if d >= state_day.isoformat()]
        fw[a] = ([e['P'][m][i] for i in idx], [e['T'][m][i] for i in idx])
    members.append(fw)
if start > state_day:
    # DWD-Stationsdaten hängen 1–2 Tage nach: Prognose am letzten Tag starten, für den Seeinhalt und Gebietszustand vorliegen
    print(f'Hinweis: DWD-Messdaten bis {s3.LAST_CLIM}, Start daher {state_day} statt {start}')
    start = state_day; V0 = D[start]['V']

# Restabfluss heute: Hann. Münden (Pegelonline) − Edersee-Abgabe des Vortags
hm = live['hmue_tage']; last = max(hm)
o_prev = D.get(dt.date.fromisoformat(last) - dt.timedelta(1), {}).get('O') or 3.0
rest_now = hm[last] - o_prev
plan = {(dt.date.fromisoformat(d) - start).days: v for d, v in live.get('wsa', {}).get('plan', []) if dt.date.fromisoformat(d) >= start}

pool = [t for t in range(2000, start.year + 1) if dt.date(t, start.month, start.day) + dt.timedelta(H - 1) <= s3.LAST_CLIM]
runs = []
for rep in range(2):
    for i, ty in enumerate(pool):
        m = (i + rep * len(pool)) % 40
        mi = s3.member_inputs(start, ty, H, members[m], rest_now)
        if mi is None: continue
        qin, rest = mi
        cin = s3.inflow_correction(start)
        qin = s3.blend(qin, cin, 15)
        runs.append(dict(jahr=ty, eps=m, qin=[round(x, 2) for x in qin], rest=[round(x, 1) for x in rest]))
sims = [s3.simulate3(V0, start, r['qin'], r['rest'], plan=plan) for r in runs]
fan = [[round(pct([s[k][1] for s in sims], p), 2) for p in (.1, .25, .5, .75, .9)] for k in range(H)]
print(f'Start {start}, Inhalt {V0:.2f}, {len(runs)} Läufe ({len(pool)} Wetterjahre × 2), Rest heute {rest_now:.1f} m³/s, Plan {plan}, Zuflusskorrektur {s3.inflow_correction(start):.2f}')
for k in (7, 14, 28, 60, 120, 196, 269, 317):
    if k < H: print(f'  +{k:3} Tage {start + dt.timedelta(k)}: {fan[k]}')
q7 = sorted(sum(s[k][2] for k in range(7)) / 7 for s in sims)
print('Zufluss Woche 1 (m³/s): 10 %', round(pct(q7, .1), 2), 'Median', round(pct(q7, .5), 2), '90 %', round(pct(q7, .9), 2))
wende = sorted(next((k for k in range(H - 7) if sum(s[j][2] - s[j][3] for j in range(k, k + 7)) > 0), H) for s in sims)
print('Wendepunkt (7-Tage-Bilanz positiv) Median Tag', pct(wende, .5), 'Anteil in 14 Tagen', sum(w <= 14 for w in wende) / len(wende))
eps_days = [d for d in eps['eder']['days'] if d >= start.isoformat()]
rain = {a: [[round(pct([eps[a]['P'][m][eps[a]['days'].index(d)] for m in range(40)], p), 1) for p in (.1, .5, .9)] for d in eps_days] for a in ('eder', 'weser')}
json.dump(dict(start=start.isoformat(), V0=round(V0, 2), level0=D[start]['L'], rest_now=round(rest_now, 1), plan=live.get('wsa', {}),
               eps=dict(abgerufen=eps['abgerufen'], days=eps_days, rain=rain), runs=runs, fan=fan,
               live=dict(see=live['see']['letzter'], schmitt=live['schmittlotheim']['letzter'], schmitt_alter=live['schmittlotheim']['alter_stunden'],
                         hmue=[last, hm[last]]),
               rest_bias=s3.REST_BIAS, target=s3.TARGET, base3=s3.BASE3),
          open(os.path.join(OUT, 'prognose3.json'), 'w'))
print('->', os.path.join(OUT, 'prognose3.json'))
