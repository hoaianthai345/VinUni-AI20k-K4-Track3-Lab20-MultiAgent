#!/usr/bin/env bash
set -euo pipefail
rg -n --glob '!*.egg-info/**' --glob '!**/__pycache__/**' "TODO\(student\)" src tests docs || true
