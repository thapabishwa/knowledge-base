# Getting traffic in

One LAN address, 10.0.0.30, in front of everything. Three pieces put it there.

## MetalLB, layer 2

A Service of type `LoadBalancer` asks for an address; on a cloud provider the
cloud hands one out. On a home LAN, MetalLB does, from a pool of
**10.0.0.30–39** — outside the DHCP range (.160–.191) and clear of every
reservation. Nothing answered on any of them when the pool was chosen.

In layer 2 mode the mechanism is ARP:

1. One node's speaker claims 10.0.0.30 and answers ARP for it with its own
   MAC.
2. The router, the host and every laptop cache that answer and send frames for
   10.0.0.30 to that node.
3. If the node dies, the speaker on the other node takes the address and sends
   a gratuitous ARP — an unsolicited "10.0.0.30 is now at my MAC" — so the LAN
   updates its caches. A few seconds.

It is not load balancing: one node carries an address at a time. Traefik's
Service uses `externalTrafficPolicy: Local`, so MetalLB announces from the
node actually running Traefik and the client's address survives into the
logs.

**BGP mode was rejected**, not ruled out. The hEX speaks BGP, and each node
advertising the address as a route would give ECMP and route-withdrawal
failover. With two VMs on one laptop that buys nothing, and it would put a
routing protocol beside the
[three-ISP routing](../../home-network/docs/04-architecture.md) on a router
that has enough to do. It remains a good thing to learn on, later.

Talos enforces the `baseline` Pod Security level everywhere; the speaker needs
host networking and raw sockets to answer ARP, so `metallb-system` is the one
namespace marked privileged for it.

## Traefik

The ingress controller: one Service on 10.0.0.30, ports 80 and 443, routing by
the `Host` header to each app's Ingress.

Not ingress-nginx, the usual default: it was retired upstream, with a last
release in March 2026. Traefik is maintained, reads standard Ingress objects,
and also speaks Gateway API for when Ingress gives way to HTTPRoutes.

## Names

Every app is a plain `<name>.internal`, each one an explicit record in the
router's Terraform pointing at 10.0.0.30:

```hcl
"home.internal"  = { address = "10.0.0.30", comment = "via Traefik (k8s)" }
"gatus.internal" = { address = "10.0.0.30", comment = "via Traefik (k8s)" }
```

The first version used a regexp record instead — `*.k8s.internal` to
10.0.0.30 — so that a new app needed no DNS change at all. It worked, and
was dropped within the hour:

- **Two naming schemes.** Every other household service was already
  `<name>.internal`. `gatus.k8s.internal` beside `jellyfin.internal` encodes
  *where* a thing runs into its name, which is exactly what should be free to
  change.
- **A wildcard for all of `.internal` was worse.** It would compete with the
  exact names — `pve`, `switch`, `k8s` — on the order the router evaluates
  static entries, and turn every typo into a Traefik 404 instead of a clean
  "no such host".

The cost of explicit records is one line in `addressing.tf` per app, and
pointing a name somewhere else is a change to that one line.

## Things that are not in the cluster

Most of what Traefik serves runs elsewhere: Jellyfin, qBittorrent and Unmanic
in LXC containers, the switch's web UI, pve. Each is a Service with **no
selector** and an EndpointSlice written by hand:

```yaml
kind: EndpointSlice
metadata:
  name: qbittorrent
  labels:
    kubernetes.io/service-name: qbittorrent
ports:
  - name: http
    port: 8090
endpoints:
  - addresses: ["10.0.0.11"]   # the qBittorrent container
```

To Traefik that is an ordinary Service, so an Ingress points at it like any
app in the cluster. Traefik passes the `Host` header through unchanged, which
qBittorrent's CSRF check depends on: Host, Origin and Referer must agree.

## The catch-all

An Ingress with no host rule is Traefik's lowest-priority router. Anything
reaching 10.0.0.30 without a matching name — a bare IP, a stale bookmark —
redirects to `https://home.internal`. A redirect, not a proxy, because
Homepage refuses any `Host` it was not told about.
