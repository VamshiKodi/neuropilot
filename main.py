import os
from google import genai

# Create client using environment variable
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

response = client.models.generate_content(
    model="models/gemini-2.5-flash",
    contents="Hello, you are NeuroPilot. Introduce yourself as a futuristic AI operator."
)

print(response.text)