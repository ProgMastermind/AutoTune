# Agentic architecture

AutoTune separates **advice** from **authority**. GPT agents may inspect and
propose; deterministic controls own execution, measurement, promotion, and
remote cleanup.

## Roles

- **Research triage — GPT-5.6 Luna:** inexpensive high-volume extraction from
  papers, upstream issues, repository docs, profiler summaries, and run logs.
- **Research synthesis — GPT-5.6 Terra:** combines those facts with the Model
  Dossier and experiment history; marks claims as observed, inferred, or
  unknown.
- **Candidate design — GPT-5.6 Terra:** returns exactly one bounded reversible
  intervention, preconditions, risk, estimated cost, and evaluation plan.
- **Policy critic — GPT-5.6 Terra:** challenges the proposed change before the
  Budget Governor authorizes an Attempt.
- **Failure triage — GPT-5.6 Luna:** converts failed remote runs into structured
  classifications and retry advice.
- **Code-change proposal — GPT-5.6 Terra:** drafts a minimal patch plan only
  after evidence supports a source-level lane. A separate deterministic branch
  manager applies allowed changes and tests them.

## Closed loop

1. The deterministic controller validates the Campaign Contract and loads the
   Dossier, Technique Catalog, history, and budget.
2. Luna gathers source-linked facts; Terra synthesizes them into an advisory
   Research Packet.
3. Terra proposes one Candidate. The policy critic reviews it.
4. The Budget Governor independently accepts or rejects the request.
5. The executor runs the approved Candidate, then writes its Evidence Bundle.
6. Failure triage classifies unsuccessful Attempts; the controller records the
   result in history.
7. Deterministic correctness, comparison, evidence, and replay gates decide
   Promotion. An agent cannot promote an Incumbent.

## Local credentials

Copy `.env.example` to `.env` in the AutoTune checkout and set
`OPENAI_API_KEY`. `.env` is ignored by Git. Do not place an API key in a
campaign manifest, Evidence Bundle, issue, prompt, or source file.

The current router builds serializable role requests without sending them. The
next executor slice will call the OpenAI Responses API only when explicitly
enabled and will redact credentials from all evidence.
