# -*- coding: utf-8 -*-
import pytest
import re
import os
import sys
import tempfile
from pathlib import Path # Import Path for checking types
from unittest.mock import MagicMock, patch
# Ensure the 'os' module used for file operations isn't mocked globally
import os as real_os # Alias standard os library

# Import necessary modules directly
try:
    from src.AIFeatures import AIFeatures
    from src.AIFlashcards import AIFlashcards
    from src.AISummary import AISummary
    from src.AIQuestions import AIQuestions
except ImportError:
    from .AIFeatures import AIFeatures
    from .AIFlashcards import AIFlashcards
    from .AISummary import AISummary
    from .AIQuestions import AIQuestions

# Use a dummy API key for testing
API_KEY = 'dummy_api_key'

# Create a temporary test file fixture (parameterized)
@pytest.fixture
def temp_file(request):
    params = getattr(request, 'param', {})
    create = params.get('create', True)
    suffix = params.get('suffix', '.txt')
    content = params.get('content', b'Test content')

    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_path = f.name
    f.close() # Close handle immediately

    if create:
        with open(temp_path, 'wb') as f_write:
              f_write.write(content)
        # print(f"[Fixture Setup {os.getpid()}] Created: {temp_path}") # Debug
    else:
        try:
            # print(f"[Fixture Setup {os.getpid()}] Attempting unlink: {temp_path}") # Debug
            real_os.unlink(temp_path) # Use aliased os.unlink
            # print(f"[Fixture Setup {os.getpid()}] Unlink success? Exists: {real_os.path.exists(temp_path)}") # Debug Check
        except FileNotFoundError:
            # print(f"[Fixture Setup {os.getpid()}] File already gone: {temp_path}") # Debug
            pass # Ignore if already deleted somehow

    yield temp_path # Yield the path string

    # Cleanup
    # print(f"[Fixture Teardown {os.getpid()}] Cleaning up: {temp_path}") # Debug
    if real_os.path.exists(temp_path):
        try:
            real_os.unlink(temp_path)
            # print(f"[Fixture Teardown {os.getpid()}] Cleanup unlink success.") # Debug
        except FileNotFoundError:
             # print(f"[Fixture Teardown {os.getpid()}] Cleanup file already gone.") # Debug
             pass
        except PermissionError:
             print(f"Warning: Could not delete {temp_path} during cleanup due to PermissionError")
    # else:
        # print(f"[Fixture Teardown {os.getpid()}] Cleanup unnecessary, file not found.") # Debug


# Fixture to mock the genai.Client structure expected by AIFeatures
@pytest.fixture
def ai_features(request):
    default_file_path = "dummy_fixture.pdf"

    # --- Mocks for the structure AIFeatures EXPECTS ---
    mock_genai_client_instance = MagicMock(name='mock_genai_client_instance')
    mock_files_api = MagicMock(name='mock_files_api')
    mock_models_api = MagicMock(name='mock_models_api')

    # Setup File API Mock
    mock_uploaded_file_obj = MagicMock(name='mock_uploaded_file_obj')
    mock_uploaded_file_obj.name = 'mock_uploaded_file_id' # Set string name
    mock_listed_file_obj_1 = MagicMock(name='mock_listed_file_obj_1')
    mock_listed_file_obj_1.name = 'mock_listed_file_id_1' # Set string name
    mock_files_api.upload.return_value = mock_uploaded_file_obj
    mock_files_api.list.return_value = [mock_listed_file_obj_1]
    mock_files_api.delete.return_value = None

    # Setup Model API Mock
    mock_response = MagicMock(name='mock_response')
    mock_response.text = "Generated content for testing"
    mock_part = MagicMock(text=mock_response.text)
    mock_content = MagicMock(parts=[mock_part])
    mock_candidate = MagicMock(content=mock_content, finish_reason="STOP")
    mock_response.candidates = [mock_candidate]
    mock_response.prompt_feedback = MagicMock(block_reason=None)
    mock_models_api.generate_content.return_value = mock_response

    mock_genai_client_instance.files = mock_files_api
    mock_genai_client_instance.models = mock_models_api

    patch_target_client = 'src.AIFeatures.genai.Client'

    try:
        with patch(patch_target_client, return_value=mock_genai_client_instance) as mock_client_class:
            file_path_for_init = default_file_path
            file_param = getattr(request, 'param', None)
            if file_param and isinstance(file_param, dict) and 'file_fixture_name' in file_param:
                 file_fixture_name = file_param['file_fixture_name']
                 try:
                     # Use request.getfixturevalue to get the actual yielded value (the path)
                     file_path_for_init = request.getfixturevalue(file_fixture_name)
                     create_flag = file_param.get('create', True)
                     # Add a check here to ensure the file exists if it should have been created
                     if create_flag and not real_os.path.exists(file_path_for_init):
                          pytest.fail(f"ai_features setup: Fixture '{file_fixture_name}' with create=True did not result in existing file: {file_path_for_init}")
                     # And check it doesn't exist if it shouldn't have been created
                     elif not create_flag and real_os.path.exists(file_path_for_init):
                          pytest.fail(f"ai_features setup: Fixture '{file_fixture_name}' with create=False resulted in existing file: {file_path_for_init}")

                 except Exception as e:
                     pytest.fail(f"Could not get fixture value '{file_fixture_name}' for ai_features: {e}", pytrace=True)

            # Instantiate AIFeatures. Its __init__ will call the patched genai.Client.
            ai_features_instance = AIFeatures(API_KEY, file_path_for_init)

            mock_client_class.assert_called_once_with(api_key=API_KEY)
            expected_path_obj = Path(file_path_for_init)
            # Check if upload mock was called - it should be if file_path_for_init is valid
            if file_path_for_init.endswith(('.pdf', '.txt')):
                mock_files_api.upload.assert_called_once_with(file=expected_path_obj)
                assert ai_features_instance.uploaded_file == mock_uploaded_file_obj
            else:
                # If init path was invalid, upload shouldn't be called, instance attr should be None
                mock_files_api.upload.assert_not_called()
                assert ai_features_instance.uploaded_file is None # Assuming init doesn't handle the error gracefully


            ai_features_instance.client = mock_genai_client_instance
            ai_features_instance._mock_client_instance = mock_genai_client_instance
            ai_features_instance._mock_files_api = mock_files_api
            ai_features_instance._mock_models_api = mock_models_api

            yield ai_features_instance

    except (ModuleNotFoundError, AttributeError) as e:
        pytest.fail(f"Patching failed for '{patch_target_client}': {e}. Check target and AIFeatures.py imports.", pytrace=True)


