import pytest
import tools

from tools import calculate, lookup


# ---------- LOOKUP TESTS ----------

def test_lookup_current_population():
    result = lookup("Ossbridge")

    assert "matches" in result

    document = next(
        item for item in result["matches"]
        if item["doc_id"] == "NR-01"
    )

    assert "52,904" in document["text"]


def test_lookup_similar_names_are_separate():
    bridge = lookup("Ossbridge")
    ford = lookup("Ossford")

    assert bridge["matches"][0]["doc_id"] == "NR-01"
    assert ford["matches"][0]["doc_id"] == "NR-02"


def test_lookup_ambiguous_name():
    result = lookup("Oss")

    assert result["error"] == "ambiguous_query"
    assert set(result["suggestions"]) == {"Ossbridge", "Ossford"}


def test_lookup_misspelled_name():
    result = lookup("Ossbrige")

    assert result["error"] == "not_found"
    assert "Ossbridge" in result["suggestions"]
    assert "matches" not in result


@pytest.mark.parametrize(
    "archived_id,replacement",
    [
        ("NR-13", "NR-03"),
        ("NR-14", "NR-04"),
    ],
)
def test_lookup_archived_profile(archived_id, replacement):
    result = lookup(archived_id)

    assert result["error"] == "archived_document"
    assert result["replacement"] == replacement


@pytest.mark.parametrize("query", ["Brightwater", "NR-05"])
def test_lookup_includes_correction(query):
    result = lookup(query)
    documents = {
        item["doc_id"]: item["text"]
        for item in result["matches"]
    }

    assert "NR-05" in documents
    assert "NR-16" in documents
    assert "921.4" in documents["NR-16"]


def test_lookup_water_tariff():
    result = lookup("water tariff")

    assert result["matches"][0]["doc_id"] == "NR-15"
    assert "142.35" in result["matches"][0]["text"]


@pytest.mark.parametrize("query", ["", "   ", None, 123, "x" * 201])
def test_lookup_invalid_input(query):
    assert lookup(query)["error"] == "invalid_query"


def test_lookup_missing_corpus(monkeypatch, tmp_path):
    monkeypatch.setattr(
        tools,
        "CORPUS_PATH",
        tmp_path / "missing.jsonl",
    )

    assert lookup("Ossbridge")["error"] == "corpus_unavailable"


def test_lookup_invalid_corpus(monkeypatch, tmp_path):
    corpus = tmp_path / "broken.jsonl"
    corpus.write_text("this is not JSON", encoding="utf-8")
    monkeypatch.setattr(tools, "CORPUS_PATH", corpus)

    assert lookup("Ossbridge")["error"] == "corpus_unavailable"


# ---------- CALCULATE TESTS ----------

def test_calculate_multiplication():
    result = calculate("48317 * 1.0947")

    assert result["result"] == pytest.approx(52892.6199)


def test_calculate_q09():
    result = calculate("37203 / 758.6 - 44675 / 921.4")

    assert result["result"] == pytest.approx(
        0.5556561156405735
    )


def test_calculate_parentheses_and_unary_minus():
    result = calculate("-(2 + 3) * 4 / 2")

    assert result["result"] == -10


def test_calculate_division_by_zero():
    assert calculate("10 / 0")["error"] == "division_by_zero"


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo hi')",
        "(1).__class__",
        "9**9**9",
    ],
)
def test_calculate_rejects_dangerous_input(expression):
    assert calculate(expression)["error"] == "unsupported_expression"


def test_calculate_does_not_execute_commands(monkeypatch):
    import os

    def forbidden_system(*args, **kwargs):
        pytest.fail("The calculator attempted to execute a command")

    monkeypatch.setattr(os, "system", forbidden_system)

    result = calculate("__import__('os').system('echo hi')")

    assert result["error"] == "unsupported_expression"


def test_calculate_invalid_syntax():
    assert calculate("2 +")["error"] == "invalid_syntax"


@pytest.mark.parametrize("expression", ["", "   ", None, 123, "1" * 201])
def test_calculate_invalid_input(expression):
    assert calculate(expression)["error"] == "invalid_expression"


@pytest.mark.parametrize(
    "expression",
    [
        "1000000000000001",
        "1000000000 * 1000000000",
        "1e309",
    ],
)
def test_calculate_numeric_limit(expression):
    assert calculate(expression)["error"] == "numeric_limit"


def test_calculate_rejects_boolean():
    assert calculate("True")["error"] == "unsupported_expression"