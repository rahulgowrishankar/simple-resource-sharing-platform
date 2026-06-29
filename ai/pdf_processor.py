import os
from pypdf import PdfReader

def extract_text_from_pdf(file_path):
    """Reads a PDF file from the disk and extracts all plain text."""
    if not os.path.exists(file_path):
        return ""
    
    reader = PdfReader(file_path)
    extracted_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text += text + "\n"
    return extracted_text

def split_into_chunks(text, chunk_size=1000, chunk_overlap=200):
    """Splits text into chunks manually without needing LangChain text splitters."""
    if not text:
        return []
        
    chunks = []
    words = text.split()
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1  # +1 for space
        
        if current_length >= chunk_size:
            chunks.append(" ".join(current_chunk))
            # Create overlap: keep the last few words for context
            overlap_words = current_chunk[-max(1, int(chunk_overlap/10)):]
            current_chunk = list(overlap_words)
            current_length = sum(len(w) + 1 for w in current_chunk)
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks