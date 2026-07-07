#!/usr/bin/env bash
# Remise en route complète des services SIA PO sur un pod Onyxia (mode B).
#
# Contexte (constaté session de validation, 03/07/2026) : sur SSP Cloud, seul
# ~/work persiste aux chutes/recréations du pod — le reste du home (dont
# ~/.bashrc), les paquets apt et les processus sont perdus. Ce script remet
# tout en état en une commande, idempotente et relançable à volonté :
#
#   cd ~/work/GRIAC/ && make pod-up
#
# Prérequis une seule fois par pod NEUF : le fichier de connexion PostgreSQL
# dans le volume persistant — ~/work/.sia-db.env (jamais dans le repo) :
#   export DATABASE_URL="postgresql+psycopg://<user>:<mdp-encodé-URL>@<host>:5432/<base>"
# (voir runbook s0 phase 0 pour le bloc de création à saisie masquée).
set -euo pipefail

RACINE="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RACINE"

# 1. Dépendance système docling/OpenCV (perdue à chaque recréation du pod)
if ! ldconfig -p | grep -q "libGL.so.1"; then
    echo "→ libGL absente : installation libgl1 + libglib2.0-0 (PDF natifs, S1.8)"
    sudo apt-get update -qq && sudo apt-get install -y -qq libgl1 libglib2.0-0
fi

# 2. Environnement python (le venv vit dans ~/work : survit aux chutes)
[ -x .venv/bin/python ] || make install
# shellcheck source=/dev/null
source .venv/bin/activate

# 3. Config — clé Albert (env du pod) + PostgreSQL (volume persistant)
for fichier in "$HOME/work/.sia-db.env" "$HOME/.sia-db.env"; do
    # shellcheck source=/dev/null
    [ -f "$fichier" ] && source "$fichier" && break
done
: "${DATABASE_URL:?DATABASE_URL absente — créer ~/work/.sia-db.env (runbook s0, phase 0)}"
: "${ALBERT_API_KEY:?ALBERT_API_KEY absente (env du pod — la clé ne vient jamais du repo)}"
grep -q "sia-db.env" "$HOME/.bashrc" 2>/dev/null \
    || echo '[ -f ~/work/.sia-db.env ] && source ~/work/.sia-db.env' >> "$HOME/.bashrc"

# 3bis. Migrations — le schéma suit TOUJOURS le code déployé (constaté session
# 30 : sans 0016/0017, l'api répond 500 sur /documents et /projects → écrans
# « en erreur », vécus comme des liens cassés). Idempotent : alembic ne rejoue
# que ce qui manque.
echo "→ migrations alembic (idempotent)"
uv run --package sia-api alembic upgrade head

# 4. Relance des services — nohup : survivent à la fermeture des terminaux
#    (pas aux chutes du pod : dans ce cas, relancer ce script).
pkill -f "uvicorn sia_api" 2>/dev/null || true
pkill -f "uvicorn sia_web" 2>/dev/null || true
sleep 1
export SIA_API_URL="http://localhost:8000"
nohup uv run --package sia-api uvicorn sia_api.main:app \
    --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &
# --root-path : par défaut l'UI est consultée via le proxy code-server
# /proxy/8081/ (port non exposable par le SA du pod — RBAC, 03/07/2026).
# Si le service Onyxia expose 8081 directement (port custom de l'onglet
# Réseau), mettre SIA_WEB_ROOT_PATH="" dans ~/work/.sia-db.env : app à la
# racine, aucun préfixe (`${VAR-…}` sans deux-points : vide explicite ≠ absent).
nohup uv run --package sia-web uvicorn sia_web.main:app \
    --host 0.0.0.0 --port 8081 --root-path "${SIA_WEB_ROOT_PATH-/proxy/8081}" \
    > /tmp/web.log 2>&1 &

# 5. Santé — on ne rend pas la main sur une stack à moitié levée
api="" ; web=""
for _ in $(seq 1 20); do
    api="$(curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health || true)"
    web="$(curl -sS -o /dev/null -w '%{http_code}' http://localhost:8081/health || true)"
    [ "$api" = "200" ] && [ "$web" = "200" ] && break
    sleep 1
done
echo "api /health : ${api:-KO} — web /health : ${web:-KO}"
if [ "$api" = "200" ] && [ "$web" = "200" ]; then
    # Le commit servi s'affiche : un écart entre l'UI vue au navigateur et le
    # code attendu se diagnostique en une ligne (vieux process = vieux sha).
    echo "✅ services relancés — code servi : $(git -C "$RACINE" rev-parse --short HEAD)" \
        "($(git -C "$RACINE" branch --show-current)) — UI : https://<url-du-pod>/proxy/8081/"
else
    echo "❌ un service ne répond pas — voir /tmp/api.log et /tmp/web.log" >&2
    exit 1
fi
