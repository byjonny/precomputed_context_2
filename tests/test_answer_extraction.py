from insights_repetition.answer_extraction import answers_match, extract_choice, extract_final_answer, normalize_answer


def test_extract_last_boxed() -> None:
    text = r"First \boxed{1}, finally \boxed{\textbf{(E)}}."
    assert extract_final_answer(text) == r"\textbf{(E)}"


def test_extract_choice() -> None:
    assert extract_choice(r"\mathrm{(D)}\text{ } 3+\sqrt6") == "D"


def test_equivalent_fraction_aliases_match() -> None:
    assert answers_match(r"$-\dfrac{2}{3}$", r"-\frac{2}{3}")
    assert answers_match("π/2", r"\dfrac{\pi}{2}")


def test_unicode_infinity_matches_latex_infinity() -> None:
    assert answers_match("∞", r"\infty")


def test_empty_set_aliases_match() -> None:
    assert answers_match("No values of k.", r"\emptyset")
