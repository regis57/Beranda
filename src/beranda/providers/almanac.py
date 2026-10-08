"""Almanac blocks for the Iberian, Italian and Brazilian themes: the astronomical season
(the right one for your hemisphere) with a traditional saying.

Spain, Italy and Portugal: one weather proverb per month, as farmers' almanacs print them.
Brazil: a popular saying (ditado popular) that changes every day. They stay in their own
language whatever the display language, like the kanji of the Japanese theme.

These sayings are traditional and public domain; spellings vary from region to region.
"""

from __future__ import annotations

from datetime import date

from . import equinox

PROVERBS = {
    "es": (
        "Año de nieves, año de bienes.",
        "Febrerillo el loco, un día peor que otro.",
        "Marzo ventoso y abril lluvioso sacan a mayo florido y hermoso.",
        "En abril, aguas mil.",
        "Hasta el cuarenta de mayo, no te quites el sayo.",
        "Junio, hoz en puño.",
        "En julio, beber y sudar, y el fresco en balde buscar.",
        "Agosto, frío en rostro.",
        "Septiembre, o seca las fuentes o se lleva los puentes.",
        "Octubre, echa pan y cubre.",
        "Noviembre acabado, invierno empezado.",
        "Por Santa Lucía, mengua la noche y crece el día.",
    ),
    "it": (
        "Gennaio secco, massaio ricco.",
        "Febbraio, febbraietto, corto e maledetto.",
        "Marzo pazzerello, guarda il sole e prendi l'ombrello.",
        "Aprile, ogni goccia un barile.",
        "Maggio ortolano, molta paglia e poco grano.",
        "Giugno, la falce in pugno.",
        "Luglio, dal gran caldo bevi bene e batti saldo.",
        "Agosto, moglie mia non ti conosco.",
        "Settembre, l'uva è fatta e il fico pende.",
        "Ottobre è bello, ma tieni pronto l'ombrello.",
        "Per San Martino ogni mosto diventa vino.",
        "Santa Lucia, il giorno più corto che ci sia.",
    ),
    "pt": (
        "Janeiro fora, cresce uma hora.",
        "Fevereiro quente traz o diabo no ventre.",
        "Março marçagão, manhã de inverno, tarde de verão.",
        "Abril, águas mil.",
        "Maio pardo, ano farto.",
        "Junho calmoso, ano formoso.",
        "Em julho, ceifo o trigo e o debulho.",
        "Agosto tem a culpa e setembro leva a fruta.",
        "Setembro molhado, figo estragado.",
        "Em outubro, sê prudente: guarda pão e semente.",
        "Pelo São Martinho, vai à adega e prova o vinho.",
        "Pelo Natal, cada ovelha no seu curral.",
    ),
}

DITADOS = (
    "Água mole em pedra dura, tanto bate até que fura.",
    "Devagar se vai ao longe.",
    "De grão em grão, a galinha enche o papo.",
    "Depois da tempestade vem a bonança.",
    "Quem semeia vento colhe tempestade.",
    "A pressa é inimiga da perfeição.",
    "Mais vale um pássaro na mão do que dois voando.",
    "Quem não tem cão, caça com gato.",
    "Em casa de ferreiro, espeto de pau.",
    "Cada macaco no seu galho.",
    "A união faz a força.",
    "Quem espera sempre alcança.",
    "Águas passadas não movem moinhos.",
    "O apressado come cru.",
    "Uma andorinha só não faz verão.",
    "Filho de peixe, peixinho é.",
    "Quem vê cara não vê coração.",
    "Antes tarde do que nunca.",
    "Não há mal que sempre dure.",
    "Pimenta nos olhos dos outros é refresco.",
)

_NOTE = {
    "es": "Refrán del mes",
    "it": "Proverbio del mese",
    "pt": "Provérbio do mês",
    "pt-BR": "Ditado do dia",
}
_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")


def current(today: date, tz: str, latitude: float, tradition: str) -> dict:
    """tradition: 'es', 'it', 'pt' (proverb of the month) or 'pt-BR' (saying of the day)."""
    sky = equinox.season(today, tz, latitude)
    if tradition == "pt-BR":
        saying = DITADOS[today.toordinal() % len(DITADOS)]
    else:
        saying = PROVERBS[tradition][today.month - 1]
    return {
        "kind": "almanac",
        "number": today.month,
        "glyph": _ROMAN[today.month - 1],
        "seal": "☼",
        "title_key": f"seasons.{sky['season']}",
        "title": {},
        "sub": {"en": saying},
        "sub_lang": tradition,
        "note": {"en": _NOTE[tradition]},
        "next_change": sky["next_change"],
        "days_left": sky["days_left"],
    }
