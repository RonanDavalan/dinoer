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

## Architecture

```
campagne.py (orchestration)
  ├─ lib/searxng.py         → API JSON SearXNG (HTTP seul, sans navigateur)
  ├─ lib/fetch_leger.py     → requests + BeautifulSoup, respecte robots.txt
  ├─ rpa.py / shot.py       → Playwright, seulement pour les pages que le palier
  │                           léger a marquées « insuffisant » (coquilles JS pures)
  ├─ lib/extraction.py      → extraction ciblée de faits, trouve/valeur/url
  ├─ lib/tables_reference.py→ table persistante et sourcée de sites de référence
  ├─ lib/cache_recherche.py → cache de recherche adossé à ChromaDB
  └─ lib/synthese.py + lib/modeles.py → LLM délégué (OpenCode/Ollama),
                                        rédige le rapport final
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

## Qualité du rapport : brouillon automatique vs. recherche supervisée

Le rapport de fin de course de `campagne.py` (`lib/synthese.py::rediger_rapport()`)
est un **brouillon de travail**, pas le livrable poli : il concatène le corpus
collecté dans l'ordre du fichier, tronqué à 4000 caractères/page et 60 000 au
total — aucune priorisation par pertinence. Sur un corpus large et bruité, ça
laisse passer des pages génériques ou hors-sujet avant les vraies sources, et
peut faire disparaître silencieusement les pages les plus pertinentes derrière
le seuil de troncature.

Le rapport qui a démontré sa supériorité sur un outil de recherche généraliste
(Perplexity) sur une tâche de recherche réelle n'a **pas** été produit par une
seule exécution de `campagne.py`. Il vient d'un opérateur bouclant `campagne.py
--extraire-cible` — des dizaines d'appels d'extraction individuels et ouverts
contre le même corpus collecté, chacun laissant le modèle délégué juger
lui-même s'il lisait un fait ponctuel ou un événement sur plusieurs jours —
suivis d'une consolidation manuelle des résultats. Voir
[`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) pour le motif d'extraction exact.

Pour un résumé rapide et non critique, le rapport automatique suffit comme
point de départ. Pour un rapport fiable sans supervision, utilisez le motif
d'extraction ciblée en boucle.

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

Canal git-clone uniquement. **Aucun paquet `.deb` n'est proposé pour le
moment** — l'empaquetage est délibérément différé jusqu'à stabilisation du
produit.

```bash
git clone https://github.com/RonanDavalan/dinoer.git
cd dinoer
bash scripts/install.sh
```

Cela crée l'utilisateur et le groupe système `dinoer`, l'environnement virtuel,
déploie le code sous `/opt/dinoer/`, et lance un test de fumée
(`shot.py --a11y` contre une URL réelle).

La configuration vit dans `/etc/dinoer/dinoer.conf` (ou `/opt/dinoer/dinoer.conf`
selon votre cible `deploy.sh`) ; un exemple commenté est installé à côté sous le
nom `dinoer-sample.conf`.

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
--gocryptfs`). Si le répertoire chiffré est initialisé mais non monté, Dinoer
renvoie une `SecretsFermesError` structurée (code de sortie 42) plutôt que
d'échouer silencieusement.

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
Fork du cœur ReAct de Diwall, du pipeline de recherche (`campagne.py` et
`lib/searxng.py`, `lib/fetch_leger.py`, `lib/extraction.py`,
`lib/tables_reference.py`, `lib/cache_recherche.py`), retrait de la couche de
perception. Auteur principal du code source.

**Synthétiseur et conseiller stratégique :** Gemini (Google)
Analyse architecturale indépendante, résolution des conflits logiques,
optimisation du flux de travail, validation croisée des décisions techniques.

---

## Licence

MIT — voir le fichier `LICENSE`.
