# Evaluation protocol

## Fixed tasks and information

Use the task files without changing frequency bands, angles, azimuth, polarization selection, material/topology allowlists, parameter bounds, Initial parameters, or goals. `splits.json` assigns eight development, four validation and 24 test tasks. Freeze the agent after validation. During a test task, the agent may receive that task's public definition, its Initial evaluation, and its own previous proposals and permitted feedback. Do not feed another test task's outcomes into a supposedly frozen agent.

The five-proposal budget limits expensive new physical designs; it does not mandate a particular candidate generator, physics prior, language model, or prompt. Report those choices, their computation budgets, random seeds, feedback policy and any extra surrogate/training data. Neither AbsorbEvo-specific guidance nor its trained Skill text is included here.

## Coverage and success

For each incidence angle and incident polarization p, compute power-normalized two-mode reflection:

```text
R_p(f) = |r_co,p(f)|² + |r_cross,p(f)|²
RL_p(f) = 10 log10 R_p(f)
A_p(f) = 1 - R_p(f)        (PEC backing, zero transmission)
```

Co- and cross-polarized coefficients refer to the two registered reflected modes, TE00 and TM00. Solve/export both incident polarizations even for a TE-only or TM-only task. Do not replace this definition with co-polarized reflection alone, a polarization average of amplitudes, or a worst-angle metric.

On the target frequency band, an interval between adjacent samples contributes its full width **only when both endpoint reflection powers are at or below** `10^(RL_threshold_dB/10)`. Divide the sum of qualified widths by the target bandwidth. This conservative endpoint rule matches the frozen benchmark evaluator; it does not linearly interpolate threshold crossings or count qualified samples. The target-band endpoints must be present. Average the resulting coverage equally across the prescribed angles and selected incident polarizations.

A new proposal succeeds only when the physical evidence is valid, the task contract is unchanged, and its mean coverage is at least `required_coverage` (inclusive). A case below the goal can still be physically valid.

## Physical evidence

The public scoring interface requires:

- a legal design with every active parameter present and all fixed settings unchanged;
- a fresh simulation project for each design × angle;
- a confirmed converged solve, a nonempty solver log and a complete export;
- finite complex co/cross reflection coefficients for TE and TM on the declared grid;
- two-mode reflected power no greater than **1.005**, checked over the full 2–18 GHz grid for both polarizations.

The scorer computes the spectral checks and records file hashes. Solver convergence, correct port assignment, geometry, material configuration and freshness are runner attestations and must be supported by saved evidence. True flags alone are not independent proof. The two-mode check is not a claim that all higher Floquet orders or an independent field-energy balance have been verified. State any additional diagnostics separately.

## Five proposals, failures and retries

Evaluate the supplied Initial as round 0 and preserve it unchanged for all compared agents. Its solve cost is reported separately. Rounds 1–5 are new proposal opportunities. For the standard complete trajectory, carry out all five, even after an early success. If using early stopping, label that protocol variant explicitly.

An invalid scientific proposal consumes its opportunity and is recorded as `invalid_proposal`; it is not replaced with a more favorable proposal under the same round number. A solver/license/export interruption is `infrastructure_failure`, with coverage and success left null. It is unresolved and is not a scientific failure. Invalid physical evidence is likewise unresolved until checked and resolved.

For the retry-compatible profile, allow at most **10 total physical attempts per design × angle, including the first**, with identical scientific input and a fresh project. Stop immediately after success. Count earlier attempts toward the cap; never start an eleventh. Shared license or execution-chain failures should pause the affected scope. After exhaustion, isolate the task trajectory, continue independent tasks and report the outstanding gap. Report attempts and retry policy separately from the five scientific opportunities. The original retry/isolation policy was an execution-stage amendment, not part of the initial experimental preregistration.

## Reported metrics

- **Task success rate:** fraction of tasks with at least one valid successful new proposal in rounds 1–5.
- **First-success round:** the smallest successful new-proposal index. Leave it null if no success was observed; do not assign a fictional sixth round.
- **Cumulative success:** number of tasks already successful by each round k=1,…,5.
- **Best valid coverage:** maximum valid coverage including Initial and available valid new proposals; keep null if the Initial needed for this definition was not evaluated.
- **Costs:** scientific proposals, design × angle evaluations, physical attempts/retries, model/auxiliary calls and wall time, reported separately.

Report the test set as complete only when all 120 new-proposal opportunities have scientifically terminal outcomes. The summary tool leaves the headline success rate null for an incomplete split. Its cumulative counts in that case are observed counts, not a complete-benchmark estimate. Results from different solvers or changed task definitions need a clearly identified protocol variant.

The benchmark includes no reference method scores. Do not infer expected success from task metadata, geometry mappings, or the synthetic unit tests.
