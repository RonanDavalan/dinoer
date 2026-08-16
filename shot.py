#!/opt/dinoer/venv/bin/python3
"""
shot.py — point d'entrée Playwright unique de Dinoer : perception sémantique
(arbre d'accessibilité) et exécution d'actions séquentielles (mode ReAct).

Pourquoi ce fichier existe :
    Un LLM ne voit pas le rendu d'une page web. shot.py lui donne un accès
    sémantique (arbre d'accessibilité) et des mains (cliquer, remplir,
    attendre) sur une session Playwright persistante, sans jamais faire
    transiter un credential en clair par le shell. Aucune capture d'image :
    perception textuelle uniquement (FONDATION_DINOER.md §3).

Entrée / sortie :
    CLI — `--url` (nouvelle session) ou `--reprendre-session` (session
    existante) + `--actions`/`--action` (JSON). Sortie : JSON structuré sur
    stdout (boussole, résultat par action, arbre d'accessibilité éventuel).

Dépend de :
    lib/repertoire_chiffre.py (credentials), lib/journal.py (journalisation),
    lib/preflight_guide.py (verrou de lecture du guide), lib/profil_operateur.py,
    lib/modeles.py, lib/ntfy.py (MFA/TOTP).
"""
import argparse
import getpass
import json
import os
import resource
import socket
import sys
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

__version__ = "1.23.0"

# Permet d'importer lib/ depuis le même répertoire que shot.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.sanitisation import (
    _neutraliser_valeur_evaluer,
    _sanitiser_url_journal,
    sanitiser_urls_dans_chaine,
    rediger_query_params_sensibles,
    valider_actions_secrets as _valider_actions_secrets,
)

# Chantier crédibilité (05/08/2026) — trouvé par le cycle .deb réel sur une
# machine où dpkg exécute les scripts postinst avec HOME=/root : sans ce
# réglage, `playwright install chromium` (postinst / install.sh, exécutés en
# root) télécharge Chromium dans /root/.cache/ms-playwright, invisible pour
# l'opérateur réel (HOME différent, ou utilisateur système `dinoer` sans
# home). Fixe l'emplacement indépendamment de qui a lancé l'installation —
# install.sh et postinst pointent tous les deux vers ce même chemin.
# setdefault : un opérateur qui a déjà positionné la variable garde la main.
#
# Restreint à une exécution réelle depuis /opt/dinoer/ (08/08/2026) : sur un
# clone git ailleurs (développement, CI), ce chemin n'existe pas et
# `playwright install` y installe Chromium sous son emplacement par défaut —
# forcer ce chemin fixe fait alors chercher le navigateur là où il n'a jamais
# été installé (BrowserType.launch: Executable doesn't exist). Trouvé sur le
# tout premier run CI réel, masqué en local sur la machine de développement
# où /opt/dinoer/.cache/ existe déjà pour de vraies raisons de production.
if os.path.dirname(os.path.abspath(__file__)) == "/opt/dinoer":
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/dinoer/.cache/ms-playwright")


def _boussole(operation_id=None):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = ""
    b = {
        "utilisateur": os.getenv("USER", ""),
        "ip_locale": ip,
        "repertoire": os.getcwd(),
    }
    if operation_id:
        b["operation_id"] = operation_id
    return b

# ── Champ sensible : prédicat partagé ─────────────────────────────────────────
# Audit 06/08/2026 (F-16) : pwd, passwd, pass, mdp, api_key, apikey,
# credential ajoutés — un champ nommé 'pwd' ou 'mdp' (nommage francophone
# plausible sur les cibles Dinoer) n'était masqué sur aucun des deux canaux
# qui dérivent de ce prédicat unique : exclusion SoM (retirée avec la couche
# visuelle, cf. FONDATION_DINOER.md), rédaction a11y (_DW_VALEURS_SENSIBLES_JS
# ci-dessous, seul consommateur restant).
_DW_EST_SENSIBLE_JS = """
    const dwEstSensible = (el) => el.type === 'password' ||
        /password|pwd|passwd|pass|mdp|token|secret|api_key|apikey|credential|otp|totp|mfa|2fa|cvv|cvc|pan|ssn|iban/i.test(el.name || '') ||
        /password|pwd|passwd|pass|mdp|token|secret|api_key|apikey|credential|otp|totp|mfa|2fa|cvv|cvc|pan|ssn|iban/i.test(el.id || '') ||
        /password/i.test(el.autocomplete || '');
"""

# Audit 06/08/2026 (F-02) : extraite vers lib/securite_url.py — c'était la
# seule des deux copies (shot.py/rpa.py) à contrôler le userinfo. Alias
# conservé pour ne pas toucher les appelants existants dans ce fichier.
from lib.securite_url import valider_schema_url as _valider_schema_url

# ── Détection passive de WAF (v1.16.0, item C) ────────────────────────────────
# Signal non fatal — jamais d'exception. Dinoer perçoit la friction, il ne
# l'arbitre pas : décision session 47 (« Dinoer est un outil de perception,
# pas un arbitre moral de l'accès »). Heuristique par mots-clés — faux positifs
# possibles, à traiter comme un signal rapide, jamais comme un verdict certain.
_WAF_MOTS_CLES_GENERIQUES = ("cloudflare", "akamai")
_WAF_MOTS_CLES_CHALLENGE = (
    "captcha", "access denied", "attention required",
    "checking your browser", "just a moment", "cf-error-details",
    "sorry, you have been blocked", "request blocked",
)


# ── Extraction de texte (palier lourd, FONDATION_DINOER.md §6) ───────────────
# Même liste que lib/fetch_leger.py::_BALISES_BRUIT (palier léger) — dupliquée
# volontairement plutôt qu'importée : le palier lourd ne dépend jamais du
# palier léger (isolation des risques), les deux évoluent indépendamment.
_BALISES_BRUIT_TEXTE = ("script", "style", "nav", "header", "footer", "aside", "noscript")


def _detecter_waf(http_status, titre_page, html_snippet):
    """True si un blocage WAF est probable — 403/429, ou mot-clé de blocage.

    v1.17.2 : les noms de fournisseur génériques (cloudflare, akamai) ne sont
    matchés que sur le titre de page — les matcher contre le HTML brut entier
    produisait un faux-positif systématique sur toute page chargeant une
    ressource CDN ordinaire (ex. <script src="cdnjs.cloudflare.com/...">),
    sans rapport avec un blocage réel. Les expressions propres à une page de
    challenge (captcha, "just a moment"...) restent matchées sur le HTML brut.
    """
    if http_status in (403, 429):
        return True
    titre = (titre_page or "").lower()
    if any(mot in titre for mot in _WAF_MOTS_CLES_GENERIQUES):
        return True
    texte = f"{titre_page or ''} {html_snippet or ''}".lower()
    return any(mot in texte for mot in _WAF_MOTS_CLES_CHALLENGE)


# ── Statistiques DOM structurelles (--no-capture) ────────────────────────────
_DOM_STATS_JS = """() => {
    var q = function(s) { return document.querySelectorAll(s).length; };
    return {
        boutons:            q('button, [role="button"], [role="menuitem"]'),
        inputs:             q('input:not([type="hidden"]), textarea'),
        listes_deroulantes: q('select'),
        formulaires:        q('form'),
        liens:              q('a[href]'),
        dialogues:          q('dialog')
    };
}"""


# ── Arbre d'accessibilité (A11y) ──────────────────────────────────────────────

# Audit 05/08/2026 (D-01, correctif ciblé) : page.aria_snapshot() inclut la
# valeur des champs de saisie, y compris type="password" — vérifié en réel
# contre une cible authentifiée (mot de passe publié en clair dans a11y_tree).
# Réutilise dwEstSensible (_DW_EST_SENSIBLE_JS), seule définition de « champ
# sensible » du fichier depuis le retrait de la couche visuelle.
_DW_VALEURS_SENSIBLES_JS = """() => {""" + _DW_EST_SENSIBLE_JS + """
    const valeurs = [];
    document.querySelectorAll('input, textarea').forEach((el) => {
        if (dwEstSensible(el) && el.value) valeurs.push(el.value);
    });
    return valeurs;
}"""


def _snapshot_a11y(page):
    """Retourne (texte, redaction_echouee) : le snapshot ARIA de la page
    (format texte YAML-like, Playwright 1.9+, rôles/noms/URLs des liens),
    et un booléen signalant si la rédaction ciblée n'a pas pu s'exécuter.
    texte est None si le snapshot lui-même n'est pas disponible, ou si la
    rédaction a échoué.

    Audit 05/08/2026 (D-01, correctif ciblé) : les valeurs des champs
    sensibles actuellement présents dans le DOM (autofill navigateur,
    session persistante — donc pas nécessairement saisis par Dinoer) sont
    rédigées du texte avant retour. Complète le correctif de fond
    (_rediger_valeurs_secrets), qui ne connaît que ce que Dinoer a lui-même
    résolu via _resoudre_valeur_secrets.

    Audit 06/08/2026 (E-07) : si `page.evaluate` échoue (navigation en
    cours, contexte détruit, CSP particulière), la version précédente
    retournait le snapshot intact, non rédigé — un repli qui publiait
    exactement ce que cette fonction existe pour protéger. Le repli sûr
    ici est l'inverse : ne rien publier, avec un signal explicite pour que
    l'appelant le porte dans la boussole plutôt que de le passer sous
    silence.
    """
    try:
        texte = page.aria_snapshot()
    except Exception:
        return None, False
    if not texte:
        return texte, False
    try:
        for v in page.evaluate(_DW_VALEURS_SENSIBLES_JS):
            if v:
                texte = texte.replace(v, "<secret_redige>")
    except Exception:
        return None, True
    return texte, False


# ── Persistance de session (ReAct) ────────────────────────────────────────────

_AVERTISSEMENT_DERIVE = (
    "URL au moment de la reprise diverge de l'URL au moment de la sauvegarde. "
    "L'état DOM (cases cochées, champs saisis, modals ouverts) n'a pas été préservé. "
    "Si le scénario présuppose un état DOM hérité de la session précédente, il échouera "
    "silencieusement. Voir _CADRE/SPECIFICATIONS/26_GUIDE_CLAUDE_SESSION_DINOER.md."
)

