---
name: lumina-image
description: "Build Docker and OCI container images using Docker or Buildah. Use this skill whenever the user wants to build a container image, create a Dockerfile, run docker build, use Buildah, containerize an app, build proxy api image, build sandbox agent image, package something as a container, or ship anything in a container. If the user is talking about building or assembling container images in any way, use this skill."
---

# Building Container Images

You help users build Docker/OCI container images. Your job is to understand what they want to containerize, choose the right approach, and produce a working image — either by writing a Dockerfile and building it, or by using Buildah commands directly.

## Lumina Pre-built Image Commands

When the user asks to **build the proxy API image** (e.g., "build proxy api image", "build lumina proxy", "build proxy api"), run the `lumina_build_proxy_api_image` function from the build script:

```powershell
. "d:\work\agent-skills\skills\lumina-image\scripts\build-proxy.ps1"; lumina_build_proxy_api_image
```

When the user asks to **build the sandbox agent image** (e.g., "build sandbox agent", "build sandbox agent image", "build sandbox image"), run the `sandbox_build_agent_image` function from the build script:

```powershell
. "d:\work\agent-skills\skills\lumina-image\scripts\build-proxy.ps1"; sandbox_build_agent_image
```

**Prerequisites:** Both functions require the `MS_PATH` environment variable to be set to the CopilotLumina root directory. If it is not set, set it to the current working directory before calling the function (e.g., `$Env:MS_PATH = Get-Location`).

**ACR Login:** Before pushing, ensure the user is logged into the ACR. If the docker push fails with an authentication error, run `az acr login -n luminaacrdev` to log in, then retry.

**Important:** These commands build, push to ACR, and copy the image tag to the clipboard automatically. Do NOT attempt to manually replicate the steps in the script — just source and call the function directly.

## Choosing Between Docker and Buildah

Both tools produce OCI-compliant images, so the output is interchangeable. Here's when to recommend each:

- **Docker** (`docker build`): The default choice. Most users have Docker installed and are familiar with it. Use this unless there's a reason not to.
- **Buildah** (`buildah bud` or scripted `buildah` commands): Prefer when the user is on a system without a Docker daemon (e.g., rootless CI environments, Podman-based setups), when they explicitly ask for Buildah, or when they need fine-grained control over individual layers without writing a Dockerfile.

If the user doesn't specify, default to Docker.

## The Build Process

### 1. Understand what's being containerized

Before writing anything, figure out:

- **What application or service?** A web server, a CLI tool, a batch job, a microservice?
- **What language/runtime?** This determines the base image.
- **What files need to go in?** Source code, configs, static assets, compiled binaries?
- **What runs at startup?** The entrypoint command.
- **Any dependencies?** System packages, language packages, build tools?

Look at the project directory if one exists — check for `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, `*.csproj`, `Makefile`, or similar files that reveal the tech stack and dependencies.

### 2. Pick the right base image

Choose a base image that balances size, security, and convenience:

| Use case | Recommended base | Why |
|----------|-----------------|-----|
| Need a full package manager and tools | `ubuntu:24.04` or `debian:bookworm-slim` | Familiar, well-supported |
| Want a small image | `alpine:3.19` | ~5MB, musl-based, good for simple apps |
| Compiled language (Go, Rust, C) | `scratch` or `gcr.io/distroless/static` | Minimal attack surface for static binaries |
| Node.js | `node:22-slim` or `node:22-alpine` | Official images with Node pre-installed |
| Python | `python:3.12-slim` or `python:3.12-alpine` | Official images with Python pre-installed |
| Java | `eclipse-temurin:21-jre` | Production-ready JRE |
| .NET | `mcr.microsoft.com/dotnet/aspnet:8.0` | Official Microsoft runtime image |
| General minimal | `gcr.io/distroless/base-debian12` | No shell, no package manager — very secure |

When in doubt, use the `-slim` variant of language-specific images. They strip out build tools and docs, cutting image size significantly without losing runtime functionality.

### 3. Write the Dockerfile

Follow these principles to produce images that are small, fast to build, and secure:

**Layer ordering matters for cache efficiency.** Docker caches each layer and rebuilds from the first changed layer onward. Put things that change rarely (system packages, base setup) at the top, and things that change often (application source code) at the bottom:

```dockerfile
# Good: dependencies cached separately from source code
COPY package.json package-lock.json ./
RUN npm ci --production
COPY . .

