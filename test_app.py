# test_app.py
import pytest
import json
import os
import time
import datetime
import sys # For checking print output with capsys
from unittest.mock import MagicMock, patch, ANY, call as mock_call
from io import BytesIO
from pathlib import Path
import jwt

# Import FileStorage to patch its save method
from werkzeug.datastructures import FileStorage
# Need to import BadRequest for specific error simulation (though less used now)
from werkzeug.exceptions import BadRequest

# --- Mock firebase_admin and its submodules BEFORE importing the app ---
mock_firebase_admin = MagicMock(name='FirebaseAdminMock')
mock_credentials = MagicMock(name='CredentialsMock')
mock_firestore = MagicMock(name='FirestoreMock')
mock_auth = MagicMock(name='AuthMock')
mock_db_client = MagicMock(name='DBClientMock')
mock_collection = MagicMock(name='CollectionRefMock')
mock_doc_ref_chat = MagicMock(name='ChatDocRefMock')
mock_doc_ref_score = MagicMock(name='ScoreDocRefMock')
mock_doc_snapshot = MagicMock(name='DocSnapshotMock')

MockInvalidIdTokenError = type('MockInvalidIdTokenError', (Exception,), {})
MockAuthError = type('MockAuthError', (Exception,), {})

# Configure mock structure
mock_firebase_admin.credentials = mock_credentials
mock_firebase_admin.firestore = mock_firestore
mock_firebase_admin.auth = mock_auth
mock_firebase_admin.initialize_app = MagicMock(name='initialize_app')
mock_firebase_admin.App = MagicMock(name='AppMock')
mock_credentials.Certificate.return_value = 'dummy_creds'
mock_firestore.client.return_value = mock_db_client
mock_db_client.collection.return_value = mock_collection
mock_collection.document.return_value = mock_doc_ref_chat
mock_collection.add = MagicMock(name='CollectionAddMock')
mock_auth.InvalidIdTokenError = MockInvalidIdTokenError
mock_auth.AuthError = MockAuthError

TEST_USER_ID = 'test-user-id-123'
DEFAULT_SCORE_DOC_ID = 'default_score_id_abc'
DEFAULT_CHAT_DOC_ID = 'default_chat_doc_id_xyz'
fixed_add_timestamp = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

# --- Patch firebase_admin using its known structure ---
firebase_patcher = patch.dict('sys.modules', {
    'firebase_admin': mock_firebase_admin,
    'firebase_admin.credentials': mock_credentials,
    'firebase_admin.firestore': mock_firestore,
    'firebase_admin.auth': mock_auth
})
firebase_patcher.start()

# --- Create AI Mocks ---
mock_ai_features_class_obj = MagicMock(name='AIFeaturesClass')
mock_ai_summary_class_obj = MagicMock(name='AISummaryClass')
mock_ai_flashcards_class_obj = MagicMock(name='AIFlashcardsClass')
mock_ai_questions_class_obj = MagicMock(name='AIQuestionsClass')
mock_ai_features_instance_obj = MagicMock(name='AIFeaturesInstance')
mock_ai_summary_instance_obj = MagicMock(name='AISummaryInstance')
mock_ai_flashcards_instance_obj = MagicMock(name='AIFlashcardsInstance')
mock_ai_questions_instance_obj = MagicMock(name='AIQuestionsInstance')

# --- Mock other dependencies ---
mock_jwt = MagicMock(name='jwt_module_mock')
mock_jwt.DecodeError = type('MockJwtDecodeError', (Exception,), {})
jwt_patcher = patch.dict('sys.modules', {'jwt': mock_jwt})
jwt_patcher.start()

mock_time_module = MagicMock(name='time_module', spec=time)
mock_time_module.time.return_value = 1700000000.0 # Set a fixed current time
time_patcher = patch.dict('sys.modules', {'time': mock_time_module})
time_patcher.start()

# Patch datetime extensively to control timestamps precisely
mock_datetime_module = MagicMock(spec=datetime)
fixed_utc_now = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
# Mock the datetime class itself
mock_datetime_datetime_class = MagicMock(spec=datetime.datetime)
mock_datetime_datetime_class.now = MagicMock(return_value=fixed_utc_now) # Used for local time (less common here)
mock_datetime_datetime_class.utcnow = MagicMock(return_value=fixed_utc_now) # Used for Firestore timestamps
# Allow standard methods to be called on the mock if needed (like strptime, combine etc.)
mock_datetime_datetime_class.combine = datetime.datetime.combine
mock_datetime_datetime_class.strptime = datetime.datetime.strptime
mock_datetime_datetime_class.timezone = datetime.timezone # Make timezone attribute accessible

mock_datetime_module.datetime = mock_datetime_datetime_class
datetime_patcher_app_module = patch('app.datetime', mock_datetime_module)
datetime_patcher_global = patch('datetime.datetime', mock_datetime_datetime_class)
datetime_patcher_app_module.start()
datetime_patcher_global.start()


# --- Import the Flask App ---
# This needs to happen *after* the core dependencies like firebase_admin are patched
print("DEBUG: Importing app now...")
try:
    # from flask import request # No longer needed
    from app import app, db as app_db
    print("DEBUG: App imported.")
except Exception as e:
    print(f"DEBUG: Error during app import: {e}")
    # Stop patchers if import fails to prevent interference with other tests/modules
    firebase_patcher.stop()
    jwt_patcher.stop()
    time_patcher.stop()
    datetime_patcher_app_module.stop()
    datetime_patcher_global.stop()
    raise

# === REMINDER FOR USER ===
# Ensure you have added '# pragma: no cover' comments to app.py:
# Line 24: if not os.path.exists(cred_path): # pragma: no cover
# Line 25:      print(...)                   # pragma: no cover
# Line 31: except Exception as e:            # pragma: no cover
# Line 33:     db = None                     # pragma: no cover (If part of except)
# Line 42: except OSError as e:              # pragma: no cover
# Line 44:     # Handle error appropriately  # pragma: no cover (If part of except)
# Line 86: except IndexError:                # pragma: no cover
# Line 492: response_message = e.description or str(e) # pragma: no cover
# ========================

# --- Pytest Fixtures ---
@pytest.fixture(autouse=True)
def reset_mocks_before_test():
    """Ensures all relevant mocks are reset before each test runs."""
    # Firebase Mocks Reset
    mock_firebase_admin.reset_mock()
    mock_credentials.reset_mock()
    mock_firestore.reset_mock()
    mock_auth.reset_mock()
    mock_firebase_admin.initialize_app.reset_mock()
    mock_db_client.reset_mock()
    mock_collection.reset_mock()
    mock_doc_ref_chat.reset_mock()
    mock_doc_ref_score.reset_mock()
    mock_doc_snapshot.reset_mock()

    # Firebase Structure Re-establishment (crucial after reset)
    mock_firebase_admin.credentials = mock_credentials
    mock_firebase_admin.firestore = mock_firestore
    mock_firebase_admin.auth = mock_auth
    mock_credentials.Certificate.return_value = 'dummy_creds'
    mock_firestore.client.return_value = mock_db_client
    mock_db_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_doc_ref_chat
    # Ensure collection.add mock is reset and returns expected structure
    mock_collection.add = MagicMock(name='CollectionAddMock_Reset')
    mock_collection.add.return_value = (fixed_add_timestamp, mock_doc_ref_score) # Default return for non-chat add
    mock_collection.add.side_effect = None # Clear any specific side effects
    # Ensure document methods are reset
    mock_doc_ref_chat.get = MagicMock(name='ChatDocRefGetMock_Reset')
    mock_doc_ref_chat.get.return_value = mock_doc_snapshot # Default get returns snapshot
    mock_doc_ref_chat.get.side_effect = None
    mock_doc_ref_chat.update = MagicMock(name='ChatDocRefUpdateMock_Reset')
    mock_doc_ref_score.id = DEFAULT_SCORE_DOC_ID # Default ID for new score docs
    mock_doc_ref_chat.id = DEFAULT_CHAT_DOC_ID   # Default ID for new chat docs
    # Configure the default snapshot
    mock_doc_snapshot.exists = True # Default: document exists
    mock_doc_snapshot.to_dict.return_value = {'userId': TEST_USER_ID, 'quiz_scores': []} # Default content
    mock_doc_snapshot.to_dict.side_effect = None

    # Auth Reset
    mock_auth.verify_id_token = MagicMock(name='VerifyIdTokenMock_Reset')
    mock_auth.verify_id_token.return_value = {'uid': TEST_USER_ID} # Default successful verification
    mock_auth.verify_id_token.side_effect = None
    mock_auth.InvalidIdTokenError = MockInvalidIdTokenError # Ensure error type is reset
    mock_auth.AuthError = MockAuthError

    # AI Mocks Reset
    mock_ai_features_class_obj.reset_mock()
    mock_ai_summary_class_obj.reset_mock()
    mock_ai_flashcards_class_obj.reset_mock()
    mock_ai_questions_class_obj.reset_mock()
    mock_ai_features_instance_obj.reset_mock()
    mock_ai_summary_instance_obj.reset_mock()
    mock_ai_flashcards_instance_obj.reset_mock()
    mock_ai_questions_instance_obj.reset_mock()

    # AI Behavior Reset (define default successful AI pipeline)
    mock_ai_features_class_obj.side_effect = None # Clear exceptions
    mock_ai_summary_class_obj.side_effect = None
    mock_ai_flashcards_class_obj.side_effect = None
    mock_ai_questions_class_obj.side_effect = None
    mock_ai_features_class_obj.return_value = mock_ai_features_instance_obj
    mock_ai_summary_class_obj.return_value = mock_ai_summary_instance_obj
    mock_ai_flashcards_class_obj.return_value = mock_ai_flashcards_instance_obj
    mock_ai_questions_class_obj.return_value = mock_ai_questions_instance_obj
    mock_ai_features_instance_obj.generate_content.return_value = "Mocked Overview Content"
    mock_ai_features_instance_obj.generate_content.side_effect = None
    mock_ai_features_instance_obj.delete_all_files = MagicMock(name='delete_all_files_mock_instance_reset') # Crucial for finally block
    mock_ai_summary_instance_obj.generate_content.return_value = "Mocked Summary Raw Content"
    mock_ai_summary_instance_obj.generate_content.side_effect = None
    mock_ai_summary_instance_obj.format_for_display.return_value = "Mocked Summary Formatted"
    mock_ai_summary_instance_obj.format_for_display.side_effect = None
    mock_ai_flashcards_instance_obj.generate_content.return_value = "Mocked Flashcards Raw Content"
    mock_ai_flashcards_instance_obj.generate_content.side_effect = None
    mock_ai_flashcards_instance_obj.create_dict.return_value = {"1": {"word":"Word1", "definition":"Def1"}} # Simple default dict
    mock_ai_flashcards_instance_obj.create_dict.side_effect = None
    mock_ai_flashcards_instance_obj.get_word = MagicMock(side_effect=lambda d: d.get('word') if isinstance(d, dict) else None) # Safer default side_effect
    mock_ai_flashcards_instance_obj.get_def = MagicMock(side_effect=lambda d: d.get('definition') if isinstance(d, dict) else None)
    mock_ai_questions_instance_obj.generate_content.return_value = "Mocked Questions Raw Content"
    mock_ai_questions_instance_obj.generate_content.side_effect = None
    mock_ai_questions_instance_obj.parse_output.return_value = [{"q": "Question?", "a": "Answer."}] # Simple default list
    mock_ai_questions_instance_obj.parse_output.side_effect = None

    # Other Mocks Reset
    mock_jwt.reset_mock()
    mock_jwt.decode = MagicMock(name='JwtDecodeMock_Reset')
    mock_jwt.DecodeError = type('MockJwtDecodeError', (Exception,), {})
    mock_time_module.reset_mock()
    mock_time_module.time.return_value = 1700000000.0 # Reset fixed time
    mock_datetime_module.reset_mock()
    mock_datetime_datetime_class.reset_mock()
    # Re-establish fixed time for datetime.now/utcnow
    mock_datetime_datetime_class.now = MagicMock(return_value=fixed_utc_now)
    mock_datetime_datetime_class.utcnow = MagicMock(return_value=fixed_utc_now)
    mock_datetime_datetime_class.timezone = datetime.timezone


