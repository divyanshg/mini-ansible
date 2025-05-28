import re

def sudo_wrap(cmd):
    tokens = re.split(r'(\|\||&&)', cmd)
    wrapped_tokens = [
        f"sudo {t.strip()}" if t.strip() and t not in ("||", "&&") else t
        for t in tokens
    ]
    return " ".join(wrapped_tokens)