#!/usr/bin/env python3
"""
campagne.py — Orchestration d'une campagne de recherche profonde Dinoer.

Couche nouvelle au-dessus de `rpa.py` (DINOER_RESEARCH.md §10), distincte du
mécanisme `--checkpoint` existant : ce dernier reprend une session Playwright
interrompue au milieu d'une interaction avec un seul site (état de
navigateur préservé). `campagne.py` orchestre des cibles indépendantes (URLs
fixes, requêtes SearXNG) où l'échec de l'une ne doit jamais compromettre les
autres — chaque cible passe par son propre appel isolé (`lib/fetch_leger`
en process, `rpa.py` en sous-processus pour l'escalade lourde), jamais une
liste d'actions unique qui s'interromprait au premier échec.

Deux artefacts distincts en sortie (§4) :
  - `operations.jsonl` (`lib/journal.py`, existant, partagé) — trace toute
    tentative, réussie ou non, taguée `intention="dinoer-campagne"`.
  - `<repertoire_campagnes>/<id_campagne>/collecte.jsonl` (nouveau, par
    campagne) — une ligne par extraction réussie uniquement ; c'est
    l'artefact que lira le traitement du matin (chunking, RAG, synthèse —
    non implémenté dans ce lot).

Usage :
  python3 campagne.py --manifeste manifeste.json

Format du manifeste (JSON) :
  {
    "id_campagne": "concerts-finistere-2026-07-28",
    "cibles": [
      {"type": "query", "valeur": "concerts finistere sud ete"},
      {"type": "url", "valeur": "https://exemple.fr/agenda"},
      {"type": "produit", "valeur": "boulangerie Corentin a Quimper", "max_candidats": 5},
      {"type": "table_reference", "valeur": "mairies du Finistere sud", "cle_thematique": "mairies_finistere_sud"}
    ],
    "max_resultats": 15,
    "max_pages_recherche_securite": 20,
    "max_pages_par_hostname": 3,
    "delai_min_secondes": 4.5,
    "delai_max_secondes": 8.5,
    "revisite_apres_jours": 30,
    "max_candidats_produit": 5
  }
Seuls "id_campagne" et "cibles" sont requis ; les autres champs reprennent
les défauts documentés dans DINOER_RESEARCH.md §7-9 s'ils sont absents.

Cible de type "produit" (volet B, fonctionnalité 2 — `lib/selection_candidats.py`,
TACHE_volet_b_recherche_avancee.md §2) : au lieu de retenir tous les résultats
d'une recherche comme le type "query", collecte jusqu'à "max_candidats"
(cible) ou "max_candidats_produit" (manifeste, défaut 5) pages candidates
puis fait choisir à OpenCode celle qui correspond réellement à la cible — la
« page produit », jamais une page de résultats, un annuaire ou une page
hors-sujet. Un seul candidat entre dans le corpus par cible "produit"
(source "produit", ou "produit_lourd" si escaladée au palier lourd faute de
candidat léger suffisant) ; aucun si le modèle juge qu'aucun candidat ne
convient.

Extraction ciblée sans synthèse (volet B, fonctionnalité 1 —
`lib/extraction.py`) : opère sur un corpus déjà collecté, sans relancer de
campagne.
  python3 campagne.py --extraire-cible "horaires de la mairie" --id-campagne concerts-finistere-2026-07-28
  python3 campagne.py --extraire-cible "date du concert" --corpus /chemin/vers/collecte.jsonl --format-extraction markdown

Cible de type "table_reference" (volet B, fonctionnalité 3 —
`lib/tables_reference.py`, TACHE_volet_b_recherche_avancee.md §3) : résout
une liste de domaines de confiance pour "cle_thematique" (fichier persistant
hors arbre déployé, résolu par `DINOER_TABLES_REFERENCE`/`dinoer.conf` ; à
défaut de "cle_thematique" explicite, dérivée de "valeur" par slug) — repli
sur une génération OpenCode si la clé est absente, résultat enregistré pour
les campagnes suivantes. Lance ensuite une recherche `site:<domaine> <valeur>`
par domaine retenu, jamais une visite directe du domaine racine.

Cache de recherche (volet B, fonctionnalité 4 — `lib/cache_recherche.py`) :
pour chaque cible de type "query", le cache est interrogé avant tout appel
SearXNG. Un hit sert directement les pages déjà collectées pour une requête
sémantiquement proche (marquées `"source": "cache"` dans le corpus) sans
refetch ni nouvelle recherche. Un manque, comme une campagne réussie, ré-
alimente le cache. Désactivable par `--desactiver-cache` ou la clé de
manifeste `"desactiver_cache": true`. Best-effort : ChromaDB/Ollama
indisponibles dégradent en cache toujours manqué, jamais en échec de
campagne.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from lib import cache_recherche, tables_reference
from lib.fetch_leger import recuperer
from lib.searxng import SearxngNonConfigureError, rechercher
from lib.selection_candidats import SelectionIntrouvableError, selectionner_meilleur

__version__ = "0.1.0"

_CONF_PATH = "/opt/dinoer/dinoer.conf"
_INTENTION_CAMPAGNE = "dinoer-campagne"
_STATUT_REFUS_DEFINITIF = "refusee"

_DEFAUT_MAX_RESULTATS = 15
_DEFAUT_MAX_PAGES_SECURITE = 20
_DEFAUT_MAX_PAGES_PAR_HOSTNAME = 3
_DEFAUT_DELAI_MIN_S = 4.5
_DEFAUT_DELAI_MAX_S = 8.5
_DEFAUT_FENETRE_FRAICHEUR_JOURS = 30
_DEFAUT_MAX_CANDIDATS_PRODUIT = 5


def _charger_manifeste(chemin: str) -> dict:
    with open(chemin, encoding="utf-8") as f:
        manifeste = json.load(f)
    if not manifeste.get("id_campagne"):
        raise ValueError("manifeste invalide : champ 'id_campagne' requis")
    if not manifeste.get("cibles"):
        raise ValueError("manifeste invalide : champ 'cibles' requis (liste non vide)")
    return manifeste


def _repertoire_campagnes() -> str:
    """Résolution du répertoire racine des corpus de campagne — même cascade
    que `lib/journal.py::_journal_path()` (env → conf → défaut), pour rester
    cohérent avec l'emplacement de `/var/log/dinoer/operations.jsonl`."""
    if "DINOER_CAMPAGNES_DIR" in os.environ:
        return os.path.expanduser(os.environ["DINOER_CAMPAGNES_DIR"])
    if os.path.isfile(_CONF_PATH):
        try:
            with open(_CONF_PATH, encoding="utf-8") as f:
                conf = json.load(f)
            if "campagnes_dir" in conf:
                return os.path.expanduser(conf["campagnes_dir"])
        except (OSError, json.JSONDecodeError):
            pass
    return "/var/log/dinoer/campagnes"