_legacy_session_warned = False


def _construire_dinoer_meta(profil, horodatage, modeles_appeles, url_finale):
    """Construit le bloc dinoer_meta v1.3 pour la sortie JSON.

    Renvoie un dict prêt à injecter sous la clé `dinoer_meta` du
    JSON de sortie. Si la traçabilité modèles est désactivée dans
    le profil, la clé `modeles_utilises` est omise (§5.4 spec 33_).
    """
    meta = {
        "version_shot": __version__,
        "horodatage_iso": horodatage,
        "hostname_executant": socket.gethostname(),
        "utilisateur_executant": getpass.getuser(),
        "profil_actif": profil.descripteur(),
        "url_au_moment_capture": url_finale,
    }
    if not profil.tracabilite_modeles_active:
        return meta

    from lib.modeles import collecter_modele_ollama, collecter_modele_claude
    modeles_utilises = []
    for entree in modeles_appeles:
        tag = entree["_tag"]
        role = entree["role"]
        if entree["mode_llm"] == "local":
            modeles_utilises.append(collecter_modele_ollama(
                tag, role,
                inclure_hash=profil.tracabilite_inclure_hash,
            ))
        else:
            modeles_utilises.append(collecter_modele_claude(tag, role))
    meta["modeles_utilises"] = modeles_utilises
    return meta


def _construire_etat(auth_status, respect, derive_session, erreurs_js,
                     waf_bloquants=None, erreurs_console=None, ignorer_waf=False,
                     mode_conseille=None):
    """Synthèse déterministe de l'état opérationnel (v1.16.0, item A).

    Calculée uniquement à partir de signaux déjà présents dans le run — aucun
    appel réseau ni navigateur supplémentaire. Isolée à dessein : appelée
    dans un bloc protégé, son échec ne doit jamais dégrader le reste de la
    sortie JSON.

    Portée assumée : « pret_a_agir » ne vérifie pas la conformité de l'URL ou
    du titre à une attente métier (Dinoer n'a aucune référence externe pour
    cela — c'est le rôle des assertions `evaluer` + `contient`/`motif`/`attendu`
    de rpa.py). Il agrège uniquement les signaux que shot.py peut déterminer
    par lui-même : authentification, dérive de session, plafond de
    navigation, friction réseau/applicative (WAF, erreurs JS/console).

    `ignorer_waf` (v1.17.2) : quand actif, un blocage WAF dégrade toujours
    `niveau_confiance` mais ne force plus `pret_a_agir` à `False` à lui seul —
    évite qu'un faux-positif résiduel bloque l'agent de façon binaire sur une
    page saine (Z.ai, signal 3).
    """
    raisons = []
    pret = True
    niveau = "eleve"

    if auth_status is not None:
        if auth_status == "active":
            raisons.append("session authentifiée active")
        else:
            raisons.append("session non authentifiée (auth_status: inactive)")
            pret = False
            niveau = "faible"

    if derive_session:
        raisons.append(
            "dérive de session détectée — URL divergente depuis la sauvegarde"
        )
        pret = False
        niveau = "faible"

    if respect and respect.get("plafond_atteint"):
        raisons.append(f"plafond de navigation atteint ({respect['plafond_atteint']})")
        pret = False
        if niveau == "eleve":
            niveau = "modere"

    if erreurs_js:
        raisons.append(f"{len(erreurs_js)} erreur(s) JS non interceptée(s)")
        if niveau == "eleve":
            niveau = "modere"

    if erreurs_console:
        raisons.append(f"{len(erreurs_console)} message(s) d'erreur en console")
        if niveau == "eleve":
            niveau = "modere"

    if waf_bloquants:
        if ignorer_waf:
            raisons.append(
                "blocage WAF détecté, ignoré sur demande explicite (--ignorer-waf)"
            )
            if niveau == "eleve":
                niveau = "modere"
        else:
            raisons.append("blocage WAF détecté (signal non fatal, à interpréter)")
            pret = False
            niveau = "faible"

    if not raisons:
        raisons.append("aucun signal de friction détecté")

    etat = {"pret_a_agir": pret, "niveau_confiance": niveau, "raisons": raisons}
    if mode_conseille:
        etat["mode_conseille"] = mode_conseille
        resume = f"mode_conseille disponible : {mode_conseille['mode']} recommandé"
        if mode_conseille["raisons"]:
            resume += f" ({', '.join(mode_conseille['raisons'])})"
        raisons.append(resume)
    return etat


def _nettoyer_session_ephemere(chemin_session, explicitement_demandee):
    """Désactivé (FR-74/FR-75) — ne supprime plus le fichier de session.

    Ancien comportement : supprimait --reprendre-session si --sauver-session
    était absent → FileNotFoundError sur les appels successifs. Le fichier
    appartient à l'opérateur ; shot.py n'a pas à le détruire.
    """


def _journaliser_run(result, actions, intention, cible_url, resultat, erreur=None,
                     operation_id=None, source_scenario=None, chainage=None,
                     secret_resolu=False, secrets_chemin=None):
    """Consigne le run dans le journal d'opérations (v1.4). Best-effort.

    N'altère jamais la sortie ni le code de retour de shot.py : toute
    erreur de journalisation est avalée par lib/journal lui-même.

    `operation_id` (v1.16.0, item B) : transmis tel quel — le journal réutilise
    l'identité de run générée par shot.py au lieu d'en régénérer une nouvelle.

    `chainage` (v1.19.0) : transmis tel quel depuis rpa.py (--chainage), qui
    l'a construit lors de l'aplatissement des `declencher_scenario`. Absent
    sur un run sans chaînage — additif strict.

    `secret_resolu`, `secrets_chemin` (audit 06/08/2026, E-02) : transmis à
    `journal.enregistrer_operation` — second signal d'authentification pour
    l'archivage des preuves, indépendant de `--auth-indicator`.
    """
    try:
        from lib import journal
    except Exception:
        return
    # Retrait de la couche visuelle (08/08/2026) : plus aucune capture PNG
    # produite par ce fichier — captures toujours vide, conservé en argument
    # pour lib/journal.py::enregistrer_operation() (signature inchangée).
    captures = []
    journal.enregistrer_operation(
        outil="shot.py",
        version=__version__,
        cible_url=cible_url,
        resultat=resultat,
        actions=actions,
        dinoer_meta=result.get("dinoer_meta"),
        intention=intention,
        captures=captures,
        erreur=erreur,
        evaluations=result.get("evaluations"),
        operation_id=operation_id,
        respect=result.get("respect"),
        source_scenario=source_scenario,
        chainage=chainage,
        auth_status=result.get("auth_status"),
        secret_resolu=secret_resolu,
        secrets_chemin=secrets_chemin,
    )


def _sauver_session(ctx, page, chemin, viewport):
    """Sauvegarde cookies + localStorage + URL courante dans un fichier JSON.

    Format v1.2 enrichi de dinoer_meta pour la détection de dérive (lot 8.5).
    Les clés url et viewport au niveau racine restent présentes pour la
    rétrocompatibilité du chargement.
    """
    horodatage_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    session = {
        "url": page.url,
        "viewport": viewport,
        "storage_state": ctx.storage_state(),
        "dinoer_meta": {
            "url_au_moment_sauvegarde": page.url,
            "horodatage_iso": horodatage_iso,
            "version_shot": __version__,
        },
    }
    # Écriture atomique : évite la corruption du fichier lors d'appels rapides successifs.
    # Audit 05/08/2026 (C-02) : storage_state est l'équivalent fonctionnel des
    # identifiants après authentification — os.open à mode explicite 0o600,
    # comme le marqueur de guide (preflight_guide.py), plutôt que l'umask du
    # processus (0644 en configuration Debian par défaut).
    # Audit 05/08/2026 (D-09) : chemin_tmp est prévisible (<cible>.tmp). Sans
    # O_EXCL, un fichier ou un lien symbolique pré-existant à ce chemin serait
    # réutilisé avec ses permissions/sa cible actuelles ; O_NOFOLLOW refuse
    # explicitement de suivre un lien. Un .tmp résiduel d'un run précédent est
    # retiré avant l'ouverture — sinon O_EXCL échouerait systématiquement.
    chemin_tmp = chemin + ".tmp"
    try:
        os.unlink(chemin_tmp)
    except FileNotFoundError:
        pass
    fd = os.open(chemin_tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)
    os.replace(chemin_tmp, chemin)  # rename : chemin hérite du mode 0o600 du .tmp


def _charger_session(chemin):
    """Charge une session Dinoer depuis un fichier JSON.

    Émet un warning unique sur stderr si le fichier est au format legacy
    (sans dinoer_meta) : la détection de dérive sera désactivée pour ce run.
    """
    global _legacy_session_warned
    # G-31 (CHANTIER_SANITISATION.md, LOT 5) : O_NOFOLLOW — même discipline
    # que l'écriture (_sauver_session, ligne ci-dessus), ferme la fenêtre où
    # le fichier de session serait remplacé par un lien symbolique avant lecture.
    fd = os.open(chemin, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, encoding="utf-8") as f:
        session = json.load(f)
    if "dinoer_meta" not in session and not _legacy_session_warned:
        print(
            f"⚠ Session legacy détectée (sans dinoer_meta) : "
            f"{chemin} — détection de dérive d'URL désactivée pour ce fichier.",
            file=sys.stderr,
        )
        _legacy_session_warned = True
    return session


