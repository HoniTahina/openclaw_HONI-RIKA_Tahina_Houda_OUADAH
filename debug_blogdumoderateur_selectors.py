import yaml
import requests
from bs4 import BeautifulSoup
from pathlib import Path

path = Path('configs/blogdumoderateur.yaml')
data = yaml.safe_load(path.read_text(encoding='utf-8'))
resp = requests.get(data['url'], timeout=20)
soup = BeautifulSoup(resp.text, 'lxml')

print('URL:', data['url'])
print('Total main article count:', len(soup.select('main article')))
for i, article in enumerate(soup.select('main article')[:3]):
    print('\nARTICLE', i)
    h2s = article.select('h2')
    h3s = article.select('h3')
    print('  h2 count', len(h2s), 'h3 count', len(h3s))
    for j, h in enumerate(h2s + h3s):
        print('   HEADER', j, 'tag', h.name, 'text:', h.get_text(strip=True))
        print('    selector path:', ' > '.join([p.name for p in h.parents if p.name]))
        for a in h.select('a'):
            print('    A href=', a.get('href'))
            print('    A text=', a.get_text(strip=True))
            print('    A parent tag=', a.parent.name, 'classes=', a.parent.get('class'))
    print('  a count in article', len(article.select('a')))
    for a in article.select('a')[:5]:
        print('   A tag', a.name, 'href=', a.get('href'), 'text=', a.get_text(strip=True))
    print('  p count', len(article.select('p')))
    for p in article.select('p')[:3]:
        print('   P text=', p.get_text(strip=True)[:120])

print('\nSELECT test:')
for s in ['main article h2 a', 'main article h3 a', 'main article a', 'article h2 a', 'article h3 a', 'main article header h2 a', 'main article header h3 a', 'article a']:
    els = soup.select(s)
    print(f"{s}: {len(els)}")
    if els:
        print('   first:', els[0].get_text(strip=True), els[0].get('href'))
