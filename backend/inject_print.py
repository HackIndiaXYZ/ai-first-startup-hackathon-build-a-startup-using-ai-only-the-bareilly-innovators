path = "c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace(
    "app_name = text_lower.split(kw, 1)[-1].strip()",
    "print(f'DEBUG: {cmd_type=} kw={repr(kw)} text={repr(text_lower)}'); app_name = text_lower.split(kw, 1)[-1].strip()"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("Injected print")
