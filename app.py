from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import sqlite3
import bcrypt
import uuid
import json
from datetime import datetime
import requests
import pdfplumber
from PIL import Image
import pytesseract
from werkzeug.utils import secure_filename
from docx import Document
import tempfile

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
OPENROUTER_API_KEY = "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"
DB_FILE = 'users.db'
HISTORY_FILE = "conversation_history.json"

# Explicitly set the path to Tesseract executable (adjust based on your system)
try:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except Exception as e:
    print(f"Error setting Tesseract path: {e}")

# --- SQLite connection ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Create users table ---
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Load existing history or initialize an empty list
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Save history to file
def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

# Extract text from uploaded files
def extract_text_from_file(file_path, file_name):
    text = ""
    ext = os.path.splitext(file_name.lower())[1]

    try:
        if ext == '.pdf':
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
            try:
                image = Image.open(file_path)
                text = pytesseract.image_to_string(image, lang="aze+eng", config="--psm 6")
            except pytesseract.TesseractNotFoundError:
                return None, "❌ Xəta: Tesseract OCR quraşdırılmayıb və ya PATH-da yoxdur."
            except pytesseract.TesseractError as e:
                return None, f"❌ Xəta: Tesseract OCR işləyə bilmədi: {str(e)}"
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif ext == '.docx':
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            return None, f"❌ Dəstəklənmənən fayl tipi: {ext}"
        return text.strip(), None
    except Exception as e:
        return None, f"❌ Xəta: {str(e)}"

@app.route("/")
def home():
    if 'user_id' in session:
        if 'selected_profile' in session:
            return render_template("chat.html")  # Chat interface
        return render_template("profile.html")  # Profile selection
    return render_template("auth.html")  # Login/Signup page

@app.route("/signup", methods=["POST"])
def signup():
    data = request.form
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    # Validation checks
    if not username or not email or not password:
        return jsonify({"error": "Bütün sahələr doldurulmalıdır."}), 400
    if len(password) < 8:
        return jsonify({"error": "Şifrə minimum 8 xarakter olmalıdır."}), 400
    if not any(c.isupper() for c in password):
        return jsonify({"error": "Şifrədə ən az 1 böyük hərf olmalıdır."}), 400
    if not any(c.isdigit() for c in password):
        return jsonify({"error": "Şifrədə ən az 1 rəqəm olmalıdır."}), 400
    if '@' not in email or '.' not in email:
        return jsonify({"error": "Düzgün e-poçt formatı daxil edin."}), 400
    if len(username) < 3:
        return jsonify({"error": "İstifadəçi adı minimum 3 xarakter olmalıdır."}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                       (username, email, hashed_password))
        conn.commit()
        session['user_id'] = cursor.lastrowid
        session['username'] = username
        return jsonify({"message": "Qeydiyyat uğurlu oldu!", "redirect": url_for("home")})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Bu istifadəçi adı və ya email artıq mövcuddur."}), 400
    finally:
        conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.form
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "E-poçt və şifrə daxil edin."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()

        if row and bcrypt.checkpw(password.encode('utf-8'), row['password']):
            session['user_id'] = row['id']
            session['username'] = row['username']
            return jsonify({"message": "Daxil oldunuz!", "redirect": url_for("home")})
        else:
            return jsonify({"error": "Yanlış e-poçt və ya şifrə."}), 401
    finally:
        conn.close()

@app.route("/logout", methods=["POST"])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('selected_profile', None)
    return jsonify({"message": "Çıxış etdiniz.", "redirect": url_for("home")})

@app.route("/select_profile", methods=["POST"])
def select_profile():
    if 'user_id' not in session:
        return jsonify({"error": "❌ Daxil olun."}), 401
    profile = request.form.get("profile")
    if not profile:
        return jsonify({"error": "Profil seçilməyib."}), 400
    session['selected_profile'] = json.loads(profile)
    return jsonify({"message": "Profil seçildi!", "redirect": url_for("home")})

@app.route("/get", methods=["POST"])
def get_response():
    if 'user_id' not in session:
        return jsonify({"response": "❌ Daxil olun.", "conversation_id": ""}), 401

    user_input = request.form.get("userMessage", "")
    conversation_id = request.form.get("conversationId", str(uuid.uuid4()))

    # Load history from file
    history = load_history()
    # Ensure only the current user's history is used
    user_history = [msg for msg in history if msg.get('user_id') == session['user_id']]
    messages = [
        {"role": "system", "content": "Azərbaycan dilində cavab verən ağıllı chatbot-san."}
    ] + user_history + [{"role": "user", "content": user_input}]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": messages
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    if r.status_code == 200:
        bot_response = r.json()["choices"][0]["message"]["content"]
        # Save to history
        history.append({
            "role": "user",
            "content": user_input,
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "user_id": session['user_id']
        })
        history.append({
            "role": "assistant",
            "content": bot_response,
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "user_id": session['user_id']
        })
        save_history(history)
        return jsonify({"response": bot_response, "conversation_id": conversation_id})
    return jsonify({"response": "❌ Xəta baş verdi.", "conversation_id": conversation_id}), 500

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'user_id' not in session:
        return jsonify({"response": "❌ Daxil olun.", "conversation_id": ""}), 401

    file = request.files.get("file")
    user_input = request.form.get("userMessage", "")
    conversation_id = request.form.get("conversationId", str(uuid.uuid4()))

    if not file:
        return jsonify({"response": "❌ Heç bir fayl göndərilməyib.", "conversation_id": conversation_id}), 400

    filename = secure_filename(file.filename)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        file.save(tmp.name)
        text, error = extract_text_from_file(tmp.name, filename)
    os.remove(tmp.name)

    if error:
        return jsonify({"response": error, "conversation_id": conversation_id}), 400

    prompt = f"{user_input}\n\nFayldan çıxarılan mətn:\n{text}"
    # Load history from file
    history = load_history()
    # Ensure only the current user's history is used
    user_history = [msg for msg in history if msg.get('user_id') == session['user_id']]
    messages = [
        {"role": "system", "content": "Azərbaycan dilində cavab verən ağıllı chatbot-san."}
    ] + user_history + [{"role": "user", "content": prompt}]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": messages
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    if r.status_code == 200:
        bot_response = r.json()["choices"][0]["message"]["content"]
        # Save to history
        history.append({
            "role": "user",
            "content": prompt,
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "user_id": session['user_id']
        })
        history.append({
            "role": "assistant",
            "content": bot_response,
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "user_id": session['user_id']
        })
        save_history(history)
        return jsonify({"response": bot_response, "conversation_id": conversation_id})
    return jsonify({"response": "❌ Xəta baş verdi.", "conversation_id": conversation_id}), 500

@app.route("/history", methods=["GET"])
def get_history():
    if 'user_id' not in session:
        return jsonify({"error": "❌ Daxil olun."}), 401
    history = load_history()
    # Strictly filter history by the current user
    user_history = [msg for msg in history if msg.get('user_id') == session['user_id']]
    return jsonify(user_history)

@app.route("/new_session", methods=["POST"])
def new_session():
    if 'user_id' not in session:
        return jsonify({"error": "❌ Daxil olun."}), 401
    new_conversation_id = str(uuid.uuid4())
    return jsonify({"status": "success", "message": "Yeni sessiya başladı.", "conversation_id": new_conversation_id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
