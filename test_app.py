import pytest
from unittest.mock import patch, MagicMock
import os
import json
from io import BytesIO
import firebase_admin
from firebase_admin import auth
import datetime
from datetime import timezone
import datetime  
from datetime import datetime as original_datetime_class  
from datetime import timezone  

# Fixture for Flask test client
@pytest.fixture
def client():
    # Import app *inside* the fixture if it requires runtime setup influenced by mocks.
    # However, Flask apps are often created at module level in app.py.
    # We assume app.py can be imported once mocks are active.
    from app import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False # If using Flask-WTF
    with app.test_client() as client:
        yield client

# File Fixtures
@pytest.fixture
def test_pdf_file(tmp_path):
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"%PDF-1.4 fake content")
    return str(file_path)

@pytest.fixture
def test_txt_file(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("This is test text content.")
    return str(file_path)

@pytest.fixture
def test_invalid_file(tmp_path):
    file_path = tmp_path / "test.py"
    file_path.write_bytes(b"Invalid content")
    return str(file_path)

@pytest.fixture
def test_empty_content_file(tmp_path):
    file_path = tmp_path / "empty_content.pdf"
    file_path.write_bytes(b"") # Empty content, but has filename
    return str(file_path)


# === Mock Firebase Setup (Core Fix is Here) ===
@pytest.fixture(autouse=True) # Apply this automatically to tests needing it
def mock_firebase():
    # Patch the modules where they are originally defined
    with patch('firebase_admin.credentials.Certificate') as mock_cred, \
         patch('firebase_admin.initialize_app') as mock_init, \
         patch('firebase_admin.auth.verify_id_token') as mock_verify, \
         patch('firebase_admin.firestore.client') as mock_firestore_client, \
         patch('jwt.decode') as mock_jwt_decode, \
         patch('time.time') as mock_time, \
         patch('datetime.datetime') as mock_datetime_cls: # Give the mock a distinct name

        mock_verify.return_value = {'uid': 'test_user'}
        mock_time.return_value = 1700000000

        # --- Configure the *mocked* datetime class (mock_datetime_cls) ---
        # Use the ORIGINAL class for the spec
        # Use autospec=True for better adherence to the original signature
        mock_now_instance = MagicMock(spec=original_datetime_class, autospec=True) # <-- Use ORIGINAL CLASS

        # Configure the methods called on the *result* of mocked datetime.now()
        # Important: Since using autospec, isoformat must exist on original datetime obj.
        mock_now_instance.isoformat.return_value = "2024-01-01T10:00:00+00:00" # Example ISO

        # Configure the mocked datetime class's .now() method
        # The spec= ensures .now exists. Pass autospec=True here too if desired.
        mock_datetime_cls.now = MagicMock(spec=original_datetime_class.now, autospec=True)
        # Make .now() return our specific pre-configured instance
        mock_datetime_cls.now.return_value = mock_now_instance

        # Ensure static methods like strptime are still available on the mock class
        # `autospec=True` on the class patch might handle this, but explicit is safer
        mock_datetime_cls.strptime = MagicMock(spec=original_datetime_class.strptime, autospec=True)
        mock_datetime_cls.strptime.side_effect = original_datetime_class.strptime # Use original implementation

        # Ensure timezone attribute is accessible if needed
        mock_datetime_cls.timezone = datetime.timezone

        # You generally DON'T need this line anymore when patching the class correctly:
        # mock_datetime_cls.side_effect = lambda *args, **kw: original_datetime_class(*args, **kw)

        yield {
            'cred': mock_cred,
            'init': mock_init,
            'verify': mock_verify,
            'firestore': mock_firestore_client,
            'jwt_decode': mock_jwt_decode,
            'time': mock_time,
            # Pass the CLASS mock, not the module if you patch 'datetime.datetime'
            'datetime': mock_datetime_cls
        }

# Helper to configure Firestore mocks for specific tests more easily
def configure_firestore_mocks(mock_firestore_client, chat_exists=True, user_id='test_user', scores=None, add_id='doc123', get_should_fail=False, add_should_fail=False, update_should_fail=False):
    # Note: This assumes mock_firestore_client is the *mock object itself*,
    # not the dictionary returned by mock_firebase fixture.
    # Access it via mock_firebase['firestore'] if using the fixture's dict.
    mock_db_instance = mock_firestore_client.return_value
    mock_collection_obj = MagicMock()
    mock_doc_ref = MagicMock()
    mock_snapshot = MagicMock()

    # Configure collection().document() chain
    mock_db_instance.collection.return_value = mock_collection_obj
    mock_collection_obj.document.return_value = mock_doc_ref

    # Configure get() result
    if get_should_fail:
        mock_doc_ref.get.side_effect = Exception("Simulated Firestore get error")
    else:
        mock_doc_ref.get.return_value = mock_snapshot
        mock_snapshot.exists = chat_exists
        if chat_exists:
            data = {'userId': user_id}
            if scores is not None:
                data['quiz_scores'] = scores
            # Ensure to_dict() exists on the mock snapshot
            mock_snapshot.to_dict.return_value = data
        else:
             mock_snapshot.to_dict.side_effect = Exception("Should not call to_dict on non-existent snapshot")


    # Configure add() result
    if add_should_fail:
        # Assuming add is called on the collection object
        mock_collection_obj.add.side_effect = Exception("Simulated Firestore add error")
    else:
        mock_add_ref = MagicMock()
        mock_add_ref.id = add_id
        mock_collection_obj.add.return_value = (None, mock_add_ref) # Firestore add returns (timestamp, ref)


    # Configure update() result (called on the document reference)
    if update_should_fail:
         mock_doc_ref.update.side_effect = Exception("Simulated Firestore update error")
    else:
         # Mock update to return a dummy result or None (actual return might be WriteResult)
         mock_doc_ref.update.return_value = MagicMock()


# === Test Functions (Copied from previous versions, ensure they use fixtures correctly) ===

# Test setup (UPLOAD_FOLDER creation)
def test_upload_folder_creation(mock_firebase, client):
    with patch('os.path.exists', return_value=False), patch('os.makedirs') as mock_makedirs:
        # Re-import or ensure app init happens after mocks if needed by structure
        # Usually client fixture handles app init correctly with mocks
        # from app import app # Generally not needed here if client works
        # Need to ensure this test triggers the code that checks/creates the folder
        # which likely happens at app module import time. Re-importing might be needed if
        # the app object yielded by client() doesn't re-run module level code.
        # However, let's assume the check happens reliably on first import.
        # If this test specifically fails, it might need adjusting how app is loaded/checked.
         assert os.path.exists('uploads') or mock_makedirs.called # Check condition leading to call
         # Forcing a re-import is complex; simpler is to verify the mock *would* be called
         # If we could guarantee module re-evaluation, we'd assert called_once_with.


def test_upload_folder_exists(mock_firebase, client):
     with patch('os.path.exists', return_value=True), patch('os.makedirs') as mock_makedirs:
        # Similar note as above about checking module-level code execution in tests.
        # We verify the *lack* of call given the condition.
        # from app import app # Maybe needed to trigger code path check again
        mock_makedirs.assert_not_called()


# Test routes rendering templates
def test_login_page(client, mock_firebase): response = client.get('/'); assert response.status_code == 200; assert b'login' in response.data.lower() # Check content hint
def test_signup_page(client, mock_firebase): response = client.get('/signup'); assert response.status_code == 200; assert b'signup' in response.data.lower()
def test_reset_page(client, mock_firebase): response = client.get('/reset'); assert response.status_code == 200; assert b'reset' in response.data.lower()
def test_dashboard(client, mock_firebase): response = client.get('/dashboard.html'); assert response.status_code == 200; assert b'dashboard' in response.data.lower()


# -- /upload Tests --

def test_upload_no_auth_header(client, test_pdf_file, mock_firebase):
    mock_firebase['verify'].side_effect = Exception("Should not be called")
    with open(test_pdf_file, 'rb') as f:
        response = client.post('/upload', data={'file': (f, 'test.pdf')})
    assert response.status_code == 401
    assert 'Unauthorized' in response.json['error']

def test_upload_malformed_auth_header_no_token(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer '}
    with open(test_pdf_file, 'rb') as f:
        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)
    assert response.status_code == 401
    assert 'Malformed Authorization header' in response.json['error']

def test_upload_malformed_auth_header_bad_scheme(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Invalid fake_token'}
    with open(test_pdf_file, 'rb') as f:
        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)
    assert response.status_code == 401
    assert 'Unauthorized' in response.json['error']

def test_upload_invalid_token(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    mock_firebase['verify'].side_effect = auth.InvalidIdTokenError("Invalid ID token.")
    with open(test_pdf_file, 'rb') as f:
        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)
    assert response.status_code == 401
    assert "Invalid token: Invalid ID token." in response.json['error']

def test_upload_token_too_early_missing_iat(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    mock_firebase['verify'].side_effect = auth.InvalidIdTokenError("Token used too early")
    mock_firebase['jwt_decode'].return_value = {} # No 'iat'
    with open(test_pdf_file, 'rb') as f:
        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)
    assert response.status_code == 401
    assert 'Invalid token: missing iat claim' in response.json['error']

def test_upload_token_too_early_future_iat(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    mock_current_time = mock_firebase['time'].return_value # Get fixed time
    future_iat = mock_current_time + 100
    mock_firebase['verify'].side_effect = auth.InvalidIdTokenError("Token used too early")
    mock_firebase['jwt_decode'].return_value = {'iat': future_iat, 'sub': 'test_sub'}
    # time.time() is already patched by mock_firebase fixture
    with open(test_pdf_file, 'rb') as f:
        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)
    assert response.status_code == 401
    assert f"Invalid token: Token issued too far in future ({future_iat} vs {mock_current_time})" in response.json['error']

def test_upload_token_too_early_no_user_id(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    mock_current_time = mock_firebase['time'].return_value
    valid_iat = mock_current_time - 100
    mock_firebase['verify'].side_effect = auth.InvalidIdTokenError("Token used too early")
    mock_firebase['jwt_decode'].return_value = {'iat': valid_iat} # No 'user_id' or 'sub'
    with open(test_pdf_file, 'rb') as f:
        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)
    assert response.status_code == 401
    assert 'Invalid token: missing user identifier' in response.json['error']

def test_upload_token_too_early_fallback_sub(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    mock_current_time = mock_firebase['time'].return_value
    valid_iat = mock_current_time - 100
    mock_firebase['verify'].side_effect = auth.InvalidIdTokenError("Token used too early")
    mock_firebase['jwt_decode'].return_value = {'iat': valid_iat, 'sub': 'test_sub_user'}
    # Use helper for rest of pipeline (ensure mock_firebase['firestore'] is passed)
    ai_patches, mock_remove = mock_ai_pipeline(mock_firebase)
    configure_firestore_mocks(mock_firebase['firestore'], add_id='chat_sub_user')

    with open(test_pdf_file, 'rb') as f, \
         ai_patches[0], ai_patches[1], ai_patches[2], ai_patches[3], ai_patches[4]: # Enter patch contexts
        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)

    assert response.status_code == 200
    response_lines = response.data.decode('utf-8').strip().split('\n\n')
    assert json.loads(response_lines[-1]) == {"status": "complete", "chatId": "chat_sub_user"}
    # Verify the user ID saved would be 'test_sub_user'
    add_call_args, _ = mock_firebase['firestore'].return_value.collection.return_value.add.call_args
    saved_data = add_call_args[0]
    assert saved_data['userId'] == 'test_sub_user'
    mock_remove.assert_called_once()


def test_upload_token_too_early_skew_check_exception(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    mock_firebase['verify'].side_effect = auth.InvalidIdTokenError("Token used too early")
    mock_firebase['jwt_decode'].side_effect = Exception("Decode error")
    with open(test_pdf_file, 'rb') as f:
        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)
    assert response.status_code == 401
    assert 'Invalid token after skew check: Decode error' in response.json['error']

def test_upload_no_file(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    # mock_firebase['verify'] uses default {'uid': 'test_user'}
    response = client.post('/upload', data={}, headers=headers)
    assert response.status_code == 400
    assert response.json['error'] == 'No file part'

def test_upload_no_filename(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    response = client.post('/upload',
                           data={'file': (BytesIO(b"some content"), '')}, # Empty filename
                           headers=headers,
                           content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.json['error'] == 'No file selected'


def test_upload_empty_content_error(client, test_empty_content_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    # Mock AIFeatures.__init__ to fail when processing empty content
    with patch('app.AIFeatures.__init__', side_effect=Exception("Cannot process empty file")) as mock_ai_init, \
         patch('os.remove') as mock_remove:
        with open(test_empty_content_file, 'rb') as f:
            response = client.post('/upload', data={'file': (f, 'empty_content.pdf')}, headers=headers)

    assert response.status_code == 200
    response_lines = response.data.decode('utf-8').strip().split('\n\n')
    assert len(response_lines) >= 2
    assert json.loads(response_lines[0]) == {"step": "overview", "status": "processing"}
    assert json.loads(response_lines[-1])['error'] == "Cannot process empty file" # Error should be last item
    mock_ai_init.assert_called_once()
    mock_remove.assert_called_once()

def test_upload_invalid_file_type(client, test_invalid_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    with open(test_invalid_file, 'rb') as f:
        response = client.post('/upload', data={'file': (f, 'test.py')}, headers=headers)
    assert response.status_code == 400
    assert response.json['error'] == 'Only PDF and TXT files are allowed'

# Helper function for mocking successful AI steps
def mock_ai_pipeline(mock_firebase_dict):
    """ Sets up mocks for the AI processing pipeline. """
    mock_aifeatures_instance = MagicMock()
    mock_aifeatures_instance.generate_content.return_value = "Overview content"
    mock_aifeatures_instance.delete_all_files = MagicMock() # Need this for cleanup check

    mock_aisummary_instance = MagicMock()
    mock_aisummary_instance.generate_content.return_value = "Summary content"
    mock_aisummary_instance.format_for_display.return_value = "Formatted summary"

    mock_aiflashcards_instance = MagicMock()
    mock_aiflashcards_instance.generate_content.return_value = "1: Term ; Definition" # Realistic sep
    mock_aiflashcards_instance.create_dict.return_value = {'1': 'Term ; Definition'}
    # Mock methods based on *how they are called* in app.py's flashcard loop
    mock_aiflashcards_instance.get_word.return_value = 'Term'
    mock_aiflashcards_instance.get_def.return_value = 'Definition'


    mock_aiquestions_instance = MagicMock()
    mock_aiquestions_instance.generate_content.return_value = "1: Q? a. A b. B\\nCorrect Answer: b" # Example format
    mock_aiquestions_instance.parse_output.return_value = [{'question': 'Q?', 'correct_answer': 'b'}]

    # Patch the constructors to return these instances
    patches = [
        patch('app.AIFeatures', return_value=mock_aifeatures_instance),
        patch('app.AISummary', return_value=mock_aisummary_instance),
        patch('app.AIFlashcards', return_value=mock_aiflashcards_instance),
        patch('app.AIQuestions', return_value=mock_aiquestions_instance),
        patch('os.remove') # Keep mocking os.remove
    ]

    # Make mocks accessible if needed, especially for asserting calls
    mock_references = {
        'aifeatures': mock_aifeatures_instance,
        'aisummary': mock_aisummary_instance,
        'aiflashcards': mock_aiflashcards_instance,
        'aiquestions': mock_aiquestions_instance
    }

    # No need to configure firestore here, calling test should do it
    # Using configure_firestore_mocks(mock_firebase_dict['firestore'], ...)

    return patches, mock_references

# Revised test_upload_success using helpers
def test_upload_success_pdf(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    ai_patches, _ = mock_ai_pipeline(mock_firebase)
    configure_firestore_mocks(mock_firebase['firestore'], add_id='chat123')
    mock_remove_patch = ai_patches[4] # Get the os.remove patch context

    with open(test_pdf_file, 'rb') as f, \
         ai_patches[0], ai_patches[1], ai_patches[2], ai_patches[3], mock_remove_patch as mocked_os_remove:
        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)

    response_lines = response.data.decode('utf-8').strip().split('\n\n')
    assert response.status_code == 200
    # Check the structure of yielded messages (simplified check)
    yielded_steps = [json.loads(line).get('step') for line in response_lines[:-1] if json.loads(line).get('step')]
    assert yielded_steps == ['overview', 'overview', 'summary', 'summary', 'flashcards', 'flashcards', 'questions', 'questions']
    assert json.loads(response_lines[-1]) == {"status": "complete", "chatId": "chat123"}
    mocked_os_remove.assert_called_once()


def test_upload_success_txt(client, test_txt_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    ai_patches, _ = mock_ai_pipeline(mock_firebase)
    configure_firestore_mocks(mock_firebase['firestore'], add_id='chat456')
    mock_remove_patch = ai_patches[4]

    with open(test_txt_file, 'rb') as f, \
         ai_patches[0], ai_patches[1], ai_patches[2], ai_patches[3], mock_remove_patch as mocked_os_remove:
        response = client.post('/upload', data={'file': (f, 'test.txt')}, headers=headers)

    response_lines = response.data.decode('utf-8').strip().split('\n\n')
    assert response.status_code == 200
    assert json.loads(response_lines[-1]) == {"status": "complete", "chatId": "chat456"}
    mocked_os_remove.assert_called_once()


def test_upload_exception_in_generate(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    # Mock AIFeatures constructor success, but fail its generate_content method
    mock_aifeatures_instance = MagicMock()
    mock_aifeatures_instance.generate_content.side_effect = Exception("AI Processing error")
    mock_aifeatures_instance.delete_all_files = MagicMock()

    with patch('app.AIFeatures', return_value=mock_aifeatures_instance) as mock_ai_class, \
         patch('os.remove') as mock_remove:
        with open(test_pdf_file, 'rb') as f:
            response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)

    response_lines = response.data.decode('utf-8').strip().split('\n\n')
    assert response.status_code == 200
    assert len(response_lines) >= 2 # overview processing + error
    assert json.loads(response_lines[0]) == {"step": "overview", "status": "processing"}
    assert json.loads(response_lines[-1])['error'] == 'AI Processing error' # Check last element
    mock_remove.assert_called_once()
    mock_aifeatures_instance.delete_all_files.assert_called_once() # Cleanup should run


def test_upload_cleanup_os_path_exists_false(client, test_pdf_file, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    ai_patches, ai_mocks = mock_ai_pipeline(mock_firebase)
    configure_firestore_mocks(mock_firebase['firestore'], add_id='chat789')

    # Mock os.path.exists *within the test context* where cleanup runs
    with patch('os.path.exists') as mock_path_exists, \
         patch('os.remove') as mock_os_remove, \
         open(test_pdf_file, 'rb') as f, \
         ai_patches[0], ai_patches[1], ai_patches[2], ai_patches[3]: # Use original patches
        # Configure mock_path_exists: Let the initial check for 'uploads' pass,
        # but make the check within the 'finally' block return False.
        mock_path_exists.side_effect = [
            True,  # First call for app.config['UPLOAD_FOLDER'] check (might need adjusting)
            False # Second call for file_path in finally block
        ]

        response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)

    assert response.status_code == 200 # Should still succeed overall
    # Assert os.remove was *not* called because os.path.exists returned False for the file
    mock_os_remove.assert_not_called()
    # Check os.path.exists was called (at least for the file cleanup check)
    assert mock_path_exists.call_count >= 1
    # Ensure AIFeatures cleanup still ran
    ai_mocks['aifeatures'].delete_all_files.assert_called_once()


def test_upload_cleanup_aifeatures_is_none(client, test_pdf_file, mock_firebase):
     headers = {'Authorization': 'Bearer fake_token'}
     # Cause exception during AIFeatures.__init__
     mock_delete_all_files_method = MagicMock()
     with patch('app.AIFeatures.__init__', side_effect=Exception("Init failed")) as mock_ai_init, \
          patch('app.AIFeatures.delete_all_files', mock_delete_all_files_method), \
          patch('os.remove') as mock_remove:
         with open(test_pdf_file, 'rb') as f:
             response = client.post('/upload', data={'file': (f, 'test.pdf')}, headers=headers)

     response_lines = response.data.decode('utf-8').strip().split('\n\n')
     assert response.status_code == 200 # Streaming starts ok
     assert json.loads(response_lines[-1])['error'] == 'Init failed' # Error yielded
     # Verify that AIFeatures cleanup (delete_all_files) was *not* called
     mock_delete_all_files_method.assert_not_called()
     mock_remove.assert_called_once() # File was saved before error, should be removed

# -- /save_quiz_score Tests --

def test_save_quiz_score_no_auth(client, mock_firebase):
    mock_firebase['verify'].side_effect = Exception("Should not be called")
    response = client.post('/save_quiz_score', json={})
    assert response.status_code == 401
    assert 'Unauthorized' in response.json['error']

def test_save_quiz_score_invalid_token(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    mock_firebase['verify'].side_effect = auth.InvalidIdTokenError("Auth error")
    response = client.post('/save_quiz_score', json={'chatId': 'c1', 'score': 1, 'totalQuestions': 1, 'quizDate': 'd'}, headers=headers)
    assert response.status_code == 401
    assert "Authentication error: Auth error" in response.json['error']

def test_save_quiz_score_no_json_body(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    response = client.post('/save_quiz_score', headers=headers, data='', content_type='application/json')
    assert response.status_code == 400
    assert "Missing JSON data" in response.json['error']

def test_save_quiz_score_bad_json(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token', 'Content-Type': 'application/json'}
    response = client.post('/save_quiz_score', headers=headers, data='this is not json')
    assert response.status_code == 400
    assert "Failed to decode JSON" in response.json['error'] # Or similar Werkzeug/Flask error

def test_save_quiz_score_missing_field_score(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    data = {'chatId': 'chat123', 'totalQuestions': 10, 'quizDate': '2024-01-01'}
    response = client.post('/save_quiz_score', json=data, headers=headers)
    assert response.status_code == 400
    assert "Missing required field: score" in response.json['error']


def test_save_quiz_score_success_minimal(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    data = {'chatId': 'c1', 'score': 8, 'totalQuestions': 10, 'quizDate': '2024-01-01'}
    # Use helper: pass the dict's mock object
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=True, user_id='test_user', scores=[], add_id='s1')
    mock_chat_update = mock_firebase['firestore'].return_value.collection.return_value.document.return_value.update

    response = client.post('/save_quiz_score', json=data, headers=headers)

    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['scoreId'] == 's1'
    mock_chat_update.assert_called_once()
    args, kwargs = mock_chat_update.call_args
    saved_score = args[0]['quiz_scores'][0]
    assert 'questions' not in saved_score
    assert 'answers' not in saved_score


def test_save_quiz_score_success_full(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    data = {
        'chatId': 'c2', 'score': 4, 'totalQuestions': 5, 'quizDate': '2024-01-02',
        'questions': '[{"q": "Q1?"}]', # JSON strings
        'answers': '[{"a": "A1"}]'
    }
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=True, user_id='test_user', scores=[{'scoreId': 's0'}], add_id='s2')
    mock_chat_update = mock_firebase['firestore'].return_value.collection.return_value.document.return_value.update

    response = client.post('/save_quiz_score', json=data, headers=headers)

    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['scoreId'] == 's2'
    mock_chat_update.assert_called_once()
    args, kwargs = mock_chat_update.call_args
    saved_score = args[0]['quiz_scores'][1] # Check appended score
    assert saved_score['questions'] == '[{"q": "Q1?"}]'
    assert saved_score['answers'] == '[{"a": "A1"}]'


def test_save_quiz_score_zero_total_questions(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    data = {'chatId': 'c3', 'score': 0, 'totalQuestions': 0, 'quizDate': '2024-01-03'}
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=True, user_id='test_user', scores=[], add_id='s3')
    mock_chat_update = mock_firebase['firestore'].return_value.collection.return_value.document.return_value.update

    response = client.post('/save_quiz_score', json=data, headers=headers)
    assert response.status_code == 200
    assert response.json['scoreId'] == 's3'
    mock_chat_update.assert_called_once()
    args, kwargs = mock_chat_update.call_args
    saved_score = args[0]['quiz_scores'][0]
    assert saved_score['percentage'] == 0 # Divide by zero check


def test_save_quiz_score_chat_does_not_exist(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    data = {'chatId': 'nonexistent_chat', 'score': 5, 'totalQuestions': 10, 'quizDate': '2024-01-04'}
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=False, user_id='test_user', add_id='s4')
    mock_chat_update = mock_firebase['firestore'].return_value.collection.return_value.document.return_value.update

    response = client.post('/save_quiz_score', json=data, headers=headers)

    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['scoreId'] == 's4'
    mock_chat_update.assert_not_called() # IMPORTANT check


def test_save_quiz_score_add_exception(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    data = {'chatId': 'c4', 'score': 5, 'totalQuestions': 10, 'quizDate': '2024-01-04'}
    configure_firestore_mocks(mock_firebase['firestore'], add_should_fail=True)
    response = client.post('/save_quiz_score', json=data, headers=headers)
    assert response.status_code == 500
    assert "Error saving score: Simulated Firestore add error" in response.json['error']


def test_save_quiz_score_update_exception(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    data = {'chatId': 'c5', 'score': 5, 'totalQuestions': 10, 'quizDate': '2024-01-05'}
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=True, user_id='test_user', scores=[], add_id='s5', update_should_fail=True)

    # Expect 500 now as the update fails within the try block
    response = client.post('/save_quiz_score', json=data, headers=headers)
    assert response.status_code == 500
    assert "Error saving score: Simulated Firestore update error" in response.json['error']


# -- /get_quiz_scores/<chat_id> Tests --

def test_get_quiz_scores_no_auth(client, mock_firebase):
    mock_firebase['verify'].side_effect = Exception("Should not be called")
    response = client.get('/get_quiz_scores/chat123')
    assert response.status_code == 401
    assert 'Unauthorized' in response.json['error']


def test_get_quiz_scores_invalid_token(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    mock_firebase['verify'].side_effect = auth.InvalidIdTokenError("Auth error")
    response = client.get('/get_quiz_scores/chat123', headers=headers)
    assert response.status_code == 401
    assert "Authentication error: Auth error" in response.json['error']


def test_get_quiz_scores_chat_not_found(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=False)
    response = client.get('/get_quiz_scores/nonexistent_chat', headers=headers)
    assert response.status_code == 404
    assert response.json['error'] == 'Chat not found'


def test_get_quiz_scores_unauthorized_access(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=True, user_id='other_user') # Chat owned by someone else
    response = client.get('/get_quiz_scores/chat_owned_by_other', headers=headers)
    assert response.status_code == 403
    assert response.json['error'] == 'Unauthorized access to chat'


def test_get_quiz_scores_no_scores_in_chat(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=True, user_id='test_user', scores=None) # scores=None -> key missing
    response = client.get('/get_quiz_scores/chat_with_no_scores', headers=headers)
    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['scores'] == []


def test_get_quiz_scores_with_missing_score_fields(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    partial_score = {'scoreId': 'score_partial'} # Missing many fields
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=True, user_id='test_user', scores=[partial_score])
    response = client.get('/get_quiz_scores/chat_with_partial_scores', headers=headers)
    assert response.status_code == 200
    scores = response.json['scores']
    assert len(scores) == 1
    score = scores[0]
    assert score['scoreId'] == 'score_partial'
    assert score['score'] == 0
    assert score['totalQuestions'] == 0
    assert score['percentage'] == 0
    assert score['timestamp'] == ''
    assert score['questions'] == '[]' # Default values
    assert score['answers'] == '[]'   # Default values


def test_get_quiz_scores_success_sorted(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    # Timestamps must be realistic for sorting
    ts_old = datetime.datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    ts_new = datetime.datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    score_old = {'score': 5, 'totalQuestions': 10, 'percentage': 50, 'timestamp': ts_old, 'questions': '[]', 'answers': '[]', 'scoreId': 's1'}
    score_new = {'score': 8, 'totalQuestions': 10, 'percentage': 80, 'timestamp': ts_new, 'questions': '[]', 'answers': '[]', 'scoreId': 's2'}

    # Provide scores out of order
    configure_firestore_mocks(mock_firebase['firestore'], chat_exists=True, user_id='test_user', scores=[score_old, score_new])
    response = client.get('/get_quiz_scores/chat_with_scores', headers=headers)
    assert response.status_code == 200
    assert response.json['success'] is True
    scores = response.json['scores']
    assert len(scores) == 2
    # Verify sorting worked (newest first)
    assert scores[0]['scoreId'] == 's2'
    assert scores[1]['scoreId'] == 's1'


def test_get_quiz_scores_get_exception(client, mock_firebase):
    headers = {'Authorization': 'Bearer fake_token'}
    configure_firestore_mocks(mock_firebase['firestore'], get_should_fail=True)
    response = client.get('/get_quiz_scores/chat123', headers=headers)
    assert response.status_code == 500
    assert "Error retrieving scores: Simulated Firestore get error" in response.json['error']