### Test cases for AIFeatures.py ###

@pytest.mark.parametrize("temp_file", [{'suffix': '.pdf', 'create': True}], indirect=True)
@pytest.mark.parametrize("ai_features", [{'file_fixture_name': 'temp_file', 'create': True, 'suffix': '.pdf'}], indirect=True)
def test_AIFeatures_init_success(ai_features, temp_file):
    # Combined test for init logic using the fixture
    assert ai_features.api_key == API_KEY
    assert isinstance(ai_features.client, MagicMock)
    assert ai_features.client == ai_features._mock_client_instance
    assert isinstance(ai_features.file_path, Path)
    assert str(ai_features.file_path) == temp_file
    assert ai_features.uploaded_file is not None
    assert ai_features.uploaded_file.name == 'mock_uploaded_file_id'
    ai_features._mock_files_api.upload.assert_called_once_with(file=Path(temp_file))


@pytest.mark.parametrize("temp_file", [{'suffix': '.py', 'create': True}], indirect=True)
def test_AIFeatures_init_invalid_extension(temp_file):
     with patch('src.AIFeatures.genai.Client'):
        with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
              AIFeatures(API_KEY, temp_file)


# FIX: Test set_file logic without calling the temp_file fixture value
@patch.object(AIFeatures, '__init__', lambda self, api_key, file_path: None) # Dummy init
def test_set_file_logic_valid_pdf():
     ai_test = AIFeatures(None, None)
     # Create temp file manually for this test
     with tempfile.NamedTemporaryFile(suffix='.pdf', delete=True) as f:
         file_path_str = f.name
         ai_test.set_file(file_path_str)
         assert isinstance(ai_test.file_path, Path)
         assert str(ai_test.file_path) == file_path_str


@patch.object(AIFeatures, '__init__', lambda self, api_key, file_path: None) # Dummy init
def test_set_file_logic_invalid_py():
     ai_test = AIFeatures(None, None)
     # Create temp file manually
     with tempfile.NamedTemporaryFile(suffix='.py', delete=True) as f:
         file_path_str = f.name
         with pytest.raises(ValueError, match="Only PDF and TXT files are allowed."):
             ai_test.set_file(file_path_str)


@pytest.mark.parametrize("temp_file", [{'suffix': '.txt', 'create': True}], indirect=True)
@pytest.mark.parametrize("ai_features", [{'file_fixture_name': 'temp_file', 'create': True, 'suffix': '.txt'}], indirect=True)
def test_upload_file_called_again(ai_features, temp_file):
    ai_features._mock_files_api.upload.reset_mock()
    result = ai_features.upload_file()
    ai_features._mock_files_api.upload.assert_called_once_with(file=Path(temp_file))
    assert result.name == 'mock_uploaded_file_id'


