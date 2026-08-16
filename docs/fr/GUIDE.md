# Dinoer — guide de l'opérateur

Version 1.11 — août 2026 (v1.0.0) — surface réalignée sur la reconstruction
Dinoer : aucune capture d'écran, aucun Set-of-Mark, aucun `watch.py` ;
l'agent lit l'arbre d'accessibilité et pilote les actions Playwright sur des
sélecteurs CSS.

*Également disponible en anglais, allemand et espagnol sous la racine
`docs/`, `docs/de/` et `docs/es/`.*

---

## Pourquoi Dinoer — ce que vous déléguez réellement

### Le problème que Dinoer résout

Quand vous travaillez avec un LLM sur une application web, une asymétrie de
perception se produit : le modèle lit le code, exécute des commandes,
observe une sortie textuelle — mais il ne voit pas l'interface que voient vos
utilisateurs. Vous, si.

Cette asymétrie crée une forme spécifique d'anxiété : vous ne savez pas si ce
que le modèle décrit correspond à ce que vous verriez dans un navigateur.
Pour en être sûr, vous devez soit le croire sur parole, soit vérifier
vous-même.

Dinoer résout ce problème en donnant au modèle la même vue structurée que
celle que vous obtiendriez dans un navigateur : l'arbre d'accessibilité, lu
au travers d'un vrai Chromium headless, plus les valeurs du DOM qu'il extrait
avec `evaluer`. Vous ne prenez plus le modèle au mot — vous observez le même
état que lui.

```
 Navigateur (Chromium headless)
        │  Playwright le pilote — clic, remplissage, navigation
        ▼
 shot.py / rpa.py
        │  lit l'état résultant du DOM au travers de vues parallèles
        ├──▶ a11y_tree            arbre d'accessibilité, texte
        ├──▶ evaluations          valeurs extraites via `evaluer`
        └──▶ fichier de session   cookies seulement (--sauver-session)
        │
        ▼
 boussole + JSON sur stdout — l'état, tel que l'opérateur peut l'auditer
        │
        ▼
 Vous (le modèle) : lire → analyser → décider → agir → boucler
```

### Ce que vous déléguez

Dinoer vous permet de déléguer une **vérification répétitive et propice au
contrôle** :

- vérifier que 20 pages d'un site répondent correctement après un déploiement
- confirmer qu'un formulaire de connexion fonctionne sur la bonne interface
- s'assurer qu'un déploiement n'a pas cassé la structure d'une vue critique
- piloter un panneau d'administration par la même interface qu'un humain
  utiliserait

Sans Dinoer, ces vérifications sont sous votre responsabilité. Avec Dinoer,
le modèle les effectue et rapporte le résultat — avec la preuve JSON à
l'appui.

### Ce que vous conservez

Vous conservez la **validation de sens de haut niveau** : décider si le
résultat que présente le modèle est acceptable, cohérent avec vos attentes,
et conforme à ce que vos utilisateurs devraient voir. Cette décision reste la
vôtre.

### Navigation respectueuse (v1.15.0)

Dinoer ne déguise pas son identité pour contourner la détection de bots.
`--stealth` retire les marqueurs techniques automatiques
(`navigator.webdriver`) qui bloquent les navigateurs headless quelle que soit
l'intention — cela ne change ni l'IP de l'opérateur, ni son identité, ni le
fait que l'exécution est déclarée. En contrepartie, chaque exécution rapporte
sa propre empreinte (`respect` : pages visitées, actions exécutées, durée)
et respecte des délais de courtoisie et des plafonds configurables
(`dinoer.conf [navigation]`). Le droit de naviguer et le devoir de naviguer
de façon mesurable sont traités comme inséparables — voir
`docs/RETOUR_EXPERIENCE.md` FR-77/FR-78/FR-79 pour le contexte terrain qui a
façonné ce choix.

**Cibles locales — le délai de courtoisie n'est pas une doctrine, c'est une
valeur par défaut (v1.19.0) :** le `min_action_delay_ms: 800` livré par
défaut protège une première exécution non configurée contre l'internet
public — il n'a aucun sens contre votre propre machine de
développement/production. Réglez-le à `0` dans votre `dinoer.conf` local pour
le débogage local ; voir `docs/MANUEL.md` section 3b.

