# Déployer la stack sur le SSP Cloud (Onyxia) — chart Helm `sia-po` (S1.6)

Chart minimal : api FastAPI + web + PostgreSQL/pgvector + job de migrations. **Aucun GPU demandé** (contrainte CLAUDE.md — l'inférence est déportée sur Albert). Cible : le lab (`*.lab.sspcloud.fr`), namespace personnel Onyxia.

## Prérequis

1. Un terminal avec `kubectl` et `helm` configurés sur votre namespace — le plus simple : le terminal d'un service VSCode Onyxia (kubeconfig injecté par la plateforme).
2. **Images poussées vers un registre accessible du cluster** (le chart ne construit rien) :

```bash
cd ~/work/GRIAC/
docker build -f infra/docker/api.Dockerfile --target runtime -t <registre>/sia-api:0.1.0 .
docker build -f infra/docker/web.Dockerfile --target runtime -t <registre>/sia-web:0.1.0 .
docker push <registre>/sia-api:0.1.0 && docker push <registre>/sia-web:0.1.0
```

> Pas de daemon Docker sous la main : builder depuis un poste avec Docker, ou via un job CI de publication (post-MVP). Relever le registre retenu dans `SESSIONS.md`.

3. **Secret Albert créé dans le namespace** (jamais dans le chart ni le repo — S1.4) :

```bash
kubectl create secret generic sia-albert \
  --from-literal=ALBERT_BASE_URL=https://albert.api.etalab.gouv.fr/v1 \
  --from-literal=ALBERT_API_KEY=<clé>
```

## Installation

```bash
cd ~/work/GRIAC/
helm lint infra/helm/sia-po
helm install sia-po infra/helm/sia-po \
  --set images.api.repository=<registre>/sia-api --set images.api.tag=0.1.0 \
  --set images.web.repository=<registre>/sia-web --set images.web.tag=0.1.0 \
  --set ingress.apiHost=sia-api.<utilisateur>.lab.sspcloud.fr \
  --set ingress.webHost=sia-web.<utilisateur>.lab.sspcloud.fr \
  --set postgres.password=<mot-de-passe-lab>          # jamais commité
```

Ordre au déploiement : postgres démarre (PVC `sia-po-pgdata`), le hook `sia-po-migrate` rejoue `alembic upgrade head` (idempotent), api et web deviennent prêts via leurs probes `/health`.

## Vérification (à consigner dans SESSIONS.md — validation stack-live)

```bash
kubectl get pods                                   # attendu : postgres, api, web Running ; migrate Completed
kubectl logs job/sia-po-migrate | tail -3          # attendu : Running upgrade ... -> 0005
curl -fsS https://sia-api.<utilisateur>.lab.sspcloud.fr/health    # {"status":"ok"}
curl -fsS https://sia-web.<utilisateur>.lab.sspcloud.fr/health    # {"status":"ok"}
curl -fsS https://sia-api.<utilisateur>.lab.sspcloud.fr/projects  # [] (base vierge)
```

## Mise à jour / désinstallation

```bash
helm upgrade sia-po infra/helm/sia-po --reuse-values --set images.api.tag=<nouveau>
helm uninstall sia-po        # le PVC pgdata survit ; kubectl delete pvc sia-po-pgdata pour purger
```

## Limites assumées (POC lab)

- PostgreSQL mono-réplica sur PVC — pas de HA ; les identifiants passent par un Secret généré par le chart (surcharger le mot de passe à l'installation).
- Pas de TLS géré par le chart : le lab SSP Cloud terminaison-ne le wildcard `*.lab.sspcloud.fr`.
- La publication des images (registre, tags) reste manuelle au MVP — à industrialiser en E7 (charts prod, ProConnect).
