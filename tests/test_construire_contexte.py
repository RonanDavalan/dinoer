"""Tests pour `lib/synthese.py::construire_contexte()` — session 3 de
`_CADRE/SPECIFICATIONS/PROCEDURES_LLM/TACHE_fiabilisation_synthese_campagne.md`
(13/08/2026) : pré-filtre temporel (`motifs_annee`/`motifs_mois`) et
classement sémantique (`sujet_synthese`), tous deux optionnels.

Deux classes de test :
  - `test_defaut_*`/`test_prefiltre_*` — purs, aucune dépendance externe,
    corpus synthétique temporaire, tournent en CI.
  - `test_sujet_synthese_*` — vérité-terrain contre le corpus réel de
    référence (`~/git/Dinoer/campagnes_dev/`, étage tampon, jamais commité)
    avec appel `embed()` réel (Ollama local). Se saute proprement quand le
    corpus ou Ollama/nomic-embed-text sont absents (même discipline que
    `test_extraction_fusion.py`).
"""
import json
import os

import pytest

from lib.synthese import construire_contexte

_CORPUS_REEL = os.path.expanduser(
    "~/git/Dinoer/campagnes_dev/spectacles-sud-finistere-2026-08-11-20/collecte.jsonl"
)


def _ecrire_corpus(tmp_path, pages):
    chemin = tmp_path / "collecte.jsonl"
    with open(chemin, "w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p) + "\n")
    return str(chemin)


def test_defaut_comportement_inchange(tmp_path):
    """Sans motifs ni sujet : ordre d'écriture préservé, pages_repoussees
    toujours vide — non-régression du comportement d'avant le 13/08/2026."""
    chemin = _ecrire_corpus(tmp_path, [
        {"url": "https://a.example/1", "titre": "Un", "texte": "contenu un"},
        {"url": "https://a.example/2", "titre": "Deux", "texte": "contenu deux"},
    ])
    contexte, sources, repoussees = construire_contexte(chemin)
    assert [s["url"] for s in sources] == ["https://a.example/1", "https://a.example/2"]
    assert repoussees == []


def test_corpus_absent_retourne_triplet_vide(tmp_path):
    contexte, sources, repoussees = construire_contexte(str(tmp_path / "absent.jsonl"))
    assert (contexte, sources, repoussees) == ("", [], [])


def test_prefiltre_temporel_relegue_sans_exclure(tmp_path):
    """Une page qui ne mentionne pas la fenêtre est reléguée en fin de
    liste, pas supprimée — et comptée dans pages_repoussees."""
    chemin = _ecrire_corpus(tmp_path, [
        {"url": "https://a.example/hors-sujet", "titre": "Hors sujet",
         "texte": "Cette page ne mentionne aucune date pertinente."},
        {"url": "https://a.example/dans-sujet", "titre": "Dans le sujet",
         "texte": "Programme du mois d'août 2026 : concerts et festivals."},
    ])
    contexte, sources, repoussees = construire_contexte(
        chemin, motifs_annee=["2026"], motifs_mois=["août", "aout", "/08"],
    )
    assert [s["url"] for s in sources] == [
        "https://a.example/dans-sujet", "https://a.example/hors-sujet",
    ]
    assert [p["url"] for p in repoussees] == ["https://a.example/hors-sujet"]


def _ollama_embed_disponible():
    try:
        from lib.vector import embed
        embed(["test"])
        return True
    except Exception:
        return False


pytestmark_verite_terrain = pytest.mark.skipif(
    not os.path.isfile(_CORPUS_REEL),
    reason=f"corpus de vérité-terrain absent ({_CORPUS_REEL!r}) — hors dépôt public",
)


@pytestmark_verite_terrain
def test_sujet_synthese_fait_remonter_le_programme_officiel():
    """Défaut réel trouvé et mesuré le 13/08/2026 : le pré-filtre temporel
    seul est insuffisant — les deux pages `deconcarneauapontaven.com`
    (programme officiel d'août 2026) passent le filtre booléen mais restent
    en position 27-28/29 par ordre d'écriture, donc hors du budget de
    troncature (60000 car. ~ 16 pages). Le classement sémantique
    (`sujet_synthese`) les fait remonter dans le budget — vérifié ici contre
    le corpus réel, pas supposé."""
    if not _ollama_embed_disponible():
        pytest.skip("Ollama/nomic-embed-text indisponible")

    contexte, sources, repoussees = construire_contexte(
        _CORPUS_REEL,
        motifs_annee=["2026"], motifs_mois=["août", "aout", "/08", "-08-"],
        sujet_synthese=(
            "spectacles, concerts, festivals et animations culturelles en "
            "août 2026 dans le Sud Finistère (Concarneau, Pont-Aven)"
        ),
    )

    urls = [s["url"] for s in sources]
    url_pdf = (
        "https://www.deconcarneauapontaven.com/wp-content/uploads/2026/07/"
        "programme-animations-aout-2026-office-de-tourisme-de-concarneau-a-pont-aven.pdf"
    )
    assert url_pdf in urls, (
        "le programme officiel (deconcarneauapontaven.com) doit être dans le "
        "budget de troncature une fois le classement sémantique appliqué"
    )

    # Page de bruit démographique (2014, 19199 habitants) : passe le
    # pré-filtre grossier (mentionne « août » une fois, hors-sujet — offre
    # d'emploi saisonnier), donc n'apparaît PAS dans pages_repoussees ; c'est
    # au classement sémantique fin de la reléguer. Absente du budget final,
    # ou à défaut classée après le PDF — jamais avant.
    url_demo = "https://www.eterritoire.fr/territoires/bretagne/finistere/concarneau/29039/11276"
    if url_demo in urls:
        assert urls.index(url_demo) > urls.index(url_pdf), (
            "la page de bruit démographique ne doit jamais précéder le "
            "programme officiel dans le contexte de synthèse"
        )
