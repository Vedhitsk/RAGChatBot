import streamlit as st
import os
from dotenv import load_dotenv
from rag_backend import verify_user, process_documents_for_department, get_department_chat_chain

# Initialize environment variables
load_dotenv()

st.set_page_config(page_title="Enterprise Policy Hub", layout="wide")

# Persistent Session State Management
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "current_provider" not in st.session_state:
    st.session_state.current_provider = "Groq"

# Employee States
if "current_chain" not in st.session_state:
    st.session_state.current_chain = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Admin States
if "admin_chain" not in st.session_state:
    st.session_state.admin_chain = None
if "admin_chat_history" not in st.session_state:
    st.session_state.admin_chat_history = []
if "admin_chat_unlocked" not in st.session_state:
    # Check if universal db already exists from a previous session
    st.session_state.admin_chat_unlocked = os.path.exists(os.path.join("vector_stores", "admin_global"))
if "admin_view_mode" not in st.session_state:
    st.session_state.admin_view_mode = "Upload Policies"

# Ensure local database exists on boot
if not os.path.exists("company_policies.db"):
    from db_init import init_db

    init_db()


def handle_logout():
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.current_chain = None
    st.session_state.chat_history = []
    st.session_state.admin_chain = None
    st.session_state.admin_chat_history = []
    st.rerun()


# ==========================================
# SCREEN 1: AUTHENTICATION INTERFACE
# ==========================================
if not st.session_state.authenticated:
    st.subheader("Protected Access: Enterprise Policy Knowledge Base")

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("login_form"):
            st.write("### Sign In")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Authenticate")

            if submit:
                user = verify_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_info = user
                    st.success("Access Granted.")
                    st.rerun()
                else:
                    st.error("Invalid corporate credentials.")
    with col2:
        st.info(
            "#### Hackathon Demo Credentials:\n\n"
            "* **Admin Portal:** User: `admin` | Pass: `admin123`\n"
            "* **HR Department:** User: `alice_hr` | Pass: `securehr`\n"
            "* **Engineering:** User: `bob_eng` | Pass: `devpass`\n"
            "* **Finance:** User: `charlie_fin` | Pass: `money123`"
        )

