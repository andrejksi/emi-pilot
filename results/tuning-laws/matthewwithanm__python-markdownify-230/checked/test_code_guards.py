"""Code conversion that already holds and must keep holding."""

from markdownify import markdownify as md


def test_code_without_backticks_keeps_single_backticks():
    """Guard: inline code without backticks, like <code>foo bar</code>, still converts to `foo bar`."""
    assert md('<code>foo bar</code>') == '`foo bar`'


def test_code_inside_text_keeps_single_backticks():
    """Guard: inline code in a sentence keeps its surrounding text, as in use <code>x</code> here -> use `x` here."""
    assert md('<p>use <code>x</code> here</p>') == 'use `x` here'


def test_pre_code_block_is_unchanged():
    """Guard: a <pre><code> block still converts to a ``` fenced block."""
    assert md('<pre><code>a = 1\nb = 2</code></pre>') == '```\na = 1\nb = 2\n```'


def test_whitespace_inside_inline_code_is_normalized():
    """Guard: runs of spaces and tabs inside inline code collapse to one space, as in <code>this  should\\t\\tnormalize</code> -> `this should normalize`."""
    assert md('<code>this  should\t\tnormalize</code>') == '`this should normalize`'


def test_blank_lines_around_a_pre_code_block_are_stripped():
    """Guard: leading and trailing blank lines inside <pre><code> are dropped from the fenced block."""
    assert md('<pre><code>\n\na = 1\n\n</code></pre>') == '```\na = 1\n```'


def test_paragraphs_with_code_are_separated_by_one_blank_line():
    """Guard: two paragraphs, the first holding inline code, convert to two lines separated by one blank line."""
    assert md('<p>use <code>x</code> here</p>\n<p>next</p>') == 'use `x` here\n\nnext'


def test_comments_and_indentation_around_code_are_dropped():
    """Guard: HTML comments and indentation whitespace around a paragraph with inline code produce no output."""
    assert md('<div>\n  <p>use <code>x</code></p>\n  <!-- note -->\n</div>') == 'use `x`'


def test_a_pre_code_block_between_paragraphs_is_set_apart():
    """Guard: a <pre><code> block between two paragraphs is separated from each by one blank line."""
    assert md('<p>a</p>\n<pre><code>b</code></pre>\n<p>c</p>') == 'a\n\n```\nb\n```\n\nc'


def test_markdown_outside_code_is_escaped_but_not_inside():
    """Guard: asterisks in text outside inline code are escaped, those inside it are not: <p>*a* <code>*b*</code></p> -> \\*a\\* `*b*`."""
    assert md('<p>*a* <code>*b*</code></p>') == '\\*a\\* `*b*`'


def test_stripped_code_tags_lose_their_backticks():
    """Guard: with strip=['code'], <p>a <code>b</code></p> converts to plain a b, without backticks."""
    assert md('<p>a <code>b</code></p>', strip=['code']) == 'a b'
