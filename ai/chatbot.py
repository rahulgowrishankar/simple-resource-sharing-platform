import os
from google import genai

def generate_answer(question, context_chunks):
    # Safety fallback if no matching context chunks are found
    if not context_chunks or not any(chunk.strip() for chunk in context_chunks):
        return "I'm sorry, but no background reference text was found inside the database matching your query. Please upload and process a PDF first."

    # Direct client initialization reads GEMINI_API_KEY from environment variables automatically
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "System Error: The Gemini API Key is missing. Please check your .env file."
        
    client = genai.Client(api_key=api_key)
    context_text = "\n---\n".join(context_chunks)
    
    prompt = f"""
You are an academic resource assistant for a college portal. 
Answer the student's question using ONLY the verified source context fragments provided below.
If the answer cannot be confidently derived from the context, respond with: 
"I'm sorry, but that information isn't available in the uploaded college resources."

Context fragments from uploaded PDFs:
{context_text}

Student Question: {question}
Answer:
"""

    try:
        # Updated model keyword parameter to active production generation standards
        response = client.models.generate_content(
            model='gemini-2.5-flash',  
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"Gemini API Communication Error: {str(e)}"