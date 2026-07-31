# DataHarvest

Framework de scraping modulaire, configurable et extensible. Scrapez
n'importe quel site HTML statique en modifiant un fichier de
configuration YAML — sans toucher au code source.

## Architecture

DataHarvest est decoupe en 7 composants independants, communiquant
exclusivement par **injection de dependances** (constructeur), jamais par
import direct entre eux (sauf via l'Orchestrator, qui est le seul
composant a connaitre tous les autres).

```
                    ┌────────────────┐
                    │  Config (YAML) │
                    └────────┬───────┘
                             │
                             v
                  ┌─────────────────────┐
                  │     Orchestrator     │
                  │  (chef d'orchestre)  │
                  └──────────┬───────────┘
                             │
      ┌───────────┬──────────┼──────────┬────────────┬─────────────┐
      v           v          v          v            v             v
┌──────────┐┌──────────┐┌───────────┐┌──────────┐┌──────────┐┌──────────┐
│ Fetcher  ││ Pipeline ││ Validator ││  Store   ││  Detail  ││Middleware│
│          ││          ││           ││          ││Extractor │││  chain   │
│ HTTP +   ││ HTML ->  ││  filtre   ││ persiste ││(optionnel)││Logging-> │
│ retry    ││list[dict]││  items    ││ csv/json ││ liste ->  ││ Retry -> │
│          ││          ││  invalides││ /sqlite  ││ detail    ││(RateLimit)│
└────┬─────┘└──────────┘└───────────┘└──────────┘└──────────┘└──────────┘
     │
     v
┌──────────────────┐
│ Middleware chain  │
│                   │
│ Logging -> Retry  │
│  -> (RateLimit)   │
└───────────────────┘
```

### Flux de donnees pour une page

```
Config (YAML)
   |
   v
Orchestrator.run()
   |-- Fetcher.fetch(url) [chaine de Middleware] --> HTML brut
   |-- Pipeline.process(html) ---------------------> list[dict]
   |-- Validator.validate(items) ------------------> (valides, rejetes)
   |-- [SI config.detail actif] pour chaque item valide :
   |      Fetcher.fetch(item.url) -> DetailExtractor.extract(html)
   |      -> fusionne les champs supplementaires dans l'item
   |-- Store.save(valides) ------------------------> csv / sqlite / json
   |-- Pipeline.next_page_url(html, url) -----------> URL suivante ou None
   '-- (boucle jusqu'a None ou max_pages atteint)
```

## Composants

| Fichier | Role |
|---|---|
| `config.py` | Charge un YAML/JSON, valide les cles obligatoires, expose les valeurs en attributs (`config.fetcher.delay`) |
| `middleware.py` | `BaseMiddleware` (ABC) + `LoggingMiddleware`, `RetryMiddleware`, `RateLimitMiddleware` (bonus) |
| `fetcher.py` | Telechargement HTTP via `requests.Session()`, orchestre la chaine de middlewares, retry avec backoff exponentiel, correction automatique de l'encodage |
| `pipeline.py` | `BasePipeline` (ABC) + `GenericPipeline` (extraction pilotee par selecteurs CSS, 2 modes) + `PaginationPipeline` (gestion de la pagination) |
| `validator.py` | Filtre les items invalides (champs obligatoires configurables, URL valide, longueur minimale) sans les modifier |
| `store.py` | Persistance multi-backend (csv/sqlite/json) avec deduplication sur `url`, export inter-backend |
| `detail.py` | Extension "liste -> detail" : enrichit un item en visitant sa propre page (3 modes de selection) |
| `orchestrator.py` | Assemble tous les composants, pilote le scraping complet, construit le rapport de session |
| `app.py` | CLI (`crawl`, `export`, `validate`) |

### GenericPipeline : deux modes d'extraction

**Mode plat (par defaut)** : chaque champ est cherche sur toute la page,
puis les items sont reconstruits en zippant les resultats par index.
Simple et rapide, mais suppose que chaque champ apparait exactement une
fois par item, dans le meme ordre.

**Mode par ligne** (`row_selector` dans la config) : delimite d'abord les
conteneurs de lignes (ex: `table tr`, `div.quote`), puis cherche chaque
champ **a l'interieur** de chaque conteneur. Beaucoup plus robuste quand
une meme "carte" peut contenir plusieurs elements similaires (ex:
plusieurs liens/noms alternatifs dans une cellule Wikipedia).

Un champ peut aussi etre marque `multi: true` (uniquement en mode par
ligne) pour capturer **toutes** les occurrences a l'interieur d'une ligne
plutot qu'une seule (ex: tous les tags d'une citation, joints par `", "`).

### Selecteurs avances

Un selecteur peut etre une simple chaine CSS, ou un dict pour plus de
controle :

```yaml
selectors:
  titre: "h2.post-title a"                          # texte simple
  url: {selector: "h2.post-title a", attr: href}    # attribut precis
  note: {selector: "p.star-rating", attr: class}    # valeur encodee en classe CSS
  tags: {selector: "a.tag", multi: true}            # plusieurs valeurs (mode par ligne)
```

