from dataharvest.config import Config

config = Config("configs/books_toscrape.yaml")

print("URL :", config.url)
print("Pagination pattern :", config.pagination.pattern)
print("Max pages :", config.pagination.max_pages)
print("Selecteurs :", config.selectors)
print("Delay fetcher :", config.fetcher.delay, type(config.fetcher.delay))
print("Store backend :", config.store.backend)
print("Repr :", config)