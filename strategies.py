import json
import time
import re
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from tool_specs import TOOL_SPECS
from tools import calculate, lookup


ROOT = Path(__file__).resolve().parent
MODEL = "gpt-5.6-luna"
MAX_ROUNDS = 12
TEMPERATURE = 0.7
SYSTEM_PROMPT = """
Answer questions about the fictional Nine Rivers Region.
Retrieve facts using lookup and perform arithmetic using calculate.
Do not invent missing facts.

Use 2025 figures unless another year is requested.
Ignore archived profiles and apply correction notices.
School figures refer to 2025/26.
Use 365 days for 2025.
One megalitre equals 1000 cubic metres or 1000000 litres.
Keep intermediate results unrounded.

End your response with exactly:
ANSWER: <name or yes/no> | <number>

Use the district's exact name or lowercase yes/no.
Use a decimal point and no thousands separators in the final number.
"""


def execute_tool(name, raw_arguments):
    """Validate the model's JSON arguments before calling a tool."""
    functions = {
        "lookup": (lookup, "query"),
        "calculate": (calculate, "expression"),
    }

    if name not in functions:
        return {"error": "unknown_tool"}

    if not isinstance(raw_arguments, str):
        return {"error": "invalid_arguments"}

    if len(raw_arguments) > 2000:
        return {"error": "invalid_arguments"}

    try:
        arguments = json.loads(raw_arguments)
    except (json.JSONDecodeError, ValueError):
        return {"error": "invalid_json"}

    if not isinstance(arguments, dict):
        return {"error": "arguments_must_be_object"}

    function, required_field = functions[name]

    if set(arguments) != {required_field}:
        return {
            "error": "invalid_arguments",
            "required": [required_field],
        }

    if not isinstance(arguments[required_field], str):
        return {
            "error": "argument_must_be_string",
            "field": required_field,
        }

    return function(**arguments)

def run_s3(question_id, question, tool_specs=None):
    active_tools = TOOL_SPECS if tool_specs is None else tool_specs
    load_dotenv(ROOT / ".env")

    # Disable automatic retries so failed attempts are not hidden.
    client = OpenAI(timeout=90.0, max_retries=0)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )
    log_path = ROOT / "outputs" / f"S3_{question_id}_{timestamp}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    log = {
        "question_id": question_id,
        "strategy": "S3",
        "tool_specs": active_tools,
        "model": MODEL,
        "max_rounds": MAX_ROUNDS,
        "temperature": TEMPERATURE,
        "reasoning_effort": "none",
        "status": "running",
        "input_tokens": 0,
        "output_tokens": 0,
        "rounds": [],
        "messages": messages,
    }

    started = time.perf_counter()

    def save_log():
        log["total_seconds"] = time.perf_counter() - started
        log_path.write_text(
            json.dumps(log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    save_log()

    try:
        for round_number in range(1, MAX_ROUNDS + 1):
            request_started = time.perf_counter()

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=active_tools,
                reasoning_effort="none",
                temperature=TEMPERATURE,
            )

            round_log = {
                "round": round_number,
                "request_seconds": (
                    time.perf_counter() - request_started
                ),
                "tool_calls": [],
                "usage": (
                    response.usage.model_dump()
                    if response.usage else None
                ),
            }
            log["rounds"].append(round_log)

            if response.usage:
                log["input_tokens"] += response.usage.prompt_tokens
                log["output_tokens"] += response.usage.completion_tokens
            else:
                log["usage_incomplete"] = True

            message = response.choices[0].message

            # Preserve the assistant's message, including tool calls.
            messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                log["final_answer"] = message.content or ""
                log["status"] = (
                    "completed" if message.content else "unanswered"
                )
                save_log()
                return log, log_path

            # Return one result for every tool_call_id.
            for call in message.tool_calls:
                tool_started = time.perf_counter()

                result = execute_tool(
                    call.function.name,
                    call.function.arguments,
                )

                tool_seconds = time.perf_counter() - tool_started

                round_log["tool_calls"].append({
                    "tool_call_id": call.id,
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                    "result": result,
                    "seconds": tool_seconds,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(
                        result,
                        ensure_ascii=False,
                    ),
                })

            save_log()

        log["status"] = "unanswered"
        log["reason"] = "round_limit"
        save_log()
        return log, log_path

    except Exception as error:
        log["status"] = "unanswered"

        # Save the error type, without credentials or raw request headers.
        log["error_type"] = type(error).__name__
        save_log()
        raise

DOCUMENT_SYSTEM_PROMPT = """
Answer questions using only the supplied Nine Rivers documents.
Do not invent missing facts.

Use 2025 figures unless another year is requested.
Ignore archived profiles and apply correction notices.
School figures refer to 2025/26.
Use 365 days for 2025.
One megalitre equals 1000 cubic metres or 1000000 litres.
Keep intermediate results unrounded.

End your response with exactly:
ANSWER: <name or yes/no> | <number>

Use the district's exact name or lowercase yes/no.
Use a decimal point and no thousands separators in the final number.
"""


def parse_answer(text):
    """Read the final non-empty line in the required format."""
    if not isinstance(text, str) or not text.strip():
        return None

    final_line = text.strip().splitlines()[-1].strip()

    match = re.fullmatch(
        r"ANSWER:\s*([^|]+?)\s*\|\s*"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)"
        r"(?:[eE][+-]?\d+)?)",
        final_line,
    )

    if match is None:
        return None

    name = match.group(1).strip()
    number = Decimal(match.group(2))

    if not name or not number.is_finite():
        return None

    return name, number


