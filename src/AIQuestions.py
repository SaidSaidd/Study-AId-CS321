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
        self.file_content = aiFeatures.file_content

        self.num_questions = num_questions
        self.prompt = (
            f"You are given the text content extracted from a PDF or TXT file.\n\n"
            f"Generate exactly {num_questions} multiple-choice questions (MCQs) based on the file. "
            "Each question must have 4 answer choices (a, b, c, d) with exactly 1 correct answer.\n\n"
            "Follow this strict format:\n"
            "1.Question text\n"
            "a.AnswerChoice1\n"
            "b.AnswerChoice2\n"
            "c.AnswerChoice3\n"
            "d.AnswerChoice4\n"
            "c.CorrectAnswer\n\n"
            "Leave a blank line between each question.\n"
            "Do not add additional commentary or explanation—only the questions, choices, and the single correct answer line."
        )

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
            r"^\s*(\d+)\.\s*(.+?)\s*\n\s*a\.\s*(.+?)\s*\n\s*b\.\s*(.+?)\s*\n\s*c\.\s*(.+?)\s*\n\s*d\.\s*(.+?)\s*\n\s*([a-d])\.\s*(.+)",
            re.DOTALL | re.MULTILINE
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
                # group(7) is the letter of the correct answer, group(8) might be the text repeated.
                "correct_answer": match.group(7).strip()
            })

        return questions