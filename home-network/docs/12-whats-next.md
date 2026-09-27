# What's next

What this network deliberately does not try to do, and what it should do next,
in order of value.

## Non-goals

- **More than ~940 Mbps in aggregate.** The single gigabit trunk caps it, and
  that cap is the price of keeping technicians out of the house. See
  [Architecture](04-architecture.md).
- **Inbound services.** All three links are behind carrier NAT. Outbound
  tunnels have the side effect of not caring which provider is up.
- **Per-flow load balancing.** A single flow never exceeds one link, and it is
  incompatible with FastTrack. Torrents are the one exception. See
  [Decisions](09-decisions.md).
- **A business-grade SLA.** It buys a faster response inside one company's
  queue, not a second physical path. See
  [Reliability without authority](03-reliability-without-authority.md).

## Next, ranked

1. **A mobile data path for the work tier.** The only failure domain on offer
   that shares nothing with the others: no pole, no fibre, no switch, no trunk.
   Even a small plan for work devices alone would have covered the 64 hours
   of the September cut. By this project's own reasoning, it is worth more than
   any further tuning of the fixed lines.
2. **Finish the failover drills.** Four ISP0 runs are done and the gap is now
   2.0 s with the call surviving, twice. What is left is the other two links,
   the double failure done on purpose, and whether losing ISP0 disturbs ISP1 —
   see [Runbooks](13-runbooks.md#drills).
3. **A power drill.** Pull mains once, time each UPS, and check whether the
   hEX's uptime resets. Turns [the power row](11-own-failure-domains.md) from
   mitigated into measured.
4. **A spare switch.** The cheapest single-point-of-failure fix available.
5. **An availability number.** The share of working hours in which the work
   tier had a healthy path, computed from probe data already collected, next to
   what a single line would have delivered. That is the impact of all this in
   one figure.
6. **A provider scorecard.** Reputation, dropouts per day and support outcomes
   per slot over a term, so the next [exit decision](10-exit-strategy.md) is
   made from a record rather than a mood.
7. **Alert on the controller's mode.** "Not enforcing" reaches the event log
   but not the phone, so the failure behind the 12½-hour outage still pages
   no one.
8. **Validate the tuning constants.** A few weeks of history is enough to check
   the [reasoned constants](06-control-loop.md) against what happened.

---

[← Own failure domains](11-own-failure-domains.md) · [Runbooks →](13-runbooks.md)
