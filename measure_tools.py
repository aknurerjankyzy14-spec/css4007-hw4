import json
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

from strategies import ROOT, MODEL, TEMPERATURE
from tool_specs import TOOL_SPECS


def main():
    load_dotenv(ROOT / ".env")
    client = OpenAI(timeout=90.0, max_retries=0)

    messages = [
        {"role": "user", "content": "Reply with OK."}
    ]

    results = {}

    for label, extra_parameters in [
        ("without_tools", {}),
        ("with_tools", {
            "tools": TOOL_SPECS,
            "tool_choice": "none",
        }),
    ]:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            reasoning_effort="none",
            temperature=TEMPERATURE,
            **extra_parameters,
        )

        if response.usage is None:
            raise RuntimeError("API did not return token usage")

        results[label] = response.usage.model_dump()

    difference = (
        results["with_tools"]["prompt_tokens"]
        - results["without_tools"]["prompt_tokens"]
    )

    results["measured_overhead_tokens"] = difference
    results["method"] = (
        "Same model and messages, with and without tool definitions. "
        "The tools condition also sets tool_choice='none'; the difference "
        "measures tool-related request overhead for this configuration."
    )

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )
    path = ROOT / "outputs" / f"tool_tokens_{timestamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print("Without tools:", results["without_tools"]["prompt_tokens"])
    print("With tools:", results["with_tools"]["prompt_tokens"])
    print("Measured overhead:", difference)
    print("Log:", path)


if __name__ == "__main__":
    main()