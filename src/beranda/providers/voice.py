"""Turning a spoken sentence into one of Beranda's own actions.

The tablet's browser listens and turns speech into text (that part is the browser's job, see
`voice.js`); the text then comes here. This is the only "understanding" voice control needs:
no assistant, no language model, just a short list of trigger words per language. It is
deliberately small - a handful of things said around a kitchen (the weather, the time, a
favourite station, stopping the radio), not a general assistant.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parent.parent / "web" / "i18n"

# Longer phrases are tried before shorter ones, so e.g. "turn off the radio" is not swallowed
# by the shorter "stop" trigger first. "radio_play" is special: whatever is left of the
# sentence after removing its trigger phrase is kept as the station name to search for.
_INTENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "en": {
        "weather": ("what's the weather", "weather", "forecast"),
        "time": ("what time is it", "time"),
        "radio_stop": ("turn off the radio", "stop the radio", "stop", "quiet"),
        "radio_play": ("play",),
        "radio_next": ("next station", "next radio", "skip"),
        "radio_prev": ("previous station", "last station", "go back"),
        "volume_up": ("volume up", "louder", "turn it up"),
        "volume_down": ("volume down", "quieter", "turn it down"),
        "tv": ("tv tonight", "what's on tonight", "on tv", "television"),
        "read_day": ("read me the day", "read the day", "what's my day", "read the screen"),
        "date": ('what day is it', "what's the date", "today's date", 'which day is it'),
        "agenda": ('what do i have today', 'my agenda', "today's agenda", "what's planned today", "what's on today"),
        "tomorrow": ('what do i have tomorrow', "tomorrow's agenda", "what's planned tomorrow", "what's on tomorrow", 'tomorrow'),
        "news": ('read the news', 'the news', 'headlines', "what's in the news"),
        "bigger": ('bigger', 'larger text', 'bigger text', 'zoom in'),
        "smaller": ('smaller', 'smaller text', 'normal text', 'zoom out'),
        "contrast_on": ('high contrast', 'more contrast', 'black and white'),
        "contrast_off": ('normal contrast', 'normal colours', 'normal colors', 'colours back'),
        "quiet": ('be quiet', 'stop talking', 'shut up', 'enough'),
    },
    "fr": {
        "weather": ("quel temps fait-il", "météo", "prévisions"),
        "time": ("quelle heure est-il", "heure"),
        "radio_stop": ("coupe la radio", "arrête la radio", "silence", "arrête", "stop"),
        "radio_play": ("joue", "mets", "remets", "écoute"),
        "radio_next": ("station suivante", "radio suivante", "suivante", "suivant"),
        "radio_prev": ("station précédente", "radio précédente", "précédente", "précédent"),
        "volume_up": ("plus fort", "monte le son", "augmente le volume"),
        "volume_down": ("moins fort", "baisse le son", "baisse le volume"),
        "tv": ("à la télé", "programme tv", "programme télé", "télévision"),
        "read_day": ("lis-moi la journée", "lis moi la journée", "lis la journée", "lis l'écran", "ma journée"),
        "date": ('quel jour on est', 'quel jour sommes-nous', 'on est quel jour', 'la date', 'quelle est la date'),
        "agenda": ("qu'est-ce que j'ai aujourd'hui", 'mon agenda', 'agenda du jour', "qu'est-ce qui est prévu aujourd'hui", "au programme aujourd'hui"),
        "tomorrow": ("qu'est-ce que j'ai demain", 'agenda de demain', "qu'est-ce qui est prévu demain", 'demain'),
        "news": ('lis les nouvelles', 'lis les actualités', 'les nouvelles', 'les actualités', 'les titres'),
        "bigger": ('plus gros', 'plus grand', 'texte plus gros', 'agrandis'),
        "smaller": ('plus petit', 'texte plus petit', 'texte normal', 'taille normale'),
        "contrast_on": ('fort contraste', 'plus de contraste', 'noir et blanc'),
        "contrast_off": ('contraste normal', 'couleurs normales', 'remets les couleurs'),
        "quiet": ('tais-toi', 'arrête de parler', 'chut'),
    },
    "de": {
        "weather": ("wie ist das wetter", "wetter", "vorhersage"),
        "time": ("wie spät ist es", "uhrzeit", "zeit"),
        "radio_stop": ("radio aus", "stopp", "stop", "leise"),
        "radio_play": ("spiele", "spiel"),
        "radio_next": ("nächster sender", "nächste station", "nächster"),
        "radio_prev": ("vorheriger sender", "letzter sender", "zurück"),
        "volume_up": ("lauter",),
        "volume_down": ("leiser",),
        "tv": ("fernsehprogramm", "im fernsehen", "tv-programm", "fernsehen"),
        "read_day": ("lies mir den tag vor", "lies den tag", "lies den bildschirm", "mein tag"),
        "date": ('welcher tag ist heute', 'welches datum haben wir', 'das datum', 'welcher tag ist es'),
        "agenda": ('was habe ich heute', 'mein kalender', 'termine heute', 'was steht heute an'),
        "tomorrow": ('was habe ich morgen', 'termine morgen', 'was steht morgen an', 'morgen'),
        "news": ('lies die nachrichten', 'die nachrichten', 'schlagzeilen', 'was gibt es neues'),
        "bigger": ('größer', 'größerer text', 'text größer', 'vergrößern'),
        "smaller": ('kleiner', 'kleinerer text', 'normaler text', 'normale größe'),
        "contrast_on": ('hoher kontrast', 'mehr kontrast', 'schwarz-weiß', 'schwarz weiß'),
        "contrast_off": ('normaler kontrast', 'normale farben', 'farben zurück'),
        "quiet": ('sei still', 'ruhe', 'hör auf zu reden', 'genug'),
    },
    "es": {
        "weather": ("qué tiempo hace", "tiempo", "pronóstico"),
        "time": ("qué hora es", "hora"),
        "radio_stop": ("para la radio", "detén la radio", "silencio", "para"),
        "radio_play": ("pon", "reproduce", "escucha"),
        "radio_next": ("siguiente emisora", "siguiente"),
        "radio_prev": ("emisora anterior", "anterior"),
        "volume_up": ("sube el volumen", "más fuerte", "más alto", "sube"),
        "volume_down": ("baja el volumen", "más bajo", "baja"),
        "tv": ("en la tele", "programa de tv", "televisión"),
        "read_day": ("léeme el día", "lee el día", "lee la pantalla", "mi día"),
        "date": ('qué día es hoy', 'qué fecha es', 'la fecha', 'qué día es'),
        "agenda": ('qué tengo hoy', 'mi agenda', 'agenda de hoy', 'qué hay previsto hoy'),
        "tomorrow": ('qué tengo mañana', 'agenda de mañana', 'qué hay previsto mañana', 'mañana'),
        "news": ('lee las noticias', 'las noticias', 'titulares', 'qué hay de nuevo'),
        "bigger": ('más grande', 'texto más grande', 'agranda', 'aumentar'),
        "smaller": ('más pequeño', 'texto más pequeño', 'texto normal', 'tamaño normal'),
        "contrast_on": ('alto contraste', 'más contraste', 'blanco y negro'),
        "contrast_off": ('contraste normal', 'colores normales', 'devuelve los colores'),
        "quiet": ('cállate', 'deja de hablar', 'basta'),
    },
    "it": {
        "weather": ("che tempo fa", "meteo", "previsioni"),
        "time": ("che ora è", "ora"),
        "radio_stop": ("ferma la radio", "silenzio", "stop"),
        "radio_play": ("metti", "riproduci", "ascolta"),
        "radio_next": ("stazione successiva", "successiva", "prossima"),
        "radio_prev": ("stazione precedente", "precedente"),
        "volume_up": ("alza il volume", "più forte", "volume su"),
        "volume_down": ("abbassa il volume", "più piano", "volume giù"),
        "tv": ("stasera in tv", "programma tv", "in tv", "televisione"),
        "read_day": ("leggimi la giornata", "leggi la giornata", "leggi lo schermo", "la mia giornata"),
        "date": ('che giorno è oggi', 'che giorno è', 'la data', 'qual è la data'),
        "agenda": ('cosa ho oggi', 'la mia agenda', 'agenda di oggi', "cosa c'è in programma oggi"),
        "tomorrow": ('cosa ho domani', 'agenda di domani', "cosa c'è in programma domani", 'domani'),
        "news": ('leggi le notizie', 'le notizie', 'i titoli', "cosa c'è di nuovo"),
        "bigger": ('più grande', 'testo più grande', 'ingrandisci'),
        "smaller": ('più piccolo', 'testo più piccolo', 'testo normale', 'dimensione normale'),
        "contrast_on": ('alto contrasto', 'più contrasto', 'bianco e nero'),
        "contrast_off": ('contrasto normale', 'colori normali', 'rimetti i colori'),
        "quiet": ('zitto', 'smetti di parlare', 'basta'),
    },
    "pt": {
        "weather": ("que tempo faz", "previsão", "meteorologia"),
        "time": ("que horas são", "hora"),
        "radio_stop": ("para a rádio", "silêncio", "para"),
        "radio_play": ("põe", "toca", "ouve"),
        "radio_next": ("estação seguinte", "seguinte"),
        "radio_prev": ("estação anterior", "anterior"),
        "volume_up": ("aumenta o volume", "mais alto", "mais forte"),
        "volume_down": ("diminui o volume", "mais baixo", "mais fraco"),
        "tv": ("na televisão", "programação", "na tv", "televisão"),
        "read_day": ("lê-me o dia", "lê o dia", "lê o ecrã", "o meu dia"),
        "date": ('que dia é hoje', 'qual é a data', 'a data', 'que dia é'),
        "agenda": ('o que tenho hoje', 'a minha agenda', 'agenda de hoje', 'o que está previsto hoje'),
        "tomorrow": ('o que tenho amanhã', 'agenda de amanhã', 'o que está previsto amanhã', 'amanhã'),
        "news": ('lê as notícias', 'as notícias', 'os títulos', 'o que há de novo'),
        "bigger": ('maior', 'texto maior', 'aumenta', 'ampliar'),
        "smaller": ('mais pequeno', 'texto mais pequeno', 'texto normal', 'tamanho normal'),
        "contrast_on": ('alto contraste', 'mais contraste', 'preto e branco'),
        "contrast_off": ('contraste normal', 'cores normais', 'repõe as cores'),
        "quiet": ('cala-te', 'para de falar', 'chega'),
    },
    "pt-BR": {
        "weather": ("que tempo faz", "previsão", "meteorologia"),
        "time": ("que horas são", "hora"),
        "radio_stop": ("para o rádio", "silêncio", "para"),
        "radio_play": ("põe", "toca", "ouve"),
        "radio_next": ("rádio seguinte", "seguinte", "próxima"),
        "radio_prev": ("rádio anterior", "anterior"),
        "volume_up": ("aumenta o volume", "mais alto", "mais forte"),
        "volume_down": ("diminui o volume", "mais baixo", "mais fraco"),
        "tv": ("na televisão", "programação", "na tv", "televisão"),
        "read_day": ("leia meu dia", "leia o dia", "leia a tela", "meu dia"),
        "date": ('que dia é hoje', 'qual é a data', 'a data', 'que dia é'),
        "agenda": ('o que eu tenho hoje', 'minha agenda', 'agenda de hoje', 'o que está previsto hoje'),
        "tomorrow": ('o que eu tenho amanhã', 'agenda de amanhã', 'o que está previsto amanhã', 'amanhã'),
        "news": ('leia as notícias', 'as notícias', 'as manchetes', 'o que há de novo'),
        "bigger": ('maior', 'texto maior', 'aumenta', 'ampliar'),
        "smaller": ('menor', 'texto menor', 'texto normal', 'tamanho normal'),
        "contrast_on": ('alto contraste', 'mais contraste', 'preto e branco'),
        "contrast_off": ('contraste normal', 'cores normais', 'volta as cores'),
        "quiet": ('fica quieto', 'para de falar', 'chega'),
    },
    "ar": {
        "weather": ("كيف حال الطقس", "الطقس", "توقعات"),
        "time": ("كم الساعة", "الوقت"),
        "radio_stop": ("أوقف الراديو", "صمت", "قف"),
        "radio_play": ("شغل", "استمع"),
        "radio_next": ("المحطة التالية", "التالي"),
        "radio_prev": ("المحطة السابقة", "السابق"),
        "volume_up": ("ارفع الصوت",),
        "volume_down": ("اخفض الصوت",),
        "tv": ("برنامج التلفاز", "على التلفاز", "التلفزيون"),
        "read_day": ("اقرأ لي اليوم", "اقرأ اليوم", "اقرأ الشاشة", "يومي"),
        "date": ('ما هو تاريخ اليوم', 'ما اليوم', 'التاريخ', 'أي يوم اليوم'),
        "agenda": ('ماذا لدي اليوم', 'مواعيدي', 'مواعيد اليوم', 'ما المخطط اليوم'),
        "tomorrow": ('ماذا لدي غدا', 'ماذا لدي غدًا', 'مواعيد الغد', 'غدا', 'غدًا'),
        "news": ('اقرأ الأخبار', 'الأخبار', 'العناوين', 'ما الجديد'),
        "bigger": ('أكبر', 'نص أكبر', 'كبّر', 'كبر'),
        "smaller": ('أصغر', 'نص أصغر', 'نص عادي', 'الحجم العادي'),
        "contrast_on": ('تباين عال', 'تباين عالٍ', 'أبيض وأسود'),
        "contrast_off": ('تباين عادي', 'الألوان العادية', 'أعد الألوان'),
        "quiet": ('اصمت', 'توقف عن الكلام', 'كفى'),
    },
    "sw": {
        "weather": ("hali ya hewa", "utabiri"),
        "time": ("saa ngapi", "muda"),
        "radio_stop": ("zima redio", "kimya", "simama"),
        "radio_play": ("cheza", "sikiliza"),
        "radio_next": ("kituo kinachofuata", "kinachofuata"),
        "radio_prev": ("kituo kilichotangulia", "kilichotangulia"),
        "volume_up": ("ongeza sauti",),
        "volume_down": ("punguza sauti",),
        "tv": ("kwenye tv", "televisheni"),
        "read_day": ("nisomee siku", "soma siku", "soma skrini", "siku yangu"),
        "date": ('leo ni tarehe gani', 'tarehe', 'leo ni siku gani', 'ni siku gani'),
        "agenda": ('nina nini leo', 'ratiba yangu', 'ratiba ya leo', 'kuna nini leo'),
        "tomorrow": ('nina nini kesho', 'ratiba ya kesho', 'kuna nini kesho', 'kesho'),
        "news": ('soma habari', 'habari', 'vichwa vya habari', 'kuna nini kipya'),
        "bigger": ('kubwa zaidi', 'maandishi makubwa', 'kuza'),
        "smaller": ('ndogo zaidi', 'maandishi madogo', 'maandishi ya kawaida', 'ukubwa wa kawaida'),
        "contrast_on": ('utofauti mkubwa', 'nyeusi na nyeupe'),
        "contrast_off": ('utofauti wa kawaida', 'rangi za kawaida', 'rudisha rangi'),
        "quiet": ('nyamaza', 'acha kuongea', 'inatosha'),
    },
    "id": {
        "weather": ("bagaimana cuacanya", "cuaca", "ramalan"),
        "time": ("jam berapa", "waktu"),
        "radio_stop": ("matikan radio", "diam", "berhenti"),
        "radio_play": ("putar", "dengarkan"),
        "radio_next": ("stasiun berikutnya", "berikutnya"),
        "radio_prev": ("stasiun sebelumnya", "sebelumnya"),
        "volume_up": ("naikkan volume", "lebih keras"),
        "volume_down": ("turunkan volume", "lebih pelan"),
        "tv": ("acara tv", "di tv", "televisi"),
        "read_day": ("bacakan hari ini", "baca hari ini", "baca layar", "hari saya"),
        "date": ('hari ini tanggal berapa', 'tanggal berapa', 'tanggalnya', 'hari apa ini'),
        "agenda": ('ada apa hari ini', 'agenda saya', 'agenda hari ini', 'jadwal hari ini'),
        "tomorrow": ('ada apa besok', 'agenda besok', 'jadwal besok', 'besok'),
        "news": ('bacakan berita', 'berita', 'judul berita', 'apa yang baru'),
        "bigger": ('lebih besar', 'teks lebih besar', 'perbesar'),
        "smaller": ('lebih kecil', 'teks lebih kecil', 'teks normal', 'ukuran normal'),
        "contrast_on": ('kontras tinggi', 'lebih kontras', 'hitam putih'),
        "contrast_off": ('kontras normal', 'warna normal', 'kembalikan warna'),
        "quiet": ('tenang', 'berhenti bicara', 'cukup'),
    },
}


def _normalise(text: str) -> str:
    """Lower case, one space between words, and no dashes or punctuation: a speech service
    writes "tais-toi" or "tais toi" as it pleases, and both must mean the same."""
    text = unicodedata.normalize("NFKC", text).lower().strip()
    # A phone keyboard types a curly apostrophe (what’s) where a speech service writes a straight
    # one (what's); an own phrase typed on an iPhone must still match what was heard.
    text = re.sub(r"[\u2018\u2019\u02bc\u00b4`]", "'", text)
    # Accents are dropped on both sides: a speech service and a person typing an own phrase do
    # not always agree on them ("pára" or "para", "previsions" or "prévisions"), and the meaning
    # does not change. A test checks that no two built-in phrases clash once accents are gone.
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[-–—,;:!?.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_intent(text: str, language: str = "en") -> dict | None:
    """The first trigger phrase found in `text`, longest phrases checked first, or None."""
    text = _normalise(text)
    if not text:
        return None
    # "fr-FR" must hear French phrases, as the replies and the guide already fall back that way.
    keywords = _INTENTS.get(language) or _INTENTS.get(language.split("-")[0]) or _INTENTS["en"]
    candidates = sorted(
        ((intent, trig) for intent, trigs in keywords.items() for trig in trigs),
        key=lambda pair: -len(pair[1]),
    )
    for intent, trig in candidates:
        trig = _normalise(trig)  # "tais-toi" in the list, "tais toi" from the microphone: the same
        # Whole words only: "time" must not fire inside "Times Radio", nor "mets" inside "remets".
        m = re.search(rf"(?<!\w){re.escape(trig)}(?!\w)", text)
        if m is None:
            continue
        if intent == "radio_play":
            remainder = re.sub(r"\s+", " ", text[: m.start()] + text[m.end() :]).strip()
            return {"intent": intent, "query": remainder}
        return {"intent": intent}
    return None


# A heard station name rarely matches a saved favourite letter for letter (mishears, accents,
# word order); below this similarity we'd rather say "not found" than play the wrong station.
PAGE_INTENTS = ("read_day", "date", "agenda", "tomorrow", "news", "bigger", "smaller", "contrast_on", "contrast_off", "quiet")
MATCH_THRESHOLD = 0.4

_RESPONSES: dict[str, dict[str, str]] = {
    "en": {
        "weather_unknown": "I don't have the weather right now.",
        "weather": "It's {temp} degrees, {sky}.",
        "time": "It's {time}.",
        "radio_playing": "Playing {name}.",
        "radio_not_found": "I couldn't find that station in your favourites.",
        "radio_stopped": "Stopped.",
        "unknown": "Sorry, I didn't understand.",
        "ok": "OK.",
        "tv": "Tonight on TV: {list}.",
        "tv_none": "I have no TV programme for tonight.",
    },
    "fr": {
        "weather_unknown": "Je n'ai pas la météo pour le moment.",
        "weather": "Il fait {temp} degrés, {sky}.",
        "time": "Il est {time}.",
        "radio_playing": "Je lance {name}.",
        "radio_not_found": "Je n'ai pas trouvé cette station dans vos favorites.",
        "radio_stopped": "Arrêté.",
        "unknown": "Désolé, je n'ai pas compris.",
        "ok": "D'accord.",
        "tv": "Ce soir à la télé : {list}.",
        "tv_none": "Je n'ai aucun programme télé pour ce soir.",
    },
    "de": {
        "weather_unknown": "Ich habe gerade keine Wetterdaten.",
        "weather": "Es sind {temp} Grad, {sky}.",
        "time": "Es ist {time} Uhr.",
        "radio_playing": "Ich spiele {name}.",
        "radio_not_found": "Diesen Sender habe ich nicht in deinen Favoriten gefunden.",
        "radio_stopped": "Gestoppt.",
        "unknown": "Entschuldigung, das habe ich nicht verstanden.",
        "ok": "Okay.",
        "tv": "Heute Abend im Fernsehen: {list}.",
        "tv_none": "Ich habe kein Fernsehprogramm für heute Abend.",
    },
    "es": {
        "weather_unknown": "No tengo el tiempo en este momento.",
        "weather": "Hace {temp} grados, {sky}.",
        "time": "Son las {time}.",
        "radio_playing": "Reproduciendo {name}.",
        "radio_not_found": "No encontré esa emisora en tus favoritas.",
        "radio_stopped": "Detenido.",
        "unknown": "Lo siento, no entendí eso.",
        "ok": "Vale.",
        "tv": "Esta noche en la tele: {list}.",
        "tv_none": "No tengo programación de TV para esta noche.",
    },
    "it": {
        "weather_unknown": "Al momento non ho il meteo.",
        "weather": "Ci sono {temp} gradi, {sky}.",
        "time": "Sono le {time}.",
        "radio_playing": "Sto riproducendo {name}.",
        "radio_not_found": "Non ho trovato quella stazione tra i tuoi preferiti.",
        "radio_stopped": "Fermato.",
        "unknown": "Scusa, non ho capito.",
        "ok": "Va bene.",
        "tv": "Stasera in TV: {list}.",
        "tv_none": "Non ho programmi TV per stasera.",
    },
    "pt": {
        "weather_unknown": "Não tenho a meteorologia neste momento.",
        "weather": "Estão {temp} graus, {sky}.",
        "time": "São as {time}.",
        "radio_playing": "A tocar {name}.",
        "radio_not_found": "Não encontrei essa estação nas suas favoritas.",
        "radio_stopped": "Parado.",
        "unknown": "Desculpe, não entendi.",
        "ok": "Está bem.",
        "tv": "Esta noite na TV: {list}.",
        "tv_none": "Não tenho programação de TV para esta noite.",
    },
    "pt-BR": {
        "weather_unknown": "Não tenho a previsão agora.",
        "weather": "Estão {temp} graus, {sky}.",
        "time": "São as {time}.",
        "radio_playing": "Tocando {name}.",
        "radio_not_found": "Não encontrei essa rádio nas suas favoritas.",
        "radio_stopped": "Parado.",
        "unknown": "Desculpe, não entendi.",
        "ok": "Tudo bem.",
        "tv": "Hoje à noite na TV: {list}.",
        "tv_none": "Não tenho programação de TV para hoje à noite.",
    },
    "ar": {
        "weather_unknown": "لا تتوفر لدي حالة الطقس الآن.",
        "weather": "الحرارة {temp} درجة، {sky}.",
        "time": "الساعة الآن {time}.",
        "radio_playing": "تشغيل {name}.",
        "radio_not_found": "لم أجد هذه المحطة بين مفضلاتك.",
        "radio_stopped": "تم التوقف.",
        "unknown": "عذرًا، لم أفهم ذلك.",
        "ok": "حسنًا.",
        "tv": "هذا المساء على التلفاز: {list}.",
        "tv_none": "ليس لدي برنامج تلفزيوني لهذا المساء.",
    },
    "sw": {
        "weather_unknown": "Sina taarifa za hali ya hewa sasa hivi.",
        "weather": "Ni nyuzijoto {temp}, {sky}.",
        "time": "Ni saa {time}.",
        "radio_playing": "Ninacheza {name}.",
        "radio_not_found": "Sikuipata kituo hicho kwenye vipendwa vyako.",
        "radio_stopped": "Imesimama.",
        "unknown": "Samahani, sikuelewa.",
        "ok": "Sawa.",
        "tv": "Usiku huu kwenye TV: {list}.",
        "tv_none": "Sina kipindi cha TV cha usiku huu.",
    },
    "id": {
        "weather_unknown": "Saya tidak punya data cuaca saat ini.",
        "weather": "Suhunya {temp} derajat, {sky}.",
        "time": "Sekarang jam {time}.",
        "radio_playing": "Memutar {name}.",
        "radio_not_found": "Saya tidak menemukan stasiun itu di favorit Anda.",
        "radio_stopped": "Dihentikan.",
        "unknown": "Maaf, saya tidak mengerti.",
        "ok": "Baik.",
        "tv": "Malam ini di TV: {list}.",
        "tv_none": "Saya tidak punya acara TV untuk malam ini.",
    },
}



def _t(language: str, key: str, **kw) -> str:
    table = _RESPONSES.get(language) or _RESPONSES.get(language.split("-")[0]) or _RESPONSES["en"]
    return table.get(key, _RESPONSES["en"][key]).format(**kw)


def sky_text(language: str, code: int) -> str:
    """"Partly cloudy" for weather code 2, in the display's own translation (English if missing)."""
    for name in dict.fromkeys([language, language.split("-")[0], "en"]):
        try:
            strings = json.loads((I18N_DIR / f"{name}.json").read_text(encoding="utf-8"))
            return strings["wmo"][str(code)]
        except (OSError, ValueError, KeyError):
            continue
    return ""


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalise(a), _normalise(b)).ratio()


