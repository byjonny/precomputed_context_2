# Insight Repetition Experiments

This project tests one narrow scientific question:

> If a problem already has a useful reasoning insight, does repeating the same insight improve accuracy or token efficiency?

The code is generic: datasets, evaluators, LLM providers, and retrieval modes are separate modules. TRS data is the first implementation, but new data sources can be added without changing the experiment runner.

## Project Layout

```text
src/insights_repetition/
  cli.py                 # command line entrypoint
  experiment.py          # main experiment loop
  prompts.py             # direct and repeated-hint prompt builders
  answer_extraction.py   # boxed/final-answer extraction and normalization
  datasets/              # dataset adapters
  evaluators/            # exact-match and dataset-specific evaluators
  llm/                   # mock, Ollama, OpenAI-compatible providers
  retrieval/             # BM25 retriever for retrieved-skill experiments
  utils/                 # small helpers

data/                    # reusable datasets and dataset catalog
references/              # downloaded upstream paper/code references
results/                 # experiment outputs
planning/                # planning docs
work/                    # scratch files only, gitignored
```

## Current Data

TRS math-facing data has been downloaded into:

```text
data/trs/
```

Most useful file:

```text
data/trs/corpora/deepmath_103k_oss_skill_corpus.jsonl.gz
```

It has:

```text
question
answer
skill_text
topic
difficulty
```

DeepMath is the recommended first dataset because the answers are mostly short canonical strings. AoPS rows often contain full worked solutions, so they use a different evaluator that extracts the boxed final answer first.

Dataset overview:

```text
data/README.md
data/datasets.json
```

Upstream TRS reference files moved to:

```text
references/trs_release/
```


## Quick Smoke Test

Run a tiny offline test:

```bash
./insights-repetition --config mock_smoke
```

The mock provider returns the gold answer so the pipeline can be tested without API calls.

## Run A Config

Use the repo-local CLI:

```bash
./insights-repetition --config openrouter_three_examples
```

That automatically:

```text
loads .env
uses configs/openrouter_three_examples.json
uses the bundled Python runtime when available
```

You can also pass a full path:

```bash
./insights-repetition --config configs/openrouter_three_examples.json
```

Most experiment settings are steered through the config:

```text
dataset
provider
model
mode
eval_offset
sample_size
k_values
temperature
max_tokens
max_token_warning_ratio
requests_per_minute
parallel_workers
request_timeout_s
max_retries
show_progress
reasoning
output_root
```

Set `parallel_workers` above `1` to run several requests at the same time. Keep `requests_per_minute` aligned with your provider limit; the rate limiter still spaces request starts across workers.

Secrets stay outside the config in `.env`, for example `OPENROUTER_API_KEY`.

## Run A Tiny OpenRouter Smoke Test

Set an API key in `.env`:

```text
OPENROUTER_API_KEY=sk-or-v1-...
```

Then run one DeepMath item with `k=0` and `k=1`:

```bash
./insights-repetition --config openrouter_smoke
```

The config is:

```text
configs/openrouter_smoke.json
```

Edit the `model` field if you want a different OpenRouter model.

The important rate-limit field is:

```json
"requests_per_minute": 20
```

Lower it if you hit OpenRouter rate limits. The runner sleeps between requests and logs `rate_limit_sleep_s` for every call.

Progress logging is on by default. To silence terminal progress for a large batch, add this to the config:

```json
"show_progress": false
```

Costs are logged per API call in each `results.jsonl` row:

```text
cost
cost_currency
cost_details
usage.cost
usage.cost_details
```

Aggregate summaries also include `mean_cost`, `total_cost`, and run-level `total_cost` when the provider returns cost metadata.

To try three later DeepMath examples:

```bash
./insights-repetition --config openrouter_three_examples
```

### macOS SSL Certificate Error

If OpenRouter fails with:

```text
ssl.SSLCertVerificationError: certificate verify failed
```

your current `python` is missing a usable certificate bundle. The repo-local CLI already prefers the bundled runtime, so use:

```bash
./insights-repetition --config openrouter_three_examples
```

Alternative fix: run the `Install Certificates.command` that ships with the Python.org macOS installer, then retry the normal CLI command.

## Run With Ollama

```bash
PYTHONPATH=src python -m insights_repetition.cli run \
  --dataset trs-deepmath \
  --provider ollama \
  --model llama3.1 \
  --mode oracle \
  --sample-size 100 \
  --k-values 0,1,2,3,5 \
  --temperature 0 \
  --requests-per-minute 30 \
  --output-root results
```

Optional:

```bash
--ollama-url http://localhost:11434
```

## Experiment Modes

### Oracle mode

Uses the same row's `skill_text` for the same row's question.

This answers:

```text
Given the right insight, does repetition help?
```

### Retrieved mode

Builds a BM25 skill library and retrieves a skill from another row.

This answers:

```text
When the insight is retrieved from a skill library, does repeating it help?
```

This is more realistic, but retrieval quality becomes a confound.

