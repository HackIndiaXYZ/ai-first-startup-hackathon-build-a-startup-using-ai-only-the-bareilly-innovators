import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base_plugin import BasePlugin


class CalculatorPlugin(BasePlugin):
    def get_name(self) -> str:
        return "Calculator"

    def get_commands(self) -> list[str]:
        return ["calculate", "math"]

    def execute(self, command: str, args: str) -> str:
        # Sanitize: only allow digits and basic math operators
        expr = "".join(c for c in args if c in "0123456789+-*/().% ")
        if not expr.strip():
            return "Please provide a math expression. Example: calculate 5 plus 3."
        # Convert natural language
        expr = expr.replace("plus", "+").replace("minus", "-")
        expr = expr.replace("times", "*").replace("divided by", "/")
        try:
            result = eval(expr)  # safe since we stripped non-math chars
            return f"The answer is {result}."
        except Exception:
            return "I couldn't calculate that. Try something like 'calculate 10 + 5'."

    def on_load(self):
        print("    Calculator plugin ready.")
