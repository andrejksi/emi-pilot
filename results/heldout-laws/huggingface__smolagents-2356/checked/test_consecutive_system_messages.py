from unittest.mock import MagicMock, patch

from smolagents.models import LiteLLMModel, get_clean_message_list

ISSUE_MESSAGES = [
    {"role": "system", "content": "When you say anything Start with 'FOO'"},
    {"role": "system", "content": "When you say anything End with 'BAR'"},
    {"role": "user", "content": "Just say '.'"},
]


def _text(content):
    if isinstance(content, str):
        return content
    return "\n".join(el.get("text", "") for el in content if isinstance(el, dict))


def _fake_response():
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = "FOO . BAR"
    resp.choices[0].message.role = "assistant"
    resp.choices[0].message.tool_calls = None
    resp.usage.prompt_tokens = 1
    resp.usage.completion_tokens = 1
    return resp


def test_litellm_model_accepts_consecutive_system_messages():
    """New: LiteLLMModel called with the issue's two consecutive system messages and a user message does not raise and sends both system instructions and the user text to the client (A1, A2)."""
    fake = MagicMock()
    fake.completion.return_value = _fake_response()
    with patch("smolagents.models.LiteLLMModel.create_client", return_value=fake):
        model = LiteLLMModel(model_id="gemini/gemini-2.5-flash", api_key="dummy")
        result = model(ISSUE_MESSAGES)
    assert result.content == "FOO . BAR"
    sent = fake.completion.call_args.kwargs["messages"]
    system_text = "\n".join(_text(m["content"]) for m in sent if m["role"] == "system")
    assert "When you say anything Start with 'FOO'" in system_text
    assert "When you say anything End with 'BAR'" in system_text
    assert system_text.index("Start with 'FOO'") < system_text.index("End with 'BAR'")
    assert sent[-1]["role"] == "user" and "Just say '.'" in _text(sent[-1]["content"])


def test_clean_message_list_handles_consecutive_string_system_messages():
    """New: get_clean_message_list on the issue's messages does not raise and keeps both system instructions, in order, before the user message (A2, A3)."""
    out = get_clean_message_list(ISSUE_MESSAGES)
    system_text = "\n".join(_text(m["content"]) for m in out if m["role"] == "system")
    assert "When you say anything Start with 'FOO'" in system_text
    assert "When you say anything End with 'BAR'" in system_text
    assert system_text.index("Start with 'FOO'") < system_text.index("End with 'BAR'")
    assert out[-1]["role"] == "user" and "Just say '.'" in _text(out[-1]["content"])
