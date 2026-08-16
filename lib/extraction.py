"""
extraction.py — Extraction ciblée sans synthèse (volet B, fonctionnalité 1).

Localise une donnée précise (mot, phrase, paragraphe, chapitre, nom, date)
dans un corpus de campagne, sans rédiger de synthèse narrative — sortie
structurée (JSON/Markdown/HTML), absence déclarée explicitement plutôt
qu'inventée (cf. TACHE_volet_b_recherche_avancee.md §1).

Réutilise `lib/synthese.py::construire_contexte()` sans modification (même
troncature, même liste `sources` vérifiable) ; seul le prompt envoyé à
OpenCode change. La vérifiabilité est appliquée deux fois, comme dans
`lib/synthese.py::rediger_rapport()` — une fois par consigne dans le prompt,
une fois en dur après coup (une URL citée par le modèle qui ne correspond à
aucune source réellement incluse dans le contexte est neutralisée, jamais
propagée telle quelle : le modèle peut mal reproduire une URL, le corpus
source, non).

Volet C (`TACHE_volet_c_ameliorations_recherche.md`, 12/08/2026) ajoute deux
fonctions indépendantes d'`extraire_cible()`, utilisées par l'appelant d'une
campagne, pas par la primitive elle-même :
  - `mentionne_fenetre_probable()` — pré-filtre textuel pur (aucun appel
    modèle) pour écarter, avant tout appel `extraire_cible()`, les sources
    qui ne mentionnent manifestement pas la fenêtre de dates recherchée.
  - `fusionner_evenements()` — regroupe, après une série d'appels
    `extraire_cible()` positifs, les résultats qui décrivent le même
    événement réel mais ont été trouvés sur des pages différentes.
"""

import json
import re

from lib.modeles import invoquer_opencode
from lib.synthese import construire_contexte

_FORMATS_VALIDES = ("json", "markdown", "html")


_MOTIF_ANNEE_GENERIQUE = re.compile(r"\b(19|20)\d{2}\b")


def mentionne_fenetre_probable(texte: str, motifs_annee: list[str], motifs_mois: list[str]) -> bool:
    """Pré-filtre textuel pur (aucun appel modèle, aucun réseau) : vrai si
    `texte` contient au moins un motif de `motifs_mois`, n'importe où dans
    le texte, **et** que l'année ne contredit pas explicitement la fenêtre
    visée — jamais une exigence de proximité ou d'ordre entre les motifs.

    Deux corrections trouvées en testant contre le corpus réel de la
    campagne du 12/08/2026 (`TACHE_volet_c_ameliorations_recherche.md`
    §3), pas anticipées dans la spécification initiale :

    1. Un regex de proximité stricte (ex. `\\d{1,2}\\s+août\\s+2026`) a été
       écarté d'emblée : invalidé par Moëlan-sur-Mer,
       `Le\\n12\\naoût\\n2026` (jour, mois et année sur des lignes
       séparées après nettoyage HTML).
    2. **Exiger la présence explicite de l'année s'est révélé trop strict**
       à l'exécution : `mairie-benodet.fr/agenda-des-evenements/` (widget
       calendrier réel) liste les dates au format court `15/08`, `16/08`,
       `21/08`... sans jamais écrire « 2026 » nulle part sur la page
       (année implicite, "en cours") — un cas fréquent sur les widgets
       d'agenda, pas une exception rare. Exiger l'année aurait produit un
       faux négatif sur un événement réellement présent (retenu positif
       dans le rapport final de cette campagne). Corrigé : l'année n'est
       exigée que si le texte mentionne **une autre année** que celle
       recherchée sans jamais mentionner celle-ci — l'absence pure et
       simple d'année dans le texte n'écarte jamais une source.

    À l'usage de l'appelant d'une campagne (jamais intégré à
    `extraire_cible()` elle-même, qui reste une primitive pure) pour
    écarter, avant l'appel modèle, une source qui ne mentionne
    manifestement pas la fenêtre recherchée — réduit le coût, au prix d'un
    risque de rappel résiduel assumé (une page ne mentionnant la fenêtre
    que par une formule relative — « ce mercredi », « vendredi prochain »
    — sans jamais écrire le mois en toutes lettres ni en chiffres ne
    serait pas détectée par ce pré-filtre). L'appelant doit compter et
    déclarer explicitement les sources écartées par ce pré-filtre, jamais
    les passer sous silence.

    **`motifs_mois` doit inclure les formes numériques, pas seulement le
    nom en toutes lettres** — troisième correction trouvée à l'exécution :
    le même widget d'agenda Bénodet n'écrit jamais « août », seulement
    `15/08`, `16/08`... `["août", "aout", "/08"]` (ou `"-08-"`, `"08/2026"`
    selon les formats rencontrés) est le motif minimal qui couvre les
    deux formes réellement observées dans le corpus du 12/08/2026.
    """
    texte_lower = texte.lower()
    if not any(motif.lower() in texte_lower for motif in motifs_mois):
        return False
    if any(motif.lower() in texte_lower for motif in motifs_annee):
        return True
    # Aucune année recherchée trouvée : rejeter seulement si une AUTRE
    # année apparaît explicitement (texte daté d'une autre période) —
    # l'absence pure et simple de toute année reste probable (cf. §2 ci-dessus).
    return _MOTIF_ANNEE_GENERIQUE.search(texte) is None

