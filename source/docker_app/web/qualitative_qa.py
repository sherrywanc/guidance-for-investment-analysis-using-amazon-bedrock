import streamlit as st
from genAI.utils.assistant.embeddingsDataLoad import vectorize_and_store
from genAI.chains.interactiveQAChain import get_qa_answer

def render():
    st.subheader("Qualitative Data Q&A")

    # File upload section
    uploaded_files = st.file_uploader("Upload Financial Documents", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        total_files = len(uploaded_files)

        with st.spinner(f"Processing {total_files} documents..."):
            progress_bar = st.progress(0)
            for i, uploaded_file in enumerate(uploaded_files):
                file_key = f'vectorized_{uploaded_file.name}'

                # Check if the document is already processed
                if file_key not in st.session_state:
                    st.write(f"Processing file: {uploaded_file.name}")

                    # Read file content
                    file_content = uploaded_file.read()

                    # Vectorize and store document content
                    db = vectorize_and_store(file_content, uploaded_file.name)

                    if db:
                        st.success(f"Document '{uploaded_file.name}' processed and stored successfully.")
                        st.session_state[file_key] = db  # Store the processed document in session state
                    else:
                        st.error(f"Failed to store the document '{uploaded_file.name}'.")

                else:
                    st.write(f"Document '{uploaded_file.name}' has already been processed.")

                # Update progress bar
                progress_bar.progress((i + 1) / total_files)

        progress_bar.empty()

    if uploaded_files and all([f'vectorized_{file.name}' in st.session_state for file in uploaded_files]):
        st.text("You can now ask questions about the uploaded documents.")
        question_input = st.text_input("Ask a question about the uploaded documents:")
        get_answer_button = st.button("Get Answer", key="get_answer_btn")

        if get_answer_button:
            if question_input:
                with st.spinner("Fetching the answer..."):
                    try:
                        # Aggregate all processed documents
                        aggregated_db = []
                        for uploaded_file in uploaded_files:
                            aggregated_db.append(st.session_state[f'vectorized_{uploaded_file.name}'])
                        
                        # Get the answer from the function, log the result
                        answer = get_qa_answer(question_input)
                        
                        st.subheader("Answer")

                        if isinstance(answer, str):
                            st.write(answer)
                        elif isinstance(answer, dict):
                            st.write(answer.get("answer", "No answer found."))

                            with st.expander("Citations"):
                                st.write("Context used to generate the answer:")
                                for document in answer.get("context", []):
                                    st.write(document)
                        elif isinstance(answer, tuple) and len(answer) == 2:
                            st.write(answer[0].get("answer", "No answer found."))

                            with st.expander("Citations"):
                                st.write("Context used to generate the answer:")
                                for document in answer[1]:
                                    st.write(document)
                        else:
                            st.write("Unexpected response format.")
                    except Exception as e:
                        st.error(f"An error occurred while fetching the answer: {e}")
            else:
                st.warning("Please enter a question to get an answer.")
    else:
        st.info("Upload documents and ensure they are processed successfully before querying.")
