# AutoTune

**Closed-loop, evidence-gated optimization for LLM inference.**

AutoTune runs *campaigns*: bounded, reproducible searches for the best sustainable inference performance a given model can reach on a given runtime. Every change is measured against a baseline, every measurement is preserved as evidence, and only changes that improve throughput **without breaking correctness** are promoted.

It is not a one-model tuning script. A campaign declares its own model, workload, runtime, quality gates, and budget — the evaluate-and-promote loop stays the same.

## Why

Tuning LLM inference today is mostly ad-hoc: try a flag, eyeball a benchmark number, keep it if it looks faster. AutoTune replaces that with a controlled experiment loop:

- **Reproducible** — every attempt records its exact environment, commands, and source revisions.
- **Bounded** — campaigns run under explicit time, cost, and attempt budgets; no unbounded search.
- **Honest** — results are only comparable within a campaign's declared workload and measurement protocol.
- **Safe** — candidates are reversible, isolated from `main`, and gated by deterministic correctness and comparison checks before they can become the new baseline.

## How a campaign works

```
            ┌──────────────────────────────────────────────────┐
            │                Campaign Contract                 │
            │  model · target runtime · evaluation · budget    │
            └───────────────────────┬──────────────────────────┘
                                    ▼
   ┌─────────┐   candidate   ┌───────────┐   metrics    ┌──────────────┐
   │ Decide  ├──────────────►│ Evaluate  ├─────────────►│   Evidence   │
   │ (budget)│               │  attempt  │              │    Bundle    │
   └────▲────┘               └───────────┘              └──────┬───────┘
        │ stop / continue                                      ▼
        │                                              ┌──────────────┐
        └──────────────────────────────────────────────┤   Promote    │
                    promote · retain · learn           │ (gated)      │
                                                       └──────────────┘
```

1. **Validate** the campaign contract and initialize the model dossier.
2. **Decide** the next candidate — one bounded, reversible intervention chosen from the technique catalog, or stop when the budget is exhausted.
3. **Evaluate** the candidate against the incumbent using the campaign's benchmark profile.
4. **Record** the outcome as an immutable evidence bundle (inputs, environment, commands, metrics or failure).
5. **Promote** the candidate to incumbent only if correctness passed and measured decode throughput strictly improved; otherwise retain the incumbent and learn from the result.

## Core concepts

| Concept | Meaning |
| --- | --- |
| **Campaign** | One bounded search for the best sustainable result for a declared model, workload, runtime, and budget |
| **Campaign contract** | The validated declaration of model, target runtime, evaluation profile, correctness requirements, comparison rule, and budget |
| **Model dossier** | Versioned record of model architecture and runtime facts that constrain candidate selection |
| **Technique catalog** | Candidate techniques a campaign may consider, each with a lane, preconditions, and provenance |
| **Candidate** | One reversible intervention evaluated against the current incumbent |
| **Attempt** | One execution of a baseline or candidate evaluation |
| **Evidence bundle** | Immutable record of an attempt: inputs, environment, commands, metrics, artifacts, failures |
| **Incumbent** | The best configuration that has passed the promotion rule so far |
| **Promotion** | The evidence-gated act of making a candidate the new incumbent |

## First campaign

| Component | Choice |
| --- | --- |
| Accelerator | AMD MI300X (`gfx942`, 304 compute units) |
| Serving stack | ATOM / vLLM-ROCm |
| Kernel library | aiter (Triton and CK/FlyDSL paths) |
| Model | `openai/gpt-oss-120b` |
| Objective | Repeatable decode-throughput frontier |

