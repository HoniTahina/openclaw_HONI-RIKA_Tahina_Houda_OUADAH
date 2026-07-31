import sqlite3, os, json
path='output/blogdumoderateur.db'
print('exists', os.path.exists(path))
if os.path.exists(path):
    con=sqlite3.connect(path)
    cur=con.cursor()
    print('tables', cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
    rows=cur.execute('SELECT data FROM items LIMIT 5').fetchall()
    print('rows', len(rows))
    for r in rows:
        data=json.loads(r[0])
        print('TITLE', data.get('titre'))
        print('URL', data.get('url'))
        print('CHAPEAU', data.get('chapeau'))
        print('---')
    con.close()
