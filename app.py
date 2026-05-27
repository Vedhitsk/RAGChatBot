import streamlit as st
import os
from rag_backend import process_documents, get_conversation_chain
from dotenv import load_dotenv
load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="Policy RAG Chatbot", page_icon="📄", layout="wide")

# Initialize Session States
if "conversation" not in st.session_state:
    st.session_state.conversation = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "process_complete" not in st.session_state:
    st.session_state.process_complete = False

st.title("📄 Policy Intelligence Chatbot")
st.subheader("Upload your policy documents and ask questions naturally.")

# --- Sidebar Configuration ---
with st.sidebar:

    st.header("Document Upload")
    uploaded_files = st.file_uploader(
        "Upload Policy Documents (PDF or DOCX)", 
        type=["pdf", "docx"], 
        accept_multiple_files=True
    )
    
    process_button = st.button("Process Documents", type="primary")

    if process_button:
        if not uploaded_files:
            st.error("Please upload at least one document!")
        else:
            with st.spinner("Analyzing and indexing documents..."):
                try:
                    # Build vector store and conversation chain
                    vector_store = process_documents(uploaded_files)
                    st.session_state.conversation = get_conversation_chain(vector_store, groq_api_key)
                    st.session_state.process_complete = True
                    st.success("Documents processed successfully! You can now chat.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# --- Main Chat Interface ---
if st.session_state.process_complete:
    
    # Display existing chat messages
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    if user_question := st.chat_input("Ask something about your policy documents:"):
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_question)
        st.session_state.chat_history.append({"role": "user", "content": user_question})

        # Generate response from RAG Chain
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Extract history for LangChain format: [(user, ai), ...]
                formatted_history = []
                history_list = st.session_state.chat_history[:-1]  # Exclude the question just asked
                temp_user_msg = ""
                for msg in history_list:
                    if msg["role"] == "user":
                        temp_user_msg = msg["content"]
                    elif msg["role"] == "assistant":
                        formatted_history.append((temp_user_msg, msg["content"]))
                        
                response = st.session_state.conversation({
                    "question": user_question,
                    "chat_history": formatted_history
                })
                answer = response['answer']
                st.markdown(answer)
                
                # Optional: Expand to see which parts of the doc were referenced
                with st.expander("View Source Context"):
                    for doc in response.get('source_documents', []):
                        st.caption(f"**Source:** {doc.metadata.get('source', 'Unknown')}")
                        st.write(doc.page_content[:300] + "...")
                        st.divider()
                        
        st.session_state.chat_history.append({"role": "assistant", "content": answer})

else:
    # Landing state prompt
    st.info("← Please enter your Groq API key and upload documents in the sidebar to begin.")