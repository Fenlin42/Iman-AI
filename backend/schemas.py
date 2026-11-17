"""JSON schemas for the structured AI steps."""


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def _arr(items: dict) -> dict:
    return {"type": "array", "items": items}


S = {"type": "string"}

NICHE = _obj({
    "name": S,
    "problem": S,
    "audience": S,
    "willingness_to_pay": S,
    "why_profitable": S,
    "demand_signal": S,
})
NICHES = _obj({"niches": _arr(NICHE)})

CONCEPT = _obj({
    "name": S,
    "format": S,
    "promise": S,
    "duration": S,
    "price": S,
    "price_reasoning": S,
})
CONCEPTS = _obj({"concepts": _arr(CONCEPT)})

_STATE = _obj({"headline": S, "situation": S, "feelings": _arr(S), "daily_reality": S})
TRANSFORMATION = _obj({
    "before": _STATE,
    "after": _STATE,
    "milestones": _arr(_obj({"title": S, "timeframe": S, "description": S, "outcome": S})),
})

CHARTER = _obj({
    "title": S,
    "subtitle": S,
    "target_price": S,
    "reading_time": S,
    "chapters": _arr(_obj({"title": S, "summary": S, "sections": _arr(S)})),
    "bonuses": _arr(_obj({"title": S, "description": S})),
})
