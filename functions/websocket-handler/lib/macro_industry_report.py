import os
import json
from typing import List, Dict, Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from langchain_aws import ChatBedrock
from langchain_aws.retrievers import AmazonKnowledgeBasesRetriever
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from lib.prompts.macro_industry_report_prompt import MacroIndustryReportPrompt

logger = Logger(service="macro_industry_report")
tracer = Tracer(service="macro_industry_report")

LLM_MODEL_ID = os.environ["LLM_MODEL_ID"]
KB_ID = os.environ["KB_ID"]
AWS_REGION = os.environ["AWS_REGION"]

bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def _format_context(docs: List[Document]) -> str:
    parts = []
    for i, d in enumerate(docs, start=1):
        meta = d.metadata or {}
        title = meta.get("title") or meta.get("x-amz-bedrock-kb-document-title") or meta.get("source") or "document"
        src = meta.get("source") or meta.get("s3Uri") or meta.get("x-amz-bedrock-kb-source-uri") or ""
        header = f"[Doc {i}] {title} | {src}"
        parts.append(f"{header}\n{d.page_content}")
    return "\n\n".join(parts)


@tracer.capture_method
def generate_macro_industry_report(industry: str, region: str = "global", time_horizon: str = "next 12 months") -> Dict[str, Any]:
    """Generates a macro industry report from Bedrock KB context."""
    retriever = AmazonKnowledgeBasesRetriever(
        knowledge_base_id=KB_ID,
        retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 6}},
    )

    query = f"{industry} industry analysis {region} {time_horizon} key drivers policy regulation competitive landscape risks trends outlook"
    docs = retriever.get_relevant_documents(query)

    if not docs:
        return {
            "industry": industry,
            "region": region,
            "time_horizon": time_horizon,
            "overview": "Insufficient context",
            "key_drivers": [],
            "market_structure": "Insufficient context",
            "policy_regulation": "Insufficient context",
            "competitive_landscape": "Insufficient context",
            "trends": [],
            "risks": [],
            "outlook": "Insufficient context",
            "citations": [],
        }

    context = _format_context(docs)

    chat = ChatBedrock(
        model_id=LLM_MODEL_ID,
        client=bedrock_runtime,
        model_kwargs={"temperature": 0.2, "top_p": 0.95, "max_tokens": 2048},
        disable_streaming=True,
    )

    prompt = MacroIndustryReportPrompt
    chain = prompt | chat | JsonOutputParser()

    try:
        result = chain.invoke({
            "industry": industry,
            "region": region,
            "time_horizon": time_horizon,
            "context": context,
        })
    except Exception as e:
        logger.exception("Failed to parse JSON output: %s", e)
        # As a fallback, try raw invoke without parser and then best-effort JSON load
        raw = (prompt | chat).invoke({
            "industry": industry,
            "region": region,
            "time_horizon": time_horizon,
            "context": context,
        })
        try:
            result = json.loads(raw.content if hasattr(raw, "content") else str(raw))
        except Exception:
            # Return a minimal structure with no content
            result = {
                "industry": industry,
                "region": region,
                "time_horizon": time_horizon,
                "overview": "Model output could not be parsed as JSON",
                "key_drivers": [],
                "market_structure": "",
                "policy_regulation": "",
                "competitive_landscape": "",
                "trends": [],
                "risks": [],
                "outlook": "",
                "citations": [],
            }

    # Attach citations derived from retrieved docs if not present
    if not result.get("citations"):
        cites = []
        for d in docs[:5]:
            meta = d.metadata or {}
            title = meta.get("title") or meta.get("x-amz-bedrock-kb-document-title") or meta.get("source") or "document"
            src = meta.get("source") or meta.get("s3Uri") or meta.get("x-amz-bedrock-kb-source-uri") or ""
            cites.append({"title": title, "source": src})
        result["citations"] = cites

    # Ensure key identifiers present
    result.setdefault("industry", industry)
    result.setdefault("region", region)
    result.setdefault("time_horizon", time_horizon)
    return result

