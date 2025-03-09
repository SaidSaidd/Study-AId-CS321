import pytest
import re
from AIFeatures import AIFeatures
from AIFlashcards import AIFlashcards
from AISummary import AISummary
from AIQuestions import AIQuestions

API_KEY = 'AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg'

# Create an instance of AIFeatures
#ai_features = AIFeatures(API_KEY,"/Users/gill_/Desktop/notes.py")
#ai_features.delete_all_files()
#flashcards = AIFlashcards(ai_features)
#summary = AISummary(ai_features)
#ai_questions = AIQuestions(ai_features, 5)
'''
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

'''


#### Test cases for AIQuestions

@pytest.fixture
def ai_features():
    return AIFeatures(API_KEY, "C:/Users/rodri/Desktop/test.txt")

@pytest.fixture
def ai_questions(ai_features):
    return AIQuestions(ai_features, 5)

def test_generate_content(ai_questions):
    result = ai_questions.generate_content()
    assert result is not None
    


def test_parse_output_text(ai_questions):
    ai_output = ai_questions.generate_content()
    print("\nGenerated AI Output:\n", ai_output)
    parsed_questions = ai_questions.parse_output(ai_output)
    print("\nParsed Questions:\n", parsed_questions)
    
    assert isinstance(parsed_questions, list)
    assert len(parsed_questions) > 0
    assert "question" in parsed_questions[0]
    assert "options" in parsed_questions[0]
    assert "correct_answer" in parsed_questions[0]
    
    
    
#ai_features.delete_all_files()

## Test cases for AIFlashcards

def test_flashcards(api_key, file_path):
    print("test_flashcards() started") 
    try:
        #Create the instance with the input file_path
        print("Creating AIFeatures instance...")  
        ai_features = AIFeatures(api_key, file_path)
        
        #Create a flashcard instance 
        print("Creating AIFlashcards instance...")  
        flashcards = AIFlashcards(ai_features)
        
        #generate the flashcards
        print("Generating flashcards...")  
        try:
            generated_text = flashcards.generate_content()
            print("Generated text:", generated_text)  
        except Exception as e:
            print("Error in generate_content():", str(e))
            generated_text = None
        
        #if generated text was successful
        if generated_text:
            #parse content into a dictionary
            print("Parsing generated text...") 
            try:
                flashcards_dict = flashcards.create_dict(generated_text)
                print("Parsed dictionary:", flashcards_dict) 
            except Exception as e:
                print("Error in create_dict():", str(e))
                flashcards_dict = {}
            
            #print the flashcards
            print("Printing flashcards...")  
            for key, value in flashcards_dict.items():
                print(f"{key}: {value['word']} - {value['definition']}")
            
            #print the word and definition
            for key, value in flashcards_dict.items():
                print(f'Word: {flashcards.get_word(value)}')
                print(f'Definition: {flashcards.get_def(value)}')
        
    except Exception as e:
        print("An error occurred:", str(e))
    
    #Delete all files
    finally:
        print("Deleting all files...")
        ai_features.delete_all_files()
