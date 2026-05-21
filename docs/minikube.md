# Minikube Deployment

This deployment path is designed for a clean Minikube rebuild after local images or containers were deleted.

## Prerequisites

- Docker Desktop is running.
- Minikube is installed.
- `kubectl` is installed and points to the Minikube context.

Start Minikube and enable metrics for the worker HPA:

```powershell
minikube start
minikube addons enable metrics-server
```

## Build And Apply

Build images inside Minikube's Docker daemon and apply manifests:

```powershell
.\scripts\minikube-deploy.ps1 -Start
```

The script builds:

- `bugswarm-backend:local`
- `bugswarm-worker:local`
- `bugswarm-frontend:local`
- `bugswarm-buggyshop:local`

The Kubernetes manifests use `imagePullPolicy: Never`, so Minikube uses those local images instead of pulling from a registry.

The local Minikube path keeps the worker CPU HPA enabled. Queue-depth autoscaling signals are still available from the backend:

```powershell
kubectl -n bugswarm port-forward svc/bugswarm-backend 8000:8000
curl http://localhost:8000/api/system/queue
curl http://localhost:8000/api/system/queue/metrics
```

For production KEDA Redis scaling, use the optional manifests documented in `docs/autoscaling.md`.

## Open Services

Use port-forwarding from separate terminals:

```powershell
kubectl -n bugswarm port-forward svc/bugswarm-frontend 5173:5173
kubectl -n bugswarm port-forward svc/bugswarm-backend 8000:8000
kubectl -n bugswarm port-forward svc/buggyshop 8090:8090
```

Then open:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/api/health`
- BuggyShop: `http://localhost:8090`

## Reset Minikube State

If the Minikube cluster was deleted or corrupted:

```powershell
minikube delete
minikube start
minikube addons enable metrics-server
.\scripts\minikube-deploy.ps1
```

PostgreSQL and shared artifact storage use PVCs inside Minikube. Deleting the Minikube cluster removes those volumes.
