import yfinance as yf
from typing import Optional, Type, Union
from pydantic import BaseModel, Field
from langchain.tools import BaseTool, StructuredTool, tool
from langchain.callbacks.manager import (AsyncCallbackManagerForToolRun,
                                         CallbackManagerForToolRun)
import boto3
from config_file import Config


bedrock_region = Config.BEDROCK_REGION
kb_id = Config.KB_ID
bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name=bedrock_region)


# Create an SSM client
ssm_client = boto3.client('ssm')

# Define the parameter name
parameter_name = '/InvestmentAnalystAssistant/kb_id'

# Retrieve the parameter value
response = ssm_client.get_parameter(
    Name=parameter_name,
    WithDecryption=False
)

# Get the parameter value
KB_ID = response['Parameter']['Value']

kb_id = KB_ID

print(f"KB_ID : {KB_ID}")

# Define the input schema for the income statement tool
class InvestmentAnalysisInput(BaseModel):
    ticker: str = Field(description="The stock ticker symbol to fetch the income statement for.")


@tool
def search_knowledge_base(query: str) -> str:
    """
    This tool provides the historical news related to stock market. 
    Use this tool to get information about sector, to know the key players in a sector
    or to understand the policies and what other companies are doing. 
    """

    # retreive api for fetching only the relevant context.
    relevant_documents = bedrock_agent_runtime_client.retrieve(
        retrievalQuery= {
            'text': query
        },
        knowledgeBaseId=kb_id,
        retrievalConfiguration= {
            'vectorSearchConfiguration': {
                'numberOfResults': 10 # will fetch top 10 documents which matches closely with the query.
            }
        }
    )

    relevant_documents = relevant_documents.get("retrievalResults")

    context = ""
    for relevant_document in relevant_documents:
        content = relevant_document.get("content")
        news = content.get("text")
        context = context + news + "\n"

    print("Returning context information.")
    return context

@tool
def get_price_history(ticker: str) -> str:
    """This tool will provide the stock prices of past 6 months.
    The input parameter is stock ticker prices and output will be
    history of end of the day price for past 6 months"""

    stock = yf.Ticker(ticker)
    stock_data = str(stock.history(period="6mo"))
    return stock_data

@tool
def get_company_info(ticker: str) -> str:
    """This tool will provide the company information.
    The input parameter is stock ticker prices and output will be
    company information"""

    stock = yf.Ticker(ticker)
    company_info = str(stock.info)
    return company_info

@tool
def get_recommendations(ticker: str) -> str:
    """This tool will provide the company recommendations.
    The input parameter is stock ticker prices and output will be
    company recommendations"""

    stock = yf.Ticker(ticker)
    recommendations = str(stock.recommendations)
    return recommendations

@tool
def get_income_statement(ticker: str) -> str:
    """This tool will provide the annual income statement of the company.
    The input parameter is stock ticker prices and output will be
    annual income statement of the company"""

    stock = yf.Ticker(ticker)
    income_statement = stock.quarterly_income_stmt
    if income_statement.empty:
        return f"No income statement data available for {ticker}."

    print("Type of the statement = ", type(income_statement))
    income_statement_str = str(income_statement.to_json())
    print("Type of the statement after conversion = ", type(income_statement_str))
    #return income_statement_str
    return f"Income statement for {ticker} (quarterly):\n\n{income_statement_str}"

@tool
def get_balance_sheet(ticker: str) -> str:
    """This tool will provide the annual balance sheet of the company.
    The input parameter is stock ticker prices and output will be
    annual balance sheet of the company"""

    print("In get_balance_sheet tool")
    stock = yf.Ticker(ticker)
    balance_sheet = str(stock.balance_sheet)
    return balance_sheet

@tool
def get_cash_flow(ticker: str) -> str:
    """This tool will provide the annual cash flow of the company.
    The input parameter is stock ticker prices and output will be
    annual cash flow of the company"""

    print("In get_cash_flow tool")
    stock = yf.Ticker(ticker)
    cash_flow = str(stock.cashflow.to_json())
    return f"cash flow for {ticker}:\n\n{cash_flow}"

@tool
def get_latest_news(ticker: str) -> str:
    """This tool will provide the latest news about the company.
    The input parameter is stock ticker prices and output will be
    latest news about the company"""

    print("In get_latest_new tool")
    stock = yf.Ticker(ticker)
    news = str(stock.news)
    print("Type of news = ", type(news))
    news = str(news)
    print("Type of news after conversion = ", type(news))
    return news


# Define the custom income statement fetching tool
class InvestmentAnalysisTool(BaseTool):
    name = "InvestmentAnalysisTool"
    description = "Analyze investment or stock based on query provided by the user"
    args_schema: Type[BaseModel] = InvestmentAnalysisInput

    # Function to fetch the annual income statement using yfinance
    def _analyze_investments(ticker: str) -> str:
        try:
            stock = yf.Ticker(ticker)
            income_statement = stock.income_stmt
            if income_statement.empty:
                return f"No income statement data available for {ticker}."

            return f"Income statement for {ticker} (annual):\n\n{income_statement}"

        except Exception as e:
            return (
                f'Error fetching the income statement for "{ticker}": {e}.'
                " Please make sure to provide a valid stock ticker."
            )


    def _run(
        self, query: Union[str, dict], run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Fetch the income statement."""
        print("Query: ", query)

        try:
            if isinstance(query, str):
                # Use the query directly as the ticker
                ticker = query.strip()
            elif isinstance(query, dict):
                # Use the structured input directly
                ticker = query.get('ticker')
            else:
                return "Invalid input format. Please provide input as 'ticker' or a dictionary with 'ticker'."
            
            # Fetch the income statement using the parsed ticker
            return _analyze_investments(ticker)
        except Exception as e:
            return (
                f"Failed to fetch the income statement with error: {e}. "
                "Please provide a valid stock ticker symbol."
            )

    async def _arun(
        self, query: Union[str, dict], run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Fetch the income statement asynchronously."""
        raise NotImplementedError("IncomeStatementTool does not support async operations.")

# Example usage of the IncomeStatementTool
if __name__ == "__main__":
    income_statement_tool = IncomeStatementTool()

    # Test the tool with a sample ticker for the annual income statement
    query = "AMZN"
    response = income_statement_tool._run(query)
    print(response)

    # Test the tool with a structured input
    #query = {"ticker": "ZM"}
    #response = income_statement_tool._run(query)
    #print(response)
