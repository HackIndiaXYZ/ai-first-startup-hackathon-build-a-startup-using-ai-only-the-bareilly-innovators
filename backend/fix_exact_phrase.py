import re

path = "c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Replace _exact_phrase calls with cmd_type checks
replacements = {
    "SHUTDOWN_KEYWORDS": "SHUTDOWN",
    "RESTART_KEYWORDS": "RESTART",
    "SLEEP_KEYWORDS": "SLEEP",
    "TAB_NEXT_KEYWORDS": "TAB_NEXT",
    "TAB_PREV_KEYWORDS": "TAB_PREV",
    "TAB_NEW_KEYWORDS": "TAB_NEW",
    "TAB_CLOSE_KEYWORDS": "TAB_CLOSE",
    "BROWSER_READ_PAGE_KEYWORDS": "BROWSER_READ_PAGE",
    "BROWSER_FULLSCREEN_KEYWORDS": "BROWSER_FULLSCREEN",
    "BROWSER_STATUS_KEYWORDS": "BROWSER_STATUS",
}

for kw, cmd in replacements.items():
    code = re.sub(
        r'if _exact_phrase\(text_lower, ' + kw + r'\):',
        r'if cmd_type == "' + cmd + r'":',
        code
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("Fixed _exact_phrase calls")
