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
"""

import json
import re

from lib.modeles import invoquer_opencode
from lib.synthese import construire_contexte

_FORMATS_VALIDES = ("json", "markdown", "html")

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
