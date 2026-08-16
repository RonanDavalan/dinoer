"""
synthese.py — Rédaction du rapport final de campagne par « context stuffing ».

Dernière étape du pipeline de recherche profonde (DINOER_RESEARCH.md §11),
version simplifiée décidée par l'opérateur le 28/07/2026 : pas de sélection par
pertinence vectorielle dans ce lot (`lib/vector.py::indexer_document` reste
disponible mais n'est pas appelé ici) — tout le corpus retenu par une
campagne est concaténé directement dans le prompt de synthèse. Plus simple,
suffisant pour un premier lot, fonctionne sans surcharge CPU sur Raspberry
Pi (aucun calcul d'embedding requis pour produire le rapport). La sélection
RAG reste une évolution possible sans changer l'appelant (`campagne.py`).

Trois fonctions, dans l'ordre d'appel :
  1. `construire_contexte()`   — lit `collecte.jsonl`, concatène et tronque.
  2. `rediger_rapport()`       — invoque OpenCode, ajoute les sources en dur.
  3. `ecrire_rapport()`        — persiste le Markdown sur disque.

Dépendance : `lib/modeles.py::invoquer_opencode()` (sous-processus OpenCode,
raisonnement déporté gratuit, cf. FONDATION_DINOER.md §3).
"""
import json
import os
from datetime import datetime, timezone

from lib.modeles import invoquer_opencode

# Garde-fous de taille — aucun modèle "flash" ne garantit une fenêtre de
# contexte illimitée, et rien ne borne aujourd'hui la taille de
# collecte.jsonl. Valeurs de départ raisonnables, non vérifiées contre la
# limite réelle du modèle OpenCode par défaut (non documentée publiquement
# de façon fiable) — à ajuster si un run réel échoue pour dépassement de
# contexte plutôt que fixées ici par anticipation non testée.
_MAX_CARACTERES_PAR_PAGE = 4000
_MAX_CARACTERES_TOTAL = 60000

_PROMPT_GABARIT = """Tu es un assistant de recherche documentaire. À partir des extraits de \
pages web ci-dessous, rédige une synthèse en français, au format Markdown, factuelle et \
structurée en sections thématiques claires. N'invente aucune information absente des \
extraits — si les extraits ne permettent pas de répondre à un point, dis-le explicitement \
plutôt que de combler par supposition. Ne rédige PAS de section « Sources » : elle est \
ajoutée automatiquement après ta réponse, à partir des mêmes extraits.

Extraits :
{contexte}
"""


def construire_contexte(
    chemin_corpus: str,
    max_caracteres_par_page: int = _MAX_CARACTERES_PAR_PAGE,
    max_caracteres_total: int = _MAX_CARACTERES_TOTAL,
) -> tuple[str, list[dict]]:
    """Lit `collecte.jsonl` (une ligne JSON par page retenue, écrite par
    `campagne.py`), concatène les textes en un contexte unique.

    Chaque page est tronquée à `max_caracteres_par_page` ; l'ajout s'arrête
    dès que `max_caracteres_total` serait dépassé — les pages suivantes du
    corpus, si tronquées de fait, ne sont simplement pas incluses (aucune
    priorisation autre que l'ordre d'écriture dans le fichier).

    Retourne `(contexte, sources)` où `sources` est la liste ordonnée des
    `{"titre", "url"}` réellement inclus dans le contexte — c'est cette
    liste, et non une production du modèle, qui alimente la section
    « Sources citées » du rapport final (§ doctrine de vérifiabilité,
    FONDATION_DINOER.md §3 : un modèle peut mal reproduire une URL, le
    corpus source, non).

    Retourne `("", [])` si le fichier est absent ou vide — jamais une
    exception : un corpus vide est un état normal (campagne sans résultat),
    pas une erreur.
    """
    sources: list[dict] = []
    morceaux: list[str] = []
    taille_totale = 0

    if not os.path.isfile(chemin_corpus):
        return "", []

    with open(chemin_corpus, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne:
                continue
            try:
                entree = json.loads(ligne)
            except json.JSONDecodeError:
                continue

            texte = (entree.get("texte") or "").strip()
            if not texte:
                continue

            url = entree.get("url")
            titre = entree.get("titre") or url or "(sans titre)"
            bloc = f"### {titre}\nSource : {url}\n\n{texte[:max_caracteres_par_page]}\n"

            if taille_totale + len(bloc) > max_caracteres_total:
                break

            morceaux.append(bloc)
            taille_totale += len(bloc)
            sources.append({"titre": titre, "url": url})

    return "\n---\n".join(morceaux), sources


def rediger_rapport(contexte: str, sources: list[dict], modele: str = None) -> str:
    """Invoque OpenCode pour rédiger le corps du rapport, puis ajoute une
    section « Sources citées » construite en dur depuis `sources` (jamais
    par le modèle — cf. `construire_contexte()`).

    Propage `RuntimeError` si OpenCode échoue (binaire absent, timeout,
    texte vide) — cf. `lib/modeles.py::invoquer_opencode()`. L'appelant
    (`campagne.py`) décide de la dégradation : le corpus source, lui, reste
    intact et exploitable même sans rapport de synthèse.
    """
    kwargs = {"modele": modele} if modele else {}
    resultat = invoquer_opencode(_PROMPT_GABARIT.format(contexte=contexte), **kwargs)

    lignes_sources = "\n".join(
        f"- [{s['titre']}]({s['url']})" for s in sources if s.get("url")
    )
    horodatage = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    return (
        f"{resultat['texte'].strip()}\n\n"
        f"## Sources citées\n\n{lignes_sources}\n\n"
        f"---\n*Rapport généré par Dinoer le {horodatage} "
        f"({len(sources)} page(s) source, modèle : {resultat['modele']}).*\n"
    )


def ecrire_rapport(repertoire_campagne: str, id_campagne: str, markdown: str) -> str:
    """Persiste le rapport sous `repertoire_campagne/rapport_<horodatage>.md`
    — même répertoire que `collecte.jsonl` de cette campagne (choix simple :
    aucune résolution de chemin supplémentaire à maintenir en cohérence avec
    `campagne.py::_repertoire_campagnes()`). Horodatage dans le nom de
    fichier pour ne jamais écraser un rapport précédent de la même
    campagne relancée un autre jour.
    """
    os.makedirs(repertoire_campagne, exist_ok=True)
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    chemin = os.path.join(repertoire_campagne, f"rapport_{horodatage}.md")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(markdown)
    return chemin
