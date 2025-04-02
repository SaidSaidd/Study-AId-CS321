from pathlib import Path
import google.generativeai as genai
from .AIFeatures import AIFeatures
import re    

class AIFlashcards(AIFeatures):
    '''
        Inherits from AIFeatures but customizes the prompt to generate flashcards.
        Also adds a utility method create_dict() to parse the output.
    '''
    def __init__(self, aiFeatures):
        # Copy over relevant attributes from the already-initialized aiFeatures:
        self.api_key = aiFeatures.api_key
        self.model = aiFeatures.model
        self.file_path = aiFeatures.file_path
        self.file_content = aiFeatures.file_content

        # Override the prompt with more explicit instructions
        self.prompt = (
            "You are given the text content extracted from a PDF or TXT file. \n"
            "Create flashcards by following these EXACT instructions:\n"
            "1. Identify 5-10 important keywords or concepts from the text.\n"
            "2. For each keyword, write a clear, concise definition (1-2 sentences).\n"
            "3. Format each flashcard EXACTLY like this, with a number, colon, term, hyphen, and definition:\n"
            "   1: Term - Definition\n"
            "   2: Another Term - Its definition\n\n"
            "Example format:\n"
            "1: Photosynthesis - The process by which plants convert sunlight into energy.\n"
            "2: Cellular Respiration - The process cells use to break down glucose and create ATP.\n\n"
            "Important: Each line MUST start with a number and colon, followed by the term, then a hyphen, then the definition.\n"
            "Start your response now, using only the format above with no additional text:"
        )

    def generate_content(self):
        '''Override parent method to add error checking'''
        content = super().generate_content()
        if not content or not content.strip():
            print("Warning: Generated content is empty")
            return "No content was generated"
        print(f"Generated flashcard content:\n{content}")  # Debug output
        return content

    def create_dict(self, generated_content):
        '''
            Parse the generated text into a dictionary of flashcards.
            Now with improved error handling and a more robust regex pattern.
        '''
        result_dict = {}
        if not generated_content or not generated_content.strip():
            print("Warning: No content to parse for flashcards")
            return result_dict

        # More flexible regex pattern that can handle various whitespace and formatting
        pattern = r'(?m)^\s*(\d+)\s*:\s*([^-]+?)\s*-\s*(.+?)(?=\s*(?:\d+\s*:|$))'
        matches = re.finditer(pattern, generated_content)
        
        for match in matches:
            num = match.group(1).strip()
            word = match.group(2).strip()
            definition = match.group(3).strip()
            
            if word and definition:  # Only add if both word and definition are non-empty
                result_dict[num] = {
                    "word": word,
                    "definition": definition
                }
                print(f"Parsed flashcard {num}: {word} - {definition}")  # Debug output
            else:
                print(f"Warning: Skipped invalid flashcard format at number {num}")

        if not result_dict:
            print("Warning: No valid flashcards were parsed from the content")
            
        return result_dict

    def get_word(self, word_and_def):
        return word_and_def.get("word", "").strip()

    def get_def(self, word_and_def):
        return word_and_def.get("definition", "").strip()