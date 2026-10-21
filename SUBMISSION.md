# HW4 — submission

**AI assistance:** I used ChatGPT to help plan the tools, understand the task, and prepare and explain the Python code. Experimental results and conclusions will come from my own runs.

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

I explicitly set reasoning_effort="none" because the API rejected
function tools with the model's default reasoning setting in Chat
Completions. I will use the same setting for all three strategies.

### B2 — Tests

```text
<!-- pytest output -->notice] To update, run: python.exe -m pip install --upgrade pip
(.venv) PS C:\Users\Admin\PycharmProjects\css4007-hw4> New-Item -ItemType Directory -Force outputs


    Каталог: C:\Users\Admin\PycharmProjects\css4007-hw4


Mode                 LastWriteTime         Length Name                            
----                 -------------         ------ ----
d-----        10/21/2026   8:28 PM                outputs


(.venv) PS C:\Users\Admin\PycharmProjects\css4007-hw4> python -m pytest tests -v 2>&1 | Tee-Object -FilePath outputs/pytest.txt
platform win32 -- Python 3.13.2, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\Admin\PycharmProjects\css4007-hw4\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Admin\PycharmProjects\css4007-hw4
plugins: anyio-4.15.1
collecting ... collected 34 items

tests/test_tools.py::test_lookup_current_population PASSED               [  2%]    
tests/test_tools.py::test_lookup_similar_names_are_separate PASSED       [  5%]    
tests/test_tools.py::test_lookup_ambiguous_name PASSED                   [  8%]    
tests/test_tools.py::test_lookup_misspelled_name PASSED                  [ 11%]    
tests/test_tools.py::test_lookup_archived_profile[NR-13-NR-03] PASSED    [ 14%]    
tests/test_tools.py::test_lookup_archived_profile[NR-14-NR-04] PASSED    [ 17%]    
tests/test_tools.py::test_lookup_includes_correction[Brightwater] PASSED [ 20%]    
tests/test_tools.py::test_lookup_includes_correction[NR-05] PASSED       [ 23%]    
tests/test_tools.py::test_lookup_water_tariff PASSED                     [ 26%]    
tests/test_tools.py::test_lookup_invalid_input[] PASSED                  [ 29%]    
tests/test_tools.py::test_lookup_invalid_input[   ] PASSED               [ 32%]
tests/test_tools.py::test_lookup_invalid_input[None] PASSED              [ 35%]    
tests/test_tools.py::test_lookup_invalid_input[123] PASSED               [ 38%]    
tests/test_tools.py::test_lookup_invalid_input[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx] PASSED [ 41%]
tests/test_tools.py::test_lookup_missing_corpus PASSED                   [ 44%]    
tests/test_tools.py::test_lookup_invalid_corpus PASSED                   [ 47%]
tests/test_tools.py::test_calculate_multiplication PASSED                [ 50%]    
tests/test_tools.py::test_calculate_q09 PASSED                           [ 52%]    
tests/test_tools.py::test_calculate_parentheses_and_unary_minus PASSED   [ 55%]    
tests/test_tools.py::test_calculate_division_by_zero PASSED              [ 58%]    
tests/test_tools.py::test_calculate_rejects_dangerous_input[__import__('os').system('echo hi')] PASSED [ 61%]
tests/test_tools.py::test_calculate_rejects_dangerous_input[(1).__class__] PASSED [ 64%]
tests/test_tools.py::test_calculate_rejects_dangerous_input[9**9**9] PASSED [ 67%] 
tests/test_tools.py::test_calculate_does_not_execute_commands PASSED     [ 70%]    
tests/test_tools.py::test_calculate_invalid_syntax PASSED                [ 73%]    
tests/test_tools.py::test_calculate_invalid_input[] PASSED               [ 76%]    
tests/test_tools.py::test_calculate_invalid_input[   ] PASSED            [ 79%]    
tests/test_tools.py::test_calculate_invalid_input[None] PASSED           [ 82%]    
tests/test_tools.py::test_calculate_invalid_input[123] PASSED            [ 85%]    
tests/test_tools.py::test_calculate_invalid_input[111111111111111111111111111111111
11111111111111111111111111111111111111111111111111111111111111111111111111111111111
1111111111111111111111111111111111111111111111111111111111111111111111111111111111111] PASSED [ 88%]
tests/test_tools.py::test_calculate_numeric_limit[1000000000000001] PASSED [ 91%]  
tests/test_tools.py::test_calculate_numeric_limit[1000000000 * 1000000000] PASSED [ 94%]
tests/test_tools.py::test_calculate_numeric_limit[1e309] PASSED          [ 97%]    
tests/test_tools.py::test_calculate_rejects_boolean PASSED               [100%]

(.venv) PS C:\Users\Admin\PycharmProjects\css4007-hw4> 

```

