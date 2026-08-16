# Dinoer — recherche web souveraine et locale pour agents LLM

> **Pour l'opérateur humain :** Dinoer s'exécute sur votre propre machine, délègue
> la recherche et la collecte à des primitives que vous pouvez lire ligne à ligne,
> et vous remet un rapport Markdown sourcé et daté — pas une réponse en boîte noire.
>
> **Pour le LLM :** [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) est votre référence
> opérationnelle. Commencez par là.

---

## Qu'est-ce que Dinoer ?

Dinoer est un **moteur de recherche et de synthèse passif, local et souverain**.
C'est un fork de [Diwall](https://github.com/RonanDavalan/diwall) (automatisation
visuelle de navigateur pour LLM), dépouillé de toute sa couche de perception —
**zéro capture d'écran, zéro Set-of-Mark, zéro modèle de vision.** Dinoer ne
regarde jamais une page ; il la lit : DOM, arbre d'accessibilité et texte de page
nettoyé.

Là où Diwall répond à « interagir avec une interface authentifiée, visuellement »,
Dinoer répond à une question différente : « explorer un grand nombre de sources
publiques et en compiler un signal sourcé et vérifiable » — sur un matériel aussi
modeste qu'un Raspberry Pi 5.

```
Requête → découverte SearXNG → collecte HTTP légère
        → escalade vers un vrai navigateur seulement pour les pages qui l'exigent
        → synthèse par un LLM délégué → rapport Markdown daté et sourcé
```

