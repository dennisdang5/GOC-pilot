# Running the LLM pipeline on USC CARC (Discovery)

All LLM runs (dev, test_a, test_b, later silver) happen on CARC, on one GPU type (A100 by
default), with the same Ollama version and model IDs as the local machine (`slurm/models.txt`).
Predictions made on the local RTX 3070 are not mixed with CARC ones.

## Data handling (PhysioNet DUA)

- Before the first transfer, confirm with CARC support that credentialed, restricted-access data
  may be stored in a personal directory.
- Copy **only** the four files the runner needs. Never copy `raw/` or `parquet/`.
- Repo and `data/` live in your own home directory, owner-only (`chmod 700`, set by
  `carc_setup.sh`). Never put them in a shared `/project` directory.
- No note text is printed to job logs. Predictions (which include evidence spans) come back only
  to your own machine.

## One-time setup

```bash
# on Discovery login node (ssh <user>@discovery.usc.edu)
git clone git@github.com:dennisdang5/GOC-pilot.git ~/GOC-pilot
mkdir -p ~/GOC-pilot/data/derived && chmod 700 ~/GOC-pilot ~/GOC-pilot/data
```

```bash
# on your PC, from the repo root
scp data/derived/{candidates,dev_sample,test_sample,test_b_sample}.parquet \
    <user>@hpc-transfer1.usc.edu:GOC-pilot/data/derived/
```

```bash
# on Discovery, from ~/GOC-pilot
module avail python            # pick a 3.11+ module, e.g. module load python/3.12.x
bash slurm/carc_setup.sh       # all three models must print "ok"
```

## Run

```bash
sbatch --account=<project_id> slurm/run_llm.sbatch dev
squeue -u $USER
cat slurm/logs/goc-llm-<jobid>.out    # counts, latency, error types, ROW_IDs only
```

- Same as the local `run.py`: test sets are refused until `src/llm/prompts/FROZEN` exists, and
  resubmitting resumes.
- After changing prompts, `git pull` on CARC before submitting.
- Pass `--gres=gpu:a40:1` to use an A40, but use one GPU type for every set.

## Bring predictions back

```bash
# on your PC, from the repo root (move any old local predictions aside first)
scp -r <user>@hpc-transfer1.usc.edu:GOC-pilot/data/predictions data/
```
