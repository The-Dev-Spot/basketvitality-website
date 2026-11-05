#!/usr/bin/env python3
"""Generate the checker and content pages. Output is committed, and the site has no build step.

Usage: build_pages.py SEED.jsonl.gz

Food-page figures come from the seed the app ships, through food_groups.py.
Everything else is written here so the shared header and footer stay in one place.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from food_groups import GRADES, GROUPS, figures, load, members  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VERSION = "2026-07"
INDEX_FILE = f"/data/products-nl-{VERSION}.json"
PLAY = "https://play.google.com/store/apps/details?id=com.thedevspot.basketvitality"
BASE = "https://basketvitality.com"
REVIEWED = {"en": "Last reviewed 5 November 2026", "nl": "Laatst nagekeken op 5 november 2026"}

PATHS = {
    "checker": ("/checker/", "/nl/lijst-checker/"),
    "scores": ("/scores/", "/nl/scores/"),
    "hagelslag": ("/scores/hagelslag/", "/nl/scores/hagelslag/"),
    "halfvolle-melk": ("/scores/semi-skimmed-milk/", "/nl/scores/halfvolle-melk/"),
    "havermout": ("/scores/oats/", "/nl/scores/havermout/"),
    "pindakaas": ("/scores/peanut-butter/", "/nl/scores/pindakaas/"),
    "muesli": ("/scores/muesli/", "/nl/scores/muesli/"),
    "methodology": ("/methodology/", "/nl/methode/"),
    "receipt": ("/receipt-scanning/", "/nl/kassabon-scannen/"),
    "professionals": ("/for-professionals/", "/nl/voor-professionals/"),
}

UI = {
    "en": {
        "home": "/", "roadmap": "/roadmap/", "skip": "Skip to content", "nav": "Main navigation",
        "checker": "List checker", "scores": "Food scores", "receipt": "Receipt scanning",
        "roadmap_label": "Roadmap", "methodology": "Methodology", "professionals": "For professionals",
        "privacy": "Privacy Policy", "footer": "Footer", "locale": "en_GB",
        "get": "Get Basket Vitality free",
        "availability": "Android · On Google Play in the Netherlands and Belgium.",
        "attribution": 'Product data © <a href="https://world.openfoodfacts.org">Open Food Facts</a> contributors, Open Database License (ODbL) v1.0. Based on data from NEVO online version 2025/9.0, RIVM, Bilthoven and other data sources. Environmental data: AGRIBALYSE® (ADEME), CC-BY 4.0.',
        "advice": "Basket Vitality gives you information, not medical or financial advice. Not affiliated with or endorsed by any supermarket or brand. Nutri-Score is a trademark of Santé publique France, which is not affiliated with Basket Vitality.",
        "business": 'The Dev Spot · Westerstraat 10 UNIT G4118, 3016 DH Rotterdam, Netherlands<br>Chamber of Commerce (KVK) 42149955 · <a href="mailto:privacy@basketvitality.com">privacy@basketvitality.com</a><br>VAT NL005535532B67<br>Prices shown include VAT. Payment and billing are handled by Google Play.',
    },
    "nl": {
        "home": "/nl/", "roadmap": "/nl/roadmap/", "skip": "Naar de inhoud", "nav": "Hoofdnavigatie",
        "checker": "Lijst-checker", "scores": "Voedingsscores", "receipt": "Kassabon scannen",
        "roadmap_label": "Roadmap", "methodology": "Methode", "professionals": "Voor professionals",
        "privacy": "Privacybeleid", "footer": "Voettekst", "locale": "nl_NL",
        "get": "Download Basket Vitality gratis",
        "availability": "Android · Op Google Play in Nederland en België.",
        "attribution": 'Productgegevens © <a href="https://world.openfoodfacts.org">Open Food Facts</a>-bijdragers, Open Database License (ODbL) v1.0. Based on data from NEVO online version 2025/9.0, RIVM, Bilthoven and other data sources. Milieugegevens: AGRIBALYSE® (ADEME), CC-BY 4.0.',
        "advice": "Basket Vitality geeft je informatie, geen medisch of financieel advies. Niet verbonden aan of goedgekeurd door een supermarkt of merk. Nutri-Score is een merk van Santé publique France, dat niet verbonden is aan Basket Vitality.",
        "business": 'The Dev Spot · Westerstraat 10 UNIT G4118, 3016 DH Rotterdam<br>KvK 42149955 · <a href="mailto:privacy@basketvitality.com">privacy@basketvitality.com</a><br>Btw-id NL005535532B67<br>Genoemde prijzen zijn inclusief btw. Betaling en facturatie lopen via Google Play.',
    },
}

# Copied from the app's strings (disclaimer_body). Keep these identical (HOM-754).
DISCLAIMER = {
    "en": "Basket Vitality provides product information and general suggestions. It is not a medical app and does not give advice for medical or dietary conditions such as diabetes, allergies, or eating disorders — always consult a qualified professional.",
    "nl": "Basket Vitality biedt productinformatie en algemene suggesties. Het is geen medische app en geeft geen advies voor medische of dieetgerelateerde aandoeningen zoals diabetes, allergieën of eetstoornissen — raadpleeg altijd een gekwalificeerde professional.",
}


def number(value, lang):
    text = f"{value:,}"
    return text.replace(",", ".") if lang == "nl" else text


def decimal(value, lang):
    text = f"{value:g}"
    return text.replace(".", ",") if lang == "nl" else text


def path(key, lang):
    return PATHS[key][0 if lang == "en" else 1]


def page(key, lang, title, description, body, scripted=False):
    ui = UI[lang]
    canonical, en, nl = BASE + path(key, lang), BASE + path(key, "en"), BASE + path(key, "nl")
    script = '\n    <script type="module" src="/checker.js"></script>' if scripted else ""
    current = lambda k: ' aria-current="page"' if k == key or (k == "scores" and key in GROUPS) else ""
    return f"""<!doctype html>