# Words people add around "radio" when they name no station ("put the radio on", "mets la radio"),
# in every voice language, already without accents. One shared set is enough: a word here only
# matters when no favourite's name came close to what was heard.
_RADIO_FILLER = frozenset(
    "the a an some on radio music "
    "la le les l' de du des un une musique "
    "das die der den ein eine radio musik "
    "el los las una musica "
    "il lo i gli "
    "o os as uma "
    "الراديو راديو الموسيقى موسيقى "
    "redio muziki "
    "musik".split()
)


def best_station(stations: list[dict], query: str) -> dict | None:
    """The saved favourite whose name is closest to what was heard, if any is close enough.

    Saying just "play the radio" (no name) picks the first favourite.
    """
    if not stations:
        return None
    if not query.strip():
        return stations[0]
    best = max(stations, key=lambda s: _similar(s.get("name", ""), query))
    if _similar(best.get("name", ""), query) >= MATCH_THRESHOLD:
        return best
    # Only after the names had their chance, so that "play radio 4" still finds "BBC Radio 4".
    if all(word in _RADIO_FILLER for word in _normalise(query).split()):
        return stations[0]
    return None


def default_commands(language: str) -> dict[str, list[str]]:
    """The built-in phrases per action, in the display language, for the settings page to show."""
    table = _INTENTS.get(language) or _INTENTS.get(language.split("-")[0]) or _INTENTS["en"]
    return {intent: list(phrases) for intent, phrases in table.items()}


