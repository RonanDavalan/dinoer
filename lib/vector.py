"""
vector.py — Interface optionnelle vers une base vectorielle ChromaDB.

Permet à Dinoer de s'interfacer avec n'importe quel écosystème RAG existant.
N'est pas un RAG embarqué — fournit les primitives d'accès pour l'utilisateur
qui souhaite connecter son propre système de mémoire vectorielle.

Résolution de DB_PATH (par ordre de priorité) :
  1. DINOER_VECTOR_DB env var
  2. Clé "vector_db" dans le fichier lu par lib.repertoire_chiffre._lire_conf()
     (DINOER_CONF, ou /opt/dinoer/dinoer.conf par défaut)
  3. _CADRE/MEMOIRE/chroma_db (si répertoire jumeau _CADRE/ présent)
  4. ~/Vaults/Dinoer/chroma_db (défaut universel)

Dépendances optionnelles : chromadb, requests (non requises pour l'import).
"""

import os
import uuid


def _chemin_db() -> str:
    """Résout le chemin de la base vectorielle ChromaDB."""
    if "DINOER_VECTOR_DB" in os.environ:
        return os.path.expanduser(os.environ["DINOER_VECTOR_DB"])

    # Audit 05/08/2026 (D-03) : une constante _CONF_PATH locale ignorait
    # DINOER_CONF — un lecteur unique désormais, partagé avec repertoire_chiffre.
    try:
        from lib.repertoire_chiffre import _lire_conf
        conf = _lire_conf()
        if "vector_db" in conf:
            return os.path.expanduser(conf["vector_db"])
    except Exception:
        pass

    # Répertoire jumeau _CADRE/ (contexte de développement, sibling du dépôt)
    _repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _cadre_dir = os.path.normpath(os.path.join(_repo_dir, "..", "_CADRE"))
    if os.path.isdir(_cadre_dir):
        return os.path.join(_cadre_dir, "MEMOIRE", "chroma_db")

    return os.path.expanduser("~/Vaults/Dinoer/chroma_db")


DB_PATH     = _chemin_db()
OLLAMA_URL  = os.environ.get("DINOER_OLLAMA_URL",  "http://localhost:11434")
EMBED_MODEL = os.environ.get("DINOER_EMBED_MODEL", "nomic-embed-text")


def get_client():
    """Retourne un client ChromaDB persistant. Requiert le paquet chromadb."""
    import chromadb
    # L-05 (CHANTIER_SANITISATION.md, LOT 2, amendement 07/08/2026) : même
    # discipline que les autres répertoires sensibles du chantier — la base
    # vectorielle peut indexer des documents privés (_CADRE/MEMOIRE/).
    os.makedirs(DB_PATH, mode=0o700, exist_ok=True)
    os.chmod(DB_PATH, 0o700)
    return chromadb.PersistentClient(path=DB_PATH)


def embed(texts: list[str]) -> list[list[float]]:
    """Génère les embeddings via Ollama (nomic-embed-text par défaut)."""
    import requests
    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": texts},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


def decouper_texte(texte: str, taille: int = 500, chevauchement: int = 50) -> list[str]:
    """Découpe `texte` en blocs de `taille` caractères avec `chevauchement`.

    Découpage léger en Python pur, par fenêtre glissante sur les caractères
    (pas de dépendance à un tokenizer) — suffisant pour une première étape
    de RAG (DINOER_RESEARCH.md §11). Chaque bloc est nettoyé des espaces de
    bord ; les blocs vides (texte source plus court que `taille`, ou
    fenêtre finale entièrement blanche) sont omis.
    """
    if chevauchement >= taille:
        raise ValueError("chevauchement doit être strictement inférieur à taille")

    texte = texte.strip()
    if not texte:
        return []

    pas = taille - chevauchement
    blocs = []
    debut = 0
    while debut < len(texte):
        bloc = texte[debut:debut + taille].strip()
        if bloc:
            blocs.append(bloc)
        if debut + taille >= len(texte):
            break
        debut += pas
    return blocs


def indexer_document(texte: str, metadonnees: dict, collection: str = "dinoer") -> int:
    """Découpe, vectorise et insère un document dans ChromaDB.

    `metadonnees` est répliqué tel quel sur chaque bloc (URL, titre, date de
    capture — cf. FONDATION_DINOER.md §6) ; ses valeurs doivent rester des
    scalaires (str/int/float/bool), contrainte de ChromaDB, non validée ici.

    Les identifiants de bloc sont dérivés de `metadonnees["url"]` (ou
    `metadonnees["id"]` à défaut, ou un UUID si aucun des deux n'est fourni)
    suffixé par l'index du bloc : réindexer le même document avec la même
    URL écrase ses blocs précédents (`upsert`) plutôt que de les dupliquer.

    Retourne le nombre de blocs effectivement insérés (0 si `texte` est vide
    après découpage).
    """
    blocs = decouper_texte(texte)
    if not blocs:
        return 0

    identifiant_base = metadonnees.get("url") or metadonnees.get("id") or uuid.uuid4().hex
    ids = [f"{identifiant_base}#{i}" for i in range(len(blocs))]
    embeddings = embed(blocs)

    client = get_client()
    coll = client.get_or_create_collection(collection)
    coll.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=blocs,
        metadatas=[metadonnees for _ in blocs],
    )
    return len(blocs)
