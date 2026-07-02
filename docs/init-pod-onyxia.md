# Initialiser le pod de dev sur Onyxia (SSP Cloud) et lancer le service

Procédure pas-à-pas pour un premier démarrage sur https://datalab.sspcloud.fr. Objectif : un pod VSCode opérationnel, le repo cloné, les tests verts, le service lancé et vérifié.

## 1. Lancer le service VSCode (sans GPU)

1. Se connecter au SSP Cloud (compte agent) → **Catalogue de services** → **vscode-python** (image CPU standard — **ne pas choisir de variante GPU** : l'inférence est déportée sur Albert, contrainte CLAUDE.md).
2. Configuration recommandée (annexe A de la note de cadrage) : **2 vCPU / 8 Go RAM** suffisent pour le dev (les jobs d'ingestion lourds auront leurs propres pods plus tard). Réseau : laisser les valeurs par défaut.
3. ✅ **Checklist premier login (action n°7 de la note — à faire une fois et consigner dans `SESSIONS.md`)** :
   - relever les **maxima des curseurs CPU/RAM** proposés à la création d'un service ;
   - relever l'**espace MinIO disponible** (menu « Mes fichiers ») ;
   - noter l'URL du service et le working dir réel, et recaler la section « Plateformes » de CLAUDE.md.

## 2. Cloner le repo et installer l'outillage

Dans le terminal du VSCode web — **premier clone** :

```bash
cd ~/work/
git clone https://github.com/jdly956/GRIAC.git   # authentification : token GitHub (compte jdly956)
cd ~/work/GRIAC/
```

**Repo déjà présent** (relance, nouveau pod sur volume persistant) — ne pas recloner :

```bash
cd ~/work/GRIAC/
git fetch origin
git checkout main && git pull origin main
# Pour valider une PR non mergée : git checkout <branche-de-la-PR> && git pull
```

Puis l'outillage :

```bash
# uv (gestionnaire Python du projet) — installe aussi Python 3.12 si absent
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH" && hash -r
# NB : les images Onyxia embarquent parfois déjà un uv (message « shadowed ») —
# n'importe quel uv >= 0.8 convient, vérifier avec : uv --version

make install              # uv sync --all-packages + hooks pre-commit
```

## 3. Lancer les tests

```bash
cd ~/work/GRIAC/
make lint                 # ruff — doit être vert
make test                 # pytest (socle + api + web) — doit être vert
uv run pre-commit run --all-files   # première exécution : télécharge les hooks (une fois)
```

## 4. Lancer le service

**Préalable commun (S1.4)** : l'api exige la configuration Albert — sans clé, elle refuse
de démarrer avec un message explicite (comportement voulu, CA3 de S1.4) :

```bash
cd ~/work/GRIAC/
cp .env.example .env      # .env est ignoré par git
# puis renseigner ALBERT_API_KEY=<clé> dans .env avec l'éditeur — jamais en ligne de commande
```

### Mode A — le pod dispose d'un daemon Docker

```bash
cd ~/work/GRIAC/
make dev            # postgres+pgvector -> migrations -> api -> web (attend l'état sain)
make dev-validate   # /health api + web = 200, extension pgvector présente en base
```

Consigner la sortie de `make dev-validate` dans `SESSIONS.md` (règle « validation stack-live »).

### Mode B — pas de daemon Docker sur le pod (cas standard des services VSCode Onyxia)

Les images VSCode d'Onyxia n'embarquent généralement pas de daemon Docker : lancer les
applications directement (le `/health` de l'api est sans dépendance DB, par conception) :

⚠️ **Le port 8080 est occupé par code-server** (le VSCode web lui-même) sur ces pods :
lancer le web sur **8081**. Un `401` en interrogeant 8080 = vous parlez à code-server.

```bash
cd ~/work/GRIAC/
uv run --package sia-api uvicorn sia_api.main:app --host 0.0.0.0 --port 8000 &
uv run --package sia-web uvicorn sia_web.main:app --host 0.0.0.0 --port 8081 &

curl -fsS http://localhost:8000/health   # {"status":"ok"}
curl -fsS http://localhost:8081/health   # {"status":"ok"}
curl -fsS http://localhost:8081/ | grep "Ne collez pas"   # bandeau D15 présent
```

Accès navigateur : via l'URL du service VSCode, chemin `/proxy/8000/health` et `/proxy/8081/`
(le proxy Onyxia expose les ports du pod ; noter l'URL exacte au premier essai).

Pour la base PostgreSQL en mode B : lancer un service **PostgreSQL** du catalogue Onyxia,
puis appliquer la migration depuis le pod :

```bash
cd ~/work/GRIAC/api/
DATABASE_URL="postgresql+psycopg://<user>:<mdp>@<host-du-service>:5432/<db>" \
  uv run alembic upgrade head
```

⚠️ L'extension pgvector doit être disponible dans l'image PostgreSQL choisie ; si le
service du catalogue ne la propose pas, la stack complète passera par les charts Helm (S1.6).
Ne jamais écrire l'URL ou le mot de passe dans un fichier versionné.

## 5. Arrêt et fair-use

- Mode A : `make dev-down` (ou `make dev-reset` pour purger les volumes).
- Mode B : `kill %1 %2` (ou fermer le terminal).
- Fair-use SSP Cloud : supprimer le service VSCode en fin de session de travail — tout
  l'état utile vit dans le repo Git (commits poussés) et, plus tard, dans MinIO.

## Dépannage

| Symptôme | Cause probable | Remède |
|---|---|---|
| `destination path 'GRIAC' already exists` | repo déjà cloné ; le `cd` chaîné après `&&` n'a pas été exécuté | `cd ~/work/GRIAC/` puis `git fetch` + `checkout`/`pull` (§2, « repo déjà présent ») |
| `make: No rule to make target 'install'` ou `No pyproject.toml found` | commandes lancées hors de la racine du repo | `cd ~/work/GRIAC/` puis relancer — cf. règle « commandes toujours préfixées » (CLAUDE.md) |
| `WARN: … shadowed by other commands in your PATH` à l'installation d'uv | l'image du pod embarque déjà un uv | `export PATH="$HOME/.local/bin:$PATH" && hash -r`, ou garder le uv de l'image s'il est ≥ 0.8 |
| `pytest: command not found` | environnement non activé | `cd ~/work/GRIAC/ && source .venv/bin/activate`, ou préfixer par `uv run` |
| `make dev` échoue immédiatement | pas de daemon Docker | passer en mode B |
| `[Errno 98] address already in use` sur 8080, ou `401` au curl | code-server occupe 8080 sur les pods VSCode | web sur 8081 (mode B) ; en mode A : `WEB_PORT=8081 make dev` |
| `Configuration Albert invalide — variables … manquantes ou vides` au lancement de l'api | config S1.4 absente ou incomplète | `cp .env.example .env` puis renseigner `ALBERT_API_KEY` (§4, préalable commun) |
| hot-reload inopérant | inotify indisponible sur le pod | `export WATCHFILES_FORCE_POLLING=true` avant de lancer |
| `DATABASE_URL absente` | migration lancée sans URL | fournir `DATABASE_URL` dans l'environnement du shell (jamais dans un fichier versionné) |
