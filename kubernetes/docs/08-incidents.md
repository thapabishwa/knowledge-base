# Incidents

Eight things that went wrong while building this, in one day. None reached
the household; two looked like real failures until they were understood.

## A false "all WANs down", caught in a scratch log

Covered in full in
[Dashboard and ISP monitoring](06-dashboard-and-isp-monitoring.md#the-test-that-mattered).
The router's REST account did not accept logins from the worker's address,
which is where pods' traffic comes from. Every call returned 401, and the ISP
watcher, unable to ask, wrote `CRIT ALL WANS DOWN` while all three lines were
up.

*Fix:* the account accepts the worker's address.

*Lesson:* test a monitor against the real thing it monitors, writing
somewhere disposable. A monitor that cannot see reports an outage, and an
outage record is evidence.

## Talos rejected its own patches

The first `terragrunt apply` created both VMs and then failed applying their
config:

```
UnattendedInstallConfig config is incompatible with v1alpha1 config (.machine.install)
.machine.kubelet.nodeIP is already set in v1alpha1 config
kube-apiserver config is already set in v1alpha1 config (.cluster.apiServer)
```

Talos 1.14 split its configuration into separate documents. Install, kubelet
and API server settings moved out of `machine:` and `cluster:` into
`UnattendedInstallConfig`, `KubeNodeConfig`, `KubeletConfig` and
`KubeAPIServerConfig`, and the generated config already contains them, so
patching the old fields collides with the new ones.

Terraform's validation passed; only the node knew. The VMs sat in maintenance
mode, untouched, until the patches were rewritten against the new documents —
checked first by rendering the configs locally.

## A template engine inside the values

The Homepage release failed to render:

```
template: gotpl:31: function "HOMEPAGE_VAR_PROXMOX_TOKEN" not defined
```

The bjw-s `app-template` chart runs its values through Helm's `tpl`, so
Homepage's own `{{HOMEPAGE_VAR_...}}` placeholder looked like a Helm function
call. Escaping it fixed that — and then a comment explaining the escape broke
it again, because it contained double braces too. Comments inside a values
block are templated as well.

Caught by rendering locally before pushing; Flux never saw either version.

## "Routing is broken" that was not

Straight after a deploy, five names served the catch-all redirect instead of
their apps. Traefik's log:

```
ERR Error configuring TLS error="secret lan-proxy/unmanic-internal-tls does not exist"
```

**Traefik drops an Ingress whose TLS Secret does not exist yet**, and
requests fall through to the next router — here, the catch-all. cert-manager
issued the certificates within seconds and the routes appeared on their own.
The resources were 51 seconds old when inspected.

*Lesson:* on a first deploy, wait for `kubectl get certificate` to say
`READY True` before concluding a route is wrong.

## A health check that tested the wrong thing

Gatus's "Router DNS" check went red the moment `home.internal`'s DNS record
was pointed at Traefik. It asked the router for `home.internal` and expected
the previous address; the answer was now, correctly, `10.0.0.30`.

The check was testing *where a service lived*, not whether the resolver
worked. It now queries `pve.internal`, a name that does not change when a
proxy does.

## An ordering trap in Flux

metrics-server cannot report healthy until the kubelets have CA-signed
certificates, and those depend on a Talos config change applied outside Flux.
Push first and Flux's `infra-controllers` step waits out its five-minute
timeout on metrics-server — and every app behind it waits too.

*Fix:* the Talos change goes in before the push. The general cost of Flux's
dependency chain is that one unhealthy controller blocks everything
downstream.

## Debugging a cluster before it existed

Three times, a "failure" was a command run seconds before the thing it
checked had been created: `kubectl get certificate` before cert-manager was
installed, a feed checked while its pod was still pulling its image, routes
tested before their certificates were issued. Flux showed `Reconciliation in
progress` each time.

*Lesson:* `flux get kustomizations` first. If it says in progress, nothing
else is evidence yet.

## A token that should not have been copied

Homepage's Proxmox API token had been sitting in plain text in a config file,
and had been copied around with it. Deploying the dashboard here was the
moment to stop carrying it: the token was rotated rather than reused, and the
new one lives only in a Kubernetes Secret.
