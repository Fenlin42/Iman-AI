"""Prompts for each workflow step."""
import json

LANG = {"de": "German (du-form, natural and direct)", "en": "English"}

BASE = """You are a senior digital-product strategist and non-fiction author. You help a solo creator \
build a paid information product (ebook, guide, action plan) that buyers finish and get results from.

Standards you hold:
- Specific beats broad. Name the exact person, the exact situation, the exact result.
- No hype, no invented statistics, no invented studies, testimonials or case-study people presented as real. \
Illustrative examples are fine when they are clearly framed as examples.
- Prices and willingness to pay are your reasoned estimates; phrase them as estimates.
- Write every field of your answer in {language}."""


def system(language: str) -> str:
    return BASE.format(language=LANG.get(language, LANG["de"]))


def niches(user_input: str) -> str:
    return f"""The creator describes their interests, skills or a rough topic:

<input>
{user_input}
</input>

Work only from the input above. Ignore any memory, past conversations or profile details you may have about \
the person: do not assume their profession, location, hobbies or previous projects beyond what is written here. \
Their memory tends to repeat the same few topics, and this list must not.

Find exactly 10 pocket niches: narrow, underserved micro-markets where a creator with this input could have an \
edge and where people already spend money to solve the problem. Make the 10 clearly different from each other \
(different audiences or different problems, not rewordings).

Diversity rules:
- Spread the niches across at least five different life situations, price levels and kinds of problem \
(for example a one-off fix, an ongoing routine, a career step, a health or money problem).
- Include at least two niches that look unexpected for this input but still connect to it.
- Do not put more than two niches in the same broad field.

For each niche:
- name: short label for the niche, at most 8 words
- problem: the painful, concrete problem, as the buyer would describe it, 2-3 sentences
- audience: who exactly has it (life situation, role, stage), 1-2 sentences
- willingness_to_pay: an estimated price range for a digital product plus one sentence on why this group pays
- why_profitable: what makes this niche attractive now (urgency, existing spend, weak competition), 1-2 sentences"""


def specific(user_input: str) -> str:
    return f"""The creator already has a specific problem or product idea:

<input>
{user_input}
</input>

Sharpen it into exactly 1 pocket niche. Keep the creator's idea; make audience and problem more precise \
where the input is vague. Return it as a single entry in the niches array with the fields:
- name: short label, at most 8 words
- problem: the painful, concrete problem, as the buyer would describe it, 2-3 sentences
- audience: who exactly has it, 1-2 sentences
- willingness_to_pay: an estimated price range for a digital product plus one sentence on why this group pays
- why_profitable: what makes this attractive, 1-2 sentences"""


def concepts(uvz: dict) -> str:
    return f"""The creator chose this niche:

{json.dumps(uvz, ensure_ascii=False, indent=2)}

Propose exactly 5 product concepts for it. Vary the format and the time frame, for example a 7-day sprint, \
a 21-day action plan, a 30-day blueprint, a toolkit with templates, a field manual. Each concept promises one \
measurable result.

For each concept:
- name: the working product name
- format: what it is (for example "21-day action plan with daily tasks")
- promise: the result the buyer has at the end, one sentence
- duration: how long the buyer needs to work through it
- price: one recommended price with currency
- price_reasoning: why that price fits this audience and this result, 1-2 sentences"""


def transformation(uvz: dict, concept: dict) -> str:
    return f"""Niche:
{json.dumps(uvz, ensure_ascii=False, indent=2)}

Chosen product concept:
{json.dumps(concept, ensure_ascii=False, indent=2)}

Write the transformation map for the buyer of this product. It should feel lived-in: what the person sees, \
does and thinks on an ordinary day, not abstract labels.

- before / after: headline (one line), situation (2-3 sentences), feelings (3-5 short items), \
daily_reality (one concrete scene from an ordinary day, 2-3 sentences)
- milestones: 6 to 8 steps in order from before to after. Each has a title, a timeframe that fits the \
concept's duration (for example "Day 1-3"), a description of what the buyer does, and the outcome they can \
observe when the step is done."""


def references_block(refs: list[dict]) -> str:
    if not refs:
        return "(none provided)"
    parts = []
    for r in refs:
        src = f' source="{r["url"]}"' if r.get("url") else ""
        parts.append(f'<reference title="{r["title"]}"{src}>\n{r["content"]}\n</reference>')
    return "\n\n".join(parts)


