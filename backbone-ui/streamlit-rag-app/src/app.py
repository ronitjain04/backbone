import streamlit as st
from rag_llm import rag_llm_call

# def main():
#     st.title("RAG LLM Query Interface")
    
#     query = st.text_input("Enter your query:")
    
#     if st.button("Submit"):
#         if query:
#             with st.spinner("Processing..."):
#                 response, rag_results_context, slides_used = rag_llm_call(query)
#             st.success("Response:")
#             st.write(response)

#             st.success("Context:")
#             for slide in slides_used:
#                 st.write(slide)
#             st.json(rag_results_context, expanded=True)
#         else:
#             st.warning("Please enter a query.")

# if __name__ == "__main__":
#     main()

st.set_page_config(page_title="RAG LLM Chat", page_icon="💬")

st.title("💬 RAG LLM Chat")

# Initialize chat history in session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def display_chat():
    for entry in st.session_state.chat_history:
        st.markdown(f"**You:** {entry['question']}")
        st.markdown(f"**Assistant:** {entry['response']}")
        if entry['slides_used']:
            st.markdown("**Slides Used:**")
            for slide in entry['slides_used']:
                st.markdown(f"- {slide}")
        if entry['context']:
            with st.expander("Show Context"):
                for idx, context_str in enumerate(entry['context']):
                    st.markdown(f"**Context {idx+1}:** {context_str}")

# Input area at the bottom
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your question:", key="input")
    submit = st.form_submit_button("Send")

if submit and user_input:
    with st.spinner("Thinking..."):
        response, rag_results_context, slides_used = rag_llm_call(user_input)
    # Save to chat history
    st.session_state.chat_history.append({
        "question": user_input,
        "response": response,
        "context": rag_results_context,
        "slides_used": slides_used
    })

# Display the chat
display_chat()