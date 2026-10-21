TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": (
                "Find current facts in the Nine Rivers corpus. "
                "Use an exact district name, a document ID, or the phrase "
                "water tariff. Return limited text with source document IDs. "
                "Archived profiles are excluded. District results include "
                "relevant correction notices; corrections override original "
                "figures. A misspelled or ambiguous query returns an error "
                "with suggestions instead of choosing a district."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "An exact district name, a document ID, "
                            "or water tariff."
                        ),
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Calculate arithmetic using numeric literals, parentheses, "
                "addition, subtraction, multiplication and division. "
                "Unary plus and minus are allowed. Names, function calls, "
                "attributes and powers are forbidden. Use this tool for "
                "arithmetic after retrieving facts and converting units. "
                "Returns a numeric result or a structured error."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "An arithmetic expression, "
                            "for example 44675 / 921.4."
                        ),
                    }
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
]