### Pattern "liste -> detail" (extension)

Pour des champs disponibles uniquement sur la fiche individuelle de
chaque item (ex: capitale et continent d'un pays, alors que la page liste
ne montre que le nom), ajoutez une section `detail` :

```yaml
detail:
  url_field: url          # champ de l'item contenant l'URL a visiter
  selectors:
    capitale:
      mode: label_lookup   # cherche un <th>/label correspondant au texte donne
      label: "Capitale"
    continent:
      mode: category_pattern  # cherche parmi des categories/tags via regex
      patterns:
        Afrique: "Portail:Afrique/Articles_li[ée]s"
        Europe: "Portail:Europe/Articles_li[ée]s"
```

L'Orchestrator visite alors automatiquement la page de chaque item valide
apres la page liste, et fusionne les champs extraits avant stockage.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate sous Windows
pip install -r requirements.txt
```

## Usage

### Lancer un crawl complet

```bash
python -m dataharvest crawl --config configs/books_toscrape.yaml
```

### Mode dry-run (teste sans stocker)

```bash
python -m dataharvest crawl --config configs/books_toscrape.yaml --dry-run
```

### Valider une config sans scraper

```bash
python -m dataharvest validate --config configs/books_toscrape.yaml
```

### Exporter d'un backend vers un autre

```bash
python -m dataharvest export --from output/articles.db --to output/articles.csv
```

## Format d'un fichier de configuration

```yaml
url: https://www.example.com/
row_selector: "article"      # optionnel : active le mode par ligne
pagination:
  pattern: "/page/{n}/"       # null si pas de pagination
  start: 1
  max_pages: 10
selectors:
  titre: "h2.post-title a"
  url: {selector: "h2.post-title a", attr: href}
  date: {selector: "time", attr: datetime}
validator:                    # optionnel : par defaut required_fields=[titre, url]
  required_fields: [titre, url]
  min_lengths: {titre: 5}
detail:                       # optionnel : pattern liste -> detail
  url_field: url
  selectors:
    capitale: {mode: label_lookup, label: "Capitale"}
fetcher:
  delay: 1.5
  retries: 3
  timeout: 15
  user_agent: "DataHarvest/1.0 (+contact@example.com)"
store:
  backend: sqlite   # csv | sqlite | json
  path: output/articles.db
```

Cles obligatoires : `url`, `pagination`, `selectors`, `fetcher`, `store`.
`row_selector`, `validator` et `detail` sont optionnels.

`Config` leve `FileNotFoundError` si le fichier n'existe pas, et
`ValueError` si une cle obligatoire manque.

## Tests

```bash
# Tests unitaires uniquement (rapide, pas de reseau)
pytest -m "not integration" -v

# Avec couverture
pytest --cov=dataharvest --cov-report=term-missing -m "not integration"

# Test d'integration (necessite internet)
pytest -m integration -v
```

Couverture actuelle : **91%** (objectif du sujet : ≥80%), 59 tests
unitaires.

## Sites testes

| Site | Niveau | Config | Sortie | Particularites |
|---|---|---|---|---|
| books.toscrape.com | 1 | `configs/books_toscrape.yaml` | `output/books.db` (sqlite) | Note encodee en classe CSS (`star-rating Three`), pas en texte -> selecteur `attr: class` |
| quotes.toscrape.com | 1 | `configs/quotes_toscrape.yaml` | `output/quotes.json` | Nombre variable de tags par citation -> mode par ligne + `multi: true` ; piege `<meta>` avant le 1er `<a class="tag">` cassant `:first-child` |
| blogdumoderateur.com | 3 | `configs/blogdumoderateur.yaml` | `output/blogdumoderateur.csv` | Selecteurs differents de l'exemple generique du sujet, verifies contre le vrai HTML |
| fr.wikipedia.org (pays) | 2 | `configs/wikipedia_pays.yaml` | `output/pays_wikipedia.json` | Plusieurs liens par cellule (noms alternatifs) -> resolu par le mode par ligne ; capitale/continent via pattern liste->detail |
| data.gouv.fr | 2 | `configs/datagouv.yaml` | `output/datagouv.csv` | Frontend Vue.js/Nuxt (cdata) avec classes Tailwind generiques mais structure stable ; titre/organisation dans des sous-elements imbriques, pas directement sur le lien |

## Limites connues (perimetre volontairement exclu)

- Pas de rendu JavaScript (sites SPA non supportes sans Selenium/Playwright)
- Pas d'authentification par formulaire (login) geree nativement
- Pas de crawl asynchrone/concurrent (contrairement a Scrapy + Twisted)
- Le mode par ligne resout l'alignement multi-champs, mais reste base sur
  CSS (pas de vrai support XPath) : certaines structures tres irregulieres
  peuvent encore necessiter une `Pipeline` personnalisee
- Le pattern liste -> detail ajoute une requete HTTP par item valide : pas
  adapte a des volumes tres eleves sans parallelisation