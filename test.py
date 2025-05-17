import streamlit as st
from assistant import TravelAssistant
import json

st.set_page_config(
    page_title="Travel Buddy - AI Travel Assistant",
    page_icon="✈️",
    layout="centered"
)

st.title("🌍 Travel Buddy")
st.caption("Your AI-powered travel assistant - ask anything about your destinations")

# Initialize assistant and conversation
if "assistant" not in st.session_state:
    st.session_state.assistant = TravelAssistant()

if "conversation" not in st.session_state:
    st.session_state.conversation = []

# Chat display
for message_data in st.session_state.conversation:
    with st.chat_message(message_data["role"]):
        st.markdown(message_data["content"])

        if message_data["role"] == "assistant" and "suggestions" in message_data:
            st.markdown("**You might want to know:**")
            cols = st.columns(2)
            for idx, suggestion in enumerate(message_data["suggestions"][:4]):
                with cols[idx % 2]:
                    if st.button(suggestion, key=f"sugg_{idx}_{suggestion}"):
                        st.session_state["user_input"] = suggestion
                        st.rerun()

# Chat input
user_input = st.chat_input("Ask about destinations, packing tips...")

if user_input:
    st.session_state.conversation.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Loading..."):
            response = st.session_state.assistant.generate_response(user_input)
        st.markdown(response["response"])

    st.session_state.conversation.append({
        "role": "assistant",
        "content": response["response"],
        "suggestions": response.get("suggestions", []),
        "sources": response.get("sources", [])
    })

# Divider and bottom section
st.divider()
left_col, _ = st.columns([1, 2])

with left_col:
    st.subheader("Travel Summary")
    if st.button("Generate JSON Summary"):
        with st.spinner("Analyzing your travel chat..."):
            summary_json = st.session_state.assistant.generate_user_summary_json()
            st.session_state["last_summary"] = summary_json

            with open("user_chat_summary.json", "w") as f:
                json.dump(summary_json, f, indent=2)

            st.success("Saved as user_chat_summary.json")

    if "last_summary" in st.session_state:
        st.json(st.session_state["last_summary"])
