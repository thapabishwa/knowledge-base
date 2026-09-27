# Talos on Proxmox

Implementation notes. **Why the cluster exists and how it is used is in
[`../README.md`](../README.md)** — read that first if you want the reasoning
rather than the mechanics.

One Terragrunt unit: the two VMs, their Talos configuration, the cluster
bootstrap, and the kubeconfig.

```sh
terragrunt plan
terragrunt apply
```

---

## What it builds

| Node | VM | Address | vCPU | RAM | Disk |
|---|---|---|---|---|---|
| `talos-cp-1` (control plane) | 110 | 10.0.0.20 | 2 | 4 GiB | 20 GiB |
| `talos-w-1` (worker) | 111 | 10.0.0.21 | 4 | 10 GiB | 40 GiB |

Talos v1.14.2, Kubernetes 1.37. Providers: `bpg/proxmox` and
`siderolabs/talos`, pinned in `.terraform.lock.hcl`.

## How it works without manual steps

1. pve downloads a Talos ISO from the image factory, built from a schematic
   that adds the QEMU guest agent. Nothing passes through the laptop running
   Terraform.
2. The VMs boot it in maintenance mode. Their addresses come from a cloud-init
   drive, which the `nocloud` image reads — so each node is already at its
   final address and Terraform knows where to send its config.
3. Talos installs itself to disk using the installer from the same schematic
   (otherwise the guest agent disappears on the first reboot), then reboots.
   Boot order puts the disk first, so the ISO is only ever used once.
4. etcd is bootstrapped on the control plane and a kubeconfig is issued.

The guest agent is enabled but Terraform does not wait for it to report an
address: in maintenance mode it may not, and the provider would sit out a
15-minute timeout for an address that is static and known anyway.

## The config patches

Talos 1.14 configuration is **multi-document**. Install, kubelet and API
server settings are separate documents, and the generated config already
contains them; patching the old `machine.install`, `machine.kubelet` or
`cluster.apiServer` fields is rejected by the node with
`... is already set in v1alpha1 config`. Terraform's validation does not catch
it. The patches in [`talos.tf`](talos.tf):

| Document | Sets | Why |
|---|---|---|
| `UnattendedInstallConfig` | install disk, installer image | same schematic as the ISO |
| `KubeNodeConfig` | `nodeIP.validSubnets: 10.0.0.0/24` | a pod or service address must never be picked as the node's |
| `KubeletConfig` | `serverTLSBootstrap: true` | kubelets get CA-signed serving certificates, so metrics-server can verify them |
| `UserVolumeConfig` | `local-path-provisioner`, `volumeType: directory` | where PersistentVolumes live; a directory on the system partition, no extra disk |
| `machine.certSANs` | `k8s.internal`, `10.0.0.20` | the Talos API answers to its DNS name |
| `KubeAPIServerConfig` (control plane) | `certExtraSANs` | the Kubernetes API answers to `k8s.internal` |

Render them locally before applying — a scratch Terraform config with only
`talos_machine_secrets` and `talos_machine_configuration` shows the merged
documents in seconds, with no VMs involved.

**Order with Flux:** the `KubeletConfig` patch must be applied before Flux
installs metrics-server, which cannot become healthy until kubelets have the
new certificates.

## Prerequisites

Done by hand once, like the router's service accounts — Terraform never
creates the account it authenticates as:

```sh
# on pve
pveum role add TerraformProv -privs 'Datastore.Allocate Datastore.AllocateSpace Datastore.AllocateTemplate Datastore.Audit Pool.Allocate Pool.Audit Sys.Audit Sys.Console Sys.Modify VM.Allocate VM.Audit VM.Clone VM.Config.CDROM VM.Config.Cloudinit VM.Config.CPU VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network VM.Config.Options VM.Migrate VM.PowerMgmt VM.GuestAgent.Audit SDN.Use'
pveum user add terraform@pve
pveum aclmod / -user terraform@pve -role TerraformProv
pveum user token add terraform@pve talos --privsep 0
```

The token goes into `credentials.hcl` (gitignored):

```hcl
locals {
  pve_endpoint  = "https://10.0.0.3:8006/"
  pve_api_token = "terraform@pve!talos=<secret>"
}
```

## After apply

```sh
terragrunt output -raw talosconfig > talosconfig
terragrunt output -raw kubeconfig  > kubeconfig
export TALOSCONFIG=$PWD/talosconfig KUBECONFIG=$PWD/kubeconfig

talosctl health --nodes 10.0.0.20
kubectl get nodes -o wide
```

Both files are admin credentials and gitignored. To use the cluster from a
desktop client such as Lens, merge it into `~/.kube/config` (the context is
`admin@home`).

Then Flux, once:

```sh
export GITHUB_TOKEN=$(gh auth token)
flux bootstrap github \
  --owner=thapabishwa --repository=knowledge-base --personal \
  --branch=main --path=kubernetes/clusters/home
git pull   # bootstrap pushes its own commit with flux-system/
```

It installs the controllers, adds a **read-only** deploy key to the repo, and
commits `clusters/home/flux-system/`.

## State

`terraform.tfstate` is local and gitignored. It holds the cluster's CA keys,
etcd secrets and bootstrap tokens: losing it does not stop the cluster, but
Terraform can no longer manage it.
