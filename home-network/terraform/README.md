# Terraform for the hEX

Implementation notes. **Why any of this exists, what the network is for, and
what broke along the way is in [`../README.md`](../README.md)** — read that
first if you want the reasoning rather than the mechanics.

One Terragrunt unit, 148 resources, converged: a re-run reports
`0 added, 0 changed, 0 destroyed`.

```sh
terragrunt plan
terragrunt apply
```

---

## Who owns what

The controller rewrites route distances every ten seconds. A naive Terraform
config covering routes would therefore show drift on every plan and an apply
would fight it — which is the usual reason edge routers end up managed by hand.

It is avoidable at the **attribute** level. The two systems manage the same
objects but own different fields of them:

| | this repo owns | `ISP-control` owns |
|---|---|---|
| `/ip route` | which routes exist — gateway, table, comment | `distance` |
| `/system script` | that it exists, its name, policy and body | — |
| `/system scheduler` | interval, on-event, policy | `start-date` / `start-time` |

Each of those carries `lifecycle { ignore_changes = [...] }` naming exactly the
field the other side owns. The result is that `terraform plan` stays quiet
during normal failover activity — so any diff it *does* report is a real
change: a route added, removed or repointed, or somebody in WinBox at 2am.

---

## Layout

One directory, one Terragrunt unit, one command.

```
terragrunt.hcl      provider + backend generation, reads credentials.hcl
credentials.hcl     the only place credentials live (gitignored)

vlans.tf            the 4 VLANs on the trunk, and the remote-LAN bridge port
interfaces.tf       WAN/LAN interface lists and their members
addressing.tf       WAN addresses, DHCP server and reservations, DNS
firewall.tf         filter chains, masquerade per WAN, packet marks
queues.tf           fq_codel trees, shaped per link
routing.tf          routing tables, default routes, policy rules
netwatch.tf         the nine probes
script.tf           the controller and its scheduler
system.tf           identity, clock, NTP, read-only API groups
```

### What is deliberately not here

`bridge-lan`, the `ether2`-`ether5` bridge ports, and `10.0.0.1/24`.

Terraform reaches this router *through* those six objects. Managing them means
the tool destroying its own path partway through a run — which is not a
hypothetical: an earlier version did exactly that, and a `destroy` stopped one
resource short of removing the address it was talking to.

The repo already had this principle and applied it to one thing: user accounts
are not managed, because Terraform needs them to connect. The management path
is the same category. Drawing the line there removes the bootstrap flag, the
second URL, the stack split, the dependency wiring and the two-phase apply,
all at once.

The cost is no drift detection on those six. In practice a change to them
announces itself immediately, by making the router unreachable.

`lan-remote` *is* managed, because nothing reaches this router over VLAN 90.

### Two places where order is load-bearing

RouterOS evaluates both firewall chains and routing rules top-down, first match
wins, and Terraform creates resources in parallel unless something forces a
sequence. Both are chained with `depends_on`:

- **Filter rules** — `drop everything else from WAN` landing above
  `accept all from LAN` would lock the LAN out of the router.
- **Routing rules** — the final rule matches `src 10.0.0.0/24`, the entire LAN.
  Anything created after it is dead config. The order is
  probes → infra → work → guest → household.

Within each group the members are mutually exclusive — distinct `/32`
destinations, or non-overlapping sources — so `for_each` creating them in
arbitrary order is safe there, and only there.

A third ordering constraint lives in `01-l2`: the LAN address is created before
any bridge port, because the workstation reaches the router through one of
those ports and its address goes inactive the moment the port joins the bridge.

## Running it

`credentials.hcl` is gitignored and the only place credentials live:

```hcl
locals {
  router_url      = "http://10.0.0.1"
  router_username = "admin"
  router_password = "..."
}
```

One address, and it does not change. The router is reachable there before
Terraform runs and stays reachable throughout, because the management path is
not managed here.

```sh
terragrunt plan
terragrunt apply
```

Run from this directory. There is no stack ordering to respect and no flag to
move.

`terraform_binary = "terraform"` is set in `terragrunt.hcl`, because Terragrunt
1.0 runs OpenTofu by default and the two are not interchangeable here: the lock
file pins `registry.terraform.io` while tofu resolves `registry.opentofu.org`.
It matters offline too — the provider is cached under the former, so `init`
needs no network at all, which is the normal state while rebuilding the router
that provides the network.

`router_url` is an address, not `hex.internal`. That name is a static record
served *by* this router and created by `addressing.tf`, so it cannot be how you
reach the router.

## The bootstrap

Once per router lifetime, in Winbox, which connects by MAC and needs no IP:

