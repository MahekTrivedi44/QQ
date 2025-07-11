# ui.py
import gradio as gr
import requests
import time
import re
import os
from pathlib import Path

API_URL = "http://localhost:5000"
session = requests.Session()

# Helper to convert backend history to Gradio's format
def _format_history_for_chatbot(history_list):
    formatted = []
    for user_msg, bot_reply in history_list:
        formatted.append({"role": "user", "content": user_msg})
        formatted.append({"role": "assistant", "content": bot_reply})
    return formatted

# Helper to convert Gradio's format back for backend use
def _convert_chatbot_history_to_backend_format(chatbot_history):
    backend_history = []
    # chatbot_history is a list of dicts: {'role': 'user'|'assistant', 'content': '...'}
    # We need to pair them up into {'message': '...', 'response': '...'}
    user_msg = None
    for item in chatbot_history:
        if item['role'] == 'user':
            user_msg = item['content']
        elif item['role'] == 'assistant' and user_msg is not None:
            backend_history.append({'message': user_msg, 'response': item['content']})
            user_msg = None # Reset for the next pair
    return backend_history


# def log_in(username, password, remember_me):
#     try:
#         r = session.post(f"{API_URL}/login", json={"username": username, "password": password, "remember_me": remember_me})
#         r.raise_for_status()
#         result = r.json()
#         if result["success"]:
#             # On success, immediately fetch data and switch UI
#             chat_data = session.get(f"{API_URL}/get_current_chat_history").json()
#             conv_data = session.get(f"{API_URL}/get_conversations").json()
#             conv_choices = [(c['title'], c['id']) for c in conv_data.get('conversations', [])]
#             valid_values = [c[1] for c in conv_choices]
#             selected_value = chat_data.get("current_conversation_id")
#             if selected_value not in valid_values:
#                 selected_value = valid_values[0] if valid_values else None

#             return (
#                 gr.update(visible=False), gr.update(visible=True),
#                 _format_history_for_chatbot(chat_data.get("history", [])),
#                 gr.update(choices=conv_choices, value=selected_value)
#             )

#         else:
#             gr.Warning(result.get("message", "Login failed."))
#             return gr.update(), gr.update(), gr.update(), gr.update()
#     except requests.RequestException as e:
#         gr.Warning(f"Login error: {e}")
#         return gr.update(), gr.update(), gr.update(), gr.update()

def log_in(username, password, remember_me):
    try:
        r = session.post(f"{API_URL}/login", json={"username": username, "password": password, "remember_me": remember_me})
        r.raise_for_status()
        result = r.json()
        if result["success"]:
            gr.Info(f"Login successful! Welcome {username}.")
            print(f"Frontend log_in: Login successful for {username}") # ADD THIS
            # On success, immediately fetch data and switch UI
            chat_data = session.get(f"{API_URL}/get_current_chat_history").json()
            conv_data = session.get(f"{API_URL}/get_conversations").json()
            # conv_choices = [(f"{c['title']} ({c['preview']})", c['id']) for c in conv_data.get('conversations', [])] # Match ui.py format
            # conv_choices = [(f"{c['title']} ({c.get('preview', '')})", c['id']) for c in conv_data.get('conversations', [])] # Safely get 'preview'
            print(f"Frontend log_in: Data received from /get_conversations: {conv_data}") # ADD THIS
            # conv_choices = [(c['title'], c['id']) for c in conv_data.get('conversations', [])] # Simplified for APPX.py's backend
            conv_choices = [("🗁 New Chat", "EMPTY_CONVO")] + [(c['title'], c['id']) for c in conv_data.get('conversations', [])]
            print(f"Frontend log_in: Conversation dropdown choices: {conv_choices}") # ADD THIS
            selected_value = chat_data.get("current_conversation_id")
            # Ensure selected_value is valid for the dropdown choices
            valid_values = [c[1] for c in conv_choices]
            dropdown_selected_value = selected_value if any(c_id == selected_value for _, c_id in conv_choices) else None

            return (
                gr.update(visible=False), 
                gr.update(visible=True),
                _format_history_for_chatbot(chat_data.get("history", [])),
                dropdown_selected_value, # Pass to current_conversation_id_state
                gr.update(choices=conv_choices, value=dropdown_selected_value),
                gr.update(value=""),  # clear username
                gr.update(value=""),  # clear password
                gr.update(value=False),  # clear checkbox
                gr.update(visible=False)  # Hide about image
            )

        else:
            gr.Warning(result.get("message", "Login failed. Please check your credentials."))
            # Return 9 gr.update() to maintain the current state for all outputs
            return (
                gr.update(), # auth_ui (no change)
                gr.update(), # chat_ui (no change)
                gr.update(), # chatbot (no change)
                gr.update(), # current_conversation_id_state (no change)
                gr.update(), # conversation_dd (no change)
                gr.update(), # login_user (no change)
                gr.update(), # login_pass (no change)
                gr.update(), # remember_chk (no change)
                gr.update()  # about_img_col (no change)
            )
    except requests.RequestException as e:
        gr.Warning(f"Login error: {e}")
        # Return 9 gr.update() to maintain the current state for all outputs
        return (
            gr.update(), # auth_ui (no change)
            gr.update(), # chat_ui (no change)
            gr.update(), # chatbot (no change)
            gr.update(), # current_conversation_id_state (no change)
            gr.update(), # conversation_dd (no change)
            gr.update(), # login_user (no change)
            gr.update(), # login_pass (no change)
            gr.update(), # remember_chk (no change)
            gr.update()  # about_img_col (no change)
        )

