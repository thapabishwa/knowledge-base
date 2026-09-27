# Decisions

Short records of the choices that shaped this, including the ones rejected.

---

### A cluster at all

**Why:** to learn the working parts of a platform — GitOps, ingress,
certificates, storage, upgrades — somewhere breaking them costs nothing.
**Rejected:** Ansible against the containers, which fit the actual workload
better. See [Why a cluster](01-why-a-cluster.md).
**Consequence:** more machinery than six small services need, and a lab that
became the front door within a day.

### Talos on Proxmox VMs

**Why:** an OS that is only an API and a config file, with nothing to drift.
VMs keep it clear of Proxmox's own networking.
**Rejected:** k3s on the Proxmox host; Kubernetes inside LXC.
**Consequence:** two VMs' worth of overhead, and Talos-specific setup for
storage, Pod Security and kubelet certificates.

### Flux, pulling

**Why:** CGNAT on all three ISPs means nothing can push in.
**Rejected:** a self-hosted GitHub runner on a public repository; a
hand-written sync agent.
**Consequence:** a push is the deploy, and a broken controller blocks every
app behind it.

### MetalLB in layer 2, not BGP

**Why:** no router configuration, on a router already routing three ISPs.
**Rejected:** BGP with ECMP, which buys nothing with two VMs on one laptop.
**Consequence:** one node carries an address at a time; failover is a
gratuitous ARP, a few seconds.

### Traefik, not ingress-nginx

**Why:** ingress-nginx was retired upstream; last release March 2026.
**Rejected:** ingress-nginx; a separate reverse proxy (Caddy) in front of
the cluster.
**Consequence:** Traefik's own CRDs (Middleware, ServersTransport) appear in
the manifests.

### Plain `<name>.internal`, one DNS record per app

**Why:** names should not encode where a thing runs.
**Rejected:** a `*.k8s.internal` wildcard (used for an hour); a `*.internal`
wildcard, which would race the exact names.
**Consequence:** a new app needs a line in the router's Terraform as well as
an Ingress.

### A private CA, name-constrained

**Why:** no public CA issues for `.internal`.
**Rejected:** no TLS; skipping certificate checks; a real domain with Let's
Encrypt (later, perhaps — it is the only way to HTTPS on the TV).
**Consequence:** every device trusts the root once, and the root is limited
to `.internal` so that trust cannot be abused.

### Jellyfin keeps plain HTTP

**Why:** the TV's Jellyfin app will not trust a user-installed CA.
**Rejected:** forcing HTTPS everywhere.
**Consequence:** one name without the redirect, documented in its Ingress.

### Proxmox proxied, with its certificate verified

**Why:** pve's login only works over HTTPS, and a proxy that skips
verification hides a man in the middle.
**Rejected:** a redirect to `pve.internal:8006`; `insecureSkipVerify`.
**Consequence:** pve's public root is committed to the repo and expires in
2036.

### The same scripts, the same toolset

**Why:** the ISP record is evidence; the tools that write it should be the
ones the scripts were written against.
**Rejected:** rewriting the scripts in Python; an Alpine image with busybox
tools.
**Consequence:** a 150 MB Debian image where a smaller one might have done.

### Router accounts stay out of Terraform

**Why:** a password in Terraform is a password in state, and an account
managed without one risks a blank password.
**Rejected:** managing the account's address in Terraform with the password
ignored.
**Consequence:** one hand-run `/user set` when a source address changes,
recorded in the router's bootstrap notes.

### Secrets by hand until SOPS

**Why:** three secrets did not justify blocking everything else on an
encryption setup.
**Rejected:** committing them; blocking on SOPS.
**Consequence:** a rebuild needs three `kubectl create secret` commands, and
both app Secrets are optional so nothing refuses to start without them.
