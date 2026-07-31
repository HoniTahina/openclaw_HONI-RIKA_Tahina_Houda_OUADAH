from dataharvest.pipeline import GenericPipeline, PaginationPipeline
from dataharvest.config import Box


HTML_SAMPLE = """
<html><body>
<div class="article">
  <h2 class="post-title"><a href="/article-1">Premier article</a></h2>
</div>
<div class="article">
  <h2 class="post-title"><a href="/article-2">Deuxieme article</a></h2>
</div>
</body></html>
"""

SELECTORS = {"titre": "h2.post-title a", "url": "h2.post-title a"}


def test_process_returns_list_on_empty_html():
    pipeline = GenericPipeline(SELECTORS)
    assert pipeline.process("") == []


def test_process_extracts_items():
    pipeline = GenericPipeline(SELECTORS, base_url="https://example.com")
    items = pipeline.process(HTML_SAMPLE)

    assert len(items) == 2
    assert items[0]["titre"] == "Premier article"
    assert items[0]["url"] == "https://example.com/article-1"
    assert items[1]["titre"] == "Deuxieme article"


def test_process_no_exception_on_missing_selector():
    selectors = {"titre": "h2.post-title a", "inexistant": ".ne-matche-rien-du-tout"}
    pipeline = GenericPipeline(selectors)
    items = pipeline.process(HTML_SAMPLE)

    assert items[0]["inexistant"] == ""


def test_process_returns_list_not_none_when_no_match():
    pipeline = GenericPipeline({"titre": ".nexiste-pas"})
    assert pipeline.process(HTML_SAMPLE) == []


def test_pagination_next_page_url():
    pagination_config = Box({"pattern": "/page/{n}/", "start": 1, "max_pages": 2})
    pipeline = PaginationPipeline(SELECTORS, pagination_config, base_url="https://example.com/")

    suivante = pipeline.next_page_url(HTML_SAMPLE, "https://example.com/")
    assert suivante == "https://example.com/page/2/"

    suivante2 = pipeline.next_page_url(HTML_SAMPLE, suivante)
    assert suivante2 is None  # max_pages atteint


def test_pagination_stops_on_empty_page():
    pagination_config = Box({"pattern": "/page/{n}/", "start": 1, "max_pages": 10})
    pipeline = PaginationPipeline(SELECTORS, pagination_config, base_url="https://example.com/")

    assert pipeline.next_page_url("<html></html>", "https://example.com/") is None


def test_pagination_no_pattern_returns_none():
    pagination_config = Box({"pattern": None, "start": 1, "max_pages": 1})
    pipeline = PaginationPipeline(SELECTORS, pagination_config, base_url="https://example.com/")

    assert pipeline.next_page_url(HTML_SAMPLE, "https://example.com/") is None


HTML_MULTI_VALUES = """
<div class="quote">
  <span class="text">Citation test</span>
  <div class="tags">
    <meta class="keywords" content="a, b, c">
    <a class="tag">change</a>
    <a class="tag">deep-thoughts</a>
    <a class="tag">thinking</a>
  </div>
</div>
"""


def test_row_mode_multi_captures_all_values():
    pipeline = GenericPipeline(
        selectors={
            "citation": "span.text",
            "tag": {"selector": "div.tags a.tag", "multi": True},
        },
        row_selector="div.quote",
    )
    items = pipeline.process(HTML_MULTI_VALUES)

    assert len(items) == 1
    assert items[0]["tag"] == "change, deep-thoughts, thinking"


def test_row_mode_single_value_ignores_meta_before_first_a():
    """
    Le premier enfant de div.tags est un <meta>, pas un <a class='tag'> --
    un champ non-multi doit quand meme trouver le premier <a> via
    select_one, sans etre trompe par le <meta> precedent.
    """
    pipeline = GenericPipeline(
        selectors={"premier_tag": "div.tags a.tag"},
        row_selector="div.quote",
    )
    items = pipeline.process(HTML_MULTI_VALUES)
    assert items[0]["premier_tag"] == "change"


HTML_RATING_SAMPLE = """
<html><body>
<article class="product_pod">
  <p class="star-rating Three"></p>
  <h3><a href="/livre-1" title="Livre Un">Livre Un</a></h3>
</article>
<article class="product_pod">
  <p class="star-rating Five"></p>
  <h3><a href="/livre-2" title="Livre Deux">Livre Deux</a></h3>
</article>
</body></html>
"""


def test_selector_with_attr_class_extracts_rating():
    selectors = {
        "titre": "h3 a",
        "url": {"selector": "h3 a", "attr": "href"},
        "note": {"selector": "p.star-rating", "attr": "class"},
    }
    pipeline = GenericPipeline(selectors, base_url="https://books.example.com/")
    items = pipeline.process(HTML_RATING_SAMPLE)

    assert len(items) == 2
    assert items[0]["note"] == "Three"
    assert items[1]["note"] == "Five"
    assert items[0]["url"] == "https://books.example.com/livre-1"


def test_selector_string_still_works_backward_compatible():
    pipeline = GenericPipeline(SELECTORS, base_url="https://example.com")
    items = pipeline.process(HTML_SAMPLE)
    assert items[0]["titre"] == "Premier article"