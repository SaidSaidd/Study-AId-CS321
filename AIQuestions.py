from pathlib import Path
from google import genai
from AIFeatures import AIFeatures

class AIQuestions(AIFeatures):
    def __init__(self, aiFeatures, num_questions):
        # take attributes from already initialized aiFeatures variables.
        self.file_path = aiFeatures.file_path
        self.client = aiFeatures.client  
        self.num_questions = num_questions
        self.prompt = f"""You are given the text content extracted from a PDF file. 
                    Your task is to generate {self.num_questions} multiple-choice questions (MCQs) based on the content of the file. 
                    Each question should have exactly 4 answer choices, with only 1 correct answer.
                    Strictly follow this format:
                    1.Question  
                    a.AnswerChoice1  
                    b.AnswerChoice2  
                    c.AnswerChoice3  
                    d.AnswerChoice4  
                    b.CorrectAnswer  
                    Do not include any extra text, explanations, or formatting outside this structure.
                    The correct answer at the bottom must start with the corresponding letter (a, b, c, or d).
                    Ensure at least one answer is correct, and all incorrect answers should be reasonable yet incorrect.
                    There must be exactly one correct answer per question.
                    Generate {self.num_questions} questions based on the content provided. Do not include any introductory or concluding text—only output the questions in the specified format.
                    """

    def generate_content(self):
            # upload file
            uploaded_file = self.upload_file()
            
            #create prompt (file and text prompt)
            #TODO: Prompt Engineering 
            prompt = [uploaded_file, "\n\n", self.prompt]
            result = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return result.text 