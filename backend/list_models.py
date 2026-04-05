import os
import google.genai as genai
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

for model in client.models.list():
    print(f"Name: {model.name}, Supported Actions: {model.supported_actions}")
