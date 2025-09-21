from langchain_core.prompts import ChatPromptTemplate


macro_industry_report_system = """
You are a macro industry analyst. Using the provided context, produce a concise, executive-ready report in valid JSON matching this schema:
{
  "industry": string,
  "region": string,
  "time_horizon": string,
  "overview": string,
  "key_drivers": [string],
  "market_structure": string,
  "policy_regulation": string,
  "competitive_landscape": string,
  "trends": [string],
  "risks": [string],
  "outlook": string,
  "citations": [
    {"title": string, "source": string}
  ]
}

Guidelines:
- Base all claims on the context only. If information is missing, say "Insufficient context" for that section.
- Keep each section brief but specific (1–3 sentences), bullet arrays where appropriate.
- Use citations to list the most relevant documents/sources from context.
"""

macro_industry_report_human = (
    "Industry: {industry}\n"
    "Region: {region}\n"
    "Time horizon: {time_horizon}\n\n"
    "Context:\n{context}\n\n"
    "Return only the JSON object, no extra text."
)

MacroIndustryReportPrompt = ChatPromptTemplate.from_messages([
    ("system", macro_industry_report_system),
    ("human", macro_industry_report_human),
])

