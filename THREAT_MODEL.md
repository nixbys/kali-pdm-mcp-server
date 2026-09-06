# Threat Model

`kali-pdm-mcp-server` is an MCP (Model Context Protocol) server that exposes
Podman/Docker container-runtime operations as tools an MCP client can call.
It has **no notion of users, sessions, or per-tool permissions of its own** --
every tool is available to every caller that can reach the server. This
document states the trust boundary so contributors can reason about security
decisions without reading through the whole tool-dispatch stack.

## Trust Boundary

The server trusts **whoever can send it MCP requests** exactly as much as it
would trust someone with a local `podman`/`docker` CLI and no confirmation
prompts. In the default (stdio) transport, that's the process that spawned
it -- normally an MCP client such as Claude Desktop, VS Code, or Goose CLI.
In HTTP mode (`--port`), it's anyone who can open a TCP connection to that
port, because the server performs no authentication of its own (see
`SECURITY.md`).

The threat model does **not** try to stop a trusted, direct caller from
running, stopping, removing, building, pulling, or pushing containers and
images -- that is the product. It does try to make the following explicit so
deployers and contributors don't assume protections that don't exist:

- There is no allowlist, confirmation step, or dry-run mode before a
  destructive or network-reaching tool call executes.
- There is no per-tool or per-target authorization -- a caller that can
  invoke `container_list` can also invoke `container_remove` on any
  container name/ID on the host, not just ones it discovered itself.
- A prompt-injection attack against the AI agent driving the MCP client
  (e.g. via untrusted content the agent reads elsewhere in its session) that
  gets the agent to call one of these tools is, from this server's point of
  view, indistinguishable from a legitimate request. The server cannot see
  or reason about *why* a tool was called.

## Backend Implementations and Their Blast Radius

`pkg/podman/registry.go` selects one of two implementations at startup
(`pkg/config`, auto-detected unless `--podman-impl` forces one):

| Implementation | Mechanism | Effective privilege |
|---|---|---|
| `api` (priority 100) | Talks to the Podman REST API over a local Unix socket | Whatever the socket's backing Podman instance runs as -- rootless (user-scoped) or rootful (host-root-equivalent), depending on deployment |
| `cli` (priority 50, fallback) | Shells out to the `podman` or `docker` binary via `os/exec` with an argument array (not a shell string, so classic shell-metacharacter injection is not applicable) | Whatever the invoking OS user can do with that binary |

Either way, the server's own process identity is not a meaningful ceiling on
what it can do -- the container runtime itself is.

## Tool Surface and Per-Tool Risk

All tools are defined in `pkg/mcp/podman_container.go`,
`pkg/mcp/podman_image.go`, `pkg/mcp/podman_network.go`, and
`pkg/mcp/podman_volume.go`. The ones with real blast radius:

- **`container_run`** -- starts any named image, with caller-supplied
  environment variables and host port publications. This is arbitrary code
  execution by design: whatever the image's entrypoint does, runs. There is
  no image allowlist. Port publication can expose a service on the host
  network that wasn't there before.
- **`image_build`** -- builds from a caller-supplied path to a
  Dockerfile/Podmanfile/Containerfile on the *host* filesystem. Every `RUN`
  instruction in that file executes during the build. A Containerfile whose
  build context includes a `COPY` of host paths can pull host file content
  into the resulting image, which can then leave the host via `image_push`.
- **`image_push`** / **`image_pull`** -- push to or pull from any registry
  the caller names. `image_push` is the exfiltration path described above;
  `image_pull` is a supply-chain path (pulling and, via `container_run`,
  executing an attacker-controlled image).
- **`container_remove`** / **`image_remove`** / **`container_stop`** --
  destructive, host-wide, and not scoped to anything this server itself
  started. A single malicious or mis-triggered call can take down containers
  or delete images unrelated to the session that requested it.
- **`container_inspect`** / **`container_logs`** -- read-only, but logs and
  inspect output can themselves contain secrets (environment variables,
  mounted-in credentials) that the calling agent then sees in its context.

`container_list`, `image_list`, `network_list`, and `volume_list` are
read-only enumeration and carry information-disclosure risk only (what's
running, what images exist) rather than an execution or destruction risk.

## Command Construction

The `cli` implementation (`pkg/podman/podman_cli.go`) builds every command as
a Go `[]string` passed to `exec.Command(binary, args...)` -- arguments are
never interpolated into a shell string, so the classic
`;`/`|`/`` ` `` ``-metacharacter shell-injection class of bug does not apply
here. The residual risk is entirely in what the arguments *mean* to
`podman`/`docker` itself (an image name, a Containerfile path, an env-var
string), not in how they're passed to the process -- see the per-tool risk
table above.

## Known Gaps

These are open, acknowledged, and contributions are welcome:

1. **No authentication in HTTP mode.** `--port` starts Streamable HTTP and
   SSE endpoints with no token or session check (`pkg/podman-mcp-server/cmd/root.go`).
   Anyone who can reach the port has the full tool surface. Mitigation today
   is entirely deployment-level (bind to loopback, front with an
   authenticating proxy) -- see `SECURITY.md`.
2. **No per-tool authorization or confirmation.** Every tool is available to
   every caller with no allowlist, rate limit, or "are you sure" step for
   destructive operations (`container_remove`, `image_remove`).
3. **No audit log.** Tool invocations are not logged anywhere the operator
   can review after the fact, beyond whatever the MCP client itself records.
4. **`image_build`'s Containerfile path is fully caller-controlled** with no
   restriction to a project directory or an allowed root, so a compromised
   caller can build from (and pull host file contents through) any path the
   server process can read.
