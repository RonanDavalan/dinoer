"""Filet de non-régression sur trois bugs déjà diagnostiqués et corrigés
(cf. `_CADRE/SPECIFICATIONS/PROCEDURES_LLM/TACHE_fiabilisation_synthese_campagne.md`,
table de vérité, session 2). Ces tests épinglent un comportement déjà
correct — ils doivent passer contre l'état actuel du code, et échoueraient
si l'un des trois correctifs était accidentellement défait.

Note sur le test 3 : la fiche source attribue le correctif à
`campagne.py::_traiter_cible_table_reference()` ; lecture du code (13/08/2026)
montre que les lignes en cause appartiennent en réalité au traitement d'une
cible `"query"` avec hit de cache, directement dans la boucle principale de
`main()` — même bug, même correctif, mauvaise attribution de nom de fonction
dans la fiche. Le test cible le code réel, pas le nom de fonction cité.
"""
import json
import sys

import requests

import campagne
from lib import fetch_leger


def test_robots_autorise_meme_user_agent(monkeypatch):
    """`_robots_autorise()` (lib/fetch_leger.py:68) doit utiliser le même
    User-Agent pour la requête robots.txt et pour la requête de contenu —
    jamais `RobotFileParser.read()`, qui délègue à `urllib.request` avec
    un User-Agent distinct (bug reproduit sur `deconcarneauapontaven.com`,
    campagne du 12/08/2026)."""
    appels = []

    class ReponseFactice:
        def __init__(self, status_code, text, content_type):
            self.status_code = status_code
            self.text = text
            self.headers = {"Content-Type": content_type}
            self.content = text.encode("utf-8")

    def get_factice(url, headers=None, timeout=None, allow_redirects=None):
        appels.append({"url": url, "headers": dict(headers or {})})
        if url.endswith("/robots.txt"):
            return ReponseFactice(200, "User-agent: *\nAllow: /", "text/plain")
        return ReponseFactice(
            200,
            "<html><head><title>Page de test</title></head><body>"
            "Contenu de test suffisamment long pour dépasser le seuil "
            "de texte minimal du palier léger de collecte."
            "</body></html>",
            "text/html; charset=utf-8",
        )

    monkeypatch.setattr(requests, "get", get_factice)

    resultat = fetch_leger.recuperer(
        "https://exemple-test.example/page", user_agent="AgentTest/1.0"
    )

    assert resultat["statut"] == "visitee"
    assert len(appels) == 2, "robots.txt puis contenu — deux appels attendus"
    user_agents = [a["headers"].get("User-Agent") for a in appels]
    assert user_agents[0] == "AgentTest/1.0"
    assert user_agents[1] == "AgentTest/1.0"
    assert user_agents[0] == user_agents[1]


def test_traiter_cible_produit_ne_crashe_jamais_la_campagne(tmp_path, monkeypatch):
    """`campagne.py::_traiter_cible_produit()` (fonction imbriquée dans
    `main()`, campagne.py:414-463) : un échec de `selectionner_meilleur()`
    (RuntimeError ou SelectionIntrouvableError) ne doit jamais interrompre
    la campagne — bug trouvé et corrigé en PHASE_VALIDATION du 09/08/2026."""
    monkeypatch.setenv("DINOER_CAMPAGNES_DIR", str(tmp_path / "campagnes"))
    monkeypatch.setenv("DINOER_JOURNAL", str(tmp_path / "operations.jsonl"))

    manifeste = {
        "id_campagne": "test-regression-produit",
        "cibles": [{"type": "produit", "valeur": "un produit de test", "max_candidats": 1}],
        "delai_min_secondes": 0,
        "delai_max_secondes": 0,
    }
    chemin_manifeste = tmp_path / "manifeste.json"
    chemin_manifeste.write_text(json.dumps(manifeste), encoding="utf-8")

    def rechercher_factice(valeur, page=1):
        return ["https://exemple-test.example/candidat"] if page == 1 else []

    def recuperer_factice(url, **kwargs):
        return {
            "statut": "visitee", "url": url, "titre": "Candidat de test",
            "texte": "Texte du candidat de test.", "raison": None,
        }

    def selectionner_meilleur_factice(cible, candidats, modele=None):
        raise RuntimeError("échec simulé de selectionner_meilleur")

    monkeypatch.setattr(campagne, "rechercher", rechercher_factice)
    monkeypatch.setattr(campagne, "recuperer", recuperer_factice)
    monkeypatch.setattr(campagne, "selectionner_meilleur", selectionner_meilleur_factice)
    monkeypatch.setattr(sys, "argv", ["campagne.py", "--manifeste", str(chemin_manifeste)])

    campagne.main()  # ne doit lever aucune exception


def test_hit_cache_journalise_avant_ajout_corpus(tmp_path, monkeypatch):
    """Un hit de cache de recherche (`campagne.py:557-566`, traitement d'une
    cible `"query"`) doit être journalisé (`_journaliser_leger()`) comme une
    extraction fraîche réussie, sinon l'URL est resservie indéfiniment par
    la déduplication (dérivée exclusivement du journal, §7) — bug trouvé et
    corrigé en PHASE_VALIDATION du 09/08/2026, corpus dupliqué observé en
    test."""
    monkeypatch.setenv("DINOER_CAMPAGNES_DIR", str(tmp_path / "campagnes"))
    monkeypatch.setenv("DINOER_JOURNAL", str(tmp_path / "operations.jsonl"))

    manifeste = {
        "id_campagne": "test-regression-cache-hit",
        "cibles": [{"type": "query", "valeur": "une requete de test"}],
        "delai_min_secondes": 0,
        "delai_max_secondes": 0,
    }
    chemin_manifeste = tmp_path / "manifeste.json"
    chemin_manifeste.write_text(json.dumps(manifeste), encoding="utf-8")

    hit = {
        "url": "https://exemple-test.example/hit-cache",
        "titre": "Page en cache",
        "texte": "Texte déjà collecté, servi depuis le cache.",
        "date_capture": "2026-01-01T00:00:00+00:00",
    }

    appels_journal = []

    def journaliser_leger_espion(url, resultat_fetch):
        appels_journal.append((url, dict(resultat_fetch)))

    monkeypatch.setattr(campagne.cache_recherche, "verifier", lambda *a, **k: [hit])
    monkeypatch.setattr(campagne, "_journaliser_leger", journaliser_leger_espion)
    # Synthèse best-effort en fin de main() : évite tout appel réseau/OpenCode
    # réel, hors périmètre de ce test de non-régression (2.3 couvre la
    # vérité-terrain avec un vrai appel OpenCode).
    monkeypatch.setattr(
        "lib.synthese.invoquer_opencode",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("opencode non appelé dans ce test")),
    )
    monkeypatch.setattr(sys, "argv", ["campagne.py", "--manifeste", str(chemin_manifeste)])

    campagne.main()

    assert (hit["url"], {"statut": "visitee"}) in appels_journal
