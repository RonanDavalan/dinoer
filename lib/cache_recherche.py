"""
cache_recherche.py — Cache sémantique optionnel pour campagne.py.

Volet B, fonctionnalité 4 (TACHE_volet_b_recherche_avancee.md §4). Réutilise
`lib/vector.py` (résolution DB_PATH, `embed()`) mais sur une collection
ChromaDB dédiée (`_COLLECTION_CACHE`), distincte de la collection RAG
documentaire par défaut ("dinoer") — pour ne jamais mélanger cache de
recherche et mémoire vectorielle générale si Dinoer sert un jour aussi de
RAG documentaire général.

Portée : cache par **requête** (cibles de type "query" d'un manifeste de
campagne), pas par URL — la déduplication par URL exacte existe déjà et
répond à un besoin différent (`campagne.py::_construire_index_dedup`,
DINOER_RESEARCH.md §7). Ce module évite de relancer une recherche SearXNG et
son palier léger quand une requête sémantiquement proche a déjà été traitée
récemment — la clé vectorielle est la requête elle-même, jamais le contenu
des pages collectées.

Seuil de similarité calibré empiriquement (09/08/2026, `nomic-embed-text` via
Ollama local, distance L2² — métrique par défaut de ChromaDB, non cosinus) :
  - paraphrase de la même requête ("concerts finistere sud ete" vs "concert
    finistere du sud cet ete") : distance ≈ 0,12
  - requête voisine mais distincte en portée ("horaires mairie quimper" vs
    "horaires mairie brest") : distance ≈ 0,46
  - requêtes sans rapport : distance ≈ 0,83
`_SEUIL_DISTANCE_MAX_DEFAUT = 0.20` sépare clairement les deux premiers cas
sur cet échantillon — marge volontairement resserrée du côté prudent : un
faux positif de cache (servir le résultat d'une requête différente) est un
risque de doctrine (jamais inventer, cf. `lib/synthese.py`), un faux négatif
(cache manqué, requête relancée) ne coûte qu'une recherche de plus. Non
revalidé à grande échelle — à ajuster si l'usage réel montre un taux de faux
positifs/négatifs problématique.

Chaque hit de cache est marqué explicitement par l'appelant (`campagne.py`,
champ `source: "cache"` dans le corpus) — jamais indiscernable d'une
extraction fraîche, pour rester auditable.
"""

import time
from datetime import datetime, timezone

from lib.vector import DB_PATH, embed  # noqa: F401 — DB_PATH ré-exporté pour cohérence d'usage

_COLLECTION_CACHE = "dinoer_cache_recherche"
_SEUIL_DISTANCE_MAX_DEFAUT = 0.20
_FENETRE_FRAICHEUR_JOURS_DEFAUT = 30
_N_RESULTATS_INTERROGATION = 5


def _get_collection():
    from lib.vector import get_client
    client = get_client()
    return client.get_or_create_collection(_COLLECTION_CACHE)


def verifier(
    requete: str,
    seuil_distance: float = _SEUIL_DISTANCE_MAX_DEFAUT,
    fenetre_jours: int = _FENETRE_FRAICHEUR_JOURS_DEFAUT,
) -> list[dict]:
    """Interroge le cache pour une requête donnée.

    Retourne la liste des pages précédemment collectées pour la requête la
    plus proche parmi celles indexées, si sa distance est sous
    `seuil_distance` et sa fraîcheur sous `fenetre_jours` — sinon liste vide
    (jamais d'exception pour un cache vide ou absent, même discipline que
    `lib/synthese.py::construire_contexte()`).

    Best-effort : toute erreur (ChromaDB absent, Ollama injoignable) est
    avalée et traitée comme une absence de cache — un cache indisponible ne
    doit jamais faire échouer une campagne, il ne fait que lui coûter une
    recherche qu'elle aurait de toute façon lancée sans lui.
    """
    try:
        collection = _get_collection()
        embedding = embed([requete])[0]
        resultat = collection.query(
            query_embeddings=[embedding],
            n_results=_N_RESULTATS_INTERROGATION,
            where={"type": "requete"},
        )
    except Exception:
        return []

    ids = resultat.get("ids") or [[]]
    distances = resultat.get("distances") or [[]]
    metadatas = resultat.get("metadatas") or [[]]
    if not ids or not ids[0]:
        return []

    limite_epoch = time.time() - fenetre_jours * 86400
    meilleure_requete_id = None
    for identifiant, distance, meta in zip(ids[0], distances[0], metadatas[0]):
        if distance > seuil_distance:
            continue
        if (meta or {}).get("horodatage_epoch", 0) < limite_epoch:
            continue
        # Premier résultat sous le seuil = le plus proche (ChromaDB trie déjà
        # par distance croissante) — c'est cette requête cache-source dont on
        # récupère toutes les pages associées.
        meilleure_requete_id = (meta or {}).get("requete_id")
        break

    if not meilleure_requete_id:
        return []

    try:
        # ChromaDB 1.5.9 exige un opérateur explicite pour un where multi-clés
        # (une seule clé nue lève ValueError "expected where to have exactly
        # one operator") — vérifié par test direct le 09/08/2026.
        pages = collection.get(where={"$and": [
            {"requete_id": meilleure_requete_id}, {"type": "page"},
        ]})
    except Exception:
        return []

    resultats = []
    for doc, meta in zip(pages.get("documents") or [], pages.get("metadatas") or []):
        resultats.append({
            "url": (meta or {}).get("url"),
            "titre": (meta or {}).get("titre"),
            "texte": doc,
            "date_capture": (meta or {}).get("date_capture"),
        })
    return resultats


