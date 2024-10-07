from langchain.agents import Tool
from genAI.tools.stockPrice import StockPriceTool
from genAI.tools.stockIncomeStatement import IncomeStatementTool

stock_price = StockPriceTool()
income_statement = IncomeStatementTool()

LLM_AGENT_TOOLS = [
    Tool(
        name="StockPrice",
        func=stock_price,
        description=(
            "Use this tool when you need to retrieve current stock price and historical price. "
            "The input to this tool should be a valid stock ticker, such as amzn and date for which we need the stock price. If date is not provided, it defaults to current date."
            "Use this tool for historical stock price data. Pass historical date as paremeter along with ticker to get stock price for that date. Example AMZN, 2024-06-01"
        ),
    ),
    Tool(
        name="IncomeStatement",
        func=income_statement,
        description=(
            "Use this tool when you need to retrieve current stocks income statement. "
            "The input to this tool should be a valid stock ticker, such as amzn. Only provide ticker symbol to this tool. Correct example is input: ZM"
        ),
    ),
]
