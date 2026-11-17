"""Prompts for each workflow step."""
import json

LANG = {"de": "German (du-form, natural and direct)", "en": "English"}

BASE = """You are a senior digital-product strategist and non-fiction author. You help a solo creator \
build a paid information product (ebook, guide, action plan) that buyers finish and get results from.

How the creator works (synthesis model): they do not claim to be an expert and give no advice of their own. \
Solutions usually exist already, scattered across studies, official data and expert publications. The product's \
value is bringing that verified knowledge into one short, usable guide and saying where each point comes from.

Standards you hold:
- Specific beats broad. Name the exact person, the exact situation, the exact result.
- No hype, no invented statistics, no invented studies, testimonials or case-study people presented as real. \
Illustrative examples are fine when they are clearly framed as examples.
- No promises of healing, income or returns.
- Short beats long: buyers pay for the transformation from A to B, not for page count.
- Prices and willingness to pay are your reasoned estimates; phrase them as estimates.
- Write every field of your answer in {language}."""


def system(language: str) -> str:
    return BASE.format(language=LANG.get(language, LANG["de"]))


NICHE_FIELDS = """For each niche:
- name: short label for the niche, at most 8 words
- problem: the painful, concrete problem, as the buyer would describe it, 2-3 sentences
- audience: who exactly has it (life situation, role, stage), 1-2 sentences
- willingness_to_pay: an estimated price range for a digital product plus one sentence on why this group pays
- why_profitable: what makes this niche attractive now (urgency, existing spend), 1-2 sentences
- supply_gap: what already exists for this audience (paid products and good free material from authorities, \
associations or companies) and why there is still room; say plainly if the market looks crowded
- demand_signal: the concrete evidence that people pay for this (existing paid products, active communities, \
search behaviour). Name what you found or know; if it is your estimate and not something you checked, say so. \
Do not invent numbers."""


def _seen_block(seen: list[str]) -> str:
    if not seen:
        return ""
    names = "\n".join(f"- {n}" for n in seen)
    return f"""

These niches were already shown to the creator. Do not repeat them or close variants of them; find different \
audiences and different problems:
{names}"""


def market(direction: str, seen: list[str]) -> str:
    wish = f"""

The creator gave this constraint or direction. Respect it:
<direction>
{direction}
</direction>""" if direction.strip() else ""
    return f"""The creator has no topic preference and claims no special expertise. Their only criterion is demand: \
they will make a product on any subject, as long as people want it and pay for it. Choosing the markets is your job.

Find exactly 10 pocket niches: narrow, underserved micro-markets with buyers. Spread them across clearly \
different markets (for example animals and pets, hobbies and crafts, home and garden, career and side income, \
parenting, travel, sport, everyday technology, relationships, organisation), with at most two from the same market.

Choose by these criteria:
- Pain before pleasure: the strongest sellers are problems in money, health and relationships, above all ones \
that get worse when ignored. Look there first, without neglecting other markets.
- People already spend money on the problem (books, courses, apps, coaching, equipment).
- One specific, painful problem or strongly wanted result, for a clearly defined group under personal pressure.
- A real gap: paying demand AND weak supply. Few good products for this exact group, and no good free \
alternative from an authority, association or software company. Many near-identical titles mean it is too late.
- Check the language gap: a market that is full in English may still be open in German.
- The group can be reached online (communities, search, marketplaces).
- Lasting demand, not a short-lived fad.
- Solid published sources exist (studies, official data, expert guidelines), because the product will be a \
synthesis of them, not the author's own advice.
- In health, money and legal topics the product informs and summarises; it makes no promise of healing or \
returns. Leave out only what stays risky even as a summary: medication and dosing decisions, treating serious \
illness, individual legal or tax cases, specific investment picks.

If you have a web search tool, use it before deciding: check current demand signals such as bestseller lists, \
marketplaces for digital products and courses, and forum or search activity, and base demand_signal on what you \
found. If you cannot search, work from what you know and say in demand_signal that it is an estimate.{wish}{_seen_block(seen)}

{NICHE_FIELDS}"""


