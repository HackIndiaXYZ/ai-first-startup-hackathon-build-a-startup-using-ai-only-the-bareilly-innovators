import re

path = "c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Intercept VALID_NO_PARAM_TYPES immediately after Trie routing
interceptor = """
    if cmd_type in VALID_NO_PARAM_TYPES:
        return PCCommand(type=cmd_type)
"""
code = code.replace("    if not cmd_type:\n        return None  # No command found by Trie!", 
                    "    if not cmd_type:\n        return None\n" + interceptor)

# Remove all remaining _exact_phrase blocks
code = re.sub(r'\s*if _exact_phrase\([^)]+\):\s*return PCCommand\([^)]+\)', '', code)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("Cleaned up exact_phrase and added interceptor")
