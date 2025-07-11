import requests
import time
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

MAX_RETRIES = 3

def ask_groq(messages_list):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages_list
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(GROQ_ENDPOINT, headers=headers, json=data, timeout=30)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                    except ValueError:
                        wait_time = 2 ** attempt  # fallback if malformed
                else:
                    wait_time = 2 ** attempt  # fallback if header missing

                print(f"🕒 Rate limit hit (429). Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']

        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                print(f"Request failed after {MAX_RETRIES} attempts: {e}")
                return "❌ Unable to connect to the AI after multiple attempts. Please try again later."
            else:
                wait_time = 2 ** attempt
                print(f"⚠️ Request error. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        except KeyError:
            return "⚠️ Received unexpected response from AI. Please try again."

    return "❌ Failed to get a response after multiple attempts."