def _hostname(url: str) -> str:
    return urlparse(url).netloc.lower()


def _slugifier(texte: str) -> str:
    """Dérive une clé thématique stable depuis un texte libre — utilisé
    quand une cible "table_reference" ne fournit pas explicitement
    "cle_thematique" (volet B fonctionnalité 3)."""
    texte = re.sub(r"[^a-z0-9]+", "_", texte.strip().lower())
    return texte.strip("_")


def _construire_index_dedup(fenetre_fraicheur_jours: int) -> dict:
    """Un seul passage sur `operations.jsonl` au démarrage de la campagne
    (DINOER_RESEARCH.md §7.1) — jamais un scan répété par cible. Réutilise
    le résolveur privé de `lib/journal.py` plutôt que de dupliquer sa
    logique de cascade (risque de divergence si `DINOER_JOURNAL`/la conf
    changent).

    Retourne `{url: True}` pour chaque URL à ignorer cette campagne — trois
    régimes de péremption (§7.3) :
      - `resultat == "succes"` et plus récent que la fenêtre de fraîcheur
        → ignorée (retirée de l'index si la fraîcheur a expiré) ;
      - `erreur == "refusee"` → ignorée indéfiniment (refus définitif) ;
      - tout le reste (échec transitoire, insuffisance déjà réévaluée) →
        jamais mémorisé comme définitif, toujours éligible.
    Ne filtre que les entrées taguées `intention="dinoer-campagne"` : le
    journal est partagé avec tout usage de Dinoer, une entrée sans ce tag
    n'a aucune valeur de déduplication pour une campagne de recherche.
    """
    from lib.journal import _journal_path

    index: dict[str, bool] = {}
    try:
        chemin = _journal_path()
        limite_fraicheur = datetime.now(timezone.utc) - timedelta(days=fenetre_fraicheur_jours)
        with open(chemin, encoding="utf-8") as f:
            for ligne in f:
                ligne = ligne.strip()
                if not ligne:
                    continue
                try:
                    entree = json.loads(ligne)
                except json.JSONDecodeError:
                    continue
                if entree.get("intention") != _INTENTION_CAMPAGNE:
                    continue
                url = entree.get("cible_url")
                if not url:
                    continue

                if entree.get("resultat") == "succes":
                    try:
                        ts = datetime.fromisoformat(entree["ts"])
                    except (KeyError, ValueError):
                        continue
                    if ts >= limite_fraicheur:
                        index[url] = True
                    else:
                        index.pop(url, None)
                elif entree.get("erreur") == _STATUT_REFUS_DEFINITIF:
                    index[url] = True
                else:
                    index.pop(url, None)
    except (FileNotFoundError, OSError):
        pass
    return index