**Doctrine :** le code Python ne porte aucune intelligence métier. Chaque module
fait une seule chose mécanique — interroger SearXNG, extraire le texte propre
d'une page, lire un identifiant chiffré, envoyer une notification. La *stratégie*
d'une recherche (comment relancer, quand escalader, quand s'arrêter) vit dans un
scénario, jamais codée en dur dans un module. Voir
[`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) pour la doctrine complète.

---

## Positionnement : ce sur quoi Dinoer se distingue et ce sur quoi il ne se concentre pas.

Dinoer ne rivalise pas avec les assistants de recherche polyvalents (comme Perplexity et similaires) en termes d'étendue, de volume ou de prix. Un véritable test (14 août 2026, recherche de réputation sur un sujet réel) a mesuré cela directement plutôt que de le supposer : parmi les 28 pages collectées par la fonction de découverte de Dinoer, basée sur SearXNG, trois sources qu'une simple requête Perplexity non préparée avait immédiatement révélées (un profil LinkedIn, une page de projet, un crédit pour une photo d'illustration) étaient totalement absentes. Cela était dû à des requêtes SearXNG ciblant le mauvais type de recherche (annuaires d'entreprises, et non les termes qui auraient permis de trouver ces pages), et non à un défaut de classement ou de troncature en aval. Un moteur de recherche généraliste avec des moteurs authentifiés et basés sur des cookies a une portée structurelle qu'une instance SearXNG locale non authentifiée n'a pas.

Ce que le même test a vérifié, sur le même ensemble de données, mesurait plutôt qu'il n'affirmait : **une synthèse traçable et reproductible d'un ensemble de données figé.** Chaque affirmation dans un rapport Dinoer peut être attribuée à une page réellement collectée et enregistrée sur disque (`collecte.jsonl`/`operations.jsonl`) – sans aucune dépendance vis-à-vis de ce que faisait un moteur de recherche tiers lors de la production de la réponse. Une vérification directe du flux d'événements complet du modèle délégué pendant la synthèse (et non seulement de son texte final) a confirmé qu'aucun appel externe `websearch`/`webfetch` n'a été effectué vers l'ensemble de données pendant la génération du rapport. C'est là la véritable valeur ajoutée : savoir précisément d'où provient une réponse, et ne pas se contenter des capacités d'un outil généraliste.

---

## Architecture

```
campagne.py (orchestration)
  ├─ lib/searxng.py         → SearXNG JSON API (HTTP only, no browser)
  ├─ lib/fetch_leger.py     → requests + BeautifulSoup, robots.txt-aware
  ├─ rpa.py / shot.py       → Playwright, only for pages the light tier
  │                           marked "insufficient" (JS-only shells)
  ├─ lib/selection_candidats.py → best-match pick among several fetched
  │                           candidates, "produit" targets only
  ├─ lib/extraction.py      → targeted fact extraction, trouve/valeur/url
  ├─ lib/tables_reference.py→ persistent, sourced table of reference sites
  ├─ lib/cache_recherche.py → ChromaDB-backed search cache
  └─ lib/synthese.py + lib/modeles.py → delegated LLM (OpenCode/Ollama),
                                        writes the final report
```

`shot.py`/`rpa.py` conservent le cœur d'exécution ReAct de Diwall (`naviguer`,
`remplir`, `cliquer`, `evaluer`, persistance de session, résolution des
identifiants) — sans aucune de sa couche de perception.

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| **Découverte SearXNG** | Requête HTTP pure contre une instance SearXNG locale ou distante — aucun coût de navigateur payé pour la recherche |
| **Collecte palier léger** | Extraction `requests` + BeautifulSoup, respecte `robots.txt`, sensible aux WAF |
| **Escalade palier lourd** | Playwright, utilisé seulement pour les pages que le palier léger n'a pas pu lire (coquilles rendues en JS) |
| **Extraction sémantique de texte** | action `extraire_texte` — texte du contenu principal nettoyé, jamais une capture d'écran |
| **Instantané d'accessibilité** | `--a11y` — structure sémantique de la page (arbre A11y), aucune image jamais produite |
| **Extraction ciblée** | `lib/extraction.py` — contrat strict `trouve`/`valeur`/`url`, déclare une absence plutôt que d'inventer une réponse |
| **Tables de sites de référence** | `lib/tables_reference.py` — table persistante et sourcée des sites connus par sujet |
| **Cache de recherche vectoriel** | `lib/cache_recherche.py` — adossé à ChromaDB, évite de rejouer une requête quasi identique |
| **Déduplication et fraîcheur** | Déduplication par URL exacte au niveau de la campagne, plafond par hôte, fenêtre de fraîcheur de 30 jours avant re-parcours |
| **Parcours respectueux** | Délai aléatoire entre les cibles, refus strict sur signal WAF/robots.txt — jamais contourné |
| **Résolution des identifiants** | Injection sécurisée des identifiants — jamais en clair, jamais sur la ligne de commande |
| **Répertoire chiffré** | Volume gocryptfs — `SecretsFermesError` (code de sortie 42) s'il n'est pas monté |
| **Journal d'opérations** | Journal persistant en ajout seul de toutes les exécutions — qui a fait quoi, où, quand |
| **Scénarios RPA** | Exécute des séquences d'actions depuis des fichiers JSON, pour le chemin d'escalade du palier lourd |
| **Iframes cross-origin** | `cliquer_iframe` / `remplir_iframe` ciblent des éléments à l'intérieur d'iframes |
| **TOTP / MFA asynchrone** | Les cibles protégées par identifiants restent atteignables quand une exécution en palier lourd doit s'authentifier |

---

## Qualité des rapports : brouillon automatique vs. recherche supervisée

Le rapport de fin d'exécution propre de `campagne.py`
(`lib/synthese.py::construire_contexte()` construit et tronque le corpus,
`rediger_rapport()` rédige ensuite le texte)
est un **projet préliminaire**, et non le produit final : il concatène
le corpus collecté dans l'ordre des fichiers, tronqué à 4000 caractères/page et 60 000
caractères au total, sans classement par pertinence. Sur un grand corpus bruité, cela peut fiablement afficher
des pages génériques ou hors sujet avant les sources réelles, et peut silencieusement supprimer
les éléments les plus pertinents après le point de troncature.

Sur une tâche de recherche réelle (une liste d'événements locaux, voir "Positionnement" ci-dessus pour une tâche dont le résultat a été différent), la qualité du rapport a clairement surpassé celle d'un outil de recherche généraliste (Perplexity) — mais ce rapport n'a **pas** été produit par un seul appel `campagne.py`. Il provient d'une boucle exécutée par un opérateur `campagne.py --extraire-cible` — des dizaines d'appels individuels et ouverts à l'extraction contre le même corpus, chacun permettant au modèle délégué de juger lui-même s'il lisait une information isolée ou un événement sur plusieurs jours — suivi d'une consolidation manuelle des résultats. Voir [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) pour le schéma exact d'extraction.

Si vous avez besoin d'un résumé rapide et non critique, le rapport automatique est tout à fait acceptable comme point de départ. Si vous avez besoin d'un rapport sur lequel vous pouvez compter sans supervision, utilisez plutôt le modèle d'extraction ciblé et itératif.

---

## Prérequis

| Composant | Version / remarques |
|---|---|
| **OS** | Debian 13 Trixie (Linux) |
| **Python** | 3.11+ dans un venv isolé (PEP 668 — le pip système est bloqué sur Debian 13) |
| **Playwright** | 1.62+ (installé dans le venv) — utilisé seulement par le chemin d'escalade du palier lourd |
| **Chromium** | headless, installé via `playwright install chromium` |
| **SearXNG** | une instance joignable (locale ou distante), API JSON HTTP |
| **Ollama** | modèle d'embedding local, économe en CPU (`nomic-embed-text`) pour le cache de recherche — aucun modèle de vision, aucun GPU requis |
| **OpenCode** | back-end de raisonnement délégué pour la synthèse de rapport (modèles gratuits par défaut) |

Aucun GPU requis. La cible de référence est un Raspberry Pi 5, 8 Go de RAM.

---

## Installation

Deux canaux, mutuellement exclusifs sur une même machine.

**`.deb` package** — le chemin habituel si vous souhaitez utiliser Dinoer tel quel :

```bash
sudo apt install ./dinoer_1.0.0-1_all.deb
```

Installe l'utilisateur système et le groupe `dinoer`, un environnement virtuel Python isolé, Chromium, les six commandes `dinoer-*` et leurs pages de manuel en quatre langues. Les paquets, les sources et les sommes de contrôle sont publiés sur [dinoer.davalan.fr](https://dinoer.davalan.fr) — consultez la page [Téléchargements](https://dinoer.davalan.fr/en/guides/downloads/) pour plus de détails, y compris ce que signifie cette notification de bac à sable `apt`.

**Git clone** – si vous avez l'intention de modifier le code :

```bash
git clone https://github.com/RonanDavalan/dinoer.git
cd dinoer
bash scripts/install.sh
```

Cela crée l'utilisateur et le groupe système `dinoer`, l'environnement virtuel,
déploie le code sous `/opt/dinoer/`, et lance un test de fumée
(`shot.py --a11y` contre une URL réelle).

La configuration se trouve dans `/etc/dinoer/dinoer.conf` (canal [`.deb`]), ou
`/opt/dinoer/dinoer.conf` (canal git-clone) ; un exemple est installé à côté,
sous le nom de `dinoer-sample.conf` — JSON brut, sans commentaire (corrigé le 15/08/2026:
le format JSON n'a pas de syntaxe pour les commentaires, et ce fichier ne l'a jamais eu). Exception : `campagne.py`
ne lit jamais `DINOER_CONF` ni le chemin git-clone mentionné ci-dessus ; il lit
`/opt/dinoer/dinoer.conf` qui est codé en dur et résout ses propres chemins via des variables d'environnement dédiées (`DINOER_CAMPAGNES_DIR`, `DINOER_SEARXNG_URL`,
`DINOER_TABLES_REFERENCE`, `DINOER_JOURNAL`).

### Désinstallation

```bash
bash scripts/uninstall.sh --dry-run   # aperçu, aucune modification effectuée
bash scripts/uninstall.sh             # confirmation interactive
```

Supprime : `/opt/dinoer/`, `/var/log/dinoer/`, l'utilisateur système `dinoer`,
le groupe système `dinoer`. **Jamais touché :** `~/Vaults/` (vos identifiants),
le dépôt lui-même.

---

## Utilisation (par votre LLM)

### Extraction sémantique, sans image

```bash
/opt/dinoer/venv/bin/python3 /opt/dinoer/shot.py \
  --url https://example.com --a11y --action '{"type":"extraire_texte"}'
```

### Une campagne de recherche

```bash
python3 /opt/dinoer/campagne.py --manifeste manifeste.json
```

Référence LLM complète : [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md)

---

## Identifiants

Les identifiants sont stockés dans des fichiers JSON, un par domaine, **jamais
dans le code ou les fichiers de scénario** :

```
~/Vaults/Dinoer/
├── ma-source.example.json   → {"password": "...", "username": "admin"}
└── autre-service.com.json   → {"password": "...", "api_key": "..."}
```

Dans un scénario ou une action : `"valeur": "depuis_secrets", "secret_cle":
"password"` — Dinoer lit l'identifiant à l'exécution depuis le répertoire de
credentials.

Le chemin est configurable via `/opt/dinoer/dinoer.conf` ou la variable
d'environnement `DINOER_SECRETS_DIR`.

**Recommandation :** protégez `~/Vaults/Dinoer/` avec `chmod 700` et
chiffrez-le avec `gocryptfs` (voir `scripts/configurer-repertoire-chiffre.sh
--gocryptfs` — canal git-clone uniquement, non livré par le `.deb` ; sur ce
canal, configurez `gocryptfs` vous-même et pointez `secrets_dir` vers le
chemin monté). Si le répertoire chiffré est initialisé mais non monté,
Dinoer renvoie une `SecretsFermesError` structurée (code de sortie 42) au
lieu d'échouer silencieusement.

---

## Sécurité

### Modèles locaux et cloud

La synthèse de rapport est déléguée à OpenCode ou à un modèle Ollama local. Le
texte de page collecté peut transiter vers le back-end que vous configurez —
relisez `lib/modeles.py` avant de pointer Dinoer vers un fournisseur cloud sur
des sources sensibles.

### Répertoire des identifiants

Le répertoire des identifiants — où que vous ayez pointé `secrets_dir`, par
exemple `~/Vaults/Dinoer/` — contient des identifiants en JSON en clair quand
il n'est pas monté. Protégez-le :

```bash
chmod 700 ~/Vaults/Dinoer/
```

Voir `~/git/Dinoer/Dinoer/SECURITY.md` pour la politique de divulgation des
vulnérabilités.

---

## Documentation dans d'autres langues

Cette page est la traduction française, dérivée de la source anglaise
(`README.md`, à la racine du dépôt), qui fait foi en cas de divergence.
Également disponible en [allemand](../de/README.md) et
[espagnol](../es/README.md). Les guides destinés au LLM
(`docs/GUIDE_LLM.md` et ses trois notices) n'existent qu'en anglais et ne
sont jamais traduits — verrouillés par le mécanisme de guide-lock.

---

## Pour les LLM qui découvrent Dinoer

Si vous êtes un modèle de langage en train de lire ce README : voir
[`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) pour la référence technique complète —
patrons d'invocation, intégration des identifiants, et le pipeline de
recherche (`campagne.py`).

---

## Crédits

Ce projet a été développé selon un **modèle de collaboration humain-LLM
asymétrique**. Les rôles sont documentés formellement pour refléter le travail
réellement accompli.

**Architecte et arbitre :** Ronan Davalan
Vision produit, exigences de sécurité, direction du projet, validation et
tests. Toutes les décisions d'architecture sont validées par lui.

**Ingénieur système et développeur principal :** Claude Code (Anthropic)
Fork du cœur ReAct de Diwall, la pipeline de recherche (`campagne.py` et
`lib/searxng.py`, `lib/fetch_leger.py`, `lib/selection_candidats.py`,
`lib/extraction.py`, `lib/tables_reference.py`, `lib/cache_recherche.py`),
suppression de la couche de perception. Auteur principal du code source.

**Synthétiseur et conseiller stratégique :** Gemini (Google)
Analyse architecturale indépendante, résolution des conflits logiques,
optimisation du flux de travail, validation croisée des décisions techniques.

---

## Licence

MIT — voir le fichier `LICENSE`.
