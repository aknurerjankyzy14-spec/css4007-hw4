import argparse
import csv
import json
import statistics
from datetime import datetime, timezone
from decimal import Decimal

from strategies import (
    ROOT,
    MODEL,
    TEMPERATURE,
    parse_answer,
    rounded_number,
    run_s1,
    run_s2,
    run_s3,
)


def evaluate(result, reference):
    """Reference answers are used here only, after generation."""
    parsed = parse_answer(result.get("final_answer", ""))

    if result["status"] != "completed" or parsed is None:
        return {
            "correct": False,
            "unanswered": True,
            "predicted_name": None,
            "predicted_value": None,
        }

    name, number = parsed
    decimals = reference["decimals"]

    try:
        predicted = rounded_number(number, decimals)
        expected = rounded_number(
            Decimal(str(reference["value"])),
            decimals,
        )
        tolerance = Decimal("1").scaleb(-decimals)

        correct = (
            name == reference["answer"]
            and abs(predicted - expected) <= tolerance
        )
    except ArithmeticError:
        return {
            "correct": False,
            "unanswered": True,
            "predicted_name": name,
            "predicted_value": str(number),
        }

    return {
        "correct": correct,
        "unanswered": False,
        "predicted_name": name,
        "predicted_value": str(number),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=int, required=True, choices=[1, 2])
    args = parser.parse_args()

    questions = json.loads(
        (ROOT / "data" / "questions.json").read_text(
            encoding="utf-8"
        )
    )

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )
    folder = ROOT / "outputs" / f"run_{args.run}_{timestamp}"
    folder.mkdir(parents=True, exist_ok=False)

    manifest = {
        "run": args.run,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "reasoning_effort": "none",
        "s2_k": 5,
        "s3_max_rounds": 12,
        "question_count": len(questions),
        "question_ids": [q["id"] for q in questions],
        "order": "question order, then S1, S2, S3",
        "vote_tie_break": "earliest sample among tied answers",
        "rounding": "ROUND_HALF_UP",
        "evaluation": (
            "Exact name; rounded numeric difference <= "
            "one unit in the last decimal place."
        ),
    }

    (folder / "settings.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    rows = []

    def save_results():
        (folder / "results.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    for question in questions:
        for strategy in ("S1", "S2", "S3"):
            print(
                f"\nRun {args.run}: {question['id']} {strategy}",
                flush=True,
            )

            # API errors stop the run. Individual strategy logs
            # preserve any successful calls made before the error.
            if strategy == "S1":
                result, log_path = run_s1(
                    question["id"],
                    question["question"],
                    question["decimals"],
                )
            elif strategy == "S2":
                result, log_path = run_s2(
                    question["id"],
                    question["question"],
                    question["decimals"],
                )
            else:
                result, log_path = run_s3(
                    question["id"],
                    question["question"],
                )

            row = {
                "run": args.run,
                "question_id": question["id"],
                "strategy": strategy,
                "status": result["status"],
                **evaluate(result, question),
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "seconds": result["total_seconds"],
                "usage_incomplete": result.get(
                    "usage_incomplete", False
                ),
                "log_file": str(log_path.relative_to(ROOT)),
            }

            rows.append(row)
            save_results()

            print("Answer:", result.get("final_answer", ""))
            print("Correct:", row["correct"])
            print("Unanswered:", row["unanswered"])
            print("Seconds:", round(row["seconds"], 2))

    summary = []

    for strategy in ("S1", "S2", "S3"):
        selected = [
            row for row in rows
            if row["strategy"] == strategy
        ]

        summary.append({
            "run": args.run,
            "strategy": strategy,
            "questions": len(selected),
            "correct": sum(row["correct"] for row in selected),
            "unanswered": sum(
                row["unanswered"] for row in selected
            ),
            "input_tokens": sum(
                row["input_tokens"] for row in selected
            ),
            "output_tokens": sum(
                row["output_tokens"] for row in selected
            ),
            "median_seconds": round(
                statistics.median(
                    row["seconds"] for row in selected
                ),
                3,
            ),
            "total_seconds": round(
                sum(row["seconds"] for row in selected),
                3,
            ),
        })

    (folder / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    with (folder / "summary.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(summary[0]),
        )
        writer.writeheader()
        writer.writerows(summary)

    print("\nFINISHED")
    for item in summary:
        print(
            f"{item['strategy']}: "
            f"{item['correct']}/{item['questions']} correct, "
            f"{item['unanswered']} unanswered, "
            f"{item['total_seconds']} seconds"
        )

    print("Results folder:", folder)


if __name__ == "__main__":
    main()