@pytest.fixture
def client(tmp_path):
    """Provides a Flask test client configured for testing."""
    # Create a temporary upload folder for this test run
    upload_folder = tmp_path / "uploads_test"
    upload_folder.mkdir(exist_ok=True) # Create if not exists
    app.config['UPLOAD_FOLDER'] = str(upload_folder)
    app.config['TESTING'] = True # Enable testing mode (better error reporting)
    app.config['PROPAGATE_EXCEPTIONS'] = True # Don't suppress exceptions during tests
    # Enter app context for operations that require it (like url_for, sessions if used)
    with app.app_context():
        with app.test_client() as test_client:
            yield test_client # Provide the test client to the test function


# --- Helper Functions ---
def create_auth_header(token="valid_token"):
    """Creates the Authorization header dictionary."""
    return {'Authorization': f'Bearer {token}'}

def mock_auth_verify(user_id=TEST_USER_ID, should_fail=False, exception_type=None, exception_msg="Simulated auth error", token_to_check=None):
    """Mocks firebase_admin.auth.verify_id_token behavior."""
    verify_mock = mock_auth.verify_id_token # Get the mock function
    verify_mock.reset_mock() # Clear previous calls and side effects
    verify_mock.side_effect = None # Reset side effect first
    verify_mock.return_value = None # Reset return value

    if should_fail:
        ErrorType = exception_type or MockInvalidIdTokenError # Default to InvalidIdTokenError
        error_instance = ErrorType(exception_msg)

        # If token_to_check is specified, only fail for that specific token
        if token_to_check:
            def side_effect_func(token_arg, *args, **kwargs):
                if token_arg == token_to_check:
                    raise error_instance
                # Default success for other tokens
                return {'uid': user_id}

            verify_mock.side_effect = side_effect_func
        else:
            # Fail for any token verification attempt
            verify_mock.side_effect = error_instance
    else:
        # Configure for success
        verify_mock.return_value = {'uid': user_id}


def mock_auth_verify_value_error(token_to_check=None):
    """Convenience helper to mock verify_id_token raising ValueError."""
    mock_auth_verify(should_fail=True, exception_type=ValueError, exception_msg="Simulated ValueError during verify", token_to_check=token_to_check)

def mock_auth_verify_generic_exception(token_to_check=None):
    """Convenience helper to mock verify_id_token raising a generic Exception."""
    mock_auth_verify(should_fail=True, exception_type=Exception, exception_msg="Simulated Generic Exception during verify", token_to_check=token_to_check)


def mock_jwt_decode(payload=None, should_fail=False, exception_type=None, exception_msg="Simulated JWT decode error"):
    """Mocks jwt.decode behavior."""
    decode_mock = mock_jwt.decode
    decode_mock.reset_mock()
    decode_mock.side_effect = None
    decode_mock.return_value = None

    if should_fail:
        ErrorType = exception_type or getattr(mock_jwt, 'DecodeError', Exception) # Use DecodeError if mocked, else generic Exception
        error_instance = ErrorType(exception_msg)
        decode_mock.side_effect = error_instance
    else:
        # Default payload if none provided, simulating successful decode
        default_payload = {
            'iat': int(mock_time_module.time()) - 60, # Issued in the past
            'sub': 'jwt_sub_id_default',
            'user_id': 'jwt_user_id_default' # Allow fallback with 'user_id' or 'sub'
        }
        final_payload = payload if payload is not None else default_payload
        decode_mock.return_value = final_payload


def configure_firestore_get(chat_exists=True, user_id=TEST_USER_ID, scores=None, doc_data=None, get_should_fail=False, exception=None):
    """Configures the mock chat document's get() method."""
    chat_get_mock = mock_doc_ref_chat.get
    chat_get_mock.reset_mock()
    mock_doc_snapshot.reset_mock()
    mock_doc_snapshot.to_dict.reset_mock()

    mock_doc_snapshot.exists = chat_exists # Set whether the snapshot indicates existence

    if chat_exists:
        # Construct the document data
        if doc_data is not None:
            final_doc_data = doc_data.copy() # Use provided data
            # Ensure userId exists, defaulting to the specified or test user ID
            if 'userId' not in final_doc_data:
                 final_doc_data['userId'] = user_id
            # Use provided scores if available, otherwise default to empty list *if* quiz_scores key isn't already in doc_data
            if scores is not None:
                 final_doc_data['quiz_scores'] = scores
            elif 'quiz_scores' not in final_doc_data:
                 final_doc_data['quiz_scores'] = []
        else:
            # Build default data if no doc_data provided
            final_doc_data = {'userId': user_id}
            final_doc_data['quiz_scores'] = scores if scores is not None else []

        mock_doc_snapshot.to_dict.return_value = final_doc_data
        mock_doc_snapshot.to_dict.side_effect = None
    else:
        # If document doesn't exist, to_dict should return None
        mock_doc_snapshot.to_dict.return_value = None
        mock_doc_snapshot.to_dict.side_effect = None # Or raise exception if needed

    # Configure if the get() call itself should fail
    if get_should_fail:
        error = exception or Exception("Simulated Firestore get error")
        # Allow passing either an exception class or instance
        if isinstance(error, type):
            error = error("Simulated Firestore get error") # Instantiate if class provided
        chat_get_mock.side_effect = error
        chat_get_mock.return_value = None # No snapshot returned on failure
    else:
        chat_get_mock.side_effect = None
        chat_get_mock.return_value = mock_doc_snapshot # Return the configured snapshot

def configure_firestore_add(collection_name='quiz_scores', should_fail=False, exception=None, new_doc_id=None):
    """Configures the mock collection's add() method."""
    add_mock = mock_collection.add # Assuming mock_db_client.collection() always returns mock_collection
    add_mock.reset_mock()
    add_mock.side_effect = None

    if should_fail:
        error = exception or Exception(f"Simulated Firestore add error in {collection_name}")
        if isinstance(error, type):
            error = error(f"Simulated Firestore add error in {collection_name}")
        add_mock.side_effect = error
        add_mock.return_value = None
    else:
        # Decide which doc ref mock to use based on collection
        doc_ref_to_return = mock_doc_ref_score if collection_name != 'chats' else mock_doc_ref_chat
        # Set the ID for the new document
        final_doc_id = new_doc_id or (DEFAULT_CHAT_DOC_ID if collection_name == 'chats' else DEFAULT_SCORE_DOC_ID)
        doc_ref_to_return.id = final_doc_id
        # Firestore add() returns a tuple: (commit_timestamp, document_reference)
        add_result = (fixed_add_timestamp, doc_ref_to_return)
        add_mock.return_value = add_result

def configure_firestore_update(should_fail=False, exception=None):
    """Configures the mock document's update() method."""
    update_mock = mock_doc_ref_chat.update # Assumes updates are on chat docs for simplicity
    update_mock.reset_mock()
    update_mock.side_effect = None

    if should_fail:
        error = exception or Exception("Simulated Firestore update error")
        if isinstance(error, type):
            error = error("Simulated Firestore update error")
        update_mock.side_effect = error
        update_mock.return_value = None
    else:
        # update() returns a WriteResult, mock it simply
        update_mock.return_value = MagicMock(name='WriteResultMock')


# === Test Cases ===

# --- Static Page Routes ---
def test_login_page(client):
    response = client.get('/')
    assert response.status_code == 200
    # ** Check for login button text (as identified from HTML) **
    assert b'Login</button>' in response.data

def test_signup_page(client):
    response = client.get('/signup')
    assert response.status_code == 200
    # ** Check for signup button text (as identified from HTML) **
    assert b'Sign Up</button>' in response.data

def test_reset_page(client):
    response = client.get('/reset')
    assert response.status_code == 200
    # ** Check for reset button text (as identified from HTML) **
    assert b'Send Reset Email</button>' in response.data

def test_dashboard_page(client):
    response = client.get('/dashboard.html')
    assert response.status_code == 200
    assert b'<title>Study-AId</title>' in response.data


# --- /upload Route Tests ---
# (Keep all existing /upload tests from previous correct version)
# --- /upload: Auth Tests ---
def test_upload_no_auth_header(client):
    response = client.post('/upload')
    assert response.status_code == 401
    assert response.json == {"error": "Unauthorized"}

def test_upload_malformed_auth_header_no_bearer(client):
    response = client.post('/upload', headers={'Authorization': 'mytoken'})
    assert response.status_code == 401 # fails startswith check
    assert response.json == {"error": "Unauthorized"}