# ==========================================
# SCREEN 2: AUTHORIZED INTERFACES
# ==========================================
else:
    user = st.session_state.user_info

    # Sidebar Configuration
    st.sidebar.write("### Connection Profiles")
    provider_choice = st.sidebar.radio("Select AI Engine:", ["Groq", "Gemini"])

    # Handle Model Switching gracefully
    if st.session_state.current_provider != provider_choice:
        st.session_state.current_chain = None
        st.session_state.chat_history = []
        st.session_state.admin_chain = None
        st.session_state.admin_chat_history = []
        st.session_state.current_provider = provider_choice
        st.rerun()

    st.sidebar.markdown("---")

    # Custom Sidebar Navigation for Admin
    if user["role"] == "admin":
        st.sidebar.write("### Admin Controls")
        admin_nav = st.sidebar.radio(
            "Navigation Menu:",
            ["📤 Upload Policies", "🌐 Universal Chat"]
        )
        # Update session state if navigation changes
        if st.session_state.admin_view_mode != admin_nav:
            st.session_state.admin_view_mode = admin_nav
            st.rerun()
        st.sidebar.markdown("---")

    if st.sidebar.button("Sign Out System", type="secondary"):
        handle_logout()

    # ==========================================
    # ADMIN WORKFLOW
    # ==========================================
    if user["role"] == "admin":

        # VIEW 1: UPLOAD MODE
        if st.session_state.admin_view_mode == "📤 Upload Policies":
            st.markdown(f"### Enterprise Policy Hub | Profile: `{user['username']}` (Admin Publisher)")
            st.header("Administrative Command Console")
            st.info(
                "System Authorization Mode: Global Publisher. Uploads are routed to target groups AND the Universal Chat.")

            target_dept = st.selectbox("Target Access Group (Department)", ["HR", "Engineering", "Finance"])
            uploaded_files = st.file_uploader("Select Policy Files", type=["pdf", "docx"], accept_multiple_files=True)

            if st.button("Commit Documents to Group Index", type="primary"):
                if not uploaded_files:
                    st.error("Execution halted: No file payloads detected.")
                else:
                    with st.spinner(f"Compiling vector arrays for {target_dept}..."):
                        success = process_documents_for_department(uploaded_files, target_dept)
                        if success:
                            st.success(
                                f"Security Matrix updated. Files mapped to {target_dept} and Universal Admin Database.")
                            st.session_state.admin_chat_unlocked = True
                            st.session_state.admin_chain = None

                            # VIEW 2: UNIVERSAL CHAT MODE
        elif st.session_state.admin_view_mode == "🌐 Universal Chat":
            st.markdown(f"### Universal Repository Workspace | Profile: `{user['username']}` (Global Access)")
            st.header("Global Policy Intelligence")

            if not st.session_state.admin_chat_unlocked:
                st.info(
                    "🔒 Universal Chat is currently locked. Switch to 'Upload Policies' to initialize the global database.")
            else:
                if st.session_state.admin_chain is None:
                    with st.spinner(f"Initializing Universal Database using {provider_choice}..."):
                        st.session_state.admin_chain = get_department_chat_chain("admin_global", provider_choice)

                # Render Chat History
                for message in st.session_state.admin_chat_history:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

                # Native Chat Input (Pinned to Bottom seamlessly)
                if admin_question := st.chat_input("Query all uploaded documents across all departments..."):
                    with st.chat_message("user"):
                        st.markdown(admin_question)
                    st.session_state.admin_chat_history.append({"role": "user", "content": admin_question})

                    with st.chat_message("assistant"):
                        with st.spinner("Executing context synthesis..."):
                            try:
                                response = st.session_state.admin_chain({"question": admin_question})
                                answer = response['answer']
                                st.markdown(answer)

                                with st.expander("Security Context Verification Logs"):
                                    for doc in response.get('source_documents', []):
                                        st.caption(f"**Source:** {doc.metadata.get('source', 'Unknown')}")
                                        st.write(doc.page_content[:250] + "...")
                                        st.divider()

                                st.session_state.admin_chat_history.append({"role": "assistant", "content": answer})
                            except Exception as e:
                                st.error(f"Query Failed: {e}")

    # ==========================================
    # EMPLOYEE WORKFLOW (Standard Isolated Chat)
    # ==========================================
    else:
        st.markdown(f"### Enterprise Policy Hub | Profile: `{user['username']}` ({user['department']})")
        st.header(f"Departmental Repository Workspace: {user['department']}")

        if st.session_state.current_chain is None:
            with st.spinner(f"Initializing partitioned storage streams using {provider_choice}..."):
                try:
                    st.session_state.current_chain = get_department_chat_chain(user["department"], provider_choice)
                except Exception as e:
                    st.error(f"Initialization Failed: {e}")

        if st.session_state.current_chain is None:
            st.info(
                f"No policy documentation published for the {user['department']} segment yet. Contact system admin.")
        else:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if user_question := st.chat_input("Query group explicit policy databases..."):
                with st.chat_message("user"):
                    st.markdown(user_question)
                st.session_state.chat_history.append({"role": "user", "content": user_question})

                with st.chat_message("assistant"):
                    with st.spinner("Executing context synthesis..."):
                        try:
                            response = st.session_state.current_chain({"question": user_question})
                            answer = response['answer']
                            st.markdown(answer)

                            with st.expander("Security Context Verification Logs"):
                                for doc in response.get('source_documents', []):
                                    st.caption(f"**Chunk Source Identifier:** {doc.metadata.get('source', 'Unknown')}")
                                    st.write(doc.page_content[:250] + "...")
                                    st.divider()

                            st.session_state.chat_history.append({"role": "assistant", "content": answer})
                        except Exception as e:
                            st.error(f"Query Failed: {e}")