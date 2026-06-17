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
        {"layout": "separate", "problem_repetitions": 2},
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 1


def test_separate_prompt_can_repeat_hint_and_problem() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        2,
        {"layout": "separate", "problem_repetitions": 2},
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 2


def test_full_block_prompt_repeats_hint_problem_blocks() -> None:
    prompt = build_prompt(
        "What is 1+1?",
        "Add directly.",
        2,
        {"layout": "full_block", "problem_repetitions": 2},
    )
    assert prompt.count("What is 1+1?") == 2
    assert prompt.count("Add directly.") == 2
    assert prompt.count("[Repeated Block") == 2
