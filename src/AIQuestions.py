from pathlib import Path
import google.generativeai as genai
from .AIFeatures import AIFeatures
import re

class AIQuestions(AIFeatures):
    '''
        Inherits from AIFeatures but customizes the prompt to generate multiple-choice questions.
    '''
    def __init__(self, aiFeatures, num_questions):
        self.api_key = aiFeatures.api_key
        self.model = aiFeatures.model
        self.file_path = aiFeatures.file_path

        self.client = aiFeatures.client  
        self.num_questions = num_questions
        self.prompt = f"""You are given the text content extracted from a PDF file. 
                    Your task is to generate {self.num_questions} multiple-choice questions (MCQs) based on the content of the file. 
                    The question should be about the topic dicussed in the file, not the examples.
                    For example, if the file is about quadratic equations, the questions should be quadratic problems similar to those in the file, not about the examples in the file.
                    Each question should have exactly 4 answer choices, with only 1 correct answer.
                    Strictly follow this format:
                    1.Question  
                    a.AnswerChoice1  
                    b.AnswerChoice2  
                    c.AnswerChoice3  
                    d.AnswerChoice4  
                    b.CorrectAnswer 
                    Ensure the whitespace matches this format exactly.
                    Do not include any extra text, explanations, or formatting outside this structure.
                    The correct answer at the bottom must start with the corresponding letter (a, b, c, or d).
                    Ensure exactly one answer is correct, and all incorrect answers should be reasonable yet incorrect.
                    There must be exactly one correct answer per question.
                    Generate {self.num_questions} questions based on the content provided. Do not include any introductory or concluding text—only output the questions in the specified format.
                    Add an empty line between questions.
                    If there are example problems in the file, try coming up with a few problems similar to the example problems.
                    Try righting problems that require application of the material covered in the file and not just vocabulary questions.
                    """
        self.uploaded_file = aiFeatures.uploaded_file
        self.file_content = aiFeatures.file_content




    def parse_output(self, generated_text):
        '''
        Parses the generated MCQs into a list of dicts:
          [
            {
              "question_number": 1,
              "question": "Some question?",
              "options": {
                "a": "option A text",
                "b": "option B text",
                "c": "option C text",
                "d": "option D text"
              },
              "correct_answer": "a"  # or b/c/d
            },
            ...
          ]
        '''
        questions = []

        # A fairly naive regex approach – you may want to adjust based on formatting
        pattern = re.compile(
            r"\s*(\d+)\.\s*(.+?)\n\s*"
            r"\s*a\.\s*(.+?)\n\s*"
            r"\s*b\.\s*(.+?)\n\s*"
            r"\s*c\.\s*(.+?)\n\s*"
            r"\s*d\.\s*(.+?)\n\s*"
            r"\s*([a-d])\.\s*(.+?)(?=\n\s*\d+\.|\n*$)",
            re.DOTALL
        )

        for match in pattern.finditer(generated_text):
            questions.append({
                "question_number": int(match.group(1)),
                "question": match.group(2).strip(),
                "options": {
                    "a": match.group(3).strip(),
                    "b": match.group(4).strip(),
                    "c": match.group(5).strip(),
                    "d": match.group(6).strip(),
                },

                "correct_answer": match.group(7) if match.group(7) is not None else "No correct answer provided"
            })
            
        return questions