### B3 — The loop

- Round limit: 12 model calls per question. This allows several retrieval
  and calculation steps while preventing an endless loop.
- Logs are saved as JSON files in outputs/.
- The Q-09 log is outputs/S3_Q-09_20261021T153310_231554Z.json.

The real conversation used 4 model calls and 5 tool calls:
two lookup calls and three calculate calls.

In round 1, the model requested Brightwater and Millbrook.
Lookup returned the Brightwater correction notice together with its
profile. The model correctly used the corrected area of 921.4 km².

In round 2, it calculated each density separately:
44675 / 921.4 = 48.48599956587801;
37203 / 758.6 = 49.041655681518584.

In round 3, it calculated the difference:
37203 / 758.6 - 44675 / 921.4 = 0.5556561156405735.

In round 4, it returned Millbrook as the answer.
The difference rounds to 0.6 residents per km².

My manual example used one calculation call for the difference.
The real model first calculated both densities separately, adding
two calculator calls and one extra model round.
Both conversations reached the same result.

The real answer was unrounded, while my manual answer was rounded.
The run used 3,185 input tokens and 178 output tokens.
Total elapsed time was approximately 11.92 seconds.

Input tokens increased across rounds: 442, 833, 928 and 982.
Each new request included the previous messages and tool results.

### B4 — Three strategies

**What I kept the same:**

All strategies use gpt-5.6-luna through Chat Completions,
temperature=0.7 and reasoning_effort="none".

They use the same questions, factual assumptions, answer format and
evaluation rule. Reference answers are never sent to the model.

S1 and S2 receive all 17 documents. S1 makes one call.
S2 requests a step-by-step solution in five independent calls.
Voting uses the exact name and rounded number. Ties are resolved
by choosing the earliest sample among tied answers.

S3 receives the tools instead of the documents and has a limit
of 12 model calls per question.

The earlier Q-09 demonstration used the default temperature.
It is a pilot and is excluded from the full-run comparison.

**My rule for a correct answer** (written before the first full run):
Read the final ANSWER line. The name must match the reference answer
exactly after removing surrounding whitespace.

Round the predicted number and reference value to the question's
specified number of decimals. Accept an absolute difference of at
most 10^(-decimals), allowing one unit in the last decimal place.

Missing or invalid ANSWER lines, API failures and round-limit failures
count as unanswered and incorrect.

Reference answers are used only for evaluation, never in model prompts.

| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | S1 direct | 2/20 | 4 | 45000 | 577 | 2.701 | 56.354 | Pending |
| 1 | S2 think and vote (k = 5) | 16/20 | 0 | 225800 | 14997 | 17.639 | 357.950 | Pending |
| 1 | S3 tools | 20/20 | 0 | 55818 | 3208 | 6.441 | 166.961 | Pending |
| 2 | S1 direct | 4/20 | 2 | 45000 | 632 | 2.914 | 67.794 | Pending |
| 2 | S2 think and vote (k = 5) | 16/20 | 0 | 225800 | 14960 | 19.352 | 407.156 | Pending |
| 2 | S3 tools | 20/20 | 0 | 57052 | 3070 | 5.789 | 135.341 | Pending |


