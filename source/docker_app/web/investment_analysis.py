import streamlit as st
from genAI.agents.investment_agent import analyze_investment
from docx import Document
import io

def render():
    st.subheader("Investment Analysis using LLM")
    st.write("Enter a stock ticker or ask generic question below to start the analysis.")

    query_text = st.text_input("Portfolio Ticker (e.g., AMZN, ZM or How semiconductor sector is doing today?):", "")
    analyze_button = st.button("Analyze Investment", key="analyze_btn_po")

    if analyze_button and query_text:
        with st.spinner(f"Analyzing financials for {query_text}..."):
            try:
                user_input = f"Can you analyze the yearly financials for {query_text}?"
                final_output, parsed_data = analyze_investment(user_input)

                st.session_state['final_output'] = final_output
                st.session_state['parsed_data'] = parsed_data
                st.session_state['query_text'] = query_text

                st.success("Analysis complete. Check the results below.")
                st.markdown(f"**query_text:** {query_text}")
                st.markdown(final_output)

            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")
                st.write("Please check your input or try again later.")
    elif analyze_button:
        st.warning("Please enter a valid stock query_text.")
    st.markdown("---")  # Horizontal line for separation

