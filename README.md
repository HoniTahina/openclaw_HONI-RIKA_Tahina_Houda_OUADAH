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
        ┌────────────┬───────┼───────┬─────────────┐
        v            v       v       v             v
  ┌──────────┐ ┌──────────┐ │ ┌───────────┐  ┌──────────┐
  │ Fetcher  │ │ Pipeline │ │ │ Validator │  │  Store   │
  │          │ │          │ │ │           │  │          │
  │ HTTP +   │ │ HTML ->  │ │ │  filtre   │  │ persiste │
  │ middle-  │ │ list[dict│ │ │  items    │  │ csv/json │
  │ wares    │ │ ]        │ │ │  invalides│  │ /sqlite  │
  └────┬─────┘ └──────────┘ │ └───────────┘  └──────────┘
       │                    │
       v                    │
┌─────────────────┐         │
│ Middleware chain │<────────┘
│                  │
│ Logging -> Retry │
│  -> (RateLimit)  │
└──────────────────┘
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
   |-- Store.save(valides) ------------------------> csv / sqlite / json
   |-- Pipeline.next_page_url(html, url) -----------> URL suivante ou None
   '-- (boucle jusqu'a None ou max_pages atteint)
```

## Composants

| Fichier | Role |
|---|---|
| `config.py` | Charge un YAML/JSON, valide les cles obligatoires, expose les valeurs en attributs (`config.fetcher.delay`) |
| `middleware.py` | `BaseMiddleware` (ABC) + `LoggingMiddleware`, `RetryMiddleware`, `RateLimitMiddleware` (bonus) |
| `fetcher.py` | Telechargement HTTP via `requests.Session()`, orchestre la chaine de middlewares, retry avec backoff exponentiel |
| `pipeline.py` | `BasePipeline` (ABC) + `GenericPipeline` (extraction pilotee par selecteurs CSS) + `PaginationPipeline` (gestion de la pagination) |
| `validator.py` | Filtre les items invalides (champs obligatoires, URL valide, longueur minimale) sans les modifier |
| `store.py` | Persistance multi-backend (csv/sqlite/json) avec deduplication sur `url`, export inter-backend |
| `orchestrator.py` | Assemble tous les composants, pilote le scraping complet, construit le rapport de session |
| `app.py` | CLI (`crawl`, `export`, `validate`) |

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate sous Windows
pip install -r requirements.txt
```
