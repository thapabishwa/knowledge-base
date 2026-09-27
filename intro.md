# Knowledge Base

Notes on the things I work with and the things I've learned, written up as I
go.

Each section is meant to be read in order — a shelf of short books rather
than a pile of notes. The reasoning and the evidence stay in, including the
parts that turned out to be wrong.

## What's documented

### [Home Network](home-network/README.md)

Three consumer ISPs in Kathmandu behind one MikroTik hEX, in a house that is
also a full-time workplace — which is the constraint that shaped it. A single
thirty-metre cable carries all three as tagged VLANs, so no technician ever
needs to come inside. Traffic is tiered by device, and a control loop scores
every link on measured loss and latency, demoting a failing one in about two
seconds. Fast enough that a video call survives it.

Start with [the problem](home-network/docs/01-the-problem.md), or go straight
to [the architecture](home-network/docs/04-architecture.md).

### [Kubernetes](kubernetes/README.md)

A two-node Talos cluster on the same laptop as everything else, built to learn
on and now the household's web front door. Flux deploys it from this
repository; MetalLB and Traefik give every service a plain `.internal` name,
and a private CA — name-constrained so trusting it cannot be abused elsewhere
— gives each one real HTTPS. It also runs the household dashboard and the
ISP monitoring, and records the test that caught a false "all WANs down"
before it reached the outage log.

## What's coming

More sections as they get written — the hypervisor and its containers next,
then whatever else earns one. The test for inclusion is whether there is a
"why" worth recording, not whether the topic is covered.

## How this is written

Figures come from a drill, a log, a screenshot or a published price, and
estimates are labelled as estimates. Where a later measurement contradicted an
earlier claim, both are kept — several diagnoses in
[Incidents](home-network/docs/08-incidents.md) were confidently wrong and are
recorded that way on purpose.

Source, including the Terraform and the controller:
[github.com/thapabishwa/knowledge-base](https://github.com/thapabishwa/knowledge-base).