<html lang="{lang}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <link rel="canonical" href="{canonical}">
    <link rel="alternate" hreflang="en" href="{en}">
    <link rel="alternate" hreflang="nl" href="{nl}">
    <link rel="alternate" hreflang="x-default" href="{en}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Basket Vitality">
    <meta property="og:locale" content="{ui['locale']}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{BASE}/og-image.png">
    <meta property="og:image:alt" content="Basket Vitality">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{BASE}/og-image.png">
    <meta name="theme-color" content="#F6F2DE">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">
    <link rel="stylesheet" href="/roadmap.css">
    <link rel="stylesheet" href="/pages.css">{script}
  </head>
  <body>
    <a class="skip-link" href="#main">{ui['skip']}</a>
    <header class="wrap">
      <nav class="primary-nav" aria-label="{ui['nav']}">
        <a class="wordmark" href="{ui['home']}">Basket <em>Vitality</em></a>
        <div class="site-links">
          <a href="{path('checker', lang)}"{current('checker')}>{ui['checker']}</a>
          <a href="{path('scores', lang)}"{current('scores')}>{ui['scores']}</a>
          <a href="{path('receipt', lang)}"{current('receipt')}>{ui['receipt']}</a>
          <a href="{ui['roadmap']}">{ui['roadmap_label']}</a>
        </div>
        <div class="langswitch">
          <a href="{path(key, 'en')}" lang="en" hreflang="en"{' aria-current="true"' if lang == 'en' else ''}>EN</a>
          <a href="{path(key, 'nl')}" lang="nl" hreflang="nl"{' aria-current="true"' if lang == 'nl' else ''}>NL</a>
        </div>
      </nav>
    </header>
    <main id="main">
{body}
    </main>
    <footer class="footer">
      <div class="wrap">
        <p>Basket Vitality · The Dev Spot</p>
        <nav class="footer-links" aria-label="{ui['footer']}">
          <a href="{ui['home']}">Home</a>
          <a href="{path('checker', lang)}">{ui['checker']}</a>
          <a href="{path('scores', lang)}">{ui['scores']}</a>
          <a href="{path('receipt', lang)}">{ui['receipt']}</a>
          <a href="{path('methodology', lang)}">{ui['methodology']}</a>
          <a href="{path('professionals', lang)}">{ui['professionals']}</a>
          <a href="{ui['roadmap']}">{ui['roadmap_label']}</a>
          <a href="/privacy/">{ui['privacy']}</a>
        </nav>
        <p class="legal">{ui['attribution']}</p>
        <p class="legal">{ui['advice']}</p>
        <p class="legal">{ui['business']}</p>
        <p class="copyright">© 2026 The Dev Spot.</p>
      </div>
    </footer>
  </body>
</html>
"""


def hero(eyebrow, heading, lead, extra=""):
    return f"""      <div class="wrap hero">
        <p class="eyebrow">{eyebrow}</p>
        <h1>{heading}</h1>
        <p class="lead">{lead}</p>
        {extra}
      </div>"""


def cta(lang, heading, text):
    ui = UI[lang]
    return f"""      <section class="tint">
        <div class="wrap cta">
          <div>
            <h2>{heading}</h2>
            <p>{text}</p>
            <p class="availability">{ui['availability']}</p>
          </div>
          <a class="btn" href="{PLAY}">{ui['get']}</a>
        </div>
      </section>"""


def section(content, tint=False):
    return f"""      <section{' class="tint"' if tint else ''}>
        <div class="wrap prose">
{content}
        </div>
      </section>"""


# ---- Checker ---------------------------------------------------------------

def checker_page(lang, stats):
    count = number(stats["products"], lang)
    if lang == "en":
        title = "Free shopping-list checker: Nutri-Scores for your groceries — Basket Vitality"
        description = "Type your shopping list and see the Nutri-Score of each product. Free, no account, and your list stays in your browser."
        top = hero("Free shopping-list checker", "Check your list <em>before you shop.</em>",
                   "Type one product per line to see its Nutri-Score. No account, and your list stays in your browser.")
        form_copy = dict(label="Your shopping list", placeholder="havermout\nhalfvolle melk\npindakaas", check="Check my list", example="Try an example",
                         example_list="havermout|halfvolle melk|pindakaas|hagelslag|appelsap|kipfilet",
                         note="Your list isn't stored or sent anywhere. <strong>Search online</strong> appears when needed, and only sends the item you tap.",
                         nojs="This checker needs JavaScript. It runs only on this page, and only from our own site.")
        how = f"""          <h2>How it works</h2>
          <p>The page downloads a list of {count} products with a Nutri-Score, then searches it in your browser. Search by product name, in Dutch, and add a brand to narrow it down.</p>
          <h3>Why some items show a range</h3>
          <p>"Chicken fillet" isn't one product. When matching products score differently, the checker shows the range and lets you choose, instead of inventing one score.</p>
          <h3>What it can't do</h3>
          <p>It only knows products with a Nutri-Score in our data, and that data comes from volunteers, so some records are wrong or out of date. We warn you when a record's numbers look inconsistent. The pack is always the final word. Read <a href="{path('methodology', lang)}">how the scores work</a>.</p>"""
        final = cta(lang, "A list can't tell you what the shop cost. <em>Your receipt can.</em>",
                    "Scan a grocery receipt to see what it cost against your budget and what it scored. Scanning is free, with no account.")
    else:
        title = "Gratis boodschappenlijst-checker: Nutri-Scores voor je boodschappen — Basket Vitality"
        description = "Typ je boodschappenlijst en zie de Nutri-Score van elk product. Gratis, zonder account, en je lijst blijft in je browser."
        top = hero("Gratis boodschappenlijst-checker", "Check je lijst <em>voordat je gaat winkelen.</em>",
                   "Typ één product per regel en zie de Nutri-Score. Geen account, en je lijst blijft in je browser.")
        form_copy = dict(label="Je boodschappenlijst", placeholder="havermout\nhalfvolle melk\npindakaas", check="Check mijn lijst", example="Probeer een voorbeeld",
                         example_list="havermout|halfvolle melk|pindakaas|hagelslag|appelsap|kipfilet",
                         note="Je lijst wordt nergens opgeslagen of naartoe gestuurd. <strong>Online zoeken</strong> verschijnt als dat nodig is, en stuurt alleen de regel waarop je tikt.",
                         nojs="Deze checker heeft JavaScript nodig. Dat draait alleen op deze pagina, en alleen vanaf onze eigen site.")
        how = f"""          <h2>Zo werkt het</h2>
          <p>De pagina downloadt een lijst van {count} producten met een Nutri-Score en doorzoekt die in je browser. Zoek op productnaam en voeg een merk toe om preciezer te zoeken.</p>
          <h3>Waarom sommige regels een bereik tonen</h3>
          <p>"Kipfilet" is niet één product. Als gevonden producten verschillend scoren, toont de checker het bereik en laat hij je kiezen, in plaats van één score te verzinnen.</p>
          <h3>Wat de checker niet kan</h3>
          <p>Hij kent alleen producten met een Nutri-Score in onze gegevens, en die gegevens komen van vrijwilligers, dus sommige records kloppen niet of zijn verouderd. We waarschuwen als de cijfers van een record niet lijken te kloppen. De verpakking heeft altijd het laatste woord. Lees <a href="{path('methodology', lang)}">hoe de scores werken</a>.</p>"""
        final = cta(lang, "Een lijst vertelt niet wat de boodschappen kostten. <em>Je kassabon wel.</em>",
                    "Scan een kassabon en zie wat het kostte ten opzichte van je budget en hoe het scoorde. Scannen is gratis, zonder account.")
    tool = f"""      <section>
        <div class="wrap checker">
          <div class="checker-form">
            <label for="list">{form_copy['label']}</label>
            <textarea id="list" rows="9" maxlength="2000" spellcheck="false" autocomplete="off" placeholder="{form_copy['placeholder']}"></textarea>
            <div class="checker-actions">
              <button id="check" type="button">{form_copy['check']}</button>
              <button id="example" type="button" data-list="{form_copy['example_list']}">{form_copy['example']}</button>
            </div>
            <p class="privacy-note">{form_copy['note']}</p>
            <noscript><p class="no-js">{form_copy['nojs']}</p></noscript>
          </div>
          <div aria-live="polite">
            <p id="status"></p>
            <div id="summary" tabindex="-1" hidden></div>
            <ul id="results"></ul>
          </div>
        </div>
      </section>"""
    return page("checker", lang, title, description,
                "\n".join([top, tool, section(how, tint=True), final]), scripted=True)


