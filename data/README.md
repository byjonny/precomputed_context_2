# Data Layout

Datasets live under `data/` so experiment configs can point to stable paths.

```text
data/
  datasets.json        # human-readable dataset catalog
  trs/
    corpora/           # JSONL / JSONL.GZ files used by dataset adapters
    manifests/         # upstream TRS README, schema, and manifests
    prompts/           # upstream direct/TRS prompts for reference
```

`work/` is reserved for scratch files and temporary analysis artifacts. `references/` stores downloaded paper/code snippets that are useful for comparison but are not used by the runner.

## Adding A Dataset

For a dataset that already has generic fields:

```text
question_id
question
answer
skill_text
```

put the file somewhere under `data/<source>/`, then run with:

```bash
PYTHONPATH=src python -m insights_repetition.cli run \
  --dataset generic-jsonl \
  --data-path data/<source>/<file>.jsonl.gz \
  --provider mock \
  --model mock
```

If the field names differ, pass:

```text
--field-question-id
--field-question
--field-answer
--field-skill-text
```

For custom answer checking, add an evaluator in `src/insights_repetition/evaluators/` and register it in `src/insights_repetition/evaluators/__init__.py`.
