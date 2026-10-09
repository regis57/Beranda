# Contrôle par la voix

Beranda peut vous écouter et vous répondre à voix haute. **Il utilise le micro et les haut-parleurs
de la tablette qui affiche Beranda**, jamais ceux du Raspberry Pi.

## Mode d'emploi, pas à pas

1. Dans la page de réglages, case **10 · Contrôle par la voix**, cochez **Afficher le bouton micro**
   puis **Enregistrez**.
2. Sur la tablette, ouvrez Beranda dans **Google Chrome**. (Edge la propose aussi, mais son service
   vocal répond souvent « network » et ne marche pas ; Firefox et Safari ne l'offrent pas aux pages web.)
3. Les navigateurs n'autorisent le micro que sur des pages « sécurisées », et une adresse comme
   `http://192.168.1.20:8080` n'en est pas une. Deux solutions, au choix :
   - **La plus simple : ajouter un « s ».** Ouvrez Beranda avec `https://` au lieu de `http://`,
     même adresse et même port (par exemple `https://beranda.local:8080`). La première fois, le
     navigateur prévient que la connexion n'est « pas privée » (le certificat est fabriqué par
     Beranda lui-même) : choisissez *Paramètres avancés*, puis *Continuer*. Rien ne sort de votre réseau.
   - **Ou un réglage unique dans Chrome**, sur la tablette ou l'ordinateur : ouvrez
     `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, tapez l'adresse de Beranda (par
     exemple `http://192.168.1.20:8080`), mettez le réglage sur **Enabled** et relancez Chrome.
4. Touchez le **micro** rond en bas à droite de l'écran. La première fois, Chrome demande
   l'autorisation d'utiliser le micro : touchez **Autoriser**.
5. Dites une courte phrase. L'écran affiche ce qui a été compris, Beranda répond à voix haute et
   exécute la demande.

> **Vie privée.** Chrome et Edge transforment votre voix en texte grâce au service *en ligne* de
> l'éditeur du navigateur : le son de votre voix passe donc par internet jusqu'à eux. Beranda, lui,
> ne reçoit que le texte obtenu, s'en sert et ne garde rien.

## Dans quelles langues ?

La tablette écoute dans la **langue d'affichage** choisie dans la case 2 des réglages.

- Dix langues ont des phrases toutes prêtes : anglais, français, allemand, espagnol, italien,
  portugais, portugais du Brésil, arabe, swahili et indonésien. Dans ces langues, Beranda répond
  aussi à voix haute dans la langue.
- Les 47 autres langues d'affichage comprennent les phrases **anglaises**, et n'importe quelle
  langue fonctionne pour **vos propres phrases** (plus bas), si Chrome sait la reconnaître.

## Ce que vous pouvez dire (phrases par défaut)

