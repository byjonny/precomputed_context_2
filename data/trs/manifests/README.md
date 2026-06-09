---
license: other
language:
  - en
task_categories:
  - text-generation
  - question-answering
pretty_name: TRS Reasoning Skill Cards
tags:
  - reasoning
  - retrieval-augmented-generation
  - skill-cards
  - math
  - competitive-programming
  - science
size_categories:
  - 100K<n<1M
---

# TRS Reasoning Skill Cards

<p align="center">
  <a href="https://arxiv.org/abs/2604.21764"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2604.21764-B31B1B?style=for-the-badge&logo=arxiv&logoColor=white"></a>
  <a href="https://huggingface.co/datasets/stallone0000/Reasoning-Skill"><img alt="Hugging Face Dataset" src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Reasoning--Skill-FFD21E?style=for-the-badge"></a>
  <a href="https://github.com/stallone0000/Reasoning-Skill"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-Code%20Release-181717?style=for-the-badge&logo=github&logoColor=white"></a>
  <a href="https://reasoning-skill.onrender.com/"><img alt="Live Demo" src="https://img.shields.io/badge/Live%20Demo-Direct%20vs%20TRS-46E3B7?style=for-the-badge&logo=render&logoColor=white"></a>
</p>

> **News (2026-04-18):** This paper has been accepted to **ACL 2026 (Oral)**.

