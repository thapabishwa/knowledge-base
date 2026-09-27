# Decisions

Short records of the choices that shaped this, including the ones rejected —
which carry more information than the accepted ones.

---

### Three consumer lines, not one business line

**Why:** a support contract shortens the response to a fault; it does not keep
the link up. Three lines cost less and fail over in seconds.
**Rejected:** a single business plan with priority support.
**Consequence:** no contractual recourse, and redundancy only as real as the
physical independence — [two domains, not three](02-failure-domains.md). Full
comparison in [Reliability without authority](03-reliability-without-authority.md).

### Per-device-class tiers, not load balancing

**Why:** a single TCP flow never exceeds one link, so balancing buys nothing for
browsing or calls. Each class gets one link and moves only when it degrades.
**Rejected:** PCC across all traffic — incompatible with FastTrack, which
short-circuits established flows past mangle.
**Consequence:** FastTrack stays on for nearly all traffic, and a failure
affects one class rather than smearing across everyone.

### One exception: qBittorrent is split three ways

**Why:** the only workload that meets all four conditions — hundreds of
independent connections, bulk, tolerant of rotating source IPs, worth leaving
FastTrack for.
**Rejected:** a wider split. Slack, Zoom and anything with a login tie sessions
to a source address.
**Consequence:** one host pays a CPU tax the rest do not, via
`connection_mark = "no-mark"` on the fasttrack rule.

### Reputation scoring, not binary up/down

**Why:** probe state misses the chronic form of the ISP0 fault, and a symmetric
average washes out a blackout. See [The control loop](06-control-loop.md).
**Rejected:** failing over on probe state alone; equal weighting; a cooldown
timer for the tiers.
**Consequence:** tuning constants that are reasoned, not fitted — a known
weakness. The global primary keeps a timer: a 110% margin held fifteen minutes.

### The controller is scheduler-driven, not netwatch-driven

**Why:** a netwatch-invoked script cannot persist a `:global`; the first version
never made a decision. See [Incidents](08-incidents.md).
**Rejected:** decisions in `up-script` / `down-script`.
**Consequence:** netwatch measures, one script decides.

### The management path is deliberately unmanaged

**Why:** Terraform reaches the router through the bridge, its ports and
`10.0.0.1/24`; owning them let a `destroy` cut its own path.
**Rejected:** full coverage.
**Consequence:** six objects are a documented bootstrap precondition, with no
drift detection — acceptable, because a change there makes the router
unreachable.

### User accounts are not in Terraform

**Why:** `routeros_system_user` carries a password, and a password in state is
a password in a public repository.
**Rejected:** managing users; using `admin` for automation.
**Consequence:** service accounts are recreated by hand after a rebuild — a
documented step, learned from an hour of once-a-minute auth failures.

### One Terragrunt unit, not modules

**Why:** this describes one network — a specific laptop, hypervisor, eleven MAC
addresses and measured line rates. A module would have exactly one caller.
**Rejected:** a `modules/` + `live/` split; stacks with cross-state
dependencies.
**Consequence:** plain `terragrunt apply` from one directory. Revisit if a
second MikroTik appears; provider config is already factored out.

### A two-stage apply, not import tooling

**Why:** the address Terraform connects to is one of the things it creates, so
the first run cannot start where it finishes.
**Rejected:** a Python importer; a bootstrap script wrapped to survive its own
disconnection.
**Consequence:** seven documented Winbox lines, then `apply`. Both rejected
options worked; both were machinery around a problem better removed by not
managing the management path.

### ISP1 holds a static address

**Why:** tested — a dhcp-client there sent nine DISCOVERs over 24 seconds and
got nothing, while the other two bind on byte-identical config.
**Rejected:** uniformity for its own sake.
**Consequence:** one interface differs, with the sniffer command that would
overturn it recorded beside the resource.

---

[← Incidents](08-incidents.md) · [Exit strategy →](10-exit-strategy.md)
