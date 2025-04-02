from pathlib import Path
import google.generativeai as genai
from .AIFeatures import AIFeatures

class AISummary(AIFeatures):
    '''
        Inherits from AIFeatures but customizes the prompt to produce
        a detailed summary of the file content.
    '''
    def __init__(self, aiFeatures):
        self.api_key = aiFeatures.api_key
        self.model = aiFeatures.model
        self.file_path = aiFeatures.file_path
        self.file_content = aiFeatures.file_content

        self.prompt = (
            "Provide a detailed summary of the file. Split the summary into logical subsections. "
            "Focus on covering all key topics concisely, but do not add superfluous detail. "
            "Do not invent new information. Do not add extraneous commentary."
        )