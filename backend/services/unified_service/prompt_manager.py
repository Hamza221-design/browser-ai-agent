import os
import logging
from typing import Dict

class PromptManager:
    def __init__(self):
        self.prompts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts')
        logging.info("[PROMPT_MANAGER] Initialized")

    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt template from file."""
        prompt_path = os.path.join(self.prompts_dir, prompt_file)
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logging.error(f"Prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        except Exception as e:
            logging.error(f"Error loading prompt file {prompt_path}: {str(e)}")
            raise

    def create_prompt(self, user_message: str, context: str = "") -> str:
        """Create a prompt for GPT to understand user intent and provide actions."""
        prompt_template = self._load_prompt("unified_chat_prompt.txt")
        
        # Format the context section
        if context and context != "No relevant context available.":
            context_section = f"\n\nRELEVANT CONTEXT:\n{context}\n"
        else:
            context_section = "\n\nNo relevant context available.\n"
        
        # Create the full prompt with context
        full_prompt = prompt_template.format(
            user_message=user_message,
            context=context_section
        )
        
        logging.info(f"Created prompt with context length: {len(context_section)}")
        return full_prompt 