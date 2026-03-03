import streamlit as st
from components.sidebar import show_sidebar
from components.analysis_form import show_analysis_form
from components.footer import show_footer
from config.app_config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON
from services.ai_service import get_chat_response
from datetime import datetime

# Must be the first Streamlit command
st.set_page_config(
    page_title="HIA - Health Insights Agent", page_icon="🩺", layout="wide"
)

# Lightweight local session/message store (no auth)
if "local_sessions" not in st.session_state:
    st.session_state.local_sessions = []
if "local_messages" not in st.session_state:
    st.session_state.local_messages = {}
if "current_session" not in st.session_state:
    st.session_state.current_session = None

# Hide all Streamlit form-related elements
st.markdown(
    """
    <style>
        /* Hide form submission helper text */
        div[data-testid="InputInstructions"] > span:nth-child(1) {
            visibility: hidden;
        }
    </style>
""",
    unsafe_allow_html=True,
)


def show_welcome_screen():
    st.markdown(
        f"""
        <div style='text-align: center; padding: 50px;'>
            <h1>{APP_ICON} {APP_NAME}</h1>
            <h3>{APP_DESCRIPTION}</h3>
            <p style='font-size: 1.2em; color: #666;'>{APP_TAGLINE}</p>
            <p>Start by creating a new analysis session</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        if st.button(
            "➕ Create New Analysis Session", use_container_width=True, type="primary"
        ):
            now = datetime.now()
            session = {
                "id": f"local-{now.strftime('%Y%m%d%H%M%S%f')}",
                "title": f"{now.strftime('%d-%m-%Y')} | {now.strftime('%H:%M:%S')}",
                "created_at": now.isoformat(),
            }
            st.session_state.local_sessions.insert(0, session)
            st.session_state.local_messages[session["id"]] = []
            st.session_state.current_session = session
            st.rerun()


def show_chat_history():
    session_id = st.session_state.current_session["id"]
    messages = st.session_state.local_messages.get(session_id, [])

    for msg in messages:
        if msg.get("role") == "system":
            continue
        if msg["role"] == "user":
            st.info(msg["content"])
        else:
            st.success(msg["content"])
    return messages


def handle_chat_input(messages):
    if prompt := st.chat_input("Ask a follow-up question about the report..."):
        # Display user message immediately
        st.info(prompt)

        # Save user message
        session_id = st.session_state.current_session["id"]
        st.session_state.local_messages.setdefault(session_id, []).append(
            {"role": "user", "content": prompt, "created_at": datetime.now().isoformat()}
        )

        # Get context (report text)
        # We try to get it from session state first (for immediate use)
        context_text = st.session_state.get("current_report_text", "")

        # If not in session state, try to retrieve from stored system message
        if not context_text and messages:
            for msg in messages:
                if msg.get("role") == "system" and "__REPORT_TEXT__" in msg.get(
                    "content", ""
                ):
                    # Extract report text from system message
                    content = msg.get("content", "")
                    start_idx = content.find("__REPORT_TEXT__\n") + len(
                        "__REPORT_TEXT__\n"
                    )
                    end_idx = content.find("\n__END_REPORT_TEXT__")
                    if start_idx > len("__REPORT_TEXT__\n") - 1 and end_idx > start_idx:
                        context_text = content[start_idx:end_idx]
                        # Also restore to session state for future use
                        st.session_state.current_report_text = context_text
                        break

        with st.spinner("Thinking..."):
            response = get_chat_response(prompt, context_text, messages)

            st.success(response)

            # Save AI response
            st.session_state.local_messages.setdefault(session_id, []).append(
                {
                    "role": "assistant",
                    "content": response,
                    "created_at": datetime.now().isoformat(),
                }
            )
            # Rerun to update history display properly
            st.rerun()


def show_user_greeting():
    pass


def main():
    # Show user greeting at the top
    show_user_greeting()

    # Show sidebar
    show_sidebar()

    # Main chat area
    if st.session_state.get("current_session"):
        messages = show_chat_history()

        # If we have messages (meaning analysis is done), show chat input
        # Otherwise show analysis form
        if messages:
            # We can still show the analysis form collapsed or just hide it
            # For better UX, if analysis is done, we might not want to show the form again
            # unless the user wants to re-analyze/start over.
            # But the current form design allows re-analysis.
            # Let's put the analysis form in an expander if analysis is done.
            with st.expander("New Analysis / Update Report", expanded=False):
                show_analysis_form()

            handle_chat_input(messages)
        else:
            show_analysis_form()
    else:
        show_welcome_screen()


if __name__ == "__main__":
    main()
