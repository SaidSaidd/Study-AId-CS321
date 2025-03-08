import pytest
from AIFeatures import AIFeatures
from AIFlashcards import AIFlashcards
from AISummary import AISummary
from AIQuestions import AIQuestions

API_KEY = 'AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg'

# Create an instance of AIFeatures
#ai_features = AIFeatures(API_KEY,"/Users/chocalmonds/test/test.txt")
#flashcards = AIFlashcards(ai_features)
#summary = AISummary(ai_features)
#questions = AIQuestions(ai_features, 5)


def test_set_file_invalid_py():
    with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
        ai_features = AIFeatures(API_KEY, "/Users/chocalmonds/test/test.py")
        #ai_features.set_file("/Users/chocalmonds/test/test.py") no need to call set_file() seperately. set_file is called in the constructor.

def test_set_file_invalid_docx():
    with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
        ai_features = AIFeatures(API_KEY, "/Users/chocalmonds/test/test.docx")

def test_set_file_valid_pdf():
    ai_features = AIFeatures(API_KEY, "/Users/chocalmonds/test/test.pdf")
    assert str(ai_features.file_path) == "/Users/chocalmonds/test/test.pdf"

def test_set_file_valid_txt():
    ai_features = AIFeatures(API_KEY, "/Users/chocalmonds/test/test.txt")
    assert str(ai_features.file_path) == "/Users/chocalmonds/test/test.txt"

test_set_file_invalid_py()
test_set_file_invalid_docx()
test_set_file_valid_pdf()
test_set_file_valid_txt()

ai_features.delete_all_files()
