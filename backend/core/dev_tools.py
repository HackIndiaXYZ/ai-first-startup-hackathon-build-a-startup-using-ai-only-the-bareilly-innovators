import os
import json
import subprocess
import psutil
import logging
import pyautogui
import sys
import time

logger = logging.getLogger("sivi.dev_tools")

try:
    from google import genai
    _genai_available = True
except ImportError:
    _genai_available = False

def _get_api_key():
    key = os.getenv("GEMINI_API_KEY")
    if key: return key
    try:
        settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sivi_settings.json")
        with open(settings_path, "r") as f:
            return json.load(f).get("api_key")
    except Exception:
        return None

class DeveloperTools:
    def __init__(self):
        self.model_name = 'gemini-2.5-flash'

    def _get_client(self):
        if not _genai_available: return None
        key = _get_api_key()
        return genai.Client(api_key=key) if key else None

    def run_command(self, cmd: str) -> str:
        """Execute a raw terminal command and return output."""
        try:
            # If the command looks like a server or dev script, spawn it in a new visible window
            long_running_keywords = ["start", "dev", "serve", "watch", "run", "nodemon"]
            is_long = any(k in cmd.lower().split() for k in long_running_keywords)
            
            if is_long:
                os.system(f'start cmd.exe /k "{cmd}"')
                return f"Spawned long-running dev command in new window: {cmd}"

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
        client = self._get_client()
        if not client:
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
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            return f"Failed to analyze code in {filename}: {str(e)}"

    def generate_code(self, filename: str, instructions: str) -> str:
        """Generate code and save it to the specified file."""
        client = self._get_client()
        if not client:
            return "Generative AI is not configured. Cannot generate code."
            
        try:
            prompt = (
                f"Act as an elite senior developer. Write code based on these instructions: '{instructions}'. "
                f"You are generating a file named '{filename}'. "
                "Output ONLY the raw code. Do not include markdown code blocks like ```python. Just the raw text."
            )
            response = client.models.generate_content(
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

    def execute_python_script(self, goal: str) -> str:
        """Autonomously generate and execute a Python script to achieve a goal."""
        client = self._get_client()
        if not client:
            return "Generative AI is not configured. Cannot write script."
            
        try:
            prompt = (
                f"Act as an autonomous AI agent running on a Windows machine. "
                f"Your goal is to write a Python script to achieve the following task: '{goal}'. "
                "The script will be executed immediately. Ensure it is robust and prints clear output. "
                "Output ONLY the raw Python code without markdown blocks."
            )
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            raw_code = response.text.strip()
            
            if raw_code.startswith("```"):
                lines = raw_code.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_code = "\n".join(lines).strip()

            script_path = os.path.join(os.path.dirname(__file__), "__sivi_auto_module.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(raw_code)
                
            # Execute the script
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=30)
            
            # Clean up
            try:
                os.remove(script_path)
            except Exception:
                pass
                
            if process.returncode == 0:
                return f"Autonomous Module Executed. Output:\n{stdout.strip()}"
            else:
                return f"Autonomous Module Error:\n{stderr.strip()}\n\nCode was:\n{raw_code}"
                
        except subprocess.TimeoutExpired:
            process.kill()
            return "Autonomous script timed out after 30 seconds."
        except Exception as e:
            return f"Autonomous module failed: {str(e)}"

    def spawn_subagent(self, goal: str) -> str:
        """Spawn a detached background Python worker to monitor something continuously."""
        client = self._get_client()
        if not client:
            return "Generative AI is not configured. Cannot spawn subagent."
            
        try:
            prompt = (
                f"Act as an autonomous AI. Your goal is to write a Python script that runs continuously in a loop to monitor the following: '{goal}'. "
                "The script will run as a detached background process. "
                "When the monitoring condition is met, the script MUST execute a requests.post to 'http://localhost:8000/voice/send-text' "
                "with a JSON payload like {'text': '[SYSTEM_EVENT: The Tesla stock just dropped below $200! Alert the user!]'} "
                "so that the main AI assistant can speak it out loud. After posting, the script can exit or keep running based on the goal. "
                "Include a time.sleep() in the loop to prevent high CPU usage. "
                "Output ONLY the raw Python code without markdown blocks."
            )
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            raw_code = response.text.strip()
            
            if raw_code.startswith("```"):
                lines = raw_code.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_code = "\n".join(lines).strip()

            script_id = int(time.time())
            script_path = os.path.join(os.path.dirname(__file__), f"__sivi_subagent_{script_id}.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(raw_code)
                
            # Spawn totally detached
            if sys.platform == 'win32':
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen([sys.executable, script_path], creationflags=DETACHED_PROCESS)
            else:
                subprocess.Popen([sys.executable, script_path], start_new_session=True)
                
            return f"Sub-Agent spawned successfully in the background to monitor: {goal}. It will alert you when ready."
                
        except Exception as e:
            return f"Failed to spawn subagent: {str(e)}"

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
