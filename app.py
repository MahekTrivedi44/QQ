import sqlite3
import os
import bcrypt
import requests
from flask import Flask, request, session, jsonify, g, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from fpdf import FPDF
import tempfile
import threading
import time
import html
import re
from chatbot import ask_groq  # Import the ask_groq function from chatbot.py
from db import init_db, get_db, close_db # Import database functions
from auth import create_user, verify_user # Import auth functions


# --- Flask App Setup ---
app = Flask(__name__, static_folder='assets')
app.secret_key = "supercutesecret"  # IMPORTANT: Use a strong, random secret key in production!
CORS(app, supports_credentials=True)

# Register the teardown function here
app.teardown_appcontext(close_db)

# Initialize DB on startup (optional)
init_db()

# --- Helper for Conversation Management ---
def get_or_create_default_conversation(user_id):
    db = get_db()
    if "current_conversation_id" in session and session["current_conversation_id"]:
        conv = db.execute("SELECT id FROM conversations WHERE id = ? AND user_id = ?",
                          (session["current_conversation_id"], user_id)).fetchone()
        if conv:
            return session["current_conversation_id"]

    cursor = db.execute("INSERT INTO conversations (user_id, title) VALUES (?, ?)",
                        (user_id, f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
    new_conv_id = cursor.lastrowid
    db.commit()
    return new_conv_id

def delete_file_later(path, delay=300):
    """Deletes a file after a specified delay."""
    def _delete():
        time.sleep(delay)
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"🧹 Deleted temp file: {path}")
        except Exception as e:
            print(f"Error deleting file {path}: {e}")
    if path:
        threading.Thread(target=_delete, daemon=True).start()

# --- PDF Generation Classes and Helpers ---
def safe_multicell(pdf_obj, line):
    """Safely add a multi-line cell to a PDF, handling potential encoding errors."""
    try:
        cleaned = re.sub(r'[^\x20-\x7E\n\r]', '', line)  # Keep basic printable chars and newlines
        page_width = pdf_obj.w - 2 * pdf_obj.l_margin
        pdf_obj.multi_cell(page_width, 6, cleaned)
    except Exception as e:
        print(f"⚠️ PDF error in safe_multicell: {e} for line: {line[:50]}...")
        truncated = cleaned[:200] + "..." if len(cleaned) > 200 else cleaned
        try:
            pdf_obj.multi_cell(page_width, 6, truncated)
        except Exception as e_fallback:
            print(f"⚠️ PDF fallback multi_cell also failed: {e_fallback}")

class CustomPDF(FPDF):
    """A custom PDF class to handle headers and Unicode fonts."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Assumes you have DejaVuSans.ttf in your project directory
            self.add_font('DejaVuSans', '', 'DejaVuSans.ttf')
            self.add_font('DejaVuSans', 'B', 'DejaVuSans-Bold.ttf')
            self.set_font('DejaVuSans', '', 10)
        except RuntimeError:
            print("Warning: DejaVu fonts not found. Falling back to Arial.")
            self.set_font('Arial', '', 10)
    def ensure_space(self, min_height=15):
        """Start a new page if there's not enough vertical space left."""
        if self.get_y() + min_height > self.page_break_trigger:
            self.add_page()
    def header(self):
        try:
            self.set_font('DejaVuSans', 'B', 15)
        except RuntimeError:
            self.set_font('Arial', 'B', 15)
        safe_multicell(self, "💖 Query Quokka Learning Material 💖")
        self.ln(10)

    def chapter_title(self, title):
        try:
            self.set_font('DejaVuSans', 'B', 12)
        except RuntimeError:
            self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        from fpdf.enums import XPos, YPos
        self.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
        self.ln(4)

    def chapter_body(self, body):
        try:
            self.set_font('DejaVuSans', '', 10)
        except RuntimeError:
            self.set_font('Arial', '', 10)
        safe_multicell(self, body)
        self.ln(6)


# --- HTML Flashcard Generation ---
def generate_flashcards_html(flashcards_text):
    """Generates an HTML string for interactive flashcards."""
    cards_html = []
    current_topic = ""
    current_question_text = None

    lines = flashcards_text.split('\n')
    for line in lines:
        line = line.strip()
        question_match = re.match(r'Q:\s*(.*)', line, re.IGNORECASE)
        answer_match = re.match(r'A:\s*(.*)', line, re.IGNORECASE)

        if line.startswith("=== ") and line.endswith(" ==="):
            current_topic = html.escape(line.replace("===", "").strip())
        elif question_match:
            current_question_text = question_match.group(1).strip()
        elif answer_match and current_question_text is not None:
            escaped_question = html.escape(current_question_text)
            escaped_answer = html.escape(answer_match.group(1).strip())
            cards_html.append(f"""
            <div class="flashcard-container">
                <div class="flashcard" onclick="this.classList.toggle('flipped');">
                    <div class="flashcard-front"><p class="card-question">{escaped_question}</p></div>
                    <div class="flashcard-back"><p class="card-answer">{escaped_answer}</p></div>
                </div>
                <div class="flashcard-topic">{current_topic}</div>
            </div>
            """)
            current_question_text = None

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Query Quokka Flashcards</title>
    <link href="https://fonts.googleapis.com/css2?family=Love+Ya+Like+A+Sister&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Arial', sans-serif; background-color: #FFFFFF; display: flex; flex-direction: column; align-items: center; padding: 20px; }}
        h1 {{ color: #6c493b; font-family: 'Love Ya Like A Sister', cursive; }}
        /* Style for the logo image */
        .logo-container {{
            text-align: center; /* Center the image */
            margin-bottom: 20px; /* Add some space below the logo */
        }}
        .logo-container img {{
            max-width: 200px; /* Adjust the size as needed */
            height: auto;
        }}
        .flashcards-grid {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }}
        .flashcard-container {{ perspective: 1000px; width: 300px; height: 200px; margin-bottom: 20px; }}
        .flashcard {{ width: 100%; height: 100%; position: absolute; transform-style: preserve-3d; transition: transform 0.6s; border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); cursor: pointer; }}
        .flashcard.flipped {{ transform: rotateY(180deg); }}
        .flashcard-front {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; display: flex; justify-content: center; align-items: center; padding: 15px; box-sizing: border-box; box-shadow: 0 0 15px 5px rgba(108, 73, 59, 0.5) !important; border-radius: 20px; text-align: center; font-family: 'Love Ya Like A Sister', cursive; font-size: 1.2em; color: #ffffff; }} /* Text color for cards */
        .flashcard-back {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; display: flex; justify-content: center; align-items: center; padding: 15px; box-sizing: border-box; box-shadow: 0 0 15px 5px rgba(108, 73, 59, 0.5) !important; border-radius: 20px; text-align: center; font-family: 'Love Ya Like A Sister', cursive; font-size: 1.2em; color: #ffffff; }} /* Text color for cards */    
        .flashcard-front {{ background-color: #b77a5a;}} /* Lightest background, medium border */
        .flashcard-back {{ background-color: #6c493b; transform: rotateY(180deg); }} /* Medium background, darkest border */
        .flashcard-topic {{ position: absolute; bottom: -25px; left: 0; right: 0; text-align: center; font-family: 'Love Ya Like A Sister', cursive; font-size: 0.9em; color: #6c493b; font-weight: bold; }} /* Darkest text for topic */
    </style>
</head>
<body>
    <div class="logo-container">
        <img src="https://github.com/MahekTrivedi44/logo/blob/main/logo.png?raw=true" alt="Query Quokka Logo">
    </div>
    <div class="flashcards-grid">{''.join(cards_html)}</div>
</body>
</html>
"""

# --- Flask Routes ---
@app.route("/signup", methods=["POST"])
# def signup():
#     data = request.json
#     if not create_user(data.get("username"), data.get("password")):
#         return jsonify({"success": False, "message": "Username already exists or server error."})
#     return jsonify({"success": True, "message": "Signup successful!"})
def signup():
    data = request.json
    success, message = create_user(data.get("username"), data.get("password"))
    if not success:
        return jsonify({"success": False, "message": message})
    return jsonify({"success": True, "message": "Signup successful! You can now log in."})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    uid = verify_user(data.get("username"), data.get("password"))
    if uid:
        session["user_id"] = uid
        session.permanent = data.get("remember_me", False)
        if session.permanent:
            app.permanent_session_lifetime = timedelta(hours=24)
        session["current_conversation_id"] = get_or_create_default_conversation(uid)
        return jsonify({"success": True, "message": "Login successful!"})
    return jsonify({"success": False, "message": "Invalid credentials."})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully!"})


@app.route("/check_login_status", methods=["GET"])
def check_login_status():
    return jsonify({"logged_in": "user_id" in session})


@app.route("/new_conversation", methods=["POST"])
def new_conversation():
    if "user_id" not in session:
        return jsonify({"success": False, "response": "Please log in first."}), 401
    
    user_id = session["user_id"]
    db = get_db()
    
    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    new_title = f"New Chat {timestamp_str}"

    cursor = db.execute("INSERT INTO conversations (user_id, title) VALUES (?, ?)", (user_id, new_title))
    new_conv_id = cursor.lastrowid
    db.commit() 
    
    # --- ADD THIS LINE ---
    time.sleep(0.05) # Add a small delay (e.g., 50 milliseconds)
    # ---------------------
    
    session["current_conversation_id"] = new_conv_id
    print(f"Backend /new_conversation: Created new conversation with ID {new_conv_id}")
    return jsonify({"success": True, "conversation_id": new_conv_id})

@app.route("/get_current_chat_history", methods=["GET"])
def get_current_chat_history():
    if "user_id" not in session:
        return jsonify({"success": False, "history": []})

    user_id = session["user_id"]
    conv_id = get_or_create_default_conversation(user_id)
    session["current_conversation_id"] = conv_id
    
    db = get_db()
    messages = db.execute("SELECT message, response, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
                          (conv_id,)).fetchall()
    history = [[m["message"], m["response"]] for m in messages]
    return jsonify({"success": True, "history": history, "current_conversation_id": conv_id})

@app.route('/summarize_chat', methods=['POST'])
def summarize_chat():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 401
    
    data = request.json
    conversation_history = data.get('history', [])
    
    messages_for_groq = []
    for h_msg in conversation_history:
        messages_for_groq.append({"role": "user", "content": h_msg["message"]})
        messages_for_groq.append({"role": "assistant", "content": h_msg["response"]})

    summarize_prompt = (
        "You are an academic tutor and curriculum writer tasked with generating a detailed, structured learning report from the following conversation. "
        "Your objective is to extract all educational content, group it by topic, and provide an in-depth explanation of each topic as if teaching it to a student. "
        "Do not summarize the conversation or reference specific dialogue. Instead, reconstruct the content into a clear, well-organized report that fully explains each subject discussed. "
        "Include additional context, definitions, and examples where needed. Fill in any gaps where a concept was mentioned but not thoroughly explained. "
        "If practical examples, case studies, **code**, logic, syntax, functions, methods, pseudocode, scenarios, or analogies were discussed in the conversation, include them in the relevant sections. "
        "If such examples were not provided, **GENERATE appropriate examples**, illustrations, or simplified explanations to help reinforce understanding. These can be from real-world situations, sample problems, or thought experiments. "
        "Where helpful, include memory techniques, mnemonics, diagrams (as descriptions), or analogies to enhance understanding and retention.\n\n"
        
        "For formatting: "
        "Use plain text only, EXCEPT for the subheadings (Explanation, Examples / Applications, Tips / Mnemonics) which MUST be bolded as shown in the structure below. Do not use other markdown like asterisks (*), backticks (`), or other symbols for emphasis. "
        "For lists, use numbered bullets like '1.', '2.', '3.' instead of asterisks or dashes. "
        "Ignore small talk, greetings, or tool usage unless directly relevant to the learning content.\n\n"
        
        "Important: Structure the report, exactly as below, and ensure EVERY topic (including any introductory sections) contains ALL three subsections. If content is not directly available from the conversation for 'Examples / Applications' or 'Tips / Mnemonics', you MUST generate relevant content for those sections:\n\n"
        "=== [Topic Title] ===\n"
        "**Explanation:**\nFull teaching-style explanation here.\n\n"
        "**Examples / Applications:**\nReal-world or code examples (if relevant). If no direct examples from the conversation, generate new ones.\n\n"
        "**Tips / Mnemonics:**\nUseful memory aids or tricks. If no direct tips/mnemonics from the conversation, generate new ones.\n\n"
        "Conversation:\n" +
        "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages_for_groq])
    )
    messages_for_groq.append({"role": "user", "content": summarize_prompt})
    
    summary_text = ask_groq(messages_for_groq)
    summary_text = re.sub(r'\*\*(.*?)\*\*', r'\1', summary_text)  # strip **bold**
    summary_text = re.sub(r'\_(.*?)\_', r'\1', summary_text)      # strip _italic_
    summary_text = re.sub(r'\`(.*?)\`', r'\1', summary_text)      # strip `code`
    summary_text = re.sub(r'^\s+', '', summary_text, flags=re.MULTILINE)  # strip leading spaces on all lines
    print(f"Generated summary:\n{summary_text}")  

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
            pdf = CustomPDF()
            pdf.add_page()
            section_pattern = re.compile(r"(Explanation|Examples / Applications|Tips / Mnemonics)[:：]?\s*(.*)", re.IGNORECASE)
            last_section = None
            seen_lines = set()

            for line in summary_text.split('\n'):
                line = line.strip()
                if not line or line in seen_lines:
                    continue

                seen_lines.add(line)

                # === Section titles ===
                if line.startswith("=== ") and line.endswith(" ==="):
                    pdf.ensure_space(20)
                    pdf.chapter_title(line.replace("===", "").strip())
                    pdf.ln(4)
                    continue

                # === Sub-section labels like Explanation: ===
                match = section_pattern.match(line)
                if match:
                    label = match.group(1).strip()
                    content = match.group(2).strip()

                    # Avoid double printing label headers
                    if last_section == label:
                        continue
                    last_section = label

                    pdf.ensure_space(15)
                    pdf.set_font('', 'B')
                    safe_multicell(pdf, label + ":")
                    pdf.set_font('', '')
                    if content:
                        safe_multicell(pdf, content)
                    pdf.ln(3)
                    continue

                # Clean up bad front spacing and asterisks
                line = re.sub(r'^\*+\s*', '• ', line)
                line = re.sub(r'\s{2,}', ' ', line)

                pdf.set_font('', '')
                pdf.ensure_space(10)
                safe_multicell(pdf, line)
                pdf.ln(2)

            pdf.output(temp.name)
            file_path = temp.name
        
        delete_file_later(file_path)
        return jsonify({"success": True, "file_path": file_path})
    except Exception as e:
        app.logger.error(f"Error creating summary file: {e}")
        return jsonify({"success": False, "message": f"Error creating summary file: {e}"}), 500


@app.route('/generate_flashcards', methods=['POST'])
def generate_flashcards():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 401
    
    data = request.json
    conversation_history = data.get('history', [])
    file_format = data.get("format", "pdf")

    messages_for_groq = []
    for h_msg in conversation_history:
        messages_for_groq.append({"role": "user", "content": h_msg["message"]})
        messages_for_groq.append({"role": "assistant", "content": h_msg["response"]})

    flashcard_prompt = (
            "You are an instructional designer and subject matter expert. Your task is to generate high-quality educational flashcards from the following conversation. "
            "Ignore greetings, social chat, and tool-related comments. Focus solely on extracting learning content from the conversation, even if it spans multiple topics. "
            "Group flashcards by topic, and ensure each card tests important concepts, definitions, processes, or problem-solving methods discussed. "
            "Where relevant, include flashcards for concepts that were only briefly mentioned or implied but are necessary for complete understanding. "
            "\n\nFlashcards must include a **mix** of question types depending on the subject and content:\n"
            "- Conceptual: definitions, distinctions, 'what' and 'why'\n"
            "- Applied: case studies, real-world examples, diagnosis-based, analysis questions\n"
            "- Practical: code snippets, pseudo-scenarios, data interpretation, step-by-step problems\n"
            "- Process-oriented: questions about sequences, protocols, workflows\n"
            "- Mnemonics & memory hacks: where helpful, embed memory aids or analogies\n"
            "Use simple yet precise language for both questions and answers. Provide mnemonics, analogies, or real-world examples where they can enhance understanding or retention. "
            "Use plain text only. Do not use markdown (e.g., no **bold**, *, or backticks). "
            "For lists, use numbered bullets like '1.', '2.', '3.' instead of asterisks or dashes. "
            "Do not reference specific user messages — focus on converting the knowledge into effective active recall material.\n\n"
            "Format the output as follows:\n\n"
            "=== [Topic Name] ===\n"
            "Q: ...\n"
            "A: ... [Answer in no more than 190 characters total. If the full explanation is longer, split it into multiple Q&A pairs to keep each answer within the limit.]\n\n"
            "Conversation:\n" +
            "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages_for_groq])
        )
    messages_for_groq.append({"role": "user", "content": flashcard_prompt})

    flashcards_text = ask_groq(messages_for_groq)
    
    file_path = None
    try:
        if file_format == "pdf":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
                pdf = CustomPDF()
                pdf.add_page()
                for line in flashcards_text.split('\n'):
                    if line.startswith("=== ") and line.endswith(" ==="):
                        pdf.chapter_title(line.replace("===", "").strip())
                    elif line.startswith("Q:") or line.startswith("A:"):
                        pdf.set_font('', 'B' if line.startswith("Q:") else '')
                        safe_multicell(pdf, line)
                        pdf.ln(2)
                pdf.output(temp.name)
                file_path = temp.name
        
        elif file_format.lower() in ["html", "html (interactive)"]:
             with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as temp:
                html_content = generate_flashcards_html(flashcards_text)
                temp.write(html_content)
                file_path = temp.name
        
        if file_path:
            delete_file_later(file_path)
            return jsonify({"success": True, "file_path": file_path})
        else:
            return jsonify({"success": False, "message": "Unsupported file format."}), 400

    except Exception as e:
        app.logger.error(f"Error creating flashcard file: {e}")
        return jsonify({"success": False, "message": f"Error creating flashcard file: {e}"}), 500


@app.route('/files/<path:filename>')
def download_file(filename):
    # Serve files from the system's temporary directory.
    return send_from_directory(tempfile.gettempdir(), filename, as_attachment=True)


# @app.route("/get_conversations", methods=["GET"])
# def get_conversations():
#     if "user_id" not in session:
#         return jsonify({"success": False, "conversations": []})
    
#     user_id = session["user_id"]
#     db = get_db()
#     convs = db.execute(
#         """
#         SELECT c.id, (SELECT message FROM messages WHERE conversation_id = c.id ORDER BY timestamp ASC LIMIT 1) as preview
#         FROM conversations c
#         WHERE c.user_id = ? AND (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) > 0
#         ORDER BY (SELECT MAX(timestamp) FROM messages WHERE conversation_id = c.id) DESC
#         """, (user_id,)
#     ).fetchall()
    
#     conv_list = [{"id": c["id"], "title": c["preview"][:40] + "..." if c["preview"] and len(c["preview"]) > 40 else c["preview"] or "Chat"} for c in convs]
#     print(f"Backend /get_conversations: Conversations fetched from DB: {conv_list}") # ADD THIS
#     return jsonify({"success": True, "conversations": conv_list})

# In APPX.py, modify the get_conversations function:
@app.route("/get_conversations", methods=["GET"])
def get_conversations():
    print(f"Backend /get_conversations: Session contents: {session}")
    if "user_id" not in session:
        print("Backend /get_conversations: User not in session, returning empty list.")
        return jsonify({"success": False, "conversations": []})
    
    user_id = session["user_id"]
    print(f"Backend /get_conversations: User ID from session: {user_id}")
    db = get_db()
    convs = db.execute(
        """
        SELECT c.id, c.title, (SELECT message FROM messages WHERE conversation_id = c.id ORDER BY timestamp ASC LIMIT 1) as preview
        FROM conversations c
        WHERE c.user_id = ? AND (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) > 0
        ORDER BY (SELECT MAX(timestamp) FROM messages WHERE conversation_id = c.id) DESC
        """, (user_id,)
    ).fetchall()
    
    # Modify this line to use c["title"] for the primary display
    conv_list = []
    for c in convs:
        display_title = c["title"] # Use the conversation's title
        if c["preview"] and c["preview"] != display_title: # If preview is different, append it
            display_title = f"{display_title} - {c['preview'][:30]}..." if len(c['preview']) > 30 else f"{display_title} - {c['preview']}"
        conv_list.append({"id": c["id"], "title": display_title})
        
    print(f"Backend /get_conversations: Conversations fetched from DB: {conv_list}")
    return jsonify({"success": True, "conversations": conv_list})

# Also, ensure your schema.sql creates a 'title' column in the conversations table,
# and that new conversations are given a unique title:
# In APPX.py, in get_or_create_default_conversation and new_conversation functions:
# Make sure 'title' is being inserted. It already is, so this is just a reminder.
# Example: (user_id, f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}")


@app.route("/load_conversation/<int:conversation_id>", methods=["GET"])
def load_conversation(conversation_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    user_id = session["user_id"]
    db = get_db()
    conv = db.execute("SELECT id FROM conversations WHERE id = ? AND user_id = ?",
                      (conversation_id, user_id)).fetchone()
    if not conv:
        return jsonify({"success": False, "message": "Conversation not found."}), 404

    session["current_conversation_id"] = conversation_id
    messages = db.execute("SELECT message, response FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
                          (conversation_id,)).fetchall()
    history = [[m["message"], m["response"]] for m in messages]
    return jsonify({"success": True, "history": history, "conversation_id": conversation_id})

@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"success": False, "response": "Please log in first."}), 401

    user_id = session["user_id"]
    data = request.json
    user_msg = data.get("message")
    if not user_msg:
        return jsonify({"success": False, "response": "Empty message."}), 400

    conv_id = get_or_create_default_conversation(user_id)
    session["current_conversation_id"] = conv_id
    
    db = get_db()
    historical_msgs = db.execute("SELECT message, response FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
                                 (conv_id,)).fetchall()
    
    messages_for_groq = []
    for h_msg in historical_msgs:
        messages_for_groq.append({"role": "user", "content": h_msg["message"]})
        messages_for_groq.append({"role": "assistant", "content": h_msg["response"]})
    messages_for_groq.append({"role": "user", "content": user_msg})
    
    reply = ask_groq(messages_for_groq)

    db.execute("INSERT INTO messages (conversation_id, user_id, message, response) VALUES (?, ?, ?, ?)",
               (conv_id, user_id, user_msg, reply))
    db.commit()

    return jsonify({"success": True, "response": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)