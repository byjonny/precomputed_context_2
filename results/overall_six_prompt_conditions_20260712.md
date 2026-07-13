# Overall Six Prompt Conditions

Full runs only. Each condition has `n=1000`; percentages are accuracy. Errors are counted as wrong by the runner.

| Model | `{i,q}` insight-first | `{q,i}` problem-first | `{i,q,sep,i,q}` insight repeated | `{q,i,sep,q,i}` problem repeated | `{q}` problem only | `{q,sep,q}` problem-problem | Best | Errors |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| Qwen 2.5 7B | 44.80% | 50.10% | 48.70% | 53.30% | 42.50% | 43.00% | `{q,i,sep,q,i}` (53.30%) | 0 |
| Qwen 2.5 32B | 63.30% | 66.00% | 64.30% | 65.50% | 53.20% | 52.20% | `{q,i}` (66.00%) | 11 |
| Mistral Nemo 12B | 18.60% | 18.10% | 17.20% | 19.30% | 13.80% | 13.80% | `{q,i,sep,q,i}` (19.30%) | 0 |
| Mistral Small 3.1 24B | 44.20% | 44.80% | 46.70% | 47.10% | 33.20% | 34.00% | `{q,i,sep,q,i}` (47.10%) | 9 |

## Counts

| Model | `{i,q}` | `{q,i}` | `{i,q,sep,i,q}` | `{q,i,sep,q,i}` | `{q}` | `{q,sep,q}` |
|---|---:|---:|---:|---:|---:|---:|
| Qwen 2.5 7B | 448/1000 | 501/1000 | 487/1000 | 533/1000 | 425/1000 | 430/1000 |
| Qwen 2.5 32B | 633/1000 | 660/1000 | 643/1000 | 655/1000 | 532/1000 | 522/1000 |
| Mistral Nemo 12B | 186/1000 | 181/1000 | 172/1000 | 193/1000 | 138/1000 | 138/1000 |
| Mistral Small 3.1 24B | 442/1000 | 448/1000 | 467/1000 | 471/1000 | 332/1000 | 340/1000 |

## Run Directories

- Qwen 2.5 7B: `results/20260710_020210_think_twice_trs-deepmath_oracle_openai-compatible_Qwen_Qwen2.5-7B-Instruct_k1-2-3-4-5-6`
- Qwen 2.5 32B: `results/20260710_175306_think_twice_trs-deepmath_oracle_openai-compatible_Qwen_Qwen2.5-32B-Instruct_k1-2-3-4-5-6`
- Mistral Nemo 12B: `results/20260710_005059_think_twice_trs-deepmath_oracle_openai-compatible_mistralai_Mistral-Nemo-Instruct-2407_k1-2-3-4-5-6`
- Mistral Small 3.1 24B: `results/20260710_221900_think_twice_trs-deepmath_oracle_openai-compatible_mistralai_Mistral-Small-3.1-24B-Instruct-2503_k1-2-3-4-5-6`
