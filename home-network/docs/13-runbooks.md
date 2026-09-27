# Runbooks

What to do, in order, for each thing that can go wrong, and the drills that
test the other pages' claims. The steps do not depend on remembering why the
system is built this way.

## Where everything is

| what | where | how to reach it |
|---|---|---|
| hEX router | `10.0.0.1` | Winbox (by MAC, works with no IP), or REST on port 80 |
| TL-SG108E switch | `10.0.0.2` | web UI only; one session at a time |
| event watcher, loss sampler, `isp-events.log` | Talos cluster, namespace `homenet` (CronJobs `isp-watch`, `isp-log`) | `kubectl -n homenet exec deploy/dash-agent -- tail /data/log/isp-events.log` |
| web names (`home`, `gatus`, `jellyfin`, `qbit`, `unmanic`, `proxmox`, `tplink` `.internal`) | Traefik on the cluster, `10.0.0.30` | [`kubernetes/`](../../kubernetes/README.md); each container is also reachable directly as `<name>-ct.internal` |
| exporter and Prometheus | `10.0.0.6` | alerts are evaluated here and delivered by Grafana Cloud |
| Orb sensors, one per ISP | `10.0.0.61` ISP0, `.62` ISP1, `.63` ISP2 | Orb's app; each is held to its ISP by a routing rule |
| router configuration | this repo, [`terraform/`](../terraform/) | `terragrunt plan` / `apply` |
| router password | `terraform/credentials.hcl` | gitignored; keep a copy off the router |
| DHCP reservations | `terraform/leases.hcl` | gitignored; keep a copy off the router |
| controller source | [`terraform/scripts/isp-control.src`](../terraform/scripts/isp-control.src) | deployed by `terragrunt apply` |

Useful on the router terminal:

```
/log print where topics~"warning" and message~"ISP-"   # every decision and probe line, nothing else
/log print where message~"ISP-control"     # heartbeat and decisions
/log print where message~"ISP-probe"       # which probe failed, since when, and why
/ip route print where dst-address=0.0.0.0/0  # current distances, per table
/tool netwatch print                         # the nine probes
/system scheduler print where name=isp-control
```

Matching on the message alone also returns every script change, with the whole
body pasted in; the `warning` topic keeps only what the scripts wrote.

---

## For anyone in the house

No knowledge of the system needed.

**The internet is down on every device.**

1. Check whether a phone on mobile data works. If it does not, the problem is
   wider than this house — wait.
2. Look at the three provider boxes by the entrance. If their lights show a
   connection, the fault is on this side: the switch, the cable or the router.
3. Power-cycle the **switch**, then the **router** (the small black MikroTik
   upstairs). Wait three minutes. The router starts working on its own; nothing
   needs to be set.
4. Still down: connect to a provider box's own Wi-Fi, if it is on, or use a
   phone hotspot. Both bypass everything above.

**Never press the reset button on the switch.** It wipes the configuration,
and all three internet lines go down until it is rebuilt by hand.

---

## Alerts

### `ISPDown` — one link is down

Nothing needs doing to keep working: the devices on that link have already
moved. The job is to find out why and report it.

1. Confirm the controller moved them: the latest `ISP-control` line shows that
   link's `up=0` and a `flush:` entry, and `yield` has that link's bit set.
2. Check the provider's box. No optical or PON light means the fibre; for ISP0,
   check receive power in the ONT dashboard.
3. Report it with the start time from `isp-events.log`, not "the internet is
   down".
4. If this is the second link down, `NoRedundancy` follows. Read that one next.

### `ISPDegraded` — some probes failing on one link

1. Run `/log print where message~"ISP-probe"`. If the *same* operator is
   failing on more than one link at the same moment, the operator is having a
   bad day, not the link. Nothing to do.
2. If it is one link only, watch its reputation in the heartbeat. Below 500k
   the tier yields on its own.
3. Read the `ISP-probe-why` line for that probe — see below.

### Why a probe failed

For each down event, `ISP-probe-why` re-tests the probe once from the router,
over the same pinned path, and logs the result:

| log says | means |
|---|---|
| `retest failed, timeout: failure: timeout connecting` | packets are being lost on the path — the link |
| `retest failed, refused: failure: Connection refused` | the target is rejecting us — rate limiting, or the target itself |
| `retest failed, reset: ...` | the same, closed mid-handshake |
| `retest connected` | the path worked seconds later — a transient, or netwatch misfired |
| `retest connected (...)` | TCP connected; the error came after it — e.g. `Status 308, Permanent Redirect` from Cloudflare, TLS, or an HTTP error page |
| anything mentioning permissions | the script's policy is wrong, not the link |

