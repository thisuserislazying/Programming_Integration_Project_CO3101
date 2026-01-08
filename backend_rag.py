import sys
import os
import json
import re

# Fix loi Windows (resource module)
if os.name == 'nt':
    import types
    module = types.ModuleType("resource")
    module.RLIMIT_NOFILE = 1
    module.setrlimit = lambda *args, **kwargs: None
    module.getrlimit = lambda *args, **kwargs: (0, 0)
    sys.modules["resource"] = module

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles 
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google.genai.errors import ServerError

from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.chat_engine import ContextChatEngine

# Cau hinh
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khoi tao AI models
embed_model = GoogleGenAIEmbedding(model_name="models/text-embedding-004", api_key=GEMINI_API_KEY)
llm = GoogleGenAI(model="gemini-2.5-flash", api_key=GEMINI_API_KEY, temperature=0.1)
Settings.embed_model = embed_model
Settings.llm = llm
reranker = SentenceTransformerRerank(model="cross-encoder/ms-marco-MiniLM-L-6-v2", top_n=3)

# Prompt he thong
SYSTEM_PROMPT = (
    "Bạn là một giảng viên môn Kinh tế Chính trị Mác - Lênin uy tín và nhiệt huyết tại Đại học Bách Khoa.\n"
    "Nhiệm vụ của bạn là giải thích các khái niệm và trả lời sinh viên dựa trên ngữ cảnh (Context) được cung cấp.\n"
    "Quy tắc quan trọng:\n"
    "1. Luôn ưu tiên dùng thông tin từ giáo trình được cung cấp để trả lời.\n"
    "2. Nếu ngữ cảnh không có thông tin, hãy nói rõ là giáo trình không đề cập, đừng tự bịa.\n"
    "3. Giải thích kĩ lưỡng, sư phạm, có ví dụ minh họa thực tế khác với giáo trình.\n"
    "4. Giọng văn: Thân thiện, dễ hiểu, khuyến khích tinh thần học tập. Xưng hô: 'mình' - 'bạn'.\n"
    "5. [QUAN TRỌNG] Về định dạng:\n"
    "   - TUYỆT ĐỐI KHÔNG sử dụng dấu thăng (#, ##, ###) để làm tiêu đề.\n"
    "   - Hãy sử dụng chữ IN ĐẬM để làm tiêu đề các mục lớn.\n"
    "   - Sử dụng dấu gạch ngang (-) không sử dụng các dấu (.) hay dấu (*).\n"
    "6. Khi đưa ra ví dụ minh họa thì hãy lấy các ví dụ thực tế, dễ hình dung ngoài giáo trình.\n"
    "7. Hãy chia các ý chính thành các đoạn nhỏ, xuống dòng hợp lý để dễ đọc.\n"
)

# Bien toan cuc
GLOBAL_ENGINE = None  # Engine dung chung cho tat ca moi nguoi
response_cache = {}
CACHE_FILE = "cache_answers.json"
index = None # Them bien index de quan ly

# Khoi tao he thong (Cache & Data & Engine)
def init_system():
    global GLOBAL_ENGINE, response_cache, index
    
    # Load cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                response_cache = json.load(f)
        except: response_cache = {}

    # Load du lieu & Khoi tao Engine
    if os.path.exists("./storage"):
        try:
            ctx = StorageContext.from_defaults(persist_dir="./storage")
            index = load_index_from_storage(ctx)
            
            # Tao Retriever Hybrid
            vector_retriever = index.as_retriever(similarity_top_k=10)
            final_retriever = vector_retriever
            
            try:
                nodes = list(index.docstore.docs.values())
                bm25_retriever = BM25Retriever.from_defaults(
                    nodes=nodes, similarity_top_k=10, language="vi"
                )
                final_retriever = QueryFusionRetriever(
                    [vector_retriever, bm25_retriever],
                    similarity_top_k=15, num_queries=1, use_async=True
                )
            except: pass

            # Khoi tao Engine toan cuc 1 lan duy nhat
            GLOBAL_ENGINE = ContextChatEngine.from_defaults(
                retriever=final_retriever,
                llm=llm,
                memory=ChatMemoryBuffer.from_defaults(token_limit=3000),
                system_prompt=SYSTEM_PROMPT,
                node_postprocessors=[reranker]
            )
            
        except Exception as e:
            print(f"Lỗi khởi tạo: {e}")