# ---- Food pages ------------------------------------------------------------

def score_table(lang, data):
    total = data["total"]
    largest = max(data["counts"].values())
    caption = f"{number(total, lang)} products with a Nutri-Score" if lang == "en" else f"{number(total, lang)} producten met een Nutri-Score"
    head = ("Nutri-Score", "Share", "Products") if lang == "en" else ("Nutri-Score", "Aandeel", "Producten")
    rows = []
    for grade in GRADES:
        count = data["counts"][grade]
        share = round(100 * count / total)
        width = round(100 * count / largest) if count else 0
        bar = f'<span class="bar" style="width:{width}%"></span>' if count else ""
        rows.append(f"""              <tr>
                <th scope="row"><span class="grade small {grade.lower()}">{grade}</span></th>
                <td class="bar-cell">{bar}</td>
                <td class="num">{share}%</td>
                <td class="num">{number(count, lang)}</td>
              </tr>""")
    rows = "\n".join(rows)
    return f"""          <table class="score-table">
            <caption>{caption}</caption>
            <thead>
              <tr><th scope="col">{head[0]}</th><th scope="col"><span class="visually-hidden">{head[1]}</span></th><th scope="col" class="num">{head[1]}</th><th scope="col" class="num">{head[2]}</th></tr>
            </thead>
            <tbody>
{rows}
            </tbody>
          </table>"""


def values(lang, data, unit):
    labels = {
        "en": {"energyKcal": "Energy", "sugars": "Sugars", "saturatedFat": "Saturated fat", "salt": "Salt", "fiber": "Fibre", "proteins": "Protein"},
        "nl": {"energyKcal": "Energie", "sugars": "Suikers", "saturatedFat": "Verzadigd vet", "salt": "Zout", "fiber": "Vezels", "proteins": "Eiwit"},
    }[lang]
    units = {"energyKcal": "kcal"}
    items = []
    for key in ("energyKcal", "sugars", "saturatedFat", "salt", "fiber", "proteins"):
        median = data["medians"].get(key)
        if median:
            value = median["value"]
            shown = round(value) if key == "energyKcal" else value
            items.append(f'            <div><dt>{labels[key]}</dt><dd>{decimal(shown, lang)} {units.get(key, "g")}</dd></div>')
    n = max(m["n"] for m in data["medians"].values() if m)
    note = (f"The middle value per {unit}, from the {number(n, lang)} products that have nutrition values in our data."
            if lang == "en" else f"De middelste waarde per {unit}, van de {number(n, lang)} producten met voedingswaarden in onze gegevens.")
    return "          <dl class=\"values\">\n" + "\n".join(items) + f"\n          </dl>\n          <p class=\"fine\">{note}</p>"


def method_note(lang, excluded):
    if lang == "en":
        removed = f" We read every product name and removed {excluded}." if excluded else " We read every product name and removed nothing."
        return f"""          <h2>How we counted</h2>
          <p>These are the products in the database shipped with the Basket Vitality app (July 2026) with this food in their name and a Nutri-Score.{removed} Every product counts once, whatever it sells. The grades come from Open Food Facts records, which volunteers add, and we haven't checked them against each pack. Read the <a href="{path('methodology', lang)}">full method</a>.</p>"""
    removed = f" We hebben elke productnaam gelezen en {excluded} verwijderd." if excluded else " We hebben elke productnaam gelezen en niets verwijderd."
    return f"""          <h2>Hoe we telden</h2>
          <p>Dit zijn de producten in de database van de Basket Vitality-app (juli 2026) met dit voedingsmiddel in de naam en een Nutri-Score.{removed} Elk product telt één keer mee, hoeveel het ook verkoopt. De scores komen uit records van Open Food Facts, die vrijwilligers toevoegen, en we hebben ze niet met elke verpakking vergeleken. Lees de <a href="{path('methodology', lang)}">volledige methode</a>.</p>"""


