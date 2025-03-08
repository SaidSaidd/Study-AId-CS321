from abc import ABC
from pathlib import Path
from google import genai
from AIFeatures import AIFeatures

class AISummary(AIFeatures):
    def __init__(self, aiFeatures):
        # take attributes from already initialized aiFeatures variables.
        self.file_path = aiFeatures.file_path
        self.client = aiFeatures.client  

    def generate_content(self):
        # upload file
        uploaded_file = self.upload_file()
        
        #create prompt (file and text prompt)
        #TODO: Prompt Engineering 
        prompt = [uploaded_file, "\n\n", "Provide a detailed summary of the file provided. Split the summary into subsections and make sure all important information from the file is included in the summary."]
        result = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return result.text 