def _normaliser_url_derive(url):
    """Normalise une URL pour la comparaison de dérive de session : schéma +
    hôte + port + chemin, plus la query normalisée (paramètres triés, query
    vide traitée comme absente) — fragment ignoré.

    Audit 06/08/2026 (E-03) : distincte de `_sanitiser_url_journal`, qui
    supprime la query entièrement pour la confidentialité du journal — un
    choix légitime là, mais qui rendait la détection de dérive aveugle à
    toute expiration de session dont l'unique signal est un paramètre de
    query (ex. `/?vue=login` remplaçant `/?vue=domaine`).
    """
    if not url:
        return url
    try:
        from urllib.parse import parse_qsl, urlencode
        p = urlparse(url)
        netloc_sans_userinfo = p.hostname or ""
        if p.port:
            netloc_sans_userinfo += f":{p.port}"
        query_triee = urlencode(sorted(parse_qsl(p.query, keep_blank_values=True)))
        base = f"{p.scheme}://{netloc_sans_userinfo}{p.path}"
        return f"{base}?{query_triee}" if query_triee else base
    except Exception:
        return "[url non parseable]"


def _detecter_derive_session(session, url_cible_reprise):
    """Compare l'URL au moment de la sauvegarde à l'URL au moment de la reprise.

    Retourne un dict prêt à injecter sous la clé `derive_session` du JSON
    de sortie si une divergence est détectée, ou None sinon (URLs identiques,
    session legacy, ou URL manquante).

    Audit 05/08/2026 (D-05), affiné 06/08/2026 (E-03) : comparaison sur des
    URL normalisées (schéma + hôte + port + chemin + query triée, via
    _normaliser_url_derive), plutôt que sur la chaîne brute ni sur la query
    entièrement écartée. Sans normalisation de query, une différence
    purement cosmétique (`.../?` vs `.../`) déclenchait une fausse dérive ;
    sans la conserver du tout, une expiration réelle signalée uniquement par
    la query (`/?vue=login` remplaçant `/?vue=domaine`) passait inaperçue —
    et `GUIDE_LLM_SESSIONS.md` prescrit de rejouer l'authentification
    complète dès que ce signal est vrai.
    """
    meta = session.get("dinoer_meta")
    if not meta:
        return None
    url_sauvegardee = meta.get("url_au_moment_sauvegarde")
    if not url_sauvegardee or not url_cible_reprise:
        return None
    if _normaliser_url_derive(url_sauvegardee) == _normaliser_url_derive(url_cible_reprise):
        return None
    return {
        "url_sauvegardee": url_sauvegardee,
        "url_reprise": url_cible_reprise,
        "avertissement": _AVERTISSEMENT_DERIVE,
    }


def parse_args():
    p = argparse.ArgumentParser(description="Dinoer — capture Playwright avec actions")
    # Mode A (séquentiel) : --url requis. Mode B (ReAct) : --reprendre-session à la place.
    p.add_argument("--url", default=None, help="URL à capturer (Mode A) ou navigation initiale (Mode B)")
    p.add_argument("--actions", help="Fichier JSON ou JSON inline d'actions séquentielles (Mode A)")
    p.add_argument("--action", default=None,
                   help="Action unique JSON pour le pas ReAct (Mode B, ex: '{\"type\":\"cliquer\",\"selecteur\":\"#valider\"}')")
    p.add_argument("--reprendre-session", dest="reprendre_session", default=None,
                   metavar="FICHIER", help="Reprend une session sauvegardée (Mode B ReAct)")
    p.add_argument("--sauver-session", dest="sauver_session", default=None,
                   metavar="FICHIER", help="Sauvegarde l'état navigateur après les actions")
    p.add_argument("--attendre-selecteur", dest="attendre_selecteur",
                   help="Sélecteur CSS à attendre avant la lecture de l'état final")
    p.add_argument("--timeout", type=int, default=10000,
                   help="Timeout en ms pour chaque opération (défaut : 10000)")
    p.add_argument("--wait-until", dest="wait_until",
                   choices=["networkidle", "load", "domcontentloaded"],
                   default="networkidle",
                   help="Condition d'arrêt de la navigation initiale (v1.22.0, défaut : "
                        "networkidle, inchangé). Utiliser 'load' sur une cible qui "
                        "n'atteint jamais le silence réseau (page à statistiques live, "
                        "polling continu) : le timeout n'est alors pas une question de "
                        "durée. N'affecte pas l'action 'naviguer'.")
    p.add_argument("--largeur", type=int, default=1280, help="Largeur viewport px (défaut : 1280)")
    p.add_argument("--hauteur", type=int, default=720, help="Hauteur viewport px (défaut : 720)")
    p.add_argument("--a11y", action="store_true",
                   help="Inclut le snapshot d'accessibilité (a11y_tree) dans le JSON")
    p.add_argument("--intention", default=None,
                   help="Libellé métier du run, consigné dans le journal d'opérations "
                        "(v1.4). Ex. : \"Suppression clone __DOMAINE_CLIENT__ 2026-05-30\".")
    p.add_argument("--auth-indicator", dest="auth_indicator", default=None,
                   help="Sélecteur CSS visible uniquement en session authentifiée (v1.9). "
                        "Ajoute auth_status (\"active\"|\"inactive\") à la racine du JSON.")
    p.add_argument("--secrets", default=None,
                   help="Chemin absolu vers un fichier JSON de credentials (v1.10). "
                        "Court-circuite la résolution par hostname pour tout le run. "
                        "Le répertoire parent doit être un point de montage actif (T1).")
    p.add_argument("--ignorer-waf", dest="ignorer_waf", action="store_true",
                   help="Un blocage WAF détecté dégrade niveau_confiance mais ne force plus "
                        "pret_a_agir à false à lui seul (v1.17.2). À utiliser quand un "
                        "faux-positif résiduel de _detecter_waf bloque l'agent sur une page "
                        "saine. Opt-in : comportement par défaut (blocage) inchangé sans ce flag.")
    p.add_argument("--auth-indicator-negative", dest="auth_indicator_negative", default=None,
                   help="Sélecteur CSS dont la présence indique l'ABSENCE d'authentification "
                        "(v1.14.0). À utiliser avec --auth-indicator pour les interfaces à "
                        "sélecteur positif ambigu (ex. menu persistant sur la page de login).")
    p.add_argument("--stealth", action="store_true",
                   help="Active le mode furtif via playwright-stealth (v1.15.0). "
                        "Supprime navigator.webdriver et normalise les attributs techniques. "
                        "Ne change pas l'IP ni l'opérateur — restauration d'équité de traitement.")
    p.add_argument("--ignore-tls-errors", dest="ignore_tls_errors", action="store_true",
                   help="Accepte les certificats TLS invalides (LAN dev/Step-CA uniquement). "
                        "Ajoute tls_errors_ignored:true dans la boussole. (v1.15.1)")
    p.add_argument("--http-credentials", dest="http_credentials", action="store_true",
                   help="Résout http_username/http_password depuis le répertoire chiffré (clés fixes, "
                        "précédent ntfy_topic) et les injecte au contexte navigateur pour "
                        "répondre à un challenge HTTP Basic Auth (v1.21.0). Identifiants "
                        "scopés à l'origine de la cible (jamais envoyés à un tiers chargé "
                        "dans la même page). N'active jamais le contournement d'un vrai "
                        "blocage — seule l'authentification réseau standard.")
    p.add_argument("--no-evaluer", dest="no_evaluer", action="store_true",
                   help="Désactive l'action 'evaluer' — recommandé en production sur cibles "
                        "avec formulaires sensibles. (v1.15.1)")
    p.add_argument("--no-filtre-evaluer", dest="no_filtre_evaluer", action="store_true",
                   help="Désactive la neutralisation stdout des valeurs 'evaluer', URLs et "
                        "messages d'erreur (LOT 1, CHANTIER_SANITISATION.md) — run de debug "
                        "explicite uniquement. Actif (filtre ON) par défaut. Pose "
                        "boussole.filtre_evaluer_actif: false dans la sortie quand désactivé.")
    p.add_argument("--version", action="store_true",
                   help="Affiche la version installée et quitte immédiatement, sans Playwright (v1.18.0).")
    p.add_argument("--guide-version", dest="guide_version", default=None,
                   help="Jeton de lecture de docs/GUIDE_LLM.md — requis sauf marqueur local valide "
                        "(v1.18.0). Valeur : <!-- notice-version: X.Y --> en tête de ce fichier.")
    p.add_argument("--source-scenario", dest="source_scenario", default=None,
                   help="Nom de fichier du scénario (sans chemin), transmis par rpa.py (v1.18.0). "
                        "Plomberie interne pour mode_conseille — pas un paramètre destiné à un "
                        "appel shot.py direct.")
    p.add_argument("--chainage", dest="chainage", default=None,
                   help="Arbre de chaînage (JSON), transmis par rpa.py quand le scénario utilise "
                        "declencher_scenario (v1.19.0). Plomberie interne pour la traçabilité du "
                        "journal — pas un paramètre destiné à un appel shot.py direct.")
    return p.parse_args()


def charger_actions(source):
    if not source:
        return []
    s = source.strip()
    if s.startswith("[") or s.startswith("{"):
        data = json.loads(s)
    else:
        with open(source, encoding="utf-8") as f:
            data = json.load(f)
    # Auto-détecte le format scénario {nom, url, actions:[…]} vs tableau direct
    if isinstance(data, dict) and "actions" in data:
        actions = data["actions"]
    else:
        actions = data
    _valider_actions_secrets(actions)
    # G-29 (CHANTIER_SANITISATION.md, LOT 5) : rpa.py valide tout scénario
    # chargé contre scenarios/schema.json avant Playwright ; shot.py invoqué
    # directement (--actions, hors rpa.py) ne validait rien. "url" n'est pas
    # toujours présent dans le fichier chargé par shot.py (il vient souvent
    # de --url CLI, séparément) — un placeholder suffit : jsonschema ne
    # vérifie pas le format "uri" sans FormatChecker explicite (même
    # comportement que rpa.py, qui ne le fournit pas non plus) ; seule la
    # structure de 'actions' importe ici.
    from lib.validation_scenario import valider_schema_scenario
    valider_schema_scenario({"url": "https://placeholder.invalid/", "actions": actions})
    return actions


