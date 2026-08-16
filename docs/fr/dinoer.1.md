% DINOER(1) | Commandes Dinoer
%
% Août 2026

# NOM

dinoer - boîte à outils d'automatisation web et de recherche basée sur ReAct, pour agents LLM

# RÉSUMÉ

**shot.py** \[*options*\] **--url** *URL*

**rpa.py** \[*options*\] **--scenario** *FICHIER*

**campagne.py** \[*options*\] **--manifeste** *FICHIER*

**journal.py** \[*options*\]

**scripts/monter-repertoire-chiffre.sh**

**scripts/demonter-repertoire-chiffre.sh**

**scripts/monitor-verifier.sh** **--scenario** *FICHIER* **--reference** *FICHIER*

# DESCRIPTION

Dinoer donne à un agent LLM des mains sur des interfaces web qu'il ne peut
autrement pas piloter : des actions Playwright pilotées par un cœur
d'exécution ReAct, avec un arbre d'accessibilité (`--a11y`) comme yeux
lorsque l'agent lit l'état. Chaque commande affiche un seul objet JSON sur
la sortie standard, conçu pour être lu par un programme plutôt que par un
humain.

Dinoer s'installe par un clone git déployé par **scripts/install.sh** sous
**/opt/dinoer/**. Un paquet `.deb` n'est délibérément pas encore proposé.
Les points d'entrée Python s'exécutent au travers de l'environnement
virtuel :

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py ...

Pour la liste exhaustive des options de n'importe quelle commande, lancez-la
avec **--help** — cette sortie fait toujours autorité sur cette page.

# COMMANDES

**shot.py**
: Capture une page et renvoie un JSON la décrivant. Avec **--a11y**, l'arbre
d'accessibilité est inclus. Des actions peuvent être exécutées dans la même
session de navigateur via **--actions** (un fichier JSON).
**--reprendre-session** réutilise les cookies seulement, jamais l'état du DOM.

**rpa.py**
: Exécute un fichier de scénario (JSON) décrivant une séquence d'actions, et
renvoie une ligne JSON. C'est la commande à utiliser pour tout ce qui est
répétable, et la seule qui évalue les assertions de scénario et prend en
charge **--replay-verifier**.

**campagne.py**
: Orchestre une campagne de recherche profonde depuis un manifeste JSON :
pagination par source, déduplication par cache vectoriel, extraction ciblée
sans synthèse. Lit sa configuration depuis **dinoer.conf**.

**journal.py**
: Lit le journal d'opérations en ajout seul à
**/var/log/dinoer/operations.jsonl**. Filtre par cible, date, mutabilité,
erreurs ou intention ; produit du texte brut ou du JSON.

**scripts/monter-repertoire-chiffre.sh**, **scripts/demonter-repertoire-chiffre.sh**
: Monte et démonte le répertoire d'identifiants chiffré par gocryptfs.
Dinoer refuse de résoudre le moindre identifiant tant qu'il est fermé, et se
termine avec le code de sortie 42 plutôt que de revenir à une méthode plus
faible. Configuré une fois par **scripts/configurer-repertoire-chiffre.sh**.

**scripts/monitor-verifier.sh**
: Exécute une passe de non-régression structurelle d'un scénario par
rapport à une référence enregistrée et se termine avec un code non nul en
cas de divergence. Destiné à être piloté par cron ou un minuteur systemd ;
ne contient aucune boucle propre.

# OPTIONS COURANTES

Les options ci-dessous sont partagées par **shot.py** et **rpa.py**, sauf
indication contraire. C'est une sélection, pas la liste complète.

**--guide-version** *X.Y*
: Preuve obligatoire que **/opt/dinoer/docs/GUIDE_LLM.md** a été lu. Sans
elle — et sans un marqueur local encore valide —, la commande refuse de
s'exécuter et se termine avec le code 1. La valeur attendue est le
commentaire *notice-version* à la ligne 3 de ce guide. C'est le seul
endroit où Dinoer n'est pas optionnel.

**--version**
: Affiche la version installée en JSON et quitte, sans lancer de navigateur.
Distinct de **--guide-version** ; les deux numéros n'ont aucun lien.

**--a11y**
: Inclut l'arbre d'accessibilité dans la sortie JSON. L'agent lit le DOM au
travers de cet arbre ; Dinoer n'a aucun chemin de capture d'écran ou
d'image.

**--wait-until** *networkidle*|*load*|*domcontentloaded*
: Quand la navigation initiale est considérée terminée. Par défaut,
*networkidle* attend 500 ms de silence réseau et convient à la plupart des
cibles. Une page qui interroge en continu ne devient jamais silencieuse —
utilisez *load* dans ce cas ; augmenter **--timeout** ne peut pas aider,
puisque la page ne se terminera jamais.

