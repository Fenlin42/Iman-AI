"""Copy mode: the user runs the prompt in their own Claude chat and pastes the answer back."""
import json
import re

FORMAT_NOTE = """Answer with exactly one JSON code block and nothing else. Use this structure \
(the "..." are placeholders, arrays hold as many entries as the task asks for):

```json
{skeleton}
```"""

MARKDOWN_NOTE = "Reply with the Markdown text only: no introduction, no closing remark, no code fence around it."


class ManualError(Exception):
    """Pasted answer could not be used; the message is shown to the user."""


def _skeleton(schema: dict):
    if schema["type"] == "object":
        return {k: _skeleton(v) for k, v in schema["properties"].items()}
    if schema["type"] == "array":
        return [_skeleton(schema["items"])]
    return "..."


def structured_prompt(system: str, user: str, schema: dict) -> str:
    skeleton = json.dumps(_skeleton(schema), ensure_ascii=False, indent=2)
    return f"{system}\n\n{user}\n\n{FORMAT_NOTE.format(skeleton=skeleton)}"


def writing_prompt(system: str, context: str, user: str) -> str:
    return f"{system}\n\n{context}\n\n{user}\n\n{MARKDOWN_NOTE}"


def _clean(value, schema: dict, path: str):
    """Check the pasted data against the schema; drops unknown keys."""
    kind = schema["type"]
    if kind == "string":
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            raise ManualError(f"„{path}“ muss ein Text sein.")
        return str(value)
    if kind == "array":
        if not isinstance(value, list) or not value:
            raise ManualError(f"„{path}“ muss eine Liste mit mindestens einem Eintrag sein.")
        return [_clean(v, schema["items"], f"{path}[{i + 1}]") for i, v in enumerate(value)]
    if not isinstance(value, dict):
        raise ManualError(f"„{path or 'Antwort'}“ hat nicht die erwartete Struktur.")
    out = {}
    for key, sub in schema["properties"].items():
        if key not in value:
            raise ManualError(f"In der Antwort fehlt das Feld „{f'{path}.{key}' if path else key}“.")
        out[key] = _clean(value[key], sub, f"{path}.{key}" if path else key)
    return out


def parse_structured(text: str, schema: dict) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ManualError("In der eingefügten Antwort wurde kein JSON gefunden. Bitte die komplette Antwort kopieren.")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        raise ManualError("Das JSON in der Antwort ist unvollständig oder fehlerhaft. Bitte die komplette Antwort kopieren.")
    return _clean(data, schema, "")


def parse_markdown(text: str) -> str:
    text = text.strip()
    m = re.fullmatch(r"```[\w-]*\n(.*)\n```", text, flags=re.S)
    return (m.group(1) if m and "```" not in m.group(1) else text).strip()
