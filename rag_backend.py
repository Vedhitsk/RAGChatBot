import os
import tempfile
import sqlite3
import bcrypt
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory

DB_PATH = "company_policies.db"
VECTOR_DIR = "vector_stores"


# --- AUTHENTICATION UTILS ---
def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, role, department FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if row and bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8')):
        return {"username": username, "role": row[1], "department": row[2]}
    return None


# --- MULTI-TENANT RAG PROCESSING ---
def process_documents_for_department(uploaded_files, department):
    documents = []
    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name

        if uploaded_file.name.endswith('.pdf'):
            loader = PyPDFLoader(temp_path)
            documents.extend(loader.load())
        elif uploaded_file.name.endswith('.docx') or uploaded_file.name.endswith('.doc'):
            loader = Docx2txtLoader(temp_path)
            documents.extend(loader.load())
        os.unlink(temp_path)

    if not documents:
        return False

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Helper function to save to a specific folder
    def save_to_vector_store(target_dir):
        if os.path.exists(target_dir):
            existing_store = FAISS.load_local(target_dir, embeddings, allow_dangerous_deserialization=True)
            existing_store.add_documents(chunks)
            existing_store.save_local(target_dir)
        else:
            vector_store = FAISS.from_documents(chunks, embeddings)
            os.makedirs(target_dir, exist_ok=True)
            vector_store.save_local(target_dir)

    # 1. Save to the specific Employee Department (e.g., HR, Engineering)
    save_to_vector_store(os.path.join(VECTOR_DIR, department))

    # 2. Save to the Universal Admin Database (so Admin can query everything)
    save_to_vector_store(os.path.join(VECTOR_DIR, "admin_global"))

    return True


def get_department_chat_chain(department, provider_choice):
    dept_vector_path = os.path.join(VECTOR_DIR, department)

    if not os.path.exists(dept_vector_path):
        return None

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vector_store = FAISS.load_local(dept_vector_path, embeddings, allow_dangerous_deserialization=True)

    if provider_choice == "Groq":
        api_key = os.getenv("GROQ_API_KEY")
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        if not api_key:
            raise ValueError("GROQ_API_KEY missing in .env file.")
        llm = ChatGroq(groq_api_key=api_key, model_name=model_name, temperature=0.2)

    elif provider_choice == "Gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing in .env file.")
        llm = ChatGoogleGenerativeAI(google_api_key=api_key, model=model_name, temperature=0.2)

    else:
        raise ValueError("Unsupported model provider selected.")

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True, output_key='answer')

    return ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=retriever, memory=memory, return_source_documents=True
    )