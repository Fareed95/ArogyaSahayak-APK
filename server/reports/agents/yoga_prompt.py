from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from typing import TypedDict
from dotenv import load_dotenv  
import os

load_dotenv() 

model = ChatOpenAI(model_name="gpt-4")  # You can choose a better model if needed

class LlmState(TypedDict):
    report_summary: str
    youtube_query: str  # This will store the prompt for YouTube search

def generate_youtube_query(state: LlmState) -> LlmState:
    summary = state['report_summary']
    
    # LLM prompt: turn report summary into YouTube search query
    prompt = f"""
    I have the following report summary on health, yoga, and exercises:
    \"\"\"{summary}\"\"\"
    
    Suggest a concise YouTube search query I can use to find videos that improve yoga and exercises relevant to this report. 
    Only give the query, no extra explanation.
    """
    
    result = model.invoke(prompt).content.strip()
    state['youtube_query'] = result
    return state

# Setup workflow graph
graph = StateGraph(LlmState)
graph.add_node("generate_youtube_query", generate_youtube_query)
graph.add_edge(START, "generate_youtube_query")
graph.add_edge("generate_youtube_query", END)
workflow = graph.compile()


def get_youtube_query(report_summary: str) -> str:
    initial_state = {'report_summary': report_summary}
    result = workflow.invoke(initial_state)
    return result['youtube_query']

if __name__ == "__main__":
# Example usage
    summary = '''
    This medical report pertains to a patient's condition in the field of Hematology, attended to by Dr. Susan Cherian, Dr. Uma P Chaturvedi, and Dr. Raji T Naidu at the Bhabha Atomic Research Centre Hospital. The report, spanning three pages, provides a comprehensive analysis of various blood tests conducted on the patient.

    On the first page, the serum sodium level is noted to be slightly below the normal range at 135.9 (normal range: 136.0-145.0), while serum potassium, chloride, creatinine, and blood urea nitrogen levels are elevated beyond their respective normal ranges. 

    The second page indicates that the patient's PCT level is within the normal range; however, several other parameters, including RDW-SD, WBC, RBC, HGB, HCT, MCV, MCH, MCHC, and PLT levels, are outside their normal ranges. Notably, the WBC count is significantly elevated at 19.2 (normal range: 4.0-10.0), which may suggest a potential infection or inflammatory response.

    On the third page, abnormalities are observed in MXD#, NEUT#, RDW-CV, PDW, and LYMPH% levels, all exceeding their respective normal ranges. These findings indicate possible underlying health issues that require further investigation.

    In light of these results, it is recommended that the patient undergo further evaluation and consultation with a healthcare provider to determine the underlying causes of the abnormal blood test results. Additional tests and monitoring may be necessary to accurately diagnose and address any potential health concerns.'''
    initial_state = {
        'report_summary':summary}

    result = workflow.invoke(initial_state)
    print("YouTube Search Query:", result['youtube_query'])
