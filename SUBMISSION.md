# HW4 — submission

**AI assistance:** AI assistance: I used ChatGPT to help plan the tools, understand the task, and prepare and explain the Python code. Experimental results and conclusions will come from my own runs.

---

## Part A — Plan on paper (Easy)

> Commit this whole part before any `.py` file exists.

### A1 — The steps

| # | Step | What goes in (types) | What comes out (types) | When it goes wrong | Tool, loop, or model? |
|---|---|---|---|---|---|
| 1 | Understand the question | question: str | district names: list[str], required facts: list[str], calculation plan: str | If the question is unclear, do not guess. | Model |
| 2 | Retrieve facts | query: str | matches with document IDs: dict | Return an error for missing, ambiguous or archived results. Suggest possible district names for misspellings. | lookup tool |
| 3 | Read values and units | retrieved facts: dict | values: list[float], units: list[str] | If a number cannot be read or a unit is unknown, retrieve more information. Do not invent values. | Model |
| 4 | Prepare arithmetic | values and units | expression: str | Convert units before comparing values. Use corrected figures. | Model |
| 5 | Calculate | expression: str | result: float, or error: dict | Reject forbidden syntax, division by zero and excessive numbers. | calculate tool |
| 6 | Compare and answer | calculation results | final answer: str | Round only the final result. Follow the required answer format. | Model |
| 7 | Control the conversation | model messages and tool requests | updated messages: list[dict], logs: list[dict] | Validate JSON arguments, return a result for every tool call and enforce a round limit. | Loop |


**How the steps connect:**

Question → identify districts and required facts → lookup → read values
and units → prepare arithmetic → calculate → compare → final answer.

The loop manages model calls and tool results throughout this process.



**What I am assuming:**

- Use the 2025 census population unless the question asks for another year.
- Population growth uses the 2020 and 2025 censuses.
- Budgets and household water use refer to 2025.
- School and pupil figures refer to 2025/26.
- Archived profiles are excluded from current-data retrieval.
- Correction notices override the original figures.
- Brightwater's corrected area is 921.4 square kilometres.
- One megalitre equals 1,000 cubic metres or 1,000,000 litres.
- Use 365 days when calculating daily water use in 2025.
- Keep intermediate values unrounded and round only the final answer.
- If a required fact remains unavailable, mark the question as unanswered.

### A2 — The two tools

#### `lookup`

```json
{
  "type": "function",
  "function": {
    "name": "lookup",
    "description": "Find current facts in the Nine Rivers corpus. Use an exact district name, a document ID, or the phrase water tariff. Return limited text with source document IDs. Archived profiles are excluded. District results include relevant correction notices; corrections override original figures. A misspelled or ambiguous query returns an error with suggestions instead of choosing a district.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "An exact district name, a document ID, or water tariff."
        }
      },
      "required": ["query"],
      "additionalProperties": false
    }
  }
}
```

| Case | What the tool returns |
|---|---|
| Success | `{"matches": [{"doc_id": "...", "text": "..."}]}` |
| No match or misspelled name | `{"error": "not_found", "suggestions": [...]}` |
| Ambiguous query | `{"error": "ambiguous_query", "suggestions": [...]}` |
| Archived document requested | `{"error": "archived_document", "replacement": "..."}` |
| Empty, non-string or excessive input | `{"error": "invalid_query"}` |
| Missing or invalid corpus | `{"error": "corpus_unavailable"}` |
Return at most three matches and limit each text to 900 characters.
A district lookup returns its current profile and relevant corrections.
A lookup by current profile ID also includes relevant corrections.

**Worst thing it could do with strange or dangerous input:**
It could return irrelevant or incomplete information, leading to an
incorrect answer. Input is treated only as search text. It cannot execute
commands, change files or access paths supplied by the model.

#### `calculate`

```json
{
  "type": "function",
  "function": {
    "name": "calculate",
    "description": "Calculate arithmetic using numeric literals, parentheses, addition, subtraction, multiplication and division. Unary plus and minus are allowed. Names, function calls, attributes and powers are forbidden. Use this tool for arithmetic after retrieving facts and converting units. Returns a numeric result or a structured error.",
    "parameters": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "An arithmetic expression, for example 44675 / 921.4."
        }
      },
      "required": ["expression"],
      "additionalProperties": false
    }
  }
}
```

| Case | What the tool returns |
|---|---|
| Success | `{"result": number}` |
| Empty, non-string or excessive input | `{"error": "invalid_expression"}` |
| Invalid syntax | `{"error": "invalid_syntax"}` |
| Forbidden operations or Python objects | `{"error": "unsupported_expression"}` |
| Division by zero | `{"error": "division_by_zero"}` |
| Excessive or non-finite number | `{"error": "numeric_limit"}` |


