import pytest
import re
from AIFeatures import AIFeatures
from AIFlashcards import AIFlashcards
from AISummary import AISummary
from AIQuestions import AIQuestions

API_KEY = 'AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg'

# Create an instance of AIFeatures
ai_features = AIFeatures(API_KEY,"/Users/gill_/Desktop/notes.pdf")
ai_features.delete_all_files()
#flashcards = AIFlashcards(ai_features)
#summary = AISummary(ai_features)
#questions = AIQuestions(ai_features, 5)

def test_set_file_invalid_py():
    with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
        ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.py")
        
def test_set_file_invalid_docx():
    with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
        ai_features = AIFeatures(API_KEY, "\\Users\\gill_\\Desktop\\notes.docx")

def test_set_file_valid_pdf():
    ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.pdf")
    assert str(ai_features.file_path) == "\\Users\\gill_\\Desktop\\notes.pdf"

def test_set_file_valid_txt():
    ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.txt")
    assert str(ai_features.file_path) == "\\Users\\gill_\\Desktop\\notes.txt"

def test_upload_file_file_not_set():
    ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.pdf")
    ai_features.file_path = None
    with pytest.raises(ValueError, match=re.escape("File path is not set. Call set_file() first.")):
        ai_features.upload_file()

def test_upload_file_client_not_set():
    ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.pdf")
    ai_features.client = None
    with pytest.raises(ValueError, match=re.escape("Client is not set.")):
        ai_features.upload_file()

def test_upload_file():
    ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.pdf")
    assert ai_features.uploaded_file is not None

def test_generate_content_file_not_uploaded():
    ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.pdf")
    ai_features.uploaded_file = None
    with pytest.raises(ValueError, match=re.escape("File not uploaded. Call upload_file() first.")):
        ai_features.generate_content()

def test_generate_content_client_not_set():
    ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.pdf")
    ai_features.client = None
    with pytest.raises(ValueError, match=re.escape("Client is not set.")):
        ai_features.generate_content()

def test_generate_content():
    ai_features = AIFeatures(API_KEY, "/Users/gill_/Desktop/notes.pdf")
    result = ai_features.generate_content()
    assert result is not None

ai_features.delete_all_files()