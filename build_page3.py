"""Konzeptseite Stufe 1–4 bauen: seite/template3.html + seite/model3.js + seite/data3.json -> seite/edersee-prognose.html."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PAGE

t = open(os.path.join(PAGE, 'template3.html')).read()
data = open(os.path.join(PAGE, 'data3.json')).read().replace('</', '<\\/')
html = t.replace('__DATA__', data).replace('__MODEL__', open(os.path.join(PAGE, 'model3.js')).read())
open(os.path.join(PAGE, 'edersee-prognose.html'), 'w').write(html)
print('->', os.path.join(PAGE, 'edersee-prognose.html'), f'({len(html) // 1024} KB)')