**Per question (run 1):**
| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | ✗ | ✓ | ✓ |
| Q-02 | ✗ | ✓ | ✓ |
| Q-03 | ✗ | ✓ | ✓ |
| Q-04 | ✗ | ✓ | ✓ |
| Q-05 | ✗ | ✗ | ✓ |
| Q-06 | ✗ | ✓ | ✓ |
| Q-07 | ✗ | ✓ | ✓ |
| Q-08 | ✗ | ✗ | ✓ |
| Q-09 | ✗ | ✓ | ✓ |
| Q-10 | ✓ | ✓ | ✓ |
| Q-11 | ✗ | ✓ | ✓ |
| Q-12 | ✗ | ✗ | ✓ |
| Q-13 | ✗ | ✓ | ✓ |
| Q-14 | ✗ | ✓ | ✓ |
| Q-15 | ✗ | ✓ | ✓ |
| Q-16 | ✓ | ✓ | ✓ |
| Q-17 | ✗ | ✓ | ✓ |
| Q-18 | ✗ | ✓ | ✓ |
| Q-19 | ✗ | ✓ | ✓ |
| Q-20 | ✗ | ✗ | ✓ |

---

## Part C — Explain and choose (Hard)

### C1 — Does the tool description matter?

I tested five questions with the original lookup description and with
the vague description "Looks things up." All other settings and tool
parameters stayed the same.

Calls in the table mean tool calls, not model requests.

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| Q-01 | 5 | 2 | Ossbridge, 4.570154 — correct | no, 0 — incorrect |
| Q-03 | 3 | 3 | Kelmarsh, 5.340159 — incorrect | unknown, 0 — incorrect |
| Q-09 | 5 | 7 | Millbrook, 0.555656 — correct | Millbrook, 0.555656 — correct |
| Q-17 | 4 | 3 | Harrowfield, 884.457162 — correct | unknown, 0 — incorrect |
| Q-20 | 7 | 3 | Ashgrove, 2993.342836 — correct | unknown, 0 — incorrect |

The detailed description achieved 4/5 correct answers.
The vague description achieved 1/5.

The inputs show an important difference. For Q-01, the detailed
version used:
{"query": "Ossbridge"}

The vague version used:
{"query": "Ossbridge 2025 population and area population density"}

My lookup supports exact district names, document IDs and "water tariff",
rather than general keyword searches. The longer query did not match
its supported inputs. The vague version then stopped without the facts.

For Q-09, the vague version first used long queries, then recovered
by requesting "Brightwater" and "Millbrook". Both versions answered
correctly, but the vague version needed seven tool calls instead of
five and took 24.31 seconds instead of 9.54 seconds.

For Q-17, the detailed version requested "Harrowfield", "Ossbridge"
and "water tariff". The vague version used long search phrases and
did not reach the calculation stage.

The detailed description did not prevent every error. On Q-03,
the model calculated Lindenmoor minus Kelmarsh:

2151400000/(29051*365)-1739000000/(24117*365)

The positive result was 5.34015866513721, meaning Lindenmoor used
more water per resident per day. However, the final answer named
Kelmarsh. The arithmetic was correct, but the model interpreted
the comparison incorrectly.

The detailed version used 24 tool calls in total; the vague version
used 18. Fewer calls were not evidence of better performance because
the vague version often stopped before calculating.

These results suggest that clear descriptions help the model select
valid inputs. However, there were only five questions and one trial
per description per question at temperature=0.7. Random variation
may explain some differences.
### C2 — Three mistakes explained
#### S1: Q-09, run 1

The log returned:

"ANSWER: Brightwater | 10.2461"

The correct answer is Millbrook, with a difference of approximately
0.6 residents per km². The model returned both the wrong district
and the wrong difference despite receiving all documents.

The answer contains no intermediate calculations, so I cannot
determine exactly which figures it used. It may have misread the
facts or performed incorrect arithmetic. The log does not establish
that the correction notice alone caused the error.

#### S2: Q-05, run 1

The first sample returned:

"ANSWER: Coldharbour | 14206.9439799035"

All five samples selected Coldharbour, but their rounded differences
were 14207, 14245, 14234, 14255 and 14223.

Each answer received one vote. My predefined tie-break selected
the first sample, producing:

"ANSWER: Coldharbour | 14207"

The correct rounded difference is 14235 tenge per resident.
The samples used the relevant budget and population figures but
made arithmetic errors. Repeated sampling did not produce agreement.

Voting can help when correct answers recur more often than incorrect
ones. It cannot guarantee a correct result when calculations vary
or the same mistake is repeated. A calculator evaluates the supplied
formula reliably, although the model must still choose the right
formula and interpret its result.