## LLM Providers

Available providers:

```text
mock               # offline smoke tests
ollama             # local Ollama /api/generate
openrouter         # OpenRouter chat completions
openai-compatible  # any OpenAI-compatible chat completions API
```

Token usage is logged for every response:

```text
prompt_tokens
completion_tokens
reasoning_tokens
visible_output_tokens
total_tokens
token_limit
raw_usage
```

When a provider does not return token counts, the code stores estimates.

Dashboard token columns:

```text
mean in       average prompt/input tokens sent to the model
mean visible  average visible answer tokens estimated from response text
mean reason   average hidden reasoning tokens, only when the provider reports them
mean out      average provider completion tokens
mean total    average provider total tokens
reason sum    total hidden reasoning tokens for that k, only when reported
limit flags   number of calls whose completion tokens reached the warning threshold
```

For reasoning models, provider `completion_tokens` often includes hidden reasoning plus visible output. That is why `reasoning_tokens` is logged separately whenever the API exposes it. If a provider does not report hidden reasoning tokens, `mean reason` / `reason sum` show `-`, not `0`.

Each row also stores a `token_limit` object. It flags `near_max_tokens`, `hit_max_tokens`, `reasoning_near_limit`, and `no_visible_output_at_limit`. This catches cases where a model burns the whole `max_tokens` budget on reasoning and returns little or no final answer. The default warning threshold is controlled by `max_token_warning_ratio` and is usually `0.95`.

OpenRouter returns reasoning-token counts in `usage.completion_tokens_details.reasoning_tokens` when applicable. Some models/providers do not expose reasoning tokens, so this metric is only guaranteed when OpenRouter includes it in the response.

To explicitly request reasoning through OpenRouter, add a `reasoning` object to your config:

```json
"model": "openai/o4-mini",
"max_tokens": 4096,
"reasoning": {
  "effort": "medium"
}
```

There is also a template config:

```bash
./insights-repetition --config openrouter_reasoning_template
```

For a one-call smoke test that should expose reasoning text and counts:

```bash
./insights-repetition --config openrouter_reasoning_smoke
```


## Run With An OpenAI-Compatible API

```bash
export INSIGHTS_API_KEY="..."

PYTHONPATH=src python -m insights_repetition.cli run \
  --dataset trs-deepmath \
  --provider openai-compatible \
  --api-base-url https://api.openai.com/v1/chat/completions \
  --api-key-env INSIGHTS_API_KEY \
  --model gpt-4o-mini \
  --mode oracle \
  --sample-size 100 \
  --k-values 0,1,2,3,5 \
  --temperature 0 \
  --requests-per-minute 30 \
  --output-root results
```

## Retrieved TRS-Style Run

```bash
PYTHONPATH=src python -m insights_repetition.cli run \
  --dataset trs-deepmath \
  --provider mock \
  --model mock \
  --mode retrieved \
  --library-size 1000 \
  --sample-size 100 \
  --k-values 0,1,2,3,5 \
  --output-root results
```

In retrieved mode the system:

1. loads records from the dataset,
2. uses the first `--library-size` rows as the skill library,
3. evaluates on later rows,
4. retrieves top-1 BM25 skill from a different row,
5. repeats that skill `k` times.

## Outputs

Each run creates:

```text
results/<run_id>/
  config.json
  results.jsonl
  per_item_summary.jsonl
  aggregate_summary.json
```

`results.jsonl` has one row per question, repeat, and `k`.

`per_item_summary.jsonl` groups all `k` conditions for each item and labels:

```text
improved_by_repetition
hurt_by_repetition
stable_correct
stable_wrong
best_k
```

`aggregate_summary.json` reports:

```text
accuracy_by_k
mean token usage by k
k=1 vs k>1 repetition deltas
transition counts
```

The terminal also prints a run dashboard at the end with accuracy bars, mean token usage, total cost, transition counts, and repetition deltas.

## Adding A New Dataset

The easiest path is `generic-jsonl`. Put your file under `data/<source>/` and make sure each row has fields for:

```text
question_id
question
answer
skill_text
```

Then run:

```bash
PYTHONPATH=src python -m insights_repetition.cli run \
  --dataset generic-jsonl \
  --data-path data/<source>/<file>.jsonl.gz \
  --provider mock \
  --model mock
```

If your field names differ, pass:

```text
--field-question-id
--field-question
--field-answer
--field-skill-text
```

For a custom dataset, add an adapter in `src/insights_repetition/datasets/`. It should return generic `ProblemRecord` objects:

```text
question_id
question
answer
skill_text
metadata
```

Then register it in `datasets/__init__.py` with its evaluator name.

## Adding A New Evaluator

Add an evaluator in `src/insights_repetition/evaluators/`.

The evaluator receives:

```text
model_output
gold_answer
record metadata
```

and returns:

```text
is_correct
predicted_answer
gold_answer
normalized strings
```

This keeps evaluation high-level while allowing dataset-specific answer logic.