### Quand Dinoer est le bon outil

| Cas d'usage | Dinoer adapté ? |
|---|---|
| Validation structurelle après déploiement | ✓ oui |
| Diagnostiquer une interaction cassée | ✓ oui |
| Navigation et saisie de formulaire (~30 s max) | ✓ oui |
| Déléguer des vérifications répétitives | ✓ oui |
| Opération serveur longue (clonage ~2–5 min) | ✗ non — timeout Playwright |
| Suppression ou mutation en masse | ✗ non — préférez un appel API direct |
| Flux nécessitant un retour arrière | ✗ non — Dinoer ne peut pas annuler |

---

**Ce document est rédigé pour la personne qui opère Dinoer.**

Il complète `GUIDE_LLM.md` (destiné aux modèles) avec des exemples concrets,
des procédures pas à pas, et des rappels sur les points de blocage courants.

---

## Cas d'usage de démonstration

Les cas ci-dessous illustrent ce à quoi peut ressembler, en pratique, une
session agent-plus-Dinoer. Ils sont destinés à être évalués dans votre propre
contexte, pas présentés comme une recommandation d'en adopter un en
particulier. Seul le cas 1 est livré comme scénario exécutable ; les autres
sont volontairement narratifs, et chacun explique pourquoi sous son propre
titre.

### Cas 1 — dépannage CSS/JS local

Commité comme un scénario réel, exécutable :
`scenarios/exemples/depannage_local.json`. Il diagnostique un décalage de
mise en page ou une interaction bloquée sur une interface servie localement —
une sonde rapide lisant `erreurs_js`/`erreurs_console` et l'arbre
d'accessibilité, puis validant le correctif avec `rpa.py
--replay-verifier` contre une référence capturée avant la régression.
Exécutez-le directement :

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/exemples/depannage_local.json \
  --guide-version 1.6
```

### Cas 2 — comparer des composants matériels entre boutiques

Un agent chargé de comparer le prix et le stock d'un composant sur plusieurs
boutiques en ligne pourrait composer Dinoer avec un outil séparé de
découverte d'URL (une instance de recherche locale, par exemple) pour
trouver des pages boutique candidates, puis utiliser Dinoer en mode lecture
seule avec des actions `evaluer` pour extraire prix/stock/spécifications de
chaque page, et enfin comparer lui-même les résultats.

**Non livré comme scénario commité, délibérément :** nommer une boutique
précise dans un scénario public et versionné est une décision qui vous
appartient, pas un défaut que ce projet devrait prendre à votre place. Cela
porte aussi un vrai risque de fragilité — un scénario public ciblant un site
commercial nommé peut échouer des mois plus tard quand la posture anti-bot de
ce site change (39 % des sites commerciaux échantillonnés dans
`docs/RETOUR_EXPERIENCE.md` FR-77 ont renvoyé un blocage immédiat), ce qui
décrédibilise l'exemple plus qu'il ne l'aide. Si vous construisez cette
composition vous-même, notez que tout outil de découverte d'URL que vous
associez à Dinoer (une instance de recherche locale ou autre) n'est pas un
composant de Dinoer — c'est une pièce séparée que l'agent compose par
dessus.

### Cas 3 — explorer et résumer une documentation technique (applications monopages)

Un agent chargé de produire un guide d'intégration pour un site de
documentation construit en application monopage pourrait utiliser `rpa.py`
avec `attendre_reseau_calme` pour laisser le routage côté client se
stabiliser, extraire l'arbre d'accessibilité pour cartographier la structure
de la page, puis parcourir récursivement les blocs de code avec `evaluer`
pour en tirer le contenu exact, et enfin synthétiser le matériau collecté en
un guide.

