from abc import ABC
from pathlib import Path
from google import genai

class AIFeatures(ABC):
    '''
        Parameters:
            self: this parameter identifies the client user instance of the system
            api_key: this parameter identifies the users given API key 
            file_path: this parameter identifies the local file path of the selected document to be uploaded
    
        Method calls:
            This method calls the set_file() and upload_file() methods that are defined in this class

        This method is the constructor for AIFeatures.
        This method creates an object of the self instance information including the users API key and document path.
    '''
    def __init__(self, api_key, file_path):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.prompt = "Generate a brief summary of the file."
        self.set_file(file_path)
        self.uploaded_file = self.upload_file()
    
    '''
        Parameters:
            self: this parameter identifies the client user instance of the system
            file_path: this parameter saves the file path of the file to upload as long as it ends in .pdf or .txt

        Error Control:
            This method prints a statement if the wrong type of file is tried to be uploaded.

        This method identifies which file the user wants to upload to Gemini and then saves the file_path to identify that file
    '''
    def set_file(self, file_path):
        # Check if the file is a pdf or txt file. Gemini is not compatible with all file types.
        if not (file_path.endswith('.pdf') or file_path.endswith('.txt')):
            raise ValueError("Only PDF and TXT files are allowed.")
        # Store the file path. 
        self.file_path = Path(file_path)
    
    '''
        Parameters:
            self: this parameter identifies the client user instance of the system

        Error Control:
            This method prints a statement if the set_file() function is not run before this function occurs

        Return:
            This method returns Gemini's output that contains a string of data about the file uploaded

        This method uploads the document to Gemini and gets a string of information back from the API
    '''
    def upload_file(self):
        if not self.client:
            raise ValueError("Client is not set.")
        
        if not self.file_path:
            raise ValueError("File path is not set. Call set_file() first.")

        uploaded_file = self.client.files.upload(file=self.file_path)
        return uploaded_file
    
    '''
        Parameters:
            self: this parameter identifies the client user instance of the system

        Return:
            This method returns the results from Gemini output based on imported file data

        This method gets an output from Gemini based on prompt defined earlier.
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
        Parameters:
            self: this parameter identifies the client user instance of the system

        Error Control:
            This method prints a statement if the file was not deleted

        This method deletes all files from Gemini, if there are any saved in Gemini.
        Needed to comply with Gemini free tiers file storage quota.
    '''
    def delete_all_files(self):
        #updated to return number of files deleted.
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
    