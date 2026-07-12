# 2x2 Ordering and Repetition Effects

Runs:

- Qwen 2.5 32B: `results/20260710_175306_think_twice_trs-deepmath_oracle_openai-compatible_Qwen_Qwen2.5-32B-Instruct_k1-2-3-4-5-6`
- Mistral Small 3.1 24B: `results/20260710_221900_think_twice_trs-deepmath_oracle_openai-compatible_mistralai_Mistral-Small-3.1-24B-Instruct-2503_k1-2-3-4-5-6`

Each cell has `n=1000`.

## Qwen 2.5 32B

| Prompt order | x1 single | x2 repeated | Repetition effect |
|---|---:|---:|---:|
| insight-first `{i,q}` | 63.30% | 64.30% | +1.00 pp, p=0.468 ns |
| problem-first `{q,i}` | 66.00% | 65.50% | -0.50 pp, p=0.748 ns |
| order effect, problem-first minus insight-first | +2.70 pp, p=0.039 * | +1.20 pp, p=0.366 ns | |

Interaction: `+1.50 pp`.

## Mistral Small 3.1 24B

| Prompt order | x1 single | x2 repeated | Repetition effect |
|---|---:|---:|---:|
| insight-first `{i,q}` | 44.20% | 46.70% | +2.50 pp, p=0.133 ns |
| problem-first `{q,i}` | 44.80% | 47.10% | +2.30 pp, p=0.170 ns |
| order effect, problem-first minus insight-first | +0.60 pp, p=0.752 ns | +0.40 pp, p=0.846 ns | |

Interaction: `+0.20 pp`.

## Compact Comparison

| Model | Best 2x2 cell | Repetition, insight-first | Repetition, problem-first | Order, single | Order, repeated |
|---|---:|---:|---:|---:|---:|
| Qwen 2.5 32B | `{q,i}` at 66.00% | +1.00 pp ns | -0.50 pp ns | +2.70 pp * | +1.20 pp ns |
| Mistral Small 3.1 24B | `{q,i,sep,q,i}` at 47.10% | +2.50 pp ns | +2.30 pp ns | +0.60 pp ns | +0.40 pp ns |

McNemar tests are continuity corrected.
