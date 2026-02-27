
import os
import fitz
from gemini_service import gemini_service

def test():
    file_path = "uploads/Machine Learning_UNIT III.pdf"
    if not os.path.exists(file_path):
        # try to find any pdf
        files = [f for f in os.listdir("uploads") if f.endswith(".pdf")]
        if not files:
            print("No PDFs found")
            return
        file_path = os.path.join("uploads", files[0])
    
    print(f"Testing {file_path}...")
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        print(f"Extracted {len(text)} chars")
        
        snippet = text[:100]
        print(f"Snippet: {snippet}")
        
        print("Generating embedding...")
        emb = gemini_service.generate_embedding(snippet)
        print(f"Embedding success! Length: {len(emb)}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test()
