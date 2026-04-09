import PyPDF2
import docx
import pandas as pd

def parse_document(file_path: str) -> str:
    if file_path.endswith(".pdf"):
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text()
        return text

    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])

    elif file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
        return df.to_string()

    else:
        raise ValueError("Unsupported file format")
