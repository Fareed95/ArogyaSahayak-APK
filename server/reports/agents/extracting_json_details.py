import tempfile
from PIL import Image
import fitz
from dotenv import load_dotenv
import os
import re
import json
from pydantic import BaseModel
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from google import genai

# ------------------------------
# Load API key
# ------------------------------
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=google_api_key)

# ------------------------------
# Pydantic models
# ------------------------------
class TestResult(BaseModel):
    Name: str
    Found: float
    Range: Optional[str] = None

class PageResults(BaseModel):
    page_number: int
    tests: List[TestResult]

# ------------------------------
# System prompt for Gemini
# ------------------------------
system_prompt = """
You are a medical report parser. Your task is to extract test values from a medical image.

Please respond ONLY in pure JSON format using this structure:

[
  {
    "Name": "Glycogen",
    "Found": 120,
    "Range": "90-110"
  }
]

Do NOT explain anything.
Do NOT include code blocks or formatting.
Respond with valid, parsable JSON only.
"""

# ------------------------------
# Extract from a single image
# ------------------------------
def extract_medical_json_from_image(image: Image.Image):
    try:
        # Save image to temp file
        with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=True) as tmp_file:
            image.save(tmp_file.name, format="JPEG")

            # Upload file using new method
            uploaded_file = client.files.upload(file=tmp_file.name)

            # Send prompt + uploaded file to Gemini
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[system_prompt, uploaded_file]
            )

            if hasattr(response, "text"):
                clean_text = re.sub(r"```(?:json)?", "", response.text).strip("` \n")
                match = re.search(r"(\{.*\}|\[.*\])", clean_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    return [TestResult(**item) for item in data]
    except Exception as e:
        print(f"Error: {e}")
    return []

# ------------------------------
# Extract from PDF
# ------------------------------
def extract_medical_from_pdf(pdf_path: str) -> List[PageResults]:
    results = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        tests = extract_medical_json_from_image(img)
        if tests:
            results.append(PageResults(page_number=i, tests=tests))
    return results

# ------------------------------
# Generate overall summary
# ------------------------------
summary_model = ChatOpenAI(temperature=0.7)

def generate_report_summary(page_results: List[PageResults]) -> str:
    # Use model_dump() instead of deprecated dict()
    data_for_summary = [r.model_dump() for r in page_results]

    CHUNK_SIZE = 5
    all_chunks = [data_for_summary[i:i+CHUNK_SIZE] for i in range(0, len(data_for_summary), CHUNK_SIZE)]
    summaries = []

    for chunk in all_chunks:
        prompt = f"""
        You are a medical report summarizer.
        Here are the extracted test values from a chunk of pages:

        {json.dumps(chunk, indent=2)}

        Generate a **human-readable summary** in good language,
        explaining the overall report in very deep, main findings, abnormal values, 
        and any recommendations if applicable.
        Keep the tone professional.
        """
        # Use .invoke() instead of deprecated __call__()
        response = summary_model.invoke([HumanMessage(content=prompt)])
        summaries.append(response.content.strip())

    final_summary = "\n\n".join(summaries)
    return final_summary

# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    pdf_file = "test.pdf"
    final_results = extract_medical_from_pdf(pdf_file)
    print("Extracted Page Results:")
    # Use model_dump() instead of dict()
    print([r.model_dump() for r in final_results])

    summary_text = generate_report_summary(final_results)
    print("\nOverall Report Summary:\n")
    print(summary_text)
