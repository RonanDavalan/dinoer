"""Test de vérité-terrain pour `lib/extraction.py::fusionner_evenements()`
(volet C, session 2.3 de
`_CADRE/SPECIFICATIONS/PROCEDURES_LLM/TACHE_fiabilisation_synthese_campagne.md`).

Vrai appel OpenCode, non mocké — c'est le point : vérifier que le
regroupement réel produit par le modèle correspond aux comptes de référence
déjà établis manuellement dans `rapport_final_cible.md` (lignes 241-242 :
« Filets Bleus ×4, Concert Keriolet ×2, Locmaria ×3, Clés de la
Ville-Close ×2 »), pas une simulation de ce que le modèle devrait faire.

Le corpus source (`reextraction_adaptative_resultats.json`,
`rapport_final_cible.md`) vit dans `~/git/Dinoer/campagnes_dev/` — étage
tampon, jamais commité dans ce dépôt public. Ce test se saute proprement
quand ce corpus est absent (tout clone hors de la machine de
développement, y compris CI).
"""
import json
import os

import pytest

from lib.extraction import FusionIntrouvableError, fusionner_evenements
from lib.modeles import _OPENCODE_BIN

_CORPUS_DIR = os.path.expanduser(
    "~/git/Dinoer/campagnes_dev/spectacles-sud-finistere-2026-08-11-20"
)
_RESULTATS_PATH = os.path.join(_CORPUS_DIR, "reextraction_adaptative_resultats.json")

pytestmark = pytest.mark.skipif(
    not os.path.isfile(_RESULTATS_PATH),
    reason=f"corpus de vérité-terrain absent ({_RESULTATS_PATH!r}) — hors dépôt public",
)


def _urls_mentionnant(positifs, motif):
    return {r["url"] for r in positifs if motif in (r["valeur"] or "").lower()}


def test_fusionner_evenements_contre_verite_terrain():
    if not os.path.isfile(_OPENCODE_BIN):
        pytest.skip(f"binaire opencode introuvable ({_OPENCODE_BIN!r})")

    with open(_RESULTATS_PATH, encoding="utf-8") as f:
        resultats = json.load(f)

    positifs = [r for r in resultats if r.get("trouve") and r.get("valeur")]
    assert len(positifs) == 17, (
        "table de vérité périmée (TACHE_fiabilisation_synthese_campagne.md) — "
        "17 positifs attendus, revérifier avant de suivre cette fiche"
    )

    # Comptes de référence, rapport_final_cible.md lignes 241-242. Les motifs
    # ci-dessous identifient sans ambiguïté les mêmes URLs que la
    # consolidation manuelle (vérifié terme à terme le 13/08/2026, y compris
    # la distinction entre "Ville-Close" (avec trait d'union, l'événement
    # nommé « Les Clés de la Ville-Close ») et "Ville Close" (sans trait
    # d'union, simple lieu cité dans deux autres textes sur Filets Bleus —
    # motif volontairement exclu ici).
    attendus = {
        "Filets Bleus": _urls_mentionnant(positifs, "filets bleus"),
        "Concert Keriolet": _urls_mentionnant(positifs, "keriolet"),
        "Locmaria": _urls_mentionnant(positifs, "locmaria"),
        "Clés de la Ville-Close": _urls_mentionnant(positifs, "ville-close"),
    }
    assert {nom: len(urls) for nom, urls in attendus.items()} == {
        "Filets Bleus": 4, "Concert Keriolet": 2, "Locmaria": 3,
        "Clés de la Ville-Close": 2,
    }, "comptes de référence non retrouvés dans le corpus réel — table de vérité périmée"

    try:
        groupes = fusionner_evenements(resultats)  # vrai appel OpenCode, non mocké
    except FusionIntrouvableError as exc:
        pytest.fail(
            "fusionner_evenements() a levé FusionIntrouvableError sur le corpus réel "
            f"({exc}) — écart trouvé, pas une erreur de test : au moins une source "
            "(ex. l'entrée qui liste Filets Bleus + Clés de la Ville-Close + Keriolet + "
            "Concert de la Bordée sur une même page) décrit plusieurs événements "
            "distincts, et le modèle place légitimement son indice dans plusieurs "
            "groupes — invariant « un indice = un seul groupe » de fusionner_evenements() "
            "non tenu par ce corpus réel. Nécessite un arbitrage de conception "
            "(TACHE_fiabilisation_synthese_campagne.md), pas un correctif mécanique."
        )

    ecarts = []
    for nom, urls_attendues in attendus.items():
        meilleur = max(
            groupes, key=lambda g: len(set(g["urls"]) & urls_attendues),
            default={"evenement": None, "urls": []},
        )
        obtenu = set(meilleur["urls"])
        if obtenu != urls_attendues:
            ecarts.append(
                f"{nom} : attendu {sorted(urls_attendues)}, "
                f"obtenu {sorted(obtenu)} (groupe {meilleur!r})"
            )

    assert not ecarts, (
        "écart(s) vs rapport_final_cible.md lignes 241-242 :\n" + "\n".join(ecarts)
    )
