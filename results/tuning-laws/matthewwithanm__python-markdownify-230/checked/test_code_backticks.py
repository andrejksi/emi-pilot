"""Rule the task adds: inline code that contains backticks is fenced with a longer backtick string."""

from markdownify import markdownify as md


def test_code_with_backticks_is_wrapped_in_double_backticks():
    """New: <code>We have to `manage` this.</code> converts to ``We have to `manage` this.``."""
    assert md('<code>We have to `manage` this.</code>') == '``We have to `manage` this.``'