**Non livré comme scénario commité, pour la même raison que le cas 2** —
nommer un site de documentation précis (ou, pire, un fournisseur de paiement
précis dont la documentation se trouve être l'exemple de travail) est un
engagement commercial et réputationnel que ce projet ne devrait pas prendre
par défaut, et le même risque de fragilité WAF s'applique à un scénario
public épinglé sur une cible réelle.

### Cas 4 — configurer un tableau de bord d'observabilité ou d'analytique auto-hébergé

Un opérateur mettant en place un tableau de bord de supervision ou
d'analytique web auto-hébergé derrière un reverse proxy peut utiliser Dinoer
pour piloter l'interface elle-même — créer un tableau de bord, brancher une
source de données, régler une règle d'alerte — de la même façon que
n'importe quel autre panneau d'administration se configure, plutôt que
d'éditer des fichiers à la main pour des étapes que l'UI est censée gérer.
Cela inclut des cibles situées derrière un défi HTTP Basic Auth au niveau
réseau (`--http-credentials`, v1.21.0) — confirmé contre une interface
d'administration réelle protégée par Caddy, pas seulement une fixture
synthétique : les identifiants stockés ont répondu au défi dès la première
tentative.

**Non livré comme scénario commité** — la disposition du tableau de bord et
les noms de sources de données sont spécifiques à l'infrastructure d'un
opérateur, et inventer un équivalent synthétique dupliquerait ce que la
fixture locale du cas 1 couvre déjà pour la régression structurelle, pas pour
ce type de travail de configuration guidée en plusieurs étapes.

### Cas 5 — administrer de bout en bout une plateforme de billetterie

Dinoer utilisé sur plusieurs sessions pour configurer et exploiter une
véritable installation de billetterie auto-hébergée — mise en place
d'événement, catégories de billets, domaine personnalisé, et l'outillage de
scan/check-in du jour même — au travers de la même interface web qu'un
administrateur humain utiliserait. De la friction réelle a été rencontrée et
résolue au passage (gestion de session, bizarreries de liste déroulante, une
invite de permission bloquant une étape non surveillée) — pas une success
story sans friction, ce qui fait partie de ce qui en fait un exemple utile :
les obstacles étaient des obstacles d'automatisation web ordinaires, rien de
spécifique à Dinoer.

**Non livré comme scénario commité** — une configuration de billetterie
touche à la facturation et à des spécificités de lieu propres à l'opérateur,
même raisonnement que le cas 2.

### Cas 6 — suivre un agenda d'événements régional

Un usage simple de sonde sémantique : demander à un agent de vérifier un
agenda d'événements local pour les prochaines manifestations, sans savoir à
l'avance quelle page détient la réponse. Le mode lecture seule de Dinoer
combiné à l'arbre d'accessibilité permet à l'agent de parcourir et de
rapporter en une poignée de requêtes — aucun modèle de vision nécessaire pour
ce type de tâche pilotée par le texte. Une session a aussi produit un exemple
propre et réel du comportement de faux positif documenté du signal WAF : une
page s'est chargée normalement (contenu riche, aucun captcha, aucun
interstitiel) alors que `respect.waf_bloquants` s'est quand même déclenché, à
cause d'une ressource tierce non liée sur la page correspondant à un
mot-clé de détection — résolu en environ une minute en lisant l'arbre
d'accessibilité déjà présent dans la même réponse, exactement comme
l'anticipe la règle du guide « un signal, jamais un verrou ».

**Non livré comme scénario commité** — un site d'événements régional précis
n'est pas une cible publique stable et reproductible, et en nommer un
publiquement relève du choix de l'opérateur, pas d'un défaut du projet.

### Cas 7 — tester l'accès réel à des sites e-commerce sous navigation respectueuse

Une observation récurrente et honnête issue de sessions réelles : utilisé
avec respect (délais limités, plafonds de pages/actions, `--stealth` actif,
aucune tentative de forcer l'accès au-delà d'un blocage réel), Dinoer lancé
contre un éventail de sites e-commerce constate qu'une large part des
grandes plateformes renvoie un blocage pur et simple — HTTP 403, ou une
requête qui ne se termine jamais — quelle que soit la courtoisie du trafic.
Ce n'est pas un défaut de Dinoer à corriger : la posture anti-bot est le
choix propre du site, et Dinoer ne cherche pas à la vaincre (voir
« navigation respectueuse » ci-dessus). En pratique : pour des tâches de
comparaison d'achats contre de grandes plateformes commerciales, attendez-vous
à une part significative d'impasses, et traitez un signal de blocage
(`respect.waf_bloquants`) comme une information à contourner, pas une erreur
à réessayer.