def food_copy(slug, lang, data, extra):
    c, m = data["counts"], data["medians"]
    t = data["total"]
    n = lambda v: number(v, lang)
    d = lambda key: decimal(m[key]["value"], lang)
    if slug == "hagelslag":
        assert c["E"] >= 70 and extra["less_sugar_e"] >= 1
        if lang == "en":
            return dict(name="hagelslag", title="How does hagelslag score on Nutri-Score?", heading="How does hagelslag <em>score?</em>", unit="100 g",
                        lead=f"{n(c['E'])} of the {n(t)} hagelslag products with a Nutri-Score get an E. The rest get a D.",
                        short=f"{n(c['E'])} of {n(t)} score E.", excluded="",
                        body=f"The typical product here has {d('sugars')} g of sugar per 100 g, which leaves little room for a better grade. Even a product labelled 30% less sugar scores E. So the score won't help you choose between brands, because nearly all of them land in the same place. It compares products, and it doesn't tell you to skip the hagelslag.")
        return dict(name="hagelslag", title="Hoe scoort hagelslag op Nutri-Score?", heading="Hoe scoort hagelslag <em>op Nutri-Score?</em>", unit="100 g",
                    lead=f"{n(c['E'])} van de {n(t)} hagelslagproducten met een Nutri-Score krijgen een E. De rest krijgt een D.",
                    short=f"{n(c['E'])} van de {n(t)} scoren E.", excluded="",
                    body=f"Het typische product heeft hier {d('sugars')} g suiker per 100 g, en dat laat weinig ruimte voor een betere score. Zelfs een product met 30% minder suiker op de verpakking scoort een E. De score helpt je dus niet kiezen tussen merken, want bijna alles komt op dezelfde plek uit. Hij vergelijkt producten en zegt niet dat je de hagelslag moet laten staan.")
    if slug == "halfvolle-melk":
        assert c["B"] >= 90 and extra["bio_lactose_b"] == extra["bio_lactose"]
        if lang == "en":
            return dict(name="semi-skimmed milk", title="How does semi-skimmed milk score on Nutri-Score?", heading="How does semi-skimmed milk <em>score?</em>", unit="100 ml",
                        lead=f"{n(c['B'])} of the {n(t)} semi-skimmed milks (halfvolle melk) with a Nutri-Score get a B.",
                        short=f"{n(c['B'])} of {n(t)} score B.", excluded="chocolate milk and plant-based drinks",
                        body=f"Organic and lactose-free versions don't change the picture: all {n(extra['bio_lactose'])} in this group get a B. The grade won't separate one carton from another, so price or preference can decide. Two records differ, one A and one D. We haven't checked whether those are real differences or record errors.")
        return dict(name="halfvolle melk", title="Hoe scoort halfvolle melk op Nutri-Score?", heading="Hoe scoort halfvolle melk <em>op Nutri-Score?</em>", unit="100 ml",
                    lead=f"{n(c['B'])} van de {n(t)} soorten halfvolle melk met een Nutri-Score krijgen een B.",
                    short=f"{n(c['B'])} van de {n(t)} scoren B.", excluded="chocolademelk en plantaardige dranken",
                    body=f"Biologisch of lactosevrij verandert het beeld niet: alle {n(extra['bio_lactose'])} in deze groep krijgen een B. De score maakt dus geen verschil tussen het ene pak en het andere, dus prijs of voorkeur mag beslissen. Twee records wijken af, een A en een D. We hebben niet gecontroleerd of dat echte verschillen of fouten in de records zijn.")
    if slug == "havermout":
        assert c["A"] >= 40 and c["B"] == 2 and c["C"] == 1
        if lang == "en":
            return dict(name="oats", title="How do oats score on Nutri-Score?", heading="How do oats <em>score?</em>", unit="100 g",
                        lead=f"{n(c['A'])} of the {n(t)} oat products (havermout) with a Nutri-Score get an A.",
                        short=f"{n(c['A'])} of {n(t)} score A.", excluded="bars, muesli, granola and snack sticks",
                        body=f"The typical product has {d('sugars')} g of sugar and {d('fiber')} g of fibre per 100 g. The two products with a B are flavoured porridges, so check flavoured versions rather than assuming they match the plain bag. Records aren't perfect here either: we found one plain oat record listing just 1 g of fibre.")
        return dict(name="havermout", title="Hoe scoort havermout op Nutri-Score?", heading="Hoe scoort havermout <em>op Nutri-Score?</em>", unit="100 g",
                    lead=f"{n(c['A'])} van de {n(t)} havermoutproducten met een Nutri-Score krijgen een A.",
                    short=f"{n(c['A'])} van de {n(t)} scoren A.", excluded="repen, muesli, granola en snacksticks",
                    body=f"Het typische product heeft {d('sugars')} g suiker en {d('fiber')} g vezels per 100 g. De twee producten met een B zijn havermout met smaak, dus controleer zulke varianten in plaats van aan te nemen dat ze net zo scoren als de gewone zak. Ook hier zijn de records niet perfect: we vonden een record van gewone havermout met maar 1 g vezels.")
    if slug == "pindakaas":
        assert extra["hundred_a"] >= 40
        if lang == "en":
            return dict(name="peanut butter", title="How does peanut butter score on Nutri-Score?", heading="How does peanut butter <em>score?</em>", unit="100 g",
                        lead=f"Peanut butter (pindakaas) has a real spread: {n(c['A'])} products get an A and {n(c['C'])} get a C, out of {n(t)}.",
                        short=f"{n(c['A'])} score A and {n(c['C'])} score C, of {n(t)}.", excluded="",
                        body=f"This is a food where comparing helps. Of the {n(extra['hundred'])} products with 100 in the name, usually meaning 100% peanuts, {n(extra['hundred_a'])} get an A. An A doesn't mean low in energy, though: the typical product has {decimal(round(m['energyKcal']['value']), lang)} kcal per 100 g. The score compares peanut butter with similar foods. To see what's been added to a jar, read the ingredients on the pack.")
        return dict(name="pindakaas", title="Hoe scoort pindakaas op Nutri-Score?", heading="Hoe scoort pindakaas <em>op Nutri-Score?</em>", unit="100 g",
                    lead=f"Bij pindakaas zit echt verschil: {n(c['A'])} producten krijgen een A en {n(c['C'])} een C, van de {n(t)}.",
                    short=f"{n(c['A'])} scoren A en {n(c['C'])} scoren C, van de {n(t)}.", excluded="",
                    body=f"Hier helpt vergelijken. Van de {n(extra['hundred'])} producten met 100 in de naam, meestal 100% pinda's, krijgen er {n(extra['hundred_a'])} een A. Een A betekent wel niet dat er weinig energie in zit: het typische product heeft {decimal(round(m['energyKcal']['value']), lang)} kcal per 100 g. De score vergelijkt pindakaas met vergelijkbare producten. Wil je weten wat er in een pot is toegevoegd, lees dan de ingrediënten op de verpakking.")
    if slug == "muesli":
        crunchy, other = extra["crunchy_a_pct"], extra["other_a_pct"]
        assert crunchy < other
        if lang == "en":
            return dict(name="muesli", title="How does muesli score on Nutri-Score?", heading="How does muesli <em>score?</em>", unit="100 g",
                        lead=f"Muesli runs the full scale from A to E. Of {n(t)} products, {n(c['C'])} get a C and {n(c['A'])} get an A.",
                        short=f"The full range: {n(c['C'])} score C and {n(c['A'])} score A, of {n(t)}.", excluded="bars, biscuits, yoghurt and bread rolls",
                        body=f"The name helps a little. Among products with crunchy or krokant in the name, {crunchy}% get an A, against {other}% of the others. That's a pattern, not a rule: some crunchy mueslis still get an A. With a spread this wide, it's worth comparing the actual box. The typical product has {d('sugars')} g of sugar per 100 g.")
        return dict(name="muesli", title="Hoe scoort muesli op Nutri-Score?", heading="Hoe scoort muesli <em>op Nutri-Score?</em>", unit="100 g",
                    lead=f"Muesli gaat van A tot en met E. Van de {n(t)} producten krijgen er {n(c['C'])} een C en {n(c['A'])} een A.",
                    short=f"Het hele bereik: {n(c['C'])} scoren C en {n(c['A'])} scoren A, van de {n(t)}.", excluded="repen, koekjes, yoghurt en broodjes",
                    body=f"De naam zegt een beetje. Van de producten met krokant of crunchy in de naam krijgt {crunchy}% een A, tegenover {other}% van de rest. Dat is een patroon, geen regel: sommige krokante muesli krijgt nog steeds een A. Bij zo'n groot verschil loont het om de doos zelf te vergelijken. Het typische product heeft {d('sugars')} g suiker per 100 g.")
    raise KeyError(slug)


