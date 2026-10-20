"""Aktuelle Messwerte für Stufe 1: Pegelonline (Edersee, Schmittlotheim, Bonaforth, Letzter Heller) und der
WSA-Abgabeplan aus dem PDF „Wasserstandsvorhersage Oberweser“ (Seite „Abgabenplanung Edertalsperre“).
Ergebnis: ausgabe/live.json; ergänzt daten/bfg/pegelonline_rest.csv (Restabfluss Hann. Münden = Bonaforth + Letzter Heller).
Das PDF wird mit pypdf gelesen (GitHub, Linux), sonst mit PDFKit (macOS, swift)."""
import os, sys, re, json, subprocess, tempfile, urllib.request, collections, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, DATA, HERE, fetch_url

PO = 'https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/{s}/{t}/measurements.json?start=P{d}D'
PDF = 'https://pss.wsv.de/wsahmue/VorhersageOberweser.pdf'


def series(station, ts='Q', days=10):
    js = json.loads(fetch_url(PO.format(s=urllib.request.quote(station), t=ts, d=days), timeout=30))
    return [(m['timestamp'], m['value']) for m in js]


def daily(sr, min_n=80):
    d = collections.defaultdict(list)
    for t, v in sr: d[t[:10]].append(v)
    return {k: st.mean(v) for k, v in d.items() if len(v) >= min_n}


def pdf_text(path):
    try:
        import pypdf
        return '\n'.join(p.extract_text(extraction_mode='layout') for p in pypdf.PdfReader(path).pages)
    except ImportError:
        return subprocess.run(['swift', os.path.join(HERE, 'pdftext.swift'), path], capture_output=True, text=True).stdout


def parse_wsa(txt):
    """Liest Stand, Abgabeplan der Edertalsperre, Statustext und langjähriges Mittel (PDFKit- und pypdf-Text)."""
    stand = re.search(r'Stand:\s*\w\w (\d\d\.\d\d\.\d{4} \d\d:\d\d)', txt)
    block = txt.split('Abgabenplanung Edertalsperre', 1)[-1].split('Abgabenplanung Diemeltalsperre', 1)[0]
    plan = [(dt.datetime.strptime(d, '%d.%m.%Y').date().isoformat(), float(v.replace(',', '.')))
            for d, v in re.findall(r'(\d\d\.\d\d\.\d{4}) \d\d:\d\d\s+([\d,]+) m³/s', block)]
    status = re.search(r'Abgabenplanung\s*\n(.*?)\n\s*Voraussichtliche Entwicklung der Wasserstände', txt, re.S)
    text = ' '.join(l.strip() for l in status.group(1).splitlines() if l.strip()) if status else None
    mittel = re.search(r'langjähriges Mittel aktuell:\s+([\d,]+)', txt)
    return dict(stand=stand.group(1) if stand else None, plan=plan, text=text,
                mittel=float(mittel.group(1).replace(',', '.')) if mittel else None)


def wsa_plan():
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, 'v.pdf')
        open(pdf, 'wb').write(fetch_url(PDF))
        return parse_wsa(pdf_text(pdf))


if __name__ == '__main__':
    out = dict(abgerufen=dt.datetime.now().isoformat(timespec='minutes'))
    see = series('EDERTALSPERRE', 'W', 8)
    out['see'] = dict(letzter=see[-1], um7=[(t, v) for t, v in see if t[11:16] == '07:00'])
    for st_, key in (('SCHMITTLOTHEIM', 'schmittlotheim'), ('BONAFORTH', 'bonaforth'), ('LETZTER HELLER', 'letzter_heller')):
        s = series(st_, 'Q', 31); out[key] = dict(letzter=s[-1], tage=daily(s))
        age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(s[-1][0])
        out[key]['alter_stunden'] = round(age.total_seconds() / 3600, 1)
    rest = {k: round(out['bonaforth']['tage'][k] + out['letzter_heller']['tage'][k], 2) for k in out['bonaforth']['tage'] if k in out['letzter_heller']['tage']}
    out['hmue_tage'] = rest
    po = os.path.join(DATA, 'bfg', 'pegelonline_rest.csv')
    os.makedirs(os.path.dirname(po), exist_ok=True)
    old = {}
    if os.path.exists(po):
        for line in open(po).read().splitlines()[1:]:
            k, v = line.split(','); old[k] = float(v)
    old.update(rest)
    with open(po, 'w') as fh:
        fh.write('date,Q_hmue\n'); [fh.write(f'{k},{old[k]}\n') for k in sorted(old)]
    try: out['wsa'] = wsa_plan()
    except Exception as e: out['wsa'] = dict(fehler=str(e))
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, 'live.json'), 'w'), indent=1)
    print('Edersee', out['see']['letzter'], '| Schmittlotheim', out['schmittlotheim']['letzter'], f"({out['schmittlotheim']['alter_stunden']} h alt)")
    print('Hann. Münden (Bonaforth + Letzter Heller), letzte Tage:', list(rest.items())[-3:])
    print('WSA:', out['wsa'])
