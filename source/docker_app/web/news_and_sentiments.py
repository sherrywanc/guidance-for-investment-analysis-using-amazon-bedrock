import streamlit as st
import pandas as pd
from genAI.bedrock_agents.fetchNewsSentiments import fetch_news_and_sentiments

def render():
    st.subheader("News and Sentiments")
    st.write("Enter a stock ticker below to get the latest news and sentiment analysis.")

    ticker = st.text_input("Stock Ticker (e.g., AMZN, RIVN):", "AMZN")
    fetch_button = st.button("Fetch News and Sentiments", key="fetch_news_btn")

    if fetch_button and ticker:
        with st.spinner(f"Fetching news and sentiments for {ticker}..."):
            data = fetch_news_and_sentiments(ticker)

            if data and data.get("news"):
                
                  # Display summary
                st.subheader("Sentiment Summary")
                summary = data.get("summary", "No summary available.")
                st.text_area("Summary", summary, height=200)
                
                # Display news in a detailed format
                st.subheader("News")
                for news_item in data["news"]:
                    st.markdown(f"**Title:** {news_item['title']}")
                    if news_item.get('summary'):
                        st.markdown(f"**Summary:** {news_item['summary']}")
                    if news_item.get('source'):
                        st.markdown(f"**Source:** {news_item['source']}")
                    if news_item.get('ticker_sentiment_label'):
                        st.markdown(f"**Sentiment:** {news_item['ticker_sentiment_label']}")
                    if news_item.get('ticker_sentiment_score'):
                        st.markdown(f"**Sentiment Score:** {news_item['ticker_sentiment_score']}")
                    st.markdown(f"[Read more]({news_item['url']})")
                    st.markdown("---")
            else:
                st.error("No news available. Please check the ticker or try again later.")

if __name__ == "__main__":
    render()
