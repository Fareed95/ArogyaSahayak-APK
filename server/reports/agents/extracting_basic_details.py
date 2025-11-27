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
class ReportDetails(BaseModel):
    disease_name: Optional[str] = None
    doctor_name: Optional[str] = None
    hospital_address: Optional[str] = None
    end: bool = False
    questions: Optional[List[str]] = None

class PageReport(BaseModel):
    page_number: int
    details: ReportDetails

# ------------------------------
# System prompt
# ------------------------------
system_prompt = """
You are a medical report parser. Your task is to extract the following details from a medical report image:

- disease_name
- doctor_name
- hospital_address
- end (True if report ends, else False)
- questions (list any questions if needed)

Please respond ONLY in pure JSON using this format:

{
    "disease_name": "Example Disease",
    "doctor_name": "Dr. ABC",
    "hospital_address": "XYZ Hospital",
    "end": false,
    "questions": ["Question 1", "Question 2"]
}

Do NOT explain anything. Do NOT include code blocks. Respond with valid JSON only.
"""

# ------------------------------
# Models
# ------------------------------
summary_model = ChatOpenAI(temperature=0.7)

# ------------------------------
# Extract from a single image
# ------------------------------
def extract_report_details_from_image(image: Image.Image) -> Optional[ReportDetails]:
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=True) as tmp_file:
            image.save(tmp_file.name, format="JPEG")

            # Upload image file to Gemini
            uploaded_file = client.files.upload(file=tmp_file.name)

            # Generate content using gemini-2.5-flash
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[system_prompt, uploaded_file]
            )

            if hasattr(response, "text"):
                clean_text = re.sub(r"```(?:json)?", "", response.text).strip("` \n")
                match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    return ReportDetails(**data)
    except Exception as e:
        print(f"Error: {e}")
    return None

# ------------------------------
# Extract from PDF
# ------------------------------
def extract_report_from_pdf(pdf_path: str) -> List[PageReport]:
    results = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        details = extract_report_details_from_image(img)
        if details:
            results.append(PageReport(page_number=i, details=details))
    return results

# ------------------------------
# Generate overall summary
# ------------------------------
def generate_report_summary(page_reports: List[PageReport]) -> str:
    # Pydantic v2: use model_dump() instead of dict()
    data_for_summary = [r.model_dump() for r in page_reports]

    prompt = f"""
    You are a medical report summarizer.
    Here are the extracted details from all pages:

    {json.dumps(data_for_summary, indent=2)}

    Generate a human-readable summary of the report,
    mentioning diseases, doctors, hospital info, end status,
    and any follow-up questions. Keep it professional.
    """
    # Use .invoke() instead of deprecated __call__()
    response = summary_model.invoke([HumanMessage(content=prompt)])
    return response.content.strip()

# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    pdf_file = "test.pdf"
    final_results = extract_report_from_pdf(pdf_file)

    # Convert Pydantic models to dicts for JSON output
    output_json = [r.model_dump() for r in final_results]

    # Print structured JSON
    print(json.dumps(output_json, indent=2))

    # Generate and print human-readable summary
    summary_text = generate_report_summary(final_results)
    print("\nOverall Report Summary:\n")
    print(summary_text)