Une distinction à garder en tête : un écran de vérification invisible qui ne
se résout jamais et ne présente rien sur quoi agir (pas de case à cocher, pas
de défi image) est différent d'un CAPTCHA interactif. Ce dernier est
légitime à résoudre honnêtement — un agent opérant pour un humain nommé,
depuis l'IP propre de cet humain, n'est pas le « robot » que la question
vise. Le premier n'offre simplement aucune porte à ouvrir du côté de l'agent,
et forcer le passage (rotation d'IP, usurpation d'empreinte TLS) sort du
périmètre de ce que fait Dinoer.

**Non livré comme scénario commité, et sans nommer délibérément les
plateformes concernées** — voir le raisonnement sur la fragilité WAF sous le
cas 2 : une table datée de blocage/non-blocage liée à des sites commerciaux
nommés se périme et sape son propre propos plus vite qu'elle ne l'illustre.
`docs/RETOUR_EXPERIENCE.md` FR-77 documente le même schéma à l'échelle d'un
panel (39 % de taux de blocage immédiat).

---

## Prérequis avant de commencer

```bash
# 1. Vérifier que Dinoer répond
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://example.com --a11y
# → doit renvoyer {"succes": true, ...}

# 2. Vérifier que le répertoire chiffré est monté (si gocryptfs)
ls ~/Vaults/Dinoer/
# → doit montrer des fichiers .json, pas du contenu chiffré

# 3. Vérifier les identifiants pour un domaine
/opt/dinoer/venv/bin/python -c "
import sys; sys.path.insert(0, '/opt/dinoer')
from lib.repertoire_chiffre import lire_credential
print('OK' if lire_credential('target.local', 'password') else 'EMPTY')
"
```

---

## Configuration des identifiants par projet

Chaque projet peut avoir son propre répertoire d'identifiants. Deux méthodes :

**Méthode 1 — variable d'environnement directe (ponctuelle) :**

```bash
DINOER_SECRETS_DIR=~/Vaults/MonProjet \
  /opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url …
```

**Méthode 2 — fichier `.dinoer.conf` de projet (recommandé pour les projets
récurrents) :**

```bash
# Créer le fichier à la racine du projet
echo '{"secrets_dir": "../MonProjet-secrets"}' > ~/git/MonProjet/.dinoer.conf

# Puis préfixer chaque invocation (ou exporter en début de session shell)
export DINOER_CONF=~/git/MonProjet/.dinoer.conf
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url …
```

Le `secrets_dir` dans `.dinoer.conf` peut être un chemin relatif — il est
résolu par rapport à l'emplacement du fichier `.dinoer.conf`.

---

## Capturer une page et l'analyser

```bash
# Lire l'état de la page (lecture seule)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y
# → renvoie url_courante, titre_page, a11y_tree dans le JSON
```

**Ce que vous obtenez :**
- `boussole.url_courante` + `boussole.titre_page` : URL et titre effectifs
  après navigation
- `a11y_tree` : structure de la page en texte (titres, champs, boutons)
- `etat.pret_a_agir` + `etat.raisons` : frictions perçues, pour que le
  modèle les contourne

---

## Automatiser un formulaire de connexion

**Étape 1** — préparer le fichier d'identifiants.

Le fichier d'identifiants est nommé `<hostname>.json` où `hostname` = le
résultat de `urlparse(url).hostname`. Pour `https://app.example.com/`, le
fichier est `app.example.com.json`.

```json
{"username": "admin@example.com", "password": "mon-secret"}
```

