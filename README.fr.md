# Beranda

*Beranda* veut dire « véranda » en indonésien : un endroit calme pour voir sa journée d'un coup d'œil.

Un tableau de bord pour miroir connecté ou vieille tablette, fait pour un **Raspberry Pi 3B+ ou
plus récent** : l'heure, la météo et la pluie chez vous, la lune, votre agenda, les jours fériés
et les dates qui comptent, et une ligne de titres d'actualité. Clair le jour, sombre la nuit.
Gratuit : pas de compte, pas d'abonnement, pas d'API payante.

> **État : alpha (v0.5).** L'installateur est testé automatiquement sur une machine Debian/Ubuntu
> neuve avec systemd ; la partie plein écran n'a pas encore été essayée sur un vrai Raspberry Pi.
> Si vous l'essayez, dites-nous comment ça s'est passé dans une « issue ».
> 🇬🇧 [Read in English](README.md)

| | |
|---|---|
| ![Japon](docs/screenshots/v0.3.0-japan-light.png) | ![Chine, nuit](docs/screenshots/v0.4.0-china-night.png) |
| ![Afrique (swahili)](docs/screenshots/v0.4.0-africa-light.png) | ![Monde arabe (de droite à gauche)](docs/screenshots/v0.4.0-arab-light.png) |
| ![Amérique du Nord](docs/screenshots/v0.4.0-america-light.png) | ![Créole (créole haïtien)](docs/screenshots/v0.4.0-creole-light.png) |

*Les captures utilisent des données de démonstration : météo, agenda et titres sont inventés ;
la lune, le soleil, les saisons et les jours fériés sont réels.* [Toutes les captures](docs/screenshots/)

## Ce que vous obtenez

- **L'heure et la date** dans votre langue.
- **La météo** : maintenant, la pluie dans les deux prochaines heures, les prévisions à 7 jours (Open-Meteo, gratuit).
- **La lune et le soleil** : phase de la lune, lever et coucher du soleil, tout est calculé sur le Pi.
- **Le calendrier** : votre agenda Google, Apple, Outlook, Nextcloud ou Proton (en lecture seule),
  les jours fériés de votre pays et vos propres dates (naissances, souvenirs, anniversaires).
- **L'actualité** : une ligne de titres en bas de l'écran. L'actualité de votre ville, les médias
  de votre pays, un média international dans votre langue, ou n'importe quel flux RSS.
