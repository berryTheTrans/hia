import streamlit as st
from components.footer import show_footer
from config.app_config import ANALYSIS_DAILY_LIMIT
from datetime import datetime

def show_sidebar():
    with st.sidebar:
        st.title("💬 Chat Sessions")
        
        if st.button("+ New Analysis Session", use_container_width=True):
            now = datetime.now()
            session = {
                "id": f"local-{now.strftime('%Y%m%d%H%M%S%f')}",
                "title": f"{now.strftime('%d-%m-%Y')} | {now.strftime('%H:%M:%S')}",
                "created_at": now.isoformat(),
            }
            if "local_sessions" not in st.session_state:
                st.session_state.local_sessions = []
            if "local_messages" not in st.session_state:
                st.session_state.local_messages = {}
            st.session_state.local_sessions.insert(0, session)
            st.session_state.local_messages[session["id"]] = []
            st.session_state.current_session = session
            st.rerun()

        # Add analysis counter
        if 'analysis_count' not in st.session_state:
            st.session_state.analysis_count = 0
        
        remaining = ANALYSIS_DAILY_LIMIT - st.session_state.analysis_count
        st.markdown(
            f"""
            <div style='
                padding: 0.5rem;
                border-radius: 0.5rem;
                background: rgba(100, 181, 246, 0.1);
                margin: 0.5rem 0;
                text-align: center;
                font-size: 0.9em;
            '>
                <p style='margin: 0; color: #666;'>Daily Analysis Limit</p>
                <p style='
                    margin: 0.2rem 0 0 0;
                    color: {"#1976D2" if remaining > 3 else "#FF4B4B"};
                    font-weight: 500;
                '>
                    {remaining}/{ANALYSIS_DAILY_LIMIT} remaining
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        show_session_list()
        
        # Add footer to sidebar
        show_footer(in_sidebar=True)

def show_session_list():
    sessions = st.session_state.get("local_sessions", [])
    if sessions:
        st.subheader("Previous Sessions")
        render_session_list(sessions)
    else:
        st.info("No previous sessions")

def render_session_list(sessions):
    # Store deletion state
    if 'delete_confirmation' not in st.session_state:
        st.session_state.delete_confirmation = None
    
    for session in sessions:
        render_session_item(session)

def render_session_item(session):
    if not session or not isinstance(session, dict) or 'id' not in session:
        return
        
    session_id = session['id']
    current_session = st.session_state.get('current_session', {})
    current_session_id = current_session.get('id') if isinstance(current_session, dict) else None
    
    # Create container for each session
    with st.container():
        # Session title and delete button side by side
        title_col, delete_col = st.columns([4, 1])
        
        with title_col:
            if st.button(f"📝 {session['title']}", key=f"session_{session_id}", use_container_width=True):
                st.session_state.current_session = session
                st.rerun()
        
        with delete_col:
            if st.button("🗑️", key=f"delete_{session_id}", help="Delete this session"):
                if st.session_state.delete_confirmation == session_id:
                    st.session_state.delete_confirmation = None
                else:
                    st.session_state.delete_confirmation = session_id
                st.rerun()
        
        # Show confirmation below if this session is being deleted
        if st.session_state.delete_confirmation == session_id:
            st.warning("Delete above session?")
            left_btn, right_btn = st.columns(2)
            with left_btn:
                if st.button("Yes", key=f"confirm_delete_{session_id}", type="primary", use_container_width=True):
                    handle_delete_confirmation(session_id, current_session_id)
            with right_btn:
                if st.button("No", key=f"cancel_delete_{session_id}", use_container_width=True):
                    st.session_state.delete_confirmation = None
                    st.rerun()

def handle_delete_confirmation(session_id, current_session_id):
    if not session_id:
        st.error("Invalid session")
        return
        
    # Delete locally
    sessions = st.session_state.get("local_sessions", [])
    st.session_state.local_sessions = [s for s in sessions if s.get("id") != session_id]
    if "local_messages" in st.session_state and session_id in st.session_state.local_messages:
        del st.session_state.local_messages[session_id]
    st.session_state.delete_confirmation = None
    if current_session_id and current_session_id == session_id:
        st.session_state.current_session = None
    st.rerun()