def food_extra(products):
    def match(pattern):
        return [p for p in products if re.search(pattern, p["name"].lower())]
    bio = match(r"bio|lactose")
    hundred = match(r"100")
    crunchy = match(r"krokant|crunchy|croustillant")
    other = [p for p in products if p not in crunchy]
    pct = lambda rows: round(100 * sum(1 for p in rows if p["nutriGrade"] == "a") / len(rows)) if rows else 0
    return {
        "bio_lactose": len(bio),
        "bio_lactose_b": sum(1 for p in bio if p["nutriGrade"] == "b"),
        "hundred": len(hundred),
        "hundred_a": sum(1 for p in hundred if p["nutriGrade"] == "a"),
        "crunchy_a_pct": pct(crunchy),
        "other_a_pct": pct(other),
        "less_sugar_e": sum(1 for p in match(r"minder suiker") if p["nutriGrade"] == "e"),
    }


def food_page(slug, lang, data, copy):
    ui = UI[lang]
    eyebrow = "Food scores" if lang == "en" else "Voedingsscores"
    meaning = ("What's typical" if lang == "en" else "Wat is gebruikelijk")
    try_it = (f'<a href="{path("checker", lang)}">Check your own list</a> to see individual products.'
              if lang == "en" else f'<a href="{path("checker", lang)}">Check je eigen lijst</a> om losse producten te zien.')
    title = f"{copy['title']} — Basket Vitality"
    description = copy["lead"]
    body = f"""{hero(eyebrow, copy['heading'], copy['lead'], f'<p class="reviewed">{REVIEWED[lang]}</p>')}
{section(score_table(lang, data) + f'''
          <p>{copy['body']}</p>
          <p>{try_it}</p>''')}
{section(f'''          <h2>{meaning}</h2>
{values(lang, data, copy['unit'])}
{method_note(lang, copy['excluded'])}''', tint=True)}
{cta(lang, 'One food is the easy part. <em>Your receipt shows the whole shop.</em>' if lang == 'en' else 'Eén product is het makkelijke deel. <em>Je kassabon laat de hele boodschappen zien.</em>',
     'Scan a grocery receipt to see what it cost against your budget and what it scored. Scanning is free, with no account.' if lang == 'en' else 'Scan een kassabon en zie wat het kostte ten opzichte van je budget en hoe het scoorde. Scannen is gratis, zonder account.')}"""
    return page(slug, lang, title, description, body)


def scores_index(lang, entries):
    cards = "\n".join(
        f'            <li><a href="{path(slug, lang)}"><h3>{copy["name"][:1].upper() + copy["name"][1:]}</h3><p>{copy["short"]}</p></a></li>'
        for slug, copy in entries)
    if lang == "en":
        top = hero("Food scores", "How does your breakfast <em>score?</em>",
                   "Five everyday foods, every product with a Nutri-Score counted. Some foods hardly vary, and some vary a lot.",
                   f'<p class="reviewed">{REVIEWED[lang]}</p>')
        foot = f'Figures come from Open Food Facts data. <a href="{path("methodology", lang)}">See how we count</a>, or <a href="{path("checker", lang)}">check your own list</a>.'
        title, description = "Food scores: how everyday foods do on Nutri-Score — Basket Vitality", "How hagelslag, milk, oats, peanut butter and muesli score on Nutri-Score, counted across every product with a score."
    else:
        top = hero("Voedingsscores", "Hoe scoort je ontbijt <em>op Nutri-Score?</em>",
                   "Vijf dagelijkse producten, met elk product met een Nutri-Score meegeteld. Bij sommige is er nauwelijks verschil, bij andere juist veel.",
                   f'<p class="reviewed">{REVIEWED[lang]}</p>')
        foot = f'De cijfers komen uit gegevens van Open Food Facts. <a href="{path("methodology", lang)}">Bekijk hoe we tellen</a>, of <a href="{path("checker", lang)}">check je eigen lijst</a>.'
        title, description = "Voedingsscores: zo scoren dagelijkse producten op Nutri-Score — Basket Vitality", "Hoe hagelslag, melk, havermout, pindakaas en muesli scoren op Nutri-Score, geteld over alle producten met een score."
    body = f"""{top}
      <section>
        <div class="wrap">
          <ul class="card-grid">
{cards}
          </ul>
          <p>{foot}</p>
        </div>
      </section>"""
    return page("scores", lang, title, description, body)


# ---- Methodology -----------------------------------------------------------

