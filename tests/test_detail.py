from dataharvest.detail import DetailExtractor


HTML_FICHE = """
<html><head>
<link rel="mw:PageProp/Category" href="./Catégorie:Portail:Afrique_du_Sud/Articles_liés">
<link rel="mw:PageProp/Category" href="./Catégorie:Portail:Afrique/Articles_liés">
</head><body>
<table>
<tr><th>Capitale</th><td><a>Pretoria</a></td></tr>
<tr><th>Code ISO 3166-1</th><td><code>ZAF, ZA</code></td></tr>
</table>
</body></html>
"""


def test_extract_returns_dict_with_all_fields():
    extractor = DetailExtractor({"capitale": {"mode": "label_lookup", "label": "Capitale"}})
    resultat = extractor.extract(HTML_FICHE)
    assert resultat == {"capitale": "Pretoria"}


def test_extract_empty_html_returns_empty_values():
    extractor = DetailExtractor({"capitale": {"mode": "label_lookup", "label": "Capitale"}})
    resultat = extractor.extract("")
    assert resultat == {"capitale": ""}


def test_label_lookup_not_found_returns_empty_string():
    extractor = DetailExtractor({"inexistant": {"mode": "label_lookup", "label": "Population"}})
    resultat = extractor.extract(HTML_FICHE)
    assert resultat["inexistant"] == ""


def test_category_pattern_finds_correct_continent():
    extractor = DetailExtractor({
        "continent": {
            "mode": "category_pattern",
            "patterns": {
                "Afrique": r"Portail:Afrique/Articles_li[ée]s",
                "Europe": r"Portail:Europe/Articles_li[ée]s",
            },
        }
    })
    resultat = extractor.extract(HTML_FICHE)
    assert resultat["continent"] == "Afrique"


def test_category_pattern_avoids_false_positive_on_country_portal():
    """
    Portail:Afrique_du_Sud/Articles_liés ne doit PAS matcher le motif
    "Afrique" seul (faux positif deja rencontre dans un TP anterieur).
    """
    extractor = DetailExtractor({
        "continent": {
            "mode": "category_pattern",
            "patterns": {"Afrique": r"Portail:Afrique/Articles_li[ée]s"},
        }
    })
    html_sans_bon_portail = """
    <link rel="mw:PageProp/Category" href="./Catégorie:Portail:Afrique_du_Sud/Articles_liés">
    """
    resultat = extractor.extract(html_sans_bon_portail)
    assert resultat["continent"] == ""


def test_css_mode_with_attr():
    html = '<p class="star-rating Three"></p>'
    extractor = DetailExtractor({"note": {"mode": "css", "selector": "p.star-rating", "attr": "class"}})
    resultat = extractor.extract(html)
    assert resultat["note"] == "Three"


def test_css_mode_simple_string_selector():
    html = "<p class='prix'>19.99</p>"
    extractor = DetailExtractor({"prix": "p.prix"})
    resultat = extractor.extract(html)
    assert resultat["prix"] == "19.99"


def test_invalid_selector_does_not_raise():
    extractor = DetailExtractor({"champ": {"mode": "css", "selector": "((("}})
    resultat = extractor.extract(HTML_FICHE)
    assert resultat["champ"] == ""