@pytest.mark.parametrize("ai_features", [{}], indirect=True) # Use default fixture setup
def test_upload_file_no_filepath(ai_features):
     ai_features.file_path = None
     with pytest.raises(ValueError, match=re.escape("File path is not set. Call set_file() first.")):
         ai_features.upload_file()


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_upload_file_no_client(ai_features):
     ai_features.client = None
     with pytest.raises(ValueError, match=re.escape("Client is not set.")):
         ai_features.upload_file()


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_generate_content_success(ai_features):
    ai_features.prompt = "Custom test prompt"
    ai_features._mock_models_api.generate_content.reset_mock()
    result = ai_features.generate_content()
    expected_prompt_list = [ai_features.uploaded_file, "\n\n", ai_features.prompt]
    call_args, call_kwargs = ai_features._mock_models_api.generate_content.call_args_list[-1]
    assert call_kwargs.get('model') == "gemini-2.0-flash"
    assert call_kwargs.get('contents') == expected_prompt_list
    assert ai_features._mock_models_api.generate_content.call_count == 2
    assert result == "Generated content for testing"


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_generate_content_no_uploaded_file(ai_features):
     ai_features.uploaded_file = None
     with pytest.raises(ValueError, match=re.escape("File not uploaded. Call upload_file() first.")):
         ai_features.generate_content()


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_generate_content_no_client(ai_features):
     ai_features.client = None
     with pytest.raises(ValueError, match=re.escape("Client is not set.")):
         ai_features.generate_content()


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_delete_all_files_one_file(ai_features):
    listed_file_name = ai_features._mock_files_api.list.return_value[0].name
    ai_features._mock_files_api.list.reset_mock()
    ai_features._mock_files_api.delete.reset_mock()
    result = ai_features.delete_all_files()
    ai_features._mock_files_api.list.assert_called_once()
    ai_features._mock_files_api.delete.assert_called_once_with(name=listed_file_name)
    assert result == 1


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_delete_all_files_multiple_files(ai_features):
    # FIX: Set .name attribute to string values
    mock_file1 = MagicMock()
    mock_file1.name = 'del_file1' # String name
    mock_file2 = MagicMock()
    mock_file2.name = 'del_file2' # String name
    ai_features._mock_files_api.list.return_value = [mock_file1, mock_file2]

    ai_features._mock_files_api.list.reset_mock()
    ai_features._mock_files_api.delete.reset_mock()
    result = ai_features.delete_all_files()
    ai_features._mock_files_api.list.assert_called_once()
    assert ai_features._mock_files_api.delete.call_count == 2
    # Assertions should now pass with string names
    ai_features._mock_files_api.delete.assert_any_call(name='del_file1')
    ai_features._mock_files_api.delete.assert_any_call(name='del_file2')
    assert result == 2


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_delete_all_files_no_files(ai_features):
    ai_features._mock_files_api.list.return_value = []
    ai_features._mock_files_api.list.reset_mock()
    ai_features._mock_files_api.delete.reset_mock()
    result = ai_features.delete_all_files()
    ai_features._mock_files_api.list.assert_called_once()
    ai_features._mock_files_api.delete.assert_not_called()
    assert result == 0


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_delete_all_files_exception(ai_features):
    mock_file_error = MagicMock()
    mock_file_error.name = "file_that_errors" # String name
    ai_features._mock_files_api.list.return_value = [mock_file_error]
    ai_features._mock_files_api.delete.side_effect = Exception("Delete failed!")

    ai_features._mock_files_api.list.reset_mock()
    ai_features._mock_files_api.delete.reset_mock()
    result = ai_features.delete_all_files()
    ai_features._mock_files_api.list.assert_called_once()
    ai_features._mock_files_api.delete.assert_called_once_with(name=mock_file_error.name)
    assert result == 0
    ai_features._mock_files_api.delete.side_effect = None


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_delete_all_files_no_client(ai_features):
     ai_features.client = None
     with pytest.raises(ValueError, match=re.escape("Client is not set.")):
         ai_features.delete_all_files()


### Test cases for AIQuestions ###
@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_aiquestions_init(ai_features):
    num_q = 7
    ai_questions = AIQuestions(ai_features, num_q)
    assert ai_questions.file_path == ai_features.file_path
    assert ai_questions.client == ai_features.client
    assert ai_questions.uploaded_file == ai_features.uploaded_file
    assert ai_questions.num_questions == num_q
    assert str(num_q) in ai_questions.prompt


