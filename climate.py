"""DWD-Tageswerte (Open Data, CDC) laden und zu Gebietsmitteln verrechnen -> daten/klima.csv.
Niederschlag aus dem Messnetz „more_precip“, Temperatur aus den Klimastationen „kl“.
Edergebiet oberhalb der Sperre (12 Niederschlags-, 3 Klimastationen) und Restgebiet bis Hann. Münden
(Fulda, Werra, Schwalm: 18 Niederschlags-, 4 Klimastationen). Historische Dateien werden nur einmal geladen,
die aktuellen („akt“, bis gestern) bei jedem Aufruf."""
import os, sys, io, re, csv, glob, time, zipfile, urllib.request, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, fetch_url

DWD = os.path.join(DATA, 'dwd')
CLIMA = os.path.join(DATA, 'klima.csv')
BASE = 'https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily'
EDER_RR = '01283 00389 00390 00310 00309 03215 02483 00817 01404 05240 02718 05297'.split()
WESER_RR = '01526 02171 04277 05912 05263 04589 03527 00091 05371 04978 03231 04469 01297 04763 02148 02618 05646 02544'.split()
EDER_KL = '02483 00390 00817'.split()
WESER_KL = '01526 02171 03231 01297'.split()


def download():
    os.makedirs(DWD, exist_ok=True)
    for kind, folder, ids in (('RR', 'more_precip', EDER_RR + WESER_RR), ('KL', 'kl', EDER_KL + WESER_KL)):
        for part in ('historical', 'recent'):
            listing = fetch_url(f'{BASE}/{folder}/{part}/').decode('latin-1')
            for sid in ids:
                pat = f'tageswerte_{kind}_{sid}_akt.zip' if part == 'recent' else f'tageswerte_{kind}_{sid}_[0-9_]*hist.zip'
                for f in sorted(set(re.findall(pat, listing))):
                    p = os.path.join(DWD, f)
                    if part == 'historical' and os.path.exists(p): continue
                    open(p, 'wb').write(fetch_url(f'{BASE}/{folder}/{part}/{f}', tries=6))
                    time.sleep(0.3)  # den DWD-Server nicht mit Anfragen überhäufen


def read(kind, sid, col):
    vals = {}
    for z in sorted(glob.glob(os.path.join(DWD, f'tageswerte_{kind}_{sid}_*.zip'))):  # „akt“ sortiert hinter „hist“ und überschreibt
        with zipfile.ZipFile(z) as zf:
            name = next(n for n in zf.namelist() if n.startswith('produkt'))
            r = csv.reader(io.TextIOWrapper(zf.open(name), encoding='latin-1'), delimiter=';')
            i = [h.strip() for h in next(r)].index(col)
            for row in r:
                v = float(row[i])
                if v > -900: vals[dt.datetime.strptime(row[1].strip(), '%Y%m%d').date()] = v
    return vals


def build():
    series = {'P_eder': [read('RR', s, 'RS') for s in EDER_RR], 'P_weser': [read('RR', s, 'RS') for s in WESER_RR],
              'T_eder': [read('KL', s, 'TMK') for s in EDER_KL], 'T_weser': [read('KL', s, 'TMK') for s in WESER_KL]}
    days = sorted(d for d in set().union(*[set(x) for l in series.values() for x in l]) if d >= dt.date(1950, 1, 1))
    # Gebietsmittel per Anomalie: jede Station relativ zu ihrem Mittel, damit Ausfälle keine Sprünge erzeugen
    means = {g: [st.mean(x.values()) for x in l] for g, l in series.items()}
    gm = {g: st.mean(means[g]) for g in series}
    with open(CLIMA, 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['date', 'P_eder', 'P_weser', 'T_eder', 'T_weser'])
        for day in days:
            row = [day.isoformat()]
            for g in ('P_eder', 'P_weser', 'T_eder', 'T_weser'):
                vs = [(x[day], means[g][i]) for i, x in enumerate(series[g]) if day in x]
                if not vs: row.append(''); continue
                row.append(round(st.mean(v / m for v, m in vs) * gm[g], 2) if g[0] == 'P' else round(st.mean(v - m for v, m in vs) + gm[g], 2))
            w.writerow(row)
    print(len(days), 'Tage', days[0], '-', days[-1], '->', CLIMA)


def load_climate():
    C = {}
    for r in csv.DictReader(open(CLIMA)):
        C[dt.date.fromisoformat(r['date'])] = {k: (float(v) if v != '' else None) for k, v in r.items() if k != 'date'}
    return C


if __name__ == '__main__':
    if '--ohne-download' not in sys.argv: download()
    build()