def match_custom(text: str, commands) -> object | None:
    """The user's own command whose phrase is contained in what was said (longest phrase first).

    Own phrases win over the built-in ones: if you taught Beranda "good night", that is what
    "good night" does, whatever the built-in list says.
    """
    heard = _normalise(text)
    for cmd in sorted(commands, key=lambda c: -len(c.phrase)):
        phrase = _normalise(cmd.phrase)
        if phrase and phrase in heard:
            return cmd
    return None


def _tv_reply(language: str, tv: dict | None) -> str:
    programmes = (tv or {}).get("programmes") or []
    if not programmes:
        return _t(language, "tv_none")
    listing = ", ".join(f"{p['channel']} : {p['title']} ({p['start']})" for p in programmes[:4])
    return _t(language, "tv", list=listing)


def answer(
    text: str,
    *,
    language: str,
    now: datetime,
    stations: list[dict],
    weather: dict | None,
    tv: dict | None = None,
    commands=(),
) -> dict:
    """What to say and do for the sentence `text`.

    Returns {"intent": name|None, "reply": text to speak, "action": None | {"type": ..., ...}}.
    The page itself plays or stops the radio and moves the volume (the sound must come out of
    the tablet, and only the page knows which station is on).
    """
    custom = match_custom(text, commands)
    if custom is not None and custom.action == "say":
        return {"intent": "say", "reply": custom.reply, "action": None}
    if custom is not None:
        name, query, wanted = custom.action, "", custom.station
    else:
        intent = parse_intent(text, language)
        if intent is None:
            return {"intent": None, "reply": _t(language, "unknown"), "action": None}
        name, query, wanted = intent["intent"], intent.get("query", ""), ""

    if name == "weather":
        if not weather:
            return {"intent": name, "reply": _t(language, "weather_unknown"), "action": None}
        current = weather["current"]
        reply = _t(language, "weather", temp=round(current["temp"]), sky=sky_text(language, current["code"]).lower())
        return {"intent": name, "reply": reply, "action": None}
    if name == "time":
        return {"intent": name, "reply": _t(language, "time", time=now.strftime("%H:%M")), "action": None}
    if name == "tv":
        return {"intent": name, "reply": _tv_reply(language, tv), "action": None}
    if name == "radio_stop":
        return {"intent": name, "reply": _t(language, "radio_stopped"), "action": {"type": "radio_stop"}}
    if name in PAGE_INTENTS:
        # Done by the page itself: it has the agenda, the headlines and the looks on screen already,
        # in the right words, so it speaks or changes them without a round trip.
        return {"intent": name, "reply": "", "action": {"type": name}}
    if name in ("radio_next", "radio_prev", "volume_up", "volume_down"):
        return {"intent": name, "reply": _t(language, "ok"), "action": {"type": name}}

    # radio_play: a favourite chosen on the settings page, or the one named out loud.
    if wanted:
        station = next((s for s in stations if s.get("uuid") == wanted), None)
    else:
        station = best_station(stations, query)
    if station is None:
        return {"intent": name, "reply": _t(language, "radio_not_found"), "action": None}
    return {
        "intent": name,
        "reply": _t(language, "radio_playing", name=station["name"]),
        "action": {"type": "radio_play", "uuid": station.get("uuid", ""), "url": station["url"], "name": station["name"]},
    }
