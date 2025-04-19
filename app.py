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

app = Flask(__name__)

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

@app.route('/upload', methods=['POST'])
def upload_file():
    print("Entered upload_file", flush=True)
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        token = auth_header.split("Bearer ")[1]
    except IndexError:
        return jsonify({"error": "Malformed Authorization header"}), 401

    try:
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token['uid']
    except auth.InvalidIdTokenError as e:
        if "Token used too early" in str(e):
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                if 'iat' not in decoded:
                    return jsonify({"error": "Invalid token: missing iat claim"}), 401
                iat = decoded['iat']
                current_time = int(time.time())
                skew_tolerance = 10
                
                if iat > current_time + skew_tolerance:
                    return jsonify({"error": f"Invalid token: Token issued too far in future ({iat} vs {current_time})"}), 401
                
                # Use 'user_id' or 'sub' instead of 'uid'
                if 'user_id' not in decoded and 'sub' not in decoded:
                    return jsonify({"error": "Invalid token: missing user identifier"}), 401
                user_id = decoded.get('user_id', decoded['sub'])  # Prefer 'user_id', fallback to 'sub'
            except Exception as e:
                return jsonify({"error": f"Invalid token after skew check: {str(e)}"}), 401
        else:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401

    # Proceed with file upload logic
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.txt')):
        return jsonify({"error": "Only PDF and TXT files are allowed"}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    print('File saved:', file_path, flush=True)

    def generate():
        # Initialize variables that need cleanup
        ai_features = None
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        
        try:
            # Overview
            yield json.dumps({"step": "overview", "status": "processing"}) + "\n\n"
            ai_features = AIFeatures("AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg", file_path)
            overview = ai_features.generate_content()
            yield json.dumps({"step": "overview", "status": "complete"}) + "\n\n"
            
            # Summary
            yield json.dumps({"step": "summary", "status": "processing"}) + "\n\n"
            ai_summary = AISummary(ai_features)
            summary_content = ai_summary.generate_content()
            summary = ai_summary.format_for_display(summary_content)
            yield json.dumps({"step": "summary", "status": "complete"}) + "\n\n"
            
            # Flashcards
            yield json.dumps({"step": "flashcards", "status": "processing"}) + "\n\n"
            ai_flashcards = AIFlashcards(ai_features)
            flashcards_content = ai_flashcards.generate_content()
            flashcards_dict = ai_flashcards.create_dict(flashcards_content)
            flashcards = [{"word": ai_flashcards.get_word(v), "definition": ai_flashcards.get_def(v)} for v in flashcards_dict.values()]
            yield json.dumps({"step": "flashcards", "status": "complete"}) + "\n\n"
            
            # Questions
            yield json.dumps({"step": "questions", "status": "processing"}) + "\n\n"
            num_questions = 100
            ai_questions = AIQuestions(ai_features, num_questions)
            questions_content = ai_questions.generate_content()
            questions = ai_questions.parse_output(questions_content)
            yield json.dumps({"step": "questions", "status": "complete"}) + "\n\n"

            # Final result
            chat_data = {
                "userId": user_id,
                "filename": file.filename,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "overview": overview,
                "summary": summary,
                "flashcards": flashcards,
                "questions": questions
            }
            doc_ref = db.collection('chats').add(chat_data)[1]
            
            yield json.dumps({
                "status": "complete",
                "chatId": doc_ref.id
            }) + "\n\n"

        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n\n"
        finally:
            # Safe cleanup - check if variables exist first
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            if ai_features is not None:  # Explicit None check
                ai_features.delete_all_files()

    return Response(generate(), mimetype="application/json")

if __name__ == '__main__':
    app.run(debug=True)
