from pathlib import Path
from google import genai
from AIFeatures import AIFeatures
import re    

class AIFlashcards(AIFeatures):
    def __init__(self, aiFeatures):
        # take attributes from already initialized aiFeatures variables.
        self.file_path = aiFeatures.file_path
        self.client = aiFeatures.client  
        self.prompt = """You are given the text content extracted from a PDF file. \
                         Your task is to: 1. Identify as many key words in the text as you can. 
                                          2. For each key word, provide a detailed definition that includes relevant context—even if that context is not explicitly mentioned in the PDF.
                                          3. Output your results as a numbered list, strictly following this format:
                                             1: Word - Definition.
                          Make sure that the output contains only the numbered list and nothing else. 
                          Do not include any additional commentary, explanations, or formatting.
                          Only pick words that are relevant to the main topic of the file.
                          For example, if a math file has an example that includes medicine, do not define the medical concepts.
                      """
        self.uploaded_file = aiFeatures.uploaded_file
        
    def create_dict(self, generated_content):
        self.result_dict = {}
    
        pattern = r'(?m)^(?P<num>\d+):\s*(?P<word>.*?)\s*-\s*(?P<definition>.*?)(?=\n\d+:|\Z)'
        
        matches = re.finditer(pattern, generated_content)
        for match in matches:
            num = match.group("num").strip()
            word = match.group("word").strip()
            definition = match.group("definition").strip()
            self.result_dict[num] = {"word": word, "definition": definition}
        
        return self.result_dict

    def get_word(self, word_and_def):
        return word_and_def.get("word", "").strip()

    def get_def(self, word_and_def):
        return word_and_def.get("definition", "").strip()