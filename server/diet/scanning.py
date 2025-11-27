import tempfile
import re
import json
from typing import Optional
from PIL import Image
import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv
import os
# Load environment variables
load_dotenv()


google_api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=google_api_key)
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 0,
    "max_output_tokens": 4096,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

report_model = genai.GenerativeModel(
    "gemini-1.5-flash",
    generation_config=generation_config,
    safety_settings=safety_settings
)


# Pydantic model for barcode output
class BarcodeDetails(BaseModel):
    barcode_number: str

# System prompt for Google LLM
system_prompt = """
You are a barcode extraction assistant.
You are given an image of a barcode.
Extract **only the barcode number** and return it as JSON like this:

{
  "barcode_number": "1234567890"
}

Do not return any additional text.
"""

# Main function using LLM
def scan_barcode_and_number(image_file) -> str:
    """
    image_file: file-like object (like what you get from Django request.FILES)
    returns: detected barcode number as string, or "No barcode detected"
    """
    try:
        # Convert image bytes to PIL Image
        image = Image.open(image_file)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=True) as tmp_file:
            image.save(tmp_file.name, format="JPEG")

            # Upload file to Google LLM
            uploaded_file = genai.upload_file(path=tmp_file.name)

            # Call your report model (LLM) to extract barcode
            response = report_model.generate_content([system_prompt, uploaded_file])

            # Parse LLM response
            if hasattr(response, "text"):
                clean_text = re.sub(r"```(?:json)?", "", response.text).strip("` \n")
                match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    barcode_details = BarcodeDetails(**data)
                    print(barcode_details)
                    return barcode_details.barcode_number

    except Exception as e:
        print(f"Error extracting barcode: {e}")

    return "No barcode detected"
