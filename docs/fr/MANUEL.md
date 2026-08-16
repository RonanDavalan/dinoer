# Dinoer — manuel opérationnel

**Version 1.0.0 — Août 2026**

Ce document répond à une seule question : **comment faire X avec Dinoer**.

> **Si vous êtes un utilisateur** — aucune commande nécessaire. Dites à votre
> modèle ce que vous voulez visiter, observer, ou accomplir sur un site web,
> une application web, ou une interface d'administration. Le modèle lit ce
> manuel et traduit votre intention en les bonnes actions.
>
> **Si vous êtes un modèle de langage** — ce sont vos commandes. Exécutez-les
> directement.

Aucune description architecturale. Des commandes qui fonctionnent.

---

## Sommaire

1. [Vérifier l'installation](#1-vérifier-linstallation)
2. [Lire une page](#2-lire-une-page)
3. [Navigation respectueuse (v1.15.0)](#3-navigation-respectueuse-v1150)
4. [Répertoire chiffré et identifiants](#4-répertoire-chiffré-et-identifiants)
5. [Écrire et exécuter un scénario RPA](#5-écrire-et-exécuter-un-scénario-rpa)
6. [Actions — référence complète](#6-actions--référence-complète)
7. [Gérer les obstacles courants](#7-gérer-les-obstacles-courants)
8. [Surveillance — vérifications structurelles](#8-surveillance--vérifications-structurelles)
9. [Journal d'opérations](#9-journal-dopérations)
10. [Options CLI — référence](#10-options-cli--référence)
11. [Codes de sortie et sortie](#11-codes-de-sortie-et-sortie-json)

---

## 1. Vérifier l'installation

```bash
# Vérification la plus simple possible – sans Playwright, sans URL, sortie immédiate avec le code 0 (v1.18.0+).
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --version
# → {"outil": "shot.py", "version": "1.0.0"}
```

```bash
# Test complet en une seule commande (environ 3 secondes).
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://example.com --a11y --guide-version 1.6
```

Résultat attendu : JSON sur stdout avec `"succes": true`.

**`--guide-version` (v1.18.0+) :** `shot.py` et `rpa.py` refusent de
s'exécuter sans lui — sauf si un marqueur local d'un appel précédent accepté
existe déjà (`~/.config/dinoer/guide_state.json`). La valeur est le
`<!-- notice-version: X.Y -->` à la ligne 3 de `docs/GUIDE_LLM.md` — pas le
numéro de release de Dinoer. Lisez la valeur courante plutôt que de faire
confiance à celle citée ici : `grep notice-version
/opt/dinoer/docs/GUIDE_LLM.md`. Voir `docs/GUIDE_LLM.md` section « Mandatory
pre-flight » pour le mécanisme complet et le format d'erreur si vous
l'omettez.

**Une fois le marqueur présent, `--guide-version` redevient optionnel** —
tous les autres exemples de commande de ce manuel l'omettent
délibérément, puisqu'un marqueur issu de n'importe quel appel réussi
antérieur les couvre déjà, tant que le `notice-version` de
`docs/GUIDE_LLM.md` n'a pas changé depuis.

```bash
# Vérifiez la version installée.
grep "__version__" /opt/dinoer/shot.py
# → __version__ = "1.0.0"

# Vérifiez que `playwright-stealth` est disponible (version v1.15.0).
/opt/dinoer/venv/bin/python -c "import playwright_stealth; print('stealth OK')"

# Vérifiez que le répertoire chiffré est monté.
ls ~/Vaults/__PROJET__/Dinoer/
# → doit afficher les fichiers .json, et non une liste vide.
```

Si `ls ~/Vaults/...` renvoie une liste vide ou une erreur :
→ montez-le : `bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh`

### 1a. Installation

Deux canaux, mutuellement exclusifs sur une même machine.

**`.deb` package** — le chemin habituel si vous souhaitez utiliser Dinoer tel quel :

```bash
sudo apt install ./dinoer_1.0.0-1_all.deb
```

Les paquets, les sources et les sommes de contrôle sont publiés sur
[dinoer.davalan.fr](https://dinoer.davalan.fr/en/guides/downloads/).
La configuration se trouve à `/etc/dinoer/dinoer.conf` (JSON, un exemple commenté est installé à côté, sous la forme `dinoer-sample.conf`).

**Cloner le dépôt Git** – si vous avez l'intention de modifier le code source de Dinoer :

```bash
git clone https://github.com/RonanDavalan/dinoer.git ~/git/Dinoer/Dinoer
cd ~/git/Dinoer/Dinoer
bash scripts/install.sh
```

`scripts/install.sh` crée l'utilisateur et le groupe système `dinoer`, le
venv Python, déploie le code vers `/opt/dinoer/`, installe Chromium, et
lance un test de fumée (`shot.py --a11y` contre une URL réelle). Déployez
les modifications ultérieures avec `scripts/deploy.sh`.

La configuration se trouve à `/opt/dinoer/dinoer.conf` (JSON) sur ce canal ; la clé du répertoire de secrets chiffrés est `secrets_dir`. Redéfinition par projet via la variable d'environnement `DINOER_CONF` ou `~/.dinoer.conf`.

Désinstallation :

```bash
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --dry-run   # aperçu, aucune modification effectuée
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh             # confirmation interactive
```

---

## 2. Lire une page

### 2a. Lecture rapide — texte et structure, sans image

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y
```

Renvoie : `a11y_tree` (arbre d'accessibilité — la structure textuelle de la
page), `boussole` (URL effective, titre, statut HTTP). Utilisez ceci pour
lire le titre, vérifier l'URL, ou cartographier la page avant d'interagir.

### 2b. Texte de page nettoyé

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ \
  --action '{"type": "extraire_texte"}'
```

Renvoie `extraction_texte` avec `titre`, `texte` (balises de bruit
retirées : `script`, `style`, `nav`, `header`, `footer`, `aside`,
`noscript`), `url`, `date_capture`. C'est le texte de la page selon
Dinoer — jamais une capture d'écran.

### 2c. Lire la boussole en premier

Chaque sortie contient un objet `boussole` — lisez-le avant tout le reste :

```json
"boussole": {
  "url_courante": "https://target.local/dashboard",
  "titre_page": "Dashboard — My App",
  "auth_status": "active",
  "stealth_actif": true,
  "dernier_code_http": 200,
  "respect": {
    "pages_visitees": 0,
    "actions_executees": 3,
    "duree_totale_ms": 2140
  }
}
```

Si `boussole.url_courante` ne correspond pas à votre attente : arrêtez-vous
et investiguez avant toute action mutante.

### 2d. Lire `etat` pour une décision go/no-go (v1.16.0)

Chaque exécution réussie inclut un objet `etat` à la racine du JSON — lisez-le
avant toute action mutante plutôt que de recouper manuellement vous-même
`auth_status`, `respect.plafond_atteint`, `erreurs_js`, et
`erreurs_console` :

```json
"etat": {
  "pret_a_agir": true,
  "niveau_confiance": "eleve",
  "raisons": ["aucun signal de friction détecté"]
}
```

Si `pret_a_agir` vaut `false` : lisez `raisons` pour la cause
(authentification inactive, dérive de session, plafond de navigation
atteint, ou blocage WAF détecté) avant de continuer.

`etat` ne vérifie pas si l'URL ou le contenu de la page correspond à votre
attente métier — utilisez `evaluer` avec `attendu`/`contient`/`motif`
(section 5d) pour cela.

---

## 3. Navigation respectueuse (v1.15.0)

### 3a. Mode furtif `--stealth`

Certains sites bloquent les navigateurs headless sur
`navigator.webdriver=true` sans examiner l'intention. `--stealth` retire ce
marqueur technique automatique.

```bash
# shot.py direct
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y --stealth

# Via rpa.py
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/my-scenario.json --stealth
```

Quand actif : `boussole.stealth_actif = true` dans la sortie JSON.

**Ce que `--stealth` change :** `navigator.webdriver` retiré, plugins, langues et plateforme normalisés.
**Ce que `--stealth` ne change pas :** l'IP, l'identité, ou l'intention de navigation de l'opérateur.

### 3b. Délais de courtoisie et plafonds

Configurés dans `/opt/dinoer/dinoer.conf` (section `[navigation]`). Les
valeurs par défaut sont actives même sans fichier de configuration
(v1.19.0 — D-10) :

```json
{
  "secrets_dir": "~/Vaults/__PROJET__/Dinoer",
  "navigation": {
    "min_action_delay_ms": 800,
    "max_pages_par_run": 10,
    "max_actions_par_run": 30
  }
}
```

`min_action_delay_ms` : délai minimum (ms) entre chaque action. Valeur par
défaut livrée : 800 ms.

**Développement local — réglez-le à `0` :** la valeur par défaut de 800 ms
protège un opérateur distrait lors de sa *première* exécution non
configurée contre l'internet public — elle n'a aucun but protecteur contre
votre propre machine de développement. Réglez la clé explicitement dans
votre `dinoer.conf` local. Conservez la valeur par défaut de 800 ms (ou
augmentez-la) pour toute cible atteinte via l'internet public.

Les plafonds `max_pages_par_run` et `max_actions_par_run` arrêtent
proprement l'exécution s'ils sont dépassés — le JSON de sortie contient
alors :

```json
"respect": {
  "pages_visitees": 10,
  "actions_executees": 10,
  "duree_totale_ms": 12400,
  "plafond_atteint": "max_pages_par_run"
}
```

### 3c. Métriques d'impact

Chaque exécution renvoie `respect` (racine du JSON et dans `boussole`) :

| Clé | Signification |
|---|---|
| `pages_visitees` | nombre de navigations `type: naviguer` exécutées |
| `actions_executees` | nombre total d'actions de scénario exécutées |
| `duree_totale_ms` | durée totale de l'exécution |
| `plafond_atteint` | `"max_pages_par_run"` ou `"max_actions_par_run"` si arrêt anticipé |
| `indice_agressivite` | ratio d'actions mutantes sur le total — restez sous 0,3 pendant une exploration ouverte |
| `waf_bloquants` | nombre de navigations signalées comme bloquées par un WAF |

### 3d. Repère furtivité — quantitatif (v1.17.1)

Préférez compter des signaux d'empreinte concrets plutôt que comparer à
l'œil — c'est la méthode utilisée pour vérifier le correctif de
compatibilité d'API `playwright-stealth` de la v1.17.0
(`docs/RETOUR_EXPERIENCE.md` FR-79) :

```bash
# Sans stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://bot.sannysoft.com --timeout 20000 \
  --actions '[{"type":"evaluer","script":"navigator.webdriver"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.failed\").length"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.passed\").length"}]'

# Avec stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://bot.sannysoft.com --stealth --timeout 20000 \
  --actions '[{"type":"evaluer","script":"navigator.webdriver"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.failed\").length"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.passed\").length"}]'
```

Lisez les trois valeurs dans `evaluations[].valeur` : `navigator.webdriver`
devrait passer de `true` à `false`, `td.failed` devrait tomber vers `0`.
Mesure de référence (correctif v1.17.0, session 47) : 12 échecs → 0 échec.

### 3e. Signal de détection WAF (v1.16.0, affiné v1.17.2)

Dinoer signale un blocage WAF probable de façon passive — HTTP 403/429, ou
une correspondance de mot-clé dans le titre/HTML (`Cloudflare`, `CAPTCHA`,
`checking your browser`, etc.). C'est un signal, jamais une exception —
l'exécution se termine normalement :

```json
"respect": {
  "waf_bloquants": 1
}
```

Quand présent et `> 0` : `etat.niveau_confiance` vaut `"faible"` et
`etat.pret_a_agir` vaut `false`. Décidez vous-même de réessayer avec
`--stealth`, de changer de cible, ou de vous arrêter — Dinoer n'interrompt
pas l'exécution à votre place.

Depuis la v1.17.2, les noms de fournisseurs génériques (`Cloudflare`,
`Akamai`) ne correspondent qu'au titre de la page — faire correspondre le
HTML complet produisait auparavant des faux positifs sur de simples
références de ressource CDN. Si un faux positif persiste,
`--ignorer-waf` dégrade `niveau_confiance` sans forcer
`pret_a_agir: false` (`boussole.waf_ignore_actif: true` enregistre la
dérogation). La détection est fondée sur des mots-clés et peut produire des
faux positifs sur des pages qui discutent légitimement de blocage/détection
— traitez-la comme un signal rapide, pas un verdict certain.

---

## 4. Répertoire chiffré et identifiants

### 4a. Structure

Les identifiants vivent dans un répertoire chiffré — un volume gocryptfs —
contenant un fichier `.json` par domaine.

```
~/Vaults/__PROJET__/Dinoer/
  ├── app.example.com.json         ← identifiants pour https://app.example.com/
  ├── admin.example.com.json       ← identifiants pour https://admin.example.com/
  └── operations.jsonl             ← journal d'opérations (v1.15.0)
```

Format du fichier d'identifiants :

```json
{
  "username": "admin@example.com",
  "password": "mon-mot-de-passe"
}
```

Le nom du fichier = `urlparse(url).hostname`. Pour `https://app.example.com/login/`, créez `app.example.com.json`.
Le répertoire provient de la clé `secrets_dir` dans le fichier de configuration nommé par
`DINOER_CONF` (par défaut `/opt/dinoer/dinoer.conf`) — corrigé le 15/08/2026:
`~/.dinoer.conf` est une convention de nommage pour l'endroit où `DINOER_CONF` pointe généralement, et non une étape de repli automatique distincte.

### 4b. Remplir un formulaire — la règle absolue

**INTERDIT — expose le mot de passe dans le shell et `/proc` :**

```bash
PASS=$(jq -r '.password' ~/Vaults/.../file.json)   # JAMAIS
curl -d "password=$PASS" https://...                 # JAMAIS
```

**CORRECT — identifiants résolus à l'intérieur de Playwright :**

```json
{"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
{"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"}
```

Les valeurs ne transitent jamais par le shell, l'historique bash, les
journaux de processus, ni aucun fichier.

### 4c. Choisir le fichier d'identifiants pour une exécution

```bash
# Répertoire d'identifiants par défaut (défini dans dinoer.conf > secrets_dir)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url https://target.local/ --a11y

# Fichier d'identifiants explicite (--secrets)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y \
  --secrets /path/to/mounted/directory/creds.json

# Répertoire d'identifiants par projet via .dinoer.conf
export DINOER_CONF=~/git/MyProject/.dinoer.conf
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url https://target.local/ --a11y
```

Contenu de `~/git/MyProject/.dinoer.conf` :

```json
{"secrets_dir": "../MyProject-secrets"}
```

Le chemin est résolu par rapport à l'emplacement de `.dinoer.conf`.

**Contenu du fichier `--secrets` — `origines_autorisees` obligatoire depuis
le 05/08/2026** (changement cassant, sans période de compatibilité) : un
fichier auquel il manque cette clé est refusé avant toute lecture.

```json
{"username": "operator", "password": "secret", "origines_autorisees": ["target.local"]}
```

`origines_autorisees` liste les hostnames contre lesquels ce fichier peut
être utilisé — même format en minuscules, sans schéma, sans port que
`domaine_depuis_url()`. Une lecture contre une page dont le domaine n'est
pas dans la liste est refusée (`SecretsOrigineNonAutoriseeError`).

### 4d. TOTP / MFA

Deux chemins effectifs, tous deux résolus à l'intérieur de Playwright
(jamais un code saisi) :

```json
{"type": "remplir", "selecteur": "input[name=otp]", "valeur": "depuis_secrets_totp"}
```

Lit la clé `totp_cle` (graine base32) du fichier d'identifiants et calcule
le code TOTP courant.

Pour recevoir le code via ntfy (flux sans intervention humaine) :

```json
{"type": "attendre_mfa_ntfy", "selecteur": "input[name=otp]", "timeout": 120}
```

`selecteur` est le sélecteur CSS du champ OTP. L'URL de base ntfy vient de
`DINOER_NTFY_URL` (environnement) ou de la clé `ntfy.url` de `dinoer.conf`.

### 4e. Somme de contrôle d'intégrité (opt-in, v1.15.0)

Pour protéger un fichier d'identifiants contre une corruption FUSE
silencieuse, ajoutez un champ `checksum` :

```bash
# Générer la somme de contrôle — corrigé le 15/08/2026, vérifié contre
# lib/repertoire_chiffre.py:32 (_CHAMPS_CHECKSUM) : la somme couvre les
# quatre champs présents, pas seulement username/password.
/opt/dinoer/venv/bin/python -c "
import json, hashlib
creds = json.load(open('mes_identifiants.json'))
champs = ('username', 'password', 'totp_cle', 'origines_autorisees')
fields = {k: creds[k] for k in sorted(champs) if k in creds}
print('sha256:' + hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest())
"
```

Ajoutez la valeur renvoyée au fichier d'identifiants :

```json
{
  "username": "admin@example.com",
  "password": "mon-mot-de-passe",
  "checksum": "sha256:a3f2c1..."
}
```

Si la somme de contrôle ne correspond pas, `shot.py` lève une
`SecretsChecksumError` (code de sortie 42) avec un message explicite. Sans
la clé `checksum` : comportement inchangé (opt-in strict).

### 4f. Répertoire chiffré fermé — que faire

```
SecretsFermesError: Le répertoire chiffré Dinoer est initialisé mais non monté.
```

```bash
# Monter le répertoire chiffré
bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh

# Vérifier le montage
ls ~/Vaults/__PROJET__/Dinoer/
# → doit montrer des fichiers JSON
```

### 4g. HTTP Basic Auth — `--http-credentials` (v1.21.0)

Pour les cibles derrière un défi HTTP Basic Auth au niveau réseau
(RFC 7617) — le mur qu'un reverse proxy comme Caddy, nginx, ou Traefik
dresse avant qu'aucune page ne se rende, courant devant les interfaces
d'administration auto-hébergées. C'est un mécanisme différent de
l'authentification par formulaire décrite ci-dessus (4a-4f), qui reste
entièrement supportée et non affectée.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://internal.example/ \
  --http-credentials --secrets ~/Vaults/__PROJET__/Dinoer/internal_example.json
```

Fichier d'identifiants — la paire `username`/`password` déjà utilisée pour
le cas courant (un seul jeu d'identifiants pour la cible) :

```json
{"username": "admin", "password": "mon-mot-de-passe"}
```

Les clés dédiées `http_username`/`http_password` sont essayées en premier
et ne sont nécessaires que quand la même cible a *à la fois* un mur Basic
Auth au niveau réseau *et* sa propre connexion applicative séparée (deux
paires d'identifiants différentes dans le même fichier) — Dinoer se replie
automatiquement sur `username`/`password` quand les clés dédiées sont
absentes.

Confirmé en production contre une cible réelle protégée par Caddy : le
comportement par défaut sûr (`send: "unauthorized"` — les identifiants ne
sont envoyés qu'après un vrai 401, jamais préventivement) a résolu le défi
dès la première tentative. `boussole.http_credentials_actif: true` confirme
un vrai succès, pas seulement le fait que le drapeau a été passé ;
`boussole.http_auth_requise: true` signale un 401 non résolu, distinct
d'un blocage WAF.

---

## 5. Écrire et exécuter un scénario RPA

### 5a. Protocole en 3 étapes

**Étape 1 — explorer la page (lecture seule)**

```bash
# Vue rapide — arbre d'accessibilité
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y

# Lecture complète — arbre + texte nettoyé
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y \
  --action '{"type": "extraire_texte"}'

# Inventaire DOM enrichi (frameworks, attributs data stables)
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/diagnostic_dom.json \
  --url https://target.local/
```

**Ce qu'il faut noter :**
- attributs stables : `name`, `id`, `aria-label`, `data-testid`
- overlays bloquants (bannières cookies, modales)
- SPA ou rechargement HTTP complet

**Étape 2 — écrire le scénario**

```json
{
  "nom": "login_app",
  "url": "https://app.example.com/login/",
  "intention": "Connexion administrateur avec identifiants stockés",
  "actions": [
    {"type": "nettoyer_overlay", "selecteur": ".cookie-banner"},
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".user-avatar"}
  ]
}
```

**Étape 3 — exécuter**

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/login_app.json
```

### 5b. Scénario complet : se connecter et naviguer entre les pages

```json
{
  "nom": "audit_pages",
  "url": "https://app.example.com/login/",
  "intention": "Lecture après déploiement",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".dashboard-main"},
    {"type": "naviguer", "url": "https://app.example.com/settings/"},
    {"type": "attendre_navigation"},
    {"type": "evaluer", "script": "document.title", "contient": "Settings"},
    {"type": "naviguer", "url": "https://app.example.com/users/"},
    {"type": "attendre_navigation"},
    {"type": "evaluer", "script": "document.querySelectorAll('.user-row').length", "attendu": 12}
  ]
}
```

### 5c. Extraire des données du DOM

```json
{
  "nom": "extract_counters",
  "url": "https://app.example.com/dashboard/",
  "actions": [
    {"type": "evaluer", "script": "document.title"},
    {"type": "evaluer", "script": "document.querySelectorAll('.user-row').length"},
    {"type": "evaluer", "script": "window.location.href"}
  ]
}
```

Résultat dans `evaluations[]` :

```json
"evaluations": [
  {"index": 0, "script": "document.title", "valeur": "Dashboard — My App"},
  {"index": 1, "script": "...", "valeur": 42},
  {"index": 2, "script": "...", "valeur": "https://app.example.com/dashboard/"}
]
```

### 5d. Assertions sur evaluer (rpa.py uniquement)

Trois clés mutuellement exclusives — une par action :

```json
{"type": "evaluer", "script": "document.querySelectorAll('.row').length", "attendu": 3}
{"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
{"type": "evaluer", "script": "window.location.href", "motif": "/dashboard$"}
```

| Clé | Comparaison | Types valides |
|---|---|---|
| `attendu` | égalité stricte `==` | str, int, bool |
| `contient` | sous-chaîne `in` | str seulement |
| `motif` | `re.search()` Python | str seulement |

Si l'assertion échoue : rpa.py s'arrête immédiatement (exit 1) avant toute
action mutante ultérieure.

### 5e. Sous-scénarios (declencher_scenario)

Définir une connexion comme un sous-scénario réutilisable :

```json
{
  "nom": "login_app",
  "url": "https://app.example.com/login/",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".user-avatar"}
  ]
}
```

Appeler ce sous-scénario depuis un autre scénario :

```json
{
  "nom": "full_audit",
  "url": "https://app.example.com/login/",
  "actions": [
    {"type": "declencher_scenario", "scenario": "login_app"},
    {"type": "naviguer", "url": "https://app.example.com/report/"}
  ]
}
```

Profondeur maximale : 5 niveaux d'imbrication. `declencher_scenario` est
aplati par `rpa.py` avant que les actions n'atteignent `shot.py`.

### 5f. Vérifier que vous êtes sur la bonne page avant toute mutation

Ajoutez toujours une garde comme première action dans les scénarios qui
suppriment ou modifient :

```json
{"type": "evaluer", "script": "window.location.href", "contient": "/dashboard"},
{"type": "evaluer", "script": "document.querySelector('.alert-danger')?.textContent ?? null", "attendu": null}
```

Si la garde échoue : rpa.py s'arrête avant que la suppression ne soit
exécutée.

### 5g. Reprendre une session (cookies persistés)

```bash
# Première invocation — authentifier et sauvegarder la session
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/login/ \
  --actions /tmp/login.json \
  --sauver-session /tmp/dinoer/session.json

# Invocations suivantes — réutiliser la session (pas de reconnexion)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/dashboard/ \
  --reprendre-session /tmp/dinoer/session.json
```

**Signal de dérive de session :** si la session a expiré,
`boussole.session_derive: true` dans le JSON. Dans ce cas : relancez la
connexion complète sans `--reprendre-session`.

### 5h. Non-régression structurelle — `--replay-verifier` (v1.17.0)

```bash
# Première exécution — sauvegarder la référence structurelle
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/dashboard.json \
  --sauver-verifier-reference /tmp/dashboard.ref.json

# Exécutions suivantes — comparer
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/dashboard.json \
  --replay-verifier /tmp/dashboard.ref.json
```

Compare `http_status`, `dom_stats`, et les résultats d'`evaluer` à la
référence sauvegardée. Verdict sur stderr :

```json
{"type_comparaison": "replay_verifier", "verdict": "stable", "diffs": []}
```

Exit 1 sur `verdict: "regression"`, avec `diffs` listant chaque champ
divergent (`reference` vs `obtenu`). Les deux drapeaux sont mutuellement
exclusifs.

### 5i. Reprendre un long scénario après un échec — `--checkpoint` (v1.17.0)

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/long_audit.json \
  --checkpoint /tmp/long_audit.checkpoint.json
```

Si le scénario échoue en cours de route, le fichier de checkpoint est
écrit avec le compte d'actions terminées et un fichier de session.
**Relancez exactement la même commande** pour reprendre : les actions déjà
terminées sont sautées. En cas de succès complet, le fichier de checkpoint
est supprimé automatiquement.

Une exécution arrêtée par un plafond de navigation
(`max_actions_par_run`/`max_pages_par_run`) est traitée de la même façon
qu'un échec partiel depuis la v1.17.2 — le checkpoint est mis à jour avec
la progression réelle, pas supprimé.

L'état du DOM (modales ouvertes, formulaires à moitié remplis) n'est
jamais préservé lors d'une reprise — seuls les cookies/`localStorage` et la
position dans la liste d'actions le sont. Ne comptez pas sur
`--checkpoint` pour reprendre au milieu d'un formulaire multi-étapes
unique ; il ne reprend qu'aux frontières entre actions.

### 5j. Cibler des éléments à l'intérieur d'une iframe (v1.17.0)

Aucune numérotation d'éléments n'existe à l'intérieur d'une iframe
(même origine ou cross-origin) — ciblez-la directement par sélecteur CSS :

```json
{"type": "cliquer_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "button.valider"},
{"type": "remplir_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`remplir_iframe` prend en charge `valeur: "depuis_secrets"` exactement
comme `remplir` (section 4b) — jamais un identifiant en clair dans le
scénario. Si l'élément cible refuse l'interaction (par exemple une région
`contenteditable` en état lecture seule), ajoutez `"force": true` à
`cliquer_iframe` — mêmes sémantiques que `cliquer` (section 7e).

Pour trouver le sélecteur interne : utilisez `evaluer` sur le contenu de
l'iframe s'il est de même origine
(`document.querySelector('iframe').contentDocument...`), ou consultez le
balisage/la documentation propre de l'application cible si cross-origin.

### 5k. Iframes imbriquées — `iframe_chemin` (v1.18.0)

Une iframe à l'intérieur d'une autre iframe : remplacez `iframe_selecteur`
par `iframe_chemin`, un tableau ordonné — un sélecteur CSS par niveau
d'imbrication, du plus externe au plus interne.

```json
{"type": "cliquer_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "button.valider"},
{"type": "remplir_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`iframe_selecteur` (une seule frame) et `iframe_chemin` (descente
imbriquée) sont mutuellement exclusifs — exactement un requis par action.
Pour une iframe à un seul niveau, continuez d'utiliser `iframe_selecteur`
(section 5j).

---

## 6. Actions — référence complète

| Type | Paramètres requis | Paramètres optionnels | Remarques |
|---|---|---|---|
| `naviguer` | `url` | — | rechargement HTTP complet. Compté dans `respect.pages_visitees` |
| `cliquer` | `selecteur` | `force` (bool), `repli_js` (bool) | `force: true` contourne les éléments cachés en CSS ou un showModal. `repli_js: true` retente via JS si le clic natif échoue encore (v1.22.0) — rejeté avec `--no-evaluer` (exit 2, avant le lancement) |
| `remplir` | `selecteur`, `valeur` | `secret_cle` | `valeur: "depuis_secrets"` requiert `secret_cle` ; `"depuis_secrets_totp"` pour le TOTP |
| `evaluer` | `script` | `attendu`, `contient`, `motif` | JS exécuté dans le navigateur. Assertions pour rpa.py uniquement |
| `defiler` | `px` ou `selecteur` | — | défilement vertical en pixels (`px`) ou jusqu'à un élément (`selecteur`) |
| `pause` | `ms` | — | délai fixe en ms. Préférez `attendre_selecteur_present` pour les signaux DOM |
| `attendre` | `selecteur` | — | attend que le sélecteur CSS devienne visible (`state=visible`, défaut Playwright — corrigé le 16/08/2026, identique à `attendre_selecteur_present`) |
| `attendre_navigation` | — | — | attend `networkidle` (fin des requêtes réseau) |
| `attendre_url` | `motif` | `attendre_changement` (bool) | correspondance de sous-chaîne d'URL. `attendre_changement: true` attend d'abord une vraie navigation (voir le piège FR-55) |
| `attendre_selecteur_present` | `selecteur` | — | attend que l'élément soit visible (`state=visible`) |
| `attendre_absence` | `selecteur` | `delai_initial_ms` | attend la disparition de l'élément du DOM (`state=detached`) |
| `attendre_reseau_calme` | — | `timeout_ms` | 500 ms de silence réseau. `timeout_ms` : durée maximale avant d'abandonner |
| `attendre_mfa_ntfy` | `selecteur` | `timeout` | attend un code TOTP via ntfy, le remplit dans le champ |
| `nettoyer_overlay` | `selecteur` | — | masque les overlays bloquants (bannière cookies, modale) — sélecteur explicite, aucune détection automatique |
| `declencher_scenario` | `scenario` | — | intègre les actions d'un sous-scénario. Profondeur max : 5 (rpa.py) |
| `extraire_texte` | — | — | texte de page nettoyé depuis le DOM rendu — `extraction_texte` (`titre`, `texte`, `url`, `date_capture`) |
| `cliquer_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur` | `force` (bool) | clic à l'intérieur d'une iframe (v1.17.0). `iframe_chemin` pour les iframes imbriquées (v1.18.0, section 5k) |
| `remplir_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur`, `valeur` | `secret_cle` | remplissage à l'intérieur d'une iframe (v1.17.0). `valeur: "depuis_secrets"` pris en charge |

---

## 7. Gérer les obstacles courants

### 7a. Bannière de cookies / overlay bloquant

```json
{"type": "nettoyer_overlay", "selecteur": ".cookie-consent-banner, #gdpr-overlay"}
```

Placez-la **avant** toute autre action de lecture/interaction. L'overlay
masque des éléments dans l'arbre d'accessibilité.

### 7b. Élément hors du viewport

Défilez jusqu'à lui (par quantité ou par sélecteur), puis agissez :

```json
{"type": "defiler", "selecteur": "#le-bouton"},
{"type": "cliquer", "selecteur": "#le-bouton"}
```

ou

```json
{"type": "defiler", "px": 600},
{"type": "cliquer", "selecteur": "button[data-testid='load-more']"}
```

### 7c. SPA (React, Vue, Angular) — naviguer sans rechargement

Après un clic qui change la vue dans une SPA, Playwright ne sait pas quand
la navigation est terminée.

```json
{"type": "cliquer", "selecteur": "a[href*='/dashboard']"},
{"type": "attendre_url", "motif": "/dashboard"},
{"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
```

Ne présumez jamais qu'un clic a terminé une navigation sans signal DOM.
Après un submit, associez `attendre_url` avec `attendre_selecteur_present`
(piège de correspondance partielle, voir
`docs/GUIDE_LLM_INTERACTIONS.md`).

### 7d. Dialogue CSS ou showModal()

`TimeoutError` sur `cliquer` alors que l'élément est visible dans le DOM =
élément caché en CSS ou à l'intérieur d'un dialogue.

```json
{"type": "cliquer", "selecteur": "#dialog-confirm button[type=submit]", "force": true}
```

Si `force: true` est insuffisant (erreur d'interactivité/obstruction) :
ajoutez `repli_js: true` à la même action (v1.22.0), ou repliez-vous sur du
JS :

```json
{"type": "evaluer", "script": "document.querySelector('#dialog-confirm button[type=submit]').click()"}
```

### 7e. Opération longue (spinner, tâche par lot)

N'utilisez pas `pause` pour attendre une durée fixe. Attendez le signal
DOM :

```json
{"type": "cliquer", "selecteur": "button[data-testid='run-job']"},
{"type": "attendre_absence", "selecteur": ".spinner", "delai_initial_ms": 500},
{"type": "attendre_selecteur_present", "selecteur": ".result-container"}
```

Si l'opération ne fournit aucun signal DOM, sondez l'état avec `evaluer` et
continuez quand la preuve est présente.

### 7f. Plafond atteint (v1.15.0)

Si `respect.plafond_atteint` est présent dans la sortie, l'exécution s'est
arrêtée avant que le scénario ne se termine. Les actions restantes n'ont
pas été exécutées.

Options :
1. augmenter `max_pages_par_run` ou `max_actions_par_run` dans
   `dinoer.conf`
2. découper le scénario en plusieurs exécutions
3. reprendre une section partielle avec `--checkpoint`

### 7g. Champ de formulaire `<select>`

`remplir` (`.fill()`) ne fonctionne pas sur `<select>`. Utilisez un
setter JS via `evaluer` :

```json
{"type": "evaluer", "script": "(() => { const s = document.querySelector('select[name=role]'); s.value='admin'; s.dispatchEvent(new Event('change',{bubbles:true})); })()"}
```

### 7h. Site bloqué par un WAF (403 immédiat)

```bash
# Essayer avec stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y --stealth
```

Si le 403 persiste avec `--stealth` : le site utilise du fingerprinting TLS
(JA3/JA4) ou une analyse comportementale avancée (Cloudflare Enterprise).
`playwright-stealth` ne contourne pas ces protections. Voir
`docs/RETOUR_EXPERIENCE.md` FR-77/FR-78/FR-79 pour le contexte.

Dinoer signale aussi un blocage probable de façon passive — voir la
section 3e (`respect.waf_bloquants`).

### 7i. La navigation initiale ne se termine jamais — `--wait-until` (v1.22.0)

Symptôme : `TimeoutError` sur la navigation initiale, et augmenter
`--timeout` ne change rien (45 s échoue exactement comme 10 s). Cause :
par défaut Dinoer attend `networkidle` — 500 ms de silence réseau. Une
page qui interroge en continu (statistiques en direct, compteurs
auto-rafraîchis, panneaux d'administration de routeur) ne produit jamais
ce silence, donc aucune valeur de timeout ne peut jamais être assez
grande.

```bash
# shot.py — reconnaissance directe
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url http://target.local/ --wait-until load --a11y

# rpa.py — propagé à shot.py, donc les scénarios atteignent les mêmes cibles
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario ./admin_login.json --wait-until load
```

Un scénario peut le porter comme propriété racine à la place, en restant
autonome :

```json
{"url": "http://target.local/", "wait_until": "load", "actions": [...]}
```

Le drapeau CLI a priorité sur la propriété de scénario.

| Valeur | Attend | À utiliser quand |
|---|---|---|
| `networkidle` | 500 ms de silence réseau | par défaut — conservez-la sauf échec |
| `load` | événement `load` (page et sous-ressources) | interrogation continue / statistiques en direct |
| `domcontentloaded` | HTML parsé, sous-ressources encore en attente | page très lourde, le DOM suffit |

S'applique uniquement à la navigation initiale — l'action `naviguer` n'est
pas affectée. `boussole.wait_until` rapporte la valeur seulement quand
elle diffère de la valeur par défaut.

---

## 8. Surveillance — vérifications structurelles

Aucune surveillance basée sur l'image n'existe dans Dinoer (aucun diff
visuel). Les vérifications structurelles sont textuelles et adaptées à la
CI.

### 8a. Surveillance structurelle continue — `scripts/monitor-verifier.sh` (v1.18.0)

Surveille la *structure* (`http_status`, `dom_stats`, `evaluations`) —
aucune image, aucun appel de LLM, construit sur `--replay-verifier`
(section 5h).

```bash
# Premier lancement : créer la référence structurelle.
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/example_login.json \
  --sauver-verifier-reference /opt/dinoer/references/example_login.ref.json

# Un script de vérification et d'alerte – ce n'est pas un démon, exécutez-le à plusieurs reprises via cron.
# Sur le canal git-clone, les fichiers scripts/*.sh ne sont jamais déployés vers /opt/dinoer/.
# de sorte qu'il s'exécute à partir du code source Git, en tant que votre propre utilisateur. Sur le canal .deb,
# les trois scripts compressés (monter/démonter-répertoire-chiffré,
# monitor-vérificateur) SONT installés sous /opt/dinoer/scripts/ – corrigé.
# 15/08/2026, ce commentaire date de l'époque précédant la véritable création de cette chaîne.
bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/example_login.json \
  --reference /tmp/ref_sillage.json \
  --ntfy-topic dinoer-monitoring
```

```bash
# crontab -e (votre propre crontab)
*/15 * * * * bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/example_login.json \
  --reference /opt/dinoer/references/example_login.ref.json \
  --ntfy-topic dinoer-monitoring \
  >> /var/log/dinoer/cron-structural.jsonl 2>&1
```

Stable → silence. Régression → une notification `ntfy` avec le diff.
Chaque invocation est un processus isolé — aucun démon, aucun risque de
fuite mémoire, et les plafonds de navigation respectueuse se réinitialisent
proprement à chaque passe.

**Corrigé le 16/08/2026 :** le script appelait auparavant `rpa.py --no-capture
--replay-verifier`, mais `--no-capture` n'était plus un drapeau de `rpa.py` —
chaque exécution réelle échouait au niveau d'argparse. Le drapeau mort a été
retiré (Dinoer n'a aucun chemin image par défaut, le retirer ne change rien
d'autre).

**Nuance sur le verrou de lecture du guide :** si invoqué sous un
utilisateur OS distinct (par exemple un compte de service système), cet
utilisateur a besoin que `--guide-version` soit validé une fois
(`~<home>/.config/dinoer/guide_state.json`).

---

## 9. Journal d'opérations

Le journal est `/var/log/dinoer/operations.jsonl`. Si le chemin de journal
configuré se trouve à l'intérieur du répertoire chiffré et qu'il n'est pas
monté, les entrées sont redirigées vers un repli local (écriture dégradée,
700/600) plutôt qu'écrites en clair sur l'hôte brut.

```bash
# Lire les 10 dernières entrées
tail -n 10 /var/log/dinoer/operations.jsonl | python3 -m json.tool

# Filtrer par cible (outil journal.py)
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com

# Filtrer les opérations mutantes seulement
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --mutatif

# Depuis une date
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --depuis 2026-07-01

# Exécutions en échec seulement (v1.20.0) — resultat != succes
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --erreurs
```

Champs de chaque entrée :

| Champ | Signification |
|---|---|
| `ts` | Horodatage ISO 8601 |
| `operation_id` | Identifiant de session unique (v1.16.0), nomme le répertoire du fichier temporaire |
| `outil` | `"shot.py"`, `"rpa.py"` ou `"campagne.py"` — corrigé le 15/08/2026, était documenté comme `mode` (`shot.py`/`rpa.py`), un champ que le code n'a jamais écrit |
| `version` | Version de Dinoer |
| `cible_url` | URL cible |
| `resultat` | `"succes"` ou `"echec"` |
| `mutatif` | `true` si au moins une action d'écriture a été effectuée |
| `hostname_executant` / `utilisateur_executant` / `profil_actif` | Boussole d'exécution (hôte, utilisateur du système d'exploitation, profil d'opérateur actif) |
| `intention` | Étiquette transmise via le champ `--intention` ou le scénario `intention` — présente uniquement si définie |
| `source_scenario` | Nom du fichier de scénario uniquement, sans chemin (v1.18.0) — présent uniquement en mode RPA. Corrigé le 15/08/2026: précédemment, le tableau listait également un champ `scenario` (chemin complet); le code n'a jamais écrit celui-ci |
| `chainage` | Liste de `{scenario, profondeur, action_debut, action_fin}` — présente uniquement lorsque `declencher_scenario` a été utilisé |
| `actions` | Liste d'actions résumée — présente lorsque la session contenait des actions |
| `actions_raw` | Liste complète d'actions neutralisée — présente uniquement lors d'une exécution réussie avec des actions |
| `captures` | Référence(s) aux captures structurelles — présente uniquement lorsque l'exécution a produit quelque chose |
| `erreur` | Présent uniquement en cas d'échec |
| `respect` | Journal de navigation de la session — présent uniquement si défini |
| `evaluations` | Valeurs de `{script, valeur_retournee}` nettoyées — présent uniquement si les actions `evaluer` ont été exécutées |

Aucun champ `duree_ms` n'existe dans le journal — corrigé le 15/08/2026,
cette table en listait un que le code n'a jamais écrit. La mesure du temps
par action est `latences_actions`, dans la sortie JSON d'un run, pas dans
l'entrée du journal.

### 9a. Rotation du journal (G-36)

Dinoer ne livre pas de configuration logrotate —
`/var/log/dinoer/operations.jsonl` croît sans limite jusqu'à ce que
l'administrateur en installe une. `lib/journal.py` ouvre et ferme le
fichier à chaque écriture (aucun descripteur de fichier persistant entre
les exécutions), spécifiquement pour que le comportement **par défaut** de
logrotate (renommer le fichier courant, en créer un nouveau) fonctionne
correctement sans aucune option spéciale : la prochaine écriture rouvre le
chemin et trouve le nouvel inode.

**N'ajoutez pas `copytruncate`** à une configuration logrotate pour
Dinoer — c'est inutile ici et cela réintroduit une fenêtre de perte
d'écriture. Exemple `/etc/logrotate.d/dinoer` :

```
/var/log/dinoer/operations.jsonl {
    weekly
    rotate 8
    compress
    delaycompress
    missingok
    notifempty
    create 0640 dinoer dinoer
}
```

`journal.py` (le lecteur) suit déjà les fichiers pivotés de façon
transparente (`operations.jsonl`, `.1`, `.2.gz`, …) — aucune étape
supplémentaire nécessaire après la rotation.

---

## 10. Options CLI — référence

### shot.py

| Option | Défaut | Description |
|---|---|---|
| `--version` | — | affiche la version installée et quitte immédiatement — pas de Playwright, aucun autre argument requis (v1.18.0) |
| `--guide-version X.Y` | — | preuve de lecture de `docs/GUIDE_LLM.md` — requis sauf si un marqueur local valide existe déjà (v1.18.0, section 1) |
| `--url URL` | requis | URL à capturer |
| `--actions FICHIER` | — | fichier JSON d'actions séquentielles |
| `--action JSON` | — | action unique en JSON en ligne — à échapper avec précaution, préférez `--actions FICHIER` pour les actions riches en JS |
| `--attendre-selecteur SEL` | — | attend un sélecteur avant de terminer l'exécution |
| `--timeout MS` | 10000 | timeout Playwright par action (ms) |
| `--wait-until VALEUR` | `networkidle` | `networkidle`\|`load`\|`domcontentloaded` — navigation initiale seulement (v1.22.0, section 7i) |
| `--largeur PX` | 1280 | largeur du viewport |
| `--hauteur PX` | 720 | hauteur du viewport |
| `--a11y` | désactivé | inclut l'arbre d'accessibilité dans le JSON |
| `--stealth` | désactivé | mode furtif playwright-stealth (v1.15.0) |
| `--secrets FICHIER` | — | chemin explicite vers un fichier d'identifiants |
| `--auth-indicator SEL` | — | sélecteur CSS présent seulement en session authentifiée |
| `--auth-indicator-negative SEL` | — | requiert `--auth-indicator` ; sélecteur CSS présent seulement hors session authentifiée |
| `--ignorer-waf` | désactivé | un blocage WAF détecté dégrade `niveau_confiance` mais ne force plus `pret_a_agir: false` à lui seul (v1.17.2, section 3e) |
| `--http-credentials` | désactivé | résout les identifiants HTTP Basic Auth depuis le fichier d'identifiants, cantonné à l'origine de la cible (v1.21.0, section 4g) |
| `--ignore-tls-errors` | désactivé | accepte un TLS invalide sur des cibles LAN/dev contrôlées — jamais sur l'internet public (v1.15.1) |
| `--no-evaluer` | désactivé | refuse l'action **evaluer** (et `repli_js`) pour toute l'exécution — recommandé contre les formulaires sensibles (v1.15.1) |
| `--no-filtre-evaluer` | désactivé | désactive la neutralisation sur stdout des valeurs de retour d'**evaluer**, des URLs et des messages d'erreur — exécutions de débogage explicites seulement ; quand désactivé, `boussole.filtre_evaluer_actif: false` est posé (v1.23.0) |
| `--intention TEXTE` | — | libellé métier enregistré dans le journal |
| `--sauver-session FICHIER` | — | sauvegarde les cookies après les actions |
| `--reprendre-session FICHIER` | — | reprend une session sauvegardée |
| `--source-scenario NOM` | — | interne (plomberie rpa.py pour le journal — pas pour des appels directs) |
| `--chainage JSON` | — | interne (plomberie rpa.py pour le journal — pas pour des appels directs) |

### rpa.py

Propage tous les drapeaux pertinents de shot.py, plus :

| Option | Description |
|---|---|
| `--version` | affiche la version installée et quitte immédiatement (v1.18.0) |
| `--guide-version X.Y` | preuve de lecture de `docs/GUIDE_LLM.md` — vérifiée indépendamment, même règle que shot.py (v1.18.0) |
| `--scenario FICHIER` | chemin vers un scénario JSON ou YAML (requis) |
| `--url URL` | surcharge l'URL du scénario sans modifier le fichier |
| `--stealth` | propagé à shot.py |
| `--wait-until` | propagé à shot.py (v1.22.0, section 7i) |
| `--ignorer-waf` | propagé à shot.py (v1.17.2, section 3e) |
| `--http-credentials` | propagé à shot.py ; également réglable comme propriété racine de scénario `"http_credentials": true` (v1.21.0, section 4g) |
| `--auth-indicator-negative` | requiert un `auth_indicator` (CLI ou propriété racine de scénario) |
| `--sauver-verifier-reference FICHIER` | sauvegarde la référence structurelle pour `--replay-verifier` (v1.17.0, section 5h) |
| `--replay-verifier FICHIER` | compare l'exécution à une référence structurelle, exit 1 en cas de régression (v1.17.0, section 5h) |
| `--checkpoint FICHIER` | reprend un long scénario après un échec en cours d'exécution (v1.17.0, section 5i) |

### campagne.py (pipeline de recherche)

| Option | Description |
|---|---|
| `--manifeste FICHIER` | manifeste de campagne (JSON) — requiert `id_campagne` + `cibles` |
| `--id-campagne ID` | identifiant de campagne (utilisé dans le manifeste et l'extraction) |
| `--extraire-cible DEMANDE` | extraction ciblée sur un corpus déjà collecté, sans synthèse |
| `--desactiver-cache` | contourne le cache de recherche |
| `--purger-cache` | purge l'intégralité du cache de recherche |
| `--purger-cache-avant-jours N` | purge les entrées de cache plus anciennes que N jours |

Types de cible dans le manifeste : `query`, `url`, `produit`,
`table_reference`. Artefacts : le `/var/log/dinoer/operations.jsonl`
partagé + un `collecte.jsonl` par campagne. Détail complet :
`campagne.py --help`.

---

## 11. Codes de sortie et sortie JSON

### Codes de sortie

| Code | Cause | Que faire |
|---|---|---|
| 0 | succès | — |
| 1 | erreur Playwright, action échouée, assertion rpa.py, `action_secret_en_clair` | lisez `erreur` dans le JSON. Voir `GUIDE_LLM_INTERACTIONS.md` |
| 1 | `guide_non_lu` — `--guide-version` manquant/faux, aucun marqueur valide (v1.18.0) | se déclenche avant le lancement de Playwright. Lisez `docs/GUIDE_LLM.md`, relancez avec `--guide-version X.Y` (section 1) |
| 2 | arguments incompatibles, `arguments_incompatibles`, `url_scheme_interdit`, `chemin_sensible_refuse` | lisez `message` — il nomme le conflit |
| 3 | module `playwright` introuvable | invoquez via `/opt/dinoer/venv/bin/python` |
| 42 | `SecretsFermesError` — répertoire chiffré non monté, ou somme de contrôle invalide | montez-le, ou vérifiez le fichier d'identifiants |
| 43 | `SecretsNonConfigureError` — aucun `secrets_dir` configuré | configurez `secrets_dir` dans `dinoer.conf` (pallier un exemple manquant : créez `/opt/dinoer/dinoer.conf`) |

### Structure de la sortie JSON

```json
{
  "succes": true,
  "http_status": 200,
  "url_finale": "https://target.local/dashboard",
  "erreurs_js": [],
  "erreurs_console": [],
  "duree_ms": 2400,
  "horodatage": "2026-07-01T12:00:00+02:00",
  "dom_stats": {"boutons": 14, "inputs": 9, "listes_deroulantes": 2, "formulaires": 1, "liens": 41, "dialogues": 0},
  "a11y_tree": "...",
  "evaluations": [],
  "extraction_texte": null,
  "latences_actions": [
    {"index": 0, "type": "naviguer", "latence_ms": 842},
    {"index": 1, "type": "cliquer", "latence_ms": 63}
  ],
  "respect": {
    "pages_visitees": 0,
    "actions_executees": 3,
    "duree_totale_ms": 2400,
    "indice_agressivite": 0.33
  },
  "etat": {
    "pret_a_agir": true,
    "niveau_confiance": "eleve",
    "raisons": ["aucun signal de friction détecté"]
  },
  "boussole": {
    "utilisateur": "operator",
    "ip_locale": "__IP_LAN__",
    "repertoire": "/opt/dinoer",
    "operation_id": "a1b2c3d4e5f6",
    "url_courante": "https://target.local/dashboard",
    "titre_page": "Dashboard — My App",
    "dernier_code_http": 200,
    "stealth_actif": true,
    "auth_status": "active",
    "respect": { "pages_visitees": 0, "actions_executees": 3, "duree_totale_ms": 2400, "indice_agressivite": 0.33 }
  },
  "dinoer_meta": {
    "version_shot": "1.0.0",
    "horodatage_iso": "2026-08-12T14:23:11+02:00",
    "hostname_executant": "operator-host",
    "utilisateur_executant": "operator",
    "profil_actif": "operateur.exemple.yaml",
    "url_au_moment_capture": "https://target.local/dashboard"
  }
}
```

`operation_id` (v1.16.0) est toujours présent et identifie cette exécution
de façon unique — il correspond au champ `operation_id` de l'entrée de
cette exécution dans le journal d'opérations (section 9), et nomme le
répertoire de preuves `preuves/<AAAA-MM>/<operation_id>/` quand des
captures y sont archivées (corrigé le 15/08/2026 : aucun répertoire
`/tmp/dinoer/<operation_id>/` n'existe dans le code — `/tmp/dinoer/` ne
contient que le fichier de repli du journal).
`etat` (v1.16.0) est présent uniquement sur le chemin de succès.
`latences_actions` (v1.20.0) est toujours présent (liste vide si aucune
action), une entrée par action réellement exécutée — voir
`GUIDE_LLM_MONITORING.md` pour la façon dont il complète
`respect.duree_totale_ms`.

Clés conditionnelles (absentes si inactives) : `dom_stats`, `a11y_tree`,
`evaluations`, `extraction_texte`, `auth_status`, `stealth_actif`,
`session_derive`, `respect.plafond_atteint`, `respect.waf_bloquants`,
`respect.indice_agressivite` (présent dès qu'au moins une action a été
exécutée), `boussole.repli_js_utilise`, `boussole.wait_until`,
`boussole.http_credentials_actif`, `boussole.http_auth_requise`,
`boussole.tls_errors_ignored`, `boussole.waf_ignore_actif`,
`boussole.filtre_evaluer_actif`, `boussole.champs_rediges`,
`actions_executees_avant_echec`, `pages_visitees_avant_echec` (JSON
d'échec seulement, v1.17.0). Voir `GUIDE_LLM_MONITORING.md` pour la table
d'activation exhaustive.

### Erreur — format

```json
{
  "succes": false,
  "erreur": "secrets_fermes",
  "message": "Le répertoire chiffré Dinoer est initialisé mais non monté.",
  "code_sortie_recommande": 42,
  "boussole": { "url_courante": "", "titre_page": "" }
}
```

---

## Chemins de référence

| Chemin | Rôle |
|---|---|
| `/opt/dinoer/` | installation de production |
| `/opt/dinoer/venv/bin/python` | Python à utiliser pour chaque invocation |
| `/opt/dinoer/dinoer.conf` | configuration machine (secrets_dir, navigation, ntfy) |
| `/opt/dinoer/scenarios/` | scénarios RPA (dont `diagnostic_dom.json`) |
| `/opt/dinoer/docs/` | documentation |
| `/opt/dinoer/references/` | références `--sauver-verifier-reference` / replay |
| `/tmp/dinoer/` | fichiers de session (`--sauver-session`/`--reprendre-session`) et fichier de repli du journal — corrigé le 15/08/2026 : aucun sous-répertoire par `operation_id` n'existe ici, voir la ligne suivante |
| `/var/log/dinoer/preuves/<AAAA-MM>/<operation_id>/` | répertoire de preuves pour une exécution, isolé par `operation_id` (v1.16.0), créé uniquement quand des captures sont archivées |
| `~/Vaults/__PROJET__/Dinoer/` | identifiants + journal (volume gocryptfs) |
| `~/git/Dinoer/Dinoer/` | sources git (éditez ici, puis `deploy.sh`) |
| `/var/log/dinoer/operations.jsonl` | journal d'opérations persistant (`journal.py`) |

Déployer après modification des sources :

```bash
bash ~/git/Dinoer/Dinoer/scripts/deploy.sh
```
