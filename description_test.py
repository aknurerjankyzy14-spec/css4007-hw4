import copy
import json
from datetime import datetime, timezone

from strategies import ROOT, run_s3
from tool_specs import TOOL_SPECS


def main():
    questions = json.loads(
        (ROOT / "data" / "questions.json").read_text(
            encoding="utf-8"
        )
    )

    selected = {"Q-01", "Q-03", "Q-09", "Q-17", "Q-20"}

    vague_tools = copy.deepcopy(TOOL_SPECS)
    vague_tools[0]["function"]["description"] = "Looks things up."

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )
    summary_path = (
        ROOT / "outputs" / f"description_test_{timestamp}.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    for question in questions:
        if question["id"] not in selected:
            continue

        for label, definitions in [
            ("detailed", TOOL_SPECS),
            ("vague", vague_tools),
        ]:
            print(
                f"\nStarting {question['id']}: {label}",
                flush=True,
            )

            result, log_path = run_s3(
                question["id"],
                question["question"],
                tool_specs=definitions,
            )

            tool_calls = [
                call
                for round_log in result["rounds"]
                for call in round_log["tool_calls"]
            ]

            row = {
                "question_id": question["id"],
                "description": label,
                "model_calls": len(result["rounds"]),
                "tool_calls": len(tool_calls),
                "lookup_calls": sum(
                    call["name"] == "lookup"
                    for call in tool_calls
                ),
                "calculate_calls": sum(
                    call["name"] == "calculate"
                    for call in tool_calls
                ),
                "status": result["status"],
                "answer": result.get("final_answer", ""),
                "inputs": [
                    {
                        "name": call["name"],
                        "arguments": call["arguments"],
                    }
                    for call in tool_calls
                ],
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "seconds": result["total_seconds"],
                "log_file": str(log_path.relative_to(ROOT)),
            }

            rows.append(row)

            summary_path.write_text(
                json.dumps(rows, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            print("Model calls:", row["model_calls"])
            print("Tool calls:", row["tool_calls"])
            print("Answer:", row["answer"])

    print("\nFINISHED")
    print("Summary:", summary_path)


if __name__ == "__main__":
    main()