- **15 thèmes**, chacun avec sa façon de raconter la saison : Japon (72 micro-saisons), Chine
  (24 termes solaires et date lunaire), Inde (ṛtu et tithi), Monde arabe (date de l'hégire),
  Afrique (un proverbe swahili par jour), Indonésie (mangsa javanais), Océanie (saisons
  tahitiennes des Pléiades), Créole (carême ou hivernage, un proverbe créole), Amérique du Nord
  (noms des pleines lunes), France (calendrier républicain), Allemagne (saisons de la nature),
  Espagne, Italie et Portugal (proverbe du mois), Brésil (dicton du jour, saisons de l'hémisphère sud).
- **48 langues** pour l'écran, dont l'arabe, l'hébreu, le persan et l'ourdou écrits de droite à
  gauche ; **243 pays et territoires** avec leurs jours fériés, leur premier jour de la semaine
  et leurs médias. [Tous les pays, toutes les langues](docs/COUNTRIES.md).
- **Fait pour le mur** : fonctionne en hauteur (portrait) ou en largeur, éteint l'écran la nuit,
  affiche un QR code pour le régler depuis votre téléphone au premier démarrage.
- **Une page de réglages** pour votre téléphone, en mots simples, avec de l'aide pas à pas.
- **Carrousel photo** : pointez-le vers un dossier sur le Pi et il affiche ces photos en plein
  écran, en alternance avec le tableau de bord. Remplissez le dossier avec
  [rclone](https://rclone.org) (Google Drive, Dropbox, OneDrive, albums partagés iCloud et bien
  d'autres) ou [Syncthing](https://syncthing.net) (la pellicule de votre téléphone) — Beranda ne
  fait que lire ce qui s'y trouve déjà, sans jamais avoir son propre compte dans le cloud.

## L'essayer sur votre ordinateur (2 minutes)

Il faut Python 3.11 ou plus récent.

```bash
git clone https://github.com/regis57/Beranda.git
cd Beranda
python3 -m venv .venv && . .venv/bin/activate
pip install .
beranda --demo
```

Ouvrez <http://localhost:8080> pour l'affichage et <http://localhost:8080/admin> pour les réglages.
Arrêtez avec Ctrl+C. Sans `--demo`, vous avez la vraie météo et votre agenda.

## L'installer sur un Raspberry Pi (une seule ligne)

**Ce qu'il faut** : un Raspberry Pi 3B+ ou plus récent, une carte microSD (8 Go ou plus), un
écran HDMI, et un téléphone ou un ordinateur sur le même Wi-Fi.

1. **Préparer la carte.** Installez [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
   sur votre ordinateur et choisissez *Raspberry Pi OS Lite (64-bit)*. Quand Imager propose de
   personnaliser le système, donnez un nom au Pi (par exemple `beranda`), le nom et le mot de
   passe de votre Wi-Fi, un nom d'utilisateur et un mot de passe, et activez SSH.
   [Guide officiel](https://www.raspberrypi.com/documentation/computers/getting-started.html).
2. **Démarrer le Pi** avec la carte et l'écran branchés, attendez deux minutes.
3. **Vous y connecter** depuis votre ordinateur : ouvrez un terminal (sous Windows : *PowerShell*)
   et tapez `ssh votre-utilisateur@beranda.local`.
   [Guide officiel](https://www.raspberrypi.com/documentation/computers/remote-access.html).
4. **Installer Beranda** en collant cette ligne (5 à 15 minutes sur un Pi 3) :
   ```bash
   curl -fsSL https://raw.githubusercontent.com/regis57/Beranda/main/install.sh | sudo bash
   ```
5. **Le régler depuis votre téléphone** : l'écran affiche une adresse et un QR code. Scannez-le,
   ou ouvrez `http://beranda.local:8080/admin`, et suivez les trois étapes en haut de la page.

C'est tout : Beranda démarre tout seul à chaque allumage, en plein écran. Depuis la page de
réglages vous pourrez ensuite **mettre à jour**, **redémarrer l'écran**, **redémarrer le Pi**,
**tourner l'image** pour un écran accroché en hauteur et **éteindre l'écran la nuit**.

<details><summary>Ce que fait l'installateur, et ses options</summary>

Il installe Python, les polices Noto (pour toutes les écritures), Cage et Chromium (le navigateur
plein écran) ; crée un utilisateur `beranda` qui fait tout tourner (jamais root) ; met Beranda
dans `/opt/beranda` et vos réglages dans `/etc/beranda` ; et installe trois services : le serveur,
l'écran plein écran, et un petit service root qui n'exécute que les trois demandes de la page de
réglages (mise à jour, redémarrage de l'écran, redémarrage du Pi). Relancez la ligne pour réparer
ou mettre à jour.

Les options se placent après `bash -s --`, par exemple `... | sudo bash -s -- --no-screen` :
`--no-screen` (serveur seul, pour l'afficher sur une tablette ou un autre appareil),
`--hostname cuisine` (renomme le Pi : `http://cuisine.local:8080/admin`), `--branch NOM`, `--dry-run`.

Un souci ? `beranda doctor` vérifie tout et dit quoi corriger.
Pour le retirer : `sudo /opt/beranda/src/uninstall.sh` (ajoutez `--purge` pour effacer aussi vos réglages).
</details>

## Relier votre agenda

Beranda lit votre agenda grâce à un **lien** privé (une adresse « iCal » ou « ICS »). Il ne fait
que lire : il ne modifie jamais rien et ne demande jamais votre mot de passe. Collez le lien dans
*Réglages → 4. Votre agenda* et appuyez sur **Tester**. La page de réglages montre ces mêmes étapes
sous la case, avec le guide officiel dans votre langue.

| Agenda | Où trouver le lien | Guide officiel |
|---|---|---|
| **Google Agenda** | Sur un ordinateur : ⚙ → Paramètres → à gauche, cliquez sur votre agenda → *Intégrer l'agenda* → copiez *Adresse secrète au format iCal*. | [Aide Google](https://support.google.com/calendar/answer/37648?hl=fr) |
| **Apple iCloud** | Sur icloud.com/calendar : ⓘ à côté du calendrier → activez *Calendrier public* → *Copier*. | [Aide Apple](https://support.apple.com/fr-fr/guide/icloud/share-a-calendar-mm6b1a9479/icloud) |
| **Outlook / Microsoft 365** | Outlook sur le web : ⚙ Paramètres → Calendrier → Calendriers partagés → *Publier un calendrier* → choisissez-le → *Publier* → copiez le lien **ICS**. | [Aide Microsoft](https://support.microsoft.com/fr-fr/outlook/share-your-calendar-in-outlook-com) |
| **Nextcloud** | Application Agenda : menu de l'agenda → *Partager le lien* → copiez. Beranda transforme tout seul le lien de partage en bonne adresse. | [Manuel Nextcloud](https://docs.nextcloud.com/server/stable/user_manual/en/groupware/calendar.html#publishing-a-calendar) |
| **Proton Calendar** | Offres payantes : Paramètres → Calendriers → votre calendrier → *Partager avec tout le monde* → *Créer un lien* → *Copier le lien*. | [Aide Proton](https://proton.me/support/share-calendar-via-link) |

**Gardez ce lien pour vous** : toute personne qui l'a peut voir vos rendez-vous. Beranda ne le
garde que sur le Pi, dans un fichier lisible par vous seul. S'il fuite, créez-en un nouveau depuis
la même page (l'ancien cesse de marcher). Les liens qui commencent par `webcal://` marchent aussi.

## Les titres de l'actualité

Une ligne en bas de l'écran affiche les derniers titres, un par un, avec le nom du média.
Seulement des titres : pas d'images, pas de publicité, pas de pistage, pas de compte.

- **« Choisir pour moi »** (par défaut) : l'actualité qui cite votre ville (trouvée par
  [GDELT](https://www.gdeltproject.org/), un index libre et gratuit de la presse mondiale), deux
  médias de votre pays et un média international dans votre langue.
- **Choisir vous-même** parmi 140 flux gratuits de tous les continents : radios et télévisions
  publiques et grands journaux d'Europe, des Amériques, d'Afrique, d'Asie et d'Océanie, et services internationaux (BBC, DW,
  France 24, RFI, ONU Info, Al Jazeera...).
- **Ajouter n'importe quel flux** : la plupart des sites d'information publient un lien RSS (cherchez
  le logo orange RSS, ou essayez l'adresse du site suivie de `/rss` ou `/feed`). Collez-le et
  appuyez sur **Tester**.

Chaque flux du catalogue est vérifié automatiquement chaque semaine.

## Vie privée et sécurité

- La page de réglages ne s'ouvre que depuis votre réseau à la maison, et peut demander un code PIN.
- Vos réglages restent sur le Pi. Le Pi ne parle qu'aux services que vous utilisez : Open-Meteo
  (météo), votre agenda, les flux d'actualité choisis, et GDELT si « actualité de ma ville » est
  activé (il envoie alors le nom de votre ville).
- N'ouvrez pas le port 8080 du Pi vers internet sur votre box.

## Pour contribuer

`pip install -e ".[dev]"`, puis `pytest` et `ruff check src tests scripts`.
Captures : `python scripts/screenshot.py` et `python scripts/screenshot_admin.py`.
Une nouvelle langue, c'est un fichier JSON dans `src/beranda/web/i18n/` (et si possible `i18n/admin/`).
Voir la [feuille de route](docs/ROADMAP.md).

## Crédits

Météo par [Open-Meteo](https://open-meteo.com/) (CC BY 4.0). Actualité locale par
[GDELT](https://www.gdeltproject.org/). Jours fériés par la bibliothèque
[holidays](https://github.com/vacanza/holidays). Les titres appartiennent à leurs éditeurs.

## Licence

MIT.
