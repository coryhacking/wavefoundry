#!/usr/bin/env python3
"""Reviewer check for change 240wz: each frozen sentence appears once in its section.

Usage: python3 -X utf8 -I check_sentences.py <guide.md> [--pointers]
Exit 0 when every sentence is present once in its section; exit 1 otherwise.
With --pointers, run from the repository root: it also checks the three pointer
sentences in the package and pause prompts and seed 100.
Presence check only. It judges no prose quality and is not a linter.
"""
import sys

UNDERSTANDABLE = "## Understandable: make meaning explicit"
CHECK = "## Check the reader's task"
BASIS = "## Basis and limits"

FROZEN = [
    (UNDERSTANDABLE, "Do not stack four or more nouns and modifiers before a head noun."),
    (UNDERSTANDABLE, "Name the thing first and attach the rest with a preposition or a clause."),
    (UNDERSTANDABLE, "For example, write “the fixture for the known-bad case with renamed vocabulary”, not “renamed-vocabulary known-bad fixture”."),
    (UNDERSTANDABLE, "A defined project term counts as one word."),
    (UNDERSTANDABLE, "Write complete sentences in handoffs, status records and the prose fields of review evidence."),
    (UNDERSTANDABLE, "Keep the subject, the verb and the articles, so the reader does not have to supply who did what."),
    (UNDERSTANDABLE, "A task, checklist item or acceptance criterion holds one action or one result, unless one command or one observation verifies every part."),
    (UNDERSTANDABLE, "Length is a prompt to check, not a limit."),
    (UNDERSTANDABLE, "When an instruction passes about 20 words, or any other sentence passes about 25, check that it carries one action or one point."),
    (UNDERSTANDABLE, "If it carries more, split it."),
    (UNDERSTANDABLE, "When such a sentence carries three or more parallel cases, move them into a list."),
    (UNDERSTANDABLE, "An extended technical explanation can be necessary"),
    (CHECK, "Apply the same reader tasks to changelog entries and the session handoff."),
    (CHECK, "In each sentence, find the actor and the result."),
    (CHECK, "The author who rewrites a paragraph or list item for substance applies the guide to all of it, and no wider."),
    (CHECK, "A rewrite is for substance when it changes what the text requires, permits or describes."),
    (CHECK, "Text that a test or machine contract quotes exactly keeps its wording."),
    (CHECK, "This guide adds no review lane, council, approval gate or prose linter."),
    (BASIS, "with selected precision and sentence-structure practices informed by"),
]

# Pointer sentences outside the guide, checked with --pointers from the repository root.
POINTERS = [
    ("docs/prompts/package-wavefoundry.prompt.md",
     "Terse bullets still follow `.wavefoundry/framework/docs/writing-guide.md`: each sentence names its actor and result and carries one point."),
    ("docs/prompts/pause-wave.prompt.md",
     "Write each section in complete sentences, as `.wavefoundry/framework/docs/writing-guide.md` directs."),
    (".wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md",
     "Tell the writer to apply `.wavefoundry/framework/docs/writing-guide.md` to the handoff sections, in complete sentences."),
]


def section(text: str, heading: str) -> str:
    start = text.find(heading + "\n")
    if start < 0:
        return ""
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end < 0 else text[start:end]


def main(argv: list[str]) -> int:
    pointers = "--pointers" in argv
    paths = [a for a in argv if a != "--pointers"]
    text = open(paths[0], encoding="utf-8").read()
    missing = []
    for heading, sentence in FROZEN:
        if section(text, heading).count(sentence) != 1:
            missing.append(f"{heading} :: {sentence}")
    total = len(FROZEN)
    if pointers:
        total += len(POINTERS)
        for path, sentence in POINTERS:
            try:
                body = open(path, encoding="utf-8").read()
            except OSError:
                body = ""
            if body.count(sentence) != 1:
                missing.append(f"{path} :: {sentence}")
    for line in missing:
        print("MISSING", line)
    print(f"{total - len(missing)}/{total} present")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
