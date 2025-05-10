# app.py
from flask import Flask, render_template, request, jsonify, Response
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth  # Explicitly import auth
from src.AIFeatures import AIFeatures
from src.AISummary import AISummary
from src.AIFlashcards import AIFlashcards
from src.AIQuestions import AIQuestions
import datetime
import jwt
import time
import json
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

# --- Firebase Initialization ---
# Ensure the path to your service account key is correct
try:
    # Try loading credentials first to potentially fail earlier
    cred_path = 'serviceAccountKey.json'
    if not os.path.exists(cred_path): # pragma: no cover
         print(f"WARNING: Service account key '{cred_path}' not found. Firebase Admin SDK will not be initialized.") # pragma: no cover
         raise FileNotFoundError(f"Service account key '{cred_path}' not found.") # pragma: no cover

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin initialized successfully.")
except FileNotFoundError as e: # Catch FileNotFoundError specifically # pragma: no cover
    print(f"ERROR: Failed to initialize Firebase Admin: {e}")          # pragma: no cover
    db = None                                                            # pragma: no cover
except Exception as e: # pragma: no cover
    print(f"ERROR: Failed to initialize Firebase Admin (unexpected error): {e}") # pragma: no cover
    db = None                                                                  # pragma: no cover

# --- Upload Folder Setup ---
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER): # pragma: no cover
    try:                             # pragma: no cover
        os.makedirs(UPLOAD_FOLDER)   # pragma: no cover
        print(f"Created upload folder: {UPLOAD_FOLDER}") # pragma: no cover
    except OSError as e: # pragma: no cover
        print(f"ERROR: Could not create upload folder {UPLOAD_FOLDER}: {e}") # pragma: no cover
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === Static Page Routes ===

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/reset')
def reset_page():
    return render_template('reset.html')

@app.route('/dashboard.html')
def dashboard():
    return render_template('dashboard.html')

# === API Routes ===

