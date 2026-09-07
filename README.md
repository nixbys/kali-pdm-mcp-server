# kali-pdm-mcp-server

[![License](https://img.shields.io/github/license/nixbys/kali-pdm-mcp-server)](LICENSE)
[![Build](https://github.com/nixbys/kali-pdm-mcp-server/actions/workflows/build.yaml/badge.svg)](https://github.com/nixbys/kali-pdm-mcp-server/actions/workflows/build.yaml)

A Model Context Protocol (MCP) server that exposes Podman and Docker
container-runtime operations (list/run/stop/remove containers, build/pull/
push/remove images, list networks and volumes) as tools an MCP client can
call.

[🧭 What This Is](#what-this-is) | [🚀 Quick Start](#quick-start) | [🏗️ Architecture](#architecture) | [⚙️ Configuration](#configuration) | [🛠️ Tools](#tools) | [🔒 Security](#security) | [📄 License](#license)

## 🧭 What This Is <a id="what-this-is"></a>

`kali-pdm-mcp-server` is a security-hardened fork of
[`manusa/podman-mcp-server`](https://github.com/manusa/podman-mcp-server),
maintained for use in a Kali Linux / container-runtime tooling context. The
fork does not change the server's Go source or its tool set relative to
upstream at this point in time -- what it adds is a hardened CI/CD pipeline
(CodeQL, secret scanning, dependency review, pinned-by-SHA Actions,
Dependabot) and this repository's own `SECURITY.md` and `THREAT_MODEL.md`.

This is a personal fork, not an independently maintained project: it tracks
upstream's Go module path (`github.com/manusa/podman-mcp-server`) and its
npm/PyPI package metadata still names the upstream package, so it has not
been published under its own package name. Build it from source (below)
rather than expecting `npx`/`pip install` to pull a `nixbys`-published
artifact. If you just want the upstream server with no fork-specific CI, use
the original repository instead.

The server understands both Podman and Docker: it auto-detects a Podman REST
API socket first and falls back to shelling out to whichever of the
`podman`/`docker` CLI binaries is on `PATH`.

## 🚀 Quick Start <a id="quick-start"></a>

### Prerequisites

- Go 1.25+ (see `go.mod`)
- A working `podman` or `docker` installation (CLI on `PATH`, and/or a
  reachable Podman socket)
- `make`

### Build from source

```shell
git clone https://github.com/nixbys/kali-pdm-mcp-server.git
cd kali-pdm-mcp-server
make build          # runs go mod tidy, go fmt, golangci-lint, then builds
./podman-mcp-server --help
```

`make build` produces a `podman-mcp-server` binary in the repository root
for your current `GOOS`/`GOARCH`. Use `make build-all-platforms` to cross
compile for darwin/linux/windows on amd64/arm64.

### Wire it into an MCP client

Point any MCP client that spawns local stdio servers at the binary you just
built. For example, in an MCP client's JSON config:

```json
{
  "mcpServers": {
    "podman": {
      "command": "/absolute/path/to/podman-mcp-server"
    }
  }
}
```

The server also supports HTTP transport for clients that don't spawn a
subprocess -- see [Configuration](#configuration) and
[Security](#security) before binding it to anything but `127.0.0.1`.

### Run the test suite

```shell
make test
```

## 🏗️ Architecture <a id="architecture"></a>

```
cmd/podman-mcp-server/   -- entrypoint: flag parsing, server startup
pkg/config/              -- CLI flag definitions and defaults
pkg/mcp/                 -- MCP tool handlers (container/image/network/volume)
pkg/api/                 -- shared tool/parameter definitions used by pkg/mcp
pkg/podman/              -- the two runtime backends and the registry that
                            picks between them (registry.go, podman_api.go,
                            podman_cli.go, socket.go)
pkg/version/             -- build-time version metadata (set via ldflags)
internal/test/           -- shared test helpers and a mock MCP client/server
internal/tools/          -- update-readme: regenerates the Tools section
                            below from the registered tool definitions
npm/, python/            -- packaging metadata for npm and PyPI distribution
                            (currently still pointing at the upstream
                            package identifiers -- see "What This Is")
```

At startup, `pkg/podman/registry.go` selects an implementation:

| Implementation | How it works | Priority |
|----------------|---------------|----------|
| `api` | Talks to the Podman REST API over a Unix socket | 100 (preferred) |
| `cli` | Shells out to the `podman` or `docker` binary | 50 (fallback) |

The `api` backend is used automatically when a Podman socket is reachable;
otherwise the server falls back to the `cli` backend. `--podman-impl` forces
one or the other. Every MCP tool call in `pkg/mcp` is dispatched to whichever
backend is active, so the tool surface is identical regardless of which one
is in use.

## ⚙️ Configuration <a id="configuration"></a>

The server takes no environment variables -- everything is a CLI flag on the
compiled binary:

| Flag | Description |
|------|-------------|
| `--port`, `-p` | Start in HTTP mode: Streamable HTTP at `/mcp`, SSE at `/sse`. |
| `--output-format`, `-o` | `text` (default) or `json` for list-style tool output. |
| `--podman-impl` | Force `api` or `cli` instead of auto-detecting. |
| `--sse-port` | **Deprecated** legacy SSE-only mode. Use `--port`. |
| `--sse-base-url` | **Deprecated** SSE public base URL. |

```shell
# stdio mode (default) -- what MCP clients spawn
./podman-mcp-server

# HTTP mode, bound only to loopback
./podman-mcp-server --port 8080

# Force the CLI backend even if a Podman socket is present
./podman-mcp-server --podman-impl=cli
```

## 🛠️ Tools <a id="tools"></a>

<!-- AVAILABLE-TOOLS-START -->

<details>

<summary>Container</summary>

- **container_inspect** - Displays the low-level information and configuration of a Docker or Podman container with the specified container ID or name
  - `name` (`string`) **(required)** - Docker or Podman container ID or name to display the information

- **container_list** - Prints out information about the running Docker or Podman containers

- **container_logs** - Displays the logs of a Docker or Podman container with the specified container ID or name
  - `name` (`string`) **(required)** - Docker or Podman container ID or name to display the logs

- **container_remove** - Removes a Docker or Podman container with the specified container ID or name (rm)
  - `name` (`string`) **(required)** - Docker or Podman container ID or name to remove

- **container_run** - Runs a Docker or Podman container with the specified image name
  - `environment` (`array`) - Environment variables to set in the container. Format: <key>=<value>. Example: FOO=bar. (Optional, add only to set environment variables)
  - `imageName` (`string`) **(required)** - Docker or Podman container image name to run
  - `ports` (`array`) - Port mappings to expose on the host. Format: <hostPort>:<containerPort>. Example: 8080:80. (Optional, add only to expose ports)

- **container_stop** - Stops a Docker or Podman running container with the specified container ID or name
  - `name` (`string`) **(required)** - Docker or Podman container ID or name to stop

</details>

<details>

<summary>Image</summary>

- **image_build** - Build a Docker or Podman image from a Dockerfile, Podmanfile, or Containerfile
  - `containerFile` (`string`) **(required)** - The absolute path to the Dockerfile, Podmanfile, or Containerfile to build the image from
  - `imageName` (`string`) - Specifies the name which is assigned to the resulting image if the build process completes successfully (--tag, -t)

- **image_list** - List the Docker or Podman images on the local machine

- **image_pull** - Copies (pulls) a Docker or Podman container image from a registry onto the local machine storage
  - `imageName` (`string`) **(required)** - Docker or Podman container image name to pull

- **image_push** - Pushes a Docker or Podman container image, manifest list or image index from local machine storage to a registry
  - `imageName` (`string`) **(required)** - Docker or Podman container image name to push

- **image_remove** - Removes a Docker or Podman image from the local machine storage
  - `imageName` (`string`) **(required)** - Docker or Podman container image name to remove

</details>

<details>

<summary>Network</summary>

- **network_list** - List all the available Docker or Podman networks

</details>

<details>

<summary>Volume</summary>

- **volume_list** - List all the available Docker or Podman volumes

</details>


<!-- AVAILABLE-TOOLS-END -->

Run `make update-readme-tools` after adding or changing a tool to
regenerate this section from the registered tool definitions.

## 🔒 Security <a id="security"></a>

This server hands an MCP client direct control over the container runtime on
the host it runs on -- there is no per-tool authorization or confirmation
step. Read [`SECURITY.md`](SECURITY.md) for deployment guidance (stdio vs.
HTTP mode, rootless vs. rootful sockets, supported-versions policy, and how
to report a vulnerability) and [`THREAT_MODEL.md`](THREAT_MODEL.md) for the
full trust-boundary and per-tool risk breakdown. CI enforces CodeQL static
analysis, gitleaks secret scanning, `govulncheck`/`gosec`, and GitHub Actions
dependency review on every change; see `.github/workflows/`.

## 📄 License <a id="license"></a>

Apache License 2.0 -- see [`LICENSE`](LICENSE). As a fork,
security-relevant fixes that also apply to the upstream implementation
should be reported to [`manusa/podman-mcp-server`](https://github.com/manusa/podman-mcp-server)
as well, so upstream users are protected too (see `SECURITY.md`).