def _resoudre_frame_locator(page, a, type_action):
    """Résout 'iframe_selecteur' (frame unique) ou 'iframe_chemin' (descente
    imbriquée, v1.18.0) en un objet FrameLocator Playwright. Exactement un
    des deux requis — même discipline que 'defiler' (px xor selecteur).
    Le schéma (scenarios/schema.json) impose déjà cette contrainte quand
    rpa.py valide le scénario ; ce contrôle défensif couvre aussi les appels
    shot.py directs (--actions) qui ne passent pas par le validateur JSON
    Schema de rpa.py.
    """
    iframe_sel = a.get("iframe_selecteur")
    iframe_chemin = a.get("iframe_chemin")
    if iframe_sel and iframe_chemin:
        raise ValueError(
            f"{type_action} : 'iframe_selecteur' et 'iframe_chemin' sont mutuellement exclusifs"
        )
    if iframe_chemin is not None:
        if not isinstance(iframe_chemin, list) or not iframe_chemin:
            raise ValueError(
                f"{type_action} : 'iframe_chemin' doit être un tableau non vide de sélecteurs CSS"
            )
        locator = page.frame_locator(iframe_chemin[0])
        for niveau in iframe_chemin[1:]:
            locator = locator.frame_locator(niveau)
        return locator
    if not iframe_sel:
        raise ValueError(f"{type_action} requiert 'iframe_selecteur' ou 'iframe_chemin'")
    return page.frame_locator(iframe_sel)


def _resoudre_valeur_secrets(a, valeur, page, secrets_chemin, type_action, valeurs_resolues=None):
    """Résout 'depuis_secrets'/'depuis_secrets_totp' en credential réel lu
    depuis le répertoire chiffré. Factorisé depuis remplir/remplir_iframe
    (chantier qualité 05/08/2026) — même bloc de résolution
    dupliqué trois fois à l'identique, même catégorie de défaut que C-01
    (dwEstSensible, corrigé en session 76) : trois copies d'un code de
    résolution de credentials sont trois endroits à corriger en cas de bug.

    `valeurs_resolues` (audit 05/08/2026, D-01, correctif de fond) : si
    fourni, chaque valeur réellement résolue y est ajoutée — point de
    passage unique qui alimente la redaction de la sortie JSON finale,
    quel que soit le canal par lequel une valeur injectée ressortirait
    (a11y_tree aujourd'hui, un canal encore inconnu demain).
    """
    if valeur == "depuis_secrets":
        cle = a.get("secret_cle")
        if not cle:
            raise ValueError(f"{type_action} depuis_secrets : champ 'secret_cle' requis")
        if secrets_chemin:
            from lib.repertoire_chiffre import lire_credential_fichier
            resultat = lire_credential_fichier(secrets_chemin, cle, page.url)
        else:
            from lib.repertoire_chiffre import lire_credential, domaine_depuis_url
            resultat = lire_credential(domaine_depuis_url(page.url), cle)
        if valeurs_resolues is not None and resultat:
            valeurs_resolues.add(resultat)
        return resultat
    if valeur == "depuis_secrets_totp":
        if secrets_chemin:
            from lib.repertoire_chiffre import lire_totp_fichier
            resultat = lire_totp_fichier(secrets_chemin, page.url)
        else:
            from lib.repertoire_chiffre import lire_totp, domaine_depuis_url
            resultat = lire_totp(domaine_depuis_url(page.url))
        if valeurs_resolues is not None and resultat:
            valeurs_resolues.add(resultat)
        return resultat
    return valeur


# Audit 06/08/2026 (F-08) : compteur d'occurrences rédigées par
# _rediger_valeurs_secrets, vidé en tête de main(). Sur une liste de comptes, l'identifiant
# masqué redevient identifiable *parce qu'il est le seul masqué* — la
# décision retenue n'est pas de revenir sur le seuil de rédaction (un faux
# positif reste préférable à une fuite), mais de signaler qu'une vue trouée
# est en cours de lecture plutôt que de laisser le lecteur le découvrir par
# élimination.
_CHAMPS_REDIGES = [0]


def _rediger_valeurs_secrets(obj, valeurs):
    """Parcourt récursivement obj (dict/list/str) et remplace, dans toute
    chaîne, chaque occurrence exacte d'une valeur de `valeurs` par un
    marqueur neutre.

    Audit 05/08/2026 (D-01, correctif de fond) : point de passage unique
    appliqué juste avant json.dumps(result) — invariant plutôt que
    protection par canal (a11y_tree aujourd'hui, un canal encore inconnu
    demain). Aucun seuil de longueur (décision Ronan, 05/08/2026) :
    correspondance exacte systématique, un faux positif de redaction étant
    strictement préférable à une fuite.
    """
    if not valeurs:
        return obj
    if isinstance(obj, str):
        for v in valeurs:
            if v and v in obj:
                _CHAMPS_REDIGES[0] += obj.count(v)
                obj = obj.replace(v, "<secret_redige>")
        return obj
    if isinstance(obj, dict):
        return {k: _rediger_valeurs_secrets(v, valeurs) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rediger_valeurs_secrets(v, valeurs) for v in obj]
    return obj