```
/system/reset-configuration no-defaults=yes skip-backup=yes

/interface/bridge/add name=bridge-lan
/interface/bridge/port/add bridge=bridge-lan interface=ether2
/interface/bridge/port/add bridge=bridge-lan interface=ether3
/interface/bridge/port/add bridge=bridge-lan interface=ether4
/interface/bridge/port/add bridge=bridge-lan interface=ether5
/ip/address/add address=10.0.0.1/24 interface=bridge-lan
/user/set admin password="..."
```

`no-defaults` matters. A plain reset leaves defconf's `bridge` holding
`ether2`-`ether5`, and an interface cannot be in two bridges — every other
resource then applies and those four fail with `device already added as bridge
port`.

Recreate the service accounts. Terraform makes the *groups* but never the
users, so after a reset every container that talks to the router fails to
authenticate — `login failure for user homepage ... via rest-api`, once a
minute, forever. Passwords live with the things that use them — `homepage`'s
in the cluster Secret `homenet/homenet-credentials`, `mktxp`'s on CT 104:

```
/user/add name=homepage group=dashboard  password="..." address=10.0.0.21/32
/user/add name=mktxp    group=monitoring password="..." address=10.0.0.6/32
```

`homepage` is used by the homenet scripts on the Talos worker (10.0.0.21 —
pods reach the router from their node's address) and speaks REST; `mktxp` is
on 10.0.0.6 and uses the binary API on 8728. The group split already reflects
that — `monitoring` has `api` without `rest-api`. Each account accepts logins
only from the one address that uses it.

Give the workstation a static `10.0.0.50/24` on the port cabled to the router,
put `ether1` on the switch trunk, and that is the end of the manual work. From
here it is `terragrunt apply`, the same command forever, against an address
that does not move.

### Why the bootstrap cannot be automated

Written down because it gets re-investigated otherwise.

Terraform needs two things before it can act: **an address to connect to, and
a credential**. A router reset with `no-defaults` has neither. A router on
defconf has `192.168.88.1` but a blank admin password, and REST will not
authenticate with that — it answers `401`. So the floor for any design, on any
tool, is one manual step: set a password. There is no configuration that
removes it.

**Winbox is not a counter-example.** It reaches a router with no IP because
MAC-Telnet is a MikroTik layer-2 protocol sending raw Ethernet frames with its
own session handling. The Terraform provider is an HTTP client: `hosturl` is
the only endpoint it takes, and it speaks REST on TCP/80 or the binary API on
TCP/8728. No MAC transport exists for either, and MAC-Telnet hands back a
terminal session rather than an API socket — so bridging them would mean
screen-scraping a CLI through a local proxy, which is more fragile than the IP
it replaces.

The closest real equivalent is the **IPv6 link-local address**, which is
derived from the MAC and never changes:

```
AA:BB:CC:DD:EE:FF  ->  fe80::a8bb:ccff:fedd:eeff
```

```sh
curl -s -o /dev/null -w '%{http_code}\n' -m 5 -u admin:PASSWORD \
  'http://[fe80::a8bb:ccff:fedd:eeff%25en11]/rest/system/resource'
```

`200` would mean it works as `router_url`. Untested here, and it carries three
conditions: RouterOS needs the `ipv6` package enabled, the provider's HTTP
client has to accept the `%25<iface>` zone suffix, and that zone is the
*workstation's* interface name — so the URL is not portable to another machine.
It also solves nothing that is still broken, since `10.0.0.1` no longer moves.

**Trimming the seven lines** is possible but not worth it. Keeping defconf's
`bridge` instead of creating `bridge-lan` removes four `add` lines, and adds
four `remove` lines for the DHCP server, masquerade rule and filter chain that
defconf ships and a three-WAN router does not want.

### If you lose the router

Discovery is scoped to the `LAN` interface list, so if `02-network` is
destroyed those members go with it and the Winbox **neighbour list goes empty**
— the router is still there, just no longer announcing itself. MAC-Winbox is a
separate mechanism (`/tool/mac-server`) that this config never touches: type
the bridge MAC into Winbox's *Connect To* field rather than picking from the
list.

## Deliberately not managed

**User accounts.** `routeros_system_user` carries a password attribute, and a
password in Terraform is a password in git history and in `terraform.tfstate`.
This repo is public. The *groups* are here — what an account is permitted to do
is the part worth reviewing — and the accounts themselves are made on the
router by hand.

**`/tool sniffer`.** Stopped, holding leftover arguments from a debugging
session. The provider also rejects `udp` for `filter_ip_protocol`, so managing
it would mean carrying a workaround for a value that does nothing.

## What this still will not catch

Logic bugs inside the controller — a reputation ceiling, a mode that defaults
the wrong way after a reboot, a conntrack flush on the wrong condition. To
Terraform the script is an opaque string: it verifies that the right bytes are
on the router, not that those bytes are correct.

The body is generated from `scripts/isp-control.src` and applied like
everything else, but RouterOS does not parse a script until it runs. After an
apply that changes it, run it once by hand and read the output:

```
/system script run ISP-control
```