Use ast.parse and allow only numeric constants, addition, subtraction,
multiplication, division and unary plus or minus. Reject booleans.

Limit input to 200 characters and 80 AST nodes. Reject any literal,
intermediate result or final result with an absolute value above 10^15.
Reject non-finite values. Do not use eval or exec.

**Worst thing it could do with strange or dangerous input:**

The model could provide an incorrect formula or trigger an error.
The calculator validates syntax but cannot know whether a formula
answers the question. Input limits and the AST allowlist prevent
arbitrary code execution and restrict computational work.

### A3 — Q-09 by hand
This is a planned conversation, not an actual model run.
Retrieved excerpts are shortened for this manual example.

```json
[
  {
    "role": "user",
    "content": "Which district has the higher population density in 2025, Brightwater or Millbrook, and by how many residents per square kilometre?"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_1",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"query\":\"Brightwater\"}"
        }
      },
      {
        "id": "call_2",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"query\":\"Millbrook\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_1",
    "content": "{\"matches\":[{\"doc_id\":\"NR-05\",\"text\":\"Brightwater's population was 44,675 in 2025. The original profile gives an area of 912.4 square kilometres.\"},{\"doc_id\":\"NR-16\",\"text\":\"The correct Brightwater area is 921.4 square kilometres. All other figures are correct.\"}]}"
  },
  {
    "role": "tool",
    "tool_call_id": "call_2",
    "content": "{\"matches\":[{\"doc_id\":\"NR-11\",\"text\":\"Millbrook covers 758.6 square kilometres and had 37,203 residents in 2025.\"}]}"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_3",
        "type": "function",
        "function": {
          "name": "calculate",
          "arguments": "{\"expression\":\"37203 / 758.6 - 44675 / 921.4\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_3",
    "content": "{\"result\":0.5556561156405735}"
  },
  {
    "role": "assistant",
    "content": "ANSWER: Millbrook | 0.6"
  }
]
```

**My arithmetic:**
Population density = population / area.

Brightwater:
44,675 / 921.4 = approximately 48.48599956587801 residents per km².

Millbrook:
37,203 / 758.6 = approximately 49.041655681518584 residents per km².

Difference:
37,203 / 758.6 − 44,675 / 921.4
= approximately 0.5556561156405735 residents per km².

Rounded to one decimal place, the difference is 0.6 residents per km².

Millbrook has the higher population density.
Using Brightwater's corrected area is essential.


### A4 — Why I split it this way

Another option is one large tool that retrieves facts, performs
calculations and returns the final answer.

I chose separate lookup and calculate tools because their results are
easier to inspect and test. Lookup provides evidence with source IDs.
Calculate performs arithmetic safely. The model decides which facts
and calculations are needed, while the loop controls execution.


---

## Part B — Build it and run it (Medium)

### What I changed from Part A while coding

<!-- what changed in your plan, and why. "None" is an answer too. -->

### B2 — Tests

```text
<!-- pytest output -->
```

### B3 — The loop

- Round limit, and why:
- Where the logs are:
- Real Q-09 conversation compared with my A3 version, what is different:

### B4 — Three strategies

**What I kept the same:**

<!-- model, temperature, k, prompts, answer format, anything else -->

**My rule for a correct answer** (written before the first full run):

| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | S1 direct | | | | | | | |
| 1 | S2 think and vote (k = ) | | | | | | | |
| 1 | S3 tools | | | | | | | |
| 2 | S1 direct | | | | | | | |
| 2 | S2 think and vote (k = ) | | | | | | | |
| 2 | S3 tools | | | | | | | |

**Per question (run 1):**

| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | | | |
| Q-02 | | | |
| Q-03 | | | |
| Q-04 | | | |
| Q-05 | | | |
| Q-06 | | | |
| Q-07 | | | |
| Q-08 | | | |
| Q-09 | | | |
| Q-10 | | | |
| Q-11 | | | |
| Q-12 | | | |
| Q-13 | | | |
| Q-14 | | | |
| Q-15 | | | |
| Q-16 | | | |
| Q-17 | | | |
| Q-18 | | | |
| Q-19 | | | |
| Q-20 | | | |

---

## Part C — Explain and choose (Hard)

### C1 — Does the tool description matter?

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| | | | | |

### C2 — Three mistakes explained

### C3 — Which strategy I would use, and what would change it

### C4 — How sure I can be

### Final questions

1.
2.
3.
4.
5.
6.
7.
8.
