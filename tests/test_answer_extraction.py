from insights_repetition.answer_extraction import extract_choice, extract_final_answer, normalize_answer


def test_extract_last_boxed() -> None:
    text = r"First \boxed{1}, finally \boxed{\textbf{(E)}}."
    assert extract_final_answer(text) == r"\textbf{(E)}"


def test_extract_choice() -> None:
    assert extract_choice(r"\mathrm{(D)}\text{ } 3+\sqrt6") == "D"


def test_trs_normalize_is_strict_about_fraction_aliases() -> None:
    assert normalize_answer(r"$-\dfrac{2}{3}$") != normalize_answer(r"-\frac{2}{3}")
