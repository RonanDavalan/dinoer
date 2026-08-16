"""
fetch_leger.py — Palier léger de collecte : HTTP pur + nettoyage HTML, sans navigateur.

Deuxième palier du pipeline de recherche profonde (DINOER_RESEARCH.md §3.2),
entre la découverte (`lib/searxng.py`) et l'escalade lourde (`shot.py`/`rpa.py`,
réservée aux cibles marquées `insuffisante_legere`). Reprend le nettoyage HTML
d'`aspirer_pages()` (Sentinelle/collecteur/module1_collecte.py), sans le crawl
en profondeur : une URL candidate est une entrée du corpus, pas un site entier
à explorer (cf. DINOER_RESEARCH.md §1 et §3.2).

Respecte robots.txt avant toute requête (`RobotFileParser`, comme Sentinelle) —
absent du palier lourd historique de `shot.py`. Réutilise l'heuristique WAF
existante (`shot.py::_detecter_waf`, fonction pure sans dépendance Playwright,
importable sans le paquet playwright installé) pour distinguer un refus
(§6, jamais escaladé) d'une simple insuffisance technique (coquille SPA,
escaladable).

Dépendances optionnelles : requests, beautifulsoup4 (non requises pour
l'import du module).
"""
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from shot import _detecter_waf

_USER_AGENT_DEFAUT = "Mozilla/5.0 (compatible; Dinoer/1.0; +https://github.com/RonanDavalan/dinoer)"
_BALISES_BRUIT = ("script", "style", "nav", "header", "footer", "aside")
# En dessous de ce seuil de caractères après nettoyage, le corps est traité
# comme une coquille SPA probable plutôt qu'un contenu réel (DINOER_RESEARCH.md §5).
# Calibré bas délibérément : un test réel contre https://example.com/ (page
# statique légitime, 142 caractères de texte complet, aucune coquille JS) a
# montré qu'un seuil de 200 la classait à tort en `insuffisante_legere` —
# escalade Chromium gaspillée sur une page déjà entièrement lue. Un seuil bas
# accepte le risque inverse (une coquille SPA très fine, quelques dizaines de
# caractères de texte de chargement, resterait classée `visitee` avec un
# contenu pauvre) — préféré ici car silencieux et sans gaspillage de ressource,
# plutôt qu'une fausse escalade coûteuse sur du contenu déjà complet.
_SEUIL_TEXTE_INSUFFISANT = 40

# PHASE_VALIDATION (28/07/2026) — confirme empiriquement le risque documenté
# ci-dessus : https://excalidraw.com/ retourne exactement "Excalidraw
# Whiteboard\nYou need to enable JavaScript to run this app." (68 caractères,
# > seuil) et passait à tort en `visitee`. Deuxième signal ajouté, même
# principe que `_WAF_MOTS_CLES_*` dans shot.py (correspondance de locutions
# connues) plutôt qu'un déplacement arbitraire du seuil, qui pénaliserait à
# nouveau des pages courtes mais légitimes comme example.com.
_LOCUTIONS_COQUILLE_JS = (
    "you need to enable javascript",
    "please enable javascript",
    "veuillez activer javascript",
    "javascript est requis",
    "javascript doit être activé",
)


def _robots_autorise(url: str, user_agent: str) -> bool | None:
    """True/False si robots.txt tranche, None si illisible (statut 'inconnu' —
    traité comme autorisé, cohérent avec `chemin_autorise_robots()` de
    Sentinelle : un robots.txt absent ou inaccessible n'est pas une interdiction).
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser(robots_url)
    try:
        parser.read()
    except Exception:
        return None
    try:
        return parser.can_fetch(user_agent, url)
    except Exception:
        return None


def recuperer(
    url: str,
    timeout: int = 10,
    user_agent: str = _USER_AGENT_DEFAUT,
    ignorer_robots: bool = False,
) -> dict:
    """Tente une extraction légère de `url`. Ne lève jamais — le statut porte
    toujours le diagnostic (machine à états, DINOER_RESEARCH.md §5).

    Retourne `{"statut", "url", "titre", "texte", "raison"}` :
      - `"visitee"`             : texte exploitable, `texte`/`titre` renseignés.
      - `"refusee"`             : robots.txt interdit, ou refus HTTP (403/429/404),
                                  ou WAF détecté même sur 200 (§6) — jamais à
                                  escalader vers le palier lourd.
      - `"insuffisante_legere"` : 200 OK mais corps quasi vide après nettoyage
                                  (coquille SPA probable) — candidate légitime
                                  à l'escalade vers le palier lourd.
      - `"echec_transitoire"`   : timeout, coupure réseau — retentable, jamais
                                  mémorisé comme définitif (§7.3).
    """
    import requests
    from bs4 import BeautifulSoup

    if not ignorer_robots and _robots_autorise(url, user_agent) is False:
        return {"statut": "refusee", "url": url, "titre": None, "texte": None,
                "raison": "robots_interdit"}

    try:
        resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout,
                             allow_redirects=True)
    except requests.exceptions.Timeout:
        return {"statut": "echec_transitoire", "url": url, "titre": None, "texte": None,
                "raison": "timeout"}
    except requests.exceptions.RequestException as e:
        return {"statut": "echec_transitoire", "url": url, "titre": None, "texte": None,
                "raison": f"reseau : {type(e).__name__}"}

    if resp.status_code in (403, 429, 404):
        return {"statut": "refusee", "url": url, "titre": None, "texte": None,
                "raison": f"http_{resp.status_code}"}

    if "html" not in resp.headers.get("Content-Type", "").lower():
        return {"statut": "refusee", "url": url, "titre": None, "texte": None,
                "raison": "contenu_non_html"}

    soup = BeautifulSoup(resp.text, "html.parser")
    titre = soup.title.get_text(strip=True) if soup.title else None

    # Doctrine WAF (DINOER_RESEARCH.md §6) : ne pas classifier sur le seul code
    # HTTP — un interstitiel de challenge répond fréquemment 200.
    if _detecter_waf(resp.status_code, titre, resp.text[:5000]):
        return {"statut": "refusee", "url": url, "titre": titre, "texte": None,
                "raison": "waf_detecte"}

    for tag in soup(_BALISES_BRUIT):
        tag.decompose()

    textes_images = [
        val for img in soup.find_all("img")
        for attr in ("alt", "title")
        if (val := (img.get(attr) or "").strip())
    ]

    texte = soup.get_text(separator="\n", strip=True)
    if textes_images:
        texte += "\n" + "\n".join(textes_images)

    texte_lower = texte.lower()
    if len(texte) < _SEUIL_TEXTE_INSUFFISANT:
        return {"statut": "insuffisante_legere", "url": url, "titre": titre,
                "texte": texte or None, "raison": "corps_vide_ou_court"}
    if any(locution in texte_lower for locution in _LOCUTIONS_COQUILLE_JS):
        return {"statut": "insuffisante_legere", "url": url, "titre": titre,
                "texte": texte, "raison": "coquille_js_detectee"}

    return {"statut": "visitee", "url": url, "titre": titre, "texte": texte, "raison": None}
