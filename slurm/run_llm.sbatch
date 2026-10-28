#!/bin/bash
#SBATCH --job-name=goc-llm
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=slurm/logs/%x-%j.out
#
# All 3 models x 2 strategies on one set, one after another, on one GPU.
# Submit from the repo root (after slurm/carc_setup.sh):
#   sbatch --account=<project_id> slurm/run_llm.sbatch [dev|test_a|test_b]
# Use the same GPU type for every set; to use an A40 instead, add --gres=gpu:a40:1.
# Resumable: resubmitting skips ROW_IDs that already have an error-free prediction.
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"

SET="${1:-dev}"
OLLAMA_VERSION=0.40.12
OLLAMA="$HOME/.local/ollama-$OLLAMA_VERSION/bin/ollama"
export OLLAMA_MODELS="/scratch1/$USER/ollama-models"
export OLLAMA_HOST="127.0.0.1:$((20000 + SLURM_JOB_ID % 10000))"  # avoid clashes on shared nodes
export OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1

echo "job $SLURM_JOB_ID on $(hostname), set=$SET"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

"$OLLAMA" serve > "slurm/logs/ollama-$SLURM_JOB_ID.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for _ in $(seq 60); do curl -sf "http://$OLLAMA_HOST/api/version" > /dev/null && break; sleep 2; done
curl -sf "http://$OLLAMA_HOST/api/version" > /dev/null || { echo "ollama server did not start"; exit 1; }

# Refuse to run if a model differs from the one used locally.
while read -r tag id; do
    [[ -z "$tag" || "$tag" == \#* ]] && continue
    got=$("$OLLAMA" list < /dev/null | awk -v t="$tag" '$1 == t {print $2}')
    [ "$got" = "$id" ] || { echo "model $tag is ${got:-missing}, want $id"; exit 1; }
done < slurm/models.txt

status=0
for model in llama3.1:8b qwen3:8b gemma3:4b; do
    for strategy in zero_shot few_shot; do
        .venv/bin/python -m src.llm.run --model "$model" --strategy "$strategy" --set "$SET" \
            --host "http://$OLLAMA_HOST" || status=1
    done
done
nvidia-smi --query-gpu=name,temperature.gpu,power.draw --format=csv,noheader
exit $status
