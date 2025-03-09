from abc import ABC
from pathlib import Path
from google import genai

class AIFeatures(ABC):
    '''
        The constructor for AIFeatures.
        Initializes the Client using the provided API key.
        Set the file path to the provided file path.
        Upload the file to the client.  
        Create the client
    '''
    def __init__(self, api_key, file_path):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.prompt = "Generate a brief summary of the file."
        self.set_file(file_path)
        self.uploaded_file = self.upload_file()
    
    '''
        Set file path to the specified file path.
        Ensure that the file is a pdf or a text file.
    '''
    def set_file(self, file_path):
        # Check if the file is a pdf or txt file. Gemini is not compatible with all file types.
        if not (file_path.endswith('.pdf') or file_path.endswith('.txt')):
            raise ValueError("Only PDF and TXT files are allowed.")
        # Store the file path. 
        self.file_path = Path(file_path)
    
    '''
        Upload file to Gemini.
        Ensure the file path is set.
        Gemini outputs a string  containing data about the file uploaded.
        Return Gemini's output.
    '''
    def upload_file(self):
        if not self.client:
            raise ValueError("Client is not set.")
        
        if not self.file_path:
            raise ValueError("File path is not set. Call set_file() first.")

        uploaded_file = self.client.files.upload(file=self.file_path)
        return uploaded_file
    
    '''
        Get output from Gemini based on prompt defined earlier.
        Returns Gemini's output.
    '''
    def generate_content(self):
        # Upload the file and then include it in the prompt
        #create prompt (file and text prompt
        #TODO: Prompt Engineering (more in subclasses)
        if not self.client:
            raise ValueError("Client is not set.")
        
        if not self.uploaded_file:
            raise ValueError("File not uploaded. Call upload_file() first.")
        prompt = [self.uploaded_file, "\n\n", self.prompt]
        result = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return result.text

    '''
        Delete all files from Gemini.
        Needed to comply with Gemini free tiers file storage quota.
    '''
    def delete_all_files(self):
        if not self.client:
            raise ValueError("Client is not set.")
        #delete all files that gemini has stored. Run frequently during development to ensure file limit is not exceeded.
        files = self.client.files.list()
        count = 0
        if not files:
            return 0
        
        for file in files:
            try:
                self.client.files.delete(name=file.name)
                count += 1
            except Exception as e:
                print(f"Failed to delete file: {file.name}. Error: {e}")
        
        return count
    
