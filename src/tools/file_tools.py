"""
File tools for the sports betting agent.
Allows the agent to save strategies, reports, and analysis.
"""
import os
from datetime import datetime
from typing import Optional


# Default output directory for agent files
OUTPUT_DIR = "/Users/dustinpitcher/ai_workspace/projects/active/sports_betting/output"


def ensure_output_dir():
    """Ensure the output directory exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_file(filename: str, content: str, subdir: Optional[str] = None) -> str:
    """
    Save content to a file in the output directory.
    
    Args:
        filename: Name of the file to save
        content: Content to write to the file
        subdir: Optional subdirectory within output/
        
    Returns:
        Full path to the saved file
    """
    ensure_output_dir()
    
    if subdir:
        target_dir = os.path.join(OUTPUT_DIR, subdir)
        os.makedirs(target_dir, exist_ok=True)
    else:
        target_dir = OUTPUT_DIR
    
    filepath = os.path.join(target_dir, filename)
    
    with open(filepath, "w") as f:
        f.write(content)
    
    return filepath


def save_strategy(name: str, content: str) -> str:
    """
    Save a betting strategy to the strategies folder.
    
    Args:
        name: Strategy name (will be used as filename)
        content: Strategy content/description
        
    Returns:
        Path to saved file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name.replace(' ', '_').lower()}_{timestamp}.md"
    return save_file(filename, content, subdir="strategies")


def save_report(content: str, report_type: str = "analysis") -> str:
    """
    Save an analysis report.
    
    Args:
        content: Report content
        report_type: Type of report (analysis, arb, daily, etc.)
        
    Returns:
        Path to saved file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report_type}_{timestamp}.md"
    return save_file(filename, content, subdir="reports")


def list_saved_files(subdir: Optional[str] = None) -> list:
    """
    List files in the output directory.
    
    Args:
        subdir: Optional subdirectory to list
        
    Returns:
        List of filenames
    """
    ensure_output_dir()
    target_dir = os.path.join(OUTPUT_DIR, subdir) if subdir else OUTPUT_DIR
    
    if not os.path.exists(target_dir):
        return []
    
    return [f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))]


def read_saved_file(filename: str, subdir: Optional[str] = None) -> Optional[str]:
    """
    Read a previously saved file.
    
    Args:
        filename: Name of the file to read
        subdir: Optional subdirectory
        
    Returns:
        File content or None if not found
    """
    target_dir = os.path.join(OUTPUT_DIR, subdir) if subdir else OUTPUT_DIR
    filepath = os.path.join(target_dir, filename)
    
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, "r") as f:
        return f.read()

