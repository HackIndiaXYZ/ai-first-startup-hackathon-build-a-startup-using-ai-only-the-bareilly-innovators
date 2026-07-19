import re

path = "c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Replace:
# if cmd_type == "OPEN_APP":
#        kw = matched_kw
# with:
# if cmd_type == "OPEN_APP":
#     if True:
#        kw = matched_kw

code = re.sub(
    r'(if cmd_type == "[A-Z_]+":\n)(\s+)(kw = matched_kw)', 
    r'\1\2if True:\n\2    \3', 
    code
)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("Fixed indentation")
