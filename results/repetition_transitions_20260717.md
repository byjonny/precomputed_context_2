# Per-item repetition transitions (x1 -> x2)

Generated 2026-07-17 17:42 from post-retry results.jsonl (error records count as wrong).
Each cell pairs the same item under the single and the repeated condition; n=1,000 per contrast.
`improved` = wrong->right, `hurt` = right->wrong, net = improved - hurt (= accuracy delta in tenths of pp).
McNemar is continuity-corrected on the discordant pairs.

## problem-first: `{q,i} -> {q,i|q,i}`

| Model | improved | hurt | stable correct | stable wrong | net (pp) | discordant | McNemar p |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mistral Nemo 12B | 99 | 87 | 94 | 720 | +1.2 | 186 (19%) | 0.420 |
| Mistral Small 24B | 140 | 117 | 331 | 412 | +2.3 | 257 (26%) | 0.170 |
| Qwen 2.5 7B | 126 | 94 | 407 | 373 | +3.2 | 220 (22%) | 0.037 |
| Qwen 2.5 32B | 75 | 81 | 579 | 265 | -0.6 | 156 (16%) | 0.689 |
| Gemma 3 12B | 88 | 89 | 555 | 268 | -0.1 | 177 (18%) | 1.000 |
| Gemma 3 27B | 72 | 60 | 663 | 205 | +1.2 | 132 (13%) | 0.338 |
| Qwen 3 8B (think off) | 117 | 80 | 517 | 286 | +3.7 | 197 (20%) | 0.010 |
| Qwen 3 8B (think on) | 70 | 79 | 241 | 610 | -0.9 | 149 (15%) | 0.512 |

## insight-first: `{i,q} -> {i,q|i,q}`

| Model | improved | hurt | stable correct | stable wrong | net (pp) | discordant | McNemar p |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mistral Nemo 12B | 93 | 107 | 79 | 721 | -1.4 | 200 (20%) | 0.358 |
| Mistral Small 24B | 140 | 115 | 327 | 418 | +2.5 | 255 (26%) | 0.133 |
| Qwen 2.5 7B | 137 | 98 | 350 | 415 | +3.9 | 235 (24%) | 0.013 |
| Qwen 2.5 32B | 82 | 72 | 561 | 285 | +1.0 | 154 (15%) | 0.468 |
| Gemma 3 12B | 98 | 72 | 545 | 285 | +2.6 | 170 (17%) | 0.055 |
| Gemma 3 27B | 79 | 60 | 640 | 221 | +1.9 | 139 (14%) | 0.127 |
| Qwen 3 8B (think off) | 107 | 87 | 500 | 306 | +2.0 | 194 (19%) | 0.173 |
| Qwen 3 8B (think on) | 102 | 73 | 228 | 597 | +2.9 | 175 (18%) | 0.034 |

## question-only: `{q} -> {q|q}`

| Model | improved | hurt | stable correct | stable wrong | net (pp) | discordant | McNemar p |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mistral Nemo 12B | 77 | 77 | 61 | 785 | +0.0 | 154 (15%) | 0.936 |
| Mistral Small 24B | 115 | 107 | 225 | 553 | +0.8 | 222 (22%) | 0.638 |
| Qwen 2.5 7B | 116 | 111 | 314 | 459 | +0.5 | 227 (23%) | 0.791 |
| Qwen 2.5 32B | 88 | 97 | 435 | 380 | -0.9 | 185 (18%) | 0.556 |
| Gemma 3 12B | 94 | 76 | 454 | 376 | +1.8 | 170 (17%) | 0.192 |
| Gemma 3 27B | 82 | 62 | 544 | 312 | +2.0 | 144 (14%) | 0.113 |
| Qwen 3 8B (think off) | 133 | 99 | 396 | 372 | +3.4 | 232 (23%) | 0.030 |
| Qwen 3 8B (think on) | 83 | 86 | 172 | 659 | -0.3 | 169 (17%) | 0.878 |
