"""Quick verification tests for command_parser.py fixes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.command_parser import parse_command

tests = [
    ("open chrome", "OPEN_APP"),
    ("close", None),                         # Bug #3 fix: bare "close" should return None
    ("close chrome", "CLOSE_APP"),
    ("set timer for 5 minutes", "SET_TIMER"), # Bug #1 fix: should NOT be SCHEDULE_TASK
    ("find file report.pdf", "FIND_FILE"),
    ("delete file named file.txt", "DELETE_FILE"),
    ("volume up", "VOLUME_UP"),
    ("open chrom", "OPEN_APP"),              # Fuzzy match test
    ("send message to Rao Alok Yadav saying hello", "SEND_WHATSAPP"),
    ("hey sivi open chrome", "OPEN_APP"),    # Wake word strip test
    ("sivi volume up", "VOLUME_UP"),         # Wake word strip test
    ("hey close chrome", "CLOSE_APP"),       # New Trie handles anywhere match, so this is valid now
]

pass_count = 0
fail_count = 0

for text, expected_type in tests:
    result = parse_command(text)
    got_type = result.type if result else None
    ok = got_type == expected_type
    status = "PASS" if ok else "FAIL"
    if ok:
        pass_count += 1
    else:
        fail_count += 1
    
    extra = ""
    if result and result.params:
        extra = f"  params={result.params}"
    print(f"  {status} | '{text}' -> expected={expected_type}, got={got_type}{extra}")

print(f"\nResults: {pass_count} passed, {fail_count} failed out of {len(tests)} tests")