Plusieurs phrases veulent dire la même chose : dites-en une, au choix. La phrase peut être plus
longue que le modèle (« dis, quel temps fait-il aujourd'hui ? ») : Beranda cherche le modèle à
l'intérieur. Si deux modèles conviennent, le plus long l'emporte.

Dire seulement « mets » lance votre **première** station favorite ; « mets France Inter » lance la
favorite dont le nom ressemble le plus à ce qui a été entendu. Seules vos stations favorites
(case 8) peuvent être lancées.

**English** (`en`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « what's the weather » · « weather » · « forecast » |
| Heure | « what time is it » · « time » |
| La télé de ce soir | « tv tonight » · « what's on tonight » · « on tv » · « television » |
| Lancer une station (dites son nom après) | « play » |
| Arrêter la radio | « turn off the radio » · « stop the radio » · « stop » · « quiet » |
| Station suivante | « next station » · « next radio » · « skip » |
| Station précédente | « previous station » · « last station » · « go back » |
| Monter le son | « volume up » · « louder » · « turn it up » |
| Baisser le son | « volume down » · « quieter » · « turn it down » |

**Français** (`fr`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « quel temps fait-il » · « météo » · « previsions » |
| Heure | « quelle heure est-il » · « heure » |
| La télé de ce soir | « à la télé » · « programme tv » · « programme télé » · « télévision » |
| Lancer une station (dites son nom après) | « joue » · « mets » · « écoute » |
| Arrêter la radio | « coupe la radio » · « arrête la radio » · « silence » · « arrête » · « stop » |
| Station suivante | « station suivante » · « radio suivante » · « suivante » · « suivant » |
| Station précédente | « station précédente » · « radio précédente » · « précédente » · « précédent » |
| Monter le son | « plus fort » · « monte le son » · « augmente le volume » |
| Baisser le son | « moins fort » · « baisse le son » · « baisse le volume » |

**Deutsch** (`de`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « wie ist das wetter » · « wetter » · « vorhersage » |
| Heure | « wie spät ist es » · « uhrzeit » · « zeit » |
| La télé de ce soir | « fernsehprogramm » · « im fernsehen » · « tv-programm » · « fernsehen » |
| Lancer une station (dites son nom après) | « spiele » · « spiel » |
| Arrêter la radio | « radio aus » · « stopp » · « stop » · « leise » |
| Station suivante | « nächster sender » · « nächste station » · « nächster » |
| Station précédente | « vorheriger sender » · « letzter sender » · « zurück » |
| Monter le son | « lauter » |
| Baisser le son | « leiser » |

**Español** (`es`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « qué tiempo hace » · « tiempo » · « pronóstico » |
| Heure | « qué hora es » · « hora » |
| La télé de ce soir | « en la tele » · « programa de tv » · « televisión » |
| Lancer une station (dites son nom après) | « pon » · « reproduce » · « escucha » |
| Arrêter la radio | « para la radio » · « detén la radio » · « silencio » · « para » |
| Station suivante | « siguiente emisora » · « siguiente » |
| Station précédente | « emisora anterior » · « anterior » |
| Monter le son | « sube el volumen » · « más fuerte » · « más alto » · « sube » |
| Baisser le son | « baja el volumen » · « más bajo » · « baja » |

**Italiano** (`it`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « che tempo fa » · « meteo » · « previsioni » |
| Heure | « che ora è » · « ora » |
| La télé de ce soir | « stasera in tv » · « programma tv » · « in tv » · « televisione » |
| Lancer une station (dites son nom après) | « metti » · « riproduci » · « ascolta » |
| Arrêter la radio | « ferma la radio » · « silenzio » · « stop » |
| Station suivante | « stazione successiva » · « successiva » · « prossima » |
| Station précédente | « stazione precedente » · « precedente » |
| Monter le son | « alza il volume » · « più forte » · « volume su » |
| Baisser le son | « abbassa il volume » · « più piano » · « volume giù » |

**Português** (`pt`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « que tempo faz » · « previsão » · « meteorologia » |
| Heure | « que horas são » · « hora » |
| La télé de ce soir | « na televisão » · « programação » · « na tv » · « televisão » |
| Lancer une station (dites son nom après) | « põe » · « toca » · « ouve » |
| Arrêter la radio | « para a rádio » · « silêncio » · « para » |
| Station suivante | « estação seguinte » · « seguinte » |
| Station précédente | « estação anterior » · « anterior » |
| Monter le son | « aumenta o volume » · « mais alto » · « mais forte » |
| Baisser le son | « diminui o volume » · « mais baixo » · « mais fraco » |

**Português (Brasil)** (`pt-BR`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « que tempo faz » · « previsão » · « meteorologia » |
| Heure | « que horas são » · « hora » |
| La télé de ce soir | « na televisão » · « programação » · « na tv » · « televisão » |
| Lancer une station (dites son nom après) | « põe » · « toca » · « ouve » |
| Arrêter la radio | « para o rádio » · « silêncio » · « para » |
| Station suivante | « rádio seguinte » · « seguinte » · « próxima » |
| Station précédente | « rádio anterior » · « anterior » |
| Monter le son | « aumenta o volume » · « mais alto » · « mais forte » |
| Baisser le son | « diminui o volume » · « mais baixo » · « mais fraco » |

**العربية** (`ar`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « كيف حال الطقس » · « الطقس » · « توقعات » |
| Heure | « كم الساعة » · « الوقت » |
| La télé de ce soir | « برنامج التلفاز » · « على التلفاز » · « التلفزيون » |
| Lancer une station (dites son nom après) | « شغل » · « استمع » |
| Arrêter la radio | « أوقف الراديو » · « صمت » · « قف » |
| Station suivante | « المحطة التالية » · « التالي » |
| Station précédente | « المحطة السابقة » · « السابق » |
| Monter le son | « ارفع الصوت » |
| Baisser le son | « اخفض الصوت » |

**Kiswahili** (`sw`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « hali ya hewa » · « utabiri » |
| Heure | « saa ngapi » · « muda » |
| La télé de ce soir | « kwenye tv » · « televisheni » |
| Lancer une station (dites son nom après) | « cheza » · « sikiliza » |
| Arrêter la radio | « zima redio » · « kimya » · « simama » |
| Station suivante | « kituo kinachofuata » · « kinachofuata » |
| Station précédente | « kituo kilichotangulia » · « kilichotangulia » |
| Monter le son | « ongeza sauti » |
| Baisser le son | « punguza sauti » |

**Bahasa Indonesia** (`id`)

| Quoi | Vous pouvez dire |
|---|---|
| Météo | « bagaimana cuacanya » · « cuaca » · « ramalan » |
| Heure | « jam berapa » · « waktu » |
| La télé de ce soir | « acara tv » · « di tv » · « televisi » |
| Lancer une station (dites son nom après) | « putar » · « dengarkan » |
| Arrêter la radio | « matikan radio » · « diam » · « berhenti » |
| Station suivante | « stasiun berikutnya » · « berikutnya » |
| Station précédente | « stasiun sebelumnya » · « sebelumnya » |
| Monter le son | « naikkan volume » · « lebih keras » |
| Baisser le son | « turunkan volume » · « lebih pelan » |

## Ajouter vos propres phrases

Dans la case **10**, sous **Vos propres phrases**, touchez **+ Ajouter une phrase** :

1. écrivez ce que *vous* direz (par exemple *bonne nuit*, *réveille-moi*, *c'est quoi ce soir*) ;
2. choisissez ce qui doit se passer : lancer la radio (et laquelle de vos favorites), l'arrêter,
   station suivante ou précédente, monter ou baisser le volume, dire la météo ou l'heure, lire la
   télé de ce soir, ou **simplement répondre par une phrase** que vous écrivez (par exemple
   *Dors bien*) ;
3. **Enregistrez**.

Vos phrases passent toujours avant celles d'origine, et la plus longue l'emporte parmi les vôtres.
Vous pouvez en garder 50 au maximum. Elles sont stockées dans la partie `[[voice.commands]]` du
fichier de configuration :

```toml
[voice]
enabled = true

[[voice.commands]]
phrase = "bonne nuit"
action = "say"
reply = "Dors bien"

[[voice.commands]]
phrase = "réveille-moi"
action = "radio_play"
station = "960d0c25-0601-11e8-ae97-52543be04c81"   # l'uuid de la favorite ; absent = la première
```

Actions possibles : `radio_play`, `radio_stop`, `radio_next`, `radio_prev`, `volume_up`,
`volume_down`, `weather`, `time`, `tv`, `say`.

## Si ça ne marche pas

Commencez par ouvrir la page de réglages **dans le même navigateur**, boîte **Contrôle par la
voix**, et appuyez sur **Tester le micro sur cet appareil** : elle dit en mots simples ce qui
bloque (autorisation refusée, aucun micro branché, service vocal du navigateur injoignable…) et
quoi faire.

- **Pas de bouton micro à l'écran** : la case de l'étape 1 n'est pas cochée, ou Enregistrer n'a pas
  été pressé. Le bouton n'existe que lorsque la voix est enregistrée comme activée ; il apparaît
  alors dans la minute (rechargez l'écran pour le voir tout de suite).
- *« Micro indisponible »* à l'écran : il manque l'étape 3 (page sécurisée) ou 4 (autorisation).
  La page de réglages indique aussi si **cet** appareil peut écouter.
- Rien n'est compris : parlez près de la tablette et vérifiez la langue d'affichage (case 2).
- Le service de reconnaissance du navigateur a besoin d'internet ; le reste de Beranda, non.