def log_out():
    session.post(f"{API_URL}/logout")
    return (
        gr.update(visible=True), gr.update(visible=False),
        [], gr.update(choices=[], value=None), gr.update(visible=True),
    )

# def sign_up(username, password):
#     if len(password) < 8:
#         gr.Warning("Password must be at least 8 characters long.")
#         return gr.update()
#     try:
#         r = session.post(f"{API_URL}/signup", json={"username": username, "password": password})
#         r.raise_for_status()
#         result = r.json()
#         if result["success"]:
#             gr.Info("Signup successful! You can now log in.")
#         else:
#             gr.Warning(result.get("message", "Signup failed."))
#     except requests.RequestException as e:
#         gr.Warning(f"Signup error: {e}")
#     return gr.update(value="") # Clear output

def sign_up(username, password):
    if not username or not password:
        gr.Warning("Username and password cannot be empty.")
        # Ensure 4 outputs are returned to match the expected number of components
        return gr.update(), gr.update(), gr.update(), gr.update()
    try:
        r = session.post(f"{API_URL}/signup", json={"username": username, "password": password})
        r.raise_for_status()
        result = r.json()
        if result["success"]:
            gr.Info("Signup successful! You can now log in.")
            # Clear signup fields and switch to login tab
            return gr.update(value=""), gr.update(value=""), gr.Tabs(selected="Login"), gr.update(value="")
        else:
            gr.Warning(result.get("message", "Signup failed."))
            # Replaced gr.update()
            return gr.update(), gr.update(), gr.update(), gr.update(value="") 
    except requests.RequestException as e:
        gr.Warning(f"Signup error: {e}")
        # Replaced gr.update()
        return gr.update(), gr.update(), gr.update(), gr.update(value="")
    
def chat_with_bot(msg, history):
    if not msg:
        return "", history
    try:
        r = session.post(f"{API_URL}/chat", json={"message": msg})
        r.raise_for_status()
        reply = r.json()["response"]

        # Modify this part:
        # 'history' here will be in the 'messages' format (list of dicts)
        # So, append new messages in that same format
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": reply})

        return "", history
    except requests.RequestException as e:
        gr.Warning(f"Chat error: {e}")
        return msg, history
    
# def start_new_conversation():
#     try:
#         r = session.post(f"{API_URL}/new_conversation")
#         r.raise_for_status()
#         # After creating a new one, refresh the conversation list and load the empty chat
#         conv_data = session.get(f"{API_URL}/get_conversations").json()
#         conv_choices = [(c['title'], c['id']) for c in conv_data.get('conversations', [])]
#         new_conv_id = r.json().get("conversation_id")
#         return [], gr.update(choices=conv_choices, value=new_conv_id)
#     except requests.RequestException as e:
#         gr.Warning(f"Failed to start new conversation: {e}")
#         return gr.update(), gr.update()