The timeout and refusal strings were checked against an unanswered address and
a closed port, not yet against a real outage. Confirm the first few with the
sniffer while a probe is down:

```
/tool sniffer quick interface=wan-isp1 ip-address=8.8.4.4 port=443
```

SYNs out and nothing back is a timeout; a RST back is a refusal; no SYN at all
means the router is not sending, which is a routing or pin problem.

### `NoRedundancy` — one healthy link left

The next failure is a total outage. This is the alert that matters for work.

1. Get a mobile hotspot ready for the work laptop *now*, before it is needed.
2. Do not start maintenance, swaps or drills.
3. If the surviving link is ISP0, watch its probes closely: its drop was only
   repaired on 20 September, after eight weeks of failing.
4. Chase whichever provider is down for a restoration time, and plan the day
   around it.

### `AllWANsDown` — nothing left

1. Work on the mobile hotspot immediately.
2. Decide which side the fault is on. If the provider boxes' own Wi-Fi works,
   the fault is the switch, the trunk cable or the hEX — go to
   [Replace the switch](#replace-the-switch) or
   [Replace the router](#replace-the-router). If they do not, it is the
   providers, and there is nothing to fix here.
3. This alert may never arrive: it has no path out of the house while it is
   true. See [Own failure domains](11-own-failure-domains.md).

### `RouterUnreachable` — the exporter cannot see the hEX

WAN state is unknown, not necessarily bad.

1. From a LAN device, open anything on the internet. If it works, the router
   is fine and the exporter is not — restart the exporter on `10.0.0.6`.
2. If nothing works either, treat it as `AllWANsDown` with a house-side cause.

### Controller not enforcing

Seen as `SHADOW` instead of `ENFORCE` in the heartbeat, or `CRIT` in
`isp-events.log`. Failover is off. This caused the
[twelve-and-a-half-hour outage](08-incidents.md).

1. On the router terminal: `:global ispShadow 0`
2. Within ten seconds the next line must read `ENFORCE`. If it does not, the
   script is not running — see the next runbook.

### Controller stalled — no heartbeat for over 15 minutes

1. `/system scheduler print where name=isp-control` — the run count should rise
   every ten seconds.
2. Not rising: the scheduler is disabled or missing. `terragrunt apply`
   restores it.
3. Rising but no log: run `/system script run ISP-control` by hand and read the
   error it prints.

---

## Procedures

### Swap a provider

Full reasoning in [Exit strategy](10-exit-strategy.md).

1. Check the other two links are healthy. Do not swap under `NoRedundancy`.
2. Unplug the old CPE from its switch port. Confirm its tier moved, as for
   `ISPDown`.
3. Connect the new CPE to the **same** switch port.
4. Edit the slot: gateway in `routing.tf`, static or DHCP in `addressing.tf`,
   limits in `queues.tf`, `caps` in `isp-control.src`, names in comments.
5. `terragrunt apply`, then deploy the controller if `caps` changed.
6. Verify: that slot's probes read `up=3`, and within about an hour the tier
   returns to its own link as the new line earns its reputation.

### Replace the switch

The configuration is small, and every uplink depends on it.

| port | VLAN | untagged / PVID | role |
|---|---|---|---|
| 1 | 10 | untagged | ISP0 CPE |
| 2 | 20 | untagged | ISP1 CPE |
| 3 | 30 | untagged | ISP2 CPE |
| 4 | 40 | untagged | spare slot |
| 5–7 | 90 | untagged | LAN access |
| 8 | 10, 20, 30, 90, 100 | tagged | trunk to the hEX |

1. Set management to a **static** `10.0.0.2` before anything else. With DHCP
   it takes a lease from whichever network answers first — once, from a
   provider's router.
2. Build the VLAN table above, then set each port's PVID to its VLAN.
3. Move the cables port for port. The trunk goes to hEX `ether1`.
4. Verify: all three links show `up=3` in the heartbeat, and a device on ports
   5–7 gets a `10.0.0.x` address.

Check the table against the live switch before relying on it: the switch has no
API, so this is maintained by hand.

### Replace the router

1. Bootstrap the new hEX: the seven Winbox lines in
   [the Terraform README](../terraform/README.md#the-bootstrap).
2. Restore `credentials.hcl` and `leases.hcl` into `terraform/`.
3. `terragrunt apply`. It works offline if the workstation still has
   `terraform/.plugin-cache/` — the provider mirror is gitignored, so a fresh
   clone needs one online `init` first.
4. Recreate the two service accounts (`homepage`, `mktxp`); their passwords
   live on the containers.
5. Verify: `terragrunt plan` reports no changes, the heartbeat reads `ENFORCE`,
   and the exporter is scraping again.

### Add or rebuild an Orb sensor

Each sensor is a small container held to one ISP by its source address, so it
measures that link alone and goes dark while the link is down.

1. On PVE, create the container with a **static** address — `10.0.0.61/24`
   for ISP0, `.62` ISP1, `.63` ISP2 — gateway `10.0.0.1`, DNS `1.1.1.1`.
   Public DNS rather than the router, so its lookups ride its own ISP too.
2. Install Orb and link it with the deployment token. The token is a
   credential: it goes into the container, never into this repo.
3. If the routing rules were created or replaced, restore their order:
   `terragrunt apply -replace=routeros_routing_rule.household`. The household
   rule matches the whole LAN and must sit below the three sensor rules.
4. Verify from inside each container: `curl -s https://ifconfig.me` must
   return a **different** public address for each of the three. Two the same
   means a rule is out of order.
5. Turn off Orb's speed tests, or schedule them outside working hours. A
   bandwidth test on the work link during a call degrades the call.

### Change the controller

1. Edit `terraform/scripts/isp-control.src`.
2. `terragrunt plan` — the diff should touch only the script's `source`.
3. `terragrunt apply`, then `/system script run ISP-control` once by hand.
   RouterOS does not check a script until it runs, so a syntax error applies
   cleanly and only shows up here.
4. Watch three heartbeat lines. Changing the interval, weights or margins
   retunes the whole scoring system.

---

## Drills

Each drill is written with an empty results table. A claim on the other pages
counts as demonstrated only once its row is filled in.

### Single-link failover

**Proves:** a tier moves off a dead link fast enough that a call survives.

**Expect:** about 2 s typically, 4 s at worst — up to one probe interval (2 s)
plus the timeout (1 s), plus up to one controller tick (1 s). Until 28
September this read 5 / 13 / 23 s, when probes ran at 10 s intervals with a 3 s
timeout behind a 10 s controller.

1. From a work device, join a real call and run
   [`tools/failover-drill.py`](../tools/failover-drill.py) `ISP0 --return`. It
   probes the internet every 0.2 s, watches the router log for the
   controller's decision, and prints the results row.
2. Unplug the CPE at a random moment and press Enter as you do.
3. It records the traffic gap and when the controller acted; you answer
   whether the call survived.
4. Plug it back in and time the tier's return. It scales with the outage: a
   one-tick blip leaves reputation near 700k and returns in about fifteen
   minutes (ISP1, 26 September: 13½); a minute and a half down leaves it near
   30k and needs about fifty. If the link was `main`'s primary, the 15-minute
   hold applies on top.
5. Three runs per link, at different moments.

| date | link pulled | traffic gap (s) | controller acted (s) | call survived | return time |
|---|---|---|---|---|---|
| 2026-09-27 07:08 | ISP0 | 14.6 | in the same tick traffic returned | no | stopped at 12 min; ~52 min computed |
| 2026-09-28 23:11 | ISP0 | 27.4 | 10.4 | no | stopped |
| 2026-09-28 23:57 | ISP0 | **2.0** | ~1.5 (fast path) | **yes** | stopped at 1 min |
| 2026-09-29 00:40 | ISP0 | **2.0** | **2.3** | **yes** | stopped at 1 min |

**What the first run showed.** Traffic stopped for 14.6 s, inside the predicted
5–23 s. A heartbeat 21 s after the keypress still read `up=3/3/3`, so the
cable came out a few seconds after Enter. The next tick found all three probes
down, pushed ISP0 to distance 51 in every table and flushed its connections,
and traffic returned in that tick — RouterOS's own gateway check did not beat
the controller. Main's primary moved to ISP1 on the following tick.

The call still dropped, and not only because of the 14.6 s: each link has its
own NAT, so failover changes the call's public address, and the flush that
makes new connections work ends the old ones. A call survives failover only if
the application reconnects by itself.

ISP0 came back at 33k and ranked third: about 52 minutes to pass 800k and
reclaim the work tier, and about 38 before `main` would consider it (110% of
ISP1), plus the 15-minute hold.

**What the third run showed.** 2.0 s, and the call survived — the first time it
has. Three things changed between the second run and the third: probe intervals
went from 10 s to 1–2 s, the timeout from 3 s to 1 s, and the controller from a
10 s tick to a 1 s tick with the emergency demotion on every pass. Traffic
returned at +13.5 s against an emergency demotion logged at about +13 s; the
full scoring pass, with its conntrack flush, did not run until +18.3 s. Traffic
never waited for it.

The second run's 27.4 s was misleading and worth recording as such. Only 10.4 s
of it was detection; the other 17 s looked like a client-side problem and was
nearly the basis for redesigning the wrong half. It was an unrelated ISP1 wobble
colliding with the 30 s of unbroken reachability the drill requires before it
calls a link recovered. The third run reports `client lag -0.3 s` and
`settling tail 0.0 s` — the laptop recovered when the router did, and the first
success was already stable. There is no client-side term.

**What the fourth run showed.** The same 2.0 s gap and the same surviving call,
from a clean start — all three links at full reputation, nothing yielding, the
work tier on ISP0 — so it is directly comparable to the third run rather than
being a lucky repeat.

It also produced the first trustworthy "controller acted" figure. Until 29
September the drill matched only `flush:`, which the emergency demotion never
emits, so it had been timing the scoring pass: it reported 6.8 s for a demotion
that happened at about 1.5 s. Matching `ISP-fastpath` first gives 2.3 s here,
against a 2.0 s gap — so the user-visible outage is essentially detection, with
nothing else of consequence after it.

The interesting non-result: probe intervals went from 10 s to 1–1.2 s and the
timeout from 3 s to 500 ms across these runs, which should have removed more
than a second of detection, and the measured gap stayed at 2.0 s both times.
Two samples cannot separate that from noise, and the drill's own probe
resolution is 0.2 s, but the predicted improvement has not appeared. More runs
before claiming the budget figure as the experienced one.

### What a failover actually costs, by activity

Two seconds is short enough that the interesting question is no longer duration.
It is whether an application holds one long-lived connection, because each link
has its own CGNAT address: **every failover changes the public address the far
end sees, and the conntrack flush that makes new connections work ends the old
ones.** No amount of detection speed changes that.

| activity | what a 2-second failover does |
|---|---|
| video call | a brief audio glitch, then the client reconnects. Survives — demonstrated 2026-09-28 |
| web browsing | a request in flight fails; a reload works. Usually unnoticed |
| video streaming | nothing. The buffer is tens of seconds and new segments open new connections |
| large download | breaks. Resumes if the client uses range requests, restarts if not |
| **SSH** | **dies.** A long-lived TCP session cannot survive its source address changing |
| VPN to work | drops, then reconnects by itself, usually in seconds |
| BitTorrent | nothing meaningful — it rebuilds peers continuously anyway |

The practical consequence for remote work: use `mosh` rather than `ssh` for
anything long-running. It is UDP and roams across address changes, so it
survives a failover that kills an SSH session outright. The alternative is an
overlay tunnel to a fixed endpoint, which is the only thing that makes the
address stop changing — see [Own failure domains](11-own-failure-domains.md).

### Double failure

**Proves:** the case that actually happened on 23 September, which has never
been drilled.

1. Run `tools/failover-drill.py ISP0,ISP1` and pull both CPEs together.
2. Record that `NoRedundancy` reached the phone, and how long it took.
3. Record where each tier ended up.

| date | links pulled | `NoRedundancy` arrived after | tiers ended on | notes |
|---|---|---|---|---|
| 2026-09-27 07:10 | ISP0 (router rebooted) and ISP1 (not touched) | not expected: both down together for 70 s, under the 5-minute threshold | ISP2, within one tick of ISP1 dropping | unplanned; ISP0 out 2 min 40 s, ISP1 out 70 s starting 10 s after ISP0 |

**The unplanned double failure.** Only the Worldlink router was rebooted, yet
Vianet dropped ten seconds later — before the controller flushed ISP0, so the
flush did not cause it. Either Vianet blipped independently (it had two others
overnight) or losing one link disturbs another. The second would turn every
single failure into a double, so rule it out first: check Vianet's record for
07:10–07:12, and repeat the reboot while watching ISP1's probes.

### Total outage

**Proves:** whether a total outage reaches anyone at all.

1. With the work laptop on a mobile hotspot, pull all three CPEs.
2. Record what reached the phone and when — if anything did, it came from
   Grafana Cloud noticing that data stopped.

| date | first alert | arrived after | via |
|---|---|---|---|
| | | | |

### Power

**Proves:** the UPS row in [Own failure domains](11-own-failure-domains.md).

1. Switch off mains to everything in the path at once.
2. Check the hEX's uptime afterwards. If it reset, the UPS changeover is not
   seamless.
3. Time each device until it goes dark, or stop at two hours.

| date | device | stayed up on changeover | runtime |
|---|---|---|---|
| | | | |

---

[← What's next](12-whats-next.md) · [Implementation →](../terraform/README.md)