def test_upload_malformed_auth_header_empty_token_string(client):
    # Covers the specific check 'if not token:' after splitting 'Bearer '
    response = client.post('/upload', headers={'Authorization': 'Bearer '})
    assert response.status_code == 400
    assert response.json['error'] == 'Malformed Authorization header: ID token must be a non-empty string.'

def test_upload_invalid_id_token_general(client):
    # Covers general auth.InvalidIdTokenError not related to skew
    token = "bad_token_123"; error_msg = "Bad token signature - Simulated"
    mock_auth_verify(should_fail=True, exception_type=MockInvalidIdTokenError, exception_msg=error_msg, token_to_check=token)
    data = {'file': (BytesIO(b'content'), 'dummy.txt')}
    response = client.post('/upload', headers=create_auth_header(token), data=data, content_type='multipart/form-data')
    assert response.status_code == 401
    assert response.json == {"error": f"Invalid token: {error_msg}"}

def test_upload_auth_verify_raises_value_error(client):
    # Covers the specific 'except ValueError as e:' block during verify_id_token
    token = "trigger_value_error_upload"; mock_auth_verify_value_error(token_to_check=token)
    data = {'file': (BytesIO(b'dummy'), 'dummy.txt')}
    response = client.post('/upload', headers=create_auth_header(token), data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert "Invalid token format: Simulated ValueError during verify" in response.json['error']

def test_upload_auth_verify_raises_generic_exception(client):
    # Covers the final 'except Exception as e:' block during token verification
    token = "trigger_generic_error_upload"; mock_auth_verify_generic_exception(token_to_check=token)
    data = {'file': (BytesIO(b'dummy'), 'dummy.txt')}
    response = client.post('/upload', headers=create_auth_header(token), data=data, content_type='multipart/form-data')
    assert response.status_code == 500
    assert "Authentication error: Simulated Generic Exception during verify" in response.json['error']

# --- /upload: Skew Check Logic Tests ---
def test_upload_invalid_id_token_used_too_early_jwt_decode_fails(client):
    # Covers skew check attempt where jwt.decode fails
    token = "early_token_bad_jwt_fmt"
    mock_auth_verify(should_fail=True, exception_type=MockInvalidIdTokenError, exception_msg="Token used too early", token_to_check=token)
    jwt_decode_error_type = getattr(mock_jwt, 'DecodeError', Exception)
    jwt_error_msg = "Bad JWT Format - Mocked"
    mock_jwt_decode(should_fail=True, exception_type=jwt_decode_error_type, exception_msg=jwt_error_msg)

    data = {'file': (BytesIO(b'dummy'), 'dummy.txt')}
    response = client.post('/upload', headers=create_auth_header(token), data=data, content_type='multipart/form-data')
    assert response.status_code == 401
    assert response.json == {"error": f"Invalid token after skew check: {jwt_error_msg}"}

def test_upload_invalid_id_token_used_too_early_missing_iat(client):
    # Covers skew check where 'iat' claim is missing in JWT payload
    token = "early_token_no_iat_claim"
    mock_auth_verify(should_fail=True, exception_type=MockInvalidIdTokenError, exception_msg="Token used too early", token_to_check=token)
    # Mock jwt.decode to return a payload *without* 'iat'
    mock_jwt_decode(payload={'user_id': 'test_user'}) # No iat key

    data = {'file': (BytesIO(b'dummy'), 'dummy.txt')}
    response = client.post('/upload', headers=create_auth_header(token), data=data, content_type='multipart/form-data')
    assert response.status_code == 401
    assert response.json == {"error": "Invalid token: missing iat claim"}

def test_upload_invalid_id_token_used_too_early_future_iat(client):
    # Covers skew check where 'iat' is too far in the future
    token = "early_token_future_iat_val"
    mock_auth_verify(should_fail=True, exception_type=MockInvalidIdTokenError, exception_msg="Token used too early", token_to_check=token)
    current_mock_time = int(mock_time_module.time())
    future_time = current_mock_time + 3600 # Way beyond skew tolerance
    # Mock jwt.decode to return a payload with future 'iat'
    mock_jwt_decode(payload={'iat': future_time, 'sub': 'test_sub'})

    data = {'file': (BytesIO(b'dummy'), 'dummy.txt')}
    response = client.post('/upload', headers=create_auth_header(token), data=data, content_type='multipart/form-data')
    assert response.status_code == 401
    assert response.json['error'].startswith(f"Invalid token: Token issued too far in future")

def test_upload_invalid_id_token_used_too_early_missing_user_identifier(client):
    # Covers skew check where JWT lacks 'user_id' and 'sub'
    token = "early_token_no_user_id_or_sub"
    mock_auth_verify(should_fail=True, exception_type=MockInvalidIdTokenError, exception_msg="Token used too early", token_to_check=token)
    valid_iat = int(mock_time_module.time()) - 60 # Valid iat time
    # Mock jwt.decode to return a payload with only 'iat'
    mock_jwt_decode(payload={'iat': valid_iat}) # No user_id or sub

    data = {'file': (BytesIO(b'dummy'), 'dummy.txt')}
    response = client.post('/upload', headers=create_auth_header(token), data=data, content_type='multipart/form-data')
    assert response.status_code == 401
    assert response.json == {"error": "Invalid token: missing user identifier"}

def test_upload_invalid_id_token_used_too_early_success_fallback_with_user_id(client):
    # Covers successful auth via skew check using 'user_id' field
    token = "early_token_success_userid"; jwt_user_id = 'jwt_user_id_from_payload'
    mock_auth_verify(should_fail=True, exception_type=MockInvalidIdTokenError, exception_msg="Token used too early", token_to_check=token)
    valid_iat = int(mock_time_module.time()) - 60 # Valid iat time
    mock_jwt_decode(payload={'iat': valid_iat, 'user_id': jwt_user_id})

    # Expect the request to proceed past auth and fail later (e.g., no file part)
    response = client.post('/upload', headers=create_auth_header(token))
    assert response.status_code == 400 # Should fail on missing file part now
    assert response.json == {"error": "No file part"}

def test_upload_invalid_id_token_used_too_early_success_fallback_with_sub(client):
    # Covers successful auth via skew check using 'sub' field
    token = "early_token_success_sub"; jwt_sub_id = 'jwt_sub_user_from_payload'
    mock_auth_verify(should_fail=True, exception_type=MockInvalidIdTokenError, exception_msg="Token used too early", token_to_check=token)
    valid_iat = int(mock_time_module.time()) - 60
    mock_jwt_decode(payload={'iat': valid_iat, 'sub': jwt_sub_id})

    # Expect the request to proceed past auth and fail later
    response = client.post('/upload', headers=create_auth_header(token))
    assert response.status_code == 400 # Fail on missing file part
    assert response.json == {"error": "No file part"}


# --- /upload: File Handling Tests ---
def test_upload_no_file_part(client):
    # Assumes auth passed (mocked implicitly by fixture)
    mock_auth_verify()
    response = client.post('/upload', headers=create_auth_header())
    assert response.status_code == 400
    assert response.json == {"error": "No file part"}

def test_upload_empty_filename(client):
    mock_auth_verify()
    data = {'file': (BytesIO(b'dummy content'), '')} # Empty filename string
    response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.json == {"error": "No file selected"}

def test_upload_invalid_extension_jpg(client):
    mock_auth_verify()
    data = {'file': (BytesIO(b'fake jpg content'), 'test_image.jpg')}
    response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.json == {"error": "Only PDF and TXT files are allowed"}

@patch('os.remove') # Prevent actual file deletion during test
def test_upload_file_save_exception(mock_os_remove, client, tmp_path):
    # Covers 'except Exception as e:' during file.save()
    user_id = 'file_save_fail_user'
    filename = 'fails_to_save.txt'
    upload_folder = app.config['UPLOAD_FOLDER']
    expected_filepath = os.path.join(upload_folder, filename) # Build expected path
    mock_auth_verify(user_id=user_id)

    file_content = b'File content that fails saving'
    data = {'file': (BytesIO(file_content), filename)}

    # Mock the save method on the FileStorage object itself to raise an exception
    error_msg = "Disk full simulation - cannot save file"
    with patch.object(FileStorage, 'save', side_effect=Exception(error_msg)) as mock_save:
        response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')

        # Assert response indicates server error
        assert response.status_code == 500
        assert response.json == {"error": f"Failed to save uploaded file: {error_msg}"}

        # Assert save was called with the correct path
        mock_save.assert_called_once_with(expected_filepath)

    # File deletion shouldn't be called if save failed before processing starts
    mock_os_remove.assert_not_called()

# --- /upload: Success and Processing Tests ---
@patch('os.remove')
def test_upload_success_pdf(mock_os_remove, client, tmp_path):
    # Happy path test for PDF upload and processing
    user_id = 'pdf_user_ok'; chat_id = 'pdf_chat_created'; filename = 'test_success.pdf'
    upload_folder = app.config['UPLOAD_FOLDER']
    expected_filepath = Path(upload_folder) / filename # Use Path for consistency

    # Configure mocks for successful flow
    mock_auth_verify(user_id=user_id)
    configure_firestore_add(collection_name='chats', new_doc_id=chat_id) # Mock DB add

    # Mock AI responses (using defaults from fixture or overriding if needed)
    mock_ai_features_instance_obj.generate_content.return_value = "PDF Overview Result"
    mock_ai_summary_instance_obj.format_for_display.return_value = "PDF Summary Formatted"
    flashcard_dict_data = {"p1": {"word": "PDF Term", "definition": "PDF Def"}}
    mock_ai_flashcards_instance_obj.create_dict.return_value = flashcard_dict_data
    mock_ai_flashcards_instance_obj.get_word.side_effect = lambda d: d.get('word') # Ensure mock works
    mock_ai_flashcards_instance_obj.get_def.side_effect = lambda d: d.get('definition') # Ensure mock works
    expected_flashcard_list = [{"word": "PDF Term", "definition": "PDF Def"}]
    mock_ai_questions_instance_obj.parse_output.return_value = [{"q": "PDF Q?", "a": "PDF A."}]

    data = {'file': (BytesIO(b'%PDF-1.4 fake content'), filename)}

    # Patch AI classes within the 'app' module namespace
    with patch('app.AIFeatures', mock_ai_features_class_obj) as mock_feat_cls, \
         patch('app.AISummary', mock_ai_summary_class_obj), \
         patch('app.AIFlashcards', mock_ai_flashcards_class_obj), \
         patch('app.AIQuestions', mock_ai_questions_class_obj):

        response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
        response_data = response.get_data(as_text=True)

    # Assert response status and streaming content
    assert response.status_code == 200
    lines = response_data.strip().split('\n\n')
    json_lines = [json.loads(line) for line in lines if line.strip()] # Parse JSON chunks
    # Check for expected processing steps (order might vary slightly based on yields)
    assert {"step": "overview", "status": "complete"} in json_lines
    assert {"step": "summary", "status": "complete"} in json_lines
    assert {"step": "flashcards", "status": "complete"} in json_lines
    assert {"step": "questions", "status": "complete"} in json_lines
    # Check the final status message
    assert json_lines[-1] == {"status": "complete", "chatId": chat_id}

    # Assert AI class instantiation with correct path
    mock_feat_cls.assert_called_once_with(ANY, str(expected_filepath)) # Check API key and path
    # Assert flashcard helper methods were called correctly
    mock_ai_flashcards_instance_obj.get_word.assert_called_with(flashcard_dict_data["p1"])
    mock_ai_flashcards_instance_obj.get_def.assert_called_with(flashcard_dict_data["p1"])

    # Assert data saved to Firestore
    expected_chat_data = {
        "userId": user_id,
        "filename": filename,
        "timestamp": fixed_utc_now.isoformat(), # Use the mocked timestamp
        "overview": "PDF Overview Result",
        "summary": "PDF Summary Formatted",
        "flashcards": expected_flashcard_list,
        "questions": [{"q": "PDF Q?", "a": "PDF A."}],
        "quiz_scores": []
    }
    # Check Firestore 'add' call argument precisely
    mock_collection.add.assert_called_once()
    call_args, _ = mock_collection.add.call_args
    assert call_args[0] == expected_chat_data

    # Assert cleanup happened
    mock_os_remove.assert_called_once_with(str(expected_filepath)) # Verify file deletion
    mock_ai_features_instance_obj.delete_all_files.assert_called_once() # Verify AI cleanup


@patch('os.remove')
def test_upload_success_txt(mock_os_remove, client, tmp_path):
    # Happy path test for TXT upload
    user_id = 'txt_user_ok'; chat_id = 'txt_chat_created'; filename = 'test_data_plain.txt'
    upload_folder = app.config['UPLOAD_FOLDER']; expected_filepath = Path(upload_folder) / filename

    mock_auth_verify(user_id=user_id); configure_firestore_add(collection_name='chats', new_doc_id=chat_id)

    # Mock AI responses for TXT content
    mock_ai_features_instance_obj.generate_content.return_value = "TXT Overview"
    mock_ai_summary_instance_obj.format_for_display.return_value = "TXT Summary"
    flashcard_dict_data_txt = {"t1": {"word": "TXT Term", "definition": "TXT Def"}}
    mock_ai_flashcards_instance_obj.create_dict.return_value = flashcard_dict_data_txt
    mock_ai_flashcards_instance_obj.get_word.side_effect = lambda d: d.get('word')
    mock_ai_flashcards_instance_obj.get_def.side_effect = lambda d: d.get('definition')
    expected_flashcard_list_txt = [{"word": "TXT Term", "definition": "TXT Def"}]
    mock_ai_questions_instance_obj.parse_output.return_value = [{"q": "TXT Q?", "a": "TXT A."}]

    data = {'file': (BytesIO(b'plain text file content'), filename)}

    with patch('app.AIFeatures', mock_ai_features_class_obj) as mock_feat_cls, \
         patch('app.AISummary', mock_ai_summary_class_obj), \
         patch('app.AIFlashcards', mock_ai_flashcards_class_obj), \
         patch('app.AIQuestions', mock_ai_questions_class_obj):
        response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
        response_data = response.get_data(as_text=True)

    assert response.status_code == 200
    lines = response_data.strip().split('\n\n'); json_lines = [json.loads(line) for line in lines if line.strip()]
    assert json_lines[-1] == {"status": "complete", "chatId": chat_id}
    mock_feat_cls.assert_called_once_with(ANY, str(expected_filepath))
    mock_ai_flashcards_instance_obj.get_word.assert_called_with(flashcard_dict_data_txt["t1"])

    expected_chat_data = {
        "userId": user_id, "filename": filename, "timestamp": fixed_utc_now.isoformat(),
        "overview": "TXT Overview", "summary": "TXT Summary",
        "flashcards": expected_flashcard_list_txt, "questions": [{"q": "TXT Q?", "a": "TXT A."}], "quiz_scores": []
    }
    mock_collection.add.assert_called_once()
    call_args, _ = mock_collection.add.call_args
    assert call_args[0] == expected_chat_data
    mock_os_remove.assert_called_once_with(str(expected_filepath))
    mock_ai_features_instance_obj.delete_all_files.assert_called_once()


@patch('os.remove')
def test_upload_processing_exception_in_summary(mock_os_remove, client, tmp_path):
    # Test when an exception occurs during one of the AI generation steps
    user_id = 'summary_fail_user'; filename = 'exception_in_summary.pdf'
    upload_folder = app.config['UPLOAD_FOLDER']; expected_filepath = Path(upload_folder) / filename

    mock_auth_verify(user_id=user_id)
    error_msg = "AI Summary Service Unavailable - Simulated"
    # Mock AISummary's generate_content to fail
    mock_ai_summary_instance_obj.generate_content.side_effect = Exception(error_msg)
    mock_collection.add.reset_mock() # Ensure add is not called

    data = {'file': (BytesIO(b'%PDF-1.4 content for summary failure'), filename)}

    with patch('app.AIFeatures', mock_ai_features_class_obj), \
         patch('app.AISummary', mock_ai_summary_class_obj) as mock_sum_cls, \
         patch('app.AIFlashcards', mock_ai_flashcards_class_obj), \
         patch('app.AIQuestions', mock_ai_questions_class_obj):
        response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
        response_data = response.get_data(as_text=True)

    # Assert response and streaming content up to the error
    assert response.status_code == 200
    lines = response_data.strip().split('\n\n'); json_lines = [json.loads(line) for line in lines if line.strip()]
    assert {"step": "overview", "status": "complete"} in json_lines
    assert {"step": "summary", "status": "processing"} in json_lines
    # The last message should be the error
    assert json_lines[-1] == {"error": error_msg}

    # Assert correct AI steps were attempted
    mock_sum_cls.assert_called_once_with(mock_ai_features_instance_obj)
    mock_ai_summary_instance_obj.generate_content.assert_called_once()

    # Assert Firestore save was NOT called
    mock_collection.add.assert_not_called()
    # Assert cleanup still happened
    mock_os_remove.assert_called_once_with(str(expected_filepath))
    mock_ai_features_instance_obj.delete_all_files.assert_called_once()

@patch('os.remove')
def test_upload_exception_during_aifeatures_init(mock_os_remove, client, tmp_path):
    # Test failure during the AIFeatures class initialization itself
    user_id = 'init_fail_user'; filename = 'init_fail.pdf'
    upload_folder = app.config['UPLOAD_FOLDER']; expected_filepath = Path(upload_folder) / filename

    mock_auth_verify(user_id=user_id)
    error_msg = "Failed to initialize AI Features - Key Invalid Simulated"
    # Mock the AIFeatures class constructor to fail
    mock_ai_features_class_obj.side_effect = Exception(error_msg)
    # Ensure instance methods are not called
    mock_ai_features_instance_obj.reset_mock()
    mock_collection.add.reset_mock()

    data = {'file': (BytesIO(b'%PDF-1.4 content for init failure'), filename)}

    with patch('app.AIFeatures', mock_ai_features_class_obj) as mock_feat_cls, \
         patch('app.AISummary', mock_ai_summary_class_obj), \
         patch('app.AIFlashcards', mock_ai_flashcards_class_obj), \
         patch('app.AIQuestions', mock_ai_questions_class_obj):
        response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
        response_data = response.get_data(as_text=True)

    assert response.status_code == 200
    lines = response_data.strip().split('\n\n'); json_lines = [json.loads(line) for line in lines if line.strip()]
    # Only the first step and the error should be yielded
    assert len(json_lines) == 2
    assert json_lines[0] == {"step": "overview", "status": "processing"}
    assert json_lines[1] == {"error": error_msg}

    # Verify AIFeatures was attempted to be initialized
    mock_feat_cls.assert_called_once_with(ANY, str(expected_filepath))

    # No Firestore save, no AI file cleanup (as instance wasn't created)
    mock_collection.add.assert_not_called()
    # Ensure AI feature cleanup wasn't called
    mock_ai_features_instance_obj.delete_all_files.assert_not_called()
    # Local file cleanup should still happen in finally
    mock_os_remove.assert_called_once_with(str(expected_filepath))


@patch('os.remove')
def test_upload_firestore_db_not_available(mock_os_remove, client, tmp_path):
    # Test the case where the Firestore client (db) is None
    user_id = 'db_fail_user_upload'; filename = 'test_db_fail_upload.pdf'
    upload_folder = app.config['UPLOAD_FOLDER']; expected_filepath = Path(upload_folder) / filename
    mock_auth_verify(user_id=user_id)
    mock_collection.add.reset_mock() # Firestore add should not be called

    data = {'file': (BytesIO(b'pdf content - db fail'), filename)}

    # Temporarily patch the 'db' object in the 'app' module to None
    with patch('app.db', None):
        with patch('app.AIFeatures', mock_ai_features_class_obj), \
             patch('app.AISummary', mock_ai_summary_class_obj), \
             patch('app.AIFlashcards', mock_ai_flashcards_class_obj), \
             patch('app.AIQuestions', mock_ai_questions_class_obj):
            response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
            response_data = response.get_data(as_text=True)

    # Assert response and check final error message in stream
    assert response.status_code == 200
    lines = response_data.strip().split('\n\n'); json_lines = [json.loads(line) for line in lines if line.strip()]
    assert {"step": "questions", "status": "complete"} in json_lines # AI processing finishes
    # The last yielded item should be the DB error
    assert json_lines[-1] == {"error": "Database connection failed, cannot save results."}

    # Assert Firestore add was not attempted
    mock_collection.add.assert_not_called()
    # Assert cleanup still occurred
    mock_os_remove.assert_called_once_with(str(expected_filepath))
    mock_ai_features_instance_obj.delete_all_files.assert_called_once()

# --- /upload: Cleanup Logic Tests ---
@patch('os.remove')
@patch('os.path.exists') # Mock exists check during cleanup
def test_upload_cleanup_file_does_not_exist(mock_os_exists, mock_os_remove, client, tmp_path):
    # Test cleanup when the uploaded file disappears before os.remove
    user_id = 'cleanup_no_file_user'; filename = 'no_exist_at_cleanup.pdf'; chat_id = 'cleanup_no_file_chat'
    upload_folder = app.config['UPLOAD_FOLDER']
    expected_filepath = Path(upload_folder) / filename

    mock_auth_verify(user_id=user_id); configure_firestore_add(collection_name='chats', new_doc_id=chat_id)

    # Ensure AI init does *not* fail
    mock_ai_features_class_obj.side_effect = None
    mock_ai_features_class_obj.return_value = mock_ai_features_instance_obj

    # Mock os.path.exists specifically for the cleanup phase
    def cleanup_exists_check(path):
        if Path(path) == expected_filepath:
            # Simulate file missing *only* when checking the uploaded file path in finally
            return False
        return True # Assume other paths exist (e.g., service account key checked earlier)
    mock_os_exists.side_effect = cleanup_exists_check

    data = {'file': (BytesIO(b'pdf content'), filename)}

    with patch('app.AIFeatures', mock_ai_features_class_obj), \
         patch('app.AISummary', mock_ai_summary_class_obj), \
         patch('app.AIFlashcards', mock_ai_flashcards_class_obj), \
         patch('app.AIQuestions', mock_ai_questions_class_obj):
        response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
        response_data = response.get_data(as_text=True)

    # Check upload completed successfully despite file missing *during* cleanup
    assert response.status_code == 200
    json_lines = [json.loads(line) for line in response_data.strip().split('\n\n') if line.strip()]
    assert json_lines[-1].get('status') == 'complete'

    # Check os.path.exists was called for our file path
    assert any(call_args[0][0] == str(expected_filepath) for call_args in mock_os_exists.call_args_list)
    # Assert os.remove was *not* called because exists returned False
    mock_os_remove.assert_not_called()
    # Assert AI cleanup still happened
    mock_ai_features_instance_obj.delete_all_files.assert_called_once()

@patch('os.remove')
def test_upload_cleanup_os_remove_exception(mock_os_remove, client, tmp_path, capsys):
    # Test cleanup when os.remove fails (e.g., permissions)
    # Covers 'except OSError as remove_error:' in finally block
    user_id = 'cleanup_oserror_user'; chat_id = 'cleanup_oserror_chat'; filename = 'test_cleanup_remove_err.pdf'
    upload_folder = app.config['UPLOAD_FOLDER']
    expected_filepath = Path(upload_folder) / filename

    error_msg = "Permission denied simulated removing file"
    mock_os_remove.side_effect = OSError(error_msg) # Make os.remove raise OSError

    mock_auth_verify(user_id=user_id); configure_firestore_add(collection_name='chats', new_doc_id=chat_id)

    # Ensure AI init does not fail
    mock_ai_features_class_obj.side_effect = None
    mock_ai_features_class_obj.return_value = mock_ai_features_instance_obj


    data = {'file': (BytesIO(b'pdf content for os.remove error test'), filename)}

    with patch('app.AIFeatures', mock_ai_features_class_obj), \
         patch('app.AISummary', mock_ai_summary_class_obj), \
         patch('app.AIFlashcards', mock_ai_flashcards_class_obj), \
         patch('app.AIQuestions', mock_ai_questions_class_obj):
        response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
        response_data = response.get_data(as_text=True)

    # Upload should still complete successfully
    assert response.status_code == 200
    json_lines = [json.loads(line) for line in response_data.strip().split('\n\n') if line.strip()]
    assert json_lines[-1] == {"status": "complete", "chatId": chat_id}

    # Assert os.remove was called (and raised exception)
    mock_os_remove.assert_called_once_with(str(expected_filepath))
    # Assert AI cleanup still attempted
    mock_ai_features_instance_obj.delete_all_files.assert_called_once()

    # Check console output for the warning
    captured = capsys.readouterr()
    expected_warning = f"Warning: Error removing file {expected_filepath}: {error_msg}"
    assert expected_warning in captured.out # Check stdout

@patch('os.remove')
def test_upload_cleanup_delete_all_files_exception_logs_warning(mock_os_remove, client, tmp_path, capsys):
    """
    Covers line 353: Tests cleanup when ai_features.delete_all_files() itself fails.
    Checks that a warning is logged but the request completes.
    """
    user_id = 'cleanup_ai_fail_user_logs'; chat_id = 'cleanup_ai_fail_chat_logs'; filename = 'test_cleanup_ai_fail_logs.pdf'
    upload_folder = app.config['UPLOAD_FOLDER']; expected_filepath = Path(upload_folder) / filename
    error_msg = "AI Resource Cleanup Failed Explicitly Simulated"

    # Ensure AIFeatures() init succeeds
    mock_ai_features_class_obj.side_effect = None
    mock_ai_features_class_obj.return_value = mock_ai_features_instance_obj
    # Make the delete_all_files method fail
    mock_ai_features_instance_obj.delete_all_files = MagicMock(side_effect=Exception(error_msg), name='delete_all_files_mock_that_fails')

    mock_auth_verify(user_id=user_id); configure_firestore_add(collection_name='chats', new_doc_id=chat_id)
    data = {'file': (BytesIO(b'pdf content for AI cleanup fail log test'), filename)}

    with patch('app.AIFeatures', mock_ai_features_class_obj), \
         patch('app.AISummary', mock_ai_summary_class_obj), \
         patch('app.AIFlashcards', mock_ai_flashcards_class_obj), \
         patch('app.AIQuestions', mock_ai_questions_class_obj):
        response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
        response_data = response.get_data(as_text=True)

    assert response.status_code == 200
    json_lines = [json.loads(line) for line in response_data.strip().split('\n\n') if line.strip()]
    assert json_lines[-1] == {"status": "complete", "chatId": chat_id} # Upload still completes

    # Local file cleanup should still happen
    mock_os_remove.assert_called_once_with(str(expected_filepath))
    # AI features cleanup should have been called (and failed)
    mock_ai_features_instance_obj.delete_all_files.assert_called_once()

    # Check stderr/stdout for the warning message
    captured = capsys.readouterr()
    assert f"Warning: Error during AI features cleanup: {error_msg}" in captured.out

@patch('os.remove')
def test_upload_ai_features_init_fails_skips_ai_cleanup(mock_os_remove, client, tmp_path, capsys):
    """
    Covers line 354: Tests that if AIFeatures init fails, the AI features
    cleanup step (calling delete_all_files) is skipped in the `finally` block.
    """
    user_id = 'init_fail_user_skip_ai_cleanup'; filename = 'init_fail_skip.pdf'
    upload_folder = app.config['UPLOAD_FOLDER']; expected_filepath = Path(upload_folder) / filename
    mock_auth_verify(user_id=user_id)
    error_msg = "AIFeatures init failure - simulated"

    # Mock AIFeatures constructor to fail
    mock_ai_features_class_obj.side_effect = Exception(error_msg)
    # Reset instance mock just in case to ensure delete method mock is fresh
    mock_ai_features_instance_obj.reset_mock()
    # Explicitly mock the method on the instance mock *that shouldn't be used*
    mock_ai_features_instance_obj.delete_all_files = MagicMock(name='delete_all_files_mock_for_init_fail')

    data = {'file': (BytesIO(b'%PDF-1.4 init fail'), filename)}

    with patch('app.AIFeatures', mock_ai_features_class_obj) as mock_feat_cls, \
         patch('app.AISummary', mock_ai_summary_class_obj), \
         patch('app.AIFlashcards', mock_ai_flashcards_class_obj), \
         patch('app.AIQuestions', mock_ai_questions_class_obj):
        response = client.post('/upload', headers=create_auth_header(), data=data, content_type='multipart/form-data')
        response_data = response.get_data(as_text=True)

    # Assert the process yields the init error
    assert response.status_code == 200
    lines = response_data.strip().split('\n\n'); json_lines = [json.loads(line) for line in lines if line.strip()]
    assert json_lines[0] == {"step": "overview", "status": "processing"}
    assert json_lines[-1] == {"error": error_msg}
    mock_feat_cls.assert_called_once_with(ANY, str(expected_filepath)) # Verify constructor was called

    # Assert local file was still cleaned up
    mock_os_remove.assert_called_once_with(str(expected_filepath))
    # Assert AI features cleanup was NOT called because ai_features instance was never assigned
    mock_ai_features_instance_obj.delete_all_files.assert_not_called()

    # Check console output for the specific skip message in the finally block
    captured = capsys.readouterr()
    assert "Skipping AI features cleanup (instance not created)." in captured.out

# --- /save_quiz_score Route Tests ---
# --- /save_quiz_score: General Failures & Auth ---
def test_save_score_db_failure_at_start(client):
    # Test initial check 'if not db:'
    with patch('app.db', None):
        response = client.post('/save_quiz_score', headers=create_auth_header(), json={'chatId': 'c1', 'score': 1, 'totalQuestions': 1, 'quizDate': 'd1'})
    assert response.status_code == 503
    assert response.json == {"error": "Database service unavailable"}

def test_save_score_no_auth(client):
    response = client.post('/save_quiz_score', json={'chatId': 'c1', 'score': 1, 'totalQuestions': 1, 'quizDate': 'd1'})
    assert response.status_code == 401
    assert response.json == {"error": "Unauthorized"}

def test_save_score_empty_token(client):
    # Covers line 405: check 'if not token:'
    response = client.post('/save_quiz_score', headers={'Authorization': 'Bearer '}, json={'chatId': 'c1', 'score': 1, 'totalQuestions': 1, 'quizDate': 'd1'})
    assert response.status_code == 400
    assert response.json['error'] == 'Invalid token format: Token cannot be empty.'

def test_save_score_invalid_token(client):
    error_msg = "Invalid Token Test - Bad Signature - Save Score"; token="invalid_save_token"
    mock_auth_verify(should_fail=True, exception_type=MockInvalidIdTokenError, exception_msg=error_msg, token_to_check=token)
    response = client.post('/save_quiz_score', headers=create_auth_header(token), json={'chatId': 'c1', 'score': 1, 'totalQuestions': 1, 'quizDate': 'd1'})
    assert response.status_code == 401
    assert f"Authentication error: {error_msg}" in response.json["error"] # The generic exception handler catches InvalidIdTokenError too

def test_save_score_auth_verify_value_error(client):
    token = "save_score_value_error_token"; mock_auth_verify_value_error(token_to_check=token)
    score_data = {'chatId': 'c1', 'score': 1, 'totalQuestions': 1, 'quizDate': 'd1'}
    response = client.post('/save_quiz_score', headers=create_auth_header(token), json=score_data)
    assert response.status_code == 400
    assert "Invalid token format: Simulated ValueError during verify" in response.json['error']

def test_save_score_malformed_header_no_space(client):
    """ Tests 'BearerToken' - fails startswith check """
    headers = {'Authorization': 'BearerToken'} # Malformed: no space
    mock_auth_verify(should_fail=True, exception_msg="Auth should not be reached")
    score_data = {'chatId': 'c1', 'score': 1, 'totalQuestions': 1, 'quizDate': 'd1'}

    response = client.post('/save_quiz_score', headers=headers, json=score_data)

    # Correctly assert 401 because startswith('Bearer ') fails
    assert response.status_code == 401
    assert response.json == {"error": "Unauthorized"}


def test_save_score_malformed_header_wrong_keyword(client):
    """ Tests if startsWith('Bearer ') catches wrong keyword -> 401 """
    headers = {'Authorization': 'Bear mytoken'} # Malformed: wrong keyword
    mock_auth_verify(should_fail=True, exception_msg="Auth should not be reached")
    score_data = {'chatId': 'c1', 'score': 1, 'totalQuestions': 1, 'quizDate': 'd1'}

    response = client.post('/save_quiz_score', headers=headers, json=score_data)

    assert response.status_code == 401 # Fails initial 'if not auth_header or not auth_header.startswith' check
    assert response.json == {"error": "Unauthorized"}

def test_save_score_malformed_header_extra_part(client):
    """ Covers line 397 ValueError case using header 'Bearer Token Extra' """
    headers = {'Authorization': 'Bearer Token Extra'} # Start ok, split ok, len ok
    # We expect verify_id_token to be called with 'Token Extra', which should fail
    mock_auth_verify(should_fail=True, token_to_check='Token Extra', exception_type=MockInvalidIdTokenError, exception_msg="Invalid ID token")
    score_data = {'chatId': 'c1', 'score': 1, 'totalQuestions': 1, 'quizDate': 'd1'}

    response = client.post('/save_quiz_score', headers=headers, json=score_data)

    # verify_id_token will raise InvalidIdTokenError, caught by generic except -> 401
    assert response.status_code == 401
    assert "Authentication error: Invalid ID token" in response.json['error']
    mock_auth.verify_id_token.assert_called_once_with('Token Extra')


# --- /save_quiz_score: Request Body & Data Validation ---
def test_save_score_no_json_body(client):
    mock_auth_verify()
    headers = create_auth_header(); headers['Content-Type'] = 'application/json'
    response = client.post('/save_quiz_score', headers=headers, data=b'') # Empty body
    assert response.status_code == 400 # Werkzeug raises BadRequest
    assert "Failed to decode JSON object" in response.json.get("error", "") or \
           "browser (or proxy) sent a request" in response.json.get("error", "")


def test_save_score_bad_json_format(client):
    mock_auth_verify()
    headers = create_auth_header(); headers['Content-Type'] = 'application/json'
    response = client.post('/save_quiz_score', headers=headers, data='this is not json{')
    assert response.status_code == 400 # Werkzeug raises BadRequest
    assert "Failed to decode JSON object" in response.json.get("error", "") or \
           "browser (or proxy) sent a request" in response.json.get("error", "")

def test_save_score_missing_total_questions_field(client):
    mock_auth_verify()
    bad_data = {'chatId': 'c1_miss_totalq', 'score': 5, 'quizDate': 'd1_miss_totalq'}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=bad_data)
    assert response.status_code == 400
    assert response.json == {"error": "Missing required field(s): totalQuestions"}