# def start_new_conversation():
#     try:
#         r = session.post(f"{API_URL}/new_conversation")
#         r.raise_for_status()
#         new_conv_id = r.json().get("conversation_id")
#         # Return an empty chat history and the NEW conversation ID
#         return [], new_conv_id
#     except requests.RequestException as e:
#         gr.Warning(f"Failed to start new conversation: {e}")
#         return gr.update(), gr.update()

# In UIX.py, replace the existing start_new_conversation and its helper state

# In UIX.py, around line 76
def start_new_conversation():
    try:
        r_new = session.post(f"{API_URL}/new_conversation")
        r_new.raise_for_status()
        new_conv_id = r_new.json().get("conversation_id")
        gr.Info("New conversation started!")
        # Return an empty chat history and the NEW conversation ID
        # The dropdown choices will be updated in the subsequent chained event
        return [], new_conv_id # Clear chatbot, return new_conv_id for the state
    except requests.RequestException as e:
        gr.Warning(f"Failed to start new conversation: {e}")
        return [], gr.update(visible=True)
# def load_selected_conversation(conv_id):
#     if not conv_id:
#         return []
#     try:
#         conv_id = int(conv_id)
#     except ValueError:
#         gr.Warning("Invalid conversation ID.")
#         return []


#     try:
#         r = session.get(f"{API_URL}/load_conversation/{conv_id}")
#         r.raise_for_status()
#         history = r.json().get("history", [])
#         return _format_history_for_chatbot(history)
#     except requests.RequestException as e:
#         gr.Warning(f"Failed to load conversation: {e}")
#         return []

# In UIX.py, modify the load_selected_conversation function:
# def load_selected_conversation(conv_id):
#     if not conv_id:
#         # If no conversation ID is provided (e.g., after logout), clear everything
#         return [], gr.update(choices=[], value=None)

#     try:
#         # Load the selected conversation's history
#         # r = session.post(f"{API_URL}/load_conversation", json={"conversation_id": conv_id}) # Changed to POST to match ui.py's load_conversation
#         r = session.get(f"{API_URL}/load_conversation/{conv_id}") # Changed to GET and path parameter
#         r.raise_for_status()
#         data = r.json()
#         formatted_history = _format_history_for_chatbot(data.get("history", []))

#         # Re-fetch the entire list of conversations to ensure the dropdown is updated
#         # with the latest choices, including the newly created one.
#         conversations_r = session.get(f"{API_URL}/get_conversations")
#         conversations_r.raise_for_status()
#         conversations_result = conversations_r.json()
#         conv_list_data = conversations_result.get("conversations", [])
#         # conv_dropdown_choices = [(f"{c['title']} ({c['preview']})", c['id']) for c in conv_list_data]
#         # conv_dropdown_choices = [(f"{c['title']} ({c.get('preview', '')})", c['id']) for c in conv_list_data] # Safely get 'preview'
#         conv_dropdown_choices = [(c['title'], c['id']) for c in conv_list_data] # Simplified for APPX.py's backend
#         # Determine the value to set for the dropdown
#         # Only set conv_id if it's actually in the list of choices (important for consistency)
#         dropdown_selected_value = conv_id if any(c_id == conv_id for _, c_id in conv_dropdown_choices) else None

#         # Return updates for both the chatbot and the dropdown
#         return formatted_history, gr.update(choices=conv_dropdown_choices, value=dropdown_selected_value)

#     except requests.RequestException as e:
#         gr.Warning(f"Failed to load conversation: {e}")
#         return gr.update(), gr.update()

