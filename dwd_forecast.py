"""DWD-Wetterprognose ICON-EPS (40 Ensemble-Läufe, ICON-D2/EU/global nahtlos, bis ~7 Tage) für beide Gebiete.
Abruf über die JSON-Schnittstelle von Open-Meteo (liefert die DWD-Modelldaten ohne GRIB-Dateien).
Ergebnis: ausgabe/dwd_eps.json mit Tagessummen Niederschlag und Tagesmitteln Temperatur je Lauf als Gebietsmittel.
Die letzten 3 Tage („past_days“) füllen die Lücke bis zum ersten DWD-Stationswert (CDC „akt“ hängt 1–2 Tage nach)."""
import os, sys, json, urllib.request, collections, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, fetch_url

POINTS = {
    'eder': [(51.03, 8.40), (51.05, 8.65), (51.12, 8.85), (51.17, 8.55), (51.20, 8.95)],
    'weser': [(50.57, 9.68), (50.87, 9.70), (51.00, 9.73), (50.92, 9.20), (51.13, 9.55),
              (50.57, 10.42), (50.98, 10.32), (51.19, 10.05), (50.50, 9.95), (50.75, 10.60)],
}
URL = 'https://ensemble-api.open-meteo.com/v1/ensemble?latitude={la}&longitude={lo}&hourly=precipitation,temperature_2m&models=icon_seamless&forecast_days=8&past_days=3&timezone=Europe%2FBerlin'


def fetch(area):
    pts = POINTS[area]
    url = URL.format(la=','.join(str(p[0]) for p in pts), lo=','.join(str(p[1]) for p in pts))
    js = json.loads(fetch_url(url))
    js = js if isinstance(js, list) else [js]
    members = ['precipitation'] + [f'precipitation_member{i:02d}' for i in range(1, 40)]
    tmembers = ['temperature_2m'] + [f'temperature_2m_member{i:02d}' for i in range(1, 40)]
    days = sorted({t[:10] for t in js[0]['hourly']['time']})
    P = [[0.0] * len(days) for _ in members]; T = [[0.0] * len(days) for _ in members]
    complete = [True] * len(days)
    for j in js:
        h = j['hourly']; di = [days.index(t[:10]) for t in h['time']]
        for m, (pk, tk) in enumerate(zip(members, tmembers)):
            ps = collections.defaultdict(float); ts = collections.defaultdict(list)
            for k, d in enumerate(di):
                p = h[pk][k] if h.get(pk) and h[pk][k] is not None else h['precipitation'][k]
                t = h[tk][k] if h.get(tk) and h[tk][k] is not None else h['temperature_2m'][k]
                if p is None or t is None: complete[d] = False; continue
                ps[d] += p; ts[d].append(t)
            for d in range(len(days)):
                P[m][d] += ps[d] / len(js)
                T[m][d] += (st.mean(ts[d]) if ts[d] else 0) / len(js)
    keep = [i for i, c in enumerate(complete) if c]
    return dict(days=[days[i] for i in keep], P=[[round(r[i], 2) for i in keep] for r in P], T=[[round(r[i], 2) for i in keep] for r in T])


if __name__ == '__main__':
    out = dict(abgerufen=dt.datetime.now().isoformat(timespec='minutes'), modell='DWD ICON-EPS (icon_seamless, 40 Läufe)')
    for a in POINTS: out[a] = fetch(a)
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, 'dwd_eps.json'), 'w'))
    for a in POINTS:
        e = out[a]; today = dt.date.today().isoformat()
        fut = [i for i, d in enumerate(e['days']) if d >= today]
        sums = sorted(sum(r[i] for i in fut) for r in e['P'])
        print(f"{a}: {e['days'][0]} bis {e['days'][-1]}, Summe ab heute: min {sums[0]:.0f}, Median {sums[len(sums) // 2]:.0f}, max {sums[-1]:.0f} mm")
