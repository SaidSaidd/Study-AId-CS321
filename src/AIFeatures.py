## `src\AIFeatures.py`

from abc import ABC
from pathlib import Path
import google.generativeai as genai

class AIFeatures(ABC):
    '''
        Parameters:
            api_key: The user's Google GenAI API key.
            file_path: Path of the local .pdf or .txt file to read.

        This class reads the file into memory (file_content) and initializes
        a GenerativeModel for prompt-based content generation.
    '''
    def __init__(self, api_key, file_path):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        # You can pick whichever GenAI model you like:
        self.model = genai.GenerativeModel('gemini-2.0-flash')

        # Default prompt (subclasses may override self.prompt)
        self.prompt = "Generate a brief summary of the file."

        # Store file contents here after reading:
        self.file_content = None

        self.set_file(file_path)
        self._read_file()

    def set_file(self, file_path):
        '''
            Ensures file exists and is .pdf or .txt
        '''
        if not isinstance(file_path, (str, Path)):
            raise ValueError("File path must be a string or Path object.")

        path_obj = Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path_obj}")

        if path_obj.suffix.lower() not in ['.txt', '.pdf']:
            raise ValueError("Only .txt and .pdf files are supported.")

        self.file_path = path_obj

    def _read_file(self):
        '''
        Internal method to read the file content into self.file_content.
        Tries several common encodings.
        '''
        if not self.file_path:
            raise ValueError("File path is not set. Call set_file() first.")

        encodings = ['utf-8', 'latin-1', 'cp1252']
        last_error = None

        for encoding in encodings:
            try:
                with open(self.file_path, 'r', encoding=encoding) as file:
                    self.file_content = file.read()
                    return
            except UnicodeDecodeError as e:
                last_error = e

        raise ValueError(
            f"Error reading file: Unable to decode with any of the attempted "
            f"encodings. Last error: {str(last_error)}"
        )

    def generate_content(self):
        '''
            Uses self.file_content and self.prompt to generate content from the model.
            Returns the resulting text.
        '''
        if not self.file_content:
            raise ValueError("File content not loaded. Make sure the file is set and readable.")

        prompt = f"{self.file_content}\n\n{self.prompt}"
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise ValueError(f"Error generating content: {str(e)}")