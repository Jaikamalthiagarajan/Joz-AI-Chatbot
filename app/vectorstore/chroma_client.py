import chromadb
from chromadb.config import Settings

client = chromadb.Client(
    Settings(
        persist_directory="data/chroma_db",
        is_persistent=True
    )
)

collection = client.get_or_create_collection(name="hr_policies")
