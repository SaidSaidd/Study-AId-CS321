import pytest
import re

from AIFeatures import AIFeatures
from AIFlashcards import AIFlashcards
from AISummary import AISummary
from AIQuestions import AIQuestions

API_KEY = 'AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg'

@pytest.fixture(autouse=True)
def ai_features():
    ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.pdf")
    yield ai_features
    ai_features.delete_all_files()
'''
###Test cases for AIFeatures.py
def test_set_file_invalid_py():
    with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
        ai_features_py_test = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.py")
        
def test_set_file_invalid_docx():
    with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
        ai_features_docx_test = AIFeatures(API_KEY, "\\Users\\gill_\\Desktop\\notes.docx")

def test_set_file_valid_pdf(ai_features):
    assert str(ai_features.file_path) == "\\Users\\gill_\\Desktop\\notes.pdf"

def test_set_file_valid_txt():
    ai_features_txt_test = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.txt")
    assert str(ai_features_txt_test.file_path) == "\\Users\\gill_\\Desktop\\notes.txt"

def test_upload_file_file_not_set(ai_features):
    ai_features.file_path = None
    with pytest.raises(ValueError, match=re.escape("File path is not set. Call set_file() first.")):
        ai_features.upload_file()

def test_upload_file_client_not_set():
    ai_features2 = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.txt")
    ai_features2.client = None
    with pytest.raises(ValueError, match=re.escape("Client is not set.")):
        ai_features2.upload_file()

def test_upload_file(ai_features):
    assert ai_features.uploaded_file is not None

def test_generate_content_file_not_uploaded(ai_features):
    ai_features.uploaded_file = None
    with pytest.raises(ValueError, match=re.escape("File not uploaded. Call upload_file() first.")):
        ai_features.generate_content()

def test_generate_content_client_not_set():
    ai_features2 = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.txt")
    ai_features2.client = None    
    with pytest.raises(ValueError, match=re.escape("Client is not set.")):
        ai_features2.generate_content()

def test_generate_content(ai_features):
    result = ai_features.generate_content()
    assert result is not None

def test_delete_all_files_client_not_set():
    ai_features2 = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.pdf")
    ai_features2.client = None
    with pytest.raises(ValueError, match=re.escape("Client is not set.")):
        ai_features2.delete_all_files()

def test_delete_all_files(ai_features):
    print(len(ai_features.client.files.list()))
    result = ai_features.delete_all_files()
    assert result == 1

def test_delete_all_files_no_files_to_delete(ai_features):
    ai_features.delete_all_files()
    result = ai_features.delete_all_files()
    assert result == 0

def test_delete_all_files_multiple_files_to_delete(ai_features):
    ai_features2 = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.txt")
    result = ai_features.delete_all_files()
    assert result == 2
'''
#### Test cases for AIQuestions
def test_parse_output_text(ai_features):
    ai_questions = AIQuestions(ai_features, 5)
    ai_output = ai_questions.generate_content()
    parsed_questions = ai_questions.parse_output(ai_output)
    assert isinstance(parsed_questions, list)
    assert len(parsed_questions) == 5
    assert "question" in parsed_questions[0]
    assert "options" in parsed_questions[0]
    assert "correct_answer" in parsed_questions[0]

####Test cases for AIFlashcards
def test_create_dict(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    sample_content = """
        1: AIFeatures - Class providing method to generate content using Gemini.
        2: AISummary - Class that creates a detailed summary using Gemini.
        3: AIFlashcards - Class that creates flashcards of key words using Gemini.
        4: AIQuestions - Class that provides practice questions using Gemini.
    """.strip()  # Strip leading/trailing whitespace

    flashcards_dict = ai_flashcards.create_dict(sample_content)
    
    expected = {
        "1": {"word":"AIFeatures","definition":"Class providing method to generate content using Gemini."},
        "2": {"word":"AISummary","definition":"Class that creates a detailed summary using Gemini."},  # Ensure consistency
        "3": {"word":"AIFlashcards","definition":"Class that creates flashcards of key words using Gemini."},
        "4": {"word":"AIQuestions","definition":"Class that provides practice questions using Gemini."}
    }
    
    assert isinstance(flashcards_dict, dict)
    assert flashcards_dict == expected  # AssertionError if mismatch

def test_create_dict_ai_input(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    ai_output = ai_flashcards.generate_content()
    flashcards = ai_flashcards.create_dict(ai_output)
    
    assert isinstance(flashcards, dict)
    assert isinstance(flashcards["1"], dict)
    assert isinstance(flashcards["1"]["word"], str)
    assert isinstance(flashcards["1"]["definition"], str)


    
