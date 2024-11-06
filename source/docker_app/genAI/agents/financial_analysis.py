# financial_analysis.py

import boto3
from datetime import datetime
from langchain_aws import ChatBedrock
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from langchain.agents import AgentExecutor, create_xml_agent
from langchain.agents import Tool
from langchain_core.prompts import ChatPromptTemplate
from genAI.tools.stockPrice import StockPriceTool  
from genAI.tools.stockIncomeStatement import IncomeStatementTool  
from langchain_core.output_parsers import StrOutputParser
from genAI.prompts.financial_analysis_prompt import FinancialAnalysisPrompt

import random
import string
import os
import numpy as np 
from config_file import Config

# Define a custom parser for handling the income statement data
class CustomIncomeStatementParser(StrOutputParser):
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
    model_kwargs={"temperature": 0.0, "top_p": 0.99, "max_tokens": 4096},
)

# Initialize tools
stock_price = StockPriceTool()
income_statement = IncomeStatementTool()
LLM_AGENT_TOOLS = [
    Tool(
        name="StockPrice",
        func=stock_price,
        description="Use this tool when you need to retrieve current stock price and historical price.",
    ),
    Tool(
        name="IncomeStatement",
        func=income_statement,
        description="Use this tool when you need to retrieve current stocks income statement.",
    ),
]

'''

# Define the prompt
date_today = str(datetime.today().date())
system_message = f"""
You are a financial analyst tasked with analyzing Company's latest financial data. Your goal is to provide a comprehensive analysis of the data, identifying trends, issues, and significant insights. The data includes revenue, net income, costs, and other financial metrics for various quarters starting from the most recent quarter.

Available tools:
<tools>
{{tools}}
</tools>

When answering questions or responding to user inputs, please follow these guidelines:

1. Use the conversation history inside <conversation_history> to provide context and avoid duplicating information.
2. In order to use a tool, you can use <tool></tool> and <tool_input></tool_input> tags. Always provide ticker as input to the tool based on user request. Example: ZM. Do not append period such as Annual or Quarter to the ticker.You will then get back a response in the form <observation></observation>.
3. Overall, you can think towards another as follows:
   <thinking>Explain your thought process and which tool(s) you plan to use</thinking>
   <tool>tool_name</tool>
   <tool_input>input_for_the_tool</tool_input>
   <observation>output_from_the_tool</observation>
   <calculate>calculate based on tool observation</calculate>
   (thinking/tool/tool_input/observation/calculate can repeat N times if answer is needed.)
   <final_answer>Your final response to the user's query in markdown format.</final_answer>
4. If the user input is a greeting or cannot be answered by the available tools, respond directly within <final_answer> tags.
5. If you cannot provide a complete answer, acknowledge the knowledge gap politely and suggest authoritative sources the user could consult.
6. Adjust your language and tone based on the user's communication style, but always remain professional and respectful.
7. Provide answers only from data collected through tools. If not enough data is available acknowledge the knowledge gap politely.

Data Description:
Revenue: The total income generated by the sale of goods or services.
Income: The net income or profit after expenses.
Costs: Total expenses incurred in generating revenue.
Tasks:
Revenue Analysis:
Analyze the quarter-over-quarter and year-over-year revenue growth.
Identify any patterns or significant changes in revenue.
Highlight quarters with unusually high or low revenue and provide potential reasons.
Profitability Analysis:
Track net income over the quarters to assess profitability.
Calculate and analyze profit margins (Net Income / Revenue).
Investigate any significant increases or decreases in net income.
Cost Analysis:
Examine cost trends relative to revenue growth.
Identify periods of cost reduction or spikes.
Determine if costs are increasing in proportion to revenue.
Quarterly Fluctuations:
Identify any seasonal trends that might affect revenue, costs, and income.
Compare financial metrics between similar quarters in different years.
Identifying Issues:
Look for quarters where revenue declined and identify potential causes.
Investigate quarters with unusually high costs and determine the reasons.
Analyze periods where profitability dropped and correlate with revenue and cost data.
External Factors:
Consider external market conditions (economic downturns, competition, regulatory changes) that might have impacted the financial data.
Assess the impact of strategic initiatives (acquisitions, new product launches, market expansions) on financial performance.
"""

user_message = """

Here is the user's next reply:
<user_input>
{input}
</user_input>

{agent_scratchpad}
"""

# Construct the prompt from the messages
messages = [
    ("system", system_message),
    ("human", user_message),
]

'''

def get_agentic_chain(user_input, verbose=True):
        # Create the XML agent with the specified prompt and tools
    agent = create_xml_agent(
        claude_chat_llm,
        LLM_AGENT_TOOLS,
        ChatPromptTemplate.from_messages(FinancialAnalysisPrompt.messages),
    )

    # Define the agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=LLM_AGENT_TOOLS,
        return_intermediate_steps=True,  # Capture intermediate steps
        verbose=verbose,
        handle_parsing_errors="Check your output and make sure it conforms!"
    )
    return agent_executor

def analyze_financials(user_input):
    # Get the agentic chain with the specified parameters
    conversation_chain = get_agentic_chain(user_input)

    try:
        # Invoke the agent to get the response with intermediate steps
        response = conversation_chain.invoke({"input": user_input})

        # Extract the final output and intermediate steps
        final_output = response.get("output", "")
        intermediate_steps = response.get("intermediate_steps", [])

        income_statement_data = None
        for action, result in intermediate_steps:
            if "IncomeStatement" in action.tool:
                income_statement_data = result
                break

        if income_statement_data:
            parser = CustomIncomeStatementParser()
            parsed_data = parser.parse(income_statement_data)
            return final_output, parsed_data

        return final_output, None

    except Exception as e:
        print(f"Failed to generate report: {str(e)}")
        return str(e), None

# Example usage
if __name__ == "__main__":
    
    analyze_financials("GOOGL")
