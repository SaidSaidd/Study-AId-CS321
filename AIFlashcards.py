from abc import ABC
from pathlib import Path
from google import genai
from AIFeatures import AIFeatures

class AIFlashcards(AIFeatures):
    def __init__(self, aiFeatures):
        from AIFeatures import AIFeatures

class AIFlashcards(AIFeatures):
    def __init__(self, aiFeatures):
        # take attributes from already initialized aiFeatures variables.
        self.file_path = aiFeatures.file_path
        self.client = aiFeatures.client  

    def generate_content(self):
        # upload file
        uploaded_file = self.upload_file()
        #create prompt (file and text prompt)
        #TODO: Prompt Engineering (more in subclasses)
        prompt = [uploaded_file, "\n\n", "Find key words in the files and provide definitions for them. Read the whole file and identify as many key words as possibl."]
        result = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        print(f"\nGenerated content:\n{result.text}")
        return result.text 