**Étape 2** — explorer la page de connexion.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/login/ --a11y
```

Lisez `a11y_tree` pour identifier les sélecteurs de champs.

**Étape 3** — écrire le scénario.

```bash
cat > /tmp/login.json << 'EOF'
{
  "nom": "app_login",
  "url": "https://app.example.com/login/",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".user-logged-in"}
  ]
}
EOF
```

**Étape 4** — exécuter.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /tmp/login.json
```

---

## Valider plusieurs pages en une seule invocation

Pour vérifier N pages d'un site authentifié sans rejouer la connexion à
chaque fois :

```bash
cat > /tmp/audit.json << 'EOF'
{
  "nom": "audit_pages",
  "url": "https://app.example.com/login/",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".dashboard-main"},
    {"type": "naviguer",     "url": "https://app.example.com/dashboard/"},
    {"type": "attendre_navigation"},
    {"type": "naviguer",     "url": "https://app.example.com/settings/"},
    {"type": "attendre_navigation"}
  ]
}
EOF
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py --scenario /tmp/audit.json
```

---

## Extraire une valeur de la page

Pour lire une chaîne de texte, un compteur, ou toute valeur du DOM :

```bash
cat > /tmp/extract.json << 'EOF'
[{"type": "evaluer", "script": "document.title"}]
EOF
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --actions /tmp/extract.json
# → résultat dans evaluations[0].valeur
```

Pour du texte documentaire nettoyé (balises de bruit et de formulaires
retirées), utilisez plutôt `extraire_texte` — la sortie est une structure
`titre`/`texte`/`url`/`date_capture` qu'un agent de synthèse peut consommer
directement.

**Important** : écrivez toujours les scripts JS dans un fichier
`--actions`, jamais en ligne avec `--action` (le shell corrompt les
guillemets imbriqués).

---

## Mettre en place une surveillance structurelle continue (v1.18.0)

Dinoer n'a aucun pipeline visuel — la surveillance est *structurelle* : elle
vérifie le code de statut de la page, le compte d'éléments DOM et les
résultats d'évaluation JS. C'est moins coûteux qu'un diff d'image et capture
une classe de régression différente (un champ de formulaire disparu avec une
mise en page inchangée, par exemple).

```bash
# 1. Sauvegarder une référence structurelle, une fois
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/mon-scenario.json \
  --sauver-verifier-reference /opt/dinoer/references/mon-scenario.ref.json

# 2. Une passe de vérification-et-alerte
bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/mon-scenario.json \
  --reference /opt/dinoer/references/mon-scenario.ref.json \
  --ntfy-topic dinoer-monitoring
```

Silencieux lorsqu'il est stable, il s'active avec une seule exécution `ntfy` lorsqu'une régression est détectée. Planifiez-le vous-même avec cron — le script effectue un seul passage et se termine, il ne boucle pas.
Sur la branche git-clone, `scripts/*.sh` n'est jamais déployé vers `/opt/dinoer/`,
donc l'entrée cron ci-dessous s'exécute à partir du code source Git, en tant que votre propre utilisateur (et non le compte de service `dinoer`, qui ne peut pas accéder à `~/git/Dinoer/Dinoer/` ). Sur la
branche `.deb`, les trois scripts sont installés sous
`/opt/dinoer/scripts/` et accessibles via les commandes `dinoer-*` — corrigé le 15/08/2026], cette section date de la création réelle de cette branche :

```bash
# crontab -e (votre propre crontab)
*/15 * * * * bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/mon-scenario.json \
  --reference /opt/dinoer/references/mon-scenario.ref.json \
  --ntfy-topic dinoer-monitoring \
  >> /var/log/dinoer/cron-structural.jsonl 2>&1
```

---

## Pièges courants

