from pathlib import Path
from google import genai
from AIFeatures import AIFeatures

class AISummary(AIFeatures):
    def __init__(self, aiFeatures):
        # take attributes from already initialized aiFeatures variables.
        self.file_path = aiFeatures.file_path
        self.client = aiFeatures.client  
        self.prompt = """Provide a detailed summary of the file provided. 
                         Split the summary into subsections and make sure all important information from the file is included in the summary. 
                         Try not defining to many topics. Instead, focus on giving a detialed overview of the contents of the file."
"""