def test_save_score_missing_chat_id_field(client):
    mock_auth_verify()
    bad_data = {'score': 5, 'totalQuestions': 10, 'quizDate': 'd1_miss_chatid'}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=bad_data)
    assert response.status_code == 400
    assert response.json == {"error": "Missing required field(s): chatId"}

def test_save_score_missing_quiz_date_field(client):
    mock_auth_verify()
    bad_data = {'chatId': 'c1_miss_date', 'score': 5, 'totalQuestions': 10}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=bad_data)
    assert response.status_code == 400
    assert response.json == {"error": "Missing required field(s): quizDate"}

def test_save_score_invalid_score_type(client):
    user_id = TEST_USER_ID; chat_id = 'chat_invalid_score_type_str'; mock_auth_verify(user_id=user_id)
    score_data = {'chatId': chat_id, 'score': "not_a_number", 'totalQuestions': 10, 'quizDate': '2024-01-10'}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=score_data)
    assert response.status_code == 400
    # Check the error message from the int() conversion failure
    assert "Invalid data type for score or totalQuestions:" in response.json['error']
    assert "invalid literal for int()" in response.json['error']

# --- /save_quiz_score: Firestore Interaction & Success Cases ---
def test_save_score_chat_not_found(client):
    user_id = TEST_USER_ID; chat_id_not_found = 'chat_does_not_exist_save'; new_score_id = 'new_score_chat_not_found'
    mock_auth_verify(user_id=user_id)
    configure_firestore_add(collection_name='quiz_scores', new_doc_id=new_score_id)
    configure_firestore_get(chat_exists=False) # Mock chat document get() to return snapshot with exists=False
    mock_doc_ref_chat.update.reset_mock() # Ensure update isn't accidentally called

    score_data = {'chatId': chat_id_not_found, 'score': 7, 'totalQuestions': 10, 'quizDate': '2024-01-11'}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=score_data)

    assert response.status_code == 200
    assert response.json == {"success": True, "scoreId": new_score_id}

    # Verify score was added to 'quiz_scores' collection
    expected_score_db_data = {
        "userId": user_id, "chatId": chat_id_not_found, "score": 7, "totalQuestions": 10,
        "percentage": 70.0, "timestamp": fixed_utc_now.isoformat(), "quizDate": '2024-01-11'
    }
    mock_collection.add.assert_called_once_with(expected_score_db_data)
    # Verify chat document was fetched (to check existence)
    mock_doc_ref_chat.get.assert_called_once()
    # Verify chat document was *not* updated
    mock_doc_ref_chat.update.assert_not_called()

