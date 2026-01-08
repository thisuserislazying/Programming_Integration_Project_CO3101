import os
import shutil
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

embed_model = GoogleGenAIEmbedding(
    model_name="models/text-embedding-004",
    api_key=GEMINI_API_KEY
)

llm = GoogleGenAI(
    model="gemini-2.5-flash", 
    api_key=GEMINI_API_KEY,
    temperature=0.1
)

Settings.embed_model = embed_model
Settings.llm = llm
Settings.text_splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=200)

def create_knowledge_base():
    if os.path.exists("./storage"):
        shutil.rmtree("./storage")

    try:
        # Tự động bỏ qua nếu folder data không tồn tại hoặc rỗng
        if not os.path.exists("data"):
            return

        documents = SimpleDirectoryReader(input_dir="data").load_data()
        
        if documents:
            index = VectorStoreIndex.from_documents(documents)
            index.storage_context.persist(persist_dir="./storage")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_knowledge_base()