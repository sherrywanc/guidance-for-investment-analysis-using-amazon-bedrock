import streamlit as st
from auth.auth import Auth
from config_file import Config
import fundamental_analysis as fundamental_analysis
import investment_analysis as investment_analysis
import financial_data as financial_data
import qualitative_qa as qualitative_qa
import news_and_sentiments as news_and_sentiments

# Initialize the Streamlit app
st.set_page_config(page_title='Investment Analyst Assistant', layout='wide')

# ID of Secrets Manager containing cognito parameters
secrets_manager_id = Config.SECRETS_MANAGER_ID

# Initialise CognitoAuthenticator
authenticator = Auth.get_authenticator(secrets_manager_id)

# Authenticate user, and stop here if not logged in
is_logged_in = authenticator.login()
if not is_logged_in:
    st.stop()

def logout():
    authenticator.logout()

# Sidebar for user authentication and logout
with st.sidebar:
    st.header("User Panel")
    st.text(f"Welcome, {authenticator.get_username()}")
    if st.button("Logout", key="logout_btn", on_click=logout):
        st.write("Logged out successfully.")
    st.markdown("---")  # Horizontal line
    
    # Application details
    st.markdown("""
    ### Application Details

    Welcome to the Investment Analyst Assistant

    This application is designed to assist Investment analysts and investors in evaluating company performance and making informed investment decisions. It provides the following features:

    - **Financial Analysis**: Analyze the yearly financials of companies by entering their stock ticker symbols. The application fetches and processes financial data to provide detailed insights.
    - **Data Visualization**: Visualize financial data through interactive charts and tables, making it easier to understand revenue, expenses, and income metrics.
    - **Interactive Q&A**: Upload Financial PDF documents and ask questions about their content. The application uses advanced AI to process the documents and provide accurate answers.
    - **News & Sentiments**: Analyze latest News and Sentiments for the stock.

    ### How to Use the Application

    1. **Analysis Overview**: Start by entering a stock ticker in the 'Analysis Overview' tab and click 'Analyze Financials' to get detailed financial analysis.
    2. **Financial Data**: View detailed financial data in various formats including JSON, tables, and interactive charts in the 'Financial Data' tab.
    3. **Interactive Q&A**: Upload relevant PDF documents and use the Q&A feature to ask questions about the content. This can help you dive deeper into specific areas of interest.
    4. **News and Sentiments**": Start by entering a stock ticker to get latest News and Sentiment data about the stock.
    
    Explore these features through the tabs above and enhance your investment research and analysis process.
    """)

# Main content area
st.title("Investment Analyst Assistant")

# Main Tabs for the application
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Fundamental Analysis using LLM", "Financial Data", "Qualitative Data Q&A", "News and Sentiments", "Investment Analysis"])

# Render the content of each tab
with tab1:
    fundamental_analysis.render()

with tab2:
    financial_data.render()

with tab3:
    qualitative_qa.render()

with tab4:
    news_and_sentiments.render()

with tab5:
    investment_analysis.render()    
