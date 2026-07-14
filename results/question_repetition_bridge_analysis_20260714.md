# Question Repetition Bridge Analysis

## Scope

Models:

- Qwen 2.5 7B
- Mistral Small 3.1 24B

New bridge conditions (`n=1,000` matched questions per condition):

| Condition | Recipe | Interpretation |
|---|---|---|
| C1 | `{q,i}` | problem-first replication control |
| C2 | `{q,i,sep,q}` | repeat question after the insight |
| C3 | `{q,sep,q,i}` | repeat question before the insight |
| C4 | `{i,q}` | insight-first replication control |

All 8,000 new calls completed. The Qwen run had zero errors. The Mistral run had zero new errors; its old six-condition run had nine saved errors across 6,000 calls. Excluding the three old errors relevant to `{q,i}` versus `{q,i,sep,q,i}` changes that effect only from +2.30 pp to +2.21 pp.

## 1. Plausibility and replication

The old and new runs contain exactly the same 1,000 question IDs. For both repeated controls, all 1,000 prompt hashes match, so the actual prompt text is identical across runs.

| Model | Control | Old | New | New - old | Paired 95% CI | McNemar p | Correctness agreement |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen 2.5 7B | `{q,i}` | 50.1% | 50.9% | +0.8 pp | [-2.31, +3.91] | .659 | 74.8% |
| Mistral Small 24B | `{q,i}` | 44.8% | 44.4% | -0.4 pp | [-3.49, +2.69] | .849 | 75.2% |
| Qwen 2.5 7B | `{i,q}` | 44.8% | 46.1% | +1.3 pp | [-1.78, +4.38] | .445 | 75.3% |
| Mistral Small 24B | `{i,q}` | 44.2% | 43.5% | -0.7 pp | [-3.84, +2.44] | .708 | 74.3% |

Conclusion: the aggregate accuracies replicate well and none differs significantly from its old value. They are not identical item by item, which is expected at `temperature=0.7`. The normalized predicted answer matches across runs for 47.1% of Qwen `{q,i}` calls and 41.6% of Mistral `{q,i}` calls.

One caveat is backend drift for Qwen: despite identical prompt hashes, mean completion length for `{q,i}` increased from 675.1 to 759.6 tokens. Mistral changed only from 601.0 to 615.8 tokens. Accuracy nevertheless remained stable.

## 2. New condition accuracies

| Model | C1 `{q,i}` | C2 `{q,i|q}` | C3 `{q|q,i}` | C4 `{i,q}` |
|---|---:|---:|---:|---:|
| Qwen 2.5 7B | 50.9% | 51.0% | 51.2% | 46.1% |
| Mistral Small 24B | 44.4% | 44.7% | 44.3% | 43.5% |

## 3. Does question repetition itself help?

| Model | Contrast | Effect | Paired 95% CI | McNemar p |
|---|---|---:|---:|---:|
| Qwen 2.5 7B | C2-C1: append second question | +0.1 pp | [-3.06, +3.26] | 1.000 |
| Qwen 2.5 7B | C3-C1: add earlier question | +0.3 pp | [-2.79, +3.39] | .899 |
| Qwen 2.5 7B | C3-C2: position of one insight | +0.2 pp | [-2.72, +3.12] | .947 |
| Mistral Small 24B | C2-C1: append second question | +0.3 pp | [-2.79, +3.39] | .899 |
| Mistral Small 24B | C3-C1: add earlier question | -0.1 pp | [-3.29, +3.09] | 1.000 |
| Mistral Small 24B | C3-C2: position of one insight | -0.4 pp | [-3.53, +2.73] | .851 |

Under an exploratory +/-3 pp equivalence margin, both question-repetition contrasts (C2-C1 and C3-C1) are equivalent to zero for both models using paired 90% CIs. The data are not precise enough to establish equivalence under a tighter +/-2 pp margin.

Conclusion: repeating only the question has no measurable effect here, and moving the single insight from the first to the second question copy also has no measurable effect.

## 4. Does the second insight explain the old full-repetition gain?

The old complete condition was `{q,i,sep,q,i}`. Its within-run effect relative to `{q,i}` was:

