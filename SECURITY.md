# Security Policy

`kali-pdm-mcp-server` is a Model Context Protocol (MCP) server that gives an
MCP client (Claude Desktop, VS Code, Goose CLI, or any other MCP-speaking
agent) direct control over the Podman or Docker container runtime on the
host it runs on. Treat it the same way you would treat handing that client a
`podman`/`docker` CLI with no confirmation prompts: whoever can talk to this
server can run, stop, remove, build, pull, and push containers and images on
your machine. See [`THREAT_MODEL.md`](THREAT_MODEL.md) for the full trust
boundary and per-tool risk breakdown.

## Supported Versions

Security fixes are handled on the default branch (`main`) until a versioned
release incorporates them. Only the latest tagged release is supported.

## Deployment Guidance

- **stdio mode (default) is the intended deployment.** The server is spawned
  as a local subprocess by the MCP client and communicates over stdin/stdout.
  Only run it as a subprocess of an MCP client you trust, the same way you
  would only run a shell as a subprocess of a trusted supervisor.
- **HTTP mode (`--port`) has no built-in authentication.** The Streamable
  HTTP and SSE endpoints accept and execute any MCP request from anyone who
  can reach the port -- there is no token, API key, or session check in the
  server itself. Never bind `--port` to a non-loopback interface (`0.0.0.0`
  or a LAN/public IP) without putting it behind an authenticating reverse
  proxy, a VPN, or an equivalent private-access layer (e.g. Tailscale,
  Cloudflare Access). Binding to `127.0.0.1` and reaching it only from the
  same host is the safe default if HTTP mode is required at all.
- **The blast radius equals whatever the underlying `podman`/`docker`
  identity can do.** If the server talks to a rootful daemon or a rootful
  Podman socket, an MCP client (or an AI agent it is driving, if that agent
  has been steered by injected instructions) effectively has root-equivalent
  control of the host's container runtime. Prefer a rootless Podman socket
  wherever the workflow allows it, so a malicious or compromised request is
  capped at the invoking user's privileges rather than root.
- **Treat every tool call as capable of running arbitrary code.**
  `container_run` starts any named image with attacker-chosen environment
  variables and port publications; `image_build` builds any Containerfile
  path the caller supplies and executes every `RUN` instruction in it. Do not
  point this server at a runtime that also hosts containers you cannot afford
  to have stopped, removed, or have their logs/inspect output read by the
  connected client.
- **`image_push` can exfiltrate.** Any image the server can see (including
  one just built from a Containerfile that `COPY`'d host files into it) can
  be pushed to any registry the caller names. If you don't want data leaving
  the host through container images, restrict outbound network access from
  the environment this server runs in, or don't expose `image_build` +
  `image_push` together to an untrusted client.
- Keep the podman/docker socket path (`--podman-impl=api`) restricted with
  normal filesystem permissions; do not widen access to it beyond the user
  running this server.

## Reporting

Please report vulnerabilities privately via GitHub Security Advisories on
this repository (`nixbys/kali-pdm-mcp-server`), or by opening a minimal issue
that does not disclose exploit details. Since this repository is a fork,
vulnerabilities that also affect the upstream implementation
(`manusa/podman-mcp-server`) should additionally be reported there so
upstream users are protected too.
