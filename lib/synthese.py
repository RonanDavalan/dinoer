"""
synthese.py — Rédaction du rapport final de campagne par « context stuffing ».

Dernière étape du pipeline de recherche profonde (DINOER_RESEARCH.md §11).
Décision du 13/08/2026 (session 3, `TACHE_fiabilisation_synthese_campagne.md`,
table de vérité mesurée dans la fiche — ne pas re-dériver) : le pré-filtre
textuel seul (`mentionne_fenetre_probable()`) s'est révélé **insuffisant**
sur le corpus de référence — les deux pages du programme officiel
(`deconcarneauapontaven.com`) passaient le filtre booléen (29/49 pages
« probables ») mais restaient en position 27-28/29 par ordre d'écriture,
donc toujours hors du budget de troncature (60000 car. ≈ 16 pages). Un
classement par similarité cosinus (`lib/vector.py::embed()`, requête =
`sujet_synthese`) les fait remonter en position 4 et 7/29 — mesuré, pas
supposé. Retenu : pré-filtre temporel (`motifs_annee`/`motifs_mois`) en
premier passage grossier, classement sémantique (`sujet_synthese`) en
second passage fin, chacun optionnel et indépendant. Coût mesuré négligeable
(11,0 s pour 1525 chunks au niveau corpus complet ; 4,33 s pour 30 textes au
niveau page, cas réel de cette décision) — usage ponctuel en mémoire, aucune
collection ChromaDB ouverte (`lib/vector.py::get_client()` reste réservé à
un usage de mémoire durable entre campagnes, hors périmètre ici).

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

# Import différé (dans construire_contexte(), pas ici) : lib.extraction importe
# construire_contexte() au niveau module, un import direct ici créerait un
# cycle d'import (lib.synthese <-> lib.extraction).

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


def _trier_par_pertinence_semantique(pages: list[dict], sujet: str, max_caracteres_par_page: int) -> list[dict]:
    """Classe `pages` par similarité cosinus décroissante entre l'embedding
    de `sujet` et celui de chaque page tronquée (même troncature que le
    contexte final, un seul appel `embed()` groupé — requête + toutes les
    pages). Usage ponctuel, en mémoire, jamais persisté sur disque : aucune
    collection ChromaDB ouverte ici (`lib/vector.py::embed()` seul, pas
    `get_client()`).

    Dégrade silencieusement vers l'ordre reçu si `embed()` échoue (Ollama
    indisponible) — une amélioration de classement optionnelle ne doit
    jamais faire échouer la synthèse, même discipline que le bloc
    best-effort qui appelle `construire_contexte()` dans `campagne.py`.
    """
    from lib.vector import embed

    textes = [sujet] + [p["texte"][:max_caracteres_par_page] for p in pages]
    try:
        vecteurs = embed(textes)
    except Exception:
        return pages

    v_sujet, v_pages = vecteurs[0], vecteurs[1:]

    def cosinus(a: list[float], b: list[float]) -> float:
        produit = sum(x * y for x, y in zip(a, b))
        norme_a = sum(x * x for x in a) ** 0.5
        norme_b = sum(x * x for x in b) ** 0.5
        return produit / (norme_a * norme_b) if norme_a and norme_b else 0.0

    classees = sorted(zip(pages, v_pages), key=lambda pv: -cosinus(v_sujet, pv[1]))
    return [p for p, _ in classees]


def construire_contexte(
    chemin_corpus: str,
    max_caracteres_par_page: int = _MAX_CARACTERES_PAR_PAGE,
    max_caracteres_total: int = _MAX_CARACTERES_TOTAL,
    motifs_annee: list[str] | None = None,
    motifs_mois: list[str] | None = None,
    sujet_synthese: str | None = None,
) -> tuple[str, list[dict], list[dict]]:
    """Lit `collecte.jsonl` (une ligne JSON par page retenue, écrite par
    `campagne.py`), concatène les textes en un contexte unique.

    Deux repositionnements optionnels et indépendants, appliqués avant la
    troncature — jamais une exclusion, toujours une relégation :

    1. Si `motifs_annee` et `motifs_mois` sont fournis : passage grossier via
       `mentionne_fenetre_probable()` (pré-filtre textuel pur, zéro appel
       modèle) — les pages qui ne mentionnent manifestement pas la fenêtre
       temporelle demandée sont reléguées après toutes les autres.
    2. Si `sujet_synthese` est fourni : passage fin par similarité cosinus
       (`_trier_par_pertinence_semantique()`) à l'intérieur du groupe retenu
       par le passage 1 (ou de tout le corpus si le passage 1 n'a pas eu
       lieu) — nécessaire en complément du passage 1 seul, mesuré
       insuffisant sur le corpus de référence (voir docstring du module).

    Sans aucun des trois paramètres (défaut), aucun repositionnement n'a
    lieu : comportement identique à avant le 13/08/2026 (session 3,
    `TACHE_fiabilisation_synthese_campagne.md`).

    Chaque page est tronquée à `max_caracteres_par_page` ; l'ajout s'arrête
    dès que `max_caracteres_total` serait dépassé — les pages reléguées en
    fin de liste sont donc les premières sacrifiées par la troncature,
    plutôt que sacrifiées au hasard de l'ordre d'écriture du fichier.

    Retourne `(contexte, sources, pages_repoussees)` :
    - `sources` est la liste ordonnée des `{"titre", "url"}` réellement
      inclus dans le contexte — c'est cette liste, et non une production du
      modèle, qui alimente la section « Sources citées » du rapport final
      (§ doctrine de vérifiabilité, FONDATION_DINOER.md §3 : un modèle peut
      mal reproduire une URL, le corpus source, non).
    - `pages_repoussees` est la liste des `{"titre", "url"}` écartées par le
      pré-filtre temporel — passage 1 uniquement, qu'elles aient fini
      incluses après troncature ou non (le classement sémantique du passage
      2 est une réorganisation, pas une exclusion, donc n'y figure jamais) —
      toujours `[]` si `motifs_annee`/`motifs_mois` ne sont pas fournis.
      L'appelant doit la compter et la déclarer explicitement, jamais la
      passer sous silence (contrat imposé par le docstring de
      `mentionne_fenetre_probable()`).

    Retourne `("", [], [])` si le fichier est absent ou vide — jamais une
    exception : un corpus vide est un état normal (campagne sans résultat),
    pas une erreur.
    """
    if not os.path.isfile(chemin_corpus):
        return "", [], []

    pages: list[dict] = []
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
            pages.append({"titre": titre, "url": url, "texte": texte})

    if motifs_annee and motifs_mois:
        from lib.extraction import mentionne_fenetre_probable

        probables, improbables = [], []
        for p in pages:
            (probables if mentionne_fenetre_probable(p["texte"], motifs_annee, motifs_mois) else improbables).append(p)
        pages_repoussees = [{"titre": p["titre"], "url": p["url"]} for p in improbables]
    else:
        probables, improbables = pages, []
        pages_repoussees = []

    if sujet_synthese and probables:
        probables = _trier_par_pertinence_semantique(probables, sujet_synthese, max_caracteres_par_page)

    pages = probables + improbables

    sources: list[dict] = []
    morceaux: list[str] = []
    taille_totale = 0
    for page in pages:
        bloc = f"### {page['titre']}\nSource : {page['url']}\n\n{page['texte'][:max_caracteres_par_page]}\n"

        if taille_totale + len(bloc) > max_caracteres_total:
            break

        morceaux.append(bloc)
        taille_totale += len(bloc)
        sources.append({"titre": page["titre"], "url": page["url"]})

    return "\n---\n".join(morceaux), sources, pages_repoussees


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