| Situation | Que faire |
|---|---|
| `FileNotFoundError` sur le fichier d'identifiants | vérifiez que le fichier JSON est nommé avec le FQDN complet (`urlparse(url).hostname`) |
| `SecretsFermesError` (code de sortie 42) | montez le répertoire chiffré : `bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh` |
| JSON invalide en sortie | utilisez `2>/dev/null \| tail -1` pour n'extraire que la ligne JSON |
| Connexion suivie d'une redirection Django vers le tableau de bord | n'utilisez pas `naviguer` dans une session Django reprise — passez l'URL via `--url` |
| Champ de formulaire `<select>` non rempli | utilisez `remplir` avec `selecteur`, puis `cliquer` sur l'option, ou pilotez-le via `evaluer` |
| Le clic n'a aucun effet sur un bouton hors du viewport | ajoutez `{"type":"defiler","selecteur":"#le-bouton"}` avant le clic |
| `auth_status: "active"` même sur la page de connexion | le sélecteur positif est ambigu (en-tête persistant) — ajoutez `--auth-indicator-negative .btn-login` |
| Les Web Components bloquent un sélecteur normal | utilisez `cliquer_iframe`/`remplir_iframe` avec un sélecteur explicite, ou atteignez l'intérieur de la racine shadow via `evaluer` |
| `respect.waf_bloquants` apparaît sur une page qui n'est pas réellement bloquée | la détection est fondée sur des mots-clés (v1.16.0, affinée v1.17.2) — traitez-la comme un signal, pas un verdict. Si ça persiste sur une page confirmée non bloquée, ajoutez `--ignorer-waf` |
| `cliquer` clique sur le mauvais élément sur une page qui a muté | préférez des sélecteurs stables dans l'ordre, ou relisez l'arbre avec un nouvel appel `--a11y` avant de cliquer |
| Un long scénario RPA échoue en cours de route et vous ne voulez pas rejouer les étapes terminées | ajoutez `--checkpoint FICHIER` (v1.17.0) — relancez la même commande pour reprendre ; l'état du DOM n'est pas préservé, seulement la session + la position dans les actions |
| Les éléments interactifs à l'intérieur d'une iframe sont invisibles pour l'arbre | utilisez `cliquer_iframe`/`remplir_iframe` (v1.17.0) avec un sélecteur CSS explicite, ou `iframe_chemin` (v1.18.0) pour une iframe imbriquée dans une autre |
| Votre modèle rapporte `"erreur": "guide_non_lu"` / exit 1 à son premier appel Dinoer | attendu la première fois qu'un modèle utilise Dinoer sur cette machine sous cet utilisateur OS (v1.18.0) — il doit lire `docs/GUIDE_LLM.md` et passer `--guide-version` une fois. C'est délibéré, pas un bug — dites au modèle de lire le guide plutôt que de contourner l'erreur |

---

## Désinstaller Dinoer

Le script `~/git/Dinoer/Dinoer/scripts/uninstall.sh` retire l'installation
proprement, dans l'ordre inverse d'`install.sh`.

```bash
# Voir ce qui sera retiré, sans rien faire
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --dry-run

# Désinstallation complète (confirmation interactive)
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh

# Sans confirmation (tests à froid, réinstallation enchaînée)
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --confirme && bash ~/git/Dinoer/Dinoer/scripts/install.sh
```

**Ce qui est retiré :**

| Élément | Détail |
|---|---|
| `/opt/dinoer/` | code, venv Python, configuration |
| `/var/log/dinoer/` | journaux d'opérations |
| utilisateur système `dinoer` | créé exclusivement pour Dinoer |
| groupe système `dinoer` | idem |
| appartenance au groupe | votre compte est retiré du groupe `dinoer` |
| hook git pre-push | `core.hooksPath` désactivé dans le dépôt source |

**Ce qui n'est jamais touché :**
- `~/Vaults/` — vos identifiants
- `~/git/Dinoer/` — les sources git
- le cache navigateur de Playwright (`~/.cache/ms-playwright/`)

**Preuves structurées (`/var/log/dinoer/preuves/`) :** si le répertoire
contient des captures, il est préservé par défaut avec un avertissement.
Pour le retirer :

```bash
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --confirme --purge-preuves
```

---

## Consulter l'historique des opérations

```bash
# Toutes les opérations sur une cible
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local

# Opérations mutantes seulement (clics, saisie de formulaire)
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local --mutatif

# Depuis une date
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local \
  --depuis 2026-06-01
```