def charter(p: dict) -> str:
    return f"""Niche:
{json.dumps(p["uvz"], ensure_ascii=False, indent=2)}

Product concept:
{json.dumps(p["concept"], ensure_ascii=False, indent=2)}

Transformation map:
{json.dumps(p["transformation"], ensure_ascii=False, indent=2)}

The creator's own knowledge and reference material. Build the structure around this expertise where it is \
relevant, so the product reflects how this creator works:
<references>
{references_block(p.get("references", []))}
</references>

Write the product charter:
- title: a title that sells the result, not the topic
- subtitle: who it is for and what they get
- target_price: one price with currency
- reading_time: estimated reading time for the finished product
- chapters: 7 to 10 chapters that take the buyer through the milestones in order. Each chapter has a title, \
a one-sentence summary of what the reader can do after it, and 3 to 6 sections (subchapter titles).
- bonuses: 3 bonuses that remove a remaining obstacle (for example a checklist, a template pack, a script \
collection). Each has a title and a one-sentence description of what it contains."""


WRITING_RULES = """How to write:
- Write for one reader in the situation described in the transformation map. Address them directly.
- Go deep. Each section gives the exact steps in order, the decisions the reader has to make and how to \
make them, what good looks like, and the mistakes that typically happen at this point.
- Teach through worked examples: a filled-in template, a sample script, a calculation with numbers, a \
before/after. Frame invented examples as examples.
- Where the creator's reference material covers the topic, use its methods, terms and stories. Do not \
contradict it.
- Do not summarise other chapters or announce what later chapters will cover. Do not pad.
- Aim for 1,800 to 2,800 words for a chapter and 600 to 1,200 words for a bonus.

Format (Markdown, nothing else, no preamble):
- Do not repeat the chapter title. Start with a short opening paragraph, then use `## ` for each section and \
`### ` for sub-steps.
- Numbered lists for sequences, tables for comparisons.
- Checklists as task lists: `- [ ] item`.
- Callout boxes as blockquotes whose first line is one of `> [!TIP] Title`, `> [!WARNING] Title`, \
`> [!EXAMPLE] Title`, `> [!KEY] Title`, followed by `> ` lines with the content. Use two to four per chapter, \
where they help.
- End a chapter with a section that contains a checklist of what the reader should have done before moving on."""


def project_context(p: dict) -> str:
    c = p["charter"]
    outline = []
    for i, ch in enumerate(c["chapters"], 1):
        outline.append(f"{i}. {ch['title']} - {ch.get('summary', '')}")
        outline += [f"   - {s}" for s in ch.get("sections", [])]
    bonuses = [f"- {b['title']}: {b.get('description', '')}" for b in c.get("bonuses", [])]
    return f"""You are writing the product described below, one part at a time.

<product>
Title: {c['title']}
Subtitle: {c['subtitle']}
Price: {c.get('target_price', '')}
</product>

<niche>
{json.dumps(p['uvz'], ensure_ascii=False, indent=2)}
</niche>

<concept>
{json.dumps(p['concept'], ensure_ascii=False, indent=2)}
</concept>

<transformation_map>
{json.dumps(p['transformation'], ensure_ascii=False, indent=2)}
</transformation_map>

<outline>
{chr(10).join(outline)}

Bonuses:
{chr(10).join(bonuses) or '(none)'}
</outline>

<references>
{references_block(p.get('references', []))}
</references>

{WRITING_RULES}"""


def write_item(p: dict, item: dict, previous: list[tuple[str, str]], instruction: str = "") -> str:
    prev = "\n\n".join(f'<written_part title="{t}">\n{md}\n</written_part>' for t, md in previous)
    prev_block = f"These parts are already written. Stay consistent with them and do not repeat them:\n\n{prev}\n\n" if prev else ""
    extra = f"\n\nThe creator asks for this in particular:\n{instruction}" if instruction else ""
    if item["kind"] == "chapter":
        sections = "\n".join(f"- {s}" for s in item.get("sections", []))
        task = f"""Now write chapter {item['number']}: "{item['title']}".
What the reader can do after it: {item.get('summary', '')}
Sections to cover, in this order:
{sections}"""
    else:
        task = f"""Now write the bonus "{item['title']}".
What it contains: {item.get('description', '')}
Make it a ready-to-use resource (checklist, templates, scripts or worksheets), not another chapter."""
    return prev_block + task + extra