def test_aiquestions_parse_output():
    ai_questions_instance = AIQuestions(MagicMock(), 5)
    sample_output = """
    1. Capital of Testland?
    a.TestA
    b.TestB
    c.TestC
    d.TestD
    b.TestB

    2. 2+2?
    a.3
    b.4
    c.5
    d.6
    b.4
    """
    parsed = ai_questions_instance.parse_output(sample_output)
    assert len(parsed) == 2
    assert parsed[0]['question_number'] == 1
    assert parsed[0]['question'] == "Capital of Testland?"
    assert parsed[0]['options']['a'] == "TestA"
    assert parsed[0]['correct_answer'] == "b"
    assert parsed[1]['question_number'] == 2
    assert parsed[1]['correct_answer'] == "b"

@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_aiquestions_generate_content(ai_features):
    ai_questions = AIQuestions(ai_features, 3)
    ai_features._mock_models_api.generate_content.reset_mock()
    ai_features._mock_models_api.generate_content.return_value.text = "1. Q?\na.A\nb.B\nc.C\nd.D\na.A"
    result = ai_questions.generate_content()
    expected_prompt_list = [ai_questions.uploaded_file, "\n\n", ai_questions.prompt]
    call_args, call_kwargs = ai_features._mock_models_api.generate_content.call_args_list[-1]
    assert call_kwargs.get('contents') == expected_prompt_list
    # FIX: Check call count reflects AIFeatures implementation
    assert ai_features._mock_models_api.generate_content.call_count == 2
    assert result == "1. Q?\na.A\nb.B\nc.C\nd.D\na.A"


