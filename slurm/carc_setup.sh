#!/bin/bash
# One-time setup on a CARC Discovery login node. Run from the repo root:
#   bash slurm/carc_setup.sh
# Installs Ollama (user space, no root), pulls the models and checks their IDs against
# slurm/models.txt, creates .venv, and locks down permissions. Prints no note text.
set -euo pipefail

OLLAMA_VERSION=0.40.12
OLLAMA_DIR="$HOME/.local/ollama-$OLLAMA_VERSION"
export OLLAMA_MODELS="/scratch1/$USER/ollama-models"
export OLLAMA_HOST="127.0.0.1:$((20000 + RANDOM % 10000))"
PYTHON="${PYTHON:-python3}"

# 1. MIMIC-derived files stay private to this account (PhysioNet DUA).
for f in candidates dev_sample test_sample test_b_sample; do
    [ -f "data/derived/$f.parquet" ] || { echo "missing data/derived/$f.parquet"; exit 1; }
done
chmod 700 . data
chmod -R go-rwx data
mkdir -p slurm/logs data/predictions && chmod 700 slurm/logs
echo "permissions: repo and data/ are owner-only"

# 2. Python environment (needs 3.11+).
"$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 11))' \
    || { echo "need Python >= 3.11: module load one, or set PYTHON=..."; exit 1; }
[ -d .venv ] || "$PYTHON" -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q duckdb pyarrow "pydantic>=2" requests
echo "python: $(.venv/bin/python --version)"

# 3. Ollama, pinned to the local version.
if [ ! -x "$OLLAMA_DIR/bin/ollama" ]; then
    mkdir -p "$OLLAMA_DIR"
    base="https://github.com/ollama/ollama/releases/download/v$OLLAMA_VERSION"
    if curl -fsSL "$base/ollama-linux-amd64.tgz" -o /tmp/ollama-$USER.tgz; then
        tar -xzf /tmp/ollama-$USER.tgz -C "$OLLAMA_DIR"
    else
        curl -fsSL "$base/ollama-linux-amd64.tar.zst" | tar --zstd -x -C "$OLLAMA_DIR"
    fi
    rm -f /tmp/ollama-$USER.tgz
fi
OLLAMA="$OLLAMA_DIR/bin/ollama"
echo "ollama: $("$OLLAMA" --version 2>&1 | tail -n 1)"

# 4. Pull models (CPU-only server on the login node, download only) and verify IDs.
mkdir -p "$OLLAMA_MODELS"
"$OLLAMA" serve > slurm/logs/ollama-setup.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for _ in $(seq 30); do curl -sf "http://$OLLAMA_HOST/api/version" > /dev/null && break; sleep 1; done
mismatch=0
while read -r tag id; do
    [[ -z "$tag" || "$tag" == \#* ]] && continue
    "$OLLAMA" pull "$tag" > /dev/null < /dev/null
    got=$("$OLLAMA" list < /dev/null | awk -v t="$tag" '$1 == t {print $2}')
    if [ "$got" = "$id" ]; then echo "ok        $tag $got"; else echo "MISMATCH  $tag got $got, want $id"; mismatch=1; fi
done < slurm/models.txt
exit $mismatch