Depending on campaign evidence, the search space includes serving strategies (speculative decoding, draft models), batching and parallelism configuration, environment and dependency combinations, and profile-guided kernel or source changes.

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/ProgMastermind/AutoTune.git
cd AutoTune
pip install -e .
```

## Quickstart

A campaign starts as a JSON manifest:

```json
{
  "campaign_id": "gpt-oss-120b-mi300x",
  "model": {
    "id": "openai/gpt-oss-120b",
    "architecture": "gpt-oss"
  },
  "target": {
    "accelerator": "AMD MI300X",
    "gpu_arch": "gfx942",
    "compute_units": 304,
    "serving_engine": "atom",
    "kernel_library": "aiter"
  },
  "evaluation": {
    "primary_profile": {
      "benchmark_id": "decode-throughput",
      "repeat_count": 3
    }
  },
  "budget": {
    "max_attempts": 10
  }
}
```

Then drive the loop with the campaign CLI:

```bash
# 1. Validate the contract
python -m autotune campaign validate manifest.json

# 2. Initialize the model dossier
python -m autotune campaign dossier initialize manifest.json dossier.json

# 3. Register a technique the campaign may evaluate
python -m autotune campaign dossier add-technique dossier.json technique.json

# 4. Ask the budget governor what to do next
python -m autotune campaign decide manifest.json dossier.json history.json decision.json

# 5. Turn a completed (or failed) attempt into an evidence bundle
python -m autotune campaign evaluate manifest.json scenario.json evidence.json

# 6. Compare candidate evidence against the incumbent
python -m autotune campaign promote incumbent.json candidate.json promotion.json
```

Every command validates its inputs and exits non-zero with specific errors on invalid contracts, scenarios, or evidence — bad data never becomes evidence.

## Promotion rule

A candidate becomes the incumbent only when **all** of the following hold:

1. Its attempt completed successfully.
2. Deterministic correctness checks passed.
3. Measured `decode_tokens_per_second` is strictly greater than the incumbent's.

Otherwise the incumbent is retained and the reason is recorded. Reverting a regression is a first-class outcome, not a failure.

## Safety model

- Experiments never mutate `main`; source and dependency candidates start from pinned revisions on isolated branches.
- Dependency changes are pinned to exact versions or commits.
- Before promotion, candidates pass diff-policy checks, secret scanning, build and smoke checks, correctness checks, evidence validation, and replay verification.
- AutoTune never automates model-weight uploads, binaries, secrets, permission changes, or unreviewed workflow changes.

## Agentic architecture

AutoTune separates **advice** from **authority**. LLM agents research and propose; deterministic controls own execution, measurement, and promotion:

| Role | Responsibility | Authority |
| --- | --- | --- |
| Research triage | High-volume fact extraction from papers, issues, profiles, logs | Advisory only |
| Research synthesis | Combine dossier + history into evidence-backed findings | Advisory only |
| Candidate design | Propose one bounded, reversible intervention | Proposal only |
| Policy critic | Challenge unsafe assumptions and budget risk | Advisory only |
| Failure triage | Classify failed attempts, advise on retry safety | Advisory only |
| Code-change proposal | Draft minimal patches for verified bottlenecks | Draft patch only |

An agent can never execute a change, write evidence, or promote an incumbent. See [`docs/agentic-architecture.md`](docs/agentic-architecture.md) for the full authority boundary.

To enable the OpenAI-backed advisory executor, copy `.env.example` to `.env` and set `OPENAI_API_KEY`. Credentials stay local and are never written into manifests, evidence bundles, or source files.

## Project layout

```
config/    Agent role map (models, purposes, authority levels)
docs/      Architecture documentation
src/autotune/  Campaign CLI and core logic
tests/     Test suite (fake providers; no GPU required)
ralph/     Development automation scripts
```

## Status

The campaign core — contract validation, dossier management, budgeted decisions, evidence bundles, and gated promotion — is implemented and tested. Remote GPU provisioning, the ATOM baseline, and live agent execution are under active development. AutoTune does not yet claim a performance gain; the first campaign will publish its baseline and evidence when it runs.

## Contributing

Issues are used to track campaign work. Bug reports and discussion are welcome — please open an issue describing the campaign context if applicable.