def methodology(lang, stats):
    n = lambda v: number(v, lang)
    pct = decimal(round(100 * stats["seed_graded"] / stats["seed_rows"], 1), lang)
    if lang == "en":
        title, description = "How the scores work: methods and sources — Basket Vitality", "Where Basket Vitality's scores and product data come from, how complete they are, and how the licences work."
        top = hero("Methodology", "Where the scores <em>come from.</em>", "We don't invent a score of our own. We use public methods and open data, and we say what's missing.", f'<p class="reviewed">{REVIEWED[lang]}</p>')
        content = f"""          <h2>The scores</h2>
          <ul>
            <li><strong>Nutri-Score</strong> rates a food's nutritional composition from A to E, for comparing similar products. It's the Dutch government's chosen food-choice label. See <a href="https://www.rijksoverheid.nl/themas/klimaat-milieu-en-natuur/voeding/voedselkeuzelogo-nutri-score">Rijksoverheid</a> and <a href="https://www.rivm.nl/voeding/onze-voedselomgeving/nutri-score">RIVM</a>.</li>
            <li><strong>Eco-Score</strong>, now shown as Green-Score on Open Food Facts, estimates a product's environmental impact. We show it where Open Food Facts has it.</li>
            <li><strong>NOVA</strong> groups foods from 1 to 4 by how processed they are. See the <a href="https://www.fao.org/3/ca5644en/ca5644en.pdf">FAO report on ultra-processed foods</a>.</li>
            <li><strong>CO₂e per kilo</strong> appears on a receipt line where <a href="https://agribalyse.ademe.fr/">AGRIBALYSE</a> has a figure for that food.</li>
          </ul>
          <h2>How the app finds a score</h2>
          <p>For each product, the app uses the first of these that's available:</p>
          <ol>
            <li>The Nutri-Score on the product's Open Food Facts record.</li>
            <li>A Nutri-Score calculated on your phone from the product's nutrition table.</li>
            <li>The score of a similar generic food from the <a href="https://nevo-online.rivm.nl/">NEVO</a> table.</li>
          </ol>
          <p>The website's checker and food pages only use the first. The app can therefore score products they can't.</p>
          <h2>How complete the data is</h2>
          <p>The database in the current app holds {n(stats['seed_rows'])} products from Open Food Facts. {n(stats['seed_graded'])} of them ({pct}%) have a Nutri-Score, so many products have none yet. When that happens, we say so instead of guessing.</p>
          <p>Volunteers add these records, so mistakes happen. The checker warns about {n(stats['flag2'])} of its {n(stats['products'])} products because their numbers look inconsistent, for example more saturated fat than fat. That check can't catch everything. If you spot an error, you can correct it on <a href="https://world.openfoodfacts.org">Open Food Facts</a>.</p>
          <h2>Data and licences</h2>
          <ul>
            <li><strong>Open Food Facts:</strong> product data © Open Food Facts contributors, Open Database License (ODbL) v1.0.</li>
            <li><strong>NEVO:</strong> based on data from NEVO online version 2025/9.0, RIVM, Bilthoven and other data sources.</li>
            <li><strong>AGRIBALYSE:</strong> environmental data, AGRIBALYSE® (ADEME), CC-BY 4.0.</li>
          </ul>
          <p>The checker's product list is available under the same licence: <a href="{INDEX_FILE}">download the data</a> (JSON), read the <a href="/data/LICENSE.txt">licence notice</a>, or see the <a href="https://github.com/The-Dev-Spot/basketvitality-website/blob/main/scripts/build_index.py">script that builds it</a>. The app's full product database and the script that cuts it are in our <a href="https://github.com/The-Dev-Spot/basketvitality-seed">public seed repository</a>.</p>
          <h2>Privacy</h2>
          <p>Receipt scanning and scoring happen on your phone, and your receipts never leave it. What does go out: the product-database download, product pictures, an anonymous barcode lookup to Open Food Facts, and Google Play for subscriptions and ratings. The website's checker works in your browser. Read the <a href="/privacy/">privacy policy</a>.</p>
          <h2>Not a medical app</h2>
          <p>{DISCLAIMER['en']}</p>"""
    else:
        title, description = "Hoe de scores werken: methode en bronnen — Basket Vitality", "Waar de scores en productgegevens van Basket Vitality vandaan komen, hoe volledig ze zijn en hoe de licenties werken."
        top = hero("Methode", "Waar de scores <em>vandaan komen.</em>", "We verzinnen geen eigen score. We gebruiken openbare methodes en open data, en we zeggen wat er ontbreekt.", f'<p class="reviewed">{REVIEWED[lang]}</p>')
        content = f"""          <h2>De scores</h2>
          <ul>
            <li><strong>Nutri-Score</strong> beoordeelt de voedingskundige samenstelling van een product van A tot E, om vergelijkbare producten te vergelijken. Het is het voedselkeuzelogo dat de Nederlandse overheid heeft gekozen. Zie <a href="https://www.rijksoverheid.nl/themas/klimaat-milieu-en-natuur/voeding/voedselkeuzelogo-nutri-score">Rijksoverheid</a> en <a href="https://www.rivm.nl/voeding/onze-voedselomgeving/nutri-score">RIVM</a>.</li>
            <li><strong>Eco-Score</strong>, op Open Food Facts nu Green-Score, schat de milieu-impact van een product. We tonen die waar Open Food Facts hem heeft.</li>
            <li><strong>NOVA</strong> deelt voedsel in van 1 tot 4 naar hoe bewerkt het is. Zie het <a href="https://www.fao.org/3/ca5644en/ca5644en.pdf">FAO-rapport over ultrabewerkt voedsel</a> (Engels).</li>
            <li><strong>CO₂e per kilo</strong> verschijnt bij een regel op de kassabon als <a href="https://agribalyse.ademe.fr/">AGRIBALYSE</a> een cijfer voor dat voedingsmiddel heeft.</li>
          </ul>
          <h2>Hoe de app een score vindt</h2>
          <p>Voor elk product gebruikt de app de eerste van deze drie die beschikbaar is:</p>
          <ol>
            <li>De Nutri-Score op het record van het product bij Open Food Facts.</li>
            <li>Een Nutri-Score die op je telefoon wordt berekend uit de voedingswaardetabel van het product.</li>
            <li>De score van een vergelijkbaar algemeen voedingsmiddel uit de <a href="https://nevo-online.rivm.nl/">NEVO</a>-tabel.</li>
          </ol>
          <p>De checker en voedingspagina's op de website gebruiken alleen de eerste. De app kan dus producten scoren die zij niet kunnen scoren.</p>
          <h2>Hoe volledig de gegevens zijn</h2>
          <p>De database in de huidige app bevat {n(stats['seed_rows'])} producten van Open Food Facts. Daarvan hebben er {n(stats['seed_graded'])} ({pct}%) een Nutri-Score, dus veel producten hebben er nog geen. Dan zeggen we dat, in plaats van te gokken.</p>
          <p>Vrijwilligers voegen deze records toe, dus er gaat weleens iets mis. De checker waarschuwt bij {n(stats['flag2'])} van zijn {n(stats['products'])} producten omdat de cijfers niet lijken te kloppen, bijvoorbeeld meer verzadigd vet dan vet. Die controle vangt niet alles. Zie je een fout, dan kun je die verbeteren op <a href="https://world.openfoodfacts.org">Open Food Facts</a>.</p>
          <h2>Gegevens en licenties</h2>
          <ul>
            <li><strong>Open Food Facts:</strong> productgegevens © Open Food Facts-bijdragers, Open Database License (ODbL) v1.0.</li>
            <li><strong>NEVO:</strong> based on data from NEVO online version 2025/9.0, RIVM, Bilthoven and other data sources.</li>
            <li><strong>AGRIBALYSE:</strong> milieugegevens, AGRIBALYSE® (ADEME), CC-BY 4.0.</li>
          </ul>
          <p>De productlijst van de checker is beschikbaar onder dezelfde licentie: <a href="{INDEX_FILE}">download de gegevens</a> (JSON), lees de <a href="/data/LICENSE.txt">licentietekst</a> (Engels), of bekijk het <a href="https://github.com/The-Dev-Spot/basketvitality-website/blob/main/scripts/build_index.py">script dat de lijst bouwt</a>. De volledige productdatabase van de app en het script dat die maakt staan in onze <a href="https://github.com/The-Dev-Spot/basketvitality-seed">openbare seed-repository</a> (Engels).</p>
          <h2>Privacy</h2>
          <p>Kassabonnen scannen en scoren gebeurt op je telefoon, en je bonnen verlaten die nooit. Wat wél naar buiten gaat: de productdatabase, productfoto's, anonieme barcodes naar Open Food Facts, en Google Play voor abonnementen en beoordelingen. De checker op de website werkt in je browser. Lees het <a href="/privacy/">privacybeleid</a> (Engels).</p>
          <h2>Geen medische app</h2>
          <p>{DISCLAIMER['nl']}</p>"""
    return page("methodology", lang, title, description, f"{top}\n{section(content)}")


# ---- Receipt scanning ------------------------------------------------------

