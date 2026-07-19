import re

path = "c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Find all occurrences of VAR_KEYWORDS in the mapping
vars_in_mapping = set(re.findall(r'([A-Z_]+_KEYWORDS)', code))

# Find all defined keywords (e.g. OPEN_KEYWORDS = [...])
defined_vars = set(re.findall(r'^([A-Z_]+_KEYWORDS)\s*=', code, re.MULTILINE))

missing = vars_in_mapping - defined_vars
print("Missing:", missing)

# Remove the missing keywords from the mapping dictionary
for m in missing:
    # Pattern to match: "SOME_KEY": MISSING_KEYWORDS, or "SOME_KEY": MISSING_KEYWORDS
    code = re.sub(r'"[A-Z_]+":\s*' + m + r'\s*,?', '', code)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("Removed missing variables from mapping.")
