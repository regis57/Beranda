"""Free news feeds Beranda knows about, and how it picks some for you.

Only headlines are shown, with the name of the medium: this is what RSS feeds are published
for. Every address is checked by a weekly job (scripts/check_feeds.py); a feed that stops
working shows up there and is fixed or removed.

scope: "world" (international news), "national" (a country's own media), "region"
(a continent). countries: ISO codes the medium is "home" for. lang: language of the titles.
"""

from __future__ import annotations

from urllib.parse import quote

from . import countries

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
    S(id="un-news-pt", name="ONU News", lang="pt", scope="world", url="https://news.un.org/feed/subscribe/pt/news/all/rss.xml"),
    S(id="bbc-arabic", name="BBC عربي", lang="ar", scope="world", url="https://feeds.bbci.co.uk/arabic/rss.xml"),
    S(id="france24-ar", name="فرانس 24", lang="ar", scope="world", url="https://www.france24.com/ar/rss"),
    S(id="dw-ar", name="DW عربية", lang="ar", scope="world", url="https://rss.dw.com/xml/rss-ar-all"),
    S(id="un-news-ar", name="أخبار الأمم المتحدة", lang="ar", scope="world", url="https://news.un.org/feed/subscribe/ar/news/all/rss.xml"),
    S(id="bbc-swahili", name="BBC News Swahili", lang="sw", scope="world", url="https://feeds.bbci.co.uk/swahili/rss.xml"),
    S(id="bbc-amharic", name="BBC News አማርኛ", lang="am", scope="world", url="https://feeds.bbci.co.uk/amharic/rss.xml"),
    S(id="bbc-indonesia", name="BBC News Indonesia", lang="id", scope="world", url="https://feeds.bbci.co.uk/indonesia/rss.xml"),
    S(id="bbc-japanese", name="BBC News Japan", lang="ja", scope="world", url="https://feeds.bbci.co.uk/japanese/rss.xml"),
    S(id="bbc-chinese", name="BBC 中文", lang="zh", scope="world", url="https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"),
    S(id="bbc-chinese-trad", name="BBC 中文（繁體）", lang="zh-TW", scope="world", url="https://feeds.bbci.co.uk/zhongwen/trad/rss.xml"),
    S(id="dw-zh", name="DW 中文", lang="zh", scope="world", url="https://rss.dw.com/xml/rss-chi-all"),
    S(id="bbc-korean", name="BBC News 코리아", lang="ko", scope="world", url="https://feeds.bbci.co.uk/korean/rss.xml"),
    S(id="bbc-hindi", name="BBC हिंदी", lang="hi", scope="world", url="https://feeds.bbci.co.uk/hindi/rss.xml"),
    S(id="bbc-bengali", name="BBC বাংলা", lang="bn", scope="world", url="https://feeds.bbci.co.uk/bengali/rss.xml"),
    S(id="bbc-urdu", name="BBC اردو", lang="ur", scope="world", url="https://feeds.bbci.co.uk/urdu/rss.xml"),
    S(id="bbc-persian", name="BBC فارسی", lang="fa", scope="world", url="https://feeds.bbci.co.uk/persian/rss.xml"),
    S(id="bbc-turkce", name="BBC News Türkçe", lang="tr", scope="world", url="https://feeds.bbci.co.uk/turkce/rss.xml"),
    S(id="dw-tr", name="DW Türkçe", lang="tr", scope="world", url="https://rss.dw.com/xml/rss-tur-all"),
    S(id="bbc-russian", name="BBC News Русская служба", lang="ru", scope="world", url="https://feeds.bbci.co.uk/russian/rss.xml"),
    S(id="dw-ru", name="DW на русском", lang="ru", scope="world", url="https://rss.dw.com/xml/rss-ru-all"),
    S(id="bbc-ukrainian", name="BBC News Україна", lang="uk", scope="world", url="https://feeds.bbci.co.uk/ukrainian/rss.xml"),
    S(id="dw-uk", name="DW Українська", lang="uk", scope="world", url="https://rss.dw.com/xml/rss-ukr-all"),
    S(id="bbc-vietnamese", name="BBC News Tiếng Việt", lang="vi", scope="world", url="https://feeds.bbci.co.uk/vietnamese/rss.xml"),
    S(id="bbc-thai", name="BBC News ไทย", lang="th", scope="world", url="https://feeds.bbci.co.uk/thai/rss.xml"),
    S(id="bbc-serbian", name="BBC News na srpskom", lang="sr", scope="world", url="https://feeds.bbci.co.uk/serbian/cyr/rss.xml"),
    S(id="dw-pl", name="DW Polski", lang="pl", scope="world", url="https://rss.dw.com/xml/rss-pol-all"),
    S(id="dw-ro", name="DW Română", lang="ro", scope="world", url="https://rss.dw.com/xml/rss-rom-all"),
    S(id="dw-el", name="DW Ελληνικά", lang="el", scope="world", url="https://rss.dw.com/xml/rss-gre-all"),
    S(id="dw-fa", name="DW فارسی", lang="fa", scope="world", url="https://rss.dw.com/xml/rss-per-all"),
    # ---------------------------------------------------------------- continents -------
    S(id="bbc-africa", name="BBC News Africa", lang="en", scope="region", region="africa", url="https://feeds.bbci.co.uk/news/world/africa/rss.xml"),
    S(id="allafrica-en", name="AllAfrica", lang="en", scope="region", region="africa", url="https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"),
    S(id="allafrica-fr", name="AllAfrica (français)", lang="fr", scope="region", region="africa", url="https://fr.allafrica.com/tools/headlines/rdf/latest/headlines.rdf"),
    S(id="rfi-afrique", name="RFI Afrique", lang="fr", scope="region", region="africa", url="https://www.rfi.fr/fr/afrique/rss"),
    S(id="bbc-afrique", name="BBC Afrique", lang="fr", scope="region", region="africa", url="https://feeds.bbci.co.uk/afrique/rss.xml"),
    S(id="jeune-afrique", name="Jeune Afrique", lang="fr", scope="region", region="africa", url="https://www.jeuneafrique.com/feed/"),
    S(id="africa-report", name="The Africa Report", lang="en", scope="region", region="africa", url="https://www.theafricareport.com/feed/"),
    S(id="bbc-latam", name="BBC News Latin America", lang="en", scope="region", region="latam", url="https://feeds.bbci.co.uk/news/world/latin_america/rss.xml"),
    S(id="bbc-europe", name="BBC News Europe", lang="en", scope="region", region="europe", url="https://feeds.bbci.co.uk/news/world/europe/rss.xml"),
    S(id="euronews-en", name="Euronews", lang="en", scope="region", region="europe", url="https://www.euronews.com/rss?format=mrss&level=theme&name=news"),
    S(id="bbc-us-canada", name="BBC News US & Canada", lang="en", scope="region", region="north_america", url="https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
    S(id="bbc-middle-east", name="BBC News Middle East", lang="en", scope="region", region="middle_east", url="https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"),
    S(id="bbc-asia", name="BBC News Asia", lang="en", scope="region", region="asia", url="https://feeds.bbci.co.uk/news/world/asia/rss.xml"),
    S(id="bbc-australia", name="BBC News Australia", lang="en", scope="region", region="oceania", url="https://feeds.bbci.co.uk/news/world/australia/rss.xml"),
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
    S(id="repubblica", name="la Repubblica", lang="it", scope="national", countries=("IT",), url="https://www.repubblica.it/rss/homepage/rss2.0.xml"),
    S(id="rtp", name="RTP Notícias", lang="pt", scope="national", countries=("PT",), url="https://www.rtp.pt/noticias/rss"),
    S(id="publico", name="Público", lang="pt", scope="national", countries=("PT",), url="https://feeds.feedburner.com/PublicoRSS"),
    S(id="observador", name="Observador", lang="pt", scope="national", countries=("PT",), url="https://observador.pt/feed/"),
    S(id="rte", name="RTÉ News", lang="en", scope="national", countries=("IE",), url="https://www.rte.ie/feeds/rss/?index=/news/"),
    S(id="nos", name="NOS Nieuws", lang="nl", scope="national", countries=("NL",), url="https://feeds.nos.nl/nosnieuwsalgemeen"),
    S(id="vrt", name="VRT NWS", lang="nl", scope="national", countries=("BE",), url="https://www.vrt.be/vrtnws/nl.rss.articles.xml"),
    S(id="rtbf", name="RTBF Info", lang="fr", scope="national", countries=("BE",), url="https://rss.rtbf.be/article/rss/highlight_rtbf_info.xml"),
    S(id="rts", name="RTS Info", lang="fr", scope="national", countries=("CH",), url="https://www.rts.ch/info/?format=rss/news"),
    S(id="svt", name="SVT Nyheter", lang="sv", scope="national", countries=("SE",), url="https://www.svt.se/nyheter/rss.xml"),
    S(id="dr", name="DR Nyheder", lang="da", scope="national", countries=("DK",), url="https://www.dr.dk/nyheder/service/feeds/allenyheder"),
    S(id="nrk", name="NRK", lang="nb", scope="national", countries=("NO",), url="https://www.nrk.no/toppsaker.rss"),
    S(id="yle", name="Yle Uutiset", lang="fi", scope="national", countries=("FI",), url="https://yle.fi/rss/uutiset/paauutiset"),
    S(id="tvn24", name="TVN24", lang="pl", scope="national", countries=("PL",), url="https://tvn24.pl/najnowsze.xml"),
    S(id="idnes", name="iDNES.cz", lang="cs", scope="national", countries=("CZ",), url="https://servis.idnes.cz/rss.aspx?c=zpravodaj"),
    S(id="ct24", name="ČT24", lang="cs", scope="national", countries=("CZ",), url="https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"),
    S(id="aktuality", name="Aktuality.sk", lang="sk", scope="national", countries=("SK",), url="https://www.aktuality.sk/rss/"),
    S(id="rtvslo", name="MMC RTV SLO", lang="sl", scope="national", countries=("SI",), url="https://www.rtvslo.si/feeds/00.xml"),
    S(id="index-hr", name="Index.hr", lang="hr", scope="national", countries=("HR", "BA"), url="https://www.index.hr/rss"),
    S(id="n1-rs", name="N1 Srbija", lang="sr", scope="national", countries=("RS", "ME", "BA"), url="https://n1info.rs/feed/"),
    S(id="dnevnik-bg", name="Дневник", lang="bg", scope="national", countries=("BG",), url="https://www.dnevnik.bg/rss/"),
    S(id="digi24", name="Digi24", lang="ro", scope="national", countries=("RO", "MD"), url="https://www.digi24.ro/rss"),
    S(id="ertnews", name="ERTNews", lang="el", scope="national", countries=("GR", "CY"), url="https://www.ertnews.gr/feed/"),
    S(id="lsm", name="LSM", lang="lv", scope="national", countries=("LV",), url="https://www.lsm.lv/rss/"),
    S(id="err", name="ERR", lang="et", scope="national", countries=("EE",), url="https://www.err.ee/rss"),
    S(id="ukrinform", name="Укрінформ", lang="uk", scope="national", countries=("UA",), url="https://www.ukrinform.ua/rss/block-lastnews"),
    S(id="meduza", name="Meduza", lang="ru", scope="national", countries=("RU", "BY", "KZ"), url="https://meduza.io/rss/all"),
    S(id="vilaweb", name="VilaWeb", lang="ca", scope="national", countries=("ES", "AD"), url="https://www.vilaweb.cat/feed/"),
    S(id="bbc-uk", name="BBC News UK", lang="en", scope="national", countries=("GB",), url="https://feeds.bbci.co.uk/news/uk/rss.xml"),
    S(id="guardian-uk", name="The Guardian UK", lang="en", scope="national", countries=("GB",), url="https://www.theguardian.com/uk-news/rss"),
    # ---------------------------------------------------------------- Americas ---------
    S(id="npr", name="NPR News", lang="en", scope="national", countries=("US",), url="https://feeds.npr.org/1001/rss.xml"),
    S(id="pbs", name="PBS NewsHour", lang="en", scope="national", countries=("US",), url="https://www.pbs.org/newshour/feeds/rss/headlines"),
    S(id="global-news", name="Global News", lang="en", scope="national", countries=("CA",), url="https://globalnews.ca/feed/"),
    S(id="radio-canada", name="Radio-Canada Info", lang="fr", scope="national", countries=("CA",), url="https://ici.radio-canada.ca/rss/4159"),
    S(id="g1", name="g1", lang="pt", scope="national", countries=("BR",), url="https://g1.globo.com/rss/g1/"),
    S(id="agencia-brasil", name="Agência Brasil", lang="pt", scope="national", countries=("BR",), url="https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml"),
    S(id="folha", name="Folha de S.Paulo", lang="pt", scope="national", countries=("BR",), url="https://feeds.folha.uol.com.br/emcimadahora/rss091.xml"),
    S(id="la-jornada", name="La Jornada", lang="es", scope="national", countries=("MX",), url="https://www.jornada.com.mx/rss/edicion.xml"),
    S(id="infobae", name="Infobae", lang="es", scope="national", countries=("AR",), url="https://www.infobae.com/arc/outboundfeeds/rss/"),
    S(id="clarin", name="Clarín", lang="es", scope="national", countries=("AR",), url="https://www.clarin.com/rss/lo-ultimo/"),
    S(id="gleaner", name="The Gleaner", lang="en", scope="national", countries=("JM",), url="https://jamaica-gleaner.com/feed/rss.xml"),
    S(id="nouvelliste", name="Le Nouvelliste", lang="fr", scope="national", countries=("HT",), url="https://lenouvelliste.com/rss"),
    S(id="eltiempo", name="EL TIEMPO", lang="es", scope="national", countries=("CO",), url="https://www.eltiempo.com/rss/colombia.xml"),
    S(id="elcomercio-pe", name="El Comercio", lang="es", scope="national", countries=("PE",), url="https://elcomercio.pe/arcio/rss/"),
    # ---------------------------------------------------------------- Africa -----------
    S(id="daily-maverick", name="Daily Maverick", lang="en", scope="national", countries=("ZA",), url="https://www.dailymaverick.co.za/dmrss/"),
    S(id="maroela", name="Maroela Media", lang="af", scope="national", countries=("ZA", "NA"), url="https://maroelamedia.co.za/feed/"),
    S(id="premium-times", name="Premium Times", lang="en", scope="national", countries=("NG",), url="https://www.premiumtimesng.com/feed"),
    S(id="punch", name="Punch", lang="en", scope="national", countries=("NG",), url="https://punchng.com/feed/"),
    S(id="bbc-hausa", name="BBC News Hausa", lang="ha", scope="national", countries=("NG", "NE"), url="https://feeds.bbci.co.uk/hausa/rss.xml"),
    S(id="bbc-yoruba", name="BBC News Yorùbá", lang="yo", scope="national", countries=("NG",), url="https://feeds.bbci.co.uk/yoruba/rss.xml"),
    S(id="myjoyonline", name="MyJoyOnline", lang="en", scope="national", countries=("GH",), url="https://www.myjoyonline.com/feed/"),
    S(id="hespress-fr", name="Hespress FR", lang="fr", scope="national", countries=("MA",), url="https://fr.hespress.com/feed"),
    S(id="tsa", name="TSA Algérie", lang="fr", scope="national", countries=("DZ",), url="https://www.tsa-algerie.com/feed/"),
    S(id="radio-okapi", name="Radio Okapi", lang="fr", scope="national", countries=("CD",), url="https://www.radiookapi.net/rss.xml"),
    # ---------------------------------------------------------------- Asia -------------
    S(id="the-hindu", name="The Hindu", lang="en", scope="national", countries=("IN",), url="https://www.thehindu.com/news/national/feeder/default.rss"),
    S(id="dawn", name="Dawn", lang="en", scope="national", countries=("PK",), url="https://www.dawn.com/feeds/home"),
    S(id="rthk", name="RTHK 香港電台", lang="zh-TW", scope="national", countries=("HK", "MO"), url="https://rthk.hk/rthk/news/rss/c_expressnews_clocal.xml"),
    S(id="yonhap", name="연합뉴스", lang="ko", scope="national", countries=("KR",), url="https://www.yna.co.kr/rss/news.xml"),
    S(id="bangkok-post", name="Bangkok Post", lang="en", scope="national", countries=("TH",), url="https://www.bangkokpost.com/rss/data/topstories.xml"),
    S(id="vnexpress", name="VnExpress", lang="vi", scope="national", countries=("VN",), url="https://vnexpress.net/rss/tin-moi-nhat.rss"),
    S(id="rappler", name="Rappler", lang="en", scope="national", countries=("PH",), url="https://www.rappler.com/feed/"),
    S(id="inquirer", name="Inquirer", lang="en", scope="national", countries=("PH",), url="https://newsinfo.inquirer.net/feed"),
    S(id="cna", name="CNA", lang="en", scope="national", countries=("SG", "MY"), url="https://www.channelnewsasia.com/rssfeeds/8395986"),
    S(id="arab-news", name="Arab News", lang="en", scope="national", countries=("SA",), url="https://www.arabnews.com/rss.xml"),
    S(id="the-national", name="The National", lang="en", scope="national", countries=("AE",), url="https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml"),
    S(id="abc-au", name="ABC News", lang="en", scope="national", countries=("AU",), url="https://www.abc.net.au/news/feed/51120/rss.xml"),
    S(id="guardian-au", name="The Guardian Australia", lang="en", scope="national", countries=("AU",), url="https://www.theguardian.com/australia-news/rss"),
    S(id="nhk", name="NHK ニュース", lang="ja", scope="national", countries=("JP",), url="https://www3.nhk.or.jp/rss/news/cat0.xml"),
    S(id="antara", name="ANTARA", lang="id", scope="national", countries=("ID",), url="https://www.antaranews.com/rss/terkini.xml"),
    S(id="tempo", name="Tempo", lang="id", scope="national", countries=("ID",), url="https://rss.tempo.co/"),
)

