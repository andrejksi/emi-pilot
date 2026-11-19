from types import SimpleNamespace
from unittest.mock import Mock

from smolagents import LiteLLMModel


def message_text(message):
    content = message["content"]
    if isinstance(content, str):
        return content
    return "\n".join(part["text"] for part in content if part["type"] == "text")


def test_litellm_accepts_consecutive_system_instructions():
    """New: LiteLLMModel accepts the consecutive FOO and BAR system instructions and sends both with the user request without error (A1)."""
    start_instruction = "When you say anything Start with 'FOO'"
    end_instruction = "When you say anything End with 'BAR'"
    user_request = "Just say '.'"
    messages = [
        {"role": "system", "content": start_instruction},
        {"role": "system", "content": end_instruction},
        {"role": "user", "content": user_request},
    ]
    reply = SimpleNamespace(role="assistant", content="FOO.BAR", tool_calls=None)
    completion = Mock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=reply)],
            usage=SimpleNamespace(prompt_tokens=15, completion_tokens=3),
        )
    )
    model = LiteLLMModel(model_id="gemini/gemini-2.5-flash", client=SimpleNamespace(completion=completion))

    assert model(messages).content == reply.content
    sent_messages = completion.call_args.kwargs["messages"]
    system_text = "\n".join(message_text(message) for message in sent_messages if message["role"] == "system")
    assert start_instruction in system_text
    assert end_instruction in system_text
    assert system_text.index(start_instruction) < system_text.index(end_instruction)
    assert [message_text(message) for message in sent_messages if message["role"] == "user"] == [user_request]