**--timeout** *MS*
: Délai d'expiration par opération en millisecondes (par défaut 10000).

**--stealth**
: Retire les marqueurs automatiques qui identifient un navigateur headless.
Cela ne change pas l'adresse IP de l'opérateur et ne forge aucune identité —
le but est un traitement équitable, pas un déguisement.

**--secrets** *FICHIER*
: Résout les identifiants depuis un fichier JSON explicite à l'intérieur
d'un répertoire monté, au lieu de la recherche par défaut fondée sur
l'hôte. Ne passez jamais de mot de passe sur la ligne de commande : les
champs de scénario utilisent `"depuis_secrets"` plus `secret_cle`, et
l'identifiant est résolu à l'intérieur de Playwright.

**--no-evaluer**
: Refuse l'action **evaluer** pour toute l'exécution — aucun JavaScript
arbitraire n'est exécuté sur la page cible.

**--no-filtre-evaluer**
: Désactive la neutralisation sur stdout des valeurs de retour d'**evaluer**,
des URLs et des messages d'erreur — exécutions de débogage explicites
seulement. La neutralisation est active par défaut ; quand elle est
désactivée, `boussole.filtre_evaluer_actif: false` est posé dans la sortie
pour que l'opérateur puisse l'auditer depuis le JSON lui-même.

**--replay-verifier** *FICHIER*
: Compare l'exécution en cours à une référence enregistrée et se termine
avec un code non nul en cas de divergence. La référence est écrite par
**--sauver-verifier-reference**. **rpa.py** uniquement.

# FICHIERS

**/etc/dinoer/dinoer.conf**
: Configuration lue par **campagne.py** et le résolveur d'identifiants.
Créée par l'opérateur, jamais générée automatiquement. La variable
d'environnement **DINOER_CONF** remplace ce chemin. `secrets_dir` à
l'intérieur pointe vers le répertoire d'identifiants monté.

**/opt/dinoer/**
: Code applicatif, environnement virtuel Python, et documentation à
laquelle les commandes elles-mêmes font référence.

**/opt/dinoer/docs/GUIDE_LLM.md**
: Le point d'entrée qu'un agent doit lire. **MANUEL.md** dans le même
répertoire contient les commandes exactes avec les chemins réels.

**/var/log/dinoer/**
: Journal d'opérations en ajout seul (`operations.jsonl`) et répertoire de
preuves structurées. Préservé lors des redéploiements.

**/tmp/dinoer/**
: Répertoire de travail éphémère par exécution, effacé au redémarrage.

# CODE DE RETOUR

**0**
: L'exécution s'est terminée. Notez qu'un code HTTP 404 ou 403 sur la
cible est rapporté dans le JSON, pas comme un échec de la commande.

**1**
: L'exécution a échoué, ou la vérification préalable de lecture du guide
n'a pas été satisfaite (*guide_non_lu*).

**2**
: Arguments incompatibles, rejetés avant tout lancement de navigateur.

**42**
: Le répertoire d'identifiants est fermé, ou un fichier d'identifiants a
échoué à sa somme de contrôle d'intégrité. Montez-le avec
**scripts/monter-repertoire-chiffre.sh**, ou vérifiez le fichier
d'identifiants si le message signale une somme de contrôle invalide.

**43**
: Aucun **secrets_dir** configuré. Configurez-le dans **dinoer.conf**, ou indiquez
**DINOER_CONF** vers un fichier de configuration spécifique au projet.

# EXEMPLES

Capturer une page avec l'arbre d'accessibilité :

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url https://example.com --a11y --guide-version 1.3

Lire seulement l'état d'une page, sans exécuter aucune action :

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url https://example.com --guide-version 1.3

Atteindre un panneau d'administration qui rafraîchit ses statistiques en
continu :

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url http://target.local/ --wait-until load --a11y

Exécuter un scénario avec des identifiants depuis un fichier explicite :

    /opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
        --scenario ./login.json --secrets ~/Vaults/project/creds.json

Vérifier qu'une page n'a pas régressé structurellement :

    bash scripts/monitor-verifier.sh --scenario ./page.json --reference ./page.ref.json

Lire le journal d'opérations pour une cible :

    /opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible example.com --format json

# VOIR AUSSI

La documentation complète est installée avec le paquet :
**/opt/dinoer/docs/MANUEL.md** pour le manuel de l'opérateur,
**/opt/dinoer/docs/GUIDE_LLM.md** pour le guide destiné à l'agent,
**/opt/dinoer/docs/FAQ_LLM.md** pour les réponses classées par version.
