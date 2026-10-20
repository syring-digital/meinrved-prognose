"""Prüft, ob seite/model.js dieselben Ergebnisse liefert wie sim.py (Fächer am 1. Mai, 15. Juli, 1. Sept.).
Nutzt JavaScriptCore über osascript (macOS), kein Node nötig. Vorher export.py ausführen."""
import os, sys, json, subprocess, tempfile, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, PAGE

P = json.load(open(os.path.join(OUT, 'prognose.json')))
start = dt.date.fromisoformat(P['start']); sy = P['season']
dates = [dt.date(sy, 5, 1), dt.date(sy, 7, 15), dt.date(sy, 9, 1)]
js = 'var DATA = ' + open(os.path.join(PAGE, 'data.json')).read() + ';\n' + open(os.path.join(PAGE, 'model.js')).read() + f'''
Model.init(DATA);
var e = Model.ensemble(DATA.V0, '{P['start']}', 365, [2000, {start.year}], {{}});
var out = {json.dumps([(d - start).days for d in dates])}.map(function (k) {{
  var xs = e.runs.map(function (r) {{ return r.vol[k]; }});
  return [0.1, 0.25, 0.5, 0.75, 0.9].map(function (p) {{ return Model.pct(xs, p); }});
}});
JSON.stringify({{n: e.runs.length, fan: out}});
'''
with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f: f.write(js)
res = json.loads(subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True).stdout)
os.unlink(f.name)
worst = 0
for d, fj in zip(dates, res['fan']):
    fp = P['fan'][(d - start).days]
    diff = max(abs(a - b) for a, b in zip(fj, fp)); worst = max(worst, diff)
    print(d, 'JS', [round(x, 2) for x in fj], 'Python', fp, 'max. Abweichung', round(diff, 3))
print('Spuren JS', res['n'], 'Python', len(P['summary']))
ok = worst < 0.2 and res['n'] == len(P['summary'])
print('OK: JavaScript und Python stimmen überein.' if ok else 'ABWEICHUNG: model.js und sim.py prüfen.')
sys.exit(0 if ok else 1)
