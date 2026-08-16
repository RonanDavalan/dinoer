"""
tables_reference.py — Table de sites de référence par sujet, volet B
fonctionnalité 3 (`TACHE_volet_b_recherche_avancee.md` §3).

Architecture hybride (proposition initiale de Gemini le 09/08/2026, validée
par Ronan, corrigée par Claude sur trois points avant exécution — détail
dans la fiche ci-dessus) :

  1. un fichier persistant contient des domaines de référence classés par
     clé thématique (`tourisme_bretagne`, `mairies_locales`, etc.) ;
  2. si la clé demandée est absente, OpenCode est sollicité pour proposer
     une liste de domaines à la volée (`generer_et_enregistrer()`) ;
  3. le résultat généré est écrit dans le fichier — enrichissement
     progressif, une campagne capitalise pour la suivante.

Emplacement du fichier : même cascade de résolution que
`campagne.py::_repertoire_campagnes()` et `lib/vector.py::DB_PATH` —
`DINOER_TABLES_REFERENCE` (env) → clé `tables_reference` de `dinoer.conf` →
défaut `/var/log/dinoer/tables_reference.json`. Jamais dans l'arbre source
déployé (`scenarios/`, `dinoer.conf.d/` — options initiales de Gemini,
écartées) : un fichier réécrit à l'exécution ne doit pas vivre dans un arbre
que la loi de reconstruction depuis zéro (`GOUVERNANCE/LOIS.md`) traite
comme figé.

Provenance tracée : chaque entrée porte `"origine"` — `"generee_llm"` (posée
par ce module, jamais garantie exacte, cf. `_PROMPT_GABARIT`) ou `"validee"`
(jamais posée par le code, réservée à une édition manuelle du fichier par
l'opérateur) — et `"date_ajout"`. Un consommateur de ce module ne doit
jamais traiter les deux avec la même confiance.

Écriture atomique : `generer_et_enregistrer()` lit le fichier entier, ajoute
une clé, réécrit via fichier temporaire + `os.replace()` — jamais une
réécriture directe qui laisserait un fichier à moitié écrit en cas
d'interruption.
"""

import json
import os
import re
import tempfile
from datetime import datetime, timezone

from lib.modeles import invoquer_opencode

_CONF_PATH = "/opt/dinoer/dinoer.conf"
_CHEMIN_DEFAUT = "/var/log/dinoer/tables_reference.json"

_ORIGINE_GENEREE = "generee_llm"

_PROMPT_GABARIT = """Tu proposes une liste de sites de référence fiables pour le sujet \
suivant : {sujet}

Cite uniquement des noms de domaine plausibles et couramment associés à ce type de sujet \
(offices de tourisme, mairies, associations, organismes officiels, selon le sujet) — jamais \
une extrapolation non fondée présentée comme certaine. Si tu n'es pas raisonnablement confiant \
sur un domaine précis, ne le propose pas plutôt que de deviner.

Réponds UNIQUEMENT par un objet JSON strict, sans texte ni balise Markdown autour, au format \
exact : {{"domaines": ["exemple1.fr", "exemple2.bzh"]}}
ou, si tu ne peux proposer aucun domaine avec une confiance raisonnable : {{"domaines": []}}
"""


class GenerationTableIntrouvableError(RuntimeError):
    """Sortie du modèle non parseable en JSON valide — distincte d'une
    proposition vide légitime (`"domaines": []`), qui n'est pas une erreur."""


def _resoudre_chemin() -> str:
    if "DINOER_TABLES_REFERENCE" in os.environ:
        return os.path.expanduser(os.environ["DINOER_TABLES_REFERENCE"])
    if os.path.isfile(_CONF_PATH):
        try:
            with open(_CONF_PATH, encoding="utf-8") as f:
                conf = json.load(f)
            if "tables_reference" in conf:
                return os.path.expanduser(conf["tables_reference"])
        except (OSError, json.JSONDecodeError):
            pass
    return _CHEMIN_DEFAUT


def _lire_fichier(chemin: str) -> dict:
    """Retourne le contenu du fichier de tables, ou `{}` s'il est absent,
    vide ou corrompu — jamais une exception : un fichier de tables
    manquant est l'état initial normal, pas une erreur."""
    if not os.path.isfile(chemin):
        return {}
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _ecrire_fichier_atomique(chemin: str, donnees: dict) -> None:
    repertoire = os.path.dirname(chemin) or "."
    os.makedirs(repertoire, exist_ok=True)
    fd, chemin_temp = tempfile.mkstemp(dir=repertoire, prefix=".tables_reference_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)
        os.replace(chemin_temp, chemin)
    except BaseException:
        try:
            os.remove(chemin_temp)
        except OSError:
            pass
        raise


def charger(cle_thematique: str) -> list[dict] | None:
    """Retourne les entrées `{"domaine", "origine", "date_ajout"}` de la clé
    thématique demandée, ou `None` si la clé n'existe pas dans le fichier
    (absence légitime — c'est ce signal qui déclenche le repli sur
    `generer_et_enregistrer()` côté appelant, pas une exception ici)."""
    donnees = _lire_fichier(_resoudre_chemin())
    entrees = donnees.get(cle_thematique)
    return entrees if entrees else None


def generer_et_enregistrer(
    cle_thematique: str, sujet: str, modele: str | None = None,
) -> list[dict]:
    """Sollicite OpenCode pour proposer des domaines de référence sur
    `sujet`, enregistre le résultat sous `cle_thematique` (fusion avec le
    fichier existant, écriture atomique), retourne les entrées ajoutées.

    Une proposition vide (`"domaines": []`) est enregistrée telle quelle
    (liste vide sous la clé) — évite de re-solliciter OpenCode à chaque
    campagne sur un sujet pour lequel le modèle a déjà décliné. Lève
    `GenerationTableIntrouvableError` si la sortie n'est pas un JSON valide
    (distinct d'une proposition vide légitime), et propage `RuntimeError`
    d'`invoquer_opencode()` telle quelle (binaire absent, timeout).
    """
    kwargs = {"modele": modele} if modele else {}
    brut = invoquer_opencode(_PROMPT_GABARIT.format(sujet=sujet), **kwargs)

    correspondance = re.search(r"\{.*\}", brut["texte"], re.DOTALL)
    if not correspondance:
        raise GenerationTableIntrouvableError(
            f"réponse OpenCode sans objet JSON identifiable : {brut['texte'][:200]!r}"
        )
    try:
        donnees_reponse = json.loads(correspondance.group(0))
    except json.JSONDecodeError as exc:
        raise GenerationTableIntrouvableError(
            f"JSON invalide dans la réponse OpenCode : {brut['texte'][:200]!r}"
        ) from exc

    domaines_bruts = donnees_reponse.get("domaines") or []
    horodatage = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entrees = [
        {"domaine": d, "origine": _ORIGINE_GENEREE, "date_ajout": horodatage}
        for d in domaines_bruts if isinstance(d, str) and d.strip()
    ]

    chemin = _resoudre_chemin()
    donnees_fichier = _lire_fichier(chemin)
    donnees_fichier[cle_thematique] = entrees
    _ecrire_fichier_atomique(chemin, donnees_fichier)

    return entrees
