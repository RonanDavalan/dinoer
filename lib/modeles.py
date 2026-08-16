"""Collecte des métadonnées modèles (format `modeles_utilises[]`, non relié à
`dinoer_meta` — retiré de `shot.py` le 12/08/2026, plomberie orpheline de la
purge vision du 09/08, `_CADRE/MEMOIRE/ADDENDUM_2026_08_12.md`), et
raisonnement déporté via OpenCode (FONDATION_DINOER.md §3). Les trois
collecteurs ci-dessous n'ont aujourd'hui aucun appelant dans le dépôt —
conservés comme utilitaires purs, prêts pour un futur branchement côté
`campagne.py` si la traçabilité du pipeline de recherche est spécifiée.

- pour un modèle Ollama, interroge l'API HTTP locale `POST /api/show`
  pour récupérer `details.quantization_level` et le `digest`,
- pour un modèle Anthropic (mode --llm claude), produit une entrée
  statique sans quantization ni hash (champs `null`),
- pour OpenCode, `invoquer_opencode()` exécute réellement le modèle
  (contrairement aux deux collecteurs ci-dessus, purement introspectifs)
  et `collecter_modele_opencode()` construit l'entrée `modeles_utilises[]`
  à partir des tokens/coût renvoyés par CET appel précis — pas d'API de
  traçabilité a posteriori côté OpenCode.
- cache mémoire par (endpoint, tag) pour la durée du processus (Ollama
  uniquement, conforme §5.5 : un appel HTTP par modèle, < 50 ms attendu).

Lecture seule pour les deux collecteurs Ollama/Claude. `invoquer_opencode`
est la seule fonction du module à avoir un effet de bord (lancement d'un
sous-processus).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Optional

import requests


_ENDPOINT_OLLAMA_DEFAUT = "http://localhost:11434"
_ENDPOINT_CLAUDE = "api.anthropic.com"
_TIMEOUT_SHOW_S = 5

_OPENCODE_BIN = os.environ.get(
    "DINOER_OPENCODE_BIN", os.path.expanduser("~/.opencode/bin/opencode")
)
_OPENCODE_MODELE_DEFAUT = os.environ.get(
    "DINOER_OPENCODE_MODEL", "opencode/deepseek-v4-flash-free"
)
_TIMEOUT_OPENCODE_S = 120

_CACHE_SHOW: dict[tuple[str, str], dict] = {}
_CACHE_TAGS: dict[str, dict[str, str]] = {}


def _separer_tag_ollama(tag: str) -> tuple[str, str]:
    if ":" in tag:
        nom, version = tag.split(":", 1)
        return nom, version
    return tag, "latest"


def _interroger_api_show(endpoint: str, tag: str) -> Optional[dict]:
    cle = (endpoint, tag)
    if cle in _CACHE_SHOW:
        return _CACHE_SHOW[cle]
    try:
        resp = requests.post(
            f"{endpoint.rstrip('/')}/api/show",
            json={"name": tag},
            timeout=_TIMEOUT_SHOW_S,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        print(
            f"⚠ Dinoer : API Ollama indisponible pour /api/show de "
            f"{tag} sur {endpoint} ({exc}). Métadonnées partielles.",
            file=sys.stderr,
        )
        _CACHE_SHOW[cle] = {}
        return None
    _CACHE_SHOW[cle] = data
    return data


def _interroger_api_tags(endpoint: str) -> dict[str, str]:
    """Retourne le dict {nom_tag: digest} pour tous les modèles installés.

    `/api/show` n'expose pas le digest (constaté Ollama 0.5+) ; c'est
    `/api/tags` qui le fournit. Un seul appel par endpoint, caché.
    """
    if endpoint in _CACHE_TAGS:
        return _CACHE_TAGS[endpoint]
    try:
        resp = requests.get(
            f"{endpoint.rstrip('/')}/api/tags",
            timeout=_TIMEOUT_SHOW_S,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        print(
            f"⚠ Dinoer : API Ollama indisponible pour /api/tags sur "
            f"{endpoint} ({exc}). Hashes modèles non collectés.",
            file=sys.stderr,
        )
        _CACHE_TAGS[endpoint] = {}
        return {}
    index = {
        m.get("name"): m.get("digest")
        for m in (data.get("models") or [])
        if m.get("name")
    }
    _CACHE_TAGS[endpoint] = index
    return index


def collecter_modele_ollama(
    tag: str,
    role: str,
    endpoint: str = _ENDPOINT_OLLAMA_DEFAUT,
    inclure_hash: bool = True,
) -> dict:
    """Construit une entrée `modeles_utilises[]` pour un modèle Ollama.

    Si l'API Ollama est injoignable, les champs `quantization` et
    `hash_tag_ollama` sont mis à `null` plutôt que d'omettre l'entrée
    ou de lever : la traçabilité partielle est meilleure que pas de
    traçabilité.
    """
    nom, version = _separer_tag_ollama(tag)
    entree = {
        "nom": nom,
        "version": version,
        "quantization": None,
        "hash_tag_ollama": None,
        "role": role,
    }
    if endpoint != _ENDPOINT_OLLAMA_DEFAUT:
        entree["endpoint"] = endpoint

    data = _interroger_api_show(endpoint, tag)
    if data:
        details = data.get("details") or {}
        entree["quantization"] = details.get("quantization_level")

    if inclure_hash:
        index = _interroger_api_tags(endpoint)
        digest = index.get(tag)
        if digest:
            entree["hash_tag_ollama"] = digest

    return entree


def collecter_modele_claude(model_id: str, role: str) -> dict:
    """Construit une entrée `modeles_utilises[]` pour un modèle Anthropic.

    Aucun appel réseau : les métadonnées riches (quantization, digest)
    n'ont pas d'équivalent côté API Anthropic.
    """
    return {
        "nom": model_id,
        "version": None,
        "quantization": None,
        "hash_tag_ollama": None,
        "role": role,
        "endpoint": _ENDPOINT_CLAUDE,
    }


def invoquer_opencode(
    prompt: str,
    modele: str = _OPENCODE_MODELE_DEFAUT,
    timeout_s: int = _TIMEOUT_OPENCODE_S,
) -> dict:
    """Invoque OpenCode en mode non interactif — raisonnement déporté gratuit
    (FONDATION_DINOER.md §3). Chaque appel est un processus indépendant, sans
    état conservé (pas de --continue/--session) : cohérent avec la discipline
    best-effort du reste du module, et suffisant pour un usage ponctuel
    (planification de recherche, filtrage, rédaction d'un passage).

    Retourne {"texte", "modele", "tokens", "cout"} — tokens/cout proviennent
    du dernier événement `step_finish` du flux JSON Lines d'OpenCode, ou None
    si absent. Lève RuntimeError si le binaire est introuvable, le processus
    échoue, dépasse le timeout, ou ne retourne aucun texte : contrairement à
    collecter_modele_ollama (dégradation silencieuse en champs `null`, la
    traçabilité partielle valant mieux que pas de traçabilité), un appel
    OpenCode raté ne produit aucun résultat exploitable pour l'appelant —
    l'avaler silencieusement masquerait l'absence du travail demandé.
    """
    if not os.path.isfile(_OPENCODE_BIN):
        raise RuntimeError(f"binaire opencode introuvable : {_OPENCODE_BIN}")

    try:
        resultat = subprocess.run(
            [_OPENCODE_BIN, "run", prompt, "--model", modele, "--format", "json"],
            capture_output=True, text=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"opencode a dépassé le timeout de {timeout_s}s") from exc

    if resultat.returncode != 0:
        raise RuntimeError(
            f"opencode a échoué (exit {resultat.returncode}) : {resultat.stderr[:500]}"
        )

    morceaux_texte = []
    tokens = None
    cout = None
    for ligne in resultat.stdout.splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            evenement = json.loads(ligne)
        except json.JSONDecodeError:
            continue
        part = evenement.get("part") or {}
        if evenement.get("type") == "text" and part.get("type") == "text":
            morceaux_texte.append(part.get("text", ""))
        elif evenement.get("type") == "step_finish":
            tokens = part.get("tokens")
            cout = part.get("cost")

    texte = "".join(morceaux_texte).strip()
    if not texte:
        raise RuntimeError("opencode n'a retourné aucun texte exploitable")

    return {"texte": texte, "modele": modele, "tokens": tokens, "cout": cout}


def collecter_modele_opencode(
    model_id: str, role: str, tokens: Optional[dict] = None, cout: Optional[float] = None,
) -> dict:
    """Construit une entrée `modeles_utilises[]` pour un modèle appelé via OpenCode.

    Contrairement à collecter_modele_ollama, aucune requête réseau séparée :
    tokens/cout proviennent directement du `step_finish` renvoyé par
    invoquer_opencode() pour CET appel précis — pas une introspection a
    posteriori sur un endpoint distinct.
    """
    entree = {
        "nom": model_id,
        "version": None,
        "quantization": None,
        "hash_tag_ollama": None,
        "role": role,
        "endpoint": "opencode",
    }
    if tokens is not None:
        entree["tokens"] = tokens
    if cout is not None:
        entree["cout"] = cout
    return entree


def reinitialiser_cache() -> None:
    """Vide les caches mémoire. Utile pour les tests."""
    _CACHE_SHOW.clear()
    _CACHE_TAGS.clear()
