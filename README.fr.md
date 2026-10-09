# Beranda

*Beranda* veut dire « véranda » en indonésien : un endroit calme pour voir sa journée d'un coup d'œil.

**Transformez un Raspberry Pi et n'importe quel écran, ou une vieille tablette, en miroir connecté
ou en affichage mural** : l'heure, la météo, votre agenda, l'actualité, vos photos, la radio et la
télé de ce soir. Clair le jour, sombre la nuit. **Gratuit** : pas de compte, pas d'abonnement,
aucun service payant.

[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-regis57-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/regis57)
[![Licence : MIT](https://img.shields.io/badge/licence-MIT-blue)](#licence)
🇬🇧 [Read in English](README.md)

![Beranda la nuit](docs/screenshots/v0.14.0-display-night.png)

| | |
|---|---|
| ![Japon](docs/screenshots/v0.14.0-theme-japan.png) | ![Chine, nuit](docs/screenshots/v0.14.0-theme-china.png) |
| ![Afrique, en swahili](docs/screenshots/v0.14.0-theme-africa.png) | ![Monde arabe, de droite à gauche](docs/screenshots/v0.14.0-theme-arab.png) |

*Les captures utilisent des données de démonstration (météo, agenda et titres sont inventés).
15 thèmes, 57 langues, 243 pays. [Tout voir](docs/COUNTRIES.md).*

## Ce que vous voyez à l'écran

| | |
|---|---|
| **L'heure et la météo** | Horloge, date, météo du moment, pluie dans les 2 prochaines heures, prévisions à 7 jours et graphique sur 24 heures (température, pluie, vent, nuits). Phase de la lune, lever et coucher du soleil. |
| **Votre quotidien** | Votre agenda (Google, Apple, Outlook, Nextcloud, Proton), les jours fériés de votre pays, anniversaires et dates qui comptent, vos photos en diaporama. |
| **Le monde** | Titres de l'actualité, radio du monde (50 000 stations), programme TV de ce soir, « Ce jour-là » dans l'histoire. |
| **Petits plus** | Qualité de l'air, UV et pollens · vigilances météo officielles de votre zone · fête du jour, durée du jour et calendrier de votre pays (hégirien, lunaire chinois, ère japonaise...) · une petite deuxième horloge. **Chacun peut être désactivé.** |
| **Mains libres** | Commande vocale facultative avec le micro de la tablette : « quel temps fait-il », « mets France Inter », « station suivante ». [Mode d'emploi](docs/VOICE.fr.md) |
| **Fait pour un mur** | En hauteur ou en largeur, écran éteint la nuit, et chaque thème raconte la saison à la façon de sa culture. |

## Essayer en 2 minutes, sur votre ordinateur

```bash
git clone https://github.com/regis57/Beranda.git && cd Beranda
python3 -m venv .venv && . .venv/bin/activate && pip install .
beranda --demo
```

Ouvrez <http://localhost:8080> (l'affichage) et <http://localhost:8080/admin> (les réglages).
Il faut Python 3.11 ou plus récent. Sans `--demo`, vous avez la vraie météo et votre agenda.

## L'installer sur un Raspberry Pi

**Il vous faut** : un Raspberry Pi (le 3B+ ou plus récent est le choix confortable ; les modèles
plus anciens marchent en mode léger, voir les [limites](#ce-que-votre-raspberry-pi-peut-contenir)),
une carte microSD de 8 Go ou plus, un écran HDMI, et votre téléphone ou ordinateur sur le même Wi-Fi.

1. **Préparez la carte** avec [Raspberry Pi Imager](https://www.raspberrypi.com/software/) : choisissez
   *Raspberry Pi OS Lite (64-bit)*. Dans la fenêtre de personnalisation, donnez un nom (par exemple
   `beranda`), votre Wi-Fi, un utilisateur et un mot de passe, et activez SSH.
2. **Branchez l'écran et la carte**, allumez, attendez deux minutes.
3. **Ouvrez un terminal** sur votre ordinateur (sous Windows : *PowerShell*) et tapez
   `ssh votre-utilisateur@beranda.local`.
4. **Collez cette ligne** (5 à 15 minutes sur un Pi 3) :
   ```bash
   curl -fsSL https://raw.githubusercontent.com/regis57/Beranda/main/install.sh | sudo bash
   ```
5. **Terminez depuis votre téléphone** : l'écran affiche un QR code. Scannez-le, ou ouvrez
   `http://beranda.local:8080/admin`.

Beranda démarre ensuite tout seul à chaque allumage, en plein écran. Un souci ? Lancez `beranda doctor`.
Pas de Wi-Fi à saisir dans Imager ? Ajoutez `--with-wifi-setup` à la ligne d'installation : le Pi
propose alors son propre réseau « Beranda setup » ([comment ça marche](docs/WIFI_SETUP.md)).

<details><summary>Une vieille tablette comme écran, options de l'installateur, désinstallation</summary>

**Tablette ou téléphone comme écran** : installez avec `--no-screen` sur le Pi (ou n'importe quel
ordinateur), puis ouvrez `http://beranda.local:8080` dans le navigateur de la tablette (Chrome ou Edge
conseillés) et ajoutez la page à l'écran d'accueil. La radio et la voix utilisent **les haut-parleurs
et le micro de la tablette**.

Les options se placent après `bash -s --`, par exemple `... | sudo bash -s -- --no-screen` :
`--no-screen`, `--hostname cuisine`, `--with-wifi-setup`, `--branch NOM`, `--dry-run`.

L'installateur ajoute Python, des polices pour toutes les écritures, Cage et Chromium (le navigateur
plein écran), un utilisateur `beranda` (jamais root) et trois services : le serveur, l'affichage plein
écran, et un petit service root qui ne fait que les quatre boutons de la page de réglages (mise à
jour, redémarrage de l'écran, redémarrage du Pi, tout recommencer). Relancez la ligne pour mettre à
jour ou réparer.

Pour le retirer : `sudo /opt/beranda/src/uninstall.sh` (ajoutez `--purge` pour effacer aussi vos réglages).
</details>

## Réglez-le depuis votre téléphone

Ouvrez `http://beranda.local:8080/admin`. Un menu ☰ mène à chaque section ; chacune a un lien
**Besoin d'aide ?** en mots simples. L'essentiel, dans l'ordre :

1. **Où êtes-vous ?** Tapez votre ville et choisissez-la. Météo, soleil et lune suivent.
2. **Pays et langue.** Jours fériés, premier jour de la semaine et langue de l'écran.
3. **Apparence.** Choisissez un thème ; l'aperçu se met à jour en direct.
4. **Extras de l'écran principal.** Activez ou retirez le graphique, la qualité de l'air, les vigilances, l'éphéméride et la deuxième horloge.
5. **Agenda, actualité, photos, radio, TV, voix.** Tout est facultatif, chacun dans sa section.
6. **Utilisateur avancé** (rarement utile). Changer le port `8080` si un autre programme l'utilise déjà, ou repartir de zéro. La page détaille ce qui change avant que vous confirmiez.

Appuyez sur **Enregistrer** : l'écran suit en moins d'une minute. Détails : [docs/USAGE.md](docs/USAGE.md).

### Relier votre agenda

Beranda lit votre agenda grâce à un **lien** privé (une adresse « iCal / ICS »). Il ne fait que lire,
ne modifie jamais rien et ne demande jamais votre mot de passe. Collez le lien dans la section
agenda et appuyez sur **Tester**.

| Agenda | Où trouver le lien | Guide officiel |
|---|---|---|
| **Google Agenda** | Paramètres → votre agenda → *Intégrer l'agenda* → *Adresse secrète au format iCal* | [aide](https://support.google.com/calendar/answer/37648?hl=fr) |
| **Apple iCloud** | icloud.com/calendar → ⓘ à côté du calendrier → *Calendrier public* → *Copier* | [aide](https://support.apple.com/fr-fr/guide/icloud/share-a-calendar-mm6b1a9479/icloud) |
| **Outlook / Microsoft 365** | Paramètres → Calendrier → Calendriers partagés → *Publier un calendrier* → copiez le lien **ICS** | [aide](https://support.microsoft.com/fr-fr/outlook/share-your-calendar-in-outlook-com) |
| **Nextcloud** | Agenda → *Partager le lien* → copiez (Beranda le convertit) | [manuel](https://docs.nextcloud.com/server/stable/user_manual/en/groupware/calendar.html#publishing-a-calendar) |
| **Proton Calendar** | Offres payantes : Paramètres → Calendriers → *Partager avec tout le monde* → *Copier le lien* | [aide](https://proton.me/support/share-calendar-via-link) |

**Gardez ce lien pour vous** : toute personne qui l'a peut lire vos rendez-vous. Il n'est conservé que
sur votre Pi. S'il fuite, créez-en un nouveau depuis la même page et l'ancien cesse de marcher.

### L'actualité

« Choisir pour moi » (par défaut) prend l'actualité de votre ville, deux médias de votre pays et un
média international dans votre langue. Ou choisissez parmi 140 flux gratuits de tous les continents,
ou collez n'importe quel lien RSS. Seulement des titres : pas d'images, pas de publicité, pas de
pistage. Chaque flux du catalogue est vérifié chaque semaine.

## Ce que votre Raspberry Pi peut contenir

Chaque agenda, flux ou chaîne ajouté est un téléchargement de plus à garder en mémoire, et les petites
cartes en ont peu. Beranda reconnaît votre carte et sa mémoire, et fixe le **maximum** de chaque
liste (la page de réglages vous le dit quand vous l'atteignez, au lieu de ralentir). Rien à régler.

| Carte | Mémoire | Profil | Agendas | Sources d'actualité* | Chaînes TV | Stations radio | Dates | Photos | Phrases vocales |
|---|---|---|---|---|---|---|---|---|---|
| Pi 2, Zero 2 W | 0,5 – 1 Go | léger | 3 | 8 | 15 | 15 | 100 | 200 | 20 |
| **Pi 3 / 3B+, Pi 4** | 1 Go | **standard** | 10 | 20 | 40 | 30 | 200 | 500 | 50 |
| Pi 4, Pi 5 | 2 Go | confortable | 15 | 30 | 60 | 50 | 400 | 800 | 80 |
| Pi 4, Pi 5, Pi 400 | 4 Go | confortable + | 25 | 50 | 100 | 80 | 800 | 1 500 | 120 |
| Pi 4, Pi 5 | 8 Go ou plus | maximum | 40 | 80 | 150 | 120 | 1 500 | 3 000 | 200 |

*\*médias et vos propres flux RSS ensemble. Un ordinateur qui n'est pas un Raspberry Pi est jugé sur sa mémoire.*

Ce que **l'écran** affiche est plafonné à part, et le reste défile simplement : 3 titres à la fois
(un nouveau lot toutes les 12 s), jusqu'à 10 chaînes TV par page, 8 lignes d'agenda, 3 vigilances, 3 pollens.

Ces chiffres sont une estimation prudente, pas un banc d'essai : seules quelques cartes ont été
essayées par l'auteur. Vous savez mieux ? Forcez un profil dans `config.toml` (`[limits]` /
`profile = "plus"`) ou dites-nous ce que votre carte a supporté dans une
[issue](https://github.com/regis57/Beranda/issues).

## Vie privée

- La page de réglages ne s'ouvre que depuis votre réseau à la maison, et peut demander un code PIN. N'ouvrez pas le port 8080 vers internet.
- Vos réglages restent sur votre Pi. Il ne parle qu'aux services que vous utilisez : Open-Meteo
  (météo, air), votre agenda, les flux choisis et, si vous les activez, GDELT (« actualité de ma ville »
  envoie le nom de votre ville), MeteoAlarm (vigilances), nameday.abalin.net (fêtes), Wikipédia,
  Radio Browser et votre guide TV.
- La voix utilise le service de reconnaissance de votre navigateur (Chrome et Edge envoient le son à leur éditeur). Beranda ne garde rien.

## Aide, contribuer, soutenir

- **Bloqué ?** `beranda doctor`, [docs/USAGE.md](docs/USAGE.md), ou [ouvrez une issue](https://github.com/regis57/Beranda/issues).
- **Contribuer** : `pip install -e ".[dev]"`, puis `pytest` et `ruff check src tests scripts`. Une nouvelle langue, c'est un fichier JSON dans `src/beranda/web/i18n/`. [Feuille de route](docs/ROADMAP.md).
- **Soutenir** : Beranda reste libre et gratuit. S'il égaye votre mur, [un café](https://buymeacoffee.com/regis57) est toujours le bienvenu.

## Crédits

Météo et qualité de l'air par [Open-Meteo](https://open-meteo.com/) (CC BY 4.0 ; air par
[Copernicus CAMS](https://atmosphere.copernicus.eu)). Vigilances par [MeteoAlarm](https://meteoalarm.org).
Fêtes par [nameday.abalin.net](https://nameday.abalin.net). Actualité locale par [GDELT](https://www.gdeltproject.org/).
Radio par [Radio Browser](https://www.radio-browser.info). « Ce jour-là » par [Wikipédia](https://www.wikipedia.org).
Jours fériés par la bibliothèque [holidays](https://github.com/vacanza/holidays). Les titres appartiennent à leurs éditeurs.

## Licence

MIT.