BY_ID = {s["id"]: s for s in SOURCES}

AFRICA = frozenset(c for c, r in countries.REGION_OF.items() if r == "africa")
LATAM = frozenset(c for c, r in countries.REGION_OF.items() if r == "latam")

# GDELT, a free and open index of the world's online press, can list recent articles that
# mention a word. We use it for "news about my town". Language names are GDELT's own.
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_LANG = {
    "en": "english", "fr": "french", "de": "german", "es": "spanish", "it": "italian",
    "pt": "portuguese", "ja": "japanese", "id": "indonesian", "ar": "arabic", "sw": "swahili",
    "am": "amharic", "af": "afrikaans", "nl": "dutch", "pl": "polish", "sv": "swedish",
    "da": "danish", "nb": "norwegian", "fi": "finnish", "cs": "czech", "sk": "slovak",
    "sl": "slovenian", "hr": "croatian", "sr": "serbian", "bg": "bulgarian", "ro": "romanian",
    "hu": "hungarian", "el": "greek", "lt": "lithuanian", "lv": "latvian", "et": "estonian",
    "tr": "turkish", "uk": "ukrainian", "ru": "russian", "ca": "catalan", "zh": "chinese",
    "ko": "korean", "hi": "hindi", "bn": "bengali", "ur": "urdu", "th": "thai",
    "vi": "vietnamese", "ms": "malay", "tl": "tagalog", "he": "hebrew", "fa": "persian",
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
    return countries.REGION_OF.get(country)


def national(country: str) -> list[dict]:
    return [s for s in SOURCES if country in s.get("countries", ())]


def automatic(country: str, language: str, city: str | None) -> list[str]:
    """What Beranda picks when you let it: your town, your country, the world, your language."""
    base = language.split("-")[0]
    picked: list[str] = ["city"] if city else []
    mine = national(country)
    mine.sort(key=lambda s: s["lang"].split("-")[0] != base)  # media in the display language first
    picked += [s["id"] for s in mine[:2]]
    region = region_of(country)
    if len(mine) < 2 and region:
        regional = [s for s in SOURCES if s.get("region") == region]
        regional.sort(key=lambda s: s["lang"] != base)
        picked += [s["id"] for s in regional[: 2 - len(mine)]]
    world = [s for s in SOURCES if s["scope"] == "world" and s["lang"] in (language, base)]
    world.sort(key=lambda s: s["lang"] != language)  # zh-TW readers get traditional characters
    picked.append(world[0]["id"] if world else "bbc-world")
    return picked