def load_selected_conversation(conv_id):
    if not conv_id or conv_id == "EMPTY_CONVO":
        # Don't try to load this from backend if it's the placeholder
        conversations_r = session.get(f"{API_URL}/get_conversations")
        conversations_r.raise_for_status()
        conversations_result = conversations_r.json()
        conv_list_data = conversations_result.get("conversations", [])
        conv_dropdown_choices = [("🗁 New Chat", "EMPTY_CONVO")] + [(c['title'], c['id']) for c in conv_list_data]
        return [], gr.update(choices=conv_dropdown_choices, value="EMPTY_CONVO")

    try:
        r = session.get(f"{API_URL}/load_conversation/{conv_id}")
        r.raise_for_status()
        data = r.json()
        formatted_history = _format_history_for_chatbot(data.get("history", []))

        # Re-fetch the entire list of conversations to ensure the dropdown is updated
        # with the latest choices, including the newly created one.
        conversations_r = session.get(f"{API_URL}/get_conversations")
        conversations_r.raise_for_status()
        conversations_result = conversations_r.json()
        conv_list_data = conversations_result.get("conversations", [])
        
        # Ensure the 'title' key is used for the display in the dropdown
        # conv_dropdown_choices = [(c['title'], c['id']) for c in conv_list_data]
        # Determine the value to set for the dropdown
        # Only set conv_id if it's actually in the list of choices
        # dropdown_selected_value = conv_id if any(c_id == conv_id for _, c_id in conv_dropdown_choices) else None
        # Set dropdown to first available valid conversation if current is invalid (e.g. an empty one)
        conv_dropdown_choices = [("🗁 New Chat", "EMPTY_CONVO")] + [(c['title'], c['id']) for c in conv_list_data]
        valid_ids = [c_id for _, c_id in conv_dropdown_choices if c_id != "EMPTY_CONVO"]
        dropdown_selected_value = conv_id if conv_id in valid_ids else "EMPTY_CONVO"


        return formatted_history, gr.update(choices=conv_dropdown_choices, value=dropdown_selected_value)

    except requests.RequestException as e:
        gr.Warning(f"Failed to load conversation: {e}")
        return [], gr.update(visible=True)
    
def generate_summary(chat_history):
    if not chat_history:
        gr.Warning("Chat is empty, nothing to summarize.")
        return None, "Chat is empty."
    
    backend_history = _convert_chatbot_history_to_backend_format(chat_history)
    try:
        r = session.post(f"{API_URL}/summarize_chat", json={"history": backend_history})
        r.raise_for_status()
        result = r.json()
        if result["success"]:
            file_path = result["file_path"]
            filename = os.path.basename(file_path)
            download_url = f"{API_URL}/files/{filename}"
            return gr.File(value=file_path, visible=True), f"Summary ready! [Download PDF]({download_url})"
        else:
            return None, f"Error: {result.get('message')}"
    except requests.RequestException as e:
        return None, f"Error generating summary: {e}"

def generate_flashcards(file_format, chat_history):
    if not chat_history:
        gr.Warning("Chat is empty, nothing to generate flashcards from.")
        return None, "Chat is empty."

    backend_history = _convert_chatbot_history_to_backend_format(chat_history)
    try:
        r = session.post(f"{API_URL}/generate_flashcards", json={"history": backend_history, "format": file_format.lower()})
        r.raise_for_status()
        result = r.json()
        if result["success"]:
            file_path = result["file_path"]
            filename = os.path.basename(file_path)
            download_url = f"{API_URL}/files/{filename}"
            if "html" in file_format.lower():
                # For HTML, provide a clickable link to open in a new tab
                return None, f"Flashcards ready! <a href='{download_url}' target='_blank'>Click here to open them</a>."
            else:
                # For PDF, provide the file for download
                return gr.File(value=file_path, visible=True), f"Flashcards ready! [Download PDF]({download_url})"
        else:
            return None, f"Error: {result.get('message')}"
    except requests.RequestException as e:
        return None, f"Error generating flashcards: {e}"


# def on_load():
#     try:
#         r = session.get(f"{API_URL}/check_login_status")
#         if r.ok and r.json().get("logged_in"):
#             chat_data = session.get(f"{API_URL}/get_current_chat_history").json()
#             conv_data = session.get(f"{API_URL}/get_conversations").json()
#             conv_choices = [(c['title'], c['id']) for c in conv_data.get('conversations', [])]
#             valid_values = [c[1] for c in conv_choices]
#             selected_value = chat_data.get("current_conversation_id")
#             if selected_value not in valid_values:
#                 selected_value = valid_values[0] if valid_values else None

#             return (
#                 gr.update(visible=False), gr.update(visible=True),
#                 _format_history_for_chatbot(chat_data.get("history", [])),
#                 gr.update(choices=conv_choices, value=selected_value)
#             )

