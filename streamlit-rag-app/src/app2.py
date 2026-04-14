import streamlit as st
from process_research_query import rag_llm_call, process_extra_papers
import os

folder = "../research_pdfs"  # or any relative path you want
abs_folder = os.path.abspath(folder)
print(abs_folder)

def main():
    st.title("RAG LLM Research Query Interface")
    
    query = st.text_input("Enter your query:")
    
    if st.button("Submit"):
        if query:
            with st.spinner("Processing..."):
                pdf_map = rag_llm_call(query)
                extra_papers_map, papers_link = process_extra_papers(query)
            st.success("Results by PDF:")
            for pdf_name, results in pdf_map.items():
                st.markdown(f"### {pdf_name}")
                if results:
                    for idx, res in enumerate(results):
                        st.markdown(f"**Result {idx+1}:**")
                        st.write(res.get("text", "No text found"))
                        st.markdown("---")
                else:
                    st.write("No results found for this PDF.")
            st.success("Results from Extra Papers:")
            for paper_name, results in extra_papers_map.items():
                st.markdown(f"### {paper_name}")
                st.markdown(
                    f'<a href="{papers_link[paper_name]}" target="_blank"><button style="font-size:16px;padding:6px 12px;">Open Paper</button></a>',
                    unsafe_allow_html=True
                )
                if results:
                    for idx, res in enumerate(results):
                        st.markdown(f"**Result {idx+1}:**")
                        st.write(res.get("text", "No text found"))
                        st.markdown("---")
                else:
                    st.write("No results found for this paper.")
        else:
            st.warning("Please enter a query.")

if __name__ == "__main__":
    main()

