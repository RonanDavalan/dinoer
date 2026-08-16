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

Volet C (`TACHE_volet_c_ameliorations_recherche.md`, 12/08/2026) ajoute la
lecture des PDF : `pdftotext` (paquet système `poppler-utils`), détecté à
l'exécution (`shutil.which`), jamais une dépendance pip nouvelle — un PDF
sans `pdftotext` disponible dégrade proprement en `refusee`, jamais une
exception, avec un avertissement `stderr` une seule fois par processus.
"""
import shutil
import subprocess
import sys
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

_TIMEOUT_PDFTOTEXT_S = 30
_AVERTI_PDFTOTEXT_ABSENT = False


def _robots_autorise(url: str, user_agent: str) -> bool | None:
    """True/False si robots.txt tranche, None si illisible (statut 'inconnu' —
    traité comme autorisé, cohérent avec `chemin_autorise_robots()` de
    Sentinelle : un robots.txt absent ou inaccessible n'est pas une interdiction).

    Fetch via `requests` avec `user_agent` — jamais `RobotFileParser.read()`,
    qui délègue en interne à `urllib.request` avec le user-agent par défaut
    de Python (`Python-urllib/x.y`), distinct de celui réellement utilisé pour
    la requête de contenu. Bug trouvé en reproduisant un cas réel
    (`deconcarneauapontaven.com`, campagne du 12/08/2026) : ce site répond
    403 au user-agent nu de `urllib` — ce qui fait basculer `RobotFileParser`
    en `disallow_all=True` — tout en répondant 200 avec un contenu qui
    n'interdit rien à un user-agent de navigateur déclaré.
    """
    import requests

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser(robots_url)
    try:
        resp = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=10)
    except requests.exceptions.RequestException:
        return None
    if resp.status_code in (401, 403):
        parser.disallow_all = True
    elif 200 <= resp.status_code < 300:
        parser.parse(resp.text.splitlines())
    else:
        # robots.txt absent (404) ou erreur serveur : traité comme autorisé,
        # même doctrine que `RobotFileParser.read()` sur un fichier introuvable.
        return None
    try:
        return parser.can_fetch(user_agent, url)
    except Exception:
        return None


def _traiter_pdf(url: str, contenu: bytes) -> dict:
    """Palier léger étendu aux PDF (volet C §1) : `pdftotext -` lit le flux
    binaire depuis stdin, écrit le texte sur stdout — aucun fichier
    temporaire. Ne tente ni titre ni détection WAF (hors périmètre d'un
    flux binaire, `_detecter_waf` attend du HTML).

    Un PDF sans texte extractible (scanné/image, aucune couche texte) ou
    dont le texte extrait tombe sous `_SEUIL_TEXTE_INSUFFISANT` retourne
    `refusee`/`pdf_illisible` — **jamais** `insuffisante_legere` : contrairement
    à une coquille JavaScript, l'escalade au palier lourd (Playwright)
    n'aide en rien ici, un navigateur ne lit pas mieux un PDF scanné qu'un
    `pdftotext` sans couche OCR (décision tranchée dans la fiche, pas une
    omission).
    """
    global _AVERTI_PDFTOTEXT_ABSENT

    chemin_pdftotext = shutil.which("pdftotext")
    if not chemin_pdftotext:
        if not _AVERTI_PDFTOTEXT_ABSENT:
            print(
                "⚠ Dinoer : pdftotext introuvable — les sources PDF ne seront pas "
                "lues (dégradation, aucune campagne interrompue). Installer : "
                "apt install poppler-utils",
                file=sys.stderr,
            )
            _AVERTI_PDFTOTEXT_ABSENT = True
        return {"statut": "refusee", "url": url, "titre": None, "texte": None,
                "raison": "pdf_sans_pdftotext"}

    try:
        resultat = subprocess.run(
            [chemin_pdftotext, "-", "-"], input=contenu,
            capture_output=True, timeout=_TIMEOUT_PDFTOTEXT_S,
        )
    except subprocess.TimeoutExpired:
        return {"statut": "echec_transitoire", "url": url, "titre": None, "texte": None,
                "raison": "timeout_pdftotext"}

    texte = resultat.stdout.decode("utf-8", errors="ignore").strip()
    if len(texte) < _SEUIL_TEXTE_INSUFFISANT:
        return {"statut": "refusee", "url": url, "titre": None,
                "texte": texte or None, "raison": "pdf_illisible"}

    return {"statut": "visitee", "url": url, "titre": None, "texte": texte, "raison": None}


def recuperer(
    url: str,
    timeout: int = 10,
    user_agent: str = _USER_AGENT_DEFAUT,
    ignorer_robots: bool = False,
) -> dict:
    """Tente une extraction légère de `url`. Ne lève jamais — le statut porte
    toujours le diagnostic (machine à états, DINOER_RESEARCH.md §5).

    Retourne `{"statut", "url", "titre", "texte", "raison"}` :
      - `"visitee"`             : texte exploitable, `texte`/`titre` renseignés
                                  (`titre` toujours `None` pour un PDF, volet C §1).
      - `"refusee"`             : robots.txt interdit, refus HTTP (403/429/404),
                                  WAF détecté même sur 200 (§6), ou PDF sans
                                  `pdftotext` disponible (`raison:
                                  "pdf_sans_pdftotext"`) ou sans texte extractible
                                  (`raison: "pdf_illisible"`, volet C §1) — jamais
                                  à escalader vers le palier lourd : un navigateur
                                  ne lit pas mieux un PDF scanné que `pdftotext`.
      - `"insuffisante_legere"` : 200 OK mais corps quasi vide après nettoyage
                                  (coquille SPA probable, HTML uniquement) —
                                  candidate légitime à l'escalade vers le palier
                                  lourd.
      - `"echec_transitoire"`   : timeout (réseau ou `pdftotext`), coupure réseau
                                  — retentable, jamais mémorisé comme définitif
                                  (§7.3).
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

    content_type = resp.headers.get("Content-Type", "").lower()
    if "pdf" in content_type or url.lower().split("?")[0].endswith(".pdf"):
        return _traiter_pdf(url, resp.content)

    if "html" not in content_type:
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
