from abc import ABC
from pathlib import Path
from google import genai

class AIFeatures(ABC):
    def __init__(self, api_key):
        self.file_path = None
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
    
    def set_file(self, file_path):
        # Check if the file is a pdf or txt file. Gemini is not compatible with all file types.
        if not (file_path.endswith('.pdf') or file_path.endswith('.txt')):
            raise ValueError("Only PDF and TXT files are allowed.")
        # Store the file path. 
        self.file_path = Path(file_path)
    
    def upload_file(self):
        if not self.file_path:
            raise ValueError("File path is not set. Call set_file() first.")
            
        uploaded_file = self.client.files.upload(file=self.file_path)
        print(f"Uploaded file: {uploaded_file}")
        return uploaded_file
    
    def generate_content(self):
        # Upload the file and then include it in the prompt
        uploaded_file = self.upload_file()
        #create prompt (file and text prompt
        #TODO: Prompt Engineering (more in subclasses)
        prompt = [uploaded_file, "\n\n", "Generate a brief summary of the file."]
        result = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return result.text

    def delete_all_files(self):
        #delete all files that gemini has stored. Run frequently during development to ensure file limit is not exceeded.
        files = self.client.files.list()
        if not files:
            print("No files to delete.")
            return
        
        print("Deleting all files:")
        for file in files:
            try:
                self.client.files.delete(name=file.name)
                print(f"Deleted file: {file.name}")
            except Exception as e:
                print(f"Failed to delete file: {file.name}. Error: {e}")
    
