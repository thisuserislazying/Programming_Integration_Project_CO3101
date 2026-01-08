# 🎓 Learning Assistant for Marxist-Leninist Political Economy

This is a programming project developed for the Programming Integration Project (CO3101) Course.\
The goal of this project is to create an intelligent learning assistant that provides curriculum-grounded answers for the "Marxist-Leninist Political Economy" subject, ensuring accuracy and controlling AI hallucinations through a specialized architecture.


## Project Implementation
The system utilizes a Retrieval-Augmented Generation (RAG) architecture with Google Gemini 2.5 Flash serving as the core reasoning engine.

1. Data Processing Pipeline: Converts raw PDFs and PPTX files into clean, unstructured text corpora.
2. Structural Organization: Normalizes Vietnamese text (NFC), filters out metadata "noise," and splits content into chapter-specific knowledge bases.
3. Semantic Chunking: Segments text into units of 1024 characters with a 200-character overlap using LlamaIndex's SentenceSplitter to preserve contextual meaning.
4. Hybrid Retrieval Strategy: Employs a QueryFusionRetriever that combines BM25 Sparse Search (for exact keywords) with Vector Dense Search (using text-embedding-004) to find the most relevant curriculum segments.
5. Neural Re-ranking: Uses a Cross-Encoder model (ms-marco-MiniLM-L-6-v2) to re-score the top 15 candidates and select only the top 3 most relevant chunks for the final response.
6. Responsive UI: A web interface that supports Streaming Responses, allowing students to see the answer as it is generated, along with explicit source citations.
