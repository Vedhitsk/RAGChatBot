# Policy Intelligence RAG Chatbot

A high-performance Retrieval-Augmented Generation (RAG) chatbot designed to extract information and answer questions based on uploaded policy documents (PDF and DOCX formats). This application uses Streamlit for the user interface, LangChain for orchestration, FAISS for in-memory vector storage, and Groq (Llama 3) for ultra-fast Large Language Model (LLM) inference.

---

## Project File Structure

```text
rag-chatbot/
│
├── app.py              # Main Streamlit UI and session state management
├── rag_backend.py      # Core RAG pipeline (document ingestion, embedding, & QA chain)
├── requirements.txt    # Project dependencies
└── README.md           # Project documentation
```

---

## Core Architecture and Code Logic Structure

```
[User Documents] -> [Text Extraction] -> [Text Chunking] -> [Vector Embeddings] -> [FAISS Vector DB]
                                                                                       |
                                                                              (Context Retrieval)
                                                                                       v
[User Question] + [Chat History Memory] -> [Standalone Query] -> [Groq LLM Inference] -> [Final Answer]
```

---

### 1. Data Ingestion and Preprocessing (rag_backend.py -> process_documents)
- **File Handling**: Streamlit processes uploaded files as raw bytes in memory. The backend writes these bytes into temporary disk storage via the standard tempfile library so that LangChain's document loaders can access them natively.

- **Text Extraction**: Files are conditionally routed based on their file extension: .pdf files are parsed using PyPDFLoader, and .docx files are parsed using Docx2txtLoader.

- **Text Chunking**: To optimize the LLM's context window and ensure high-granularity retrieval, the raw text is partitioned using RecursiveCharacterTextSplitter. It is configured with a chunk size of 1000 characters and a chunk overlap of 200 characters, preserving contextual continuity across boundaries.

### 2. Embedding and Vectorization (rag_backend.py -> process_documents)
- **Vector Embeddings**: The generated text chunks are converted into dense mathematical vectors using the HuggingFace all-MiniLM-L6-v2 model. This model runs locally to extract semantic meaning from sentences without relying on external API calls.

- **Vector Store**: The resulting vectors are indexed inside a FAISS (Facebook AI Similarity Search) structure. This in-memory vector database allows for highly efficient semantic similarity searches when querying the document collection.

### 3. Memory and Retrieval Chain Logic (rag_backend.py -> get_conversation_chain)
- **LLM Engine**: The pipeline initializes the ChatGroq interface, pointing to the high-throughput llama3-8b-8192 model with a low temperature setting (0.2) to minimize hallucinations and enforce factual adherence.

- **Conversation Memory**: LangChain's ConversationBufferMemory is integrated into the chain. It is configured to pass message objects explicitly and maps to the output_key='answer' to isolate the final response text from background source documents.

- **The Conversational Retrieval Chain**: This component orchestrates the LLM, the FAISS retriever, and the chat history. When a user submits a follow-up question, the logic executes as follows:

- **The chain combines the active chat history and the new question, instructing the LLM to synthesize a consolidated "Standalone Question".

- **This standalone question is used to query the FAISS vector database, retrieving the top 3 most semantically relevant text chunks.

- **The retrieved chunks and the standalone question are compiled into a prompt template and sent to the Groq LLM to generate the final response.

### 4. UI Rendering and Persistent States (app.py)
- **Streamlit Session State**: Streamlit re-executes scripts from top to bottom upon every user interaction. To maintain continuity, st.session_state is utilized to persistently store the instantiated conversation chain and the cumulative chat history list across execution cycles.

- **Dynamic Chat Interface**: Past interactions are rendered sequentially using st.chat_message. When a new query is submitted, the system triggers a visual processing spinner, queries the backend chain, appends both the question and answer to the session state, and exposes the exact text fragments used as context inside a collapsible UI element.