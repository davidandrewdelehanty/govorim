"""Classic stories as a grammar course: one lesson per public-domain story,
in its original text, with the opening paragraphs to read and exercises on
the story's own sentences (tools/courses/story_drills.py)."""
import io, json, os
from kit import *

HERE = os.path.dirname(os.path.abspath(__file__))
_P = os.path.join(HERE, "story_drills.json")
DATA = json.load(io.open(_P, encoding="utf-8")) if os.path.exists(_P) else {}
IN_SECTION = 20
SECS = []
for n, (slug, x) in enumerate(DATA.items(), 1):
    exs = x["exercises"]
    blocks = [P(t) for t in x["intro"]] + [NOTE("%s, «%s» (public domain). Explanations: the DLI Grammar Reference Book." % (x["author"], x["title"]))]
    s = SEC("s%02d-%s" % (n, slug), x["author"] + " · " + x["title"], blocks, exercises=exs[:IN_SECTION], sub=None)
    s["more"] = exs[IN_SECTION:]
    SECS.append(s)

COURSE_DEFS = [({"id": "stories", "title": "Classic Stories: Grammar in Context", "short": "Stories", "mark": "Рас",
                 "blurb": "",
                 "credit": "Texts: the library's public-domain editions; explanations: the DLI Basic Course (public domain)",
                 "creditUrl": "", "license": "Public domain", "licenseUrl": ""}, SECS)] if SECS else []
