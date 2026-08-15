# AutoTune domain glossary

## Campaign

A bounded search for the best sustainable inference result for one declared
model, workload, runtime envelope, and budget.

## Campaign contract

The complete, validated declaration of a Campaign's model, target runtime,
evaluation profile, correctness requirements, comparison rule, and budget.

## Candidate

One reversible intervention that a Campaign evaluates against its current
Incumbent.

## Incumbent

The best Campaign configuration that has passed its promotion rule so far.

## Evaluation profile

A named workload and measurement procedure used to compare a Candidate with an
Incumbent.

## Evidence bundle

The immutable record of an Attempt: inputs, environment, commands, metrics,
artifacts, and failure information.

## Promotion

The evidence-gated act of making a Candidate the Campaign's new Incumbent.
