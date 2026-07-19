import subprocess
import logging
import os

logger = logging.getLogger("sivi.git_orchestrator")

class GitOrchestrator:
    """
    Sivi's Autonomous Git & CI/CD Orchestrator.
    Handles auto-committing, pushing, and running tests.
    """
    def __init__(self):
        pass

    def _run_shell(self, cmd: str, cwd: str = None) -> str:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                shell=True,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            output = result.stdout.strip()
            err = result.stderr.strip()
            
            if result.returncode != 0:
                logger.error(f"Command failed: {cmd}\nError: {err}")
                return f"Error executing command: {err or output}"
                
            return output if output else "Success"
        except Exception as e:
            logger.error(f"Failed to run shell command '{cmd}': {e}")
            return f"Exception: {str(e)}"

    def commit_and_push(self, message: str, cwd: str = None) -> str:
        """Automates `git add .`, `git commit -m`, and `git push`."""
        if not message:
            return "Please provide a commit message."
            
        logger.info(f"Running git commit with message: {message}")
        
        # 1. Add all
        add_res = self._run_shell("git add .", cwd)
        if "Error" in add_res or "Exception" in add_res:
            return f"Failed to stage files: {add_res}"
            
        # 2. Commit
        # Use quotes carefully
        safe_msg = message.replace('"', "'")
        commit_res = self._run_shell(f'git commit -m "{safe_msg}"', cwd)
        
        if "nothing to commit" in commit_res.lower():
            return "There are no changes to commit. Working tree is clean."
            
        if "Error" in commit_res or "Exception" in commit_res:
            return f"Failed to commit: {commit_res}"
            
        # 3. Push
        push_res = self._run_shell("git push", cwd)
        if "Error" in push_res or "Exception" in push_res:
            return f"Commit succeeded, but failed to push: {push_res}"
            
        return f"Successfully committed and pushed all changes with message: '{message}'"

    def run_test_suite(self, cmd: str, cwd: str = None) -> str:
        """Runs a test suite like pytest or npm test and summarizes it."""
        logger.info(f"Running test suite: {cmd}")
        res = self._run_shell(cmd, cwd)
        
        # We don't want to blow up the LLM context if output is massive.
        # We return the first 500 chars and the last 1000 chars.
        if len(res) > 2000:
            summary = res[:500] + "\n...[TRUNCATED]...\n" + res[-1000:]
            return f"Test Execution Output (Truncated):\n{summary}"
        
        return f"Test Execution Output:\n{res}"

git_orchestrator = GitOrchestrator()
