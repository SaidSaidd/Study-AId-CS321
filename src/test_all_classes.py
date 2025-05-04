import pytest
import re
import os
import tempfile
from unittest.mock import MagicMock, patch

# Mock the genai module before importing our classes
sys_modules_patcher = patch.dict('sys.modules', {
    'google': MagicMock(),
    'google.genai': MagicMock(),
})
sys_modules_patcher.start()

# Now import our classes after mocking their dependencies
from .AIFeatures import AIFeatures
from .AIFlashcards import AIFlashcards
from .AISummary import AISummary
from .AIQuestions import AIQuestions

# Use a dummy API key for testing
API_KEY = 'dummy_api_key'

# Create a temporary test file
@pytest.fixture
def test_pdf_file(request):
    # Default to creating the file unless specified otherwise
    create_file = getattr(request, 'param', True)
    temp_path = None
    if create_file:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'Test PDF content')
            temp_path = f.name
    else:
        temp_path = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
        os.unlink(temp_path)

    yield temp_path
    # Clean up after test
    if os.path.exists(temp_path):
        os.unlink(temp_path)
        
@pytest.fixture
def test_txt_file(request):
    # Default to creating the file unless specified otherwise
    create_file = getattr(request, 'param', True)
    temp_path = None
    if create_file:
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'Test TXT content')
            temp_path = f.name
    else:
        # Create a nonexistent path for the False branch
        temp_path = tempfile.NamedTemporaryFile(suffix='.txt', delete=False).name
        os.unlink(temp_path)  # Delete it immediately to ensure it doesn’t exist
    yield temp_path
    # Clean up after test
    if os.path.exists(temp_path):
        os.unlink(temp_path)
# Mock the AIFeatures class to avoid actual API calls
@pytest.fixture
def mock_client():
    mock = MagicMock()
    # Setup the mock to return expected values
    mock_file = MagicMock()
    mock_file.name = 'test_file'
    mock.files.upload.return_value = mock_file
    mock.files.list.return_value = [mock_file]
    mock.models.generate_content.return_value.text = "Generated content for testing"
    return mock

@pytest.fixture
def ai_features(test_pdf_file, mock_client):
    # Create AIFeatures instance with mocked components
    with patch.object(AIFeatures, '__init__', return_value=None):
        ai_features = AIFeatures(API_KEY, test_pdf_file)
        # Set up the instance manually
        ai_features.api_key = API_KEY
        ai_features.client = mock_client
        ai_features.prompt = "Generate a brief summary of the file."
        ai_features.file_path = test_pdf_file
        # Mock the uploaded file
        mock_file = MagicMock()
        mock_file.name = 'test_file'
        ai_features.uploaded_file = mock_file
        yield ai_features

###Test cases for AIFeatures.py
def test_create_AIFeatures_instance():
    # Test the constructor of AIFeatures
    ai_test = AIFeatures("AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg", "file.pdf")
    assert ai_test.api_key == "AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg"

def test_set_file_invalid_py(mock_client):
    # Test directly with the set_file method
    with patch.object(AIFeatures, '__init__', return_value=None):
        ai_test = AIFeatures(None, None)
        ai_test.client = mock_client
        with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
            ai_test.set_file("test_file.py")
        
def test_set_file_invalid_docx(mock_client):
    # Test directly with the set_file method
    with patch.object(AIFeatures, '__init__', return_value=None):
        ai_test = AIFeatures(None, None)
        ai_test.client = mock_client
        with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
            ai_test.set_file("test_file.docx")

def test_set_file_valid_pdf(test_pdf_file, mock_client):
    with patch.object(AIFeatures, '__init__', return_value=None):
        ai_test = AIFeatures(None, None)
        ai_test.client = mock_client
        ai_test.set_file(test_pdf_file)
        assert str(ai_test.file_path).endswith('.pdf')

def test_set_file_valid_txt(test_txt_file, mock_client):
    with patch.object(AIFeatures, '__init__', return_value=None):
        ai_test = AIFeatures(None, None)
        ai_test.client = mock_client
        ai_test.set_file(test_txt_file)
        assert str(ai_test.file_path).endswith('.txt')

def test_upload_file_file_not_set(ai_features):
    ai_features.file_path = None
    with pytest.raises(ValueError, match=re.escape("File path is not set. Call set_file() first.")):
        ai_features.upload_file()

