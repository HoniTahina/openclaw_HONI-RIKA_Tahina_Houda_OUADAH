import requests
from bs4 import BeautifulSoup
url='https://www.blogdumoderateur.com/articles/'
html=requests.get(url, timeout=20, headers={'User-Agent':'Mozilla/5.0'}).text
soup=BeautifulSoup(html, 'lxml')
print('TITLE:', soup.title.get_text(' ', strip=True))
articles=soup.select('main article')[:5]
print('count', len(articles))
for i, article in enumerate(articles, 1):
    print('--- article', i, '---')
    a=article.select_one('a')
    print('link', a.get('href') if a else None)
    for sel in ['p','h2','h3','.entry-content','.post-excerpt','.excerpt','.entry-summary','.post-card__excerpt','.entry-title']:
        el=article.select_one(sel)
        if el:
            txt=' '.join(el.get_text(' ', strip=True).split())
            print(sel, '->', txt[:500])
    print('all p tags:')
    for p in article.select('p')[:8]:
        txt=' '.join(p.get_text(' ', strip=True).split())
        print(' ', txt[:500])
