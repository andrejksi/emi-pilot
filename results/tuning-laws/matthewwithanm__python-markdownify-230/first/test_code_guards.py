"""Code conversion that already holds and must keep holding."""

from markdownify import markdownify as md


def test_code_without_backticks_keeps_single_backticks():
    """Guard: inline code without backticks, like <code>foo bar</code>, still converts to `foo bar`."""
    assert md('<code>foo bar</code>') == '`foo bar`'


def test_code_inside_text_keeps_single_backticks():
    """Guard: inline code in a sentence keeps its surrounding text, as in use <code>x</code> here -> use `x` here."""
    assert md('<p>use <code>x</code> here</p>') == '\n\nuse `x` here\n\n'


def test_pre_code_block_is_unchanged():
    """Guard: a <pre><code> block still converts to a ``` fenced block."""
    assert md('<pre><code>a = 1\nb = 2</code></pre>') == '\n\n```\na = 1\nb = 2\n```\n\n'
