# Exit strategy

The one lever a consumer has is leaving — and before this network, leaving was
expensive. The ISP's router was the LAN gateway; its subnet and DHCP ran
through everything, the hypervisor included, so changing provider meant
rebuilding the network behind it.

Now the hEX owns the LAN, and a provider is a **slot**: a VLAN on the trunk and
a port on the switch.

## Providers are slots, not dependencies

Every tier, table, probe and torrent rule refers to `isp0`, `isp1` or `isp2` —
never to Worldlink, Vianet or NTFiber. Swapping the provider behind a slot
touches:

| what | where |
|---|---|
| the gateway the CPE hands out | [`routing.tf`](../terraform/routing.tf) `local.gw` |
| static address or DHCP client | [`addressing.tf`](../terraform/addressing.tf) |
| shaping limits for the new line rate | [`queues.tf`](../terraform/queues.tf) |
| capacity used for ranking | `caps` in [`isp-control.src`](../terraform/scripts/isp-control.src) |
| the provider's name | comments in `vlans.tf` and `routing.tf` |

The new CPE goes into the same switch port. Nothing on the LAN changes.

To the controller, unplugging the old CPE is the same event as that link
failing: its tier moves to the other two within about fifteen seconds. After
`apply`, the new link earns its reputation like any recovered one and the tier
moves back. A planned swap is an outage the system already handles, provided
the other two links are healthy. Steps are in
[Runbooks](13-runbooks.md#swap-a-provider).

## When to leave

Outage length is not the trigger. Vianet was down for
[65 hours](02-failure-domains.md) and is not a candidate: it handled the
incident well, the delay was weather, and another provider on the same pole
would buy nothing.

A provider is replaced when **both** of these hold:

1. **The incidents recur, measurably.** Not "it feels bad" — dropouts per day
   from `isp-events.log`, a reputation that never recovers between incidents,
   a physical-layer reading getting worse over weeks.
2. **Support has stopped producing progress.** Each contact returns a canned
   response, a reboot instruction or a promise with no date; the evidence is
   acknowledged but not engaged with; the same ticket goes round again.

Either alone is a reason to keep escalating. Both together mean escalation has
become the cost.

**ISP0 was the live case.** For eight weeks both conditions held: an
[optical fault](01-the-problem.md) from installation day, readings as low as
-31 dBm, and repeated patches that failed within a day or two. It was repaired
on 20 September, to about -17 dBm, and is now on probation: measured like the
others, and on a short term, so that if the fault returns, leaving costs
nothing more than letting the plan lapse.

## Before signing with the replacement

- **Ask which poles it uses.** A new provider on the shared pole adds a logo,
  not a failure domain. A stranger question than bandwidth, and a more useful
  one.
- **Ask which distribution box it will use, and check the level at install.**
  Worldlink's fault came from an older box with a newer one nearby. Anything
  near -27 dBm on installation day is a fault, not a pass.
- **Keep the term short while a provider is on probation.** Plans are prepaid.
  Residential lines come in one-, three- and twelve-month terms. On Worldlink's
  old 600 Mbps plan a quarter cost Rs 6,544 against Rs 22,000 a year — about
  19% more annualised, the price of being able to leave in three months rather
  than twelve. Business plans are sold a year upfront, and leaving early
  forfeits the rest.
- **Measure it like the others from day one.** The probes and reputation apply
  to the new slot unchanged, so within a week it has the same record the old
  provider was judged by.

The point is leverage: a customer who can leave in an afternoon is a different
customer from one whose whole network runs through the provider's router.

---

[← Decisions](09-decisions.md) · [Own failure domains →](11-own-failure-domains.md)
