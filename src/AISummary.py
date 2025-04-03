from .AIFeatures import AIFeatures

class AISummary(AIFeatures):
    '''
        Inherits from AIFeatures but customizes the prompt to produce
        a detailed summary of the file content.
    '''
    def __init__(self, aiFeatures):
        self.file_path = aiFeatures.file_path
        self.client = aiFeatures.client  
        self.uploaded_file = aiFeatures.uploaded_file

        self.prompt = (
            "Provide a detailed summary of the file. Split the summary into logical subsections. "
            "Focus on covering all key topics concisely, but do not add superfluous detail. "
            "Do not invent new information. Do not add extraneous commentary."
        )