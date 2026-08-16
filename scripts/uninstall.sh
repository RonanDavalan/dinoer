#!/usr/bin/env bash
# uninstall.sh — désinstallation complète de Dinoer
#
# Supprime : /opt/dinoer/, /var/log/dinoer/, utilisateur système dinoer,
#            groupe dinoer, appartenance $USER au groupe, hook git pre-push.
#
# Préservé en toutes circonstances : ~/Vaults/, ~/git/Dinoer/, cache Playwright.
#
# Options :
#   --dry-run        Affiche les actions sans les exécuter
#   --confirme       Saute la confirmation interactive (tests à froid, CI)
#   --purge-preuves  Supprime /var/log/dinoer/preuves/ même si non vide
set -euo pipefail

DEST="/opt/dinoer"
GROUPE="dinoer"
LOG_DIR="/var/log/dinoer"
TMP_DIR="/tmp/dinoer"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=false
CONFIRME=false
PURGE_PREUVES=false

# ── Arguments ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)       DRY_RUN=true;       shift ;;
        --confirme)      CONFIRME=true;      shift ;;
        --purge-preuves) PURGE_PREUVES=true; shift ;;
        *) echo "Option inconnue : $1" >&2; exit 1 ;;
    esac
done

# ── Helper ───────────────────────────────────────────────────────────────────
cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] $*"
    else
        eval "$@"
    fi
}

# ── En-tête ──────────────────────────────────────────────────────────────────
if [ "$DRY_RUN" = true ]; then
    echo "=== Dinoer — désinstallation (DRY-RUN — aucune modification) ==="
else
    echo "=== Dinoer — désinstallation complète ==="
fi
echo ""

# ── Confirmation interactive ──────────────────────────────────────────────────
if [ "$DRY_RUN" = false ] && [ "$CONFIRME" = false ]; then
    echo "  Cette opération supprime de façon irréversible :"
    echo "    /opt/dinoer/             (code, venv, configuration)"
    echo "    /var/log/dinoer/         (journaux)"
    echo "    utilisateur système      'dinoer'"
    echo "    groupe système           'dinoer'"
    echo "    appartenance de $USER au groupe dinoer"
    echo "    hook git pre-push        (core.hooksPath)"
    echo ""
    echo "  Préservé en toutes circonstances :"
    echo "    ~/Vaults/                (répertoire chiffrés de credentials)"
    echo "    ~/git/Dinoer/            (sources git)"
    echo "    ~/.cache/ms-playwright/  (cache Playwright)"
    echo ""
    read -r -p "  Tapez 'oui' pour confirmer : " reponse
    if [ "$reponse" != "oui" ]; then
        echo "  Annulé."
        exit 0
    fi
    echo ""
fi

# ── Étape 1 — Vérification des processus actifs ───────────────────────────────
echo "  Vérification des processus Dinoer actifs..."
PROCESSUS=$(pgrep -f "shot\.py\|rpa\.py\|watch\.py\|journal\.py" 2>/dev/null || true)
if [ -n "$PROCESSUS" ]; then
    echo ""
    echo "  ERREUR : processus Dinoer en cours d'exécution :"
    echo "$PROCESSUS" | while read -r pid; do
        echo "    PID $pid : $(ps -p "$pid" -o cmd= 2>/dev/null || echo 'inconnu')"
    done
    echo ""
    echo "  Arrêter ces processus avant de relancer uninstall.sh."
    exit 1
fi
echo "  Aucun processus actif."

# ── Étape 2 — Hook git pre-push ───────────────────────────────────────────────
echo "  Retrait du hook git pre-push..."
if git -C "$REPO" config core.hooksPath &>/dev/null; then
    cmd git -C "$REPO" config --unset core.hooksPath
    echo "  Retiré : core.hooksPath"
else
    echo "  Inchangé : hook non configuré"
fi

# ── Étape 3 — /opt/dinoer/ ───────────────────────────────────────────────────
echo "  Suppression de $DEST..."
if [ -d "$DEST" ]; then
    cmd sudo rm -rf "$DEST"
    echo "  Supprimé : $DEST"
else
    echo "  Absent   : $DEST"
fi

# ── Étape 4 — /var/log/dinoer/ ───────────────────────────────────────────────
echo "  Suppression de $LOG_DIR..."
if [ -d "$LOG_DIR" ]; then
    PREUVES_DIR="$LOG_DIR/preuves"
    NB_PREUVES=0
    if [ -d "$PREUVES_DIR" ]; then
        NB_PREUVES=$(find "$PREUVES_DIR" -maxdepth 1 -type f 2>/dev/null | wc -l)
    fi

    if [ "$NB_PREUVES" -gt 0 ] && [ "$PURGE_PREUVES" = false ]; then
        echo ""
        echo "  AVERTISSEMENT : $PREUVES_DIR contient $NB_PREUVES capture(s)."
        echo "  Répertoire conservé. Utiliser --purge-preuves pour supprimer."
        echo "  Suppression de $LOG_DIR/dinoer.log uniquement..."
        cmd sudo find "$LOG_DIR" -maxdepth 1 -type f -delete
    else
        cmd sudo rm -rf "$LOG_DIR"
        echo "  Supprimé : $LOG_DIR"
    fi
else
    echo "  Absent   : $LOG_DIR"
fi

# ── Étape 5 — /tmp/dinoer/ ───────────────────────────────────────────────────
if [ -d "$TMP_DIR" ]; then
    echo "  Suppression de $TMP_DIR..."
    cmd sudo rm -rf "$TMP_DIR"
    echo "  Supprimé : $TMP_DIR"
fi

# ── Étape 6 — Retirer $USER du groupe dinoer ─────────────────────────────────
echo "  Retrait de $USER du groupe $GROUPE..."
if id -Gn "$USER" 2>/dev/null | tr ' ' '\n' | grep -qx "$GROUPE"; then
    cmd sudo gpasswd -d "$USER" "$GROUPE"
    echo "  Retiré   : $USER hors du groupe $GROUPE"
    echo "  Note     : le changement sera effectif à la prochaine connexion."
else
    echo "  Inchangé : $USER n'est pas membre du groupe $GROUPE"
fi

# ── Étape 7 — Utilisateur système dinoer ─────────────────────────────────────
echo "  Suppression de l'utilisateur système '$GROUPE'..."
if id "$GROUPE" &>/dev/null; then
    # userdel peut afficher un avertissement si d'autres membres sont dans le groupe —
    # non bloquant : le groupdel de l'étape suivante le supprime explicitement.
    cmd sudo userdel "$GROUPE" 2>/dev/null || true
    echo "  Supprimé : utilisateur '$GROUPE'"
else
    echo "  Absent   : utilisateur '$GROUPE'"
fi

# ── Étape 8 — Groupe système dinoer ──────────────────────────────────────────
echo "  Suppression du groupe système '$GROUPE'..."
if getent group "$GROUPE" &>/dev/null; then
    cmd sudo groupdel "$GROUPE"
    echo "  Supprimé : groupe '$GROUPE'"
else
    echo "  Absent   : groupe '$GROUPE'"
fi

# ── Résumé ────────────────────────────────────────────────────────────────────
echo ""
if [ "$DRY_RUN" = true ]; then
    echo "=== DRY-RUN terminé — aucune modification effectuée ==="
else
    echo "=== Désinstallation terminée ==="
    echo ""
    echo "  Pour réinstaller :"
    echo "    bash $REPO/scripts/install.sh"
fi