def test_upload_file_client_not_set(test_txt_file):
    with patch.object(AIFeatures, '__init__', return_value=None):
        ai_test = AIFeatures(None, None)
        ai_test.file_path = test_txt_file
        ai_test.client = None
        with pytest.raises(ValueError, match=re.escape("Client is not set.")):
            ai_test.upload_file()

def test_upload_file(ai_features):
    assert ai_features.uploaded_file is not None

def test_generate_content_file_not_uploaded(ai_features):
    ai_features.uploaded_file = None
    with pytest.raises(ValueError, match=re.escape("File not uploaded. Call upload_file() first.")):
        ai_features.generate_content()

def test_generate_content_client_not_set(test_txt_file):
    with patch.object(AIFeatures, '__init__', return_value=None):
        ai_test = AIFeatures(None, None)
        ai_test.file_path = test_txt_file
        ai_test.client = None
        with pytest.raises(ValueError, match=re.escape("Client is not set.")):
            ai_test.generate_content()

def test_generate_content(ai_features):
    result = ai_features.generate_content()
    assert result is not None
    
def test_aiflashcards_empty_content(ai_features):
    # Test empty content handling in AIFlashcards
    with patch.object(AIFlashcards, '__init__', return_value=None):
        ai_flashcards = AIFlashcards(None)
        ai_flashcards.file_path = ai_features.file_path
        ai_flashcards.client = ai_features.client
        ai_flashcards.uploaded_file = ai_features.uploaded_file
        
        # Mock the parent generate_content to return empty string
        with patch.object(AIFeatures, 'generate_content', return_value=""):
            result = ai_flashcards.generate_content()
            assert result == "No content was generated"

def test_delete_all_files_client_not_set(test_pdf_file):
    with patch.object(AIFeatures, '__init__', return_value=None):
        ai_test = AIFeatures(None, None)
        ai_test.file_path = test_pdf_file
        ai_test.client = None
        with pytest.raises(ValueError, match=re.escape("Client is not set.")):
            ai_test.delete_all_files()

def test_delete_all_files(ai_features):
    print(len(ai_features.client.files.list()))
    result = ai_features.delete_all_files()
    assert result == 1
    
def test_delete_all_files_with_exception(ai_features):
    # Test exception handling in delete_all_files
    mock_file = MagicMock()
    mock_file.name = "test_file_error"
    ai_features.client.files.list.return_value = [mock_file]
    
    # Mock delete to raise an exception
    ai_features.client.files.delete.side_effect = Exception("Test error")
    
    # Should handle the exception and return 0 (no successful deletions)
    result = ai_features.delete_all_files()
    assert result == 0

def test_delete_all_files_no_files_to_delete(ai_features):
    # Mock the files.list to return an empty list (no files to delete)
    ai_features.client.files.list.return_value = []
    result = ai_features.delete_all_files()
    assert result == 0

def test_delete_all_files_multiple_files_to_delete(ai_features, test_txt_file, mock_client):
    # Mock files.list to return multiple files
    mock_file1 = MagicMock()
    mock_file1.name = 'test_file1'
    mock_file2 = MagicMock()
    mock_file2.name = 'test_file2'
    ai_features.client.files.list.return_value = [mock_file1, mock_file2]
    
    result = ai_features.delete_all_files()
    assert result == 2

#### Test cases for AIQuestions
def test_parse_output_text(ai_features):
    ai_questions = AIQuestions(ai_features, 5)
    
    # Set up mock response with expected format
    sample_output = """
    1.What is the capital of France?  
    a.London  
    b.Paris  
    c.Berlin  
    d.Madrid  
    b.Paris
    
    2.What is the largest planet in our solar system?  
    a.Earth  
    b.Mars  
    c.Jupiter  
    d.Saturn  
    c.Jupiter
    
    3.Who wrote 'Romeo and Juliet'?  
    a.Charles Dickens  
    b.William Shakespeare  
    c.Jane Austen  
    d.Mark Twain  
    b.William Shakespeare
    
    4.What is the chemical symbol for gold?  
    a.Go  
    b.Au  
    c.Ag  
    d.Gl  
    b.Au
    
    5.Which of these is a primary color?  
    a.Green  
    b.Orange  
    c.Blue  
    d.Purple  
    c.Blue
    """
    
    # Mock the generate_content method
    with patch.object(ai_questions, 'generate_content', return_value=sample_output):
        ai_output = ai_questions.generate_content()
        parsed_questions = ai_questions.parse_output(ai_output)
        
        assert isinstance(parsed_questions, list)
        assert len(parsed_questions) == 5
        assert parsed_questions[0]["question"] == "What is the capital of France?"
        assert "options" in parsed_questions[0]
        assert parsed_questions[0]["options"]["a"] == "London"
        assert parsed_questions[0]["correct_answer"] == "b"

