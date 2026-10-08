"""Free news feeds Beranda knows about, and how it picks some for you.

Only headlines are shown, with the name of the medium: this is what RSS feeds are published
for. Every address is checked by a weekly job (scripts/check_feeds.py); a feed that stops
working shows up there and is fixed or removed.

scope: "world" (international news), "national" (a country's own media), "region"
(a continent). countries: ISO codes the medium is "home" for. lang: language of the titles.
"""

from __future__ import annotations

from urllib.parse import quote

S = dict  # short alias for readability below

SOURCES: tuple[dict, ...] = (
    # ---------------------------------------------------------------- international ---
    S(id="bbc-world", name="BBC News World", lang="en", scope="world", url="https://feeds.bbci.co.uk/news/world/rss.xml"),
    S(id="aljazeera-en", name="Al Jazeera English", lang="en", scope="world", url="https://www.aljazeera.com/xml/rss/all.xml"),
    S(id="guardian-world", name="The Guardian World", lang="en", scope="world", url="https://www.theguardian.com/world/rss"),
    S(id="dw-en", name="DW English", lang="en", scope="world", url="https://rss.dw.com/xml/rss-en-all"),
    S(id="un-news-en", name="UN News", lang="en", scope="world", url="https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
    S(id="france24-fr", name="France 24", lang="fr", scope="world", url="https://www.france24.com/fr/rss"),
    S(id="rfi-fr", name="RFI", lang="fr", scope="world", url="https://www.rfi.fr/fr/rss"),
    S(id="un-news-fr", name="ONU Info", lang="fr", scope="world", url="https://news.un.org/feed/subscribe/fr/news/all/rss.xml"),
    S(id="dw-de", name="DW Deutsch", lang="de", scope="world", url="https://rss.dw.com/xml/rss-de-all"),
    S(id="bbc-mundo", name="BBC News Mundo", lang="es", scope="world", url="https://feeds.bbci.co.uk/mundo/rss.xml"),
    S(id="dw-es", name="DW Español", lang="es", scope="world", url="https://rss.dw.com/xml/rss-sp-all"),
    S(id="france24-es", name="France 24 Español", lang="es", scope="world", url="https://www.france24.com/es/rss"),
    S(id="un-news-es", name="Noticias ONU", lang="es", scope="world", url="https://news.un.org/feed/subscribe/es/news/all/rss.xml"),
    S(id="ansa-mondo", name="ANSA Mondo", lang="it", scope="world", url="https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml"),
    S(id="bbc-brasil", name="BBC News Brasil", lang="pt", scope="world", url="https://feeds.bbci.co.uk/portuguese/rss.xml"),
    S(id="dw-br", name="DW Brasil", lang="pt", scope="world", url="https://rss.dw.com/xml/rss-br-all"),
    S(id="un-news-pt", name="ONU News", lang="pt", scope="world", url="https://news.un.org/feed/subscribe/pt/news/all/rss.xml"),
    S(id="bbc-arabic", name="BBC عربي", lang="ar", scope="world", url="https://feeds.bbci.co.uk/arabic/rss.xml"),
    S(id="france24-ar", name="فرانس 24", lang="ar", scope="world", url="https://www.france24.com/ar/rss"),
    S(id="dw-ar", name="DW عربية", lang="ar", scope="world", url="https://rss.dw.com/xml/rss-ar-all"),
    S(id="un-news-ar", name="أخبار الأمم المتحدة", lang="ar", scope="world", url="https://news.un.org/feed/subscribe/ar/news/all/rss.xml"),
    S(id="bbc-swahili", name="BBC News Swahili", lang="sw", scope="world", url="https://feeds.bbci.co.uk/swahili/rss.xml"),
    S(id="dw-sw", name="DW Kiswahili", lang="sw", scope="world", url="https://rss.dw.com/xml/rss-sw-all"),
    S(id="bbc-amharic", name="BBC News አማርኛ", lang="am", scope="world", url="https://feeds.bbci.co.uk/amharic/rss.xml"),
    S(id="dw-am", name="DW አማርኛ", lang="am", scope="world", url="https://rss.dw.com/xml/rss-amh-all"),
    S(id="bbc-indonesia", name="BBC News Indonesia", lang="id", scope="world", url="https://feeds.bbci.co.uk/indonesia/rss.xml"),
    S(id="dw-id", name="DW Indonesia", lang="id", scope="world", url="https://rss.dw.com/xml/rss-id-all"),
    S(id="bbc-japanese", name="BBC News Japan", lang="ja", scope="world", url="https://feeds.bbci.co.uk/japanese/rss.xml"),
    # ---------------------------------------------------------------- continents -------
    S(id="bbc-africa", name="BBC News Africa", lang="en", scope="region", region="africa", url="https://feeds.bbci.co.uk/news/world/africa/rss.xml"),
    S(id="allafrica-en", name="AllAfrica", lang="en", scope="region", region="africa", url="https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"),
    S(id="allafrica-fr", name="AllAfrica (français)", lang="fr", scope="region", region="africa", url="https://fr.allafrica.com/tools/headlines/rdf/latest/headlines.rdf"),
    S(id="rfi-afrique", name="RFI Afrique", lang="fr", scope="region", region="africa", url="https://www.rfi.fr/fr/afrique/rss"),
    S(id="bbc-afrique", name="BBC Afrique", lang="fr", scope="region", region="africa", url="https://feeds.bbci.co.uk/afrique/rss.xml"),
    S(id="jeune-afrique", name="Jeune Afrique", lang="fr", scope="region", region="africa", url="https://www.jeuneafrique.com/feed/"),
    S(id="africa-report", name="The Africa Report", lang="en", scope="region", region="africa", url="https://www.theafricareport.com/feed/"),
    S(id="bbc-latam", name="BBC News Latin America", lang="en", scope="region", region="latam", url="https://feeds.bbci.co.uk/news/world/latin_america/rss.xml"),
    # ---------------------------------------------------------------- Europe -----------
    S(id="franceinfo", name="franceinfo", lang="fr", scope="national", countries=("FR",), url="https://www.francetvinfo.fr/titres.rss"),
    S(id="lemonde", name="Le Monde", lang="fr", scope="national", countries=("FR",), url="https://www.lemonde.fr/rss/une.xml"),
    S(id="tagesschau", name="tagesschau", lang="de", scope="national", countries=("DE",), url="https://www.tagesschau.de/xml/rss2/"),
    S(id="spiegel", name="DER SPIEGEL", lang="de", scope="national", countries=("DE",), url="https://www.spiegel.de/schlagzeilen/index.rss"),
    S(id="zeit", name="ZEIT ONLINE", lang="de", scope="national", countries=("DE",), url="https://newsfeed.zeit.de/index"),
    S(id="orf", name="ORF.at", lang="de", scope="national", countries=("AT",), url="https://rss.orf.at/news.xml"),
    S(id="srf", name="SRF News", lang="de", scope="national", countries=("CH",), url="https://www.srf.ch/news/bnf/rss/1646"),
    S(id="rtve", name="RTVE Noticias", lang="es", scope="national", countries=("ES",), url="https://api2.rtve.es/rss/temas_noticias.xml"),
    S(id="elpais", name="EL PAÍS", lang="es", scope="national", countries=("ES",), url="https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"),
    S(id="20minutos", name="20minutos", lang="es", scope="national", countries=("ES",), url="https://www.20minutos.es/rss/"),
    S(id="ansa", name="ANSA", lang="it", scope="national", countries=("IT",), url="https://www.ansa.it/sito/ansait_rss.xml"),
    S(id="ilpost", name="Il Post", lang="it", scope="national", countries=("IT",), url="https://www.ilpost.it/feed/"),
    S(id="repubblica", name="la Repubblica", lang="it", scope="national", countries=("IT",), url="https://www.repubblica.it/rss/homepage/rss2.0.xml"),
    S(id="rtp", name="RTP Notícias", lang="pt", scope="national", countries=("PT",), url="https://www.rtp.pt/noticias/rss"),
    S(id="publico", name="Público", lang="pt", scope="national", countries=("PT",), url="https://feeds.feedburner.com/PublicoRSS"),
    S(id="observador", name="Observador", lang="pt", scope="national", countries=("PT",), url="https://observador.pt/feed/"),
    S(id="bbc-uk", name="BBC News UK", lang="en", scope="national", countries=("GB",), url="https://feeds.bbci.co.uk/news/uk/rss.xml"),
    S(id="guardian-uk", name="The Guardian UK", lang="en", scope="national", countries=("GB",), url="https://www.theguardian.com/uk-news/rss"),
    # ---------------------------------------------------------------- Americas ---------
    S(id="npr", name="NPR News", lang="en", scope="national", countries=("US",), url="https://feeds.npr.org/1001/rss.xml"),
    S(id="cbc", name="CBC News", lang="en", scope="national", countries=("CA",), url="https://www.cbc.ca/webfeed/rss/rss-topstories"),
    S(id="radio-canada", name="Radio-Canada Info", lang="fr", scope="national", countries=("CA",), url="https://ici.radio-canada.ca/rss/4159"),
    S(id="g1", name="g1", lang="pt", scope="national", countries=("BR",), url="https://g1.globo.com/rss/g1/"),
    S(id="agencia-brasil", name="Agência Brasil", lang="pt", scope="national", countries=("BR",), url="https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml"),
    S(id="folha", name="Folha de S.Paulo", lang="pt", scope="national", countries=("BR",), url="https://feeds.folha.uol.com.br/emcimadahora/rss091.xml"),
    S(id="la-jornada", name="La Jornada", lang="es", scope="national", countries=("MX",), url="https://www.jornada.com.mx/rss/edicion.xml"),
    S(id="clarin", name="Clarín", lang="es", scope="national", countries=("AR",), url="https://www.clarin.com/rss/lo-ultimo/"),
    S(id="pagina12", name="Página/12", lang="es", scope="national", countries=("AR",), url="https://www.pagina12.com.ar/rss/portada"),
    S(id="eltiempo", name="EL TIEMPO", lang="es", scope="national", countries=("CO",), url="https://www.eltiempo.com/rss/colombia.xml"),
    S(id="latercera", name="La Tercera", lang="es", scope="national", countries=("CL",), url="https://www.latercera.com/arc/outboundfeeds/rss/?outputType=xml"),
    S(id="elcomercio-pe", name="El Comercio", lang="es", scope="national", countries=("PE",), url="https://elcomercio.pe/arcio/rss/"),
    # ---------------------------------------------------------------- Africa -----------
    S(id="news24", name="News24", lang="en", scope="national", countries=("ZA",), url="https://feeds.news24.com/articles/news24/TopStories/rss"),
    S(id="daily-maverick", name="Daily Maverick", lang="en", scope="national", countries=("ZA",), url="https://www.dailymaverick.co.za/dmrss/"),
    S(id="maroela", name="Maroela Media", lang="af", scope="national", countries=("ZA", "NA"), url="https://maroelamedia.co.za/feed/"),
    S(id="premium-times", name="Premium Times", lang="en", scope="national", countries=("NG",), url="https://www.premiumtimesng.com/feed"),
    S(id="punch", name="Punch", lang="en", scope="national", countries=("NG",), url="https://punchng.com/feed/"),
    S(id="bbc-hausa", name="BBC News Hausa", lang="ha", scope="national", countries=("NG", "NE"), url="https://feeds.bbci.co.uk/hausa/rss.xml"),
    S(id="bbc-yoruba", name="BBC News Yorùbá", lang="yo", scope="national", countries=("NG",), url="https://feeds.bbci.co.uk/yoruba/rss.xml"),
    S(id="nation-ke", name="Nation", lang="en", scope="national", countries=("KE",), url="https://nation.africa/kenya/rss.xml"),
    S(id="addis-standard", name="Addis Standard", lang="en", scope="national", countries=("ET",), url="https://addisstandard.com/feed/"),
    S(id="myjoyonline", name="MyJoyOnline", lang="en", scope="national", countries=("GH",), url="https://www.myjoyonline.com/feed/"),
    S(id="citinewsroom", name="Citi Newsroom", lang="en", scope="national", countries=("GH",), url="https://citinewsroom.com/feed/"),
    S(id="hespress-fr", name="Hespress FR", lang="fr", scope="national", countries=("MA",), url="https://fr.hespress.com/feed"),
    S(id="tsa", name="TSA Algérie", lang="fr", scope="national", countries=("DZ",), url="https://www.tsa-algerie.com/feed/"),
    S(id="journal-du-cameroun", name="Journal du Cameroun", lang="fr", scope="national", countries=("CM",), url="https://www.journalducameroun.com/feed/"),
    S(id="radio-okapi", name="Radio Okapi", lang="fr", scope="national", countries=("CD",), url="https://www.radiookapi.net/rss.xml"),
    S(id="herald-zw", name="The Herald", lang="en", scope="national", countries=("ZW",), url="https://www.herald.co.zw/feed/"),
    # ---------------------------------------------------------------- Asia -------------
    S(id="nhk", name="NHK ニュース", lang="ja", scope="national", countries=("JP",), url="https://www3.nhk.or.jp/rss/news/cat0.xml"),
    S(id="antara", name="ANTARA", lang="id", scope="national", countries=("ID",), url="https://www.antaranews.com/rss/terkini.xml"),
    S(id="tempo", name="Tempo", lang="id", scope="national", countries=("ID",), url="https://rss.tempo.co/"),
)

BY_ID = {s["id"]: s for s in SOURCES}

AFRICA = frozenset({
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD", "KM", "CG", "CD", "CI", "DJ",
    "EG", "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR", "LY", "MG",
    "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST", "SN", "SC", "SL", "SO",
    "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "ZM", "ZW", "EH",
})
LATAM = frozenset({
    "AR", "BO", "BR", "CL", "CO", "CR", "CU", "DO", "EC", "SV", "GT", "HN", "MX", "NI", "PA",
    "PY", "PE", "PR", "UY", "VE", "HT",
})

# GDELT, a free and open index of the world's online press, can list recent articles that
# mention a word. We use it for "news about my town". Language names are GDELT's own.
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_LANG = {
    "en": "english", "fr": "french", "de": "german", "es": "spanish", "it": "italian",
    "pt": "portuguese", "ja": "japanese", "id": "indonesian", "ar": "arabic", "sw": "swahili",
    "am": "amharic", "af": "afrikaans",
}


def city_feed_url(city: str, language: str) -> str:
    """Recent articles mentioning the town, in the display language when GDELT knows it."""
    query = f'"{city}"'
    lang = GDELT_LANG.get(language.split("-")[0])
    if lang:
        query += f" sourcelang:{lang}"
    return (
        f"{GDELT_URL}?query={quote(query)}&mode=artlist&format=rss"
        "&maxrecords=15&sort=datedesc&timespan=3d"
    )


def region_of(country: str) -> str | None:
    return "africa" if country in AFRICA else "latam" if country in LATAM else None


def national(country: str) -> list[dict]:
    return [s for s in SOURCES if country in s.get("countries", ())]


def automatic(country: str, language: str, city: str | None) -> list[str]:
    """What Beranda picks when you let it: your town, your country, the world, your language."""
    base = language.split("-")[0]
    picked: list[str] = ["city"] if city else []
    mine = national(country)
    mine.sort(key=lambda s: s["lang"] != base)  # media in the display language first
    picked += [s["id"] for s in mine[:2]]
    region = region_of(country)
    if len(mine) < 2 and region:
        regional = [s for s in SOURCES if s.get("region") == region]
        regional.sort(key=lambda s: s["lang"] != base)
        picked += [s["id"] for s in regional[: 2 - len(mine)]]
    world = [s for s in SOURCES if s["scope"] == "world" and s["lang"] == base]
    picked.append(world[0]["id"] if world else "bbc-world")
    return picked
