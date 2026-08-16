"""
selection_candidats.py — Sélection du meilleur candidat parmi plusieurs
(volet B, fonctionnalité 2 : « vrai lien produit », cf.
TACHE_volet_b_recherche_avancee.md §2).

Depuis une liste de pages candidates déjà collectées pour une même cible
(un produit, un lieu, une entité nommée), retient celle qui correspond le
mieux — remplace l'hypothèse implicite « le premier résultat SearXNG est le
bon » par une comparaison explicite. Ne fait aucun fetch : opère sur des
candidats déjà extraits par `lib/fetch_leger.py` (appelant :
`campagne.py::_traiter_cible_produit`).
"""

import json
import re

from lib.modeles import invoquer_opencode

_PROMPT_GABARIT = """Tu compares plusieurs pages web candidates pour trouver celle qui \
correspond le mieux à la cible suivante : {cible}

Candidats (numérotés à partir de 0) :
{candidats}

Choisis le candidat qui correspond le mieux à la cible — la page réelle et pertinente
(la « page produit », ou son équivalent selon la cible), pas une page de résultats, un
annuaire, ou une page hors-sujet. Si aucun candidat ne correspond raisonnablement, dis-le \
plutôt que de choisir le moins mauvais par défaut.

Réponds UNIQUEMENT par un objet JSON strict, sans texte ni balise Markdown autour, au
format exact :
  {{"indice_retenu": <numéro entier du candidat retenu>, "raison": "<justification brève>"}}
ou, si aucun ne convient :
  {{"indice_retenu": null, "raison": "<pourquoi aucun ne convient>"}}
"""


class SelectionIntrouvableError(RuntimeError):
    """Sortie du modèle non parseable, ou indice hors bornes/non entier —
    distincte d'un rejet légitime de tous les candidats (`indice_retenu:
    null`), qui n'est pas une erreur : c'est le modèle qui n'a pas respecté
    le contrat de sortie, pas les candidats qui sont tous mauvais."""


def selectionner_meilleur(
    cible: str, candidats: list[dict], modele: str | None = None,
) -> dict | None:
    """`candidats` : liste de `{"url", "titre", "texte"}` (même forme qu'une
    entrée de corpus, cf. `campagne.py::_ajouter_au_corpus`). Retourne le
    candidat retenu, enrichi d'une clé `raison`, ou `None` si aucun candidat
    n'est fourni ou si le modèle juge qu'aucun ne convient (les deux cas sont
    des résultats négatifs légitimes, jamais une exception — même discipline
    que `lib/extraction.py`).
    """
    if not candidats:
        return None
    if len(candidats) == 1:
        # Rien à comparer — un appel modèle serait un coût pur sans valeur
        # de sélection (aucune alternative face à laquelle arbitrer).
        return {**candidats[0], "raison": "candidat_unique"}

    bloc_candidats = "\n---\n".join(
        f"[{i}] {c.get('titre') or c['url']}\nURL : {c['url']}\n{(c.get('texte') or '')[:1500]}"
        for i, c in enumerate(candidats)
    )
    prompt = _PROMPT_GABARIT.format(cible=cible, candidats=bloc_candidats)

    kwargs = {"modele": modele} if modele else {}
    brut = invoquer_opencode(prompt, **kwargs)

    correspondance = re.search(r"\{.*\}", brut["texte"], re.DOTALL)
    if not correspondance:
        raise SelectionIntrouvableError(
            f"réponse OpenCode sans objet JSON identifiable : {brut['texte'][:200]!r}"
        )
    try:
        donnees = json.loads(correspondance.group(0))
    except json.JSONDecodeError as exc:
        raise SelectionIntrouvableError(
            f"JSON invalide dans la réponse OpenCode : {brut['texte'][:200]!r}"
        ) from exc

    indice = donnees.get("indice_retenu")
    if indice is None:
        return None
    try:
        indice = int(indice)
    except (TypeError, ValueError) as exc:
        raise SelectionIntrouvableError(f"indice_retenu non entier : {indice!r}") from exc
    if not (0 <= indice < len(candidats)):
        raise SelectionIntrouvableError(
            f"indice_retenu hors bornes : {indice!r} (attendu 0..{len(candidats) - 1})"
        )

    return {**candidats[indice], "raison": donnees.get("raison")}