####Test cases for AIFlashcards
def test_generate_content_valid_flashcards():
    # Create a dummy instance with required attributes
    class Dummy:
        file_path = "dummy.pdf"
        client = MagicMock() 
        uploaded_file = MagicMock()

    ai_summary = AIFlashcards(Dummy())
    
    # Patch the generate_content method in AIFeatures to return an empty string
    with patch.object(AIFeatures, "generate_content", MagicMock(return_value="Flashcards generated.")):
        result = ai_summary.generate_content()
        assert result == "Flashcards generated."

def test_create_dict(ai_features):
    with patch.object(AIFlashcards, '__init__', return_value=None):
        ai_flashcards = AIFlashcards(None)
        ai_flashcards.file_path = ai_features.file_path
        ai_flashcards.client = ai_features.client  
        ai_flashcards.uploaded_file = ai_features.uploaded_file
        
        # Format content in the exact format expected by the regex pattern
        sample_content = """
        1: AIFeatures; Class providing method to generate content using Gemini.
        2: AISummary; Class that creates a detailed summary using Gemini.
        3: AIFlashcards; Class that creates flashcards of key words using Gemini.
        4: AIQuestions; Class that provides practice questions using Gemini.
        """.strip()

        flashcards_dict = ai_flashcards.create_dict(sample_content)
        
        expected = {
            "1": {"word":"AIFeatures","definition":"Class providing method to generate content using Gemini."},
            "2": {"word":"AISummary","definition":"Class that creates a detailed summary using Gemini."},
            "3": {"word":"AIFlashcards","definition":"Class that creates flashcards of key words using Gemini."},
            "4": {"word":"AIQuestions","definition":"Class that provides practice questions using Gemini."}
        }
        
        assert isinstance(flashcards_dict, dict)
        assert flashcards_dict == expected

def test_create_dict_ai_input(ai_features):
    with patch.object(AIFlashcards, '__init__', return_value=None):
        ai_flashcards = AIFlashcards(None)
        ai_flashcards.file_path = ai_features.file_path
        ai_flashcards.client = ai_features.client  
        ai_flashcards.uploaded_file = ai_features.uploaded_file
        
        # Mock the generate_content method to return properly formatted output
        mock_output = """1: Pythagoras; Greek mathematician known for the Pythagorean theorem.
                      2: Algorithm; Step-by-step procedure for calculations or problem-solving."""
        
        with patch.object(ai_flashcards, 'generate_content', return_value=mock_output):
            ai_output = ai_flashcards.generate_content()
            flashcards = ai_flashcards.create_dict(ai_output)
            
            assert isinstance(flashcards, dict)
            assert len(flashcards) == 2
            assert isinstance(flashcards["1"], dict)
            assert flashcards["1"]["word"] == "Pythagoras"
            assert flashcards["1"]["definition"] == "Greek mathematician known for the Pythagorean theorem."
            assert isinstance(flashcards["2"], dict)

