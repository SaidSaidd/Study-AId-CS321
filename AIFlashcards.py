from pathlib import Path
from google import genai
from AIFeatures import AIFeatures
import re    

class AIFlashcards(AIFeatures):
    '''
        Parameters:
            self: this parameter identifies the client user instance of the system
            The self object is the same one created in AI Features class. 
            aiFeatures: this parameter is a reference to the Ai Feature class and is used to get information from AIFeatures methods and variables

        This method creates an object with initalized values. The object values are based on the AIFeatures class values located in aiFeatures parameter.
    '''
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
        
    '''
        Parameters:
            self: this parameter identifies the client user instance of the system
            generated_content: this parameter identifies the content pulled from Gemini output to save in the dictonary
    
        Returns:
            This method returns a directory of the information from the gemini call

        This method takes information from a gemini call and initializes it in a dictionary object. 
        This method dictonary works as explained below:
            The key of the dictionary is the number of the word.
            The value is a dictionary itself.
            The key of the sub dictionary is the word.
            The value of the sub dictionary is the definition.
    '''
    def create_dict(self, generated_content):
        self.result_dict = {}
    
        pattern = r'(?m)^\s*(?P<num>\d+):\s*(?P<word>.*?)\s*-\s*(?P<definition>.*?)(?=\n\s*\d+:|\Z)'
        
        matches = re.finditer(pattern, generated_content)
        for match in matches:
            num = match.group("num").strip()
            word = match.group("word").strip()
            definition = match.group("definition").strip()
            self.result_dict[num] = {"word": word, "definition": definition}
        
        return self.result_dict

    '''
        Parameters:
            self: this parameter identifies the client user instance of the system
            word_and_def: this parameter is the word and definition of the dictionary
        
        Return:
            this method returns the word in the given word and definition pair

        This method gets the word from a word and definition pair.
    '''
    def get_word(self, word_and_def):
        return word_and_def.get("word", "").strip()
    '''
        Parameters:
            self: this parameter identifies the client user instance of the system
            word_and_def: this parameter is the word and definition of the dictionary
        
        Return:
            this method returns the definition in the given word and definition pair
 
        This method gets the definition from a word and definition pair.
    '''
    def get_def(self, word_and_def):
        return word_and_def.get("definition", "").strip()