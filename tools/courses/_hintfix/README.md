Grammatical hint labels for the course exercises (Oct 25 2026).

After any course rebuild (build_courses.py rewrites the exercise files without them), run in order:

    python3 tools/courses/_hintfix/apply_hints.py --apply   # the labels
    python3 tools/courses/_hintfix/apply_fixes.py --apply   # corrections from the line-by-line review

Both skip anything whose exercise text changed since the audit rather than guessing.
