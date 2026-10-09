"""Every country Beranda knows about: its region and the display languages that suit it.

The first language listed is the one the settings page suggests when the country is picked;
any of the translated languages can still be chosen anywhere. Languages Beranda does not
speak yet fall back to the closest one people there commonly read (often English or French).
"""

from __future__ import annotations

# Display languages, in the order the settings page lists them.
LANGUAGES = (
    "en", "fr", "de", "es", "it", "pt", "pt-BR", "nl", "ca",
    "da", "sv", "nb", "fi", "pl", "cs", "sk", "sl", "hr", "sr", "bg", "ro", "hu", "el",
    "lt", "lv", "et", "uk", "ru", "tr",
    "ar", "he", "fa", "ur", "hi", "bn", "zh", "zh-TW", "ja", "ko", "th", "vi", "ms", "id", "tl",
    "sw", "am", "af", "ht",
    "ha", "yo", "zu", "so", "mg", "wo", "ta", "ty", "qu",
)

_TABLE = """
europe: AD ca es fr | AL en | AT de | AX sv | BA hr sr | BE fr nl de | BG bg | BY ru | CH de fr it
 | CY el tr | CZ cs | DE de | DK da | EE et | ES es ca | FI fi sv | FO da | FR fr | GB en | GG en
 | GI en | GR el | HR hr | HU hu | IE en | IM en | IS en | IT it | JE en | LI de | LT lt | LU fr de
 | LV lv | MC fr | MD ro ru | ME sr | MK en | MT en | NL nl | NO nb | PL pl | PT pt | RO ro | RS sr
 | RU ru | SE sv | SI sl | SJ nb | SK sk | SM it | UA uk | VA it | XK en
north_america: US en es | CA en fr | BM en | PM fr | GL da
latam: AR es | BO es qu | BR pt-BR | CL es | CO es | CR es | CU es | DO es | EC es qu | SV es | GT es
 | HN es | MX es | NI es | PA es | PY es | PE es qu | PR es en | UY es | VE es | HT ht fr | BZ en
 | GY en | SR nl | GF fr | GP fr | MQ fr | MF fr | BL fr | JM en | TT en | BB en | BS en | LC en
 | DM en | GD en | VC en | AG en | KN en | AW nl | CW nl | SX nl en | BQ nl | KY en | TC en | VG en
 | VI en | AI en | MS en | FK en
africa: DZ ar fr | AO pt | BJ fr | BW en | BF fr | BI fr sw en | CV pt | CM fr en | CF fr | TD fr ar
 | KM fr ar | CG fr | CD fr sw | CI fr | DJ fr ar | EG ar en | GQ es fr pt | ER ar en | SZ en
 | ET am en | GA fr | GM en | GH en | GN fr | GW pt | KE sw en | LS en | LR en | LY ar | MG mg fr
 | MW en | ML fr | MR ar fr | MU en fr | MA ar fr | MZ pt | NA en af | NE fr ha | NG en ha yo | RW en fr sw
 | ST pt | SN fr wo | SC en fr | SL en | SO so ar en | ZA en af zu | SS en ar | SD ar en | TZ sw en | TG fr
 | TN ar fr | UG en sw | ZM en | ZW en | EH ar es | RE fr | YT fr | SH en
middle_east: AE ar en | BH ar | IL he ar | IQ ar | IR fa | JO ar | KW ar | LB ar fr | OM ar | PS ar
 | QA ar | SA ar | SY ar | TR tr | YE ar
asia: AF fa | AM en | AZ en | BD bn | BN ms | BT en | CN zh | GE en | HK zh-TW en | ID id | IN hi en ta
 | JP ja | KG ru | KH en | KP ko | KR ko | KZ ru | LA en | LK en ta | MM en | MN en | MO zh-TW pt
 | MV en | MY ms en | NP en | PH tl en | PK ur en | SG en zh ms | TH th | TJ ru | TL pt | TM ru
 | TW zh-TW | UZ ru | VN vi
oceania: AU en | NZ en | FJ en | PG en | SB en | VU fr en | NC fr | PF fr ty | WF fr | WS en | TO en
 | KI en | TV en | NR en | FM en | MH en | PW en | CK en | NU en | GU en | MP en | AS en | NF en
 | PN en | TK en | CX en | CC en
"""


def _parse() -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    region_of: dict[str, str] = {}
    languages: dict[str, tuple[str, ...]] = {}
    for block in _TABLE.strip().split("\n"):
        if ":" in block.split("|")[0] and not block.startswith(" "):
            region, rest = block.split(":", 1)
            current = region.strip()
        else:
            rest = block
        for entry in rest.split("|"):
            parts = entry.split()
            if not parts:
                continue
            code, langs = parts[0], tuple(parts[1:])
            region_of[code] = current
            languages[code] = langs
    return region_of, languages


REGION_OF, COUNTRY_LANGUAGES = _parse()

REGION_NAMES = {
    "europe": "Europe",
    "north_america": "North America",
    "latam": "Latin America and the Caribbean",
    "africa": "Africa",
    "middle_east": "Middle East",
    "asia": "Asia",
    "oceania": "Oceania and the Pacific",
}


def suggested_language(country: str) -> str:
    langs = COUNTRY_LANGUAGES.get(country.upper())
    return langs[0] if langs else "en"
