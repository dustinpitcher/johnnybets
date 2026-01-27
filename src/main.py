import sys
import os
import asyncio
import typer
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

# Load environment variables from the workspace root
load_dotenv("/Users/dustinpitcher/ai_workspace/.env")

# Add the project root to sys.path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from projects.active.sports_betting.src.agent import run_agent
from projects.active.sports_betting.src.chat_agent import run_chat
from projects.active.sports_betting.src.analysis.contextual_props import run_matchup_analysis

app = typer.Typer()
console = Console()


@app.command()
def chat(
    model: str = typer.Option(
        "grok-fast", 
        "--model", "-m",
        help="LLM model to use. Options: gemini-online, gemini, claude, gpt, grok, qwen"
    ),
    reasoning: str = typer.Option(
        "high",
        "--reasoning", "-r",
        help="Reasoning/thinking mode. Options: xhigh, high, medium, low, minimal, none"
    ),
):
    """
    Start interactive chat with the betting agent (RECOMMENDED)
    
    DEFAULTS: --model grok-fast --reasoning high
    
    Model shortcuts (2026 flagships):
      --model grok-fast      → x-ai/grok-4.1-fast (DEFAULT - fast with reasoning)
      --model grok           → x-ai/grok-4
      --model gemini-online  → google/gemini-3-pro-preview:online (has web search)
      --model gemini         → google/gemini-3-pro-preview (offline)
      --model gemini-flash   → google/gemini-3-flash-preview (fast)
      --model claude         → anthropic/claude-opus-4.5
      --model claude-sonnet  → anthropic/claude-sonnet-4.5
      --model gpt            → openai/gpt-5.2
      --model gpt-pro        → openai/gpt-5.2-pro
      --model qwen           → qwen/qwen3-235b-a22b
    
    Reasoning modes (see https://openrouter.ai/docs/guides/best-practices/reasoning-tokens):
      --reasoning high       → Deep analysis with extended thinking (DEFAULT)
      --reasoning medium     → Balanced reasoning
      --reasoning low        → Light reasoning for faster responses
      --reasoning none       → Disable reasoning
      
    Note: Reasoning uses extra tokens and is billed accordingly.
    """
    # Map shortcuts to full model names
    model_map = {
        # Gemini
        "gemini-online": "google/gemini-3-pro-preview:online",
        "gemini": "google/gemini-3-pro-preview",
        "gemini-flash": "google/gemini-3-flash-preview",
        # Claude
        "claude": "anthropic/claude-opus-4.5",
        "claude-sonnet": "anthropic/claude-sonnet-4.5",
        # OpenAI
        "gpt": "openai/gpt-5.2",
        "gpt-pro": "openai/gpt-5.2-pro",
        # Grok
        "grok": "x-ai/grok-4",
        "grok-fast": "x-ai/grok-4.1-fast",
        # Qwen
        "qwen": "qwen/qwen3-235b-a22b",
    }
    
    selected_model = model_map.get(model, model) if model else None
    
    console.print(Panel.fit(
        "[bold green]Sports Betting Agent - Interactive Mode[/bold green]\n"
        "Chat with the agent to analyze markets, find arbs, and save strategies.",
        style="bold blue"
    ))
    
    try:
        asyncio.run(run_chat(model=selected_model, reasoning=reasoning))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Chat ended.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise


@app.command()
def start():
    """Run a one-shot market scan and analysis"""
    console.print(Panel.fit("Starting One-Shot Market Scan", style="bold green"))
    
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        console.print("\n[bold red]Agent stopped by user.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Error running agent:[/bold red] {e}")


@app.command()
def scan():
    """Quick arb scan (alias for start)"""
    console.print("[yellow]Running Arb Scan...[/yellow]")
    asyncio.run(run_agent())


@app.command()
def props(
    qb: str = typer.Argument(..., help="QB name (e.g., 'J.Allen' or 'Josh Allen')"),
    opponent: str = typer.Argument(..., help="Opponent team abbreviation (e.g., 'DEN')"),
    passing_yards: float = typer.Option(None, "--yards", "-y", help="Current passing yards line"),
    passing_tds: float = typer.Option(None, "--tds", "-t", help="Current passing TDs line"),
):
    """
    Run contextual prop analysis for a QB matchup.
    
    Example: python main.py props "J.Allen" DEN --yards 265.5 --tds 1.5
    """
    console.print(Panel.fit(
        f"[bold green]Prop Alpha Analysis[/bold green]\n"
        f"Analyzing {qb} vs {opponent}",
        style="bold blue"
    ))
    
    lines = {}
    if passing_yards:
        lines["passing_yards"] = passing_yards
    if passing_tds:
        lines["passing_tds"] = passing_tds
    
    try:
        run_matchup_analysis(qb, opponent, lines)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise


if __name__ == "__main__":
    app()

