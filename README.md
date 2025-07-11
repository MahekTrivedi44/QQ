# Query Quokka

#### An AI-Powered Chat and Data Management Tool

---

### 🚀 Introduction

Query Quokka is a full-featured, AI-powered chatbot application designed to help users manage their conversations. It features a secure user authentication system, a conversational interface, and powerful data management capabilities, including the ability to store chat history and export conversations into summary documents or flashcards.

### ✨ Key Features

* **User Authentication**: Secure user registration and login system with password hashing powered by `bcrypt`.
* **AI-Powered Chatbot**: Leverages the powerful Groq API to provide real-time, intelligent responses to user queries.
* **Persistent Conversations**: All chat messages and conversations are stored in a local SQLite database, allowing users to revisit and continue their chats.
* **Content Generation & Export**: Generate and export chat summaries and flashcards in PDF format (`.pdf`) for easy sharing and offline use.
* **Intuitive UI**: A clean, single-page web interface built with Gradio and styled with custom CSS for a friendly user experience.

### ⚙️ Technologies Used

* **Backend**: Python, Flask, Gunicorn
* **Frontend**: Gradio, Custom CSS
* **AI API**: Groq API
* **Authentication**: `bcrypt`
* **Database**: SQLite
* **Data Export**: `fpdf`

### 📦 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

#### Prerequisites

-   Python 3.8 or higher
-   `pip` (Python package installer)
-   Git

#### Installation

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/your-username/query-quokka.git](https://github.com/your-username/query-quokka.git)
    cd query-quokka
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the database**:
    The database will be automatically created and initialized with the schema when you run the application for the first time, thanks to the `init_db()` function.

5.  **Configure your API key**:
    Set your Groq API key as an environment variable. **DO NOT hardcode your key in the `chatbot.py` file.**
    * **On macOS/Linux:**
        ```bash
        export GROQ_API_KEY="gsk_YOUR_API_KEY_HERE"
        ```
    * **On Windows (Command Prompt):**
        ```bash
        set GROQ_API_KEY="gsk_YOUR_API_KEY_HERE"
        ```

#### Running the Application

This application requires two separate processes to run concurrently: the Flask backend and the Gradio frontend.

1.  **Open two terminal windows** in the project's root directory.

2.  **In the first terminal**, start the Flask backend:
    ```bash
    gunicorn --bind 0.0.0.0:5000 app:app
    ```

3.  **In the second terminal**, start the Gradio frontend:
    ```bash
    python ui.py
    ```

Your application should now be running. Open your web browser and navigate to the address provided by Gradio, typically `http://127.0.0.1:7860`.

### 📂 Project Structure
```bash
├── app.py              # The Flask backend application
├── auth.py             # User authentication functions
├── chatbot.py          # Groq API integration for the chatbot
├── db.py               # Database connection and utility functions
├── requirements.txt    # Python dependencies
├── schema.sql          # SQL commands to create database tables
├── style.css           # Custom CSS for the Gradio UI
└── ui.py               # The Gradio frontend interface
```