def _journaliser_leger(url: str, resultat_fetch: dict) -> None:
    from lib.journal import enregistrer_operation

    statut = resultat_fetch["statut"]
    enregistrer_operation(
        outil="campagne.py",
        version=__version__,
        cible_url=url,
        resultat="succes" if statut == "visitee" else "echec",
        actions=[],
        intention=_INTENTION_CAMPAGNE,
        erreur=None if statut == "visitee" else statut,
        mutatif=False,
    )


def _ajouter_au_corpus(
    chemin_corpus: str, url: str, resultat_fetch: dict, requete_source,
    source: str = "fraiche", date_capture: str | None = None,
) -> dict:
    """Écrit une entrée dans le corpus de campagne. `source` distingue une
    extraction fraîche ("fraiche") d'un hit de cache sémantique ("cache",
    volet B fonctionnalité 4) — jamais indiscernable l'un de l'autre, pour
    rester auditable. `date_capture` : réutilisée telle quelle pour un hit de
    cache (date de la collecte originale, pas de cette relecture) ; générée
    à l'instant sinon. Retourne l'entrée écrite, pour permettre à l'appelant
    de la ré-indexer dans le cache sans la reconstruire."""
    os.makedirs(os.path.dirname(chemin_corpus), exist_ok=True)
    entree = {
        "url": url,
        "titre": resultat_fetch.get("titre"),
        "texte": resultat_fetch.get("texte"),
        "date_capture": date_capture or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "requete_source": requete_source,
        "source": source,
    }
    with open(chemin_corpus, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")
    return entree


def _escalader_lourd(url: str) -> dict:
    """Invoque `rpa.py` en sous-processus pour extraire le texte via
    Playwright (palier lourd, §3.3) — uniquement sur les cibles marquées
    `insuffisante_legere`, jamais par défaut. Isolation par sous-processus :
    un échec ici ne doit jamais interrompre la boucle appelante (§10), même
    mécanisme que `rpa.py` vis-à-vis de `shot.py`.

    Ne gère aucun refus WAF explicitement ici : un refus au palier lourd
    n'existe pas dans ce flux — seules les cibles `insuffisante_legere`
    (jamais `refusee`) atteignent cette fonction, conformément à la
    doctrine §6 (un refus n'est jamais escaladé).
    """
    import subprocess

    from lib.preflight_guide import GUIDE_VERSION_ATTENDUE

    rpa_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rpa.py")
    scenario = {"url": url, "actions": [{"type": "extraire_texte"}]}
    chemin_scenario = os.path.join(
        "/tmp", f"dinoer_campagne_{uuid.uuid4().hex}.json"
    )
    with open(chemin_scenario, "w", encoding="utf-8") as f:
        json.dump(scenario, f)

    try:
        resultat = subprocess.run(
            [sys.executable, rpa_py,
             "--scenario", chemin_scenario,
             "--guide-version", GUIDE_VERSION_ATTENDUE,
             "--intention", _INTENTION_CAMPAGNE],
            capture_output=True, text=True, timeout=120,
        )
        try:
            sortie = json.loads(resultat.stdout.strip().splitlines()[-1]) if resultat.stdout.strip() else None
        except json.JSONDecodeError:
            sortie = None

        if not sortie:
            return {"statut": "echec_transitoire", "url": url, "titre": None,
                     "texte": None, "raison": "sortie_rpa_illisible"}
        if not sortie.get("succes"):
            return {"statut": "refusee", "url": url, "titre": None, "texte": None,
                     "raison": sortie.get("erreur", "echec_palier_lourd")}

        extraction = sortie.get("extraction_texte") or {}
        texte = extraction.get("texte")
        if not texte:
            return {"statut": "refusee", "url": url, "titre": extraction.get("titre"),
                     "texte": None, "raison": "aucun_texte_extrait_palier_lourd"}
        return {"statut": "visitee_lourde", "url": url, "titre": extraction.get("titre"),
                 "texte": texte, "raison": None}
    except subprocess.TimeoutExpired:
        return {"statut": "echec_transitoire", "url": url, "titre": None, "texte": None,
                 "raison": "timeout_palier_lourd"}
    finally:
        try:
            os.remove(chemin_scenario)
        except OSError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dinoer — orchestration d'une campagne de recherche profonde"
    )
    parser.add_argument("--manifeste", required=False,
                         help="Chemin vers le manifeste de campagne (JSON)")
    parser.add_argument("--desactiver-cache", action="store_true",
                         help="Ignore le cache de recherche vectoriel pour cette campagne "
                              "(volet B, fonctionnalité 4) — recherche et refetch systématiques.")
    parser.add_argument("--purger-cache", action="store_true",
                         help="Vide entièrement le cache de recherche et quitte, sans lancer "
                              "de campagne (aucun --manifeste requis).")
    parser.add_argument("--purger-cache-avant-jours", type=int, default=None, metavar="N",
                         help="Purge uniquement les entrées du cache plus vieilles que N jours "
                              "et quitte, sans lancer de campagne (aucun --manifeste requis).")
    parser.add_argument("--extraire-cible", default=None, metavar="CIBLE",
                         help="Extrait une donnée précise (mot, phrase, date, nom...) d'un "
                              "corpus déjà collecté et quitte, sans lancer de campagne. "
                              "Requiert --id-campagne ou --corpus.")
    parser.add_argument("--id-campagne", default=None,
                         help="Identifiant de campagne dont le corpus sert de base à "
                              "--extraire-cible (résout <repertoire_campagnes>/<id>/collecte.jsonl).")
    parser.add_argument("--corpus", default=None,
                         help="Chemin direct vers un collecte.jsonl — alternative à "
                              "--id-campagne pour --extraire-cible.")
    parser.add_argument("--format-extraction", choices=["json", "markdown", "html"], default="json",
                         help="Format de sortie de --extraire-cible (défaut : json).")
    args = parser.parse_args()

    if args.purger_cache or args.purger_cache_avant_jours is not None:
        n = cache_recherche.purger(avant_jours=args.purger_cache_avant_jours)
        print(f"Cache de recherche purgé : {n} entrée(s) supprimée(s).")
        return

    if args.extraire_cible:
        chemin_corpus_extraction = args.corpus or (
            os.path.join(_repertoire_campagnes(), args.id_campagne, "collecte.jsonl")
            if args.id_campagne else None
        )
        if not chemin_corpus_extraction:
            print("⚠ --extraire-cible requiert --id-campagne ou --corpus.", file=sys.stderr)
            sys.exit(1)

        from lib.extraction import ExtractionIntrouvableError, extraire_cible
        try:
            print(extraire_cible(chemin_corpus_extraction, args.extraire_cible, args.format_extraction))
        except (RuntimeError, ExtractionIntrouvableError) as e:
            print(f"⚠ extraction échouée : {type(e).__name__} : {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.manifeste:
        print("⚠ --manifeste est requis en dehors d'une purge de cache (--purger-cache*) ou "
              "d'une extraction ciblée (--extraire-cible).", file=sys.stderr)
        sys.exit(1)

    try:
        manifeste = _charger_manifeste(args.manifeste)
    except (OSError, ValueError) as e:
        # ValueError couvre json.JSONDecodeError (manifeste JSON malformé) et
        # les erreurs de _charger_manifeste elle-même (champs requis absents).
        # PHASE_VALIDATION (28/07/2026) : un manifeste cassé produisait une
        # trace Python brute plutôt qu'un message actionnable — corrigé.
        print(f"⚠ manifeste invalide ({args.manifeste!r}) : {e}", file=sys.stderr)
        sys.exit(1)

    id_campagne = manifeste["id_campagne"]
    max_resultats = int(manifeste.get("max_resultats", _DEFAUT_MAX_RESULTATS))
    max_pages_securite = int(manifeste.get("max_pages_recherche_securite", _DEFAUT_MAX_PAGES_SECURITE))
    max_par_hostname = int(manifeste.get("max_pages_par_hostname", _DEFAUT_MAX_PAGES_PAR_HOSTNAME))
    delai_min = float(manifeste.get("delai_min_secondes", _DEFAUT_DELAI_MIN_S))
    delai_max = float(manifeste.get("delai_max_secondes", _DEFAUT_DELAI_MAX_S))
    fenetre_fraicheur = int(manifeste.get("revisite_apres_jours", _DEFAUT_FENETRE_FRAICHEUR_JOURS))
    desactiver_cache = bool(args.desactiver_cache or manifeste.get("desactiver_cache"))

    chemin_corpus = os.path.join(_repertoire_campagnes(), id_campagne, "collecte.jsonl")
    index_dedup = _construire_index_dedup(fenetre_fraicheur)
    compteur_hostname: dict = {}
    urls_retenues = 0
    file_insuffisantes: list = []

    def _cible_eligible(url: str) -> bool:
        if url in index_dedup:
            return False
        return compteur_hostname.get(_hostname(url), 0) < max_par_hostname

    def _traiter_url(url: str, requete_source) -> dict | None:
        nonlocal urls_retenues
        resultat = recuperer(url)
        _journaliser_leger(url, resultat)
        entree = None
        if resultat["statut"] == "visitee":
            entree = _ajouter_au_corpus(chemin_corpus, url, resultat, requete_source)
            urls_retenues += 1
            compteur_hostname[_hostname(url)] = compteur_hostname.get(_hostname(url), 0) + 1
        elif resultat["statut"] == "insuffisante_legere":
            file_insuffisantes.append(url)
            compteur_hostname[_hostname(url)] = compteur_hostname.get(_hostname(url), 0) + 1
        # refusee / echec_transitoire : déjà journalisé, rien de plus à faire ici.
        time.sleep(random.uniform(delai_min, delai_max))
        return entree

    def _traiter_cible_produit(valeur: str, max_candidats: int) -> None:
        """Cible "produit" (volet B, fonctionnalité 2) : collecte jusqu'à
        `max_candidats` pages, fait choisir la meilleure par
        `selectionner_meilleur()`, n'écrit que celle-là au corpus — jamais
        tous les candidats testés, contrairement au type "query"."""
        nonlocal urls_retenues
        candidats_bruts: list[tuple[str, dict]] = []
        page = 1
        while page <= max_pages_securite and len(candidats_bruts) < max_candidats:
            urls = rechercher(valeur, page=page)
            # Discipline anti-ban (§9 DINOER_RESEARCH.md) étendue à l'appel
            # SearXNG lui-même, pas seulement aux pages retenues : une cible
            # sans URL éligible enchaînait sinon immédiatement sur l'appel
            # suivant, sans délai — root cause d'une suspension réelle des
            # moteurs sous-jacents (Brave/DuckDuckGo/Startpage) constatée en
            # exécution le 12/08/2026 (pipeline territorial).
            time.sleep(random.uniform(delai_min, delai_max))
            if not urls:
                break
            for url in urls:
                if len(candidats_bruts) >= max_candidats:
                    break
                if not _cible_eligible(url):
                    continue
                resultat = recuperer(url)
                _journaliser_leger(url, resultat)
                if resultat["statut"] in ("visitee", "insuffisante_legere"):
                    candidats_bruts.append((url, resultat))
                    compteur_hostname[_hostname(url)] = compteur_hostname.get(_hostname(url), 0) + 1
                # refusee / echec_transitoire : déjà journalisé, non retenu comme candidat.
                time.sleep(random.uniform(delai_min, delai_max))
            page += 1

        candidats_legers = [
            {"url": url, "titre": r.get("titre"), "texte": r.get("texte")}
            for url, r in candidats_bruts if r["statut"] == "visitee"
        ]

        try:
            retenu = selectionner_meilleur(valeur, candidats_legers)
        except (RuntimeError, SelectionIntrouvableError) as e:
            # RuntimeError couvre aussi les échecs génériques d'invoquer_opencode()
            # (binaire absent, timeout) — pas seulement SelectionIntrouvableError
            # (sortie non conforme). Un échec de sélection ne doit jamais faire
            # échouer toute la campagne, même discipline que la synthèse finale
            # (bug trouvé en PHASE_VALIDATION du 09/08/2026 : un RuntimeError non
            # catché ici faisait planter campagne.py entièrement, exit 1).
            print(f"⚠ sélection de candidat échouée pour {valeur!r} : "
                  f"{type(e).__name__} : {e}", file=sys.stderr)
            retenu = None

        if retenu:
            _ajouter_au_corpus(chemin_corpus, retenu["url"], retenu, valeur, source="produit")
            urls_retenues += 1
            return

        # Aucun candidat léger retenu : tente l'escalade lourde sur les
        # candidats marqués insuffisante_legere, dans l'ordre de découverte —
        # premier qui produit du texte exploitable, retenu directement. Pas
        # de deuxième passe de sélection comparative sur le palier lourd
        # (coûteux, hors périmètre de ce lot, cf. TACHE_volet_b_recherche_avancee.md §2).
        for url, r in candidats_bruts:
            if r["statut"] != "insuffisante_legere":
                continue
            resultat_lourd = _escalader_lourd(url)
            if resultat_lourd["statut"] == "visitee_lourde":
                _ajouter_au_corpus(chemin_corpus, url, resultat_lourd, valeur, source="produit_lourd")
                urls_retenues += 1
                return
            time.sleep(random.uniform(delai_min, delai_max))

    def _traiter_cible_table_reference(valeur: str, cle_thematique: str) -> None:
        """Cible "table_reference" (volet B, fonctionnalité 3) : résout une
        liste de domaines de confiance pour `cle_thematique` (fichier
        persistant, repli génération OpenCode si absente — `lib/tables_reference.py`),
        puis lance une recherche `site:<domaine> <valeur>` par domaine —
        recherche générique restreinte, jamais une visite directe du domaine
        racine (qui n'atterrirait pas forcément sur le contenu pertinent,
        cf. TACHE_volet_b_recherche_avancee.md §3). Réutilise `_traiter_url()`
        et donc la déduplication/plafond par hostname existants sans les
        dupliquer."""
        entrees = tables_reference.charger(cle_thematique)
        if entrees is None:
            try:
                entrees = tables_reference.generer_et_enregistrer(cle_thematique, valeur)
            except (RuntimeError, tables_reference.GenerationTableIntrouvableError) as e:
                print(f"⚠ génération de la table de référence échouée pour "
                      f"{cle_thematique!r} : {type(e).__name__} : {e}", file=sys.stderr)
                entrees = []

        if not entrees:
            print(f"⚠ aucun domaine de référence disponible pour {cle_thematique!r} "
                  f"({valeur!r}) — cible ignorée.", file=sys.stderr)
            return

        trouvees = 0
        for entree in entrees:
            if trouvees >= max_resultats:
                break
            domaine = entree.get("domaine")
            if not domaine:
                continue
            requete_ciblee = f"site:{domaine} {valeur}"
            page = 1
            while page <= max_pages_securite and trouvees < max_resultats:
                urls = rechercher(requete_ciblee, page=page)
                time.sleep(random.uniform(delai_min, delai_max))
                if not urls:
                    break
                for url in urls:
                    if trouvees >= max_resultats:
                        break
                    if not _cible_eligible(url):
                        continue
                    _traiter_url(url, valeur)
                    trouvees += 1
                page += 1

    for cible in manifeste["cibles"]:
        type_cible = cible.get("type")
        valeur = cible.get("valeur")
        if not type_cible or not valeur:
            print(f"⚠ cible ignorée, champ 'type' ou 'valeur' manquant : {cible!r}", file=sys.stderr)
            continue

        if type_cible == "url":
            if _cible_eligible(valeur):
                _traiter_url(valeur, None)
            continue

        if type_cible == "query":
            # Cache de recherche (volet B, fonctionnalité 4) : un hit sert les
            # pages d'une requête sémantiquement proche déjà collectée
            # récemment, sans appel SearXNG ni refetch. Simplification assumée
            # de ce premier lot : un hit remplace entièrement la recherche
            # live pour cette cible, même si le cache contient moins de pages
            # que max_resultats — pas de complément live partiel. À affiner
            # si l'usage réel montre que cette simplification coûte trop de
            # rappel (cf. TACHE_volet_b_recherche_avancee.md §4).
            if not desactiver_cache:
                hits = cache_recherche.verifier(valeur, fenetre_jours=fenetre_fraicheur)
                hits_retenus = [h for h in hits if _cible_eligible(h["url"])][:max_resultats]
                if hits_retenus:
                    for hit in hits_retenus:
                        # Journalisé comme une extraction fraîche réussie :
                        # sans cette écriture, un hit de cache ne laisse
                        # aucune trace dans operations.jsonl, et la même URL
                        # serait resservie indéfiniment à chaque rejeu de
                        # cette requête dans la fenêtre de fraîcheur (la
                        # déduplication §7 est dérivée exclusivement du
                        # journal — bug trouvé et corrigé en PHASE_VALIDATION
                        # du 09/08/2026, corpus dupliqué observé en test).
                        _journaliser_leger(hit["url"], {"statut": "visitee"})
                        _ajouter_au_corpus(
                            chemin_corpus, hit["url"], hit, valeur,
                            source="cache", date_capture=hit.get("date_capture"),
                        )
                        urls_retenues += 1
                        compteur_hostname[_hostname(hit["url"])] = (
                            compteur_hostname.get(_hostname(hit["url"]), 0) + 1
                        )
                    continue

            page = 1
            trouvees_pour_requete = 0
            pages_pour_cache: list[dict] = []
            # Boucle jusqu'au premier des deux seuils atteints (§8) : N URLs
            # retenues, ou plafond de pages de sécurité (SearXNG épuisé ou
            # requête à faible renouvellement dont la plupart des résultats
            # sont déjà dans l'index de déduplication).
            while page <= max_pages_securite and trouvees_pour_requete < max_resultats:
                urls = rechercher(valeur, page=page)
                time.sleep(random.uniform(delai_min, delai_max))
                if not urls:
                    break
                for url in urls:
                    if trouvees_pour_requete >= max_resultats:
                        break
                    if not _cible_eligible(url):
                        continue
                    entree = _traiter_url(url, valeur)
                    if entree:
                        pages_pour_cache.append(entree)
                    trouvees_pour_requete += 1
                page += 1

            if not desactiver_cache and pages_pour_cache:
                cache_recherche.indexer(valeur, pages_pour_cache)
            continue

        if type_cible == "produit":
            max_candidats = int(
                cible.get("max_candidats")
                or manifeste.get("max_candidats_produit", _DEFAUT_MAX_CANDIDATS_PRODUIT)
            )
            _traiter_cible_produit(valeur, max_candidats)
            continue

        if type_cible == "table_reference":
            cle_thematique = cible.get("cle_thematique") or _slugifier(valeur)
            _traiter_cible_table_reference(valeur, cle_thematique)
            continue

        print(f"⚠ type de cible inconnu, ignoré : {type_cible!r}", file=sys.stderr)

    # Passe d'escalade lourde, ciblée uniquement sur les cibles insuffisantes
    # accumulées ci-dessus — jamais sur tout le lot par défaut (§3.3, §10).
    escaladees = 0
    for url in file_insuffisantes:
        resultat = _escalader_lourd(url)
        if resultat["statut"] == "visitee_lourde":
            _ajouter_au_corpus(chemin_corpus, url, resultat, None)
            escaladees += 1
        time.sleep(random.uniform(delai_min, delai_max))

    print(
        f"Campagne {id_campagne!r} terminée : {urls_retenues} page(s) retenue(s) au palier "
        f"léger, {escaladees}/{len(file_insuffisantes)} escaladée(s) avec succès vers le "
        f"palier lourd. Corpus : {chemin_corpus}"
    )

    # Synthèse finale — context stuffing (DINOER_RESEARCH.md §11, version
    # simplifiée actée par l'opérateur le 28/07/2026 : pas de retrieval vectoriel
    # dans ce lot). Isolée dans un bloc best-effort large et volontaire : le
    # corpus déjà écrit sur disque ci-dessus reste la valeur produite par la
    # campagne, un échec de synthèse (OpenCode indisponible, contexte vide)
    # ne doit jamais l'invalider ni faire échouer la commande — même
    # discipline que `lib/journal.py::enregistrer_operation()`.
    try:
        from lib.synthese import construire_contexte, ecrire_rapport, rediger_rapport

        repertoire_campagne = os.path.dirname(chemin_corpus)
        contexte, sources = construire_contexte(chemin_corpus)
        if not sources:
            print("⚠ corpus vide — synthèse non tentée.", file=sys.stderr)
        else:
            markdown = rediger_rapport(contexte, sources)
            chemin_rapport = ecrire_rapport(repertoire_campagne, id_campagne, markdown)
            print(f"Rapport écrit : {chemin_rapport}")

            topic = manifeste.get("ntfy_topic") or os.environ.get("DINOER_NTFY_TOPIC")
            if topic:
                from lib.ntfy import notifier
                notifier(
                    topic, "Dinoer — rapport prêt",
                    f"Campagne {id_campagne!r} terminée : {len(sources)} source(s), "
                    f"rapport disponible ({chemin_rapport}).",
                )
            else:
                print(
                    "⚠ aucun topic ntfy configuré (champ 'ntfy_topic' du manifeste, ou "
                    "DINOER_NTFY_TOPIC) — notification non envoyée.",
                    file=sys.stderr,
                )
    except Exception as e:
        print(f"⚠ synthèse/notification échouée, corpus préservé : {type(e).__name__} : {e}",
              file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except SearxngNonConfigureError as e:
        print(f"⚠ {e}", file=sys.stderr)
        sys.exit(1)
