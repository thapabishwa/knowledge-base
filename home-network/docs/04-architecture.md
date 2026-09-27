# Architecture

## Why the CPEs are downstairs

The three ISP routers live on the ground floor, by the building entrance —
deliberately, and everything else follows from it.

**ISP support needs physical access to its own equipment.** Every provider's
first move on a fault is to come and look at the box. Indoors, every visit
means being home and letting a stranger in. With three providers that is three
dispatch queues — one of them for an [optical fault](01-the-problem.md) that
took eight weeks of visits.
Now a technician can do the work in the entrance area and leave.

It is only a partial security boundary. The router, hypervisor and rack stay
behind a door, but the switch has to sit with the CPEs, and its ports 5–7 are
untagged LAN (VLAN 90, bridged into `bridge-lan`). Anyone standing at it can
plug in and land on the home network, or reach the switch's management. The
door protects the rack, not the LAN.

## What that forces

The router is upstairs, about **thirty metres** of cable run from the
entrance. Three separate cables were never realistic, so **one gigabit cable**
carries everything and each ISP becomes a VLAN tag on it. `ether1` is a pure trunk — no IP address, not in any bridge.

```mermaid
%%{init: {'flowchart': {'useMaxWidth': false}, 'themeVariables': {'fontSize': '16px'}}}%%
flowchart LR
  subgraph ground["ground floor — reachable by an ISP technician without entering the house"]
    direction TB
    C0["Worldlink CPE"]
    C1["Vianet CPE"]
    C2["NTFiber CPE"]
    SW["TL-SG108E<br>ports 1-3 untagged"]
    C0 -->|"port 1"| SW
    C1 -->|"port 2"| SW
    C2 -->|"port 3"| SW
  end

  subgraph top["top floor — behind a door"]
    direction TB
    HEX["hEX rack<br>ether1 · pure trunk"]
    LAN["LAN and hypervisor"]
    HEX --- LAN
  end

  SW ==>|"one gigabit cable · 30 m<br>VLAN 10 · 20 · 30 · 90 · 100"| HEX
```

**This is also the throughput ceiling.** Three lines summing to 1000 Mbps
share one gigabit trunk — which also carries the remote LAN — so the aggregate
can never exceed about 940 Mbps. A decision made for human reasons sets the
hard limit, knowingly: the alternative is three sets of contractors in the
house on someone else's schedule.

## The trunk

```mermaid
%%{init: {'flowchart': {'useMaxWidth': false}, 'themeVariables': {'fontSize': '16px'}}}%%
flowchart LR
  subgraph carriers["three carriers · all CGNAT"]
    direction TB
    C0["Worldlink CPE<br>192.168.1.254"]
    C1["Vianet CPE<br>192.168.2.1"]
    C2["NTFiber CPE<br>192.168.100.1"]
  end

  subgraph sw["TL-SG108E · 10.0.0.2"]
    direction TB
    S1["p1 · untagged 10"]
    S2["p2 · untagged 20"]
    S3["p3 · untagged 30"]
    S57["p5-7 · untagged 90"]
    S8["p8 · trunk<br>tagged 10 20 30 90 100"]
  end

  subgraph hex["MikroTik hEX · 10.0.0.1"]
    direction TB
    E1["ether1 · no IP, not bridged"]
    V0["wan-isp0 · vlan 10"]
    V1["wan-isp1 · vlan 20"]
    V2["wan-isp2 · vlan 30"]
    LR["lan-remote · vlan 90"]
    BR["bridge-lan<br>10.0.0.1/24"]
    E25["ether2-5"]
  end

  H["remote LAN hosts"] --- S57
  C0 --- S1
  C1 --- S2
  C2 --- S3
  S1 --- S8
  S2 --- S8
  S3 --- S8
  S57 --- S8
  S8 ==>|"one 30 m cable"| E1
  E1 --- V0
  E1 --- V1
  E1 --- V2
  E1 --- LR
  LR --- BR
  E25 --- BR
```

VLAN 40 is reserved and 100 carries switch management; the hEX terminates only
10, 20, 30 and 90. `ether1` is deliberately a member of the **WAN** interface
list rather than LAN — the switch's own management CPU answers on that trunk,
so it is treated as untrusted and the input chain drops it.

**"All CGNAT" was confirmed for all three links on 5 October 2026, and a
traceroute cannot show it.** Over Worldlink and Vianet, the hop after the CPE
is public (202.166.192.2, 43.245.84.97), which reads like a public WAN
address. It is not one. The shared address is on the CPE's own WAN side, and a
traceroute never lists it: the carrier's first router answers from whatever
address it chooses, and the NAT step does not answer at all. Only NTFiber
shows it in a trace, and only because it numbers its first router in private
space (10.133.0.1). The test that settles it is the CPE's WAN address on its
status page against what `curl -s https://ifconfig.me` returns over that link.
Different addresses mean carrier NAT. To trace a single link from the router,
target one of its probe pins (`/tool/traceroute 8.8.8.8` for ISP0,
`8.8.4.4` for ISP1, `208.67.220.220` for ISP2): RouterOS v7 has no `routing-table=` on traceroute.

| | line | shaped at | CPE hands us |
|---|---|---|---|
| **ISP0** Worldlink | 400 / 200 | 380M / 186M | `192.168.1.x` by DHCP |
| **ISP1** Vianet | 400 / 200 | 380M / 186M | `192.168.2.2` static |
| **ISP2** NTFiber | 200 / 100 | 190M / 95M | `192.168.100.x` by DHCP |

ISP1's CPE does not answer DHCP at all (nine DISCOVERs over 24 seconds, no
reply), so that one address is static. Every DHCP client runs with
`add-default-route=no`: a route installed by the lease would fight the
controller for the one attribute it owns.

Every link is behind carrier NAT, so **no inbound port forwarding exists on any
of them**; anything reachable from outside is an outbound tunnel, and adding
links does not change that. Shaping runs at 93–95% of line rate to own the
queue: if the bottleneck sits in the ISP's buffer, fq_codel has nothing to
schedule and the bufferbloat happens upstream, out of sight.

---

[← Reliability without authority](03-reliability-without-authority.md) · [Device tiers →](05-tiering.md)
