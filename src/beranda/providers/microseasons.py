"""The 72 micro-seasons (七十二候, shichijūni kō) of the traditional Japanese calendar.

Each lasts about five days. The start dates below are the commonly published modern
approximations; the real boundaries move by a day from year to year.

Tuple: (month, day, kanji, romaji, english, french)
"""

from __future__ import annotations

from datetime import date

KO: tuple[tuple[int, int, str, str, str, str], ...] = (
    (2, 4, "東風解凍", "Harukaze kōri o toku", "East wind melts the ice",
     "Le vent d'est fait fondre la glace"),
    (2, 9, "黄鶯睍睆", "Kōō kenkan su", "Bush warblers start singing in the mountains",
     "La fauvette chante dans les montagnes"),
    (2, 14, "魚上氷", "Uo kōri o izuru", "Fish emerge from the ice",
     "Les poissons sortent de la glace"),
    (2, 19, "土脉潤起", "Tsuchi no shō uruoi okoru", "Rain moistens the soil",
     "La pluie humecte la terre"),
    (2, 24, "霞始靆", "Kasumi hajimete tanabiku", "Mist starts to linger",
     "La brume commence à flotter"),
    (3, 1, "草木萌動", "Sōmoku mebae izuru", "Grass sprouts, trees bud",
     "L'herbe germe, les arbres bourgeonnent"),
    (3, 6, "蟄虫啓戸", "Sugomori mushito o hiraku", "Hibernating insects surface",
     "Les insectes sortent de leur abri"),
    (3, 11, "桃始笑", "Momo hajimete saku", "First peach blossoms",
     "Premières fleurs de pêcher"),
    (3, 16, "菜虫化蝶", "Namushi chō to naru", "Caterpillars become butterflies",
     "Les chenilles deviennent papillons"),
    (3, 21, "雀始巣", "Suzume hajimete sukū", "Sparrows start to nest",
     "Les moineaux commencent à nicher"),
    (3, 26, "桜始開", "Sakura hajimete saku", "First cherry blossoms",
     "Premières fleurs de cerisier"),
    (3, 31, "雷乃発声", "Kaminari sunawachi koe o hassu", "Distant thunder",
     "Premier tonnerre lointain"),
    (4, 5, "玄鳥至", "Tsubame kitaru", "Swallows return", "Les hirondelles reviennent"),
    (4, 10, "鴻雁北", "Kōgan kaeru", "Wild geese fly north",
     "Les oies sauvages repartent vers le nord"),
    (4, 15, "虹始見", "Niji hajimete arawaru", "First rainbows", "Premiers arcs-en-ciel"),
    (4, 20, "葭始生", "Ashi hajimete shōzu", "First reeds sprout",
     "Les premiers roseaux poussent"),
    (4, 25, "霜止出苗", "Shimo yamite nae izuru", "Last frost, rice seedlings grow",
     "Dernier gel, les plants de riz poussent"),
    (4, 30, "牡丹華", "Botan hana saku", "Peonies bloom", "Les pivoines fleurissent"),
    (5, 5, "蛙始鳴", "Kawazu hajimete naku", "Frogs start singing",
     "Les grenouilles se mettent à chanter"),
    (5, 10, "蚯蚓出", "Mimizu izuru", "Worms surface", "Les vers de terre sortent"),
    (5, 16, "竹笋生", "Takenoko shōzu", "Bamboo shoots sprout", "Les pousses de bambou jaillissent"),
    (5, 21, "蚕起食桑", "Kaiko okite kuwa o hamu", "Silkworms start feasting on mulberry",
     "Les vers à soie se nourrissent de mûrier"),
    (5, 26, "紅花栄", "Benibana sakau", "Safflowers bloom", "Les carthames fleurissent"),
    (5, 31, "麦秋至", "Mugi no toki itaru", "Wheat ripens", "Le blé mûrit"),
    (6, 6, "螳螂生", "Kamakiri shōzu", "Praying mantises hatch",
     "Les mantes religieuses éclosent"),
    (6, 11, "腐草為螢", "Kusaretaru kusa hotaru to naru", "Rotten grass becomes fireflies",
     "Les lucioles naissent de l'herbe humide"),
    (6, 16, "梅子黄", "Ume no mi kibamu", "Plums turn yellow", "Les prunes jaunissent"),
    (6, 21, "乃東枯", "Natsukarekusa karuru", "Self-heal withers", "La brunelle se flétrit"),
    (6, 27, "菖蒲華", "Ayame hana saku", "Irises bloom", "Les iris fleurissent"),
    (7, 2, "半夏生", "Hange shōzu", "Crow-dipper sprouts", "Le pinellia pousse"),
    (7, 7, "温風至", "Atsukaze itaru", "Warm winds blow", "Les vents chauds soufflent"),
    (7, 12, "蓮始開", "Hasu hajimete hiraku", "First lotus blossoms",
     "Premières fleurs de lotus"),
    (7, 17, "鷹乃学習", "Taka sunawachi waza o narau", "Hawks learn to fly",
     "Les faucons apprennent à voler"),
    (7, 22, "桐始結花", "Kiri hajimete hana o musubu", "Paulownia trees produce seeds",
     "Les paulownias donnent des graines"),
    (7, 28, "土潤溽暑", "Tsuchi uruōte mushiatsushi", "Earth is damp, air humid",
     "La terre est moite, l'air étouffant"),
    (8, 2, "大雨時行", "Taiu tokidoki furu", "Great rains sometimes fall",
     "De grandes pluies tombent parfois"),
    (8, 7, "涼風至", "Suzukaze itaru", "Cool winds blow", "Le vent frais se lève"),
    (8, 12, "寒蝉鳴", "Higurashi naku", "Evening cicadas sing", "Les cigales du soir chantent"),
    (8, 17, "蒙霧升降", "Fukaki kiri matō", "Thick fog descends", "Un épais brouillard descend"),
    (8, 23, "綿柎開", "Wata no hana shibe hiraku", "Cotton flowers bloom",
     "Les fleurs de coton s'ouvrent"),
    (8, 28, "天地始粛", "Tenchi hajimete samushi", "Heat starts to die down",
     "La chaleur commence à retomber"),
    (9, 2, "禾乃登", "Kokumono sunawachi minoru", "Rice ripens", "Le riz mûrit"),
    (9, 7, "草露白", "Kusa no tsuyu shiroshi", "Dew glistens white on grass",
     "La rosée blanchit l'herbe"),
    (9, 12, "鶺鴒鳴", "Sekirei naku", "Wagtails sing", "Les bergeronnettes chantent"),
    (9, 17, "玄鳥去", "Tsubame saru", "Swallows leave", "Les hirondelles s'en vont"),
    (9, 23, "雷乃収声", "Kaminari sunawachi koe o osamu", "Thunder ceases", "Le tonnerre se tait"),
    (9, 28, "蟄虫坏戸", "Mushi kakurete to o fusagu", "Insects hole up underground",
     "Les insectes se retirent sous terre"),
    (10, 3, "水始涸", "Mizu hajimete karuru", "Farmers drain fields", "On vide les rizières"),
    (10, 8, "鴻雁来", "Kōgan kitaru", "Wild geese return", "Les oies sauvages reviennent"),
    (10, 13, "菊花開", "Kiku no hana hiraku", "Chrysanthemums bloom",
     "Les chrysanthèmes fleurissent"),
    (10, 18, "蟋蟀在戸", "Kirigirisu to ni ari", "Crickets chirp around the door",
     "Les grillons chantent près de la porte"),
    (10, 23, "霜始降", "Shimo hajimete furu", "First frost", "Première gelée"),
    (10, 28, "霎時施", "Kosame tokidoki furu", "Light rains sometimes fall",
     "Petites pluies passagères"),
    (11, 2, "楓蔦黄", "Momiji tsuta kibamu", "Maple leaves and ivy turn yellow",
     "Érables et lierres jaunissent"),
    (11, 7, "山茶始開", "Tsubaki hajimete hiraku", "Camellias bloom",
     "Les camélias fleurissent"),
    (11, 12, "地始凍", "Chi hajimete kōru", "Land starts to freeze",
     "La terre commence à geler"),
    (11, 17, "金盞香", "Kinsenka saku", "Daffodils bloom", "Les jonquilles fleurissent"),
    (11, 22, "虹蔵不見", "Niji kakurete miezu", "Rainbows hide", "Les arcs-en-ciel se cachent"),
    (11, 27, "朔風払葉", "Kitakaze konoha o harau", "North wind blows the leaves from the trees",
     "Le vent du nord emporte les feuilles"),
    (12, 2, "橘始黄", "Tachibana hajimete kibamu", "Tachibana citrus tree leaves turn yellow",
     "Les tachibana jaunissent"),
    (12, 7, "閉塞成冬", "Sora samuku fuyu to naru", "Cold sets in, winter begins",
     "Le froid s'installe, l'hiver commence"),
    (12, 12, "熊蟄穴", "Kuma ana ni komoru", "Bears start hibernating",
     "Les ours entrent en hibernation"),
    (12, 17, "鱖魚群", "Sake no uo muragaru", "Salmon gather and swim upstream",
     "Les saumons remontent les rivières"),
    (12, 22, "乃東生", "Natsukarekusa shōzu", "Self-heal sprouts", "La brunelle pousse"),
    (12, 27, "麋角解", "Sawashika no tsuno otsuru", "Deer shed antlers",
     "Les cerfs perdent leurs bois"),
    (1, 1, "雪下出麦", "Yuki watarite mugi nobiru", "Wheat sprouts under snow",
     "Le blé sort de sous la neige"),
    (1, 5, "芹乃栄", "Seri sunawachi sakau", "Parsley flourishes",
     "Le persil japonais prospère"),
    (1, 10, "水泉動", "Shimizu atataka o fukumu", "Springs thaw", "Les sources se réveillent"),
    (1, 15, "雉始雊", "Kiji hajimete naku", "Pheasants start to call",
     "Les faisans se mettent à crier"),
    (1, 20, "款冬華", "Fuki no hana saku", "Butterburs bud", "Les pétasites bourgeonnent"),
    (1, 25, "水沢腹堅", "Sawamizu kōri tsumeru", "Ice thickens on streams",
     "La glace s'épaissit sur les ruisseaux"),
    (1, 30, "鶏始乳", "Niwatori hajimete toya ni tsuku", "Hens start laying eggs",
     "Les poules recommencent à pondre"),
)

# Sorted by calendar position so that "the latest start on or before today" always exists
# (the Jan 1 entry precedes every other date of the year).
_BY_CALENDAR = sorted(range(len(KO)), key=lambda i: (KO[i][0], KO[i][1]))


def current(today: date) -> dict:
    """The micro-season in force on `today`, plus when the next one begins."""
    key = (today.month, today.day)
    position = max(p for p, i in enumerate(_BY_CALENDAR) if (KO[i][0], KO[i][1]) <= key)
    idx = _BY_CALENDAR[position]
    nxt = _BY_CALENDAR[(position + 1) % len(_BY_CALENDAR)]

    next_month, next_day = KO[nxt][0], KO[nxt][1]
    next_start = date(today.year, next_month, next_day)
    if next_start <= today:
        next_start = date(today.year + 1, next_month, next_day)

    _, _, kanji, romaji, en, fr = KO[idx]
    return {
        "number": idx + 1,  # 1 = start of spring (立春), 72 = last of the year
        "kanji": kanji,
        "romaji": romaji,
        "en": en,
        "fr": fr,
        "next_change": next_start.isoformat(),
        "days_left": (next_start - today).days,
    }
