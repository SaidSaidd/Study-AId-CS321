from .AIFeatures import AIFeatures
import re    

class AIFlashcards(AIFeatures):
    '''
        Inherits from AIFeatures but customizes the prompt to generate flashcards.
        Also adds a utility method create_dict() to parse the output.
    '''
    def __init__(self, aiFeatures):
        # take attributes from already initialized aiFeatures variables.
         self.file_path = aiFeatures.file_path
         self.client = aiFeatures.client  
         self.uploaded_file = aiFeatures.uploaded_file
         self.prompt = """You are given the text content extracted from a PDF file. 
                          Your task is to: 1. Identify as many key words in the text as you can. 
                                           2. For each key word, provide a detailed definition that includes relevant context—even if that context is not explicitly mentioned in the PDF.
                                           3. Output your results as a numbered list, strictly following this format:
                                              1: Word;Definition.
                           Make sure that the output contains only the numbered list and nothing else. 
                           Do not include any additional commentary, explanations, or formatting.
                           Only pick words that are relevant to the main topic of the file.
                           For example, if a math file has an example that includes medicine, do not define the medical concepts.
                           Ignore all words from example problems. Focus on just the notes.
                           Each words should be relevant to the main topic directly.
                       """

    def generate_content(self):
        '''Override parent method to add error checking'''
        content = super().generate_content()
        if not content or not content.strip():
            print("Warning: Generated content is empty")
            return "No content was generated"
        print(f"Generated flashcard content:\n{content}")  # Debug output
        return content

    def create_dict(self, generated_content):
         self.result_dict = {}
 
         pattern = r'(?m)^\s*(?P<num>\d+):\s*(?P<word>.*?)\s*;\s*(?P<definition>.*?)(?=\n\s*\d+:|\Z)'
 
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