#     except requests.ConnectionError:
#         gr.Warning("Could not connect to the backend. Please ensure app.py is running.")
#     except Exception as e:
#         print(f"Error on load: {e}")
#     # Default to login screen
#     return gr.update(visible=True), gr.update(visible=False), [], gr.update(choices=[], value=None)

# def on_load():
#     try:
#         r = session.get(f"{API_URL}/check_login_status")
#         if r.ok and r.json().get("logged_in"):
#             chat_data = session.get(f"{API_URL}/get_current_chat_history").json()
#             conv_data = session.get(f"{API_URL}/get_conversations").json()
#             print(f"Frontend on_load (check_initial_login_status): Data received from /get_conversations: {conv_data}") # ADD THIS
#             # conv_choices = [(f"{c['title']} ({c['preview']})", c['id']) for c in conv_data.get('conversations', [])] # Match ui.py format
#             # conv_choices = [(f"{c['title']} ({c.get('preview', '')})", c['id']) for c in conv_data.get('conversations', [])] # Safely get 'preview'
#             conv_choices = [(c['title'], c['id']) for c in conv_data.get('conversations', [])] # Simplified for APPX.py's backend
#             print(f"Frontend on_load: Conversation dropdown choices: {conv_choices}") # ADD THIS
#             selected_value = chat_data.get("current_conversation_id")
#             dropdown_selected_value = selected_value if any(c_id == selected_value for _, c_id in conv_choices) else None

#             return (
#                 gr.update(visible=False), gr.update(visible=True),
#                 _format_history_for_chatbot(chat_data.get("history", [])),
#                 selected_value, # Pass to current_conversation_id_state
#                 gr.update(choices=conv_choices, value=dropdown_selected_value)
#             )

#     except requests.ConnectionError:
#         gr.Warning("Could not connect to the backend. Please ensure app.py is running.")
#     except Exception as e:
#         print(f"Error on load: {e}")
#     # Default to login screen
#     return gr.update(visible=True), gr.update(visible=False), [], None, gr.update(choices=[], value=None) # Added None for current_conversation_id_state

def on_load():
    try:
        r = session.get(f"{API_URL}/check_login_status")
        if r.ok and r.json().get("logged_in"):
            chat_data = session.get(f"{API_URL}/get_current_chat_history").json()
            conv_data = session.get(f"{API_URL}/get_conversations").json()
            print(f"Frontend on_load (check_initial_login_status): Data received from /get_conversations: {conv_data}")
            
            # Ensure the 'title' key is used for the display in the dropdown
            conv_choices = [(c['title'], c['id']) for c in conv_data.get('conversations', [])]
            print(f"Frontend on_load: Conversation dropdown choices: {conv_choices}")
            
            selected_value = chat_data.get("current_conversation_id")
            dropdown_selected_value = selected_value if any(c_id == selected_value for _, c_id in conv_choices) else None

            return (
                gr.update(visible=False), gr.update(visible=True),
                _format_history_for_chatbot(chat_data.get("history", [])),
                selected_value, # Pass to current_conversation_id_state
                gr.update(choices=conv_choices, value=dropdown_selected_value),
                gr.update(visible=False),  # Hide about image
            )

    except requests.ConnectionError:
        gr.Warning("Could not connect to the backend. Please ensure app.py is running.")
    except Exception as e:
        print(f"Error on load: {e}")
    return gr.update(visible=True), gr.update(visible=False), [], None, gr.update(choices=[], value=None)

def show_generating_summary():
    return gr.update(visible=True)

def hide_generating_summary():
    return gr.update(visible=False)

def show_generating_flashcards():
    return gr.update(visible=True)

def hide_generating_flashcards():
    return gr.update(visible=False)

custom_css = Path("style.css").read_text()
with gr.Blocks(theme=None, elem_id="flashcard_block", css=custom_css) as flashcard_ui:
    flashcard_format = gr.Radio(["PDF", "HTML (Interactive)"], show_label=False, value="PDF")
    flashcard_btn = gr.Button("Generate Flashcards", elem_id="submit_buttons")
    generating_flashcards_msg = gr.Markdown("Generating flashcards, please wait...", visible=False)
    flashcard_file = gr.File(label="Download Flashcards", visible=False, interactive=False)
    flashcard_output = gr.Markdown()

