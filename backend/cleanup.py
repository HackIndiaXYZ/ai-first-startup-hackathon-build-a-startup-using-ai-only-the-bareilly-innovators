path = "c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("print(f'TRIE RETURNED {cmd_type=} {matched_kw=}')", "")
code = code.replace("print(f'DEBUG: {cmd_type=} kw={repr(kw)} text={repr(text_lower)}'); ", "")

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