| Model | Old `{q,i}` | Old `{q,i|q,i}` | Full effect | Paired 95% CI | McNemar p |
|---|---:|---:|---:|---:|---:|
| Qwen 2.5 7B | 50.1% | 53.3% | +3.2 pp | [+0.30, +6.10] | .037 |
| Mistral Small 24B | 44.8% | 47.1% | +2.3 pp | [-0.84, +5.44] | .170 |

Using the repeated `{q,i}` condition as a bridge, the difference-in-differences is:

`(old full repetition - old {q,i}) - (new question repetition - new {q,i})`

| Model | Versus C2 `{q,i|q}` | Versus C3 `{q|q,i}` | Versus average(C2,C3) |
|---|---:|---:|---:|
| Qwen 2.5 7B | +3.1 pp | +2.9 pp | +3.0 pp, 95% CI [-0.99, +6.99], p=.141 |
| Mistral Small 24B | +2.0 pp | +2.4 pp | +2.2 pp, 95% CI [-2.01, +6.41], p=.305 |
| Pooled, conditional on these models | +2.55 pp | +2.65 pp | +2.6 pp, 95% CI [-0.30, +5.50], p=.079 |

Conclusion: the point estimates consistently indicate approximately 2-3 pp of additional value from the second insight or from repeating the complete `{q,i}` pair. The individual uncertainty intervals still include zero, and the full condition came from an earlier run. Therefore this is suggestive rather than decisive. It does not support the claim that question repetition alone explains the earlier gain, and it cannot establish that the second insight has no effect.

## 5. Embedded `{q,i}` pattern hypothesis

The exact proposed pattern was:

`Accuracy({q,i}) ~= Accuracy({i,q|i}) ~= Accuracy({i,q|i,q}) > Accuracy({i,q})`

No completed run contains `{i,q,sep,i}`. Therefore the full hypothesis cannot yet be tested.

Partial evidence:

| Model | Comparison | Effect | Paired 95% CI | p |
|---|---|---:|---:|---:|
| Qwen 2.5 7B, new | `{q,i}` minus `{i,q}` | +4.8 pp | [+1.68, +7.92] | .003 |
| Qwen 2.5 7B, old | `{i,q|i,q}` minus `{i,q}` | +3.9 pp | [+0.90, +6.90] | .013 |
| Qwen 2.5 7B, old | `{i,q|i,q}` minus `{q,i}` | -1.4 pp | [-4.56, +1.76] | .420 |
| Mistral Small 24B, new | `{q,i}` minus `{i,q}` | +0.9 pp | [-2.07, +3.87] | .597 |
| Mistral Small 24B, old | `{i,q|i,q}` minus `{i,q}` | +2.5 pp | [-0.63, +5.63] | .133 |
| Mistral Small 24B, old | `{i,q|i,q}` minus `{q,i}` | +1.9 pp | [-1.15, +4.95] | .248 |

Across the old and new control runs, the averaged order effect `{q,i}-{i,q}` is +5.05 pp for Qwen (95% CI [+2.80, +7.30], p<.001) but only +0.75 pp for Mistral (95% CI [-1.34, +2.84], p=.482).

Conclusion: Qwen shows the predicted partial pattern `{q,i} ~= {i,q|i,q} > {i,q}`. Mistral does not provide clear evidence for it. The missing `{i,q|i}` condition is necessary before making the proposed mechanism claim.

## Overall conclusion

1. The old `{q,i}` and `{i,q}` controls replicate plausibly at the aggregate level.
2. Repeating only the question produces essentially zero effect in both models.
3. The previous full-pair repetition gain is larger than the new question-only repetition gain by about 2-3 pp, although the cross-run estimate remains imprecise.
4. The results therefore argue against "question repetition alone" as the explanation.
5. The embedded `{q,i}` explanation is supported for Qwen only at a partial level and remains untestable as stated because `{i,q,sep,i}` is missing.

All confidence intervals are paired at the question level. McNemar p-values use the continuity-corrected test; errors are counted as wrong, matching the runner's saved aggregates.