# Bad: any source change invalidates the dependency cache
COPY . .
RUN npm ci --production
```

**Use multi-stage builds for compiled languages.** The build environment (compilers, dev headers, build tools) shouldn't ship in the production image. Multi-stage builds let you compile in one stage and copy just the artifact to a minimal runtime image:

```dockerfile
FROM golang:1.22 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /app .

FROM gcr.io/distroless/static
COPY --from=build /app /app
ENTRYPOINT ["/app"]
```

**Minimize layers.** Combine related `RUN` commands with `&&` to reduce layer count and avoid leaving deleted files in intermediate layers:

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*
```

**Don't run as root.** Create a non-root user and switch to it before the entrypoint:

```dockerfile
RUN addgroup --system app && adduser --system --ingroup app app
USER app
```

**Use `.dockerignore`.** If the project doesn't have one, suggest creating it. At minimum, exclude `.git`, `node_modules`, `__pycache__`, build artifacts, and any secrets or local config files.

**Prefer `COPY` over `ADD`.** `ADD` has implicit behavior (auto-extracting archives, fetching URLs) that can be surprising. Use `COPY` unless you specifically need those features.

**Use exec form for `ENTRYPOINT` and `CMD`.** The exec form (`["executable", "arg"]`) runs the process directly as PID 1, which means it receives signals correctly — important for graceful shutdown:

```dockerfile
ENTRYPOINT ["python", "app.py"]     # Good: exec form
ENTRYPOINT python app.py             # Avoid: shell form wraps in /bin/sh
```

### 4. Build the image

**Docker:**
```bash
docker build -t <image-name>:<tag> .
```

Common options worth knowing:
- `--no-cache` — rebuild everything from scratch (useful when debugging layer issues)
- `--build-arg KEY=VALUE` — pass build-time variables
- `--target <stage>` — build up to a specific stage in a multi-stage Dockerfile
- `--platform linux/amd64,linux/arm64` — cross-platform builds (requires BuildKit)
- `-f <path>` — use a Dockerfile at a non-default location

**Buildah:**
```bash
# From a Dockerfile (equivalent to docker build)
buildah bud -t <image-name>:<tag> .

# Or script it step by step for more control
container=$(buildah from alpine:3.19)
buildah run $container -- apk add --no-cache python3
buildah copy $container ./app /app
buildah config --entrypoint '["python3", "/app/main.py"]' $container
buildah commit $container <image-name>:<tag>
```

### 5. Verify the image works

After building, do a quick sanity check:

```bash
# Check the image exists and see its size
docker images <image-name>

# Run it and verify the entrypoint works
docker run --rm <image-name>:<tag>

# For services, map a port and test
docker run --rm -p 8080:8080 <image-name>:<tag>
```

## Troubleshooting Common Issues

**Build fails on `COPY` — file not found:** The file is probably excluded by `.dockerignore`, or the build context doesn't include it. Check the build context path (the `.` in `docker build .`) and the `.dockerignore` contents.

**Image is unexpectedly large:** Check for unnecessary files copied in (`docker history <image>` shows layer sizes). Common culprits: `.git` directory, `node_modules` copied then reinstalled, build tools left in the final image. Use multi-stage builds to fix this.

**Permission denied at runtime:** The `USER` directive might have switched to a non-root user who can't read the copied files. Make sure file ownership is correct: `COPY --chown=app:app . .`

**Package install fails in Alpine:** Alpine uses `musl` instead of `glibc`. Some packages (especially Python C extensions) may not have pre-built wheels for musl. Options: use a `-slim` Debian-based image instead, or install build dependencies and compile from source.

**Signals not working / container won't stop gracefully:** Likely using shell form for `ENTRYPOINT`. Switch to exec form so your process runs as PID 1 and receives `SIGTERM` directly.
