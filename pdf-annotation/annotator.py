import os
import pathlib
import pandas as pd
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from sentence_transformers import SentenceTransformer


#Used ChatGPT for help
#many of the pdfs got coruppted and could not be processed but the code is fully functional

GOOGLE_API_KEY = "AIzaSyATJ3gXYZSwNevrj1qgfYwrtEZ_7Ijg424"
client = genai.Client(api_key=GOOGLE_API_KEY)

# Initialize the SentenceTransformer model for embeddings
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  

pdf_dir = pathlib.Path('./scrap_downloaded_pdfs')

df = pd.DataFrame(columns=["Paper_Title", "Author", "Year", "Category", "Embedding"])

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using PyMuPDF (fitz)."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def generate_label(pdf_path):
    try:
        text = extract_text_from_pdf(pdf_path)

        # Limit text to 3000 words
        words = text.split()
        if len(words) > 3000:
            text = " ".join(words[:3000])

        prompt = f"""Read the contents of the research paper and classify it into the most appropriate category from the following:
        Deep Learning, Computer Vision, Reinforcement Learning, NLP, Optimization.
        If the paper does not fit any of these, classify it as Other.
        Output Format:
        Paper Title: (extracted_title)
        Author: (author_name)
        Year: (year)
        Category: (One of the above labels)"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(
                    data=pdf_path.read_bytes(),
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )

        response_text = response.text.strip().split("\n")
        extracted_data = {key.strip(":"): value.strip() for key, value in (line.split(": ", 1) for line in response_text if ": " in line)}

        # Generate the embedding for the extracted text (for semantic search or analysis)
        embedding = embedding_model.encode(text).tolist()

        return {
            "Paper_Title": extracted_data.get("Paper Title", "Unknown Title"),
            "Author": extracted_data.get("Author", "Unknown Author"),
            "Year": extracted_data.get("Year", "Unknown Year"),
            "Category": extracted_data.get("Category", "Other"),
            "Embedding": embedding  
        }

    except Exception as e:
        print(f"Error processing {pdf_path.name}: {str(e)}")
        return None

def extract_pdf(pdf_dir):
    result_list = []
    for pdf_path in pdf_dir.rglob("*.pdf"):
        print(f"Processing: {pdf_path.name}")  # Debugging print

        result = generate_label(pdf_path)
        if result:
            result_list.append(result)

    return result_list

def main():
    processed_data = extract_pdf(pdf_dir)

    df = pd.DataFrame(processed_data)

    df.to_csv("classified_pdfs_with_embeddings.csv", index=False)
    print("\nAll PDFs processed. Data saved to classified_pdfs_with_embeddings.csv")

if __name__ == "__main__":
    main()