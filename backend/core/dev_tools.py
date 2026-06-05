import os
import subprocess
import psutil
import logging
import pyautogui

logger = logging.getLogger("sivi.dev_tools")

try:
    from google import genai
    _genai_available = True
except ImportError:
    _genai_available = False

class DeveloperTools:
    def __init__(self):
        key = os.getenv("GEMINI_API_KEY")
        if key and _genai_available:
            self.client = genai.Client(api_key=key)
            self.model_name = 'gemini-2.5-flash'
        else:
            self.client = None
            self.model_name = None

    def run_command(self, cmd: str) -> str:
        """Execute a raw terminal command and return output."""
        try:
            # Using PowerShell for robust execution on Windows
            process = subprocess.Popen(
                ["powershell", "-Command", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=15)
            if process.returncode == 0:
                return stdout.strip() or f"Command executed successfully: {cmd}"
            else:
                return f"Error executing {cmd}:\n{stderr.strip()}"
        except subprocess.TimeoutExpired:
            process.kill()
            return "Command timed out after 15 seconds."
        except Exception as e:
            return f"Failed to run command: {str(e)}"

    def get_git_status(self) -> str:
        """Return the current git status."""
        return self.run_command("git status -s")

    def kill_port(self, port: str) -> str:
        """Find and kill the process using a specific port."""
        try:
            port = int(port)
            killed = False
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    pid = conn.pid
                    if pid:
                        p = psutil.Process(pid)
                        p.terminate()
                        killed = True
            if killed:
                return f"Successfully killed the process running on port {port}."
            return f"No active process found on port {port}."
        except ValueError:
            return "Invalid port number provided."
        except psutil.AccessDenied:
            return "Access Denied: Try running Sivi as Administrator."
        except Exception as e:
            return f"Failed to kill port: {str(e)}"

    def analyze_code(self, filename: str) -> str:
        """Deep read of a file to find bugs using Gemini."""
        if not self.client:
            return "Generative AI is not configured. Cannot analyze code."
            
        # Try to find file in current dir or desktop or workspace
        filepath = os.path.abspath(filename)
        if not os.path.exists(filepath):
            # Try searching loosely in current directory tree
            found = False
            for root, dirs, files in os.walk(os.getcwd()):
                if filename in files:
                    filepath = os.path.join(root, filename)
                    found = True
                    break
            if not found:
                return f"File '{filename}' not found."
                
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code_content = f.read()
                
            prompt = (
                f"Act as an elite senior developer. Review the following code from '{filename}'. "
                "Identify any syntax errors, logical bugs, memory leaks, or security vulnerabilities. "
                "Provide a highly technical, concise explanation of the bugs found. Do not output the fixed code yet, just the analysis.\n\n"
                f"CODE:\n{code_content}"
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            return f"Failed to analyze code in {filename}: {str(e)}"

    def generate_code(self, filename: str, instructions: str) -> str:
        """Generate code and save it to the specified file."""
        if not self.client:
            return "Generative AI is not configured. Cannot generate code."
            
        try:
            prompt = (
                f"Act as an elite senior developer. Write code based on these instructions: '{instructions}'. "
                f"You are generating a file named '{filename}'. "
                "Output ONLY the raw code. Do not include markdown code blocks like ```python. Just the raw text."
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            raw_code = response.text.strip()
            
            # Remove markdown blocks if Gemini stubbornly includes them
            if raw_code.startswith("```"):
                lines = raw_code.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_code = "\n".join(lines).strip()

            filepath = os.path.abspath(filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(raw_code)
                
            return f"Code successfully generated and saved to {filepath}."
        except Exception as e:
            return f"Failed to generate code: {str(e)}"

    def open_in_editor(self, filename: str) -> str:
        """Open a file in VS Code."""
        try:
            subprocess.Popen(["code", filename], shell=True)
            return f"Opened {filename} in your editor."
        except Exception as e:
            return f"Failed to open in editor: {str(e)}"

    def close_current_file(self) -> str:
        """Simulate Ctrl+W to close the active tab in the editor."""
        try:
            # Simulate Ctrl+W
            pyautogui.hotkey('ctrl', 'w')
            return "Closed the current active file."
        except Exception as e:
            return f"Failed to close file: {str(e)}"

dev_tools = DeveloperTools()
