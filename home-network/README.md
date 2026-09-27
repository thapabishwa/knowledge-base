# Home network

Three consumer fibre lines, one cable, and a router that reconsiders which one
you are on every ten seconds.

This is the uplink for a full-time remote job, not a lab exercise. A dropped
call or a dead SSH session is lost work; the household rides on the same
links, and everything in these pages was learned by it breaking.

---

## What it does

A MikroTik hEX terminates three ISPs over a single 30 m trunk, sorts every
device into a class, and gives each class its own link. A controller scores the
three lines continuously and rewrites the routing tables when one degrades.
Leaving a dead link is immediate once detected — traffic was back 14.6 s after
a pull in the first drill; returning on quality grounds is damped, so a
marginally better link cannot cause flapping.

Providers are slots, not dependencies: every rule refers to `isp0`, `isp1` or
`isp2`, so replacing one touches a handful of values and nothing on the LAN.
The whole configuration is declarative; a re-run reports
`0 added, 0 changed, 0 destroyed`.

## Findings

- **A fault that could be measured but not fixed — for eight weeks.** Installed
  at -27 dBm, the rated limit, with -13 dBm at the previous address; the
  provider's own app later read -31 dBm. Near that edge a link does not slow
  down, it disappears. Repaired on 20 September, to -17 dBm.
  → [The problem](docs/01-the-problem.md)
- **Redundancy is about poles, not logos.** Two of three providers share one
  electricity pole. Both were cut together and stayed down for 65 hours, and no
  support tier would have shortened that. → [Failure domains](docs/02-failure-domains.md)
- **The mean hides the fault.** 2.42% average loss is really fifty clean minutes
  and two dead ones, so scoring weights severity, not incident count.
  → [Measurement](docs/07-measurement.md)
- **A human decision sets the throughput ceiling.** The ISP routers sit by the
  entrance so technicians never enter the house, which puts all three carriers
  on one gigabit trunk: ~940 Mbps, however fast the lines get.
  → [Architecture](docs/04-architecture.md)
- **Classic SRE assumes you can fix the failing thing.** Here you cannot, which
  leaves five levers — the last of them leaving.
  → [Reliability without authority](docs/03-reliability-without-authority.md)
- **Output is not evidence of work.** The first controller ran for days without
  making a decision, because RouterOS silently discards `:global` state in
  netwatch-invoked scripts. → [Incidents](docs/08-incidents.md)

## Contents

| | |
|---|---|
| [The problem](docs/01-the-problem.md) | instrumenting the ISP's black box, and what it found |
| [Failure domains](docs/02-failure-domains.md) | three providers, two poles |
| [Reliability without authority](docs/03-reliability-without-authority.md) | what you can build when you cannot fix the dependency |
| [Architecture](docs/04-architecture.md) | one cable, four VLANs, three carriers |
| [Device tiers](docs/05-tiering.md) | classes of device, not classes of traffic |
| [The control loop](docs/06-control-loop.md) | probes, reputation, failover |
| [Measurement](docs/07-measurement.md) | the instruments, what they cannot see, and alerting |
| [Incidents](docs/08-incidents.md) | seven things that broke, and what each changed |
| [Decisions](docs/09-decisions.md) | ten choices, and the alternatives rejected |
| [Exit strategy](docs/10-exit-strategy.md) | providers as slots, and when to replace one |
| [Own failure domains](docs/11-own-failure-domains.md) | the same analysis, turned on this side of the handoff |
| [What's next](docs/12-whats-next.md) | non-goals, and the next eight things, ranked |
| [Runbooks](docs/13-runbooks.md) | what to do for each alert, the procedures, and the drills |
| [Implementation](terraform/README.md) | the Terraform, 148 resources, one unit |

---

Configuration lives in [`terraform/`](terraform/). The reputation controller is
[`terraform/scripts/isp-control.src`](terraform/scripts/isp-control.src),
commented in full.