def receipt(lang):
    if lang == "en":
        title, description = "Scan your grocery receipt: what it cost and how it scored — Basket Vitality", "Scan a grocery receipt on your phone to see your budget, Nutri-Scores and a few useful swaps. How it works, and how it differs from cashback apps."
        top = hero("Receipt scanning", "One photo of your receipt. <em>The whole shop, explained.</em>",
                   "Basket Vitality reads your grocery receipt on your phone and shows what it cost against your budget and what it scored on Nutri-Score.",
                   f'<a class="btn" href="{PLAY}">{UI[lang]["get"]}</a><p class="availability">{UI[lang]["availability"]}</p>')
        how = """          <h2>How it works</h2>
          <ol>
            <li><strong>Take a photo.</strong> No account and no typing.</li>
            <li><strong>Your phone reads it.</strong> Text recognition happens on the device, and the receipt stays there.</li>
            <li><strong>Each line is matched</strong> against a built-in database of more than 70,000 grocery products. A wrong match takes one tap to fix.</li>
            <li><strong>You see the result:</strong> your budget, how much of the shop scored Nutri-D or worse, and the few swaps worth making.</li>
          </ol>"""
        compare = f"""          <h2>How is this different from a cashback app?</h2>
          <p>Cashback apps pay you back for what you already bought. Basket Vitality doesn't pay you. It helps you see what to change next time. They do different jobs, so you can use both.</p>
          <div class="table-scroll"><table class="compare">
            <thead><tr><th scope="col"></th><th scope="col">Cashback apps</th><th scope="col">Basket Vitality</th></tr></thead>
            <tbody>
              <tr><th scope="row">What you get</th><td>Money back on selected offers</td><td>What the shop cost and how it scored, line by line</td></tr>
              <tr><th scope="row">Which products</th><td>The ones on offer</td><td>Every line it can recognise</td></tr>
              <tr><th scope="row">The cost</th><td>Free, and they pay you</td><td>Scanning is free. Pro costs €6,99 a month or €49,99 a year</td></tr>
              <tr><th scope="row">Your receipt</th><td>Check each app's privacy terms</td><td>Stays on your phone, with no account</td></tr>
            </tbody>
          </table></div>"""
        faq = """          <h2>Common questions</h2>
          <h3>Is it free?</h3>
          <p>Receipt and barcode scanning are free and unlimited. Free also includes the top two swaps for each shop, one budget category, the last seven days of history and one bank-statement import. Pro adds every budget category, your full history, every swap and unlimited statement imports, with a 14-day free trial for new subscribers.</p>
          <h3>Which receipts does it read?</h3>
          <p>It's built for Dutch supermarket receipts and sold on Google Play in the Netherlands and Belgium.</p>
          <h3>What if it doesn't recognise a line?</h3>
          <p>It says so instead of guessing, and you can fix the match yourself. Product data comes from Open Food Facts and RIVM's NEVO table, and neither is complete.</p>
          <h3>Does my receipt get uploaded?</h3>
          <p>No. Your receipts stay in an encrypted database on your phone. <a href="/privacy/">Read exactly what does go out</a>.</p>"""
        final = cta(lang, "Your shopping already told you this. <em>See it.</em>", "One photo of one receipt is enough to try it.")
    else:
        title, description = "Kassabon scannen: wat het kostte en hoe het scoorde — Basket Vitality", "Scan je kassabon op je telefoon en zie je budget, Nutri-Scores en een paar nuttige swaps. Hoe het werkt, en het verschil met cashback-apps."
        top = hero("Kassabon scannen", "Eén foto van je kassabon. <em>De hele boodschappen uitgelegd.</em>",
                   "Basket Vitality leest je kassabon op je telefoon en laat zien wat het kostte ten opzichte van je budget en hoe het scoorde op Nutri-Score.",
                   f'<a class="btn" href="{PLAY}">{UI[lang]["get"]}</a><p class="availability">{UI[lang]["availability"]}</p>')
        how = """          <h2>Zo werkt het</h2>
          <ol>
            <li><strong>Maak een foto.</strong> Geen account en geen getyp.</li>
            <li><strong>Je telefoon leest de bon.</strong> Tekstherkenning gebeurt op het toestel, en de bon blijft daar.</li>
            <li><strong>Elke regel wordt gekoppeld</strong> aan een ingebouwde database van meer dan 70.000 producten. Een verkeerde koppeling verbeter je met één tik.</li>
            <li><strong>Je ziet het resultaat:</strong> je budget, hoeveel van je boodschappen Nutri-D of slechter scoorde, en de paar swaps die de moeite waard zijn.</li>
          </ol>"""
        compare = f"""          <h2>Wat is het verschil met een cashback-app?</h2>
          <p>Cashback-apps betalen je terug voor wat je al hebt gekocht. Basket Vitality betaalt je niet, maar helpt je zien wat je de volgende keer kunt veranderen. Ze doen iets anders, dus je kunt ze allebei gebruiken.</p>
          <div class="table-scroll"><table class="compare">
            <thead><tr><th scope="col"></th><th scope="col">Cashback-apps</th><th scope="col">Basket Vitality</th></tr></thead>
            <tbody>
              <tr><th scope="row">Wat je krijgt</th><td>Geld terug op bepaalde aanbiedingen</td><td>Wat de boodschappen kostten en hoe ze scoorden, regel voor regel</td></tr>
              <tr><th scope="row">Welke producten</th><td>De producten in de aanbieding</td><td>Elke regel die de app herkent</td></tr>
              <tr><th scope="row">De kosten</th><td>Gratis, en jij krijgt geld</td><td>Scannen is gratis. Pro kost €6,99 per maand of €49,99 per jaar</td></tr>
              <tr><th scope="row">Je kassabon</th><td>Bekijk de privacyvoorwaarden per app</td><td>Blijft op je telefoon, zonder account</td></tr>
            </tbody>
          </table></div>"""
        faq = """          <h2>Veelgestelde vragen</h2>
          <h3>Is het gratis?</h3>
          <p>Kassabonnen en barcodes scannen is gratis en onbeperkt. Gratis zijn ook de twee beste swaps per boodschappenronde, één budgetcategorie, de laatste zeven dagen geschiedenis en één import van een bankafschrift. Pro voegt alle budgetcategorieën, je volledige geschiedenis, elke swap en onbeperkt afschriften importeren toe, met 14 dagen gratis proberen voor nieuwe abonnees.</p>
          <h3>Welke kassabonnen leest de app?</h3>
          <p>De app is gemaakt voor kassabonnen van Nederlandse supermarkten en te koop op Google Play in Nederland en België.</p>
          <h3>Wat als de app een regel niet herkent?</h3>
          <p>Dan zegt de app dat, in plaats van te gokken, en kun je de koppeling zelf verbeteren. Productgegevens komen van Open Food Facts en de NEVO-tabel van het RIVM, en geen van beide is compleet.</p>
          <h3>Wordt mijn kassabon geüpload?</h3>
          <p>Nee. Je kassabonnen staan in een versleutelde database op je telefoon. <a href="/privacy/">Lees precies wat er wel naar buiten gaat</a> (Engels).</p>"""
        final = cta(lang, "Je boodschappen vertelden je dit al. <em>Bekijk het zelf.</em>", "Eén foto van één kassabon is genoeg om het te proberen.")
    return page("receipt", lang, title, description, "\n".join([top, section(how), section(compare, tint=True), section(faq), final]))