init_system()

# Luu cache xuong file
def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(response_cache, f, ensure_ascii=False, indent=4)
    except: pass

# Chuan hoa cau hoi
def normalize_query_key(query: str) -> str:
    q = query.lower()
    q = re.sub(r'[^\w\s]', ' ', q)
    q = re.sub(r'\s+', ' ', q)
    return q.strip()

# Lam dep ten file
def prettify_source(file_name):
    name = file_name.replace(".txt", "")
    mapping = {
        "Chuong_0": "Chương 0: PHẦN MỞ ĐẦU / KHÁI QUÁT",
        "Chuong_1": "Chương 1: ĐỐI TƯỢNG, PHƯƠNG PHÁP & CHỨC NĂNG CỦA KTCT MÁC - LÊNIN",
        "Chuong_2": "Chương 2: KINH TẾ THỊ TRƯỜNG & CÁC QUY LUẬT CƠ BẢN",
        "Chuong_3": "Chương 3: LÝ LUẬN CỦA C.MÁC VỀ GIÁ TRỊ THẶNG DƯ",
        "Chuong_4": "Chương 4: TÍCH LŨY & TÁI SẢN XUẤT TRONG NỀN KTTT",
        "Chuong_5": "Chương 5: CẠNH TRANH, ĐỘC QUYỀN & VAI TRÒ CỦA NHÀ NƯỚC",
        "Chuong_6": "Chương 6: KINH TẾ THỊ TRƯỜNG ĐỊNH HƯỚNG XHCN Ở VIỆT NAM",
        "Chuong_7": "Chương 7: LỢI ÍCH KINH TẾ & HÀI HÒA QUAN HỆ LỢI ÍCH",
        "Chuong_8": "Chương 8: CÔNG NGHIỆP HÓA, HIỆN ĐẠI HÓA Ở VIỆT NAM",
        "Chuong_9": "Chương 9: HỘI NHẬP KINH TẾ QUỐC TẾ & XÂY DỰNG NỀN KINH TẾ ĐỘC LẬP TỰ CHỦ"
    }
    return mapping.get(name, name)

# Xu ly cau hoi (Streaming) - KHONG session_id
async def response_generator(query: str):
    # Kiem tra neu Engine chua san sang
    if GLOBAL_ENGINE is None:
        yield "Hệ thống đang khởi động hoặc chưa có dữ liệu."
        return

    try:
        # Kiem tra cache
        cache_key = normalize_query_key(query)
        if cache_key in response_cache:
            yield response_cache[cache_key]
            return

        # Goi AI tu Global Engine
        try:
            streaming_response = await GLOBAL_ENGINE.astream_chat(query)
            full_text = ""
            
            async for token in streaming_response.async_response_gen():
                full_text += token
                yield token
            
            # Xu ly nguon
            final_resp = str(streaming_response)
            refusals = ["không có thông tin", "không được đề cập", "tôi không biết", "xin lỗi"]
            is_refusal = any(p in final_resp.lower() for p in refusals)
            
            clean_sources = []
            seen = set()
            if not is_refusal and streaming_response.source_nodes:
                for node in streaming_response.source_nodes:
                    fname = node.node.metadata.get('file_name', '')
                    if not fname or any(x in fname for x in ["Loi_Mo_Dau", "C00", "C0_"]): continue
                    if fname not in seen:
                        seen.add(fname)
                        clean_sources.append(prettify_source(fname))
            
            if clean_sources:
                src_html = "<br>".join([f"📖 <i>{src}</i>" for src in clean_sources[:3]])
                append_text = f"\n\n<hr><b>📚 Nguồn tham khảo:</b><br>{src_html}"
                yield append_text
                full_text += append_text
            
            # Luu cache
            response_cache[cache_key] = full_text
            save_cache()

        except ServerError:
            yield "Lỗi: Server bận (503)."
        except Exception as e:
            yield f"Lỗi: {str(e)}"

    except Exception as e:
        yield f"Lỗi hệ thống: {str(e)}"

# API Endpoint - KHONG session_id
class QueryRequest(BaseModel):
    query: str

@app.post("/api/query")
async def handle_query(request: QueryRequest):
    return StreamingResponse(response_generator(request.query), media_type="text/plain")

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)