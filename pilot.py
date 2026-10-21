import json

from strategies import ROOT, run_s1, run_s2


def main():
    questions = json.loads(
        (ROOT / "data" / "questions.json").read_text(
            encoding="utf-8"
        )
    )

    for question in questions:
        if question["id"] not in {"Q-01", "Q-09"}:
            continue

        for strategy, function in [
            ("S1", run_s1),
            ("S2", run_s2),
        ]:
            print(
                f"\nStarting {strategy}: {question['id']}",
                flush=True,
            )

            result, path = function(
                question["id"],
                question["question"],
                question["decimals"],
            )

            print("Status:", result["status"])
            print("Answer:", result["final_answer"])
            print("Input tokens:", result["input_tokens"])
            print("Output tokens:", result["output_tokens"])
            print("Seconds:", round(result["total_seconds"], 2))
            print("Log:", path)


if __name__ == "__main__":
    main()