# ---- Professionals ---------------------------------------------------------

def professionals(lang):
    mail_en = "mailto:feedback@basketvitality.com?subject=Basket%20Vitality%20for%20professionals"
    mail_nl = "mailto:feedback@basketvitality.com?subject=Basket%20Vitality%20voor%20professionals"
    if lang == "en":
        title, description = "For dietitians and coaches: Basket Vitality and your clients", "How dietitians and budget coaches can use Basket Vitality with clients: real grocery receipts, Nutri-Scores and budgets, with data that stays on the client's phone."
        top = hero("For dietitians and coaches", "Start from what your client <em>actually bought.</em>",
                   "Basket Vitality turns a grocery receipt into a budget and a Nutri-Score overview on your client's own phone. That gives you something real to talk about.")
        content = f"""          <h2>How it can fit your work</h2>
          <ul>
            <li><strong>Dietitians:</strong> your client scans a week's receipts, and you look at the shop together in the session.</li>
            <li><strong>Budget coaches:</strong> grocery spending appears line by line, not as one bank entry called "Supermarket".</li>
            <li><strong>Swaps, not lectures:</strong> the app suggests a few changes on the same shelf. It has no streaks, no shame and no daily reminders.</li>
          </ul>
          <h2>What you should know first</h2>
          <ul>
            <li><strong>Privacy:</strong> there's no account or dashboard, and nothing reaches you or us. Your client decides what to show you on their own phone.</li>
            <li><strong>Limits:</strong> it runs on Android, in the Netherlands and Belgium. Product data is incomplete, and some lines won't get a score. <a href="{path('methodology', lang)}">See how the scores work</a>.</li>
            <li><strong>Use your judgement:</strong> a score on every shop may not suit every client, including anyone with a history of disordered eating.</li>
          </ul>
          <h2>Not a medical app</h2>
          <p>{DISCLAIMER['en']}</p>
          <h2>Talk to us</h2>
          <p>Scanning is free, so you can try it now. If you'd like to use it with clients, or Pro access would help, email us and tell us about your practice. We especially want to hear what's missing.</p>
          <p><a class="btn" href="{mail_en}">Email feedback@basketvitality.com</a></p>"""
    else:
        title, description = "Voor diëtisten en coaches: Basket Vitality en je cliënten", "Hoe diëtisten en budgetcoaches Basket Vitality met cliënten kunnen gebruiken: echte kassabonnen, Nutri-Scores en budgetten, met gegevens die op de telefoon van de cliënt blijven."
        top = hero("Voor diëtisten en coaches", "Begin bij wat je cliënt <em>echt heeft gekocht.</em>",
                   "Basket Vitality maakt van een kassabon een budget- en Nutri-Score-overzicht op de eigen telefoon van je cliënt. Dan heb je iets echts om over te praten.")
        content = f"""          <h2>Hoe het in je werk past</h2>
          <ul>
            <li><strong>Diëtisten:</strong> je cliënt scant de kassabonnen van een week, en jullie bekijken de boodschappen samen tijdens het consult.</li>
            <li><strong>Budgetcoaches:</strong> boodschappen staan regel voor regel in beeld, niet als één bankregel "Supermarkt".</li>
            <li><strong>Swaps, geen preek:</strong> de app stelt een paar wijzigingen voor uit hetzelfde schap. Geen streaks, geen schuldgevoel en geen dagelijkse herinneringen.</li>
          </ul>
          <h2>Wat je vooraf moet weten</h2>
          <ul>
            <li><strong>Privacy:</strong> er is geen account of dashboard, en er komt niets bij jou of bij ons terecht. Je cliënt bepaalt zelf wat hij of zij je op de eigen telefoon laat zien.</li>
            <li><strong>Beperkingen:</strong> de app werkt op Android, in Nederland en België. Productgegevens zijn niet compleet, en sommige regels krijgen geen score. <a href="{path('methodology', lang)}">Bekijk hoe de scores werken</a>.</li>
            <li><strong>Gebruik je eigen oordeel:</strong> een score bij elke boodschappenronde past niet bij iedere cliënt, onder wie mensen met een eetstoornis in de voorgeschiedenis.</li>
          </ul>
          <h2>Geen medische app</h2>
          <p>{DISCLAIMER['nl']}</p>
          <h2>Praat met ons</h2>
          <p>Scannen is gratis, dus je kunt het nu proberen. Wil je het met cliënten gebruiken, of zou Pro-toegang helpen, mail ons dan en vertel over je praktijk. We horen vooral graag wat er ontbreekt.</p>
          <p><a class="btn" href="{mail_nl}">Mail feedback@basketvitality.com</a></p>"""
    return page("professionals", lang, title, description, f"{top}\n{section(content)}")


# ---- Output ----------------------------------------------------------------

def write(url_path, html):
    target = ROOT / url_path.lstrip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def write_sitemap():
    entries = [("/", "monthly", "1.0"), ("/nl/", "monthly", "1.0"), ("/privacy/", "yearly", "0.3"),
               ("/roadmap/", "monthly", "0.7"), ("/nl/roadmap/", "monthly", "0.7")]
    priorities = {"checker": "0.9", "receipt": "0.9", "scores": "0.8", "methodology": "0.5", "professionals": "0.5"}
    for key, pair in PATHS.items():
        for url in pair:
            entries.append((url, "monthly", priorities.get(key, "0.7")))
    body = "\n".join(
        f"  <url>\n    <loc>{BASE}{url}</loc>\n    <changefreq>{freq}</changefreq>\n    <priority>{priority}</priority>\n  </url>"
        for url, freq, priority in entries)
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n', encoding="utf-8")


def main():
    rows, graded = load(sys.argv[1])
    index = json.loads((ROOT / INDEX_FILE.lstrip("/")).read_text(encoding="utf-8"))["products"]
    stats = {"seed_rows": len(rows), "seed_graded": len(graded), "products": len(index),
             "flag2": sum(1 for row in index if row[5] == 2)}
    for lang in ("en", "nl"):
        write(path("checker", lang), checker_page(lang, stats))
        entries = []
        for slug, group in GROUPS.items():
            products = members(graded, group)
            data = figures(products)
            copy = food_copy(slug, lang, data, food_extra(products))
            write(path(slug, lang), food_page(slug, lang, data, copy))
            entries.append((slug, copy))
        write(path("scores", lang), scores_index(lang, entries))
        write(path("methodology", lang), methodology(lang, stats))
        write(path("receipt", lang), receipt(lang))
        write(path("professionals", lang), professionals(lang))
    write_sitemap()
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