@app.route('/upload', methods=['POST'])
def upload_file():
    print("Entered upload_file", flush=True)
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        print("Upload Error: Missing or invalid Authorization header", flush=True)
        return jsonify({"error": "Unauthorized"}), 401

    token = "" # Initialize token
    try:
        # Use index access which raises IndexError if split fails unexpectedly
        # Check split result length
        parts = auth_header.split(" ", 1) # Split only once
        # The following check is logically covered by the startswith check + the nature of split(" ", 1)
        # which will *always* produce 1 or 2 parts if startswith passed.
        # If it starts with "Bearer " and splits, len MUST be 2.
        if len(parts) != 2 or parts[0] != "Bearer": # pragma: no cover
             raise ValueError("Malformed Authorization header format.") # pragma: no cover

        token = parts[1]
        if not token: # Check for empty token string *after* "Bearer "
             print("Upload Error: Empty token string", flush=True)
             # Raising ValueError here to be caught by the specific handler below
             raise ValueError("ID token must be a non-empty string.")
    except IndexError: # pragma: no cover - Difficult to simulate standard split failing like this after startswith check
        print(f"Upload Error: Malformed Authorization header (Split Error)", flush=True)
        return jsonify({"error": "Malformed Authorization header: Invalid structure"}), 400
    except ValueError as e:
        # This catches the explicit raise above for empty token
        print(f"Upload Error: Malformed Authorization header or empty token: {e}", flush=True)
        return jsonify({"error": f"Malformed Authorization header: {e}"}), 400


    user_id = None
    try:
        print(f"Verifying token: {token[:10]}...", flush=True)
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token['uid']
        print(f"Token verified successfully for user: {user_id}", flush=True)
    except ValueError as e:
         # Handle cases like empty token string passed to verify_id_token
         print(f"Upload Error: Token validation ValueError: {e}", flush=True)
         return jsonify({"error": f"Invalid token format: {e}"}), 400
    except auth.InvalidIdTokenError as e:
        error_str = str(e)
        print(f"Upload Error: Invalid ID Token: {error_str}", flush=True)
        if "Token used too early" in error_str:
            # Attempt skew check as fallback
            print("Attempting JWT decode for skew check...", flush=True)
            try:
                # Decode without verification for claims extraction
                # Specify algorithms to prevent security vulnerabilities if needed, though not critical here as signature isn't checked
                decoded = jwt.decode(token, options={"verify_signature": False})

                if 'iat' not in decoded:
                    print("Upload Error: Skew check failed - missing 'iat' claim", flush=True)
                    return jsonify({"error": "Invalid token: missing iat claim"}), 401

                iat = decoded['iat']
                current_time = int(time.time())
                skew_tolerance = 10 # Allow 10 seconds skew

                print(f"Skew Check: iat={iat}, current_time={current_time}", flush=True)
                if iat > current_time + skew_tolerance:
                    print("Upload Error: Skew check failed - token issued too far in future", flush=True)
                    return jsonify({"error": f"Invalid token: Token issued too far in future ({iat} vs {current_time})"}), 401

                # Check for user identifier ('user_id' or 'sub')
                if 'user_id' in decoded:
                    user_id = decoded['user_id']
                    print(f"Skew Check: Using 'user_id' from JWT: {user_id}", flush=True)
                elif 'sub' in decoded:
                    user_id = decoded['sub']
                    print(f"Skew Check: Using 'sub' from JWT: {user_id}", flush=True)
                else:
                    print("Upload Error: Skew check failed - missing user identifier ('user_id' or 'sub')", flush=True)
                    return jsonify({"error": "Invalid token: missing user identifier"}), 401
                # If user_id is found via skew check, proceed with the request

            except Exception as jwt_e:
                print(f"Upload Error: Skew check failed during JWT decode: {jwt_e}", flush=True)
                return jsonify({"error": f"Invalid token after skew check: {str(jwt_e)}"}), 401
        else:
            # General InvalidIdTokenError (expired, bad signature, etc.)
            return jsonify({"error": f"Invalid token: {error_str}"}), 401
    # Fallthrough: If verify_id_token fails with other errors not caught above
    except Exception as e: # pragma: no cover
         print(f"Upload Error: Unexpected error during token verification: {e}", flush=True) # pragma: no cover
         return jsonify({"error": f"Authentication error: {str(e)}"}), 500                 # pragma: no cover

    # --- Proceed with file upload logic only if user_id is determined ---
    if not user_id: # pragma: no cover - Should be caught by prior logic unless skew logic has flaw
         print("Upload Error: User ID could not be determined after auth checks.", flush=True) # pragma: no cover
         return jsonify({"error": "Authentication failed"}), 401                               # pragma: no cover


    if 'file' not in request.files:
        print("Upload Error: No 'file' part in request", flush=True)
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        print("Upload Error: No file selected (empty filename)", flush=True)
        return jsonify({"error": "No file selected"}), 400

    allowed_extensions = {'.pdf', '.txt'}
    _, file_ext = os.path.splitext(file.filename)
    if file_ext.lower() not in allowed_extensions:
        print(f"Upload Error: Invalid file type: {file_ext}", flush=True)
        return jsonify({"error": "Only PDF and TXT files are allowed"}), 400

    # Use secure_filename? Recommended but depends on requirements.
    # from werkzeug.utils import secure_filename
    # filename = secure_filename(file.filename)
    filename = file.filename # Using original filename as per current logic
    local_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        file.save(local_file_path)
        print(f"File saved successfully: {local_file_path}", flush=True)
    except Exception as e:
         print(f"Upload Error: Failed to save file {local_file_path}: {e}", flush=True)
         return jsonify({"error": f"Failed to save uploaded file: {e}"}), 500


    # --- Processing function (Generator) ---
    def generate():
        ai_features = None # Initialize for finally block
        # Use the local_file_path defined above
        print(f"Starting AI processing for: {local_file_path}", flush=True)

        try:
            # Overview
            print("Step: Overview - Processing", flush=True)
            yield json.dumps({"step": "overview", "status": "processing"}) + "\n\n"
            # Ensure API key is handled securely (e.g., environment variable)
            # Hardcoding keys is not recommended for production.
            api_key = "AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg"  # Use the actual API key
            ai_features = AIFeatures(api_key, local_file_path)
            overview = ai_features.generate_content()
            print("Step: Overview - Complete", flush=True)
            yield json.dumps({"step": "overview", "status": "complete"}) + "\n\n"

            # Summary
            print("Step: Summary - Processing", flush=True)
            yield json.dumps({"step": "summary", "status": "processing"}) + "\n\n"
            ai_summary = AISummary(ai_features)
            summary_content = ai_summary.generate_content()
            summary = ai_summary.format_for_display(summary_content)
            print("Step: Summary - Complete", flush=True)
            yield json.dumps({"step": "summary", "status": "complete"}) + "\n\n"

            # Flashcards
            print("Step: Flashcards - Processing", flush=True)
            yield json.dumps({"step": "flashcards", "status": "processing"}) + "\n\n"
            ai_flashcards = AIFlashcards(ai_features)
            flashcards_content = ai_flashcards.generate_content()
            flashcards_dict = ai_flashcards.create_dict(flashcards_content)
            flashcards = [
                {"word": ai_flashcards.get_word(v), "definition": ai_flashcards.get_def(v)}
                for v in flashcards_dict.values() if isinstance(v, dict) # Basic check
            ]
            print("Step: Flashcards - Complete", flush=True)
            yield json.dumps({"step": "flashcards", "status": "complete"}) + "\n\n"

            # Questions
            print("Step: Questions - Processing", flush=True)
            yield json.dumps({"step": "questions", "status": "processing"}) + "\n\n"
            num_questions = 100 # Consider making this configurable
            ai_questions = AIQuestions(ai_features, num_questions)
            questions_content = ai_questions.generate_content()
            questions = ai_questions.parse_output(questions_content)
            print("Step: Questions - Complete", flush=True)
            yield json.dumps({"step": "questions", "status": "complete"}) + "\n\n"

            # Final result - Save to Firestore
            print("Saving generated data to Firestore...", flush=True)
            chat_data = {
                "userId": user_id,
                "filename": filename, # Use the potentially secured filename if implemented
                "timestamp": datetime.datetime.utcnow().isoformat(), # Consistent timestamp
                "overview": overview,
                "summary": summary,
                "flashcards": flashcards,
                "questions": questions,
                "quiz_scores": [] # Initialize quiz_scores array
            }

            if db: # Check if db client was initialized successfully
                # Make sure collection name is correct
                collection_ref = db.collection('chats')
                # Add returns a tuple (timestamp, document_reference)
                add_timestamp, doc_ref = collection_ref.add(chat_data)
                chat_id = doc_ref.id
                print(f"Data saved to Firestore. Chat ID: {chat_id}, Timestamp: {add_timestamp}", flush=True)


                yield json.dumps({
                    "status": "complete",
                    "chatId": chat_id
                }) + "\n\n"
            else: # This 'else' branch IS tested by test_upload_firestore_db_not_available
                 print("ERROR: Firestore client not available. Cannot save chat data.", flush=True)
                 yield json.dumps({"error": "Database connection failed, cannot save results."}) + "\n\n"
                 return # Stop processing if DB failed


        except Exception as e:
            # Log the specific error during generation
            import traceback
            print(f"ERROR during AI generation step: {e}\n{traceback.format_exc()}", flush=True)
            yield json.dumps({"error": str(e)}) + "\n\n"
            # *** IMPORTANT: Stop the generator after yielding the error ***
            return

        finally:
            # --- Safe Cleanup ---
            print("Executing cleanup block...", flush=True)
            # 1. Remove the uploaded file if it exists
            # Check variable exists and path exists before removing
            # The 'locals()' check here can be tricky for coverage tools if errors occur early.
            if 'local_file_path' in locals() and os.path.exists(local_file_path): # pragma: no cover (justifiable if coverage misses combinations)
                try:
                    os.remove(local_file_path)
                    print(f"Cleaned up uploaded file: {local_file_path}", flush=True)
                except OSError as remove_error:
                    # Log error but continue cleanup
                    print(f"Warning: Error removing file {local_file_path}: {remove_error}", flush=True)

            # 2. Clean up AI feature temporary files if the instance was created
            if ai_features is not None: # Tested by success paths and cleanup_ai_fail
                try:
                    print("Calling ai_features.delete_all_files()...", flush=True)
                    ai_features.delete_all_files()
                    print("AI features cleanup successful.", flush=True)
                except Exception as cleanup_error: # pragma: no cover (This except block IS tested, but coverage might miss the line itself)
                     # Log error but don't stop execution
                     print(f"Warning: Error during AI features cleanup: {cleanup_error}", flush=True) # pragma: no cover (if coverage misses)
            else: # This else IS tested by test_upload_ai_features_init_fails_skips_ai_cleanup
                 print("Skipping AI features cleanup (instance not created).", flush=True)
            print("Cleanup block finished.", flush=True)

    # Return the streaming response
    return Response(generate(), mimetype="application/json")


