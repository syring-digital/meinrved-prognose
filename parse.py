"""Monats-HTML aus daten/roh in eine Tabelle daten/hist.csv umwandeln (date, level, volume, inflow, outflow)."""
import os, re, sys, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, HIST


def num(s):
    s = re.sub(r'<[^>]*>|&nbsp;', '', s).strip()
    if ',' in s: s = s.replace('.', '').replace(',', '.')
    try: return float(s)
    except ValueError: return None  # z. B. „k.A.“


rows = {}
for f in sorted(os.listdir(RAW)):
    h = open(os.path.join(RAW, f), 'rb').read().decode('utf-8', 'replace')
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S):
        c = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        if len(c) < 5: continue
        m = re.match(r'(\d\d)\.(\d\d)\.(\d{4})', re.sub(r'<[^>]*>', '', c[0]).strip())
        if m: rows[f'{m[3]}-{m[2]}-{m[1]}'] = [num(x) for x in c[1:5]]

with open(HIST, 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['date', 'level', 'volume', 'inflow', 'outflow'])
    for k in sorted(rows): w.writerow([k] + ['' if v is None else v for v in rows[k]])
print(len(rows), 'Tage von', min(rows), 'bis', max(rows), '->', HIST)