def executer_actions(page, actions, timeout,
                     modeles_appeles=None, secrets_chemin=None,
                     min_action_delay_ms=0, max_pages_par_run=0, max_actions_par_run=0,
                     t_debut=None, no_evaluer=False, operation_id=None, progress=None,
                     valeurs_secrets_resolues=None):
    from playwright.sync_api import Error as PWError

    # Audit 05/08/2026 (D-01, correctif de fond) : valeurs réellement résolues
    # par _resoudre_valeur_secrets durant ce run — l'appelant fournit
    # l'ensemble (créé avant l'appel) pour que les valeurs résolues restent
    # accessibles même si une exception interrompt executer_actions avant son
    # retour normal ; rédigées de la sortie JSON finale quel que soit le
    # canal où elles réapparaîtraient.
    if valeurs_secrets_resolues is None:
        valeurs_secrets_resolues = set()
    evaluations = []
    extraction_texte = None
    latences_actions = []
    if modeles_appeles is None:
        modeles_appeles = []
    pages_visitees = 0
    actions_executees = 0
    plafond_atteint = None
    waf_bloquants = 0
    # v1.22.0, Axe B — dernier code HTTP capturé sur une action naviguer,
    # remonté en boussole à côté de session_derive. None si aucune action
    # naviguer n'a eu lieu (le code de la navigation initiale, capturé par
    # l'appelant, fait alors foi).
    dernier_code_http = None
    # v1.22.0, Axe A — reflète une escalade JS réellement survenue, jamais le
    # seul flag posé sur l'action (même discipline que stealth_actif corrigé
    # en v1.16.0/FR-79 : ne jamais confondre l'intention et l'application réelle).
    repli_js_utilise = False
    if t_debut is None:
        t_debut = time.time()

    # Indice d'agressivité (v1.16.0, item E) — réutilise la taxonomie
    # ACTIONS_ECRITURE déjà arbitrée pour est_mutatif (lib/journal.py),
    # source unique, pas de seconde liste à maintenir en synchronisation.
    from lib.journal import ACTIONS_ECRITURE
    actions_ecriture = 0

    for idx, a in enumerate(actions):
        t = a.get("type")
        _t0_latence = time.time()

        actions_executees += 1
        if max_actions_par_run > 0 and actions_executees > max_actions_par_run:
            plafond_atteint = "max_actions_par_run"
            actions_executees -= 1
            break
        if t in ACTIONS_ECRITURE:
            actions_ecriture += 1

        if t == "naviguer":
            pages_visitees += 1
            if max_pages_par_run > 0 and pages_visitees > max_pages_par_run:
                plafond_atteint = "max_pages_par_run"
                pages_visitees -= 1
                actions_executees -= 1
                break
            _valider_schema_url(a.get("url", ""))
            rep_nav = page.goto(a["url"], timeout=timeout)
            try:
                statut_nav = rep_nav.status if rep_nav else None
                dernier_code_http = statut_nav
                if _detecter_waf(statut_nav, page.title(), page.content()[:5000]):
                    waf_bloquants += 1
            except Exception:
                pass  # détection best-effort — ne doit jamais casser la navigation

        elif t == "attendre":
            if "selecteur" not in a:
                raise ValueError(
                    "attendre requiert un champ 'selecteur' (CSS). "
                    "Pour un délai fixe : {\"type\":\"pause\",\"ms\":N}"
                )
            page.wait_for_selector(a["selecteur"], timeout=timeout)

        elif t == "attendre_navigation":
            page.wait_for_load_state("networkidle", timeout=timeout)

        elif t == "remplir":
            valeur = a.get("valeur", "")
            valeur = _resoudre_valeur_secrets(a, valeur, page, secrets_chemin, "remplir", valeurs_secrets_resolues)
            page.locator(a["selecteur"]).fill(valeur, timeout=timeout)

        elif t == "cliquer":
            if a.get("repli_js"):
                # v1.22.0, Axe A — escalade à deux niveaux, distincte de
                # force: true (force-click natif Playwright, déjà insuffisant
                # seul — FR-81) : force-click d'abord, clic JS ensuite
                # seulement si le premier échoue par inaccessibilité/obstruction.
                # --no-evaluer est garanti inactif ici (rejet précoce plus haut).
                # PWError (classe mère) est capté, pas seulement PWTimeoutError :
                # vérifié empiriquement (fixture dialog_ferme.html) qu'un clic
                # avec force=True sur un élément sans boîte de mise en page
                # (<dialog> non ouvert) lève "Element is not visible", une
                # Error simple, jamais un TimeoutError — un except trop étroit
                # aurait laissé passer exactement le cas réel FN14.
                try:
                    page.locator(a["selecteur"]).click(
                        timeout=timeout,
                        force=bool(a.get("force", False)),
                    )
                except PWError:
                    page.eval_on_selector(a["selecteur"], "el => el.click()")
                    repli_js_utilise = True
            else:
                page.locator(a["selecteur"]).click(
                    timeout=timeout,
                    force=bool(a.get("force", False)),
                )

        elif t == "pause":
            duree_s = a.get("ms", 500) / 1000.0
            time.sleep(duree_s)

        elif t == "evaluer":
            if no_evaluer:
                raise ValueError("evaluer bloqué — --no-evaluer est actif sur ce run")
            script = a.get("script")
            if not script:
                raise ValueError("evaluer requiert un champ 'script' (chaîne JS pour page.evaluate)")
            valeur = page.evaluate(script)
            entree = {"index": idx, "script": script}
            try:
                json.dumps(valeur)
                entree["valeur"] = valeur
            except (TypeError, ValueError):
                entree["valeur"] = str(valeur)
                entree["serialisation"] = "str"
            evaluations.append(entree)

        elif t == "cliquer_iframe":
            # v1.17.0, item 4 — primitive scopée pour iframes cross-origin.
            # page.frame_locator() franchit la frontière Same-Origin Policy via
            # CDP (contrairement à une injection JS page-level, qui ne peut pas
            # atteindre le contenu d'un iframe cross-origin). Pas de numérotation
            # SoM à l'intérieur du frame — ciblage par sélecteur CSS explicite
            # uniquement (limite documentée, GUIDE_LLM_INTERACTIONS.md).
            if "selecteur" not in a:
                raise ValueError("cliquer_iframe requiert un champ 'selecteur' (cible dans le frame)")
            frame_locator = _resoudre_frame_locator(page, a, "cliquer_iframe")
            frame_locator.locator(a["selecteur"]).click(
                timeout=timeout, force=bool(a.get("force", False)),
            )

        elif t == "remplir_iframe":
            if "selecteur" not in a:
                raise ValueError("remplir_iframe requiert un champ 'selecteur' (cible dans le frame)")
            frame_locator = _resoudre_frame_locator(page, a, "remplir_iframe")
            valeur = a.get("valeur", "")
            valeur = _resoudre_valeur_secrets(a, valeur, page, secrets_chemin, "remplir_iframe", valeurs_secrets_resolues)
            frame_locator.locator(a["selecteur"]).fill(valeur, timeout=timeout)

        elif t == "defiler":
            px = a.get("px")
            sel = a.get("selecteur")
            if sel:
                page.evaluate(
                    "(s) => document.querySelector(s)?.scrollIntoView({block:'center',inline:'nearest'})",
                    sel,
                )
            elif px is not None:
                page.evaluate("(n) => window.scrollBy(0, n)", int(px))
            else:
                raise ValueError("defiler requiert 'px' (pixels relatifs) ou 'selecteur' (CSS scrollIntoView)")

        elif t == "attendre_mfa_ntfy":
            # Retrait de la couche visuelle (08/08/2026) : ciblage par
            # sélecteur CSS explicite, plus par id Set-of-Mark — même
            # discipline que cliquer_iframe/remplir_iframe.
            selecteur_mfa = a.get("selecteur")
            if not selecteur_mfa:
                raise ValueError("attendre_mfa_ntfy requiert un champ 'selecteur' (CSS)")
            timeout_mfa = int(a.get("timeout", 120))
            from lib import ntfy as ntfy_lib
            if secrets_chemin:
                from lib.repertoire_chiffre import lire_credential_fichier
                topic = lire_credential_fichier(secrets_chemin, "ntfy_topic", page.url)
            else:
                from lib.repertoire_chiffre import lire_credential, domaine_depuis_url
                topic = lire_credential(domaine_depuis_url(page.url), "ntfy_topic")
            ntfy_lib.publier_attente(topic, page.url)
            code = ntfy_lib.attendre_code(topic, timeout_s=timeout_mfa)
            # G-27 (CHANTIER_SANITISATION.md, LOT 5) : le code TOTP tapé au
            # clavier n'était jamais ajouté à valeurs_secrets_resolues — s'il
            # réapparaît ailleurs dans le résultat (evaluer, message d'erreur),
            # _rediger_valeurs_secrets ne le rédigeait pas.
            valeurs_secrets_resolues.add(str(code))
            page.locator(selecteur_mfa).click(timeout=timeout)
            page.keyboard.press("Control+a")
            page.keyboard.type(str(code))

        elif t == "attendre_url":
            motif = a.get("motif", "")
            if not motif:
                raise ValueError(
                    "attendre_url requiert un champ 'motif' (sous-chaîne de l'URL attendue). "
                    "Exemple : {\"type\":\"attendre_url\",\"motif\":\"/dashboard\"}. "
                    "Attention : correspondance partielle — si l'URL courante contient déjà "
                    "le motif, l'action retourne immédiatement. Utiliser 'attendre_changement':true "
                    "pour attendre une navigation effective avant de tester le motif (FR-55)."
                )
            # FR-55 : si attendre_changement=true, attendre que l'URL quitte l'URL courante
            if a.get("attendre_changement", False):
                url_avant = page.url
                page.wait_for_function(
                    "url => window.location.href !== url",
                    arg=url_avant,
                    timeout=timeout,
                )
            page.wait_for_url(f"**{motif}**", timeout=timeout)

        elif t == "attendre_selecteur_present":
            if "selecteur" not in a:
                raise ValueError(
                    "attendre_selecteur_present requiert un champ 'selecteur' (CSS). "
                    "Attend que l'élément devienne visible (state=visible)."
                )
            page.wait_for_selector(a["selecteur"], state="visible", timeout=timeout)

        elif t == "attendre_absence":
            if "selecteur" not in a:
                raise ValueError(
                    "attendre_absence requiert un champ 'selecteur' (CSS). "
                    "Attend que l'élément disparaisse du DOM (state=detached)."
                )
            delai_initial = a.get("delai_initial_ms", 0)
            if delai_initial > 0:
                time.sleep(delai_initial / 1000.0)
            page.wait_for_selector(a["selecteur"], state="detached", timeout=timeout)

        elif t == "attendre_reseau_calme":
            # timeout_ms = durée max avant abandon (distinct des 500ms de silence interne networkidle)
            timeout_ms_local = int(a.get("timeout_ms", timeout))
            page.wait_for_load_state("networkidle", timeout=timeout_ms_local)

        elif t == "nettoyer_overlay":
            selecteur = a.get("selecteur")
            if not selecteur:
                raise ValueError(
                    "nettoyer_overlay requiert un champ 'selecteur' (CSS). "
                    "Pas d'auto-détection — déclarer explicitement les éléments à masquer. "
                    "Exemple : {\"type\":\"nettoyer_overlay\",\"selecteur\":\".cookie-banner\"}"
                )
            page.evaluate(
                """(sel) => {
                    document.querySelectorAll(sel).forEach(el => {
                        el.style.setProperty('visibility', 'hidden', 'important');
                    });
                }""",
                selecteur,
            )

        elif t == "extraire_texte":
            # Primitive manquante identifiée dans FONDATION_DINOER.md §6 et
            # consommée par campagne.py::_escalader_lourd() (palier lourd du
            # pipeline de recherche profonde, DINOER_RESEARCH.md §3.3) : une
            # cible marquée `insuffisante_legere` par le palier léger (coquille
            # SPA probable) est revisitée ici, après exécution JS complète —
            # contrairement au palier léger (lib/fetch_leger.py), qui lit le
            # HTML brut avant tout rendu.
            #
            # Même doctrine de nettoyage que le palier léger (mêmes balises de
            # bruit retirées), appliquée au DOM déjà rendu par Playwright
            # (page.content()) plutôt qu'à une réponse HTTP brute — c'est la
            # seule différence fonctionnelle entre les deux paliers.
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page.content(), "html.parser")
            titre_extrait = soup.title.get_text(strip=True) if soup.title else None
            for tag in soup(_BALISES_BRUIT_TEXTE):
                tag.decompose()
            texte_extrait = soup.get_text(separator="\n", strip=True)
            extraction_texte = {
                "titre": titre_extrait,
                "texte": texte_extrait or None,
                "url": page.url,
                "date_capture": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }

        else:
            raise ValueError(f"Type d'action inconnu : {t!r}")

        # Profilage latence par action (v1.20.0) — même point d'atteinte que le
        # marqueur de progression ci-dessous : uniquement si l'action s'est
        # terminée sans exception et sans plafond de navigation atteint avant
        # dispatch. Coût de mesure nul (un time.time() déjà en cours).
        latences_actions.append({
            "index": idx,
            "type": t,
            "latence_ms": int((time.time() - _t0_latence) * 1000),
        })

        # Point de progression (v1.17.0, item 2) — atteint uniquement si l'action
        # ci-dessus s'est terminée sans exception. `progress` (dict mutable
        # fourni par l'appelant) reste donc figé sur le dernier état réussi si
        # une action suivante lève — support des checkpoints rpa.py.
        if progress is not None:
            progress["actions_executees"] = actions_executees
            progress["pages_visitees"] = pages_visitees

        if min_action_delay_ms > 0:
            time.sleep(min_action_delay_ms / 1000.0)

    respect = {
        "pages_visitees": pages_visitees,
        "actions_executees": actions_executees,
        "duree_totale_ms": int((time.time() - t_debut) * 1000),
    }
    if plafond_atteint:
        respect["plafond_atteint"] = plafond_atteint
    if waf_bloquants:
        respect["waf_bloquants"] = waf_bloquants
    if actions_executees > 0:
        respect["indice_agressivite"] = round(actions_ecriture / actions_executees, 3)
    return (evaluations, modeles_appeles, respect,
            latences_actions, dernier_code_http, repli_js_utilise, extraction_texte)


# Audit 05/08/2026 (D-10) : constaté en production — dinoer.conf
# absent, les plafonds valaient 0 (donc inactifs, max_* > 0 conditionne tout
# contrôle) et les runs s'exécutaient sans aucune limite ni délai minimal.
# La protection ne doit pas dépendre de la présence d'un fichier optionnel —
# mêmes valeurs que celles déjà proposées par dinoer-sample.conf.
_NAVIGATION_DEFAUT = {
    "min_action_delay_ms": 800,
    "max_pages_par_run": 10,
    "max_actions_par_run": 30,
}


