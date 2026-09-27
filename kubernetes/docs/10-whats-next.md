# What's next

The cluster stopped being a lab partway through. Most of this list is what a
front door needs that a lab could do without.

## Non-goals

- **High availability.** Both nodes are VMs on one laptop. Three nodes on the
  same laptop would be the same failure domain with more overhead.
- **Running Jellyfin, qBittorrent or Prometheus in the cluster.** Each has a
  reason in [Why a cluster](01-why-a-cluster.md#what-runs-outside-it).
- **Exposing anything to the internet.** Nothing here has a public address,
  and nothing needs one.

## Next, in order

1. **SOPS with age.** Encrypt the three hand-made Secrets into this
   repository, so a rebuild is `terragrunt apply` and a push, with nothing
   typed in between.
2. **Back up `homenet-data`.** The ISP outage record now sits on one VM's
   disk. A nightly copy off the host — anywhere — is the minimum.
3. **Back up the CA key** somewhere other than the laptop, and say where.
4. **Renovate.** Chart and image versions are pinned; a bot opening pull
   requests for new ones keeps them current without anyone remembering to
   look.
5. **A real domain for HTTPS on the TV.** Names under a domain this household
   owns, resolving only inside the house, with Let's Encrypt certificates via
   DNS-01. The one route to HTTPS on devices that will not trust a private CA.
6. **Manage the Proxmox host itself.** Its fan curve, battery limits and
   power script are files nobody deploys; Ansible, or Talos-style
   declarative config on the host, would close the gap.
7. **Observability inside the cluster.** Prometheus in its container scrapes
   the router and the host, not the cluster; kube-prometheus-stack writing to
   the same Grafana Cloud would.