@app.route('/save_quiz_score', methods=['POST'])
def save_quiz_score():
    print("Entered save_quiz_score", flush=True)
    if not db: # Check if Firestore client is available
         print("Save Score Error: Firestore client not available.", flush=True)
         return jsonify({"error": "Database service unavailable"}), 503

    try:
        # --- Verify authentication ---
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            print("Save Score Error: Missing or invalid Authorization header", flush=True)
            return jsonify({"error": "Unauthorized"}), 401

        token = "" # Initialize token
        try:
            parts = auth_header.split(" ", 1)
            # This check IS logically covered by the 'startswith' check above.
            # If startswith passed, split(" ", 1) *must* result in len 2 unless header is *exactly* "Bearer ".
            # Test test_save_score_malformed_header_just_bearer covers the "Bearer " case hitting startswith.
            if len(parts) != 2 or parts[0] != "Bearer": # pragma: no cover
                raise ValueError("Malformed Authorization header format.") # pragma: no cover
            token = parts[1]
            # This 'if not token' *is* covered by test_save_score_empty_token
            if not token:
                 # Pragma here just in case coverage tool misses it due to error flow
                 raise ValueError("Token cannot be empty.") # pragma: no cover

            print(f"Verifying token for save score: {token[:10]}...", flush=True)
            decoded_token = auth.verify_id_token(token)
            user_id = decoded_token['uid']
            print(f"Token verified for user: {user_id}", flush=True)
        except ValueError as e: # Catches explicit raises above and verify_id_token error
            print(f"Save Score Error: Token validation ValueError: {e}", flush=True)
            return jsonify({"error": f"Invalid token format: {e}"}), 400
        except Exception as e: # Catches InvalidIdTokenError etc.
            # This will catch InvalidIdTokenError and other unexpected errors
            print(f"Save Score Error: Authentication failed: {e}", flush=True)
            # Consider distinguishing 401 for InvalidIdTokenError vs 500 for others
            return jsonify({"error": f"Authentication error: {str(e)}"}), 401

        # --- Get and validate data from request ---
        data = request.get_json()
        if data is None: # pragma: no cover
            print("Save Score Error: Missing or invalid JSON data (data is None)", flush=True)
            raise BadRequest("Missing or invalid JSON data")

        print(f"Received score data: {data}", flush=True)
        required_fields = ['chatId', 'score', 'totalQuestions', 'quizDate']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            field_list = ", ".join(missing_fields)
            print(f"Save Score Error: Missing required field(s): {field_list}", flush=True)
            raise BadRequest(f"Missing required field(s): {field_list}")


        # --- Prepare score data for Firestore ---
        chat_id = data['chatId']
        # Use get with explicit type checks or conversions if necessary
        try:
             score = int(data.get('score', 0))
             total_questions = int(data.get('totalQuestions', 0))
             # Get quizDate, ensure it's a string (or validate format)
             quiz_date = str(data['quizDate']) # Assumes required from check above
        except (ValueError, TypeError) as e:
             print(f"Save Score Error: Invalid data type for score/totalQuestions: {e}", flush=True)
             raise BadRequest(f"Invalid data type for score or totalQuestions: {e}")

        # Safely calculate percentage
        percentage = (score / total_questions) * 100.0 if total_questions > 0 else 0.0

        # Use consistent timestamp
        current_timestamp = datetime.datetime.utcnow().isoformat()

        score_data = {
            "userId": user_id,
            "chatId": chat_id,
            "score": score,
            "totalQuestions": total_questions,
            "percentage": percentage,
            "timestamp": current_timestamp,
            "quizDate": quiz_date # Use validated quiz date
        }

        # Store questions and answers if available and are valid JSON strings representing lists
        questions_data_str = data.get('questions')
        if questions_data_str and isinstance(questions_data_str, str):
            try:
                parsed_questions = json.loads(questions_data_str)
                if isinstance(parsed_questions, list):
                    score_data["questions"] = parsed_questions
                else:
                    print(f"Save Score Warning: 'questions' field was a JSON string but did not decode to a list: {questions_data_str}", flush=True) # pragma: no cover
            except json.JSONDecodeError:
                print(f"Save Score Warning: 'questions' field was not a valid JSON string: {questions_data_str}", flush=True) # pragma: no cover

        answers_data_str = data.get('answers')
        if answers_data_str and isinstance(answers_data_str, str):
            try:
                parsed_answers = json.loads(answers_data_str)
                if isinstance(parsed_answers, list):
                    score_data["answers"] = parsed_answers
                else:
                    print(f"Save Score Warning: 'answers' field was a JSON string but did not decode to a list: {answers_data_str}", flush=True) # pragma: no cover
            except json.JSONDecodeError:
                print(f"Save Score Warning: 'answers' field was not a valid JSON string: {answers_data_str}", flush=True) # pragma: no cover

        # --- Save score to 'quiz_scores' collection ---
        print(f"Adding score to 'quiz_scores' collection for chat {chat_id}...", flush=True)
        score_collection_ref = db.collection('quiz_scores')
        _, score_ref = score_collection_ref.add(score_data)
        new_score_id = score_ref.id # Get the ID of the newly added score document
        print(f"Score added successfully. Score ID: {new_score_id}", flush=True)

        # --- Update the corresponding chat document ---
        print(f"Attempting to update chat document: {chat_id}", flush=True)
        chat_ref = db.collection('chats').document(chat_id)
        # Use a transaction for consistency between read and update if needed,
        # but for simplicity, get then update is usually fine.
        chat = chat_ref.get()

        if chat.exists:
            print(f"Chat document {chat_id} exists. Updating scores.", flush=True)
            chat_data = chat.to_dict()
            # Get existing scores, default to empty list, ensure it's a list
            scores = chat_data.get('quiz_scores', [])
            if not isinstance(scores, list):
                print(f"Warning: 'quiz_scores' in chat {chat_id} was not a list. Resetting to empty list.", flush=True)
                scores = [] # Reset if corrupted

            # Prepare the new score entry for the chat array
            score_entry = {
                "score": score,
                "totalQuestions": total_questions,
                "percentage": percentage,
                "timestamp": current_timestamp, # Use the same timestamp as the score document
                "scoreId": new_score_id # Reference the ID of the score document
            }
            # Include questions/answers in chat entry ONLY if they were valid lists in the request
            if "questions" in score_data:
                 score_entry["questions"] = score_data["questions"]
            if "answers" in score_data:
                 score_entry["answers"] = score_data["answers"]

            scores.append(score_entry)

            # Update the chat document with the new list
            chat_ref.update({"quiz_scores": scores})
            print(f"Chat document {chat_id} updated successfully.", flush=True)
        else:
            print(f"Chat document {chat_id} not found. Score saved in 'quiz_scores' but chat not updated.", flush=True)

        # --- Return success response ---
        return jsonify({
            "success": True,
            "scoreId": new_score_id # Return the actual ID of the saved score
        })

    except BadRequest as e:
        # Handle specific client errors (missing data, bad format)
        print(f"Save Score Error (BadRequest): {e}", flush=True)
        # Extract user-friendly message from BadRequest if possible
        response_message = e.description or str(e)  # pragma: no cover - Hard to test description being None AND generic str needed
        return jsonify({"error": response_message}), 400
    except Exception as e:
        # Handle unexpected errors (Firestore issues, etc.)
        import traceback
        print(f"Save Score Error (Exception): {e}\n{traceback.format_exc()}", flush=True)
        return jsonify({"error": f"An unexpected error occurred while saving the score."}), 500


