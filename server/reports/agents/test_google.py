from google import genai
from dotenv import load_dotenv
import os
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")


client = genai.Client(api_key=google_api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash", contents="Explain how AI works in a few words"
)
print(response.text)