def indexer(requete: str, pages: list[dict]) -> int:
    """Indexe les pages retenues pour `requete` dans le cache.

    `pages` : liste de `{"url", "titre", "texte", "date_capture"}` (même
    forme que les entrées de `collecte.jsonl`, cf. `campagne.py::_ajouter_au_corpus`).
    Une entrée "requete" (embedding de la requête, jamais du contenu) sert de
    point d'ancrage pour `verifier()` ; chaque page associée est stockée à
    part, liée par `requete_id`, pour ne jamais dupliquer l'embedding sur
    chaque page d'une même requête.

    Best-effort, comme `verifier()` : un échec d'indexation ne doit jamais
    faire échouer la campagne dont le corpus, lui, est déjà écrit sur disque.
    Retourne le nombre de pages indexées (0 si `pages` est vide ou en cas
    d'échec).
    """
    if not pages:
        return 0

    try:
        collection = _get_collection()
        requete_id = f"requete::{requete}"
        horodatage = time.time()
        embedding_requete = embed([requete])[0]

        collection.upsert(
            ids=[requete_id],
            embeddings=[embedding_requete],
            documents=[requete],
            metadatas=[{
                "type": "requete",
                "requete_id": requete_id,
                "horodatage_epoch": horodatage,
                "date_capture": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }],
        )

        ids_pages = [f"{requete_id}::{i}" for i in range(len(pages))]
        # ChromaDB exige un embedding par entrée même pour une entrée retrouvée
        # uniquement par métadonnées (collection.get) — on réutilise
        # l'embedding de la requête, jamais interrogé par similarité pour ces
        # entrées de type "page" (verifier() ne query() que type "requete").
        collection.upsert(
            ids=ids_pages,
            embeddings=[embedding_requete] * len(pages),
            documents=[p.get("texte") or "" for p in pages],
            metadatas=[{
                "type": "page",
                "requete_id": requete_id,
                "url": p.get("url"),
                "titre": p.get("titre"),
                "date_capture": p.get("date_capture"),
                "horodatage_epoch": horodatage,
            } for p in pages],
        )
        return len(pages)
    except Exception:
        return 0


def purger(avant_jours: int | None = None) -> int:
    """Purge le cache. `avant_jours=None` : vide la collection entièrement
    (purge manuelle totale). Sinon : supprime uniquement les entrées plus
    vieilles que `avant_jours` (purge par ancienneté, appelable en tâche
    planifiée).

    Retourne le nombre d'entrées supprimées (0 si le cache est déjà vide ou
    absent — jamais une exception, purger un cache inexistant n'est pas une
    erreur).
    """
    try:
        collection = _get_collection()
        avant = collection.count()
        if avant_jours is None:
            tout = collection.get()
            if tout.get("ids"):
                collection.delete(ids=tout["ids"])
        else:
            limite_epoch = time.time() - avant_jours * 86400
            collection.delete(where={"horodatage_epoch": {"$lt": limite_epoch}})
        return avant - collection.count()
    except Exception:
        return 0