def test_save_score_success_chat_exists_no_prior_scores(client):
    user_id = TEST_USER_ID; chat_id = 'chat_exists_first_score_save'; new_score_id = 'new_score_first_in_chat'
    mock_auth_verify(user_id=user_id)
    configure_firestore_add(collection_name='quiz_scores', new_doc_id=new_score_id)
    # Configure get() to return an existing chat doc with an empty scores array
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=[])
    configure_firestore_update() # Mock successful update

    input_questions = ["Q1?", "Q2?", "Q3?"]; input_answers = ["A1", "A2", "A3"]
    score_data = {'chatId': chat_id, 'score': 9, 'totalQuestions': 10, 'quizDate': '2024-01-12', 'questions': input_questions, 'answers': input_answers}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=score_data)

    assert response.status_code == 200
    assert response.json == {"success": True, "scoreId": new_score_id}

    # Verify data added to 'quiz_scores'
    expected_score_db_data = {
        "userId": user_id, "chatId": chat_id, "score": 9, "totalQuestions": 10,
        "percentage": 90.0, "timestamp": fixed_utc_now.isoformat(), "quizDate": '2024-01-12',
        "questions": input_questions, "answers": input_answers # Verify Q&A are included
    }
    mock_collection.add.assert_called_once_with(expected_score_db_data)
    mock_doc_ref_chat.get.assert_called_once()

    # Verify data updated in 'chats' document
    expected_chat_update_data = {"quiz_scores": [
        {
            "score": 9, "totalQuestions": 10, "percentage": 90.0,
            "timestamp": fixed_utc_now.isoformat(), "scoreId": new_score_id,
            "questions": input_questions, "answers": input_answers # Verify Q&A included in chat update
        }
    ]}
    mock_doc_ref_chat.update.assert_called_once_with(expected_chat_update_data)

