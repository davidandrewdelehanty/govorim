"""Small helpers for writing course sections as Python data.
A section is {"id", "title", "sub", "blocks": [...], "exercises": [...]}; the
builder (build_courses.py) numbers the exercises and writes the JSON."""


def P(text): return {"t": "p", "text": text}
def H(text): return {"t": "h", "text": text}
def NOTE(text): return {"t": "note", "text": text}
def L(*items): return {"t": "list", "items": list(items)}
def EX(*pairs): return {"t": "ex", "items": [list(p) if isinstance(p, (list, tuple)) else [p, ""] for p in pairs]}


def T(head, rows, caption=None, row_heads=True):
    b = {"t": "table", "head": head, "rows": rows, "rowHeads": row_heads}
    if caption:
        b["caption"] = caption
    return b


def MC(q, options, answer, why="", ru=None):
    """Multiple choice. `answer` is the index of the right option."""
    e = {"type": "mc", "q": q, "options": options, "answer": answer, "why": why}
    if ru:
        e["ru"] = ru
    return e


def FILL(q, answers, why="", hint=None, prompt=None):
    """Type the answer where ___ is. `answers` lists every accepted spelling
    (stress marks, ё/е, case and punctuation are ignored when checking)."""
    e = {"type": "fill", "q": q, "answers": answers if isinstance(answers, list) else [answers], "why": why}
    if hint:
        e["hint"] = hint
    if prompt:
        e["prompt"] = prompt
    return e


def SEC(id, title, blocks, exercises=(), sub=None):
    s = {"id": id, "title": title, "blocks": blocks, "exercises": list(exercises)}
    if sub:
        s["sub"] = sub
    return s
