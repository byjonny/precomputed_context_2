# TRS Repetition Experiment Plan

## Goal

Measure the repetition effect only:

> If a problem is given the right/relevant insight, does repeating that same insight `k` times improve accuracy or token efficiency?

We vary only:

```text
k = 0, 1, 2, 3, 5
```

Everything else stays fixed: same question, same model, same decoding settings, same insight text, same answer checker.

## Links

- TRS paper: https://arxiv.org/abs/2604.21764
- TRS dataset: https://huggingface.co/datasets/stallone0000/Reasoning-Skill
- TRS code: https://github.com/stallone0000/Reasoning-Skill

## Downloaded TRS Data

Downloaded locally into:

```text
work/trs_data/
```

Downloaded files:

```text
README.md
schema.json
source_files.jsonl
skill_datasets.json
deepmath_103k_oss_skill_corpus.jsonl.gz
aops_skill_corpus.jsonl.gz
benchmark_correct_cot_skill_corpus.jsonl.gz
benchmark_error_priority_skill_corpus.jsonl.gz
trs_skill_corpus.jsonl
```

I did not download the coding archive because this experiment is math-focused.

Important dataset finding:

```text
DeepMath file: 103,020 rows, clean short answers in almost all rows.
AoPS file: 7,735 rows, many answers are full worked solutions with boxed final answers.
TRS mixed file: 10,476 rows, mostly clean short answers.
```

Recommended primary dataset:

```text
deepmath_103k_oss_skill_corpus.jsonl.gz
```

because it already has:

```text
question
answer
skill_text
topic
difficulty
```

and the `answer` column is mostly clean.

## Important Caveat

The Hugging Face TRS package is a skill-card release, not the raw paper evaluation split. Its README says it excludes raw benchmark datasets.

So we should not claim we reproduce the exact TRS paper evaluation. We are using the released skill-card data to run a new controlled repetition experiment.

## Experimental Designs

### Main Design: Oracle Right-Insight Repetition

Use the same row's `skill_text` as the insight for that row's question.

This directly tests:

```text
Given a correct/relevant insight for this problem, does repeating it help?
```

Pipeline:

1. Load DeepMath rows.
2. Filter rows with non-empty `question`, `answer`, and `skill_text`.
3. Optionally remove rows where `skill_text` directly contains the exact answer.
4. For each row, create prompts with:
   - `k = 0`: no insight
   - `k = 1`: skill once
   - `k = 2`: same skill twice
   - `k = 3`: same skill three times
   - `k = 5`: same skill five times
5. Run the same model on all variants.
6. Extract final answer.
7. Compare to gold answer.
8. Store per-question results.

This is the cleanest test for "right insight repetition."

Limitation:

```text
It is oracle-style because the skill was distilled from that same solved problem.
```

So the claim should be:

```text
Conditional on having the right insight, repetition helps/saturates/hurts.
```

not:

```text
Retrieval in TRS improves because repetition helps.
```

### Secondary Design: TRS-Style Retrieved Insight Repetition

Use a separate skill library and retrieve one skill for each eval question.

Pipeline:

1. Split DeepMath rows into:
   - skill library
   - held-out eval questions
2. Build BM25 over library keys:
   - `question`
   - optionally `topic`
   - optionally `skill_text`
3. For each held-out question, retrieve top-1 skill from a different row.
4. Keep that retrieved skill fixed.
5. Repeat it `k = 0, 1, 2, 3, 5`.
6. Evaluate the same way.

This tests repetition in a more realistic TRS setting.

Limitation:

```text
Now retrieval quality becomes a confound.
```

So this should be a robustness check, not the clean main experiment.

## Prompt Template

Use the released TRS shape, but make repetition explicit.

Baseline:

```text
You are a helpful and harmless assistant.
Let's think step by step:

Problem:
{question}
```

Insight prompt:

```text
You are a helpful and harmless assistant.
You may be given a Solving Hints section. Use it only if relevant; otherwise ignore it.
If useful, try to solve correctly with fewer tokens.

[Solving Hints]
{repeated_skill_text}
[/Solving Hints]

Problem:
{question}
```

For repetition:

```text
{repeated_skill_text} = skill_text repeated k times
```

Use a delimiter between repetitions:

```text
--- same hint repeated ---
```

This keeps the intervention visible and easy to audit.

## Answer Checking

For DeepMath:

