import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory
from dotenv import load_dotenv
load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
groq_model = os.getenv("GROQ_MODEL")
gemini_model = os.getenv("GEMINI_MODEL")

def process_documents(uploaded_files):
    """Loads uploaded files, splits text, and creates a FAISS vector store."""
    documents = []
    
    for uploaded_file in uploaded_files:
        # Streamlit files are bytes, so we write to a temp file for LangChain loaders
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name

        # Load based on file extension
        if uploaded_file.name.endswith('.pdf'):
            loader = PyPDFLoader(temp_path)
            documents.extend(loader.load())
        elif uploaded_file.name.endswith('.docx') or uploaded_file.name.endswith('.doc'):
            loader = Docx2txtLoader(temp_path)
            documents.extend(loader.load())
            
        os.unlink(temp_path)  # Clean up temp file

    # Split documents into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)

    # Create embeddings and store in FAISS vector database
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    return vector_store

def get_conversation_chain(vector_store, groq_api_key, model_name=groq_model):
    """Creates a conversational QA chain using Groq LLM."""
    llm = ChatGroq(
        groq_api_key=groq_api_key, 
        model_name=model_name,
        temperature=0.2
    )
    
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        return_source_documents=True
    )
    
    return conversation_chain