_PROMPT_GABARIT = """Tu es un assistant d'extraction documentaire. À partir des extraits de \
pages web ci-dessous, localise strictement la donnée suivante, sans la reformuler ni la \
compléter par une déduction : {cible}

Règles impératives :
- Ne réponds qu'à partir du texte des extraits ci-dessous, jamais de connaissance générale.
- Si la donnée n'apparaît dans aucun extrait, déclare-le explicitement plutôt que de deviner
  ou d'approcher une valeur plausible.
- Réponds UNIQUEMENT par un objet JSON strict, sans texte ni balise Markdown autour, au
  format exact :
  {{"trouve": true, "valeur": "<citation exacte trouvée>", "url": "<url de l'extrait source>"}}
  ou, si absent :
  {{"trouve": false, "valeur": null, "url": null}}

Extraits :
{contexte}
"""


class ExtractionIntrouvableError(RuntimeError):
    """Sortie du modèle non parseable en JSON valide — distincte d'un
    résultat négatif légitime (`trouve: false`), qui n'est pas une erreur :
    c'est le modèle qui n'a pas respecté le contrat de sortie, pas le corpus
    qui manque de la donnée cherchée."""


def extraire_cible(
    chemin_corpus: str, cible: str, format_sortie: str = "json", modele: str | None = None,
) -> str:
    """Point d'entrée. `format_sortie` : "json" (défaut), "markdown" ou
    "html". Lève `ValueError` sur un format inconnu, `ExtractionIntrouvableError`
    si OpenCode ne respecte pas le contrat JSON (propagé, jamais avalé : une
    sortie non-conforme n'est pas la même chose qu'une absence légitime dans
    le corpus). Propage aussi `RuntimeError` de `invoquer_opencode()` telle
    quelle (binaire absent, timeout — mêmes conditions que `rediger_rapport()`).
    """
    if format_sortie not in _FORMATS_VALIDES:
        raise ValueError(f"format_sortie inconnu : {format_sortie!r} (attendu {_FORMATS_VALIDES})")

    contexte, sources = construire_contexte(chemin_corpus)
    if not sources:
        resultat = {"trouve": False, "valeur": None, "url": None, "raison": "corpus_vide"}
        return _serialiser(resultat, format_sortie, cible)

    kwargs = {"modele": modele} if modele else {}
    brut = invoquer_opencode(_PROMPT_GABARIT.format(cible=cible, contexte=contexte), **kwargs)

    resultat = _parser_reponse(brut["texte"])

    urls_valides = {s["url"] for s in sources if s.get("url")}
    if resultat.get("url") and resultat["url"] not in urls_valides:
        resultat["url"] = None

    return _serialiser(resultat, format_sortie, cible)


def _parser_reponse(texte: str) -> dict:
    """Extrait le premier objet JSON du texte brut renvoyé par OpenCode —
    tolère un modèle qui entoure sa réponse de texte ou de balises Markdown
    malgré la consigne, sans tolérer une réponse qui n'en contient aucun."""
    correspondance = re.search(r"\{.*\}", texte, re.DOTALL)
    if not correspondance:
        raise ExtractionIntrouvableError(
            f"réponse OpenCode sans objet JSON identifiable : {texte[:200]!r}"
        )
    try:
        donnees = json.loads(correspondance.group(0))
    except json.JSONDecodeError as exc:
        raise ExtractionIntrouvableError(
            f"JSON invalide dans la réponse OpenCode : {texte[:200]!r}"
        ) from exc

    return {
        "trouve": bool(donnees.get("trouve")),
        "valeur": donnees.get("valeur"),
        "url": donnees.get("url"),
    }


def _serialiser(resultat: dict, format_sortie: str, cible: str) -> str:
    corps = {"cible": cible, **resultat}

    if format_sortie == "json":
        return json.dumps(corps, ensure_ascii=False, indent=2)

    if format_sortie == "markdown":
        if corps["trouve"]:
            return f"**{cible}** : {corps['valeur']}\n\nSource : {corps.get('url') or '(non vérifiable)'}\n"
        return f"**{cible}** : non trouvé dans le corpus.\n"

    # html
    if corps["trouve"]:
        valeur = _echapper_html(corps.get("valeur") or "")
        url = _echapper_html(corps.get("url") or "")
        return (
            f"<p><strong>{_echapper_html(cible)}</strong> : {valeur}</p>\n"
            f"<p>Source : {url or '(non vérifiable)'}</p>\n"
        )
    return f"<p><strong>{_echapper_html(cible)}</strong> : non trouvé dans le corpus.</p>\n"


def _echapper_html(texte: str) -> str:
    return (
        texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;")
    )