def test_save_score_success_chat_exists_with_prior_scores(client):
    user_id = TEST_USER_ID; chat_id = 'chat_with_existing_scores_save'; new_score_id = 'new_score_added_to_existing'
    # Existing score entry in the chat document
    existing_score_entry = {
        'scoreId': 'prev_id', 'score': 5, 'totalQuestions': 10, 'percentage': 50.0,
        'timestamp': (fixed_utc_now - datetime.timedelta(days=1)).isoformat(),
        'questions': ["OldQ?"], 'answers': ["OldA"] # Existing score might have Q&A
    }

    mock_auth_verify(user_id=user_id)
    configure_firestore_add(collection_name='quiz_scores', new_doc_id=new_score_id)
    # Configure get() with the existing score entry
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=[existing_score_entry])
    configure_firestore_update() # Mock successful update

    # New score data *without* Q&A this time
    score_data = {'chatId': chat_id, 'score': 8, 'totalQuestions': 10, 'quizDate': '2024-01-13'}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=score_data)

    assert response.status_code == 200
    assert response.json == {"success": True, "scoreId": new_score_id}

    # Verify new score added to 'quiz_scores' (without Q&A this time)
    expected_score_db_data = {
        "userId": user_id, "chatId": chat_id, "score": 8, "totalQuestions": 10,
        "percentage": 80.0, "timestamp": fixed_utc_now.isoformat(), "quizDate": '2024-01-13'
        # No 'questions' or 'answers' keys here
    }
    mock_collection.add.assert_called_once_with(expected_score_db_data)
    mock_doc_ref_chat.get.assert_called_once()

    # Verify chat update includes *both* scores, new one *without* Q&A
    new_score_entry_for_chat = {
        "score": 8, "totalQuestions": 10, "percentage": 80.0,
        "timestamp": fixed_utc_now.isoformat(), "scoreId": new_score_id
        # No Q&A in this new entry for the chat array
    }
    expected_chat_update_data = {"quiz_scores": [existing_score_entry, new_score_entry_for_chat]}
    mock_doc_ref_chat.update.assert_called_once_with(expected_chat_update_data)