def test_get_word_valid(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    word_and_def = {"word": "AIFeatures", "definition": "Class providing method to generate content using Gemini."}
    word = ai_flashcards.get_word(word_and_def)
    
    assert word == "AIFeatures"

def test_get_word_missing_word(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    word_and_def = {"definition": "Class providing method to generate content using Gemini."}
    word = ai_flashcards.get_word(word_and_def)
    
    assert word == ""

def test_get_word_with_spaces(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    word_and_def = {"word": "  AIFeatures  ", "definition": "Class providing method to generate content using Gemini."}
    word = ai_flashcards.get_word(word_and_def)
    
    # Assert that leading and trailing spaces are removed
    assert word == "AIFeatures"

def test_get_def_valid(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    word_and_def = {"word": "AIFeatures", "definition": "Class providing method to generate content using Gemini."}
    definition = ai_flashcards.get_def(word_and_def)
    
    # Assert that the definition is correctly extracted
    assert definition == "Class providing method to generate content using Gemini."

def test_get_def_missing_definition(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    word_and_def = {"word": "AIFeatures"}
    definition = ai_flashcards.get_def(word_and_def)
    
    # Assert that an empty string is returned when the definition is missing
    assert definition == ""

def test_get_def_with_spaces(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    word_and_def = {"word": "Some word", "definition": "  Class providing method to generate content using Gemini.  "}
    definition = ai_flashcards.get_def(word_and_def)
    
    # Assert that leading and trailing spaces are removed from the definition
    assert definition == "Class providing method to generate content using Gemini."

#Test cases for AISummary
def test_generate_content_valid_summary():
    # Create a dummy instance with required attributes
    class Dummy:
        file_path = "dummy.pdf"
        client = MagicMock()  # dummy client
        uploaded_file = MagicMock()

    ai_summary = AISummary(Dummy())
    
    # Patch the generate_content method in AIFeatures to return an empty string
    with patch.object(AIFeatures, "generate_content", MagicMock(return_value="Content generated.")):
        result = ai_summary.generate_content()
        assert result == "Content generated."

def test_create_AISummary_instance(ai_features):
    ai_summary = AISummary(ai_features)

    assert ai_summary.file_path == ai_features.file_path
    assert ai_summary.client == ai_features.client
    assert ai_summary.prompt is not None
    assert ai_summary.uploaded_file == ai_features.uploaded_file
    assert hasattr(ai_summary, 'sections')
    assert isinstance(ai_summary.sections, dict)

def test_AISummary_parse_sections(ai_features):
    ai_summary = AISummary(ai_features)
    test_content = "## Introduction\nThis is an introduction.\n\n## Main Content\nThis is the main content.\n\n## Conclusion\nThis is a conclusion."
    
    sections = ai_summary.parse_sections(test_content)
    
    assert len(sections) == 3
    assert sections["1"]["title"] == "Introduction"
    assert sections["1"]["content"] == "This is an introduction."
    assert sections["2"]["title"] == "Main Content"
    assert sections["3"]["title"] == "Conclusion"

def test_AISummary_parse_sections_no_sections(ai_features):
    ai_summary = AISummary(ai_features)
    test_content = "This is a single section without headers."
    
    sections = ai_summary.parse_sections(test_content)
    
    assert len(sections) == 1
    assert sections["1"]["title"] == "Summary"
    assert sections["1"]["content"] == test_content.strip()

def test_AISummary_format_for_display(ai_features):
    ai_summary = AISummary(ai_features)
    test_content = "## Introduction\nThis is an introduction.\n\n## Conclusion\nThis is a conclusion."
    
    formatted = ai_summary.format_for_display(test_content)
    
    assert "## Introduction" in formatted
    assert "## Conclusion" in formatted
    assert "This is an introduction." in formatted
    assert "This is a conclusion." in formatted
    
def test_aisummary_empty_content(ai_features):
    # Test empty content handling in AISummary
    with patch.object(AISummary, '__init__', return_value=None):
        ai_summary = AISummary(None)
        ai_summary.file_path = ai_features.file_path
        ai_summary.client = ai_features.client
        ai_summary.uploaded_file = ai_features.uploaded_file
        ai_summary.sections = {}
        
        # Mock the parent generate_content to return empty string
        with patch.object(AIFeatures, 'generate_content', return_value=""):
            result = ai_summary.generate_content()
            assert result == "No summary content was generated"

# Test for test_pdf_file fixture
@pytest.mark.parametrize("test_pdf_file", [True], indirect=True)
def test_pdf_file_exists(test_pdf_file):
    assert os.path.exists(test_pdf_file)

@pytest.mark.parametrize("test_pdf_file", [False], indirect=True)
def test_pdf_file_not_exists(test_pdf_file):
    assert not os.path.exists(test_pdf_file)

# Test for test_txt_file fixture
@pytest.mark.parametrize("test_txt_file", [True], indirect=True)
def test_txt_file_exists(test_txt_file):
    assert os.path.exists(test_txt_file) 

@pytest.mark.parametrize("test_txt_file", [False], indirect=True)
def test_txt_file_not_exists(test_txt_file):
    assert not os.path.exists(test_txt_file)
