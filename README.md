# AutoTune

AutoTune is a closed-loop optimization platform for LLM inference. It runs an
optimization **campaign**: establish a reproducible baseline, choose one
bounded change, test it, preserve the evidence, and keep only changes that
improve the campaign's measured result without breaking correctness or the
campaign budget.

The first campaign targets `openai/gpt-oss-120b` on AMD MI300X GPUs using the
ATOM serving engine and the aiter kernel library. AutoTune is intentionally
not a one-model tuning script. Later campaigns will describe their own model,
workload, runtime, and limits while using the same evaluation and promotion
loop.

## What AutoTune optimizes

There is no predeclared throughput target. A campaign searches for the best
**sustainable** result it can find within its explicit time, cost, attempt, and
quality budget.

The search is system-wide. Depending on the campaign evidence, it can evaluate:

- serving strategies such as speculative decoding and draft models;
- batching, parallelism, and engine configuration;
- environment, dependency, and upstream-version combinations;
- profile-guided kernel, dispatch, and source changes.

Profiling is an important source of evidence, but it is not the only source of
ideas. The model architecture, known runtime compatibility, experiment history,
and relevant upstream improvements also inform the next candidate.

## Initial operating envelope

| Component | Initial choice |
| --- | --- |
| Accelerator | AMD MI300X, `gfx942`, 304 compute units |
| Serving stack | ATOM / vLLM-ROCm |
| Kernel library | aiter (Triton and CK/FlyDSL paths) |
| First model | `openai/gpt-oss-120b` |
| Primary objective | Attainable, repeatable decode-throughput frontier |

The platform records the exact workload, quality gates, measurement protocol,
and comparison rule in each campaign. A result is therefore meaningful only in
the context of its campaign contract.

## How a campaign works

1. Validate a campaign contract and model dossier.
2. Create a baseline run with complete environment and benchmark provenance.
3. Select one candidate intervention from a bounded policy.
4. Provision and run the required environment, benchmark, and optional profile.
5. Store metrics, artifacts, failures, source revisions, and decisions as an
   evidence bundle.
6. Compare the candidate with the incumbent using the campaign's promotion
   rule.
7. Promote, revert, or learn from the outcome, then continue until budget or
   stop rules are reached.

## Safety and promotion

Experiments never mutate `main`. A source or dependency candidate begins from
a pinned revision on an isolated `candidate/<campaign>/<candidate-id>` branch.
Dependency changes are pinned to exact versions or commits.

Before a candidate can become an incumbent, it must pass allowed-path and diff
policy checks, secret scanning, build and smoke checks, deterministic
correctness checks, the campaign evaluation contract, evidence validation, and
replay verification. Source changes are proposed as draft pull requests with
their provenance and benchmark comparison. Reversions are first-class
candidates.

AutoTune never automates model-weight uploads, binaries, secrets, permission
changes, or unreviewed workflow changes.

## Delivery roadmap

The first implementation sequence is deliberately vertical: campaign
validation, model dossier, deterministic evaluation/evidence, budgeted decision
loop, RunPod execution, an ATOM baseline, serving-strategy candidates,
profile-guided source candidates, and evidence-gated promotion.

Each ticket is implemented in a separate fresh Codex execution using
test-driven development. The public test seam is the campaign command: local
tests use fake providers, while production campaigns use real RunPod and ATOM
adapters.

## Codex ticket runner

The `ralph/` scripts turn a ready-for-agent GitHub issue into one fresh,
non-interactive Codex run. They never reuse a previous agent session.

```bash
# Run one specific ticket from the AutoTune checkout.
ralph/once.sh 13

# Run up to five currently open ready-for-agent tickets, one process each.
ralph/afk.sh 5
```

`once.sh` can read public issue data with `curl` and `jq`; authenticated GitHub
CLI access is required to comment on and close a completed ticket. `afk.sh`
requires authenticated GitHub CLI access because it selects and closes tickets.
Both scripts require an authenticated Codex CLI. Use `AUTOTUNE_REPO_DIR` when
invoking a copied runner from outside the AutoTune checkout.

## Advisory agent roles

AutoTune uses agents to research and propose, never to bypass execution or
promotion gates. Copy `.env.example` to a local `.env` and set
`OPENAI_API_KEY` when enabling the OpenAI-backed advisory executor. The tracked
role map sends high-volume fact extraction and failure triage to GPT-5.6 Luna;
GPT-5.6 Terra handles research synthesis, candidate design, policy criticism,
and code-change proposals. See `docs/agentic-architecture.md` for the complete
authority boundary and loop.

## Status

The repository currently contains the platform definition and is being built
from the campaign contract outward. It does not yet provision GPUs, run ATOM,
or claim a performance gain.