def _conf_navigation():
    """Lit les paramètres [navigation] depuis le fichier résolu par
    lib.repertoire_chiffre._lire_conf() (DINOER_CONF, ou /opt/dinoer/dinoer.conf
    par défaut). Valeurs par défaut non nulles si absentes ou si dinoer.conf
    lui-même est absent (D-10)."""
    try:
        from lib.repertoire_chiffre import _lire_conf
        conf = _lire_conf()
        nav = conf.get("navigation", {})
        return {
            "min_action_delay_ms": int(nav.get("min_action_delay_ms", _NAVIGATION_DEFAUT["min_action_delay_ms"])),
            "max_pages_par_run": int(nav.get("max_pages_par_run", _NAVIGATION_DEFAUT["max_pages_par_run"])),
            "max_actions_par_run": int(nav.get("max_actions_par_run", _NAVIGATION_DEFAUT["max_actions_par_run"])),
        }
    except Exception:
        return dict(_NAVIGATION_DEFAUT)


def main():
    args = parse_args()
    _CHAMPS_REDIGES[0] = 0  # F-08 — état propre à chaque run

    # LOT 1e (CHANTIER_SANITISATION.md §1e) : --no-filtre-evaluer désactive la
    # neutralisation stdout du LOT 1 pour un run de debug explicite. Défaut :
    # filtre actif. Wrappers utilisés à la place d'un appel direct partout où
    # le LOT 1 a inséré une neutralisation, pour que le seul point de bascule
    # soit ce flag.
    _filtre_evaluer_actif = not args.no_filtre_evaluer

    def _filtrer_evaluer(valeur):
        return _neutraliser_valeur_evaluer(valeur) if _filtre_evaluer_actif else valeur

    def _filtrer_url(url):
        return _sanitiser_url_journal(url) if _filtre_evaluer_actif else url

    def _filtrer_url_query(url):
        return rediger_query_params_sensibles(url) if _filtre_evaluer_actif else url

    def _filtrer_chaine(texte):
        return sanitiser_urls_dans_chaine(texte) if _filtre_evaluer_actif else texte

    # ── --version (v1.18.0) : zéro Playwright, zéro autre argument requis ─────
    if args.version:
        print(json.dumps({"outil": "shot.py", "version": __version__}))
        sys.exit(0)

    import importlib.util
    if importlib.util.find_spec("playwright") is None:
        sys.stderr.write(
            "Dinoer : module 'playwright' introuvable dans cet interpréteur.\n"
            "  Exécutez via le venv : /opt/dinoer/venv/bin/python depuis /opt/dinoer\n"
        )
        sys.exit(3)

    # ── Verrou de lecture obligatoire (v1.18.0) ────────────────────────────────
    # Avant tout autre traitement — y compris la validation --url. Exception
    # consciente à la doctrine d'additivité de Dinoer (seule du projet) :
    # la documentation seule a échoué à se faire lire spontanément (retour
    # terrain répété, cf. docs/RADAR_MODELES.md).
    from lib.preflight_guide import guide_valide, erreur_guide_non_lu
    if not guide_valide(args.guide_version):
        print(json.dumps(erreur_guide_non_lu(__version__)), file=sys.stderr)
        sys.exit(1)

    # Interdire les core dumps pour ce processus : si Playwright crashe
    # pendant qu'un credential est en mémoire, le noyau ne peut pas écrire
    # un dump contenant le secret (spec 36_ §2.5).
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ValueError, resource.error):
        pass  # best-effort — certains environnements refusent, ce n'est pas bloquant

    # ── Identité de run unifiée (v1.16.0, item B) ─────────────────────────────
    # Générée avant toute autre chose : disponible dans la boussole de TOUTE
    # sortie JSON, y compris les échecs de validation précoces.
    operation_id = uuid.uuid4().hex[:12]


    conf_nav = _conf_navigation()
    t0 = time.time()
    horodatage = datetime.now(timezone.utc).astimezone().isoformat()

    from lib.profil_operateur import charger_profil
    profil = charger_profil()
    modeles_appeles = []

    # ── Validation ────────────────────────────────────────────────────────────
    if not args.url and not args.reprendre_session:
        print(json.dumps({
            "succes": False, "erreur": "argument_manquant",
            "message": "--url ou --reprendre-session est requis",
            "horodatage": horodatage,
            "boussole": _boussole(operation_id),
        }))
        sys.exit(1)

    # ── Chargement des actions ────────────────────────────────────────────────
    if args.reprendre_session:
        try:
            if args.action:
                parsed = json.loads(args.action)
                # Accepte un objet unique {"type":...} OU un tableau [{...},{...}]
                actions = parsed if isinstance(parsed, list) else [parsed]
                _valider_actions_secrets(actions)
            elif args.actions:
                # FR-54 : --actions (fichier) désormais supporté en Mode B
                actions = charger_actions(args.actions)
            else:
                actions = []
        except (json.JSONDecodeError, Exception) as e:
            print(json.dumps({
                "succes": False, "erreur": "action_invalide",
                "message": _filtrer_chaine(str(e)), "horodatage": horodatage,
                "boussole": _boussole(operation_id),
            }))
            sys.exit(1)
    else:
        try:
            actions = charger_actions(args.actions)
        except Exception as e:
            print(json.dumps({
                "succes": False, "erreur": "actions_invalides",
                "message": _filtrer_chaine(str(e)), "horodatage": horodatage,
                "boussole": _boussole(operation_id),
            }))
            sys.exit(1)

    # v1.19.0 — arbre de chaînage transmis par rpa.py (--chainage), plomberie
    # interne pour le journal. Best-effort : un JSON malformé ne bloque jamais
    # le run, exactement comme mode_conseille.
    try:
        chainage = json.loads(args.chainage) if args.chainage else None
    except (json.JSONDecodeError, TypeError):
        chainage = None

    # ── Validation schéma URL principale ────────────────────────────────────
    try:
        _valider_schema_url(args.url)
    except ValueError as e:
        print(json.dumps({
            "succes": False, "erreur": "url_scheme_interdit",
            "message": _filtrer_chaine(str(e)), "horodatage": horodatage, "boussole": _boussole(operation_id),
        }))
        sys.exit(2)

    # ── Validation --auth-indicator-negative (v1.15.2, item 2 / GL1) ─────────
    # Sans --auth-indicator, le bloc de vérification d'authentification est
    # entièrement sauté (voir main() plus bas) : --auth-indicator-negative
    # serait silencieusement ignoré. Rejet précoce, avant tout lancement de
    # Chromium — design orienté agent, zéro navigateur pour rien.
    if args.auth_indicator_negative and not args.auth_indicator:
        print(json.dumps({
            "succes": False, "erreur": "arguments_incompatibles",
            "message": "--auth-indicator-negative requiert --auth-indicator "
                       "(sans lui, l'indicateur négatif est ignoré silencieusement)",
            "horodatage": horodatage, "boussole": _boussole(operation_id),
        }))
        sys.exit(2)

    # ── Validation repli_js + --no-evaluer (v1.22.0, Axe A) ──────────────────
    # repli_js exécute du JS (element.click()) — --no-evaluer l'interdit sur ce
    # run. Rejet précoce, avant tout lancement de Chromium, même discipline que
    # --auth-indicator-negative ci-dessus : un abandon silencieux laisserait
    # l'agent face à l'échec du clic standard sans comprendre pourquoi son
    # repli_js n'a rien fait.
    if args.no_evaluer and any(
        a.get("type") == "cliquer" and a.get("repli_js") for a in actions
    ):
        print(json.dumps({
            "succes": False, "erreur": "arguments_incompatibles",
            "message": "repli_js requiert que --no-evaluer soit inactif "
                       "(repli_js exécute du JS, --no-evaluer l'interdit sur ce run)",
            "horodatage": horodatage, "boussole": _boussole(operation_id),
        }))
        sys.exit(2)

    erreurs_js = []
    erreurs_console = []
    # v1.17.0, item 2 — rempli par executer_actions() au fil des actions
    # réussies ; lu dans le except si une action échoue en cours de route
    # (support des checkpoints rpa.py).
    progress = {}
    # Audit 05/08/2026 (D-01, correctif de fond) : créé ici, avant le bloc
    # try qui englobe executer_actions, pour rester lisible depuis le
    # handler d'erreur si une exception interrompt le run après qu'un
    # secret a déjà été résolu.
    valeurs_secrets_resolues = set()
    http_status = None
    # v1.22.0, Axe D — condition d'arrêt réellement appliquée à la navigation
    # initiale, posée seulement si elle diffère du défaut et que la navigation
    # a abouti. Initialisée ici pour rester lisible depuis le handler d'erreur.
    wait_until_applique = None
    url_finale = args.url or ""
    url_cible = url_finale  # pour le handler d'erreur

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)

            # ── Contexte navigateur ───────────────────────────────────────────
            derive_session = None
            session = None
            if args.reprendre_session:
                session = _charger_session(args.reprendre_session)
                viewport = session.get("viewport", {"width": args.largeur, "height": args.hauteur})
                url_cible = args.url if args.url else session["url"]
                if not args.url:
                    # Audit 06/08/2026 (F-15) : args.url est déjà validé plus
                    # haut (schéma + userinfo), mais quand --reprendre-session
                    # est utilisé sans --url, url_cible vient de session["url"]
                    # — seul chemin de navigation qui échappait au contrôle.
                    try:
                        _valider_schema_url(url_cible)
                    except ValueError as e:
                        print(json.dumps({
                            "succes": False, "erreur": "url_scheme_interdit",
                            "message": _filtrer_chaine(str(e)), "horodatage": horodatage,
                            "boussole": _boussole(operation_id),
                        }))
                        sys.exit(2)
            else:
                viewport = {"width": args.largeur, "height": args.hauteur}
                url_cible = args.url

            # ── Identifiants HTTP Basic Auth (v1.21.0) ─────────────────────────
            # Résolus avant new_context() — le challenge Basic Auth se joue au
            # niveau du protocole, avant tout rendu de page. 'origin' est
            # obligatoire : sans lui, Chromium peut renvoyer ces identifiants à
            # toute origine tierce chargée dans le même contexte (CDN, tracker,
            # redirection) — fuite réelle, pas théorique (Playwright 1.61.0
            # vérifié supporter {username, password, origin, send}).
            # 'send: "unauthorized"' : envoi uniquement après un vrai 401, jamais
            # préventif. Repli documenté si un reverse-proxy n'émet pas de 401
            # propre : 'send: "always"', qui reste scopé par 'origin' — jamais un
            # header Authorization fait main, qui contournerait ce scoping.
            new_context_kwargs = {}
            if args.http_credentials:
                from urllib.parse import urlparse
                secrets_chemin = getattr(args, "secrets", None)
                # Clés dédiées http_username/http_password en priorité — nécessaires
                # si la même cible a aussi un login applicatif distinct (Basic Auth
                # réseau devant un formulaire web, ex. Caddy devant Grafana). Repli
                # sur username/password (v1.21.0, trouvé en test réel contre une
                # cible Basic Auth réelle) : la plupart des fichiers d'identifiants
                # existants n'ont qu'une paire de clés, pas de raison de forcer un
                # renommage pour le cas le plus courant.
                if secrets_chemin:
                    from lib.repertoire_chiffre import lire_credential_fichier
                    # Audit 05/08/2026 (C-03), site retrouvé lors de la revue de
                    # couverture du 05/08/2026 : url_cible plutôt que page.url —
                    # ce bloc s'exécute avant new_context(), page n'existe pas
                    # encore. url_cible est la même source que 'origin' ci-dessous.
                    try:
                        http_username = lire_credential_fichier(secrets_chemin, "http_username", url_cible)
                        http_password = lire_credential_fichier(secrets_chemin, "http_password", url_cible)
                    except KeyError:
                        http_username = lire_credential_fichier(secrets_chemin, "username", url_cible)
                        http_password = lire_credential_fichier(secrets_chemin, "password", url_cible)
                else:
                    from lib.repertoire_chiffre import lire_credential, domaine_depuis_url
                    _domaine = domaine_depuis_url(url_cible)
                    try:
                        http_username = lire_credential(_domaine, "http_username")
                        http_password = lire_credential(_domaine, "http_password")
                    except KeyError:
                        http_username = lire_credential(_domaine, "username")
                        http_password = lire_credential(_domaine, "password")
                _parsed = urlparse(url_cible)
                new_context_kwargs["http_credentials"] = {
                    "username": http_username,
                    "password": http_password,
                    "origin": f"{_parsed.scheme}://{_parsed.netloc}",
                    "send": "unauthorized",
                }

            if args.reprendre_session:
                ctx = browser.new_context(
                    storage_state=session["storage_state"],
                    viewport=viewport,
                    ignore_https_errors=args.ignore_tls_errors,
                    **new_context_kwargs,
                )
            else:
                ctx = browser.new_context(
                    viewport=viewport,
                    ignore_https_errors=args.ignore_tls_errors,
                    **new_context_kwargs,
                )

            page = ctx.new_page()
            # Correctif compatibilité playwright-stealth 2.x (v1.16.0) : l'API
            # 1.x (fonction stealth_sync) a été retirée au profit d'une classe
            # Stealth().apply_stealth_sync(page). L'ancien appel échouait à
            # l'import et --stealth se dégradait silencieusement en no-op —
            # navigator.webdriver restait exposé malgré le flag actif, et la
            # boussole affichait quand même stealth_actif: true (voir plus bas).
            stealth_applique = False
            if args.stealth:
                try:
                    from playwright_stealth import Stealth
                    Stealth().apply_stealth_sync(page)
                    stealth_applique = True
                except Exception as e:
                    sys.stderr.write(
                        f"playwright-stealth indisponible ou incompatible — "
                        f"--stealth ignoré ({type(e).__name__}: {e})\n"
                    )
            page.on("pageerror", lambda err: erreurs_js.append(str(err)))
            # v1.16.0, item D — messages de console de niveau erreur, distincts
            # des exceptions non interceptées (erreurs_js/pageerror). Complète
            # sans remplacer : un site peut avoir des erreurs console (requêtes
            # réseau échouées, avertissements applicatifs) sans lever d'exception JS.
            page.on("console", lambda msg: (
                erreurs_console.append(msg.text) if msg.type == "error" else None
            ))

            # ── Navigation ────────────────────────────────────────────────────
            # v1.22.0, Axe D — la condition d'arrêt est paramétrable, défaut
            # networkidle inchangé. Ne s'applique qu'ici : l'action `naviguer`
            # de executer_actions() garde le défaut Playwright ("load"), sans
            # override — asymétrie assumée, aucun second cas d'usage réel ne
            # justifie de l'étendre à ce stade.
            rep = page.goto(url_cible, timeout=args.timeout, wait_until=args.wait_until)
            if rep:
                http_status = rep.status
            url_finale = page.url
            # Signal boussole posé après coup, sur navigation réellement aboutie
            # par une condition différente du défaut — jamais sur le seul flag CLI
            # (précédent stealth_actif, corrigé en v1.16.0).
            if args.wait_until != "networkidle":
                wait_until_applique = args.wait_until

            # ── Détection WAF sur la navigation initiale (v1.16.0, item C) ────
            waf_initial = False
            try:
                waf_initial = _detecter_waf(http_status, page.title(), page.content()[:5000])
            except Exception:
                pass

            # ── Challenge HTTP Basic Auth non résolu (v1.21.0) ────────────────
            # Signal distinct du WAF — c'est une authentification réseau, pas un
            # blocage anti-bot. Pointe explicitement vers --http-credentials
            # plutôt que de laisser l'agent face à un 401 opaque.
            http_auth_requise = (http_status == 401)

            # ── Détection de dérive de session (lot 8.5) ──────────────────────
            # Comparaison sur l'URL effective après navigation (post-normalisation)
            # afin d'éviter les faux positifs liés au slash terminal ou aux
            # redirections HTTP transparentes.
            if args.reprendre_session and session is not None:
                derive_session = _detecter_derive_session(session, url_finale)

            if args.attendre_selecteur:
                page.wait_for_selector(args.attendre_selecteur, timeout=args.timeout)

            # ── Actions ───────────────────────────────────────────────────────
            # v1.17.0, item 2 — try/except localisé à ce seul appel : si une
            # action échoue en cours de route, ctx/page sont encore vivants ici
            # (avant la fermeture implicite par la sortie du bloc `with`) —
            # dernière occasion de sauvegarder la session pour un checkpoint.
            try:
                (evaluations, modeles_appeles, respect,
                 latences_actions, dernier_code_http_actions,
                 repli_js_utilise, extraction_texte) = executer_actions(
                    page, actions, args.timeout,
                    modeles_appeles=modeles_appeles,
                    secrets_chemin=getattr(args, "secrets", None),
                    min_action_delay_ms=conf_nav["min_action_delay_ms"],
                    max_pages_par_run=conf_nav["max_pages_par_run"],
                    max_actions_par_run=conf_nav["max_actions_par_run"],
                    t_debut=t0,
                    no_evaluer=args.no_evaluer,
                    operation_id=operation_id,
                    progress=progress,
                    valeurs_secrets_resolues=valeurs_secrets_resolues,
                )
            except Exception:
                if args.sauver_session:
                    try:
                        _sauver_session(ctx, page, args.sauver_session,
                                        {"width": args.largeur, "height": args.hauteur})
                    except Exception:
                        pass  # best-effort — ne jamais masquer l'erreur originale
                raise
            if waf_initial:
                respect["waf_bloquants"] = respect.get("waf_bloquants", 0) + 1
            url_finale = page.url  # mise à jour après actions

            # ── A11y ──────────────────────────────────────────────────────────
            a11y_tree, a11y_redaction_echouee = (
                _snapshot_a11y(page) if args.a11y else (None, False)
            )

            # ── Auth status ───────────────────────────────────────────────────
            auth_status = None
            if args.auth_indicator:
                try:
                    visible = page.locator(args.auth_indicator).is_visible()
                    if visible and args.auth_indicator_negative:
                        neg_visible = page.locator(args.auth_indicator_negative).is_visible()
                        visible = not neg_visible
                    auth_status = "active" if visible else "inactive"
                except Exception:
                    auth_status = "inactive"

            # Audit 05/08/2026 (D-05) : un indicateur d'authentification actif
            # annule une dérive de session résiduelle — les deux signaux ne
            # doivent jamais se contredire dans le même objet de sortie.
            if auth_status == "active" and derive_session:
                derive_session = None

            # ── Sauvegarde session ────────────────────────────────────────────
            session_file = None
            if args.sauver_session:
                _sauver_session(ctx, page, args.sauver_session,
                                {"width": args.largeur, "height": args.hauteur})
                session_file = args.sauver_session

            # ── Stats DOM structurelles ────────────────────────────────────────
            # Toujours calculées depuis le retrait de la couche visuelle
            # (08/08/2026) — seule vue structurelle de la page hors a11y_tree.
            dom_stats = None
            try:
                dom_stats = page.evaluate(_DOM_STATS_JS)
            except Exception:
                pass

            # ── Titre de page (boussole enrichie) ─────────────────────────────
            titre_page = ""
            try:
                titre_page = page.title()
            except Exception:
                pass

            browser.close()

        # LOT 1 (CHANTIER_SANITISATION.md §1b) : calculée une seule fois, à la
        # sortie de la session Playwright, réutilisée pour tous les champs
        # stdout qui exposent cette URL — le journal applique déjà ce filtre
        # depuis lib/journal.py, stdout ne le faisait pas (G-01 à G-08).
        url_finale_sanitisee = _filtrer_url(url_finale)

        result = {
            "succes": True,
            "http_status": http_status,
            "url_finale": url_finale_sanitisee,
            "erreurs_js": [_filtrer_evaluer(x) for x in erreurs_js],
            "erreurs_console": [_filtrer_evaluer(x) for x in erreurs_console],
            "duree_ms": int((time.time() - t0) * 1000),
            "horodatage": horodatage,
            "dinoer_meta": _construire_dinoer_meta(
                profil, horodatage, modeles_appeles, url_finale_sanitisee,
            ),
        }
        if dom_stats is not None:
            result["dom_stats"] = dom_stats
        if auth_status is not None:
            result["auth_status"] = auth_status
        if evaluations:
            result["evaluations"] = [
                {**e, "valeur": _filtrer_evaluer(e.get("valeur"))}
                for e in evaluations
            ]
        if extraction_texte is not None:
            result["extraction_texte"] = extraction_texte
        if a11y_tree is not None:
            result["a11y_tree"] = a11y_tree
        if session_file:
            result["session_file"] = session_file
        # Note derive_session (§1b) : url_sauvegardee/url_reprise gardent leur
        # query brute côté fichier de session (jamais touché ici) — le signal
        # de dérive (`?vue=login` remplaçant `?vue=domaine`) en dépend
        # (_detecter_derive_session, D-05/E-03). Seule la sortie stdout est
        # rédigée : rediger_query_params_sensibles rédige la valeur des
        # paramètres sensibles (token, code, state...) et conserve le nom du
        # paramètre et le signal fonctionnel — _sanitiser_url_journal, qui
        # supprime toute la query, casserait ce signal (variante FR-55).
        # Rédigé une seule fois : réutilisé aux deux points de sortie stdout
        # (result["derive_session"] et boussole.session_derive plus bas), pour
        # ne pas laisser fuir en clair sous une clé la valeur rédigée sous l'autre.
        derive_session_sanitisee = None
        if derive_session:
            derive_session_sanitisee = {
                **derive_session,
                "url_sauvegardee": _filtrer_url_query(derive_session["url_sauvegardee"]),
                "url_reprise": _filtrer_url_query(derive_session["url_reprise"]),
            }
            result["derive_session"] = derive_session_sanitisee
        result["boussole"] = _boussole(operation_id)
        if not _filtre_evaluer_actif:
            result["boussole"]["filtre_evaluer_actif"] = False
        result["boussole"]["url_courante"] = url_finale_sanitisee
        result["boussole"]["titre_page"] = titre_page
        # v1.22.0, Axe B — toujours présent (contrairement à session_derive,
        # conditionnel à --reprendre-session) : reflète la dernière navigation
        # du run (une action naviguer si le scénario en contient une, sinon la
        # navigation initiale). Sur un run multi-navigations, ne présume pas
        # laquelle explique une dérive éventuelle — voir GUIDE_LLM_SESSIONS.md.
        result["boussole"]["dernier_code_http"] = (
            dernier_code_http_actions if dernier_code_http_actions is not None else http_status
        )
        if stealth_applique:
            result["boussole"]["stealth_actif"] = True
        # v1.21.0 — jamais conditionné au seul flag CLI (précédent stealth_actif
        # corrigé en v1.16.0/FR-79) : le flag doit être actif ET la navigation
        # initiale ne doit pas s'être terminée en 401, preuve que les
        # identifiants ont réellement résolu le challenge.
        if args.http_credentials and not http_auth_requise:
            result["boussole"]["http_credentials_actif"] = True
        if http_auth_requise:
            result["boussole"]["http_auth_requise"] = True
        if args.ignore_tls_errors:
            result["boussole"]["tls_errors_ignored"] = True
        if args.ignorer_waf:
            result["boussole"]["waf_ignore_actif"] = True
        if repli_js_utilise:
            result["boussole"]["repli_js_utilise"] = True
        # v1.22.0, Axe D — porte la valeur employée, pas un booléen : un agent
        # qui relit une sortie doit savoir sous quelle condition la page a été
        # jugée prête. Absente quand la navigation a suivi le défaut.
        if wait_until_applique is not None:
            result["boussole"]["wait_until"] = wait_until_applique
        result["respect"] = respect
        result["boussole"]["respect"] = respect
        result["latences_actions"] = latences_actions
        if args.reprendre_session and derive_session_sanitisee is not None:
            result["boussole"]["session_derive"] = derive_session_sanitisee
        if auth_status is not None:
            result["boussole"]["auth_status"] = auth_status
        if a11y_redaction_echouee:
            result["boussole"]["a11y_redaction_echouee"] = True
        try:
            result["etat"] = _construire_etat(
                auth_status, respect, derive_session, erreurs_js,
                waf_bloquants=respect.get("waf_bloquants"),
                erreurs_console=erreurs_console,
                ignorer_waf=args.ignorer_waf,
            )
        except Exception:
            pass  # etat est un confort de lecture, jamais un bloquant (item A)
        result = _rediger_valeurs_secrets(result, valeurs_secrets_resolues)
        if _CHAMPS_REDIGES[0]:
            result["boussole"]["champs_rediges"] = _CHAMPS_REDIGES[0]
        print(json.dumps(result, ensure_ascii=False))
        _journaliser_run(result, actions, args.intention, url_finale_sanitisee, "succes",
                         operation_id=operation_id, source_scenario=args.source_scenario,
                         chainage=chainage, secret_resolu=bool(valeurs_secrets_resolues),
                         secrets_chemin=getattr(args, "secrets", None))
        _nettoyer_session_ephemere(
            getattr(args, "reprendre_session", None),
            explicitement_demandee=bool(args.sauver_session),
        )

    except Exception as e:
        # Répertoire chiffré fermé : erreur distincte, pas de tentative Playwright (inutile),
        # code de sortie 42 par symétrie avec Phase 7bis.
        from lib.repertoire_chiffre import SecretsFermesError
        if isinstance(e, SecretsFermesError):
            # LOT 1 (§1b) : cette branche reçoit url_cible (args.url d'origine),
            # pas url_finale — calculée localement, pas de variable de la
            # branche succès (qui peut ne pas exister si l'échec est survenu
            # avant sa construction).
            url_cible_sanitisee = _filtrer_url(url_cible)
            result = {
                "succes": False,
                "erreur": "secrets_fermes",
                "message": _filtrer_chaine(str(e)),
                "code_sortie_recommande": SecretsFermesError.CODE_SORTIE,
                "http_status": http_status,
                "duree_ms": int((time.time() - t0) * 1000),
                "horodatage": horodatage,
                "dinoer_meta": _construire_dinoer_meta(
                    profil, horodatage, modeles_appeles, url_cible_sanitisee,
                ),
                "boussole": _boussole(operation_id),
            }
            if not _filtre_evaluer_actif:
                result["boussole"]["filtre_evaluer_actif"] = False
            result = _rediger_valeurs_secrets(result, valeurs_secrets_resolues)
            if _CHAMPS_REDIGES[0]:
                result["boussole"]["champs_rediges"] = _CHAMPS_REDIGES[0]
            print(json.dumps(result, ensure_ascii=False))
            # Audit 06/08/2026 (F-03) : erreur= reprend result["message"], déjà
            # rédigé ci-dessus par _rediger_valeurs_secrets (credentials) et
            # sanitiser_urls_dans_chaine (URLs, LOT 1 §1b) — reconstruire
            # séparément depuis str(e) aurait écrit sur le canal persistant
            # (journal) une valeur que le canal éphémère (stdout) venait de
            # rédiger, exactement l'asymétrie que ces correctifs ferment.
            _journaliser_run(result, actions, args.intention, url_cible, "echec",
                             erreur=f"SecretsFermesError: {result['message']}", operation_id=operation_id,
                             source_scenario=args.source_scenario, chainage=chainage,
                             secret_resolu=bool(valeurs_secrets_resolues),
                             secrets_chemin=getattr(args, "secrets", None))
            sys.exit(SecretsFermesError.CODE_SORTIE)

        # LOT 1 (§1b) : recalculée localement, ne réutilise pas la variable de
        # la branche succès — l'exception peut survenir avant sa construction,
        # avant la sortie du bloc `with sync_playwright()`.
        url_finale_sanitisee = _filtrer_url(url_finale)

        result = {
            "succes": False,
            "erreur": type(e).__name__,
            "message": _filtrer_chaine(str(e)),
            "http_status": http_status,
            "duree_ms": int((time.time() - t0) * 1000),
            "horodatage": horodatage,
            "dinoer_meta": _construire_dinoer_meta(
                profil, horodatage, modeles_appeles, url_finale_sanitisee,
            ),
        }
        # v1.17.0, item 2 — progression partielle pour les checkpoints rpa.py.
        # Absent si l'échec est survenu avant tout appel executer_actions()
        # (ex. répertoire chiffré fermé, URL invalide) : progress reste vide dans ce cas.
        if progress.get("actions_executees") is not None:
            result["actions_executees_avant_echec"] = progress["actions_executees"]
            result["pages_visitees_avant_echec"] = progress.get("pages_visitees", 0)
        result["boussole"] = _boussole(operation_id)
        if not _filtre_evaluer_actif:
            result["boussole"]["filtre_evaluer_actif"] = False
        result = _rediger_valeurs_secrets(result, valeurs_secrets_resolues)
        if _CHAMPS_REDIGES[0]:
            result["boussole"]["champs_rediges"] = _CHAMPS_REDIGES[0]
        print(json.dumps(result, ensure_ascii=False))
        # Audit 06/08/2026 (F-03) : erreur= reprend result["message"] déjà
        # rédigé par _rediger_valeurs_secrets (credentials) et
        # sanitiser_urls_dans_chaine (URLs, LOT 1 §1b) — voir le commentaire
        # jumeau sur la branche SecretsFermesError.
        _journaliser_run(result, actions, args.intention, url_cible, "echec",
                         erreur=f"{result['erreur']}: {result['message']}", operation_id=operation_id,
                         source_scenario=args.source_scenario, chainage=chainage,
                         secret_resolu=bool(valeurs_secrets_resolues),
                         secrets_chemin=getattr(args, "secrets", None))
        _nettoyer_session_ephemere(
            getattr(args, "reprendre_session", None),
            explicitement_demandee=bool(getattr(args, "sauver_session", None)),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