**Project links:** [arXiv](https://arxiv.org/abs/2604.21764) · [GitHub](https://github.com/stallone0000/Reasoning-Skill) · [Hugging Face Dataset](https://huggingface.co/datasets/stallone0000/Reasoning-Skill) · [Interactive Demo](https://reasoning-skill.onrender.com/)

This folder is a HuggingFace-ready staging package for the skill-card data used by **Thinking with Reasoning Skills** and its camera-ready additions.

The package includes compact skill-card corpora where they are already small/sanitized, plus manifest-only entries for larger local sources. It intentionally excludes raw benchmark datasets, raw problem-bank dumps, BM25 pickle caches, private logs, API keys, and unfiltered full CoT traces.

## Files In This Package

Release-ready or near-release data files are under `data/`:

- `deepmath_103k_oss_skill_corpus.jsonl.gz`: 103,020-row normalized DeepMath OSS skill archive. This is useful for demos and full-archive release, but the paper's strict DeepMath source split is the 93,020-card source library listed in `manifests/source_files.jsonl`.
- `aops_skill_corpus.jsonl.gz`: 7,735-row normalized AoPS/contest-math skill corpus. The camera-ready headline transfer result uses the pure 7,616-card AoPS source listed in the manifest; the extra rows correspond to later benchmark-extension/merged assets and should be described carefully.
- `coding_nemotron_competitive_programming.jsonl.gz`: 42,564-row normalized competitive-programming v5 skill corpus from the Nemotron CP experiments. It contains compact success, contrast, and failure-diagnostic cards, plus problem text and retrieval triggers; raw generated programs, model trajectories, and judge logs are excluded.
- `trs_skill_corpus.jsonl`: 10,476-row mixed demo skill corpus used by the interactive assets.
- `benchmark_correct_cot_skill_corpus.jsonl.gz`: 120 benchmark-derived cards from the correct-CoT-preferred pipeline.
- `benchmark_error_priority_skill_corpus.jsonl.gz`: 120 benchmark-derived cards from the error-priority pipeline.

Metadata and previews:

- `schema.json`: canonical JSON schema for released skill-card rows.
- `manifests/skill_datasets.json`: checksums and field summaries for the files under `data/`.
- `manifests/source_files.jsonl`: paper/camera-ready source inventory, including large local sources that should be normalized before upload.
- `samples/*.sample.jsonl`: small previews for existing packaged corpora.
- `samples/skill_card_samples.jsonl`: normalized examples from representative paper/camera-ready sources, including manifest-only large sources.
- `.gitattributes`: suggested Git LFS rules for future Hugging Face upload.

## Canonical Schema

Most release rows should follow this compact shape:

```json
{
  "dataset_id": "deepmath_oss_93020",
  "source_question_id": "q_1",
  "domain": "math",
  "question": "...",
  "answer": "...",
  "topic": "...",
  "difficulty": 5.0,
  "skill_text": "Trigger / Do / Avoid / Check / Risk style card text...",
  "keywords": "comma-separated retrieval triggers",
  "source_model": "gpt-oss-120b",
  "distill_model": "Gemini Flash/Pro family",
  "verdict": "CORRECT",
  "representation_type": "structured_skill_card"
}
```

For existing normalized corpora, `source_key` and `source_label` may be used instead of `dataset_id`/`source_model`; keep those fields for backwards compatibility, but use `schema.json` for future exports.

## Paper And Camera-Ready Source Coverage

The source manifest covers the skill-card datasets that appear in the paper or camera-ready additions:

- `deepmath_oss_93020`: 93,020-card DeepMath math library distilled from GPT-OSS trajectories. Used by main math TRS, selective deployment, non-reasoning mismatch, and optional science mismatch controls.
- `deepmath_doubao_93020`: 93,020-card DeepMath math library distilled from Doubao trajectories. Used by cross-model/source-transfer analysis.
- `aops_pure_7616`: pure 7,616-card AoPS-derived contest-math library used for the clean external AIME/HMMT transfer study.
- `aops_benchmark_extension_120` and `aops_plus_benchmark_7736`: exploratory benchmark-derived extension and merged AoPS+benchmark library. These overlap the evaluation suite and should be released only as supplemental/internal-ablation data.
- `deepmath_structured_2500_*` and `deepmath_drop_caution_2500_*`: structured-card ablation libraries used in the camera-ready representation-control study.
- `science_oss_30000`: 30,000-card science-domain extension used by the optional science robustness study.
- `coding_nemotron_competitive_programming`: 42,564-card competitive-programming library described in the paper appendix and packaged under `data/`. The staged v5 source contains 31,044 success cards, 5,069 contrast cards, and 6,451 failure-diagnostic cards (3,733 wrong-approach cards plus 2,718 edge-fix cards).

## Upload Strategy

Recommended Hugging Face layout after final export:

```text
data/
  deepmath_oss_93020.jsonl.gz
  deepmath_doubao_93020.jsonl.gz
  aops_pure_7616.jsonl.gz
  coding_nemotron_competitive_programming.jsonl.gz
  deepmath_structured_2500_oss.jsonl.gz
  deepmath_structured_2500_doubao.jsonl.gz
  science_oss_30000.jsonl.gz
supplemental/
  deepmath_oss_103020_archive.jsonl.gz
  aops_benchmark_extension_120.jsonl.gz
  aops_plus_benchmark_7736.jsonl.gz
manifests/
  source_files.jsonl
schema.json
README.md
```

For large local sources, export a stripped JSONL/Parquet file from `manifests/source_files.jsonl`: map `heuristic` to `skill_text`, retain `question`, `answer`, `topic`, `difficulty`, `keywords`, source model, distill model, and verifier metadata, and drop `model_think`, `reasoning_trace`, full `model_response`, raw provider responses, token logs, and BM25 caches.

## Caveats

Keep `license: other` until source-dataset licenses and model-output release rights are audited. The benchmark-derived 120-card files and the 7,736-card AoPS+benchmark merged library overlap the evaluation suite; they are useful for transparency and ablations but should not be described as clean external generalization data.

## Citation

If you use this dataset or the TRS skill-card format, please cite:

```bibtex
@inproceedings{
zhao2026thinking,
title={Thinking with Reasoning skills: Fewer Tokens, More Accuracy},
author={Guangxiang Zhao and Qilong Shi and Xiangzheng Zhang and Tong Yang and Xusen Xiao and Lin Sun},
booktitle={The 64th Annual Meeting of the Association for computational Linguistics -- Industry Track},
year={2026},
url={https://openreview.net/forum?id=FI93dzMCSN},
eprint={2604.21764},
archivePrefix={arXiv},
primaryClass={cs.CL}
}
```
