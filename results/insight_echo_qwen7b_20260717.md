# Insight-echo plausibility study: Qwen 2.5 7B, {q,i} -> {q,i|q,i}

Generated 2026-07-17 17:56. n=1000 items analyzed (0 skipped for distinctive card vocabulary < 10 words).
Echo = share of the card's distinctive vocabulary (card words absent from the question,
stopwords removed) that appears in the completion. Bootstrap CIs, 10k resamples.

## P1 sanity: does the metric detect card usage at all?

- mean echo with card in prompt ({q,i}): **13.5%** [12.8%, 14.3%]
- mean echo without card ({q}):        **10.1%** [9.8%, 10.4%]

## P2 correctness confound, measured where the card was never shown ({q}):

- echo of correct {q} responses: 9.8% [9.3%, 10.3%]  (n=425)
- echo of wrong {q} responses:   10.4% [9.9%, 10.8%]  (n=575)
- confound size (correct - wrong, no card): **-0.6%**

## P3/P4 paired echo change under repetition, by transition group

| Group | n | echo at x1 | echo at x2 | paired delta | 95% CI | sign-test p |
|---|---:|---:|---:|---:|---:|---:|
| improved (wrong->right) | 126 | 13.1% | 13.5% | 0.5% | [-1.8%, 2.6%] | 0.3029 |
| hurt (right->wrong) | 94 | 14.4% | 15.0% | 0.6% | [-3.3%, 4.4%] | 0.9152 |
| stable correct | 407 | 12.3% | 12.4% | 0.1% | [-0.8%, 1.1%] | 0.6676 |
| stable wrong | 373 | 14.7% | 13.7% | -1.0% | [-2.6%, 0.4%] | 0.0560 |

- length check, improved (wrong->right): mean words 383 (x1) vs 320 (x2)
- length check, hurt (right->wrong): mean words 325 (x1) vs 362 (x2)

## P5 prospective: echo at x1 among items that were WRONG at x1

- future improved (flip to correct at x2): 13.1% [11.5%, 15.0%]  (n=126)
- stable wrong:                            14.7% [13.4%, 16.2%]  (n=373)
- difference (improved - stable wrong): **-1.6%** [-3.8%, 0.7%]

Uptake account predicts a NEGATIVE difference: flips should come from items where
the first copy was under-used.

- share of improved items whose echo rose under repetition: 50%
