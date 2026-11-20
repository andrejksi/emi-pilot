import json
from smolagents.models import get_clean_message_list

def call(msgs, flatten=False):
    try:
        res = get_clean_message_list(msgs, flatten_messages_as_text=flatten)
        clean = [{"role": str(m["role"]), "content": m["content"]} for m in res]
        return {"returned": clean}
    except Exception as exc:
        return {"raised": f"{type(exc).__name__}: {exc}"}

msgs = [
    {"role": "system", "content": "Start with FOO"},
    {"role": "system", "content": "End with BAR"},
    {"role": "user", "content": "Hi"},
]
results = {
    "consecutive_str_default": call(msgs, False),
    "consecutive_str_flatten": call(msgs, True),
    "mixed_str_and_blocks": call([
        {"role": "system", "content": "Start with FOO"},
        {"role": "system", "content": [{"type": "text", "text": "End with BAR"}]},
    ], False),
}
print(json.dumps(results, sort_keys=True))
