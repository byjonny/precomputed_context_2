from insights_repetition.prompts import build_prompt


def test_default_prompt_keeps_problem_once_without_hint() -> None:
    prompt = build_prompt("What is 1+1?", "Add directly.", 0)
    assert prompt.count("What is 1+1?") == 1
    assert "[Solving Hints]" not in prompt


def test_separate_prompt_can_repeat_problem() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        1,
        {"mode": "separate", "repeat_problem": 2},
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 1


def test_separate_prompt_can_repeat_hint_and_problem() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        2,
        {"mode": "separate", "repeat_problem": 2},
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 2


def test_full_block_prompt_repeats_hint_problem_blocks() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        2,
        {"mode": "full_block", "repeat_problem": 2},
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 2
    assert "[Repeated Block" not in prompt
    assert "[Repeated Problem" not in prompt
    assert prompt.count("Let me repeat it:") == 1


def test_old_prompt_config_names_still_work() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        2,
        {"layout": "separate", "problem_repetitions": 2},
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 2


def test_sequence_prompt_can_be_defined_directly() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        0,
        {"mode": "sequence", "sequence": ["q", "q", "sep", "i", "i"]},
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 2
    assert prompt.count("Let me repeat it:") == 1


def test_sequence_prompt_accepts_braced_recipe_string() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        0,
        {"mode": "sequence", "sequence": "{q, q, sep, i, i}"},
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 2
    assert prompt.count("Let me repeat it:") == 1


def test_sequence_by_k_can_define_different_prompt_conditions() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        2,
        {
            "mode": "sequence",
            "sequence_by_k": {
                "0": ["q"],
                "1": ["i", "q"],
                "2": ["i", "sep", "i", "q"],
            },
        },
    )
    assert prompt.count("What is 1+1?") == 1
    assert prompt.count("Add directly.") == 2
    assert prompt.count("Let me repeat it:") == 1


def test_sequence_i_i_q_matches_separate_insight_repetition() -> None:
    sequence_prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        2,
        {"mode": "sequence", "sequence": "{i, i, q}"},
    )
    separate_prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        2,
        {"mode": "separate", "repeat_insight": 2, "repeat_question": 1},
    )
    assert sequence_prompt == separate_prompt
    assert sequence_prompt.count("[Solving Hints]") == 1


def test_sequence_q_matches_default_direct_prompt() -> None:
    sequence_prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        0,
        {"mode": "sequence", "sequence": "{q}"},
    )
    default_prompt = build_prompt("What is 1+1?", "Add directly.", 0)
    assert sequence_prompt == default_prompt


def test_separate_prompt_accepts_question_and_insight_arrays() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        2,
        {
            "mode": "separate",
            "repeat_question": [1, 1, 2],
            "repeat_insight": [0, 1, 2],
        },
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 2
    assert prompt.count("Let me repeat it:") == 2


def test_conditions_can_define_count_recipes() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        4,
        {
            "mode": "separate",
            "conditions": {
                "4": {"q": 2, "i": 2},
            },
        },
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 2
    assert prompt.count("Let me repeat it:") == 2
