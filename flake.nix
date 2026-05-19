# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 DirectJob Scout contributors
#
# DirectJob Scout — Nix flake for reproducible dev + run environments.
#
# Why this exists
# ---------------
# `pip install -r requirements.txt` is fine for human contributors,
# but NLnet reviewers (and anyone re-running our AI Act compliance
# evidence) deserve a build that resolves byte-identically against a
# pinned nixpkgs commit. The flake pins:
#
#   - The Python 3.12 interpreter
#   - The OS-level dev toolchain (git, curl, pkg-config, ...)
#   - The pip resolver invoked inside a project-local .venv
#
# Pip deps themselves remain pinned in `requirements.txt` +
# `requirements-dev.txt` (single source of truth across the bare-host
# pip workflow and the Nix workflow). The shellHook bootstraps the
# venv on first entry and caches it via a sentinel file so subsequent
# `nix develop` shells are fast.
#
# Hybrid approach (Nix-native interpreter + pip-managed deps) is the
# pragmatic Phase 1 choice: many of our transitive pip deps (pypdf,
# pywebpush, etc.) aren't packaged in nixpkgs at the exact versions
# we pin, and forcing them into Nix derivations would multiply
# maintenance overhead without adding reproducibility (the pip
# resolver itself is deterministic against a pinned hash range).
# A future slice can convert the runtime to a pure-Nix
# buildPythonApplication if the Conservancy / NixOS Foundation
# packaging support engages.
#
# Outputs:
#   - devShells.<system>.default — `nix develop`
#   - apps.<system>.default — `nix run`
#
# `packages.<system>.default` is intentionally not provided yet —
# see the docs/deployment-recipe.md "Nix reproducible build" section
# for the rationale.

{
  description = "DirectJob Scout — civic employment commons for the European labour market (Nix flake).";

  inputs = {
    # Pin to nixos-25.05 stable (May 2025 release line). Update via
    # `nix flake update` when the project deliberately wants newer
    # upstream packages. flake.lock captures the exact resolved
    # commit so a reviewer running `nix develop` six months from now
    # gets the same shell.
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

    # flake-utils provides eachDefaultSystem so the same outputs
    # work on x86_64-linux, aarch64-linux, x86_64-darwin, and
    # aarch64-darwin without copy-pasted per-system blocks.
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;

        # OS-level tools the bare-host setup expects: git for the
        # repo itself, curl for the npm-installed axe-core CLI (the
        # accessibility runner uses Node + Chromium which the
        # maintainer installs separately; the flake doesn't try to
        # pull a 200 MB Chromium into the dev shell).
        osTools = with pkgs; [
          git
          curl
          gnumake
          # cryptography wheels are pre-built for arm64-darwin +
          # x86_64-linux + aarch64-linux. The `pkg-config` + OpenSSL
          # headers are kept around for the rare host where pip
          # decides to source-build (older macOS / niche linux).
          pkg-config
        ];

        # Bootstrap the project venv on first `nix develop` and
        # idempotently reuse it on subsequent entries. The sentinel
        # `.venv/.deps_installed` flips after `pip install` succeeds;
        # delete it to force re-install (or just `rm -rf .venv`).
        shellHook = ''
          set -e
          if [ ! -d .venv ]; then
            echo "[flake] bootstrapping .venv with Nix-pinned Python..."
            ${python}/bin/python -m venv .venv
          fi
          # shellcheck disable=SC1091
          . .venv/bin/activate
          if [ ! -f .venv/.deps_installed ] \
              || [ requirements.txt -nt .venv/.deps_installed ] \
              || [ requirements-dev.txt -nt .venv/.deps_installed ]; then
            echo "[flake] installing pinned pip dependencies into .venv..."
            pip install --quiet --upgrade pip
            pip install --quiet -r requirements.txt -r requirements-dev.txt
            touch .venv/.deps_installed
          fi
          set +e
          echo "[flake] DirectJob Scout dev shell ready. Try: python3 -m unittest discover -s tests"
        '';
      in {
        devShells.default = pkgs.mkShell {
          name = "directjob-scout-dev";
          packages = osTools ++ [ python ];
          inherit shellHook;
        };

        # `nix run` — boots .venv if needed, then launches the
        # HTTP server on the bare-host default port. Same env-var
        # conventions as `python3 app.py` directly.
        apps.default = {
          type = "app";
          program =
            let
              script = pkgs.writeShellApplication {
                name = "directjob-scout";
                runtimeInputs = osTools ++ [ python ];
                text = ''
                  set -e
                  if [ ! -d .venv ]; then
                    echo "[flake-app] bootstrapping .venv with Nix-pinned Python..."
                    ${python}/bin/python -m venv .venv
                  fi
                  # shellcheck disable=SC1091
                  . .venv/bin/activate
                  if [ ! -f .venv/.deps_installed ]; then
                    echo "[flake-app] installing pinned pip dependencies..."
                    pip install --quiet --upgrade pip
                    pip install --quiet -r requirements.txt -r requirements-dev.txt
                    touch .venv/.deps_installed
                  fi
                  exec python3 app.py "$@"
                '';
              };
            in
            "${script}/bin/directjob-scout";
        };
      });
}
