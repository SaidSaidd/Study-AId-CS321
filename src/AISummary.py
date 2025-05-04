from .AIFeatures import AIFeatures
import re

class AISummary(AIFeatures):
    '''
        Inherits from AIFeatures but customizes the prompt to produce
        a detailed summary of the file content with logical subsections.
        Also adds utility methods to format the summary for better display.
    '''
    def __init__(self, aiFeatures):
        self.file_path = aiFeatures.file_path
        self.client = aiFeatures.client  
        self.uploaded_file = aiFeatures.uploaded_file
        self.sections = {}

        self.prompt = (
            "Provide a detailed summary of the file. Split the summary into 3-5 logical subsections with clear headings. "
            "Format each section with a '## ' heading followed by the section content. "
            "Focus on covering all key topics concisely, but do not add superfluous detail. "
            "Do not invent new information. Do not add extraneous commentary. "
            "Use markdown formatting for emphasis where appropriate."
        )
    
    def generate_content(self):
        '''Override parent method to add error checking'''
        content = super().generate_content()
        if not content or not content.strip():
            print("Warning: Generated summary content is empty")
            return "No summary content was generated"
        return content
    
    def parse_sections(self, generated_content):
        '''Parse the generated content into sections'''
        self.sections = {}
        
        # Split content by section headers (## )
        pattern = r'##\s+(.+?)\n([\s\S]*?)(?=##\s+|$)'
        matches = re.finditer(pattern, generated_content)
        
        section_num = 1
        for match in matches:
            section_title = match.group(1).strip()
            section_content = match.group(2).strip()
            self.sections[str(section_num)] = {
                "title": section_title,
                "content": section_content
            }
            section_num += 1
            
        # If no sections were found, create a single section with the entire content
        if not self.sections:
            self.sections["1"] = {
                "title": "Summary",
                "content": generated_content.strip()
            }
            
        return self.sections
    
    def format_for_display(self, generated_content):
        '''Format the summary for display in markdown'''
        sections = self.parse_sections(generated_content)
        formatted_content = ""
        
        for section_num, section in sections.items():
            formatted_content += f"## {section['title']}\n\n{section['content']}\n\n"
        
        return formatted_content.strip()