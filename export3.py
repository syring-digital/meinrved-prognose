"""Daten für die Konzeptseite (Stufe 1–4) -> seite/data3.json.
Liest ausgabe/prognose3.json, bewertung.json, bewertung3.json, hindcast3.json und die Messreihen."""
import os, sys, json, csv, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, PAGE, DATA, CURVE, pct, last_season
import sim
import stage3 as s3
from stage3 import D

J = lambda f: json.load(open(os.path.join(OUT, f)))
P3 = J('prognose3.json'); B2 = J('bewertung.json'); B3 = J('bewertung3.json'); HC = J('hindcast3.json')
start = dt.date.fromisoformat(P3['start'])
out = dict(start=P3['start'], V0=P3['V0'], level0=P3['level0'], rest_now=P3['rest_now'], plan=P3['plan'], eps=P3['eps'], live=P3['live'],
           target=P3['target'], base3=P3['base3'], up=[[m, dd, v] for (m, dd), v in sim.UP], curve=CURVE, cap=sim.CAP,
           runs=[dict(j=r['jahr'], q=r['qin'], r=r['rest']) for r in P3['runs']])
out['recent'] = [[x.isoformat(), round(D[x]['V'], 2)] for x in sorted(D) if start - dt.timedelta(366) < x <= start and D[x]['V'] is not None]

# Was-wäre-wenn: echte Jahre Mai–Oktober (Zufluss, echte Abgabe, Inhalt)
wi = {}
for y in range(2003, start.year + 1):
    d = dt.date(y, 5, 1); q = o = None; rows = []
    while d <= min(dt.date(y, 10, 31), start - dt.timedelta(1)):
        q = sim.inflow(d) if sim.inflow(d) is not None else q
        o = D[d]['O'] if D[d]['O'] is not None else o
        rows.append([round(q, 2), o, round(D[d]['V'], 1)]); d += dt.timedelta(1)
    wi[y] = rows
out['whatif'] = wi

# Beleg Weser-Stützung: BfG-Tageswerte Hann. Münden 2015 und Edersee-Abgabe
bfg = {r['date']: float(r['Q']) for r in csv.DictReader(open(os.path.join(DATA, 'bfg', 'hmue_q_2013_2015.csv')))}
out['bfg2015'] = [[k, bfg[k], D[dt.date.fromisoformat(k)]['O']] for k in sorted(bfg) if '2015-05-01' <= k <= '2015-10-31']

# Bewertung
calib = lambda rows: {k: [round(st.mean(r['p'] for r in rows if r['ev'] == k), 2), round(st.mean(r['ist'] for r in rows if r['ev'] == k), 2)] for k in ('voll', 'regatta', 'unter125')}
out['skill2'] = B2['skill']; out['skill3'] = B3['skill']; out['calib2'] = calib(B2['rows']); out['calib3'] = calib(B3['rows'])
out['hindcast'] = HC
out['drawdown'] = [[y, round(D[dt.date(y, 6, 1)]['V'] - D[dt.date(y, 8, 1)]['V'], 1)] for y in range(1980, last_season(D) + 1)]
out['inflow_decade'] = [[dec, round(st.mean(sim.QIN[x] for x in sim.QIN if dec <= x.year < dec + 10), 1)] for dec in range(1960, start.year + 1, 10)]
out['rr'] = {a: {k: v for k, v in s3.PARS[a].items() if k != 'monat'} for a in ('eder', 'weser')}

# Fallbeispiel 2026 mit Stufe 2 und Stufe 3
case = []
for s in (dt.date(2026, 3, 1), dt.date(2026, 5, 1), dt.date(2026, 6, 1)):
    H = (dt.date(2026, 7, 19) - s).days; k = (dt.date(2026, 7, 18) - s).days
    r2 = [r for r in (sim.simulate(D[s]['V'], s, dt.date(t, s.month, s.day), H, adapt=20) for t in range(2000, 2026)) if r]
    r3 = [r for _, r in s3.ensemble3(D[s]['V'], s, H, list(range(2000, 2026)))]
    x2 = [r[k][1] for r in r2]; x3 = [r[k][1] for r in r3]
    case.append(dict(start=s.isoformat(), V0=round(D[s]['V'], 1), ist=round(D[dt.date(2026, 7, 18)]['V'], 1),
                     s2=[round(pct(x2, .5), 1), round(pct(x2, .1), 1), round(sum(x >= 63 for x in x2) / len(x2), 2)],
                     s3=[round(pct(x3, .5), 1), round(pct(x3, .1), 1), round(sum(x >= 63 for x in x3) / len(x3), 2)]))
    print('Fall 2026', case[-1])
out['case2026'] = case

os.makedirs(PAGE, exist_ok=True)
json.dump(out, open(os.path.join(PAGE, 'data3.json'), 'w'), separators=(',', ':'))
print('->', os.path.join(PAGE, 'data3.json'), os.path.getsize(os.path.join(PAGE, 'data3.json')) // 1024, 'KB')
