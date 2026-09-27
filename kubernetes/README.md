# Kubernetes

Two VMs on a laptop, one address in front of every household name, and a
repository that is the only way anything changes.

It began as somewhere to learn the parts of a platform — GitOps, ingress,
certificates, storage — where breaking them costs nothing. It now serves the
household's web names, the dashboard and the ISP monitoring, so it is held to
the standard of the [network](../home-network/README.md) it sits on: a re-run
with nothing to do changes nothing, and the reasoning is written down.

---

## What it does

A two-node Talos cluster on the Proxmox host, deployed by Flux from this
repository. Every `<name>.internal` web address resolves to one MetalLB
address, where Traefik routes it — to an app in the cluster, or to a service
running outside it. Each name has an HTTPS certificate from a household CA
that is constrained to `.internal`, so trusting it on a laptop cannot be
turned against any other site.

The cluster runs Homepage, Gatus health checks, the dashboard's data feeds,
and the two jobs that keep a timestamped record of every ISP outage. Media,
torrents and Prometheus stay in their own containers, for reasons that are
not "haven't got round to it".

## Findings

- **The monitor reported an outage it could not see.** Tested against the real
  router before deploying, the ISP watcher got 401 on every call — its account
  did not accept the cluster's address — and wrote `ALL WANS DOWN` while all
  three lines were up. Deployed as it was, that is a false entry in the record
  used as evidence against a provider.
  → [Dashboard and ISP monitoring](docs/06-dashboard-and-isp-monitoring.md)
- **On resources alone, a cluster was overkill.** Six services used 3.7 GiB of
  46. It was built to learn on, and became the front door within a day.
  → [Why a cluster](docs/01-why-a-cluster.md)
- **Trusting a private CA does not have to mean trusting it for everything.**
  The root carries a name constraint: certificates for anything outside
  `.internal` are rejected even if its key leaks. → [HTTPS](docs/05-https.md)
- **Behind CGNAT, deployment has to be pulled.** Nothing on the internet can
  reach the house, so the cluster fetches its own changes; a push to `main` is
  the deploy. → [GitOps](docs/03-gitops.md)
- **A name should not say where a thing runs.** A `*.k8s.internal` wildcard
  lasted an hour; every app is a plain `<name>.internal` with one DNS record.
  → [Getting traffic in](docs/04-getting-traffic-in.md)
- **A health check can test the wrong thing.** One went red when a DNS record
  correctly changed, because it checked where a service lived rather than
  whether the resolver worked. → [Incidents](docs/08-incidents.md)

## Contents

| | |
|---|---|
| [Why a cluster](docs/01-why-a-cluster.md) | an audit that said "not needed", and why it was built anyway |
| [Architecture](docs/02-architecture.md) | two VMs, one address, and the dependency that creates |
| [GitOps](docs/03-gitops.md) | Flux, pulling, and the order things come up in |
| [Getting traffic in](docs/04-getting-traffic-in.md) | MetalLB over ARP, Traefik, names, and services outside the cluster |
| [HTTPS](docs/05-https.md) | a private CA, name-constrained, and the two names without a redirect |
| [Dashboard and ISP monitoring](docs/06-dashboard-and-isp-monitoring.md) | Homepage, the feeds, the outage record, and the test that mattered |
| [State and secrets](docs/07-state-and-secrets.md) | the little that is not in git, and what losing it costs |
| [Incidents](docs/08-incidents.md) | eight things that went wrong, and what each changed |
| [Decisions](docs/09-decisions.md) | twelve choices, and the alternatives rejected |
| [What's next](docs/10-whats-next.md) | non-goals, and the next seven things, ranked |
| [Runbooks](docs/11-runbooks.md) | where everything is, and what to do when it breaks |
| [Implementation](talos/README.md) | the VMs and Talos, one Terragrunt unit |

---

The VMs and Talos are in [`talos/`](talos/); everything that runs on the
cluster is under [`clusters/home/`](clusters/home/),
[`infrastructure/`](infrastructure/) and [`apps/`](apps/), applied by Flux.
DNS names are in the router's
[`addressing.tf`](../home-network/terraform/addressing.tf).