1. Extract final model answer from:
   - last `\boxed{...}`
   - `Final answer: ...`
   - `Answer: ...`
   - fallback: last non-empty line
2. Normalize:
   - lowercase
   - remove `$`, `\(`, `\)`, `\boxed{}`, spaces
   - strip trailing punctuation
3. Exact-match with the `answer` field.

For AoPS optional:

1. Extract gold answer from the row's `answer` field first.
2. Prefer last `\boxed{...}`.
3. For multiple choice, canonicalize to `(A)` / `A`.
4. Then compare model output to the extracted gold.

## Per-Item Evaluation

Store one row per question, with all conditions side-by-side:

```text
question_id
topic
difficulty
gold_answer
skill_text_hash
correct_k0
correct_k1
correct_k2
correct_k3
correct_k5
output_tokens_k0
output_tokens_k1
output_tokens_k2
output_tokens_k3
output_tokens_k5
prompt_tokens_k0
prompt_tokens_k1
prompt_tokens_k2
prompt_tokens_k3
prompt_tokens_k5
predicted_answer_k0
predicted_answer_k1
predicted_answer_k2
predicted_answer_k3
predicted_answer_k5
```

Then derive per-item transition labels:

```text
improved_by_repetition: k0 wrong, any k>0 correct
hurt_by_repetition: k0 correct, any k>0 wrong
stable_correct: all or most variants correct
stable_wrong: all variants wrong
best_k: smallest k with correct answer and lowest output tokens
```

For direct repetition effects:

```text
delta_correct_k2_vs_k1 = correct_k2 - correct_k1
delta_correct_k3_vs_k1 = correct_k3 - correct_k1
delta_correct_k5_vs_k1 = correct_k5 - correct_k1
delta_output_tokens_k2_vs_k1 = tokens_k2 - tokens_k1
```

This lets us ask:

```text
Did repeating the same insight improve this exact question?
Did it make the model more verbose?
Did it preserve correctness with fewer output tokens?
```

## Overall Evaluation

Report aggregate scores by condition:

```text
accuracy@k
mean output tokens@k
mean prompt tokens@k
mean total tokens@k
estimated cost@k
```

Key comparisons:

```text
k=0 vs k=1: insight effect
k=1 vs k=2/3/5: pure repetition effect
```

The central result should be:

```text
Does accuracy go up/down from k=1 to higher k?
Does output token count go down/up from k=1 to higher k?
Does total cost increase because prompt repetition dominates?
```

Recommended tables:

1. Overall accuracy and token table.
2. Per-item transition counts.
3. Topic/difficulty breakdown.
4. Win/loss table for repetition:

```text
k comparison | improved items | hurt items | unchanged items | net accuracy delta | token delta
1 -> 2
1 -> 3
1 -> 5
```

## Statistical Checks

Because the same questions are tested under every `k`, use paired comparisons:

```text
McNemar test for accuracy changes
paired bootstrap confidence intervals for accuracy delta
paired bootstrap confidence intervals for token delta
```

This is better than comparing two independent averages.

## What Has To Be Added

The TRS dataset gives us:

```text
question
answer
skill_text
topic/difficulty metadata
```

We still need to add:

1. Data loader for JSONL/GZ.
2. Filters for clean rows.
3. Optional leakage filter: remove rows where `skill_text` contains the gold answer.
4. Prompt builder for `k = 0, 1, 2, 3, 5`.
5. Model runner.
6. Answer extractor.
7. Exact-match normalizer.
8. Token/cost logger.
9. Per-question result table.
10. Aggregate report generator.
11. Optional BM25 retriever for the realistic TRS-style condition.

## Recommended First Implementation

Start small:

```text
Dataset: DeepMath
Sample: 500 or 1,000 rows
Design: oracle right-insight repetition
k values: 0, 1, 2, 3, 5
Model: one fixed model
Temperature: 0 or low
Repeats: 1 initially, then 3 if budget allows
```

Then expand:

```text
Run 5,000+ DeepMath rows.
Add topic/difficulty analysis.
Add retrieved-skill condition.
Add AoPS multiple-choice robustness check.
```

## Minimal Success Criterion

The experiment is successful if we can answer:

```text
Among questions where k=1 is correct, does k>1 stay correct and reduce output tokens?
Among questions where k=1 is wrong, does repetition rescue any items?
How often does repetition hurt?
Is the net effect worth the extra prompt tokens?
```

That directly isolates the repetition effect.