def test_save_score_corrupted_chat_scores_not_list(client):
    # Covers the 'if not isinstance(scores, list):' check when updating chat doc
    user_id = TEST_USER_ID; chat_id = 'chat_corrupted_score_field'; new_score_id = 'new_score_after_corrupt_reset'
    mock_auth_verify(user_id=user_id)
    configure_firestore_add(collection_name='quiz_scores', new_doc_id=new_score_id)
    # Configure get() with corrupted 'quiz_scores' field (not a list)
    configure_firestore_get(chat_exists=True, user_id=user_id, scores="this string is not a list")
    configure_firestore_update() # Mock successful update

    score_data = {'chatId': chat_id, 'score': 7, 'totalQuestions': 10, 'quizDate': '2024-01-14'}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=score_data)

    assert response.status_code == 200
    assert response.json == {"success": True, "scoreId": new_score_id}

    mock_doc_ref_chat.get.assert_called_once()
    # Verify update was called and the score list was reset + new score added
    mock_doc_ref_chat.update.assert_called_once()
    update_args, _ = mock_doc_ref_chat.update.call_args
    updated_scores = update_args[0]['quiz_scores']
    assert isinstance(updated_scores, list) # Ensure it's now a list
    assert len(updated_scores) == 1 # Contains only the new score
    assert updated_scores[0]['scoreId'] == new_score_id


def test_save_score_division_by_zero(client):
    # Covers 'percentage = ... if total_questions > 0 else 0.0'
    user_id = TEST_USER_ID; chat_id = 'chat_div_zero_save_case'; new_score_id = 'new_score_divzero'
    mock_auth_verify(user_id=user_id)
    configure_firestore_add(collection_name='quiz_scores', new_doc_id=new_score_id)
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=[]) # Assume chat exists
    configure_firestore_update()

    # Pass totalQuestions as 0
    score_data = {'chatId': chat_id, 'score': 0, 'totalQuestions': 0, 'quizDate': 'date_div_zero'}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=score_data)

    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['scoreId'] == new_score_id

    # Verify percentage was calculated as 0.0 in the Firestore 'add' call
    mock_collection.add.assert_called_once()
    call_args_add, _ = mock_collection.add.call_args
    assert call_args_add[0]['percentage'] == 0.0

    # Verify percentage was 0.0 in the chat document 'update' call
    expected_chat_update_data = {"quiz_scores": [{
        "score": 0, "totalQuestions": 0, "percentage": 0.0, # Ensure 0.0 here too
        "timestamp": fixed_utc_now.isoformat(), "scoreId": new_score_id
    }]}
    mock_doc_ref_chat.update.assert_called_once_with(expected_chat_update_data)


def test_save_score_firestore_add_exception(client):
    # Covers failure in the 'collection_ref.add(score_data)' step
    user_id = TEST_USER_ID; chat_id = 'chat_for_score_add_fail'
    mock_auth_verify(user_id=user_id)
    error_msg = "Firestore ADD unavailable simulated error"
    # Configure collection.add to fail
    configure_firestore_add(collection_name='quiz_scores', should_fail=True, exception=Exception(error_msg))

    # Ensure subsequent Firestore calls are not made if add fails
    mock_doc_ref_chat.get.reset_mock()
    mock_doc_ref_chat.update.reset_mock()

    score_data = {'chatId': chat_id, 'score': 5, 'totalQuestions': 10, 'quizDate': 'd1_add_fail'}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=score_data)

    assert response.status_code == 500
    assert response.json == {"error": "An unexpected error occurred while saving the score."}
    # Verify add was attempted
    mock_collection.add.assert_called_once()
    # Verify get/update were *not* attempted
    mock_doc_ref_chat.get.assert_not_called()
    mock_doc_ref_chat.update.assert_not_called()

def test_save_score_firestore_update_exception(client):
    # Covers failure in the 'chat_ref.update({"quiz_scores": scores})' step
    user_id = TEST_USER_ID; chat_id = 'chat_for_score_update_fail'; new_score_id = 'score_id_before_update_fail'
    mock_auth_verify(user_id=user_id)
    # Configure score add to succeed
    configure_firestore_add(collection_name='quiz_scores', new_doc_id=new_score_id)
    # Configure chat get to succeed
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=[])
    # Configure chat update to *fail*
    error_msg = "Firestore UPDATE unavailable simulated error"
    configure_firestore_update(should_fail=True, exception=Exception(error_msg))

    score_data = {'chatId': chat_id, 'score': 5, 'totalQuestions': 10, 'quizDate': 'd1_update_fail'}
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=score_data)

    assert response.status_code == 500
    assert response.json == {"error": "An unexpected error occurred while saving the score."}
    # Verify add, get, and update were all attempted
    mock_collection.add.assert_called_once()
    mock_doc_ref_chat.get.assert_called_once()
    mock_doc_ref_chat.update.assert_called_once()


# --- /get_quiz_scores/<chat_id> Route Tests ---
# --- /get_quiz_scores: General Failures & Auth ---
def test_get_scores_db_failure_at_start(client):
    # Test initial check 'if not db:'
    with patch('app.db', None):
        response = client.get('/get_quiz_scores/any_chat_id', headers=create_auth_header())
    assert response.status_code == 503
    assert response.json == {"error": "Database service unavailable"}

def test_get_scores_no_auth(client):
    response = client.get('/get_quiz_scores/any_chat_id')
    assert response.status_code == 401
    assert response.json == {"error": "Unauthorized"}

def test_get_scores_empty_token(client):
    # Test check 'if not token:' after splitting 'Bearer '
    response = client.get('/get_quiz_scores/any_chat_id', headers={'Authorization': 'Bearer '})
    assert response.status_code == 400
    assert response.json['error'] == 'Invalid token format: Token cannot be empty.'

def test_get_scores_invalid_token(client):
    error_msg = "Bad Token Signature Get Scores"; token = "invalid_get_token"
    mock_auth_verify(should_fail=True, exception_type=MockInvalidIdTokenError, exception_msg=error_msg, token_to_check=token)
    response = client.get(f'/get_quiz_scores/any_chat_id', headers=create_auth_header(token))
    assert response.status_code == 401
    assert f"Authentication error: {error_msg}" in response.json["error"]

def test_get_scores_auth_verify_value_error(client):
    token = "get_scores_value_error_token"; mock_auth_verify_value_error(token_to_check=token)
    response = client.get('/get_quiz_scores/any_chat_id', headers=create_auth_header(token))
    assert response.status_code == 400
    assert "Invalid token format: Simulated ValueError during verify" in response.json['error']

# --- /get_quiz_scores: Chat Fetching and Authorization ---
def test_get_scores_chat_not_found(client):
    user_id = TEST_USER_ID; chat_id = 'nonexistent_chat_id_for_get'
    mock_auth_verify(user_id=user_id)
    configure_firestore_get(chat_exists=False) # Mock chat get() as not found
    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())
    assert response.status_code == 404
    assert response.json == {"error": "Chat not found"}
    mock_doc_ref_chat.get.assert_called_once() # Verify get was attempted

def test_get_scores_unauthorized_access(client):
    requesting_user = 'user_making_get_request'
    owner_user = 'actual_owner_of_the_chat_doc'
    chat_id = 'chat_owned_by_someone_else_get'; mock_auth_verify(user_id=requesting_user)
    # Configure get() to return a chat owned by a different user
    configure_firestore_get(chat_exists=True, user_id=owner_user, scores=[])
    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())
    assert response.status_code == 403
    assert response.json == {"error": "Unauthorized access to chat"}
    mock_doc_ref_chat.get.assert_called_once() # Verify get was attempted

# --- /get_quiz_scores: Score Data Handling and Corruption ---
def test_get_scores_success_no_scores_field_in_chat_doc(client):
    # Test case where chat exists but 'quiz_scores' field is missing entirely
    user_id = TEST_USER_ID; chat_id = 'chat_exists_but_no_scores_array'; mock_auth_verify(user_id=user_id)
    # Configure get() with doc_data lacking 'quiz_scores' key
    configure_firestore_get(chat_exists=True, user_id=user_id, doc_data={'userId': user_id, 'filename': 'somefile.txt'})
    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())
    assert response.status_code == 200
    assert response.json == {"success": True, "scores": []} # Defaults to empty list
    mock_doc_ref_chat.get.assert_called_once()

def test_get_scores_corrupted_scores_not_list(client):
    # Covers 'if not isinstance(scores, list):' after fetching chat data
    user_id = TEST_USER_ID; chat_id = 'chat_get_corrupted_scores_field'; mock_auth_verify(user_id=user_id)
    # Configure get() with 'quiz_scores' being a string instead of a list
    configure_firestore_get(chat_exists=True, user_id=user_id, scores="this string is bad data")
    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())
    assert response.status_code == 200
    assert response.json == {"success": True, "scores": []} # Defaults to empty list on corruption
    mock_doc_ref_chat.get.assert_called_once()

def test_get_scores_corrupted_scores_item_not_dict(client):
    # Covers 'if not isinstance(score, dict):' within the processing loop
    user_id = TEST_USER_ID; chat_id = 'chat_get_scores_item_is_not_dict'; mock_auth_verify(user_id=user_id)
    ts = fixed_utc_now.isoformat()
    valid_score = {'scoreId': 's_valid_in_list', 'score': 5, 'totalQuestions': 10, 'percentage': 50.0, 'timestamp': ts}
    corrupt_item = "i_am_a_string_not_a_score_dict" # Invalid item within the list
    scores_with_corrupt = [valid_score, corrupt_item]
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=scores_with_corrupt)
    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())
    assert response.status_code == 200
    assert response.json['success'] is True
    scores_returned = response.json['scores']
    # The corrupted item should be skipped
    assert len(scores_returned) == 1
    assert scores_returned[0]['scoreId'] == 's_valid_in_list'
    # Check default applied correctly to the valid item
    assert scores_returned[0]['answers'] == []
    assert scores_returned[0]['questions'] == []


