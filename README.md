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
experiment_name
mode
eval_offset
sample_size
seed
shuffle_records
k_values
temperature
max_tokens
max_token_warning_ratio
progress_summary_interval
prompt_config
experiments
requests_per_minute
parallel_workers
request_timeout_s
max_retries
show_progress
reasoning
output_root
```

Set `parallel_workers` above `1` to run several requests at the same time. Keep `requests_per_minute` aligned with your provider limit; the rate limiter still spaces request starts across workers.

Set `shuffle_records` to `true` to deterministically shuffle the loaded dataset before `eval_offset` and `sample_size` are applied. The `seed` controls that shuffle, so the same seed gives the same batch and a different seed gives a different batch.

Set `progress_summary_interval` to print a preliminary evaluation table every N completed result rows. The default is `100`; set it to `0` to disable live summaries.

For prompt-structure experiments, the shortest config is just an `experiments` object. The keys are condition ids, and the values are prompt recipes:

```json
"experiments": {
  "0": "{q}",
  "1": "{i, q}",
  "2": "{q, q, sep, i, i}"
}
```

This automatically sets:

```json
"k_values": [0, 1, 2],
"prompt_config": {
  "mode": "sequence",
  "sequence_by_k": {
    "0": "{q}",
    "1": "{i, q}",
    "2": "{q, q, sep, i, i}"
  }
}
```

So you usually do not need to write `k_values` manually for prompt recipe experiments.

Canonical recipes such as `{q}`, `{i, q}`, and `{i, i, q}` are rendered with the same direct/TRS-style templates as the original repetition experiment. In particular, `{i, i, q}` is equivalent to "repeat the insight twice, then show the problem" inside one Solving Hints block.

Older runs before the prompt refactor used the delimiter `--- same hint repeated ---`. To reproduce those hashes exactly, set:

```json
"prompt_config": {
  "hint_delimiter": "\n\n--- same hint repeated ---\n\n"
}
```

Set `prompt_config` directly only when you need more control. The default mode is `separate`: question copies and insight copies are repeated separately, with the separator `Let me repeat it:` between copies.

Use arrays when each `k` condition should have its own number of question and insight copies:

```json
"k_values": [0, 1, 2, 3],
"prompt_config": {
  "mode": "separate",
  "repeat_question": [1, 1, 2, 2],
  "repeat_insight": [0, 1, 0, 2]
}
```

This means:

```text
k=0 -> q
k=1 -> i + q
k=2 -> q + q
k=3 -> i + i + q + q
```

Arrays are indexed by the numeric `k`. For sparse or non-contiguous condition ids, use `conditions`:

```json
"k_values": [0, 1, 5],
"prompt_config": {
  "mode": "separate",
  "conditions": {
    "0": {"q": 1, "i": 0},
    "1": {"q": 1, "i": 1},
    "5": {"q": 2, "i": 2}
  }
}
```

Use `sequence` mode when you want to write the exact prompt recipe yourself. Use `q` for the problem, `i` for the insight, and `sep` for the separator text.

```json
"prompt_config": {
  "mode": "sequence",
  "sequence": "{q, q, sep, i, i}"
}
```

This produces:

```text
[Q] [Q] Let me repeat it: [I] [I]
```

Use `sequence_by_k` when each `k` condition should have its own exact prompt structure:

```json
"prompt_config": {
  "mode": "sequence",
  "sequence_by_k": {
    "0": ["q"],
    "1": ["i", "q"],
    "2": ["i", "sep", "i", "q"],
    "3": ["q", "sep", "q"],
    "4": ["i", "q", "sep", "i", "q"]
  }
}
```

Then set matching `k_values`:

```json
"k_values": [0, 1, 2, 3, 4]
```

One config file can also contain several full runs. In that case, `experiments` is a list. Put shared settings at the top, then override only the fields that differ:

```json
{
  "dataset": "trs-deepmath",
  "provider": "openrouter",
  "model": "deepseek/deepseek-v4-flash",
  "sample_size": 100,
  "temperature": 0,
  "max_tokens": 4096,
  "output_root": "results",
  "experiments": [
    {
      "experiment_name": "trs_baseline",
      "k_values": [0, 1],
      "prompt_config": {
        "mode": "separate",
        "repeat_question": [1, 1],
        "repeat_insight": [0, 1]
      }
    },
    {
      "experiment_name": "question_and_insight_repetition",
      "k_values": [0, 1, 2],
      "prompt_config": {
        "mode": "sequence",
        "sequence_by_k": {
          "0": "{q}",
          "1": "{i, q}",
          "2": "{q, q, sep, i, i}"
        }
      }
    }
  ]
}
```

Run it like any other config:

```bash
./insights-repetition --config prompt_experiments_template
```

Each entry in `experiments` becomes its own result folder, with the `experiment_name` included in the run id.

The default separator is:

```text
Let me repeat it:
```

You can override it:

```json
"prompt_config": {
  "mode": "sequence",
  "separator": "Let me repeat that:",
  "sequence": ["q", "sep", "q"]
}
```

Count-based prompt configs are still supported:

TRS-style baseline/insertion:

```json
"prompt_config": {
  "mode": "separate",
  "repeat_insight": "k",
  "repeat_question": 1
}
```

Problem repetition only:

```json
"prompt_config": {
  "mode": "separate",
  "repeat_insight": 0,
  "repeat_question": 2
}
```

Separate insight and problem repetition:

```json
"prompt_config": {
  "mode": "separate",
  "repeat_insight": "k",
  "repeat_question": 2
}
```

Full block repetition:

```json
"prompt_config": {
  "mode": "full_block",
  "repeat_insight": "k",
  "repeat_question": 2
}
```

Older names are still accepted for compatibility: `layout` means `mode`, `insight_repetitions` means `repeat_insight`, and `problem_repetitions` / `repeat_problem` mean `repeat_question`.

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
