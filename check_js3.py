"""Prüft seite/model3.js gegen stage3.simulate3 (Standardregeln, WSA-Plan, Haltelinie) und die Seitenskripte auf Syntaxfehler."""
import os, sys, re, json, subprocess, tempfile, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PAGE, pct
import stage3 as s3

D = json.load(open(os.path.join(PAGE, 'data3.json')))
start = dt.date.fromisoformat(D['start'])
plan = {(dt.date.fromisoformat(d) - start).days: v for d, v in D['plan']['plan'] if dt.date.fromisoformat(d) >= start}
ks = [7, 60, 200, 300]
py = {}
for name, kw in (('standard', {}), ('haltelinie', dict(rule125=True))):
    sims = [s3.simulate3(D['V0'], start, r['q'], r['r'], plan=plan, **kw) for r in D['runs']]
    py[name] = [round(pct([s[k][1] for s in sims], .5), 2) for k in ks]
js = 'var DATA = ' + json.dumps(D) + ';\n' + open(os.path.join(PAGE, 'model3.js')).read() + f'''
Model3.init(DATA);
var T0 = Model3.utc({start.year}, {start.month}, {start.day}), plan = {json.dumps({str(k): v for k, v in plan.items()})}, out = {{}};
[['standard', null], ['haltelinie', {{limit: 125, spar: 6, from: 5, to: 8}}]].forEach(function (c) {{
  var sims = DATA.runs.map(function (r) {{ return Model3.simulate(DATA.V0, T0, r.q, r.r, {{plan: plan, h125: c[1]}}); }});
  out[c[0]] = {json.dumps(ks)}.map(function (k) {{ return Math.round(Model3.pct(sims.map(function (s) {{ return s.vol[k]; }}), .5) * 100) / 100; }});
}});
JSON.stringify(out);
'''
with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f: f.write(js)
res = json.loads(subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True).stdout); os.unlink(f.name)
ok = True
for name in py:
    diff = max(abs(a - b) for a, b in zip(py[name], res[name])); ok &= diff < 0.2
    print(f'{name:11} Tag {ks}: Python {py[name]} JS {res[name]} max. Abweichung {diff:.3f}')
html = open(os.path.join(PAGE, 'edersee-prognose.html')).read()
scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
chk = 'var src = ' + json.dumps(scripts) + ';\nvar r = []; src.forEach(function (s, i) { try { new Function(s); r.push("Skript " + i + " ok"); } catch (e) { r.push("Skript " + i + " FEHLER: " + e); } }); r.join("; ");'
with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f: f.write(chk)
syn = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True).stdout.strip(); os.unlink(f.name)
print(syn); ok &= 'FEHLER' not in syn
print('OK' if ok else 'ABWEICHUNG')
sys.exit(0 if ok else 1)
