from flask import Flask, render_template, request, jsonify
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth  # Explicitly import auth
from src.AIFeatures import AIFeatures
from src.AISummary import AISummary
from src.AIFlashcards import AIFlashcards
from src.AIQuestions import AIQuestions
import datetime

app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Directory for file uploads
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Your Google Gemini API key (replace with your actual key)
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"

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
    print('Upload endpoint called')  # Debug: Confirm endpoint is reached
    auth_header = request.headers.get('Authorization')
    print('Received Authorization header:', auth_header)
    if not auth_header or not auth_header.startswith('Bearer '):
        print('No valid Bearer token found')
        return jsonify({"error": "Unauthorized"}), 401
    
    token = auth_header.split("Bearer ")[1]
    print('Token received:', token)
    try:
        decoded_token = auth.verify_id_token(token)
        print('Decoded token:', decoded_token)
        user_id = decoded_token['uid']
    except Exception as e:
        print('Token verification failed:', str(e))
        return jsonify({"error": "Invalid token: " + str(e)}), 401

    if 'file' not in request.files:
        print('No file part in request')
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        print('No file selected')
        return jsonify({"error": "No file selected"}), 400
    
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.txt')):
        print('Invalid file type:', file.filename)
        return jsonify({"error": "Only PDF and TXT files are allowed"}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    print('File saved:', file_path)

    try:
        ai_features = AIFeatures("AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg", file_path)
        overview = ai_features.generate_content()
        ai_summary = AISummary(ai_features)
        summary = ai_summary.generate_content()

        ai_flashcards = AIFlashcards(ai_features)
        flashcards_content = ai_flashcards.generate_content()
        flashcards_dict = ai_flashcards.create_dict(flashcards_content)
        flashcards = [{"word": ai_flashcards.get_word(v), "definition": ai_flashcards.get_def(v)} for v in flashcards_dict.values()]

        num_questions = 5
        ai_questions = AIQuestions(ai_features, num_questions)
        questions_content = ai_questions.generate_content()
        questions = ai_questions.parse_output(questions_content)

        ai_features.delete_all_files()
        print('AI processing completed')

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
        chat_id = doc_ref.id
        print('Chat stored in Firestore, ID:', chat_id)

        os.remove(file_path)
        print('Local file deleted')

        return jsonify({"chatId": chat_id}), 200

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print('Processing error:', str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print('Starting Flask app...')
    app.run(debug=True)