path = "c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace(
    "cmd_type, matched_kw = _global_trie.search_anywhere(text_lower)",
    "cmd_type, matched_kw = _global_trie.search_anywhere(text_lower)\n        print(f'TRIE RETURNED {cmd_type=} {matched_kw=}')"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("Injected print 2")
