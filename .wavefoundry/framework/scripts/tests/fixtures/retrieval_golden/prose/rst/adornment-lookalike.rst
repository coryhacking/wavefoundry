Adornment Lookalikes
====================

This file pins negative parsing cases: lines that resemble reStructuredText section adornment but are not headings.
A structure-aware chunker must not split or title-tag any of the runs below.

The paragraph that follows contains a transition line, which is a legitimate horizontal separator between two blocks of prose.

----------------------------------------------------------------

The dash run above has blank lines on both sides and no title text attached, so it is a transition, not a section heading.
Splitting here as if a new section began would attribute the following prose to a heading that does not exist.

Literal blocks routinely contain adornment-shaped rows copied from program output::

    Report summary
    ==============
    total requests    18422
    failed requests       7
    --------------
    p99 latency      212ms

The equals row and the dash row inside the literal block are table decoration in captured output, not section titles.
Any parser that promotes them to headings has ignored the literal block context.

Some authors paste ASCII banners straight into running prose, like this one
---------------------------------------------------------------------------
and continue the sentence on the next line as if nothing happened.
The dash run above sits mid-paragraph with no blank line after it, so it is a visual separator inside a paragraph, not an underline for the text above it.

A final lookalike: a sentence that simply ends with a row of equals signs pasted from a log follows.

    boot sequence complete
    ======================

The indented block above is quoted output; its equals row underlines nothing in the document structure.
