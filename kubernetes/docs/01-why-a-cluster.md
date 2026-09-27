# Why a cluster

The honest answer starts with "it wasn't needed".

## The question that started it

The Proxmox host's configuration had been copied into a repository, and the
next question was the obvious one: could the repository deploy it, instead of
someone editing the containers by hand and copying the result back?

Answering that meant knowing what was being deployed. An audit of the host,
read-only, on 9 October 2026:

| | Capacity | In use |
|---|---|---|
| CPU | i7-8850H, 6 cores / 12 threads | load about 1.1 |
| Memory | 46 GiB | **3.7 GiB** |
| Container disks (NVMe thin pool) | 141 GiB | 13% |
| Media disk | 916 GiB | 69% |

Six LXC containers — media, torrents, a reverse proxy, a dashboard,
monitoring, a transcoder — and no VMs. Each used a few hundred megabytes.

## The first answers were wrong

**A hand-built sync agent.** A systemd timer on the host, pulling the repo and
pushing files into containers with `pct push`, with checks and rollback.
Around 150 lines. Rejected on reflection: it is a deployment tool, and a
deployment tool is a thing to maintain. Existing tools already do this.

**Push from GitHub.** Impossible here: all three ISPs are behind carrier-grade
NAT, so nothing on the internet can reach the host. And a self-hosted GitHub
runner on a repository meant to be public is a way for any pull request to run
code on the hypervisor. Whatever deploys has to *pull*.

**Ansible, or `ansible-pull` on a timer.** The right shape for configuration
files in containers, and it covered every container as well as the host. It
was on the table when the question changed.

## The question changed

"Run Kubernetes on this machine instead, and do GitOps there."

On resources alone, the honest assessment was that it is overkill: six small
services, a few changes a month, 3.7 GiB in use. The containers worked, and
Proxmox already provides snapshots, start order and resource limits.

As a place to learn, it was not overkill at all. Flux, SOPS, ingress, storage,
certificates and upgrades are the working parts of a production platform, and
a cluster that can be broken without consequence is the cheapest place to
practise them. So the plan was a lab: two VMs, and nothing the household
depends on until the cluster had earned it.

## What it runs

More than planned. In order of deployment:

1. **Homepage**, the household dashboard, as the first real workload.
2. **MetalLB and Traefik**, so apps get a real LAN address and a name instead
   of a node port.
3. **Plain `.internal` names** for everything, through Traefik — the cluster
   apps and the services that run outside it.
4. **HTTPS** from a private CA, for all of them.
5. **The dashboard's data feeds and the ISP monitoring** — including the
   watcher whose log is the evidence in a complaint against a provider.

So the "lab" is the household's web front door. That changes what it is
allowed to do: see [Architecture](02-architecture.md) for what runs outside
it, and [What's next](10-whats-next.md) for what a front door needs that a
lab does not.

## What runs outside it

Jellyfin, qBittorrent, Unmanic and Prometheus stay in their containers. Each
has a reason that is not "haven't got round to it":

- **qBittorrent's source address is load-bearing.** The router splits torrent
  traffic across all three ISPs by matching
  [its address, 10.0.0.11](../../home-network/docs/05-tiering.md). A pod
  leaves the cluster from its node's address, so running it there silently
  breaks the split.
- **Jellyfin needs the iGPU and the media disk.** Both are on the host. Getting
  them into a VM is GPU passthrough on a laptop and a filesystem share for
  600 GiB — effort spent arriving back where it already is.
- **Unmanic** was mid-way through a library re-encode, with tunnels to cloud
  workers. Not the moment.
- **Prometheus** scrapes the router and the host; nothing about it is better
  in a cluster.