def test_get_scores_invalid_percentage_type_in_db(client):
    # Covers 'except (ValueError, TypeError):' when converting percentage to float
    user_id = TEST_USER_ID; chat_id = 'chat_get_scores_invalid_percentage_val'; mock_auth_verify(user_id=user_id)
    ts = fixed_utc_now.isoformat()
    # Score entry with a non-numeric percentage
    score_with_bad_percent = {
        'scoreId': 's_bad_percent_val', 'score': 7, 'totalQuestions': 10,
        'percentage': 'eighty-five-percent', # Invalid type for float()
        'timestamp': ts
    }
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=[score_with_bad_percent])
    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())
    assert response.status_code == 200
    assert response.json['success'] is True
    scores_returned = response.json['scores']
    assert len(scores_returned) == 1
    assert scores_returned[0]['scoreId'] == 's_bad_percent_val'
    # Percentage should default to 0.0 due to conversion failure
    assert scores_returned[0]['percentage'] == 0.0

def test_get_scores_corrupted_score_type_in_db(client, capsys):
    """ Covers lines 576-580: Tests handling non-int score/totalQ from DB. """
    user_id = TEST_USER_ID; chat_id = 'chat_get_corrupt_score_int'; mock_auth_verify(user_id=user_id)
    ts = fixed_utc_now.isoformat()
    corrupted_score_entry = {
        'scoreId': 's_corrupt_type',
        'score': 'seven', # Invalid type for int()
        'totalQuestions': None, # Check None handling in int() path
        'percentage': 70.0,
        'timestamp': ts
    }
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=[corrupted_score_entry])

    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())

    assert response.status_code == 200
    assert response.json['success'] is True
    scores_returned = response.json['scores']
    assert len(scores_returned) == 1
    # Check that defaults were applied after failing int() conversion
    assert scores_returned[0]['scoreId'] == 's_corrupt_type'
    assert scores_returned[0]['score'] == 0 # Defaulted from 'seven'
    assert scores_returned[0]['totalQuestions'] == 0 # Defaulted from None
    assert scores_returned[0]['percentage'] == 70.0 # Original percentage kept

    # Check for the warning print due to int conversion failure
    captured = capsys.readouterr()
    assert "Warning: Could not convert score or totalQ to int for item" in captured.out

def test_get_scores_corrupted_answers_type_in_db(client):
    """ Covers line 584: Tests handling non-list 'answers'/'questions' field from DB. """
    user_id = TEST_USER_ID; chat_id = 'chat_get_corrupt_ans_ques_type'; mock_auth_verify(user_id=user_id)
    ts = fixed_utc_now.isoformat()
    corrupted_answers_entry = {
        'scoreId': 's_corrupt_ans', 'score': 8, 'totalQuestions': 10, 'percentage': 80.0, 'timestamp': ts,
        'answers': "this should be a list, but it's a string" # Invalid type
    }
    # Also test corruption for questions list
    corrupted_questions_entry = {
        'scoreId': 's_corrupt_ques', 'score': 9, 'totalQuestions': 10, 'percentage': 90.0, 'timestamp': ts,
        'questions': {"q1": "a1"} # dict, not list
    }
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=[corrupted_answers_entry, corrupted_questions_entry])

    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())

    assert response.status_code == 200
    assert response.json['success'] is True
    scores_returned = response.json['scores']
    # Sort by scoreId to make checking deterministic
    scores_returned.sort(key=lambda x: x.get('scoreId', ''))
    assert len(scores_returned) == 2

    # Find the specific scores to check defaults
    score_ans = scores_returned[0] # Should be s_corrupt_ans
    score_ques = scores_returned[1] # Should be s_corrupt_ques
    assert score_ans['scoreId'] == 's_corrupt_ans'
    assert score_ques['scoreId'] == 's_corrupt_ques'


    # Check that 'answers' was defaulted to an empty list for score_ans
    assert score_ans['answers'] == []
    assert score_ans.get('questions', []) == [] # Ensure questions defaulted too if missing

    # Check that 'questions' was defaulted to an empty list for score_ques
    assert score_ques['questions'] == []
    assert score_ques.get('answers', []) == [] # Ensure answers defaulted too if missing


def test_get_scores_success_with_defaults_applied_and_sorting(client):
    # Test application of defaults for missing fields and sorting by timestamp
    user_id = TEST_USER_ID; chat_id = 'chat_get_needs_defaults_and_sort'; mock_auth_verify(user_id=user_id)
    ts_now = fixed_utc_now
    ts_yesterday = ts_now - datetime.timedelta(days=1)
    ts_two_days_ago = ts_now - datetime.timedelta(days=2)

    # Define score data with various missing fields and timestamps
    score1_db = {'scoreId': 's1_missing_fields', 'score': 5} # Missing totalQ, %, timestamp, Q&A
    score2_db = {'scoreId': 's2_complete_recent', 'score': 8, 'totalQuestions': 10, 'percentage': 80.0, 'timestamp': ts_yesterday.isoformat(), 'questions': ['Q2?'], 'answers': ['A2']}
    score3_db = {'scoreId': 's3_missing_some_older', 'score': 3, 'timestamp': ts_two_days_ago.isoformat()} # Missing totalQ, %, Q&A
    score4_db = {'scoreId': 's4_no_timestamp', 'score': 6, 'totalQuestions': 12} # Missing %, timestamp, Q&A

    # Put them in the list out of order
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=[score1_db, score3_db, score4_db, score2_db])
    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())

    assert response.status_code == 200
    assert response.json['success'] is True
    scores_returned = response.json['scores']
    assert len(scores_returned) == 4

    # --- Assert Sorting Order (newest timestamp first, then those without timestamp) ---
    assert scores_returned[0]['scoreId'] == 's2_complete_recent' # Timestamp: yesterday
    assert scores_returned[1]['scoreId'] == 's3_missing_some_older' # Timestamp: 2 days ago
    sorted_ids_no_timestamp = sorted([scores_returned[2]['scoreId'], scores_returned[3]['scoreId']])
    assert sorted_ids_no_timestamp == ['s1_missing_fields', 's4_no_timestamp']

    # --- Assert Defaults Applied ---
    score1_processed = next(s for s in scores_returned if s['scoreId'] == 's1_missing_fields')
    score3_processed = next(s for s in scores_returned if s['scoreId'] == 's3_missing_some_older')
    score4_processed = next(s for s in scores_returned if s['scoreId'] == 's4_no_timestamp')

    assert score1_processed['totalQuestions'] == 0
    assert score1_processed['percentage'] == 0.0
    assert score1_processed['timestamp'] == ''
    assert score1_processed['questions'] == []
    assert score1_processed['answers'] == []

    assert score3_processed['totalQuestions'] == 0
    assert score3_processed['percentage'] == 0.0
    assert score3_processed['timestamp'] == ts_two_days_ago.isoformat()
    assert score3_processed['questions'] == []
    assert score3_processed['answers'] == []

    assert score4_processed['totalQuestions'] == 12
    assert score4_processed['percentage'] == 0.0
    assert score4_processed['timestamp'] == ''
    assert score4_processed['questions'] == []
    assert score4_processed['answers'] == []


# --- /get_quiz_scores: Firestore Failure ---
def test_get_scores_firestore_get_exception(client):
    # Covers failure during the 'chat_ref.get()' step
    user_id = TEST_USER_ID; chat_id = 'any_chat_get_fail_db_scenario'
    mock_auth_verify(user_id=user_id)
    error_msg = "Firestore GET unavailable simulated get scores"
    # Configure get() to fail
    configure_firestore_get(get_should_fail=True, exception=Exception(error_msg))
    response = client.get(f'/get_quiz_scores/{chat_id}', headers=create_auth_header())
    assert response.status_code == 500
    assert response.json == {"error": "An unexpected error occurred while retrieving scores."}
    # Verify get was attempted
    mock_doc_ref_chat.get.assert_called_once()

# test_app.py

# ... (inside test suite)

def test_save_score_invalid_question_answer_type(client):
    """
    Covers lines ~357-358: Tests sending non-list data for questions/answers.
    """
    user_id = TEST_USER_ID; chat_id = 'chat_bad_qa_type'; new_score_id = 'new_score_bad_qa_type'
    mock_auth_verify(user_id=user_id)
    configure_firestore_add(collection_name='quiz_scores', new_doc_id=new_score_id)
    # Assume chat exists so update is attempted (or doesn't exist, check doesn't matter for this test)
    configure_firestore_get(chat_exists=True, user_id=user_id, scores=[])
    configure_firestore_update()

    # Send 'questions' as a string, 'answers' as a dict
    score_data = {
        'chatId': chat_id, 'score': 5, 'totalQuestions': 10, 'quizDate': 'd1_bad_qa',
        'questions': "This should be a list",
        'answers': {"ans1": "a"}
    }
    response = client.post('/save_quiz_score', headers=create_auth_header(), json=score_data)

    assert response.status_code == 200 # Request should still succeed
    assert response.json['success'] is True
    assert response.json['scoreId'] == new_score_id

    # Verify the saved score data *doesn't* include the invalid questions/answers
    mock_collection.add.assert_called_once()
    call_args_add, _ = mock_collection.add.call_args
    saved_score_data = call_args_add[0]
    assert 'questions' not in saved_score_data
    assert 'answers' not in saved_score_data

    # Verify the chat update data also *doesn't* include the invalid fields
    mock_doc_ref_chat.update.assert_called_once()
    call_args_update, _ = mock_doc_ref_chat.update.call_args
    score_entry_in_chat = call_args_update[0]['quiz_scores'][0]
    assert 'questions' not in score_entry_in_chat
    assert 'answers' not in score_entry_in_chat
    
# --- Stop Global Patchers (Session Scoped) ---
@pytest.fixture(scope="session", autouse=True)
def stop_global_patchers(request):
    """Stop global patchers after the test session finishes."""
    yield # Let the session run
    # Teardown: Stop patchers after all tests in the session are done
    print("\nDEBUG: Stopping global patchers (session scope)...")
    firebase_patcher.stop()
    jwt_patcher.stop()
    time_patcher.stop()
    datetime_patcher_app_module.stop()
    datetime_patcher_global.stop()
    print("DEBUG: Global patchers stopped.")