def niches(user_input: str, seen: list[str]) -> str:
    return f"""The creator describes their interests, skills or a rough topic:

<input>
{user_input}
</input>

Find exactly 10 pocket niches: narrow, underserved micro-markets where this creator has a credible edge and \
where people already spend money to solve the problem. Make the 10 clearly different from each other \
(different audiences or different problems, not rewordings).{_seen_block(seen)}

{NICHE_FIELDS}"""


def specific(user_input: str) -> str:
    return f"""The creator already has a specific problem or product idea:

<input>
{user_input}
</input>

Sharpen it into exactly 1 pocket niche. Keep the creator's idea; make audience and problem more precise \
where the input is vague. Return it as a single entry in the niches array.

{NICHE_FIELDS}"""


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
- chapters: 5 to 7 chapters that take the buyer through the milestones in order; the finished product should \
be a strong 20 to 30 pages, not a long book. Each chapter delivers one action or result and has a title, a \
one-sentence summary of what the reader can do after it, and 2 to 4 sections (subchapter titles).
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
- Sources: the product summarises what studies, official data and experts say. Build factual claims on the \
sources in the references and name the source in the sentence or in brackets (institution or first author, \
year). Never invent a study, a number, an author or a quotation. Write "according to X studies" only if exactly \
that many are in the references. A factual claim you cannot tie to a reference gets the marker [PRÜFEN] right \
after it, so the creator can check it before selling.
- No promises of healing, income or returns. In a health, money or legal topic, state once near the start that \
the guide summarises published knowledge and does not replace individual professional advice.
- Every section contains at least one of: a concrete step, an example, a number with its source, a template, \
a wording to copy. No opening platitudes, no empty motivation, no tips found in every blog, no filler sentence \
at the end of a section.
- Do not summarise other chapters or announce what later chapters will cover. Do not pad.
- Aim for 900 to 1,500 words for a chapter and 400 to 800 words for a bonus.

Format (Markdown, nothing else, no preamble):
- Do not repeat the chapter title. Start with a short opening paragraph, then use `## ` for each section and \
`### ` for sub-steps.
- Numbered lists for sequences, tables for comparisons.
- Checklists as task lists: `- [ ] item`.
- Callout boxes as blockquotes whose first line is one of `> [!TIP] Title`, `> [!WARNING] Title`, \
`> [!EXAMPLE] Title`, `> [!KEY] Title`, followed by `> ` lines with the content. Use two to four per chapter, \
where they help.
- End a chapter with a checklist of what the reader should have done before moving on, followed by a section \
"Quellen" (or "Sources" in English) listing only the references actually used in this chapter, with their links. \
Leave that section out if the chapter used none."""


def sources(p: dict) -> str:
    """Copy-mode research prompt: collect real, checked sources the product can stand on."""
    return f"""I am building a short paid guide as a synthesis of existing, verified knowledge. I need the sources \
it will stand on.

Niche:
{json.dumps(p["uvz"], ensure_ascii=False, indent=2)}

Product concept:
{json.dumps(p["concept"], ensure_ascii=False, indent=2)}

Transformation the buyer goes through:
{json.dumps(p["transformation"], ensure_ascii=False, indent=2)}

Use your web search tool. If you have no web search in this chat, say so in one sentence and stop; do not \
answer from memory.

Find 8 to 15 sources that cover the milestones above. Rank evidence like this: studies and systematic reviews, \
official data and guidelines from authorities or professional bodies, publications by named experts. Blog posts \
and pages from people selling something on the topic are not evidence. List only sources you actually opened \
and read in this chat; leave out anything you could not open.

For each source give, in {LANG.get(p.get("language", "de"), LANG["de"])}:
- title, authors or institution, year
- the link
- what it found, in 2 to 4 sentences, with the numbers it reports
- which milestone or question of the guide it supports
- limits worth knowing (small sample, old data, funded by a seller)

Then add a short section on what is disputed or unknown, and a list of the important questions for which you \
found no good source. Reply in Markdown, without an introduction."""


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