def rounded_number(number, decimals):
    unit = Decimal("1").scaleb(-decimals)
    return number.quantize(unit, rounding=ROUND_HALF_UP)


def load_documents():
    """Load all documents, including archives and corrections."""
    path = ROOT / "data" / "corpus.jsonl"

    documents = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    return "\n\n".join(
        f"[{document['id']}] {document['title']}\n"
        f"{document['text']}"
        for document in documents
    )


def run_document_strategy(question_id, question, decimals, strategy):
    """S1: one sample. S2: five independent samples and voting."""
    if strategy not in ("S1", "S2"):
        raise ValueError("Strategy must be S1 or S2")

    load_dotenv(ROOT / ".env")
    client = OpenAI(timeout=90.0, max_retries=0)

    sample_count = 1 if strategy == "S1" else 5
    documents = load_documents()

    instruction = (
        "Answer the question directly."
        if strategy == "S1"
        else "Solve the problem step by step, then give the final answer."
    )

    messages = [
        {"role": "system", "content": DOCUMENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"DOCUMENTS:\n{documents}\n\n"
                f"QUESTION:\n{question}\n\n"
                f"{instruction}"
            ),
        },
    ]

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )
    log_path = (
        ROOT / "outputs"
        / f"{strategy}_{question_id}_{timestamp}.json"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    log = {
        "question_id": question_id,
        "strategy": strategy,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "reasoning_effort": "none",
        "k": sample_count,
        "decimals_for_voting": decimals,
        "status": "running",
        "input_tokens": 0,
        "output_tokens": 0,
        "messages": messages,
        "samples": [],
        "voting_rule": (
            "Vote on exact name and rounded number. "
            "Invalid samples do not vote. "
            "Break ties by earliest sample among tied answers."
        ),
    }

    started = time.perf_counter()

    def save_log():
        log["total_seconds"] = time.perf_counter() - started
        log_path.write_text(
            json.dumps(log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    save_log()

    try:
        for sample_number in range(1, sample_count + 1):
            sample_started = time.perf_counter()

            # Each sample receives the same original messages.
            # Previous answers are never included.
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                reasoning_effort="none",
                temperature=TEMPERATURE,
            )

            answer = response.choices[0].message.content or ""

            log["samples"].append({
                "sample": sample_number,
                "answer": answer,
                "seconds": time.perf_counter() - sample_started,
                "usage": (
                    response.usage.model_dump()
                    if response.usage else None
                ),
            })

            if response.usage:
                log["input_tokens"] += response.usage.prompt_tokens
                log["output_tokens"] += response.usage.completion_tokens
            else:
                log["usage_incomplete"] = True

            save_log()

        if strategy == "S1":
            log["final_answer"] = log["samples"][0]["answer"]
            log["status"] = (
                "completed"
                if parse_answer(log["final_answer"]) is not None
                else "unanswered"
            )

        else:
            votes = []

            for sample in log["samples"]:
                parsed = parse_answer(sample["answer"])

                if parsed is not None:
                    name, number = parsed
                    votes.append((
                        name,
                        rounded_number(number, decimals),
                    ))

            if votes:
                counts = Counter(votes)
                highest_count = max(counts.values())

                # Deterministic tie-break: earliest tied answer.
                winner = next(
                    vote for vote in votes
                    if counts[vote] == highest_count
                )

                name, number = winner

                log["final_answer"] = f"ANSWER: {name} | {number}"
                log["winning_votes"] = highest_count
                log["valid_samples"] = len(votes)
                log["status"] = "completed"
            else:
                log["final_answer"] = ""
                log["status"] = "unanswered"

        save_log()
        return log, log_path

    except Exception as error:
        log["status"] = "unanswered"
        log["error_type"] = type(error).__name__
        save_log()
        raise


def run_s1(question_id, question, decimals):
    return run_document_strategy(
        question_id, question, decimals, "S1"
    )


def run_s2(question_id, question, decimals):
    return run_document_strategy(
        question_id, question, decimals, "S2"
    )
if __name__ == "__main__":
    questions_path = ROOT / "data" / "questions.json"

    questions = json.loads(
        questions_path.read_text(encoding="utf-8")
    )

    q09 = next(
        question for question in questions
        if question["id"] == "Q-09"
    )

    # Only the question text is sent, never the reference answer.
    result, path = run_s3(q09["id"], q09["question"])

    print("Status:", result["status"])
    print("Answer:", result.get("final_answer", "No answer"))
    print("Input tokens:", result["input_tokens"])
    print("Output tokens:", result["output_tokens"])
    print("Rounds:", len(result["rounds"]))
    print("Log:", path)