### Test cases for AIFlashcards ###
@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_aiflashcards_init(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    assert ai_flashcards.file_path == ai_features.file_path
    assert ai_flashcards.client == ai_features.client
    assert ai_flashcards.uploaded_file == ai_features.uploaded_file
    assert "key words" in ai_flashcards.prompt

@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_aiflashcards_generate_content_valid(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    expected_output = "1: Term; Definition."
    ai_features._mock_models_api.generate_content.return_value.text = expected_output
    ai_features._mock_models_api.generate_content.reset_mock()
    result = ai_flashcards.generate_content()
    assert result == expected_output
    expected_prompt_list = [ai_flashcards.uploaded_file, "\n\n", ai_flashcards.prompt]
    call_args, call_kwargs = ai_features._mock_models_api.generate_content.call_args_list[-1]
    assert call_kwargs.get('contents') == expected_prompt_list
    # FIX: Check call count reflects AIFeatures implementation
    assert ai_features._mock_models_api.generate_content.call_count == 2


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_aiflashcards_generate_content_empty(ai_features):
    ai_flashcards = AIFlashcards(ai_features)
    ai_features._mock_models_api.generate_content.return_value.text = ""
    ai_features._mock_models_api.generate_content.reset_mock()
    result = ai_flashcards.generate_content()
    assert result == "No content was generated"
    # FIX: Check call count reflects AIFeatures implementation
    assert ai_features._mock_models_api.generate_content.call_count == 2


def test_aiflashcards_create_dict():
    ai_flashcards_instance = AIFlashcards(MagicMock())
    sample_content = """
    1: Word1; Def1.
    2: Another Word ; Some definition.
    3: Third:Item; With Colon ; Definition part.
    """.strip()
    flashcards_dict = ai_flashcards_instance.create_dict(sample_content)
    expected = {
        "1": {"word": "Word1", "definition": "Def1."},
        "2": {"word": "Another Word", "definition": "Some definition."},
         "3": {"word": "Third:Item", "definition": "With Colon ; Definition part."}
    }
    assert flashcards_dict == expected

def test_aiflashcards_get_word_valid():
    ai_flashcards_instance = AIFlashcards(MagicMock())
    data = {"word": " Test ", "definition": "Def"}
    assert ai_flashcards_instance.get_word(data) == "Test"

def test_aiflashcards_get_word_missing():
    ai_flashcards_instance = AIFlashcards(MagicMock())
    data = {"definition": "Def"}
    assert ai_flashcards_instance.get_word(data) == ""

def test_aiflashcards_get_def_valid():
    ai_flashcards_instance = AIFlashcards(MagicMock())
    data = {"word": "Test", "definition": " Def "}
    assert ai_flashcards_instance.get_def(data) == "Def"

def test_aiflashcards_get_def_missing():
    ai_flashcards_instance = AIFlashcards(MagicMock())
    data = {"word": "Test"}
    assert ai_flashcards_instance.get_def(data) == ""


### Test cases for AISummary ###
@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_aisummary_init(ai_features):
    ai_summary = AISummary(ai_features)
    assert ai_summary.file_path == ai_features.file_path
    assert ai_summary.client == ai_features.client
    assert ai_summary.uploaded_file == ai_features.uploaded_file
    assert isinstance(ai_summary.sections, dict)
    assert "detailed summary" in ai_summary.prompt

@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_aisummary_generate_content_valid(ai_features):
    ai_summary = AISummary(ai_features)
    expected_output = "## Section 1\nContent 1."
    ai_features._mock_models_api.generate_content.return_value.text = expected_output
    ai_features._mock_models_api.generate_content.reset_mock()
    result = ai_summary.generate_content()
    assert result == expected_output
    expected_prompt_list = [ai_summary.uploaded_file, "\n\n", ai_summary.prompt]
    call_args, call_kwargs = ai_features._mock_models_api.generate_content.call_args_list[-1]
    assert call_kwargs.get('contents') == expected_prompt_list
    # FIX: Check call count reflects AIFeatures implementation
    assert ai_features._mock_models_api.generate_content.call_count == 2


@pytest.mark.parametrize("ai_features", [{}], indirect=True)
def test_aisummary_generate_content_empty(ai_features):
    ai_summary = AISummary(ai_features)
    ai_features._mock_models_api.generate_content.return_value.text = "  "
    ai_features._mock_models_api.generate_content.reset_mock()
    result = ai_summary.generate_content()
    assert result == "No summary content was generated"
    # FIX: Check call count reflects AIFeatures implementation
    assert ai_features._mock_models_api.generate_content.call_count == 2


def test_AISummary_parse_sections():
    ai_summary_instance = AISummary(MagicMock())
    test_content = "## Intro\nIntro content.\n\n## Body\nBody content."
    sections = ai_summary_instance.parse_sections(test_content)
    expected = {
        "1": {"title": "Intro", "content": "Intro content."},
        "2": {"title": "Body", "content": "Body content."}
    }
    assert sections["1"]["title"] == expected["1"]["title"]
    assert sections["1"]["content"] == expected["1"]["content"]
    assert sections["2"]["title"] == expected["2"]["title"]
    assert sections["2"]["content"] == expected["2"]["content"]

def test_AISummary_parse_sections_no_sections():
    ai_summary_instance = AISummary(MagicMock())
    test_content = "Just plain text."
    sections = ai_summary_instance.parse_sections(test_content)
    expected = {
        "1": {"title": "Summary", "content": "Just plain text."}
    }
    assert sections["1"]["title"] == expected["1"]["title"]
    assert sections["1"]["content"] == expected["1"]["content"]

def test_AISummary_format_for_display():
    ai_summary_instance = AISummary(MagicMock())
    test_content = "## Title\nContent."
    formatted = ai_summary_instance.format_for_display(test_content)
    expected_formatted = "## Title\n\nContent."
    assert formatted == expected_formatted


### Test Fixture Correctness ###

@pytest.mark.parametrize("temp_file", [{'suffix': '.pdf', 'create': True}], indirect=True)
def test_fixture_pdf_file_exists(temp_file):
    import os.path # Import directly in test scope
    assert os.path.exists(temp_file)
    assert temp_file.endswith('.pdf')

@pytest.mark.parametrize("temp_file", [{'suffix': '.pdf', 'create': False}], indirect=True)
def test_fixture_pdf_file_not_exists(temp_file):
    import os.path # Import directly in test scope
    # print(f"[Test {os.getpid()}] Checking exists: {temp_file}") # Debug
    # print(f"[Test {os.getpid()}] Result: {os.path.exists(temp_file)}") # Debug
    assert not os.path.exists(temp_file)
    assert temp_file.endswith('.pdf')

@pytest.mark.parametrize("temp_file", [{'suffix': '.txt', 'create': True}], indirect=True)
def test_fixture_txt_file_exists(temp_file):
    import os.path # Import directly in test scope
    assert os.path.exists(temp_file)
    assert temp_file.endswith('.txt')

@pytest.mark.parametrize("temp_file", [{'suffix': '.txt', 'create': False}], indirect=True)
def test_fixture_txt_file_not_exists(temp_file):
    import os.path # Import directly in test scope
    # print(f"[Test {os.getpid()}] Checking exists: {temp_file}") # Debug
    # print(f"[Test {os.getpid()}] Result: {os.path.exists(temp_file)}") # Debug
    assert not os.path.exists(temp_file)
    assert temp_file.endswith('.txt')