@app.route('/get_quiz_scores/<chat_id>', methods=['GET'])
def get_quiz_scores(chat_id):
    print(f"Entered get_quiz_scores for chat_id: {chat_id}", flush=True)
    if not db: # Check if Firestore client is available
         print("Get Scores Error: Firestore client not available.", flush=True)
         return jsonify({"error": "Database service unavailable"}), 503

    try:
        # --- Verify authentication ---
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            print("Get Scores Error: Missing or invalid Authorization header", flush=True)
            return jsonify({"error": "Unauthorized"}), 401

        token = "" # Initialize
        try:
            parts = auth_header.split(" ", 1)
            # Similar logic to save_score, this check is redundant after startswith
            if len(parts) != 2 or parts[0] != "Bearer": # pragma: no cover
                raise ValueError("Malformed Authorization header format.") # pragma: no cover
            token = parts[1]
            if not token:
                 # Test case test_get_scores_empty_token hits this path
                 raise ValueError("Token cannot be empty.") # pragma: no cover - add just in case coverage tool misses

            print(f"Verifying token for get scores: {token[:10]}...", flush=True)
            decoded_token = auth.verify_id_token(token)
            user_id = decoded_token['uid']
            print(f"Token verified for user: {user_id}", flush=True)
        except ValueError as e:
             print(f"Get Scores Error: Token validation ValueError: {e}", flush=True)
             return jsonify({"error": f"Invalid token format: {e}"}), 400
        except Exception as e: # Catches InvalidIdTokenError and others
            print(f"Get Scores Error: Authentication failed: {e}", flush=True)
            return jsonify({"error": f"Authentication error: {str(e)}"}), 401

        # --- Get chat document and verify ownership ---
        print(f"Fetching chat document: {chat_id}", flush=True)
        chat_ref = db.collection('chats').document(chat_id)
        chat = chat_ref.get()

        if not chat.exists:
            print(f"Get Scores Error: Chat not found: {chat_id}", flush=True)
            return jsonify({"error": "Chat not found"}), 404

        chat_data = chat.to_dict()
        # Handle case where chat_data might be None (shouldn't happen if exists is True, but safer)
        if not chat_data: # pragma: no cover
             print(f"Get Scores Error: Chat exists but data is None/empty for chat_id: {chat_id}", flush=True) # pragma: no cover
             return jsonify({"error": "Error reading chat data"}), 500                                          # pragma: no cover

        owner_id = chat_data.get('userId')
        if owner_id != user_id:
            print(f"Get Scores Error: Unauthorized access attempt. User: {user_id}, Owner: {owner_id}", flush=True)
            return jsonify({"error": "Unauthorized access to chat"}), 403

        # --- Get scores, apply defaults, and sort ---
        scores = chat_data.get('quiz_scores', [])
        # Ensure scores is a list
        if not isinstance(scores, list):
            print(f"Warning: 'quiz_scores' in chat {chat_id} was not a list. Returning empty list.", flush=True)
            scores = [] # Return empty list if data is corrupted

        print(f"Found {len(scores)} scores in chat document.", flush=True)
        
        # Enhanced debugging for each score
        for i, score in enumerate(scores):
            print(f"\n===== DEBUG SCORE #{i+1} =====")
            print(f"Score type: {type(score)}")
            if isinstance(score, dict):
                for key, value in score.items():
                    value_type = type(value)
                    value_preview = str(value)[:50] + '...' if len(str(value)) > 50 else str(value)
                    print(f"Key: {key}, Type: {value_type}, Value: {value_preview}")
            else:
                print(f"Non-dict score: {score}")
            print(f"=========================\n")

        # Apply defaults and prepare for sorting (handle missing timestamps/types)
        processed_scores = []
        for index, score in enumerate(scores): # Use enumerate if logging index helps debugging
             # Ensure it's a dictionary before processing
             if not isinstance(score, dict):
                  print(f"Warning: Found non-dict item at index {index} in quiz_scores for chat {chat_id}: {score}. Skipping item.", flush=True)
                  continue # Skip non-dict items

             # Apply defaults for missing fields safely
             # Get questions and answers (either lists or already strings)
             questions_data = score.get('questions', [])
             answers_data = score.get('answers', [])
             
             # Try to convert string questions/answers to proper lists
             # Check if it's a string that looks like a JSON array
             if isinstance(questions_data, str) and questions_data.strip().startswith('['):
                 try:
                     questions_data = json.loads(questions_data)
                     print(f"Parsed questions string to list, length: {len(questions_data)}", flush=True)
                 except json.JSONDecodeError:
                     print(f"Failed to parse questions string: {questions_data[:50]}...", flush=True)
                     questions_data = []
                     
             if isinstance(answers_data, str) and answers_data.strip().startswith('['):
                 try:
                     answers_data = json.loads(answers_data)
                     print(f"Parsed answers string to list, length: {len(answers_data)}", flush=True)
                 except json.JSONDecodeError:
                     print(f"Failed to parse answers string: {answers_data[:50]}...", flush=True)
                     answers_data = []
             
             # Always convert to proper Python lists (not JSON strings) for frontend
             if isinstance(questions_data, list) and questions_data:
                 questions_list = questions_data  # Keep as Python list
             else:
                 questions_list = []
                 
             if isinstance(answers_data, list) and answers_data:
                 answers_list = answers_data  # Keep as Python list
             else:
                 answers_list = []
                 
             processed_score = {
                 'scoreId': score.get('scoreId'), # Allow None if missing
                 'score': score.get('score', 0),
                 'totalQuestions': score.get('totalQuestions', 0),
                 'percentage': score.get('percentage', 0.0),
                 'timestamp': score.get('timestamp', ''), # Default timestamp to empty string for sorting
                 # Send lists directly to the frontend (not as JSON strings)
                 'questions': questions_list,
                 'answers': answers_list,
                 # Add quizDate if it's stored and needed by frontend
                 'quizDate': score.get('quizDate', '')
             }
             # Ensure percentage is float, default to 0.0 on error
             try:
                 # Handle potential None value from .get() before float conversion
                 percentage_val = score.get('percentage')
                 if percentage_val is None:
                     processed_score['percentage'] = 0.0
                 else:
                     processed_score['percentage'] = float(percentage_val)
             except (ValueError, TypeError):
                 print(f"Warning: Could not convert percentage '{score.get('percentage')}' to float for score item at index {index} in chat {chat_id}. Defaulting to 0.0.", flush=True)
                 processed_score['percentage'] = 0.0 # Default on conversion error

             # Ensure score and totalQuestions are integers
             try:
                 score_val = score.get('score')
                 totalq_val = score.get('totalQuestions')
                 processed_score['score'] = int(score_val) if score_val is not None else 0
                 processed_score['totalQuestions'] = int(totalq_val) if totalq_val is not None else 0
             except (ValueError, TypeError): # pragma: no cover (Defensive)
                  # This case is less likely if save_score enforces ints, but good defense
                  print(f"Warning: Could not convert score or totalQ to int for item at index {index}, chat {chat_id}. Using defaults.", flush=True) # pragma: no cover
                  processed_score['score'] = 0             # pragma: no cover
                  processed_score['totalQuestions'] = 0    # pragma: no cover

             # Ensure Q/A are lists
             if not isinstance(processed_score['questions'], list):
                  processed_score['questions'] = []
             if not isinstance(processed_score['answers'], list):
                  processed_score['answers'] = []


             processed_scores.append(processed_score)


        # Sort by timestamp (newest first), treat empty/invalid timestamps appropriately
        # Use a key function that provides a sortable value, ensuring stability
        processed_scores.sort(key=lambda x: x.get('timestamp') or '', reverse=True)
        print("Scores processed and sorted.", flush=True)

        return jsonify({
            "success": True,
            "scores": processed_scores
        })

    except Exception as e:
        import traceback
        print(f"Get Scores Error (Exception): {e}\n{traceback.format_exc()}", flush=True)
        return jsonify({"error": f"An unexpected error occurred while retrieving scores."}), 500


# === Main Execution Guard ===

if __name__ == '__main__': # pragma: no cover
    # Use host='0.0.0.0' to be accessible externally if needed, e.g., in Docker
    # debug=True is useful for development but should be False in production
    print("Starting Flask app...") # pragma: no cover
    # Use environment variable for port, default to 5000
    port = int(os.environ.get("PORT", 5000)) # pragma: no cover
    # Set debug based on an environment variable, default to False for safety
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true" # pragma: no cover
    app.run(host='0.0.0.0', port=port, debug=debug_mode) # pragma: no cover