# Runbooks

What to do, in order, without needing to remember why it is built this way.

## Where everything is

| what | where | how to reach it |
|---|---|---|
| Kubernetes API | `talos-cp-1`, `10.0.0.20` | `https://k8s.internal:6443`, kubeconfig from `talos/` outputs |
| Talos API | both nodes, port 50000 | `talosctl`, talosconfig from `talos/` outputs |
| ingress | Traefik, `10.0.0.30` | every `<name>.internal` web name |
| deploys | Flux, from `main` | `flux get kustomizations`, `flux get helmreleases -A` |
| ISP event log, history | `homenet-data` volume on the worker | `kubectl -n homenet exec deploy/dash-agent -- …` |
| household CA | `cert-manager/internal-root-ca` | see [HTTPS](05-https.md) |
| hand-made Secrets | three, listed in [State and secrets](07-state-and-secrets.md) | `kubectl` |
| VMs and Talos config | [`../talos/`](../talos/README.md) | `terragrunt plan` / `apply` |

## The cluster is down — reach things directly

Every web name goes through the cluster. When it is the problem, use the
direct names:

| instead of | use |
|---|---|
| jellyfin.internal | `http://jellyfin-ct.internal:8096` |
| qbit.internal | `http://qbit-ct.internal:8090` |
| unmanic.internal | `http://unmanic-ct.internal:8888` |
| proxmox.internal | `https://pve.internal:8006` (pve's own certificate; the browser will warn) |
| tplink.internal | `http://switch.internal` |
| home.internal | none — the dashboard runs in the cluster |

Failover is unaffected: it runs on the router.

## A change did not deploy

1. `flux get kustomizations`. If one says `Reconciliation in progress`, wait;
   nothing else is evidence yet.
2. If one is not Ready, its message names the blocker. `infra-controllers`
   blocks `infra-configs`, which blocks `apps`.
3. `flux get helmreleases -A` for the chart that failed, then
   `kubectl -n <ns> get pods,events`.
4. To retry now: `flux reconcile kustomization flux-system --with-source`.

## A name answers with a redirect to home.internal

The catch-all caught it: Traefik has no working route for that name.

1. Is the Ingress there? `kubectl get ingress -A | grep <name>`
2. Is its certificate ready? `kubectl get certificate -A` — Traefik drops an
   Ingress until its TLS Secret exists.
3. Does its Service have endpoints? `kubectl -n <ns> get endpointslices`
4. `kubectl -n traefik logs deploy/traefik --since=10m | grep -i <name>`

## A 404 from 10.0.0.30

Usually plain HTTP sent to port 443 (`curl name.internal:443` instead of
`curl https://name.internal`), or a name with no DNS record yet.

## Read the ISP record

```sh
kubectl -n homenet exec deploy/dash-agent -- tail -20 /data/log/isp-events.log
kubectl -n homenet exec deploy/dash-agent -- tail -6 /data/log/isp-history.csv
kubectl -n homenet get cronjobs,jobs
```

Dropouts per day, for a provider complaint:

```sh
kubectl -n homenet exec deploy/dash-agent -- cat /data/log/isp-events.log \
  | awk '/ISP0 DOWN/{split($1,d,"T"); c[d[1]]++} END{for(k in c) print k, c[k]}' | sort
```

## Use the switch's web UI

The switch allows one web session, and the dashboard's scraper logs you out.
Pause it first:

```sh
kubectl -n homenet exec deploy/dash-agent -- touch /data/state/switch-scrape.pause
# … use the UI …
kubectl -n homenet exec deploy/dash-agent -- rm /data/state/switch-scrape.pause
```

## Trust the CA on a new device

See [HTTPS](05-https.md#trusting-it-on-a-device).

## Add an app

1. `apps/<name>/` with its manifests and an Ingress for `<name>.internal`,
   annotated `cert-manager.io/cluster-issuer: internal-ca`, plus a
   `redirect-https` Middleware if it is browser-only.
2. Add it to `apps/kustomization.yaml`.
3. One record in `home-network/terraform/addressing.tf` pointing at
   `10.0.0.30`; `terragrunt apply` there.
4. Push.

## Rebuild from nothing

1. Recreate the Proxmox API token for Terraform (see
   [`../talos/README.md`](../talos/README.md#prerequisites)).
2. `terragrunt apply` in `talos/`; write out the kubeconfig and talosconfig.
3. `flux bootstrap` (same page).
4. Restore the CA Secret from its backup **before** cert-manager mints a new
   root — or accept re-trusting every device.
5. Recreate the two app Secrets.
6. Restore `homenet-data` from its backup, if there is one; otherwise the ISP
   history starts again from empty.
