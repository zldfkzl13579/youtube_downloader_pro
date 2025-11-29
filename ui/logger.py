# ui/logger.py
from rich.console import Console

console = Console()

class Logger:
    @staticmethod
    def info(msg):
        console.print(f"[bold cyan][INFO][/bold cyan] {msg}")

    @staticmethod
    def success(msg):
        console.print(f"[bold green][SUCCESS][/bold green] {msg}")

    @staticmethod
    def warning(msg):
        console.print(f"[bold yellow][WARNING][/bold yellow] {msg}")

    @staticmethod
    def error(msg):
        console.print(f"[bold red][ERROR][/bold red] {msg}")

    @staticmethod
    def ask(msg):
        console.print(f"\n[bold magenta][ASK][/bold magenta] {msg}")