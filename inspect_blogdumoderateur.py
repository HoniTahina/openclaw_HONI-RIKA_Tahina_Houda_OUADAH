import yaml
import requests
from bs4 import BeautifulSoup
from pathlib import Path

path = Path('configs/blogdumoderateur.yaml')
data = yaml.safe_load(path.read_text(encoding='utf-8'))
url = data['url']
print('URL:', url)
print('Selectors:')
for k, v in data['selectors'].items():
    print(' ', k, v)

resp = requests.get(url, timeout=20)
print('status', resp.status_code)
html = resp.text
soup = BeautifulSoup(html, 'lxml')
print('Page title:', soup.title.string if soup.title else 'no title')
print('\nFirst article titles/links/paragraphs:')
for i, article in enumerate(soup.select('main article')[:3]):
    print('ARTICLE', i)
    titles = article.select('h2, h3, h1')
    for t in titles:
        print(' TITLE:', t.get_text(strip=True))
        for a in t.select('a'):
            print('  LINK:', a.get('href'), 'TEXT:', a.get_text(strip=True))
    for a in article.select('a'):
        if a.get_text(strip=True):
            print(' A:', a.get('href'), 'TEXT:', a.get_text(strip=True))
    for p in article.select('p'):
        print(' P:', p.get_text(strip=True)[:120])
    print('---')

for champ, spec in data['selectors'].items():
    if isinstance(spec, dict):
        selector = spec.get('selector')
        attr = spec.get('attr', 'text')
    else:
        selector = spec
        attr = 'text'
    els = soup.select(selector)
    print(f'{champ}: selector={selector!r} count={len(els)} attr={attr}')
    if els:
        for i, el in enumerate(els[:3]):
            print('   ', i, repr(el)[:200])
print('ref selector count:', len(soup.select('main article h2 a, main article h3 a')))