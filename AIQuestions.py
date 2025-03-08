from pathlib import Path
from google import genai
from AIFeatures import AIFeatures
import re
class AIQuestions(AIFeatures):
    def __init__(self, aiFeatures, num_questions):
        # take attributes from already initialized aiFeatures variables.
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
                    Do not include any extra text, explanations, or formatting outside this structure.
                    The correct answer at the bottom must start with the corresponding letter (a, b, c, or d).
                    Ensure at least one answer is correct, and all incorrect answers should be reasonable yet incorrect.
                    There must be exactly one correct answer per question.
                    Generate {self.num_questions} questions based on the content provided. Do not include any introductory or concluding text—only output the questions in the specified format.
                    Add an empty line between questions.
                    """
        self.uploaded_file = aiFeatures.uploaded_file

    def parse_output(self, generated_text):
        questions = []
        pattern = re.compile(r"(\d+)\.\s(.+?)\n(a\..+?)\n(b\..+?)\n(c\..+?)\n(d\..+?)\n([a-d])\.\s(.+?)\n", re.DOTALL)
        
        for match in pattern.finditer(generated_text):
            question_data = {
                "question_number": int(match.group(1)),
                "question": match.group(2).strip(),
                "options": {
                    "a": match.group(3)[2:].strip(),
                    "b": match.group(4)[2:].strip(),
                    "c": match.group(5)[2:].strip(),
                    "d": match.group(6)[2:].strip(),
                },
                "correct_answer": match.group(7).strip(),
                "correct_answer_text": match.group(8).strip()
            }
            questions.append(question_data)
        
        return questions