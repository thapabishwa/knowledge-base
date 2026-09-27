# State and secrets

Almost everything here can be rebuilt from git. These are the exceptions.

## Storage

local-path-provisioner gives PersistentVolumes as directories on a node's own
disk. On Talos the root filesystem is read-only, so the directories live
under a **user volume** at `/var/mnt/local-path-provisioner` — declared in the
Talos config as `volumeType: directory`, which carves it out of the existing
system partition rather than needing a second disk.

One volume exists today, `homenet-data`, 1 GiB, holding:

| | |
|---|---|
| `/data/log` | `isp-events.log`, `isp-history.csv` and its rotated copies — the ISP outage record |
| `/data/state` | counter baselines; loss is a difference against these |
| `/data/www` | the dashboard feeds' last good copies |

It grows by roughly 20 KB a day.

**Not replicated.** A local volume lives and dies with its node: lose the
worker's disk and the ISP history goes with it. It is also not backed up yet
— see [What's next](10-whats-next.md). The volume pins every pod that uses it
to the worker, which is why `dash-agent` and both CronJobs always run there,
and why the router only needs to accept the worker's address.

## Secrets

Three, created with `kubectl` and kept out of git until SOPS can encrypt them
in it:

| Secret | Holds | If lost |
|---|---|---|
| `homepage/homepage-secrets` | the Proxmox widget's API token | the Proxmox widget breaks; issue a new token with `pveum user token add homepage@pve dashboard --privsep 0` |
| `homenet/homenet-credentials` | router and switch logins, as `hex-api.conf` and `switch-scrape.conf` | feeds go stale and the ISP watcher stops; recreate from the router account and the switch admin |
| `cert-manager/internal-root-ca` | the household CA's private key | a new root is minted, and every device has to trust it again |

Both app Secrets are mounted `optional`: a missing Secret costs a widget or
stale data, never a pod that refuses to start. That matters on a rebuild,
where Flux brings everything up before anyone has run `kubectl create
secret`.

**The CA key is the one to back up**, because it is the only secret whose loss
has a cost outside the cluster:

```sh
kubectl -n cert-manager get secret internal-root-ca -o yaml > ~/home-internal-ca.secret.yaml
```

## The router account

The ISP scripts log in to the router's REST API as `homepage`, a read-only
account in the `dashboard` group. Like every router account it is
[deliberately not in Terraform](../../home-network/docs/09-decisions.md#user-accounts-are-not-in-terraform):
a password in Terraform is a password in state, and the provider's own
documentation says an account created without one gets a blank password.

It only accepts logins from listed addresses — the test before deploying the
ISP jobs found that the hard way
([Dashboard and ISP monitoring](06-dashboard-and-isp-monitoring.md#the-test-that-mattered)).
The worker, 10.0.0.21, must be on the list.

## What else is state

- **Terraform state** for the cluster (`talos/terraform.tfstate`, gitignored)
  holds the cluster's CA keys and bootstrap tokens. Lose it and the cluster
  still runs, but Terraform can no longer manage it.
- **`talosconfig` and `kubeconfig`** are admin credentials, written from
  Terraform outputs and gitignored.
- **etcd** holds every object the cluster runs, but all of it comes from git
  except the three Secrets above.