#### S3: Q-11, run 1 — highest token use

S3 answered every question correctly in both full runs, so I examined
Q-11, which used the most tokens in S3.

It retrieved Redfen, Ashgrove and Millbrook, then made four separate
calculator calls:

- 8837/24 → 368.2083333333333
- 5562/15 → 370.8
- 3147/10 → 314.7
- 370.8-314.7 → 56.10000000000002

The final answer was:

"ANSWER: Redfen | 56.1"

The model used six rounds: one retrieval round, four calculation
rounds and one final-answer round. Some independent calculations
could have been requested together.

The run used 5,570 input tokens and 192 output tokens.
Input tokens per round were 457, 944, 985, 1022, 1059 and 1103.
Each request included previous messages and tool results, so the
conversation became longer.
### C3 — Which strategy I would use, and what would change it
I would choose S3 for this problem. It answered 20/20 questions
correctly in both runs. S2 answered 16/20, while S1 answered
2/20 and 4/20.

S3 used approximately 59,000–60,000 total tokens per run,
compared with approximately 241,000 for S2. Its median time per
question was 6.441 and 5.789 seconds, compared with 17.639 and
19.352 seconds for S2.

I did not choose S1 because its speed and lower token use came
with poor accuracy. I did not choose S2 because it used many
more tokens and more time than S3 while still making errors.

My choice could change in these situations:

- For simple questions without arithmetic, a short corpus and a strict
  time limit, I would test S1 first because it needs only one call.
- For a much larger corpus, I would keep S3 but replace the current
  lookup with indexed retrieval and metadata filters.
- If tools were unavailable and accuracy mattered more than time,
  I would consider S2 after validating it on representative questions.

These choices would require new tests because my results apply
to the current corpus and questions.
### C4 — How sure I can be
S1 changed from 2/20 to 4/20 correct, a difference of 10 percentage
points. Its unanswered count decreased from four to two.

S2 scored 16/20 in both runs and failed the same four questions:
Q-05, Q-08, Q-12 and Q-20. S3 scored 20/20 in both runs.
The accuracy gap between S3 and S2 was 20 percentage points,
larger than the observed between-run change for any strategy.

However, two runs on the same 20 questions are limited evidence.
They are repeated trials, not 40 independent questions.
The C1 experiment also showed that S3 can make an interpretation
error even with the detailed description.

Before trusting the conclusion more broadly, I would test at least
100–200 new, varied questions and repeat the comparison.
This is a practical starting point, not a guaranteed sample size.
The required number depends on the accuracy difference I want
to detect and the uncertainty I can accept.
### Final questions

1. Only model inference has run. The model has produced tool names
   and arguments, but the requested functions have not executed.
   My Python loop validates the requests and runs the tools.

2. The API represents arguments as JSON text inside a string.
   My loop uses json.loads and checks the resulting dictionary.
   Passing the raw string directly would give the function the wrong
   input type or fail to unpack the required keyword arguments.

3. I measured tool-related overhead using identical messages with
   and without the two tool definitions. Input usage increased from
   10 to 287 tokens, a difference of 277 tokens.
   The tools condition used tool_choice="none", so this measures
   overhead for that configuration; it is not a separate charge
   to add to the recorded S3 usage.
4. 
4. To be completed using the API prices and saved usage.

5. Q-11 needed the most S3 rounds: six in both full runs.
   The model retrieved three profiles, calculated three pupil-to-school
   ratios separately, calculated their difference and gave the answer.

6. For 100,000 documents, I would use an indexed database with
   exact-name matching and keyword or semantic retrieval.
   Metadata filters would select current documents, while correction
   links would preserve precedence. I would still return short excerpts
   with source IDs.

7. The calculator allows only specific AST nodes and arithmetic
   operators, without eval or exec. It limits input length, AST size
   and numeric magnitude. The model can still submit a wrong formula,
   trigger errors or interpret a correct result incorrectly.

8. Tools helped most with multi-step arithmetic, unit conversion
   and questions requiring corrected facts, such as Q-03 and Q-09.
   They did not improve full-run accuracy on Q-10 or Q-16 because
   S1 already answered these correctly in both runs, although tools
   added time and tokens.