FROM python:3.11-slim

# Minimal runtime to run Bazel targets inside containers for local ops.
# This is intended for development / local orchestration, not production hardening.

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    openjdk-17-jre-headless \
  && rm -rf /var/lib/apt/lists/*

# Install bazelisk (Bazel launcher) for Linux x86_64.
RUN curl -fsSL -o /usr/local/bin/bazelisk \
    https://github.com/bazelbuild/bazelisk/releases/latest/download/bazelisk-linux-amd64 \
  && chmod +x /usr/local/bin/bazelisk \
  && ln -s /usr/local/bin/bazelisk /usr/local/bin/bazel

WORKDIR /repo

