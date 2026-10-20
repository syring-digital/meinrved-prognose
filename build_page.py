"""Konzeptseite bauen: seite/template.html + seite/model.js + seite/data.json -> seite/edersee-prognose.html.
Hinweis: Stufe-1-Kennzahlen, Starttag und Regattatermine stehen als Stand 19.10.2026 fest im Template."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PAGE

t = open(os.path.join(PAGE, 'template.html')).read()
data = open(os.path.join(PAGE, 'data.json')).read().replace('</', '<\\/')
html = t.replace('__DATA__', data).replace('__MODEL__', open(os.path.join(PAGE, 'model.js')).read())
open(os.path.join(PAGE, 'edersee-prognose.html'), 'w').write(html)
print('->', os.path.join(PAGE, 'edersee-prognose.html'), f'({len(html) // 1024} KB)')
