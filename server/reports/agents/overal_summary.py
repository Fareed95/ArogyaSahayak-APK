import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# OpenAI LLM (fast aur sasta model)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4, api_key=openai_api_key)

def generate_final_summary(basic_details: dict, summary: str) -> str:
    """
    basic_details (dict) + summary (text) ko mila kar ek polished summary banata hai.
    """
    prompt = ChatPromptTemplate.from_template("""
    You are a medical report summarizer.
    Combine the structured details and free text into one clear professional summary.

    Basic details:
    {basic_details}

    Report summary:
    {summary}

    Return the final summary in plain text (no bullet points, no JSON).
    """)

    chain = prompt | llm
    response = chain.invoke({"basic_details": basic_details, "summary": summary})
    return response.content.strip()

# ------------------------------
# Example usage
# ------------------------------
if __name__ == "__main__":
    basic_details = {
        "disease_name": "Diabetes",
        "doctor_name": "Dr. Ramesh",
        "hospital_address": "Apollo Hospital, Mumbai"
    }
    summary = "The report indicates elevated blood sugar levels and regular monitoring is recommended."

    final_summary = generate_final_summary(basic_details, summary)
    print("Final Summary:\n", final_summary)
