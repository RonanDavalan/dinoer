"""
ntfy.py — Pont asynchrone pour les codes 2FA reçus par SMS ou courriel.

Pattern : Dinoer publie une attente sur un topic ntfy →
l'opérateur publie le code depuis son téléphone (ou via curl) →
Dinoer interroge l'API ntfy, récupère le code et l'injecte.

Configuration (par ordre de priorité) :
  1. DINOER_NTFY_URL (variable d'environnement)
  2. Clé "ntfy.url" dans le fichier lu par lib.repertoire_chiffre._lire_conf()
     (DINOER_CONF, ou /opt/dinoer/dinoer.conf par défaut)
  3. Défaut : https://ntfy.sh

Sécurité : le topic doit être un secret partagé opérateur-machine,
jamais un nom prévisible. Le stocker dans le répertoire chiffré sous 'ntfy_topic'.
"""
import json
import os
import re
import time

_NTFY_DEFAULT = "https://ntfy.sh"
_POLL_INTERVAL_S = 3
# Audit 05/08/2026 (C-05) : le topic est le seul secret du canal — un
# identifiant, pas une clé. Sans validation de format, quiconque connaît le
# topic peut injecter une valeur arbitraire dans le champ MFA. Forme
# quasi-universelle d'un code MFA SMS/email.
_CODE_MFA_FORMAT = re.compile(r"^\d{4,8}$")


def _ntfy_url() -> str:
    if "DINOER_NTFY_URL" in os.environ:
        return os.environ["DINOER_NTFY_URL"].rstrip("/")
    # Audit 05/08/2026 (D-03) : une constante _CONF_PATH locale ignorait
    # DINOER_CONF — sous le canal .deb, une instance ntfy privée déclarée
    # dans /etc/dinoer/dinoer.conf était silencieusement contournée.
    try:
        from lib.repertoire_chiffre import _lire_conf
        ntfy_conf = _lire_conf().get("ntfy") or {}
        if "url" in ntfy_conf:
            return ntfy_conf["url"].rstrip("/")
    except Exception:
        pass
    return _NTFY_DEFAULT


def publier_attente(topic: str, url_page: str, url_ntfy: str = None) -> None:
    """Publie un message d'attente MFA sur le topic ntfy.

    Audit 05/08/2026 (C-05) : l'URL cible ne part plus dans le corps du
    message — le titre suffit à identifier l'attente sans exposer
    l'infrastructure interne vers un service tiers public par défaut.
    """
    import requests
    base = (url_ntfy or _ntfy_url()).rstrip("/")
    requests.post(
        f"{base}/{topic}",
        data=b"Code MFA attendu",
        headers={
            "Title": "Dinoer — Code 2FA requis",
            "Priority": "high",
            "Tags": "key",
        },
        timeout=10,
    )


def attendre_code(topic: str, timeout_s: int = 120, url_ntfy: str = None) -> str:
    """Interroge l'API ntfy jusqu'à réception d'un message ou timeout.

    Retourne le premier message reçu sur le topic depuis l'appel de cette
    fonction **dont le format correspond à un code MFA** (4 à 8 chiffres,
    audit 05/08/2026, C-05). Un message hors format est ignoré, la boucle de
    polling continue — le topic est un identifiant, pas une clé
    cryptographique ; sans cette validation, quiconque le connaît peut
    injecter une valeur arbitraire dans le champ MFA. Lève TimeoutError si
    timeout_s est dépassé sans message valide.
    """
    import requests
    base = (url_ntfy or _ntfy_url()).rstrip("/")
    ts_debut = int(time.time())
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{base}/{topic}/json",
                params={"poll": "1", "since": str(ts_debut)},
                timeout=10,
            )
            for ligne in resp.text.strip().splitlines():
                if not ligne:
                    continue
                try:
                    msg = json.loads(ligne)
                except json.JSONDecodeError:
                    continue
                if msg.get("event") == "message" and msg.get("message"):
                    code = msg["message"].strip()
                    if _CODE_MFA_FORMAT.match(code):
                        return code
        except Exception:
            pass
        time.sleep(_POLL_INTERVAL_S)

    raise TimeoutError(
        f"Aucun code MFA reçu sur le topic ntfy après {timeout_s}s."
    )