_PROMPT_GABARIT_FUSION = """Tu compares une liste de descriptions d'événements extraites de pages web \
différentes, pour regrouper celles qui décrivent le même événement réel (même date, même lieu, même \
intitulé), même si le texte diffère d'une page à l'autre.

Descriptions (numérotées à partir de 0) :
{descriptions}

Ne regroupe que les descriptions qui décrivent RÉELLEMENT le même événement — jamais deux événements \
simplement proches en date ou au même endroit. Une description qui ne correspond à aucune autre reste \
seule : ne l'invente pas dans un groupe.

Réponds UNIQUEMENT par un objet JSON strict, sans texte ni balise Markdown autour, au format exact :
  {{"groupes": [{{"indices": [0, 3], "evenement_canonique": "<description fusionnée, factuelle, sans invention>"}}]}}
Les indices non mentionnés dans aucun groupe restent des événements séparés — ne les liste pas ici.
"""


class FusionIntrouvableError(RuntimeError):
    """Sortie du modèle non parseable, indices dupliqués ou hors bornes —
    distincte d'une absence de regroupement légitime (`"groupes": []`),
    qui n'est pas une erreur : c'est le modèle qui n'a pas respecté le
    contrat de sortie, pas les événements qui sont tous distincts."""


def fusionner_evenements(resultats: list[dict], modele: str | None = None) -> list[dict]:
    """Regroupe des résultats positifs d'appels `extraire_cible()` répétés
    (volet C, `TACHE_volet_c_ameliorations_recherche.md` §2) qui décrivent
    le même événement réel trouvé sur des pages différentes.

    `resultats` : liste de dicts au format retourné par
    `extraire_cible(..., format_sortie="json")` une fois parsé — au
    minimum les clés `valeur` et `url`. Les entrées où `trouve` est faux
    ou `valeur` absente sont ignorées.

    Retourne une liste de `{"evenement": <texte>, "urls": [...]}` — chaque
    URL source d'origine est toujours conservée, groupée ou non (jamais une
    seule URL retenue au détriment des autres : l'utilisateur doit pouvoir
    remonter à toutes les pages qui mentionnent un événement, pas
    seulement la première).

    Écarté après vérification contre des données réelles (voir la fiche) :
    une empreinte de hachage sur le texte brut des pages avant l'appel
    `extraire_cible()` — inefficace par construction, le doublon est au
    niveau de l'événement décrit, jamais de la page qui le décrit (des
    pages différentes du même site ne sont jamais du texte identique).

    0 ou 1 résultat positif : aucun appel modèle (rien à regrouper), même
    économie que `selectionner_meilleur()` sur un candidat unique. Lève
    `FusionIntrouvableError` sur une sortie modèle non conforme — la
    dégradation (aucun regroupement) est la responsabilité de l'appelant,
    pas de cette fonction.
    """
    positifs = [r for r in resultats if r.get("trouve") and r.get("valeur")]
    if len(positifs) <= 1:
        return [
            {"evenement": r["valeur"], "urls": [r["url"]] if r.get("url") else []}
            for r in positifs
        ]

    bloc_descriptions = "\n---\n".join(
        f"[{i}] {r['valeur']}" for i, r in enumerate(positifs)
    )
    prompt = _PROMPT_GABARIT_FUSION.format(descriptions=bloc_descriptions)

    kwargs = {"modele": modele} if modele else {}
    brut = invoquer_opencode(prompt, **kwargs)

    correspondance = re.search(r"\{.*\}", brut["texte"], re.DOTALL)
    if not correspondance:
        raise FusionIntrouvableError(
            f"réponse OpenCode sans objet JSON identifiable : {brut['texte'][:200]!r}"
        )
    try:
        donnees = json.loads(correspondance.group(0))
    except json.JSONDecodeError as exc:
        raise FusionIntrouvableError(
            f"JSON invalide dans la réponse OpenCode : {brut['texte'][:200]!r}"
        ) from exc

    groupes_bruts = donnees.get("groupes") or []
    indices_couverts: set[int] = set()
    resultat: list[dict] = []

    for groupe in groupes_bruts:
        indices = groupe.get("indices")
        if not isinstance(indices, list) or not indices:
            raise FusionIntrouvableError(f"groupe sans indices valides : {groupe!r}")
        indices_valides = []
        for indice in indices:
            try:
                indice = int(indice)
            except (TypeError, ValueError) as exc:
                raise FusionIntrouvableError(f"indice non entier dans un groupe : {indice!r}") from exc
            if not (0 <= indice < len(positifs)):
                raise FusionIntrouvableError(
                    f"indice hors bornes dans un groupe : {indice!r} (attendu 0..{len(positifs) - 1})"
                )
            if indice in indices_couverts:
                raise FusionIntrouvableError(f"indice {indice!r} présent dans plusieurs groupes")
            indices_valides.append(indice)
            indices_couverts.add(indice)

        evenement = groupe.get("evenement_canonique") or positifs[indices_valides[0]]["valeur"]
        urls = [positifs[i]["url"] for i in indices_valides if positifs[i].get("url")]
        resultat.append({"evenement": evenement, "urls": urls})

    for i, r in enumerate(positifs):
        if i not in indices_couverts:
            resultat.append({"evenement": r["valeur"], "urls": [r["url"]] if r.get("url") else []})

    return resultat
