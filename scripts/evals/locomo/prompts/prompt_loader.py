"""
Prompt Loader for Memory Agent

This module provides functionality to load and manage prompts from text files.
"""

import os
from pathlib import Path
from typing import Dict, Optional


class PromptLoader:
    """Prompt loader for managing prompts from text files"""
    
    def __init__(self, prompts_dir: str = None):
        """
        Initialize prompt loader
        
        Args:
            prompts_dir: Directory containing prompt files (defaults to current directory)
        """
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent
        self.prompts_dir = Path(prompts_dir)
        self._cached_prompts = {}
    
    def load_prompt(self, prompt_name: str) -> str:
        """
        Load a prompt from file
        
        Args:
            prompt_name: Name of the prompt file (without .txt extension)
            
        Returns:
            Prompt content as string
        """
        if prompt_name in self._cached_prompts:
            return self._cached_prompts[prompt_name]
        
        prompt_file = self.prompts_dir / f"{prompt_name}.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        self._cached_prompts[prompt_name] = content
        return content
    
    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Load and format a prompt with variables
        
        Args:
            prompt_name: Name of the prompt file
            **kwargs: Variables to format in the prompt
            
        Returns:
            Formatted prompt string
        """
        prompt_template = self.load_prompt(prompt_name)
        return prompt_template.format(**kwargs)
    
    def list_available_prompts(self) -> list:
        """
        List all available prompt files
        
        Returns:
            List of available prompt names (without .txt extension)
        """
        prompt_files = list(self.prompts_dir.glob("*.txt"))
        return [f.stem for f in prompt_files]
    
    def clear_cache(self):
        """Clear the cached prompts"""
        self._cached_prompts.clear()


# Global prompt loader instance
_prompt_loader = None


def get_prompt_loader(prompts_dir: str = None) -> PromptLoader:
    """
    Get the global prompt loader instance
    
    Args:
        prompts_dir: Directory containing prompt files
        
    Returns:
        PromptLoader instance
    """
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader(prompts_dir)
    return _prompt_loader


def load_prompt(prompt_name: str, prompts_dir: str = None) -> str:
    """
    Convenience function to load a prompt
    
    Args:
        prompt_name: Name of the prompt file
        prompts_dir: Directory containing prompt files
        
    Returns:
        Prompt content as string
    """
    loader = get_prompt_loader(prompts_dir)
    return loader.load_prompt(prompt_name)


def format_prompt(prompt_name: str, prompts_dir: str = None, **kwargs) -> str:
    """
    Convenience function to load and format a prompt
    
    Args:
        prompt_name: Name of the prompt file
        prompts_dir: Directory containing prompt files
        **kwargs: Variables to format in the prompt
        
    Returns:
        Formatted prompt string
    """
    loader = get_prompt_loader(prompts_dir)
    return loader.format_prompt(prompt_name, **kwargs)
