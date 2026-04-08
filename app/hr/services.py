import os
import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.vectorstore import collection
from app.llm.embeddings import get_embedding


def process_policy(file_path: str, filename: str):

    filename = os.path.basename(filename)

    collection.delete(where={"source": filename})

    doc = fitz.open(file_path)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False,
    )

    for page_number in range(len(doc)):

        page = doc[page_number]
        text = page.get_text()

        if not text.strip():
            continue

        text = text.replace("\n", " ").strip()

        chunks = text_splitter.split_text(text)

        for i, chunk in enumerate(chunks):

            if len(chunk.strip()) < 100:
                continue

            embedding = get_embedding(chunk)

            unique_id = f"{filename}_page{page_number+1}_chunk{i}"

            collection.add(
                documents=[chunk],
                embeddings=[embedding],
                ids=[unique_id],
                metadatas=[{
                    "source": filename,
                    "page": page_number + 1,
                    "chunk": i
                }]
            )

    print("Indexed successfully")