# HTTPS

`.internal` is reserved for private networks, so no public CA will ever issue
a certificate for it. Real HTTPS on these names means running a CA.

## The household CA

cert-manager, with three objects
([`infrastructure/configs/internal-ca.yaml`](../infrastructure/configs/internal-ca.yaml)):

| | |
|---|---|
| `selfsigned` | a ClusterIssuer that bootstraps exactly one thing, the root |
| `internal-root-ca` | 10-year ECDSA P-256 root, key never rotated |
| `internal-ca` | the ClusterIssuer every Ingress names |

An Ingress annotated `cert-manager.io/cluster-issuer: internal-ca` gets a
90-day certificate for its hosts, renewed automatically. Nothing else to do
per app.

**The root's key is never rotated** (`rotationPolicy: Never`). Renewing the
root must not mint a new key, or every device that trusts it would stop.

## Name constraints

Installing a root CA on a laptop is a large grant of trust: by default a root
can sign for *any* site — a bank, an email provider. This one cannot. The root
carries an X.509 name constraint, marked critical, permitting only `.internal`:

```yaml
nameConstraints:
  critical: true
  permitted:
    dnsDomains: [internal]
```

A device that trusts it will reject any certificate it signs for a name
outside `.internal`. If the key ever leaked, the damage stops at this
network's own names.

## HTTP or HTTPS

Every browser-facing name redirects HTTP to HTTPS, through a small `redirect-https`
middleware referenced per Ingress. Two names are exempt:

- **`jellyfin.internal`.** The TV's Jellyfin app connects over plain HTTP and
  would not trust the household CA — on Android TV, apps ignore user-installed
  CAs unless they opt in. HTTPS works too, for browsers; only the redirect is
  missing.
- **`dash.internal`.** The pve host PUTs the battery reading to it every
  minute with `curl`.

The redirect is per Ingress, not on the whole HTTP entrypoint, precisely so
these two can opt out.

**The way to HTTPS on the TV too** is a publicly trusted certificate, which
needs a real domain: names like `jellyfin.home.example.com` resolving to
10.0.0.30 only inside the house, with Let's Encrypt certificates obtained by
DNS-01 — proving ownership through a DNS provider's API, which works behind
CGNAT because Let's Encrypt never has to reach in. Not done; see
[What's next](10-whats-next.md).

## Proxmox, verified both ways

Proxmox cannot be proxied over plain HTTP at all: its login sets a `Secure`
cookie in JavaScript, and a browser will not store a `Secure` cookie on an
HTTP page, so every request after login fails. Over HTTPS it can, and the hop
from Traefik to pve is verified rather than trusted blindly:

- pve's own certificate is issued by pve's cluster CA, for the names `pve`,
  `pve.homelab` and `localhost`.
- A Traefik `ServersTransport` checks it against pve's root (public — it is
  `/etc/pve/pve-root-ca.pem`, committed in
  [`apps/lan-proxy/pve-tls.yaml`](../apps/lan-proxy/pve-tls.yaml)) and the
  name `pve`.
- pve renews its node certificate itself, under the same root, so this holds
  until the root expires in September 2036.

The browser sees `proxmox.internal`'s certificate from the household CA; it
never sees pve's.

## Gatus trusts the CA without a copy of it

Gatus checks the household names over HTTPS, so it must trust the CA. It could
be given a copy of the CA certificate, committed to the repo. It does not need
one: cert-manager writes the issuing CA into **every certificate Secret** it
creates, as `ca.crt`. Gatus mounts that key from its own certificate's Secret
and adds the directory to `SSL_CERT_DIR`, which Go reads alongside the normal
CA bundle.

## Trusting it on a device

```sh
kubectl -n cert-manager get secret internal-root-ca \
  -o jsonpath='{.data.ca\.crt}' | base64 -d > home-internal-ca.crt

# macOS
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain home-internal-ca.crt
# iPhone/iPad: AirDrop the file, install the profile, then
#   Settings > General > About > Certificate Trust Settings > enable it
```

## Not the same as the kubelet certificates

The cluster has a second, unrelated certificate story. metrics-server talks to
each node's kubelet over TLS, and by default kubelets serve self-signed
certificates — the usual workaround is `--kubelet-insecure-tls`. Instead,
Talos sets `serverTLSBootstrap` so kubelets request certificates signed by the
*cluster* CA, and kubelet-serving-cert-approver approves those requests after
checking each comes from the node it names. cert-manager is not involved:
these are signed by Kubernetes itself.