with gr.Blocks(theme=gr.themes.Soft(), title="Query Quokka Chat", css=custom_css) as demo:
    # gr.Markdown("# 💖 Query Quokka 💖")
    # gr.Image("assets/Query_Quokka.png", width=200, show_label=False, interactive=False, show_download_button=False, show_fullscreen_button=False, height=200, container=False)
    gr.Image(
            value="assets/logo.png",
            elem_id="logo-img",
            show_label=False,
            interactive=False,
            show_download_button=False,
            show_fullscreen_button=False,
            width=250, 
            height=105
        )
    with gr.Column(visible=False) as chat_ui:
        with gr.Row():
            with gr.Column(scale=1, elem_id="chatbot-cont"): # Sidebar
                # conversation_dd = gr.Dropdown(label="Past Chats", interactive=True, allow_custom_value=False)
                
                gr.Markdown("### Past Chats:", elem_classes="pastconvos-label")
                conversation_dd = gr.Dropdown(
                    show_label=False,
                    interactive=True,
                    allow_custom_value=False,
                    # placeholder="🗁 New Chat"
                )


                new_chat_btn = gr.Button("New Chat", elem_id="submit_buttons")
                logout_btn = gr.Button("Logout", elem_id="submit_buttons")
                
                with gr.Accordion("Export Tools", open=False):
                    gr.Markdown("#### Generate Summary")
                    summary_btn = gr.Button("Generate PDF Summary", elem_id="submit_buttons")
                    generating_summary_msg = gr.Markdown("Generating Summary, please wait...", visible=False)
                    summary_file = gr.File(label="Download Summary", visible=False, interactive=False)
                    summary_output = gr.Markdown()

                    gr.Markdown("---")
                    
                    gr.Markdown("#### Generate Flashcards")
                    # flashcard_format = gr.Radio(["PDF", "HTML (Interactive)"], label="Format", value="PDF")
                    gr.Markdown("### Format", elem_classes="custom-label")
                    flashcard_ui.render()  # Render the flashcard UI
                    # flashcard_format = gr.Radio(["PDF", "HTML (Interactive)"], show_label=False, value="PDF")
                    # flashcard_btn = gr.Button("Generate Flashcards")
                    # generating_flashcards_msg = gr.Markdown("Generating flashcards, please wait...", visible=False)
                    # flashcard_file = gr.File(label="Download Flashcards", visible=False, interactive=False)
                    # flashcard_output = gr.Markdown()

            with gr.Column(scale=3, elem_id="chatbot-cont"): # Main chat area
                chatbot = gr.Chatbot(
                    type='messages', label="Query Quokka", height=500,
                    avatar_images=(None, "https://github.com/MahekTrivedi44/logo/blob/main/download%20(13).jpg?raw=true")
                )
                msg_txt = gr.Textbox(label="Your Message", placeholder="Type here...", show_label=False, lines=1)
                send_btn = gr.Button("Send", elem_id="send_buttons")

    with gr.Row():
        with gr.Column(scale=2, visible=True, elem_id="about_img_col") as about_img_col:
            gr.Image(
                value="assets/about.png",  # <-- your about image here
                elem_id="about-img",
                show_label=False,
                interactive=False,
                show_download_button=False,
                show_fullscreen_button=False
            )
        with gr.Column(scale=1) as auth_ui:
            with gr.Column(visible=True, elem_id="auth_container"):
                with gr.Tabs(selected="Login", elem_id="auth_tabs") as auth_tabs:
                    with gr.Tab("Log In", id="Login"):
                        gr.Markdown("### Username", elem_classes="custom-label")
                        login_user = gr.Textbox(show_label=False, placeholder="Enter your username", elem_id="login-user")
                        gr.Markdown("### Password", elem_classes="custom-label")
                        login_pass = gr.Textbox(type="password", show_label=False, placeholder="Enter your password", elem_id="login-pass")
                        remember_chk = gr.Checkbox(label="Remember Me (24 hours)")
                        login_btn = gr.Button("Log In", elem_id="submit_buttons")
                    with gr.Tab("Sign Up", id="SignUp"):
                        gr.Markdown("### Username", elem_classes="custom-label")
                        signup_user = gr.Textbox(show_label=False, placeholder="Create your username", elem_id="login-user")
                        gr.Markdown("### Password", elem_classes="custom-label")
                        signup_pass = gr.Textbox(type="password", show_label=False, placeholder="Create your password", elem_id="login-pass")
                        signup_btn = gr.Button("Sign Up", elem_id="submit_buttons")
                        

                status_output = gr.Markdown()
            # NEW: Creator Info Container
            with gr.Column(elem_id="creator_info_container"):
                gr.Markdown("### Connect with the Creator", elem_classes="custom-label")
                with gr.Row(elem_id="creator_button_row"):
                    gr.Button("LinkedIn", link="https://www.linkedin.com/in/mahek-devang-trivedi-511a1b29a/", elem_id="btn_linkedin")
                    gr.Button("GitHub", link="https://github.com/MahekTrivedi44", elem_id="btn_github")
                    gr.Button("Mail", link="mailto:mahektrivedi2006@gmail.com", elem_id="btn_mail")

        # A state to hold the current conversation ID, just like in ui.py
    current_conversation_id_state = gr.State(None)
    # Event Handlers
    # login_btn.click(log_in, [login_user, login_pass, remember_chk], [auth_ui, chat_ui, chatbot, conversation_dd])
    
    login_btn.click(
        log_in, 
        inputs=[login_user, login_pass, remember_chk], 
        outputs=[
            auth_ui, chat_ui, chatbot, current_conversation_id_state, conversation_dd,
            login_user, login_pass, remember_chk, about_img_col,  # ✅ Clear inputs
        ]
    )

    
    logout_btn.click(log_out, [], [auth_ui, chat_ui, chatbot, conversation_dd, about_img_col,])
    # signup_btn.click(sign_up, [signup_user, signup_pass], [status_output])
    signup_btn.click(
        sign_up,
        inputs=[signup_user, signup_pass],
        outputs=[signup_user, signup_pass, auth_tabs, status_output] # Added auth_tabs to outputs
    )
    msg_txt.submit(chat_with_bot, [msg_txt, chatbot], [msg_txt, chatbot])
    send_btn.click(chat_with_bot, [msg_txt, chatbot], [msg_txt, chatbot])
    
    # In UIX.py, find this event handler and modify the .then() block
    
    new_chat_btn.click(
        fn=start_new_conversation,
        inputs=[],
        outputs=[chatbot, current_conversation_id_state] # Update chatbot and the new state
    ).then( # Chained event to reload conversations and set the newly created one
        fn=load_selected_conversation,
        inputs=[current_conversation_id_state], # Pass the ID from the previous step
        outputs=[chatbot, conversation_dd] # Now load it into the dropdown and chatbot
    )

    conversation_dd.change(
        load_selected_conversation,
        [conversation_dd],
        [chatbot, conversation_dd] # <-- Make sure the dropdown is listed as an output
    )
    # summary_btn.click(generate_summary, [chatbot], [summary_file, summary_output], show_progress=True)
    # flashcard_btn.click(generate_flashcards, [flashcard_format, chatbot], [flashcard_file, flashcard_output], show_progress=True)
    summary_btn.click(
        fn=show_generating_summary,
        inputs=[],
        outputs=generating_summary_msg
    ).then(
        fn=generate_summary,
        inputs=[chatbot],
        outputs=[summary_file, summary_output]
    ).then(
        fn=hide_generating_summary,
        inputs=[],
        outputs=generating_summary_msg
    )

    # Hook for flashcard button
    flashcard_btn.click(
        fn=show_generating_flashcards,
        inputs=[],
        outputs=generating_flashcards_msg
    ).then(
        fn=generate_flashcards,
        inputs=[flashcard_format, chatbot],
        outputs=[flashcard_file, flashcard_output]
    ).then(
        fn=hide_generating_flashcards,
        inputs=[],
        outputs=generating_flashcards_msg
    )
    # demo.load(on_load, [], [auth_ui, chat_ui, chatbot, conversation_dd])
    demo.load(
        on_load, 
        inputs=[], 
        outputs=[auth_ui, chat_ui, chatbot, current_conversation_id_state, conversation_dd, about_img_col]
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)