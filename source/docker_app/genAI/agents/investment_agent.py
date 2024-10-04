# investment_agent.py

import boto3
from datetime import datetime
from langchain_aws import ChatBedrock
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from langchain.agents import AgentExecutor, create_xml_agent
from langchain.agents import Tool
from langchain_core.prompts import ChatPromptTemplate
from genAI.tools.investment_analysis_tool import get_price_history, get_income_statement, InvestmentAnalysisTool
from genAI.tools.investment_analysis_tool import get_latest_news, get_cash_flow, get_recommendations, search_knowledge_base
from langchain_core.output_parsers import StrOutputParser
from genAI.prompts.investment_analysis_prompt import InvestmentAnalysisPrompt
from langchain.tools.retriever import create_retriever_tool

import random
import string
import os
import numpy as np 
from config_file import Config

import traceback


from langchain_aws.retrievers import AmazonKnowledgeBasesRetriever

# Define a custom parser for handling the income statement data
class CustomIncomeStatementParsers(StrOutputParser):
    def parse(self, text: str):
        lines = text.split('\n')
        header_line_index = 1
        
        # Find the header line index that contains actual headers
        while header_line_index < len(lines) and not lines[header_line_index].strip():
            header_line_index += 1
        
        # Get headers if available
        header_line = lines[header_line_index].strip() if header_line_index < len(lines) else ''
        headers = header_line.split()
        
        if not headers:
            print("No headers found")
            raise ValueError("No headers found in the income statement data.")
        
        income_statement_json = []

        for line in lines[header_line_index + 1:]:
            if line.strip():
                parts = line.split()
                
                # Ensure there are enough parts to match headers + metric name
                if len(parts) >= len(headers) + 1:
                    row_data = {
                        "Metric": " ".join(parts[:-len(headers)])
                    }
                    for i, header in enumerate(headers):
                        row_data[header] = self._convert_to_number(parts[-len(headers) + i])
                    
                    income_statement_json.append(row_data)
                else:
                    # Log or handle cases where parts do not match expected length
                    print(f"Line skipped due to insufficient parts: {line}")

        return income_statement_json

    def _convert_to_number(self, value: str):
        """Convert string to a number, handling NaN values by converting them to 0."""
        try:
            number = float(value)
            if np.isnan(number):
                return 0
            return number
        except ValueError:
            return 0

bedrock_region = Config.BEDROCK_REGION
bedrock_runtime = boto3.client("bedrock-runtime", region_name=bedrock_region)
claude_chat_llm = ChatBedrock(
    model_id=Config.LLM_MODEL_ID,
    client=bedrock_runtime,
    model_kwargs={"temperature": 0.2, "top_p": 0.99, "max_tokens": 4096},
)

amzn_kb_retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id="XFG61CFOTV",
    retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 4}},
)

kb_retriever_tool = create_retriever_tool(
    retriever=amzn_kb_retriever,
    name="knowledge_base",
    description="""This tool provides the historical news related to stock market. 
    Use this tool to get information about sector, to know the key players in a sector
    or to understand the policies and what other companies are doing. 
	""",
)

# Initialize tools
#stock_price = StockPriceTool()
#income_statement = IncomeStatementTool()
investment_analysis_tool = InvestmentAnalysisTool()
LLM_AGENT_TOOLS = [
    Tool(
        name="search_knowledge_base",
        func=search_knowledge_base,
        description="""    This tool provides the historical news related to stock market. 
        Use this tool to get information about sector, to know the key players in a sector
        or to understand the policies and what other companies are doing. 
        """,
    ),
    Tool(
        name="get_price_history",
        func=get_price_history,
        description="""This tool will provide the stock prices of past 6 months.
        The input parameter is stock ticker prices and output will be
        history of end of the day price for past 6 months""",
    ),
    Tool(
        name="get_income_statement",
        func=get_income_statement,
        description="""This tool will provide the annual income statement of the company.
        The input parameter is stock ticker prices and output will be
        annual income statement of the company""",
    ),
    Tool(
        name="get_recommendations",
        func=get_recommendations,
        description="""This tool will provide the recommendations based on the investment analysis.
        The input parameter is stock ticker prices and output will be
        recommendations based on the investment analysis""",
    ),
    Tool(
        name="get_latest_news",
        func=get_latest_news,
        description="""This tool will provide the latest news related to stock market.
        The input parameter is stock ticker prices and output will be
        latest news related to stock market""",
    ),
    Tool(
        name="get_cash_flow",
        func=get_cash_flow,
        description="""This tool will provide the cash flow of the company.
        The input parameter is stock ticker prices and output will be
        cash flow of the company""",
    ),
]

def _handle_error(error) -> str:
    print("---"*80)
    print(f"Am I successful in capturing an error?: {error}")
    print("---"*80)
    return str(error)[:50]

def get_agentic_chain(user_input, verbose=True):
        # Create the XML agent with the specified prompt and tools
    agent = create_xml_agent(
        claude_chat_llm,
        LLM_AGENT_TOOLS,
        ChatPromptTemplate.from_messages(InvestmentAnalysisPrompt.messages),
    )

    # Setting the verbose mode to false to prevent lots of messages. 
    verbose = True

    # Define the agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=LLM_AGENT_TOOLS,
        return_intermediate_steps=True,  # Capture intermediate steps
        verbose=verbose,
        max_iterations=10,  # Setting max iteration to avoid loop.
        #handle_parsing_errors="Check your output and make sure it conforms!"
        #handle_parsing_errors=True
        handle_parsing_errors=_handle_error
    )
    return agent_executor

def analyze_investment(user_input):
    # Get the agentic chain with the specified parameters
    conversation_chain = get_agentic_chain(user_input)

    try:
        # Invoke the agent to get the response with intermediate steps
        response = conversation_chain.invoke({"input": user_input})

        # Extract the final output and intermediate steps
        final_output = response.get("output", "")

        print("Final Output = ", final_output)

        return final_output, None

    except Exception as e:
        print(f"Failed to generate report: {str(e)}")
        traceback.print_exc()        
        return str(e), None


# Example usage
if __name__ == "__main__":
    
    analyze_investment("GOOGL")
