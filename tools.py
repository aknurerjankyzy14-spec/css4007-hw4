import ast
import math
import operator
import json
import difflib
from pathlib import Path

MAX_LENGTH = 200
MAX_NODES = 80
MAX_VALUE = 10**15

BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class CalculationError(Exception):
    """An expected calculator error."""


def check_number(value):
    """Reject non-numeric, excessive and non-finite values."""
    if type(value) not in (int, float):
        raise CalculationError("unsupported_expression")

    if abs(value) > MAX_VALUE:
        raise CalculationError("numeric_limit")

    if not math.isfinite(value):
        raise CalculationError("numeric_limit")

    return value


def evaluate_node(node):
    """Evaluate only explicitly permitted AST nodes."""
    if isinstance(node, ast.Constant):
        return check_number(node.value)

    if isinstance(node, ast.UnaryOp):
        operation = UNARY_OPERATORS.get(type(node.op))

        if operation is None:
            raise CalculationError("unsupported_expression")

        value = evaluate_node(node.operand)
        return check_number(operation(value))

    if isinstance(node, ast.BinOp):
        operation = BINARY_OPERATORS.get(type(node.op))

        # Check the operator before evaluating its operands.
        # This immediately rejects powers such as 9**9**9.
        if operation is None:
            raise CalculationError("unsupported_expression")

        left = evaluate_node(node.left)
        right = evaluate_node(node.right)

        if isinstance(node.op, ast.Div) and right == 0:
            raise CalculationError("division_by_zero")

        return check_number(operation(left, right))

    raise CalculationError("unsupported_expression")


def calculate(expression):
    """Return an arithmetic result or a structured error."""
    if not isinstance(expression, str):
        return {"error": "invalid_expression"}

    expression = expression.strip()

    if not expression or len(expression) > MAX_LENGTH:
        return {"error": "invalid_expression"}

    try:
        tree = ast.parse(expression, mode="eval")

        if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
            return {"error": "invalid_expression"}

        result = evaluate_node(tree.body)
        return {"result": result}

    except SyntaxError:
        return {"error": "invalid_syntax"}

    except CalculationError as error:
        return {"error": str(error)}

    except ZeroDivisionError:
        return {"error": "division_by_zero"}

    except (OverflowError, FloatingPointError):
        return {"error": "numeric_limit"}

    except Exception:
        return {"error": "invalid_expression"}
CORPUS_PATH = Path(__file__).resolve().parent / "data" / "corpus.jsonl"

MAX_QUERY_LENGTH = 200
MAX_TEXT_LENGTH = 900
MAX_MATCHES = 3


def lookup(query):
    """Retrieve current profiles and corrections with source IDs."""
    if not isinstance(query, str):
        return {"error": "invalid_query"}

    query = query.strip()

    if not query or len(query) > MAX_QUERY_LENGTH:
        return {"error": "invalid_query"}

    try:
        documents = []

        with CORPUS_PATH.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                document = json.loads(line)

                if not isinstance(document, dict):
                    raise ValueError("Invalid document")

                for field in ("id", "title", "text"):
                    if not isinstance(document.get(field), str):
                        raise ValueError("Invalid document field")

                documents.append(document)

        if not documents:
            return {"error": "corpus_unavailable"}

        by_id = {document["id"]: document for document in documents}

        if len(by_id) != len(documents):
            return {"error": "corpus_unavailable"}

        current_profiles = {}
        archived_profiles = {}

        for document in documents:
            title = document["title"]
            marker = " district profile"

            if marker not in title:
                continue

            district = title.split(marker, 1)[0]
            district_key = district.casefold()

            entry = {
                "district": district,
                "document": document,
            }

            if "ARCHIVED" in title.upper():
                archived_profiles[document["id"]] = entry
            else:
                if district_key in current_profiles:
                    return {"error": "corpus_unavailable"}

                current_profiles[district_key] = entry

        def build_result(selected):
            return {
                "matches": [
                    {
                        "doc_id": document["id"],
                        "text": document["text"][:MAX_TEXT_LENGTH],
                    }
                    for document in selected[:MAX_MATCHES]
                ]
            }

        def profile_with_corrections(entry):
            district_key = entry["district"].casefold()

            corrections = [
                document
                for document in documents
                if document["title"].casefold()
                == f"correction notice - {district_key}"
            ]

            # Corrections come first so they cannot be lost to the limit.
            return build_result(corrections + [entry["document"]])

        normalized = query.casefold()
        requested_id = query.upper()

        # A direct request for an archived profile is refused.
        if requested_id in archived_profiles:
            archived = archived_profiles[requested_id]
            current = current_profiles.get(
                archived["district"].casefold()
            )

            return {
                "error": "archived_document",
                "replacement": (
                    current["document"]["id"] if current else None
                ),
            }

        # Handle exact document IDs.
        if requested_id in by_id:
            for entry in current_profiles.values():
                if entry["document"]["id"] == requested_id:
                    return profile_with_corrections(entry)

            return build_result([by_id[requested_id]])

        # Handle exact district names.
        if normalized in current_profiles:
            return profile_with_corrections(
                current_profiles[normalized]
            )

        # Handle the regional tariff.
        if normalized == "water tariff":
            tariff = by_id.get("NR-15")

            if tariff is None:
                return {"error": "corpus_unavailable"}

            return build_result([tariff])

        # Partial names are suggested, never silently selected.
        partial_matches = [
            entry["district"]
            for district_key, entry in current_profiles.items()
            if normalized in district_key
        ]

        if len(partial_matches) > 1:
            return {
                "error": "ambiguous_query",
                "suggestions": sorted(partial_matches),
            }

        if partial_matches:
            return {
                "error": "not_found",
                "suggestions": partial_matches,
            }

        # Suggest similar spellings without automatically using them.
        close_names = difflib.get_close_matches(
            normalized,
            list(current_profiles),
            n=3,
            cutoff=0.5,
        )

        return {
            "error": "not_found",
            "suggestions": [
                current_profiles[name]["district"]
                for name in close_names
            ],
        }

    except Exception:
        return {"error": "corpus_unavailable"}

if __name__ == "__main__":
    if __name__ == "__main__":
        queries = [
            "Ossbridge",
            "Ossford",
            "Oss",
            "Ossbrige",
            "NR-13",
            "Brightwater",
            "NR-05",
            "water tariff",
        ]

        for query in queries:
            print(f"\nQUERY: {query}")
            print(json.dumps(lookup(query), indent=2, ensure_ascii=False))

