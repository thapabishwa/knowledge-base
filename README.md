# knowledge-base

Notes on the things I work with and the things I've learned, written up as I
go — with the reasoning and the evidence kept in.

**Read it as a book: [thapabishwa.gitbook.io/knowledge-base](https://thapabishwa.gitbook.io/knowledge-base)**

Each section is meant to be read in order rather than browsed at random. This
repository is the source the site syncs from.

## What's here

| | |
|---|---|
| [`home-network/`](home-network/README.md) | Three consumer ISPs behind one MikroTik hEX: failover, device tiers, measurement, and why each choice was made |
| [`home-network/terraform/`](home-network/terraform/README.md) | The router configuration. One Terragrunt unit — `terragrunt apply` is the whole deploy |
| [`home-network/tools/`](home-network/tools/) | Failover drill harness |
| [`kubernetes/`](kubernetes/README.md) | A two-node Talos cluster on the Proxmox host, deployed by Flux from this repo: the household's web front door, HTTPS from a private CA, the dashboard and the ISP monitoring |

More sections as they get written.

## How this is kept

- **Declarative and converged.** Where something is managed as code, a run
  with nothing to do reports no changes — so any change it does report is
  real.
- **No secrets.** Credentials and device reservations live in gitignored files
  beside the configuration that reads them.
- **The reasoning lives next to the thing.** Decisions record the options that
  were rejected; incidents record what was wrong, including diagnoses that
  were later retracted.
- **Sourced figures.** Numbers come from a drill, a log, a screenshot or a
  published price, and estimates are labelled as estimates.
