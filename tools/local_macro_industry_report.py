#!/usr/bin/env python3
"""
Local macro industry report generator that avoids CDK/CloudFormation.

Requirements:
- Python 3.10+
- pip install boto3
- Optional (for PDFs): pip install pypdf

Usage:
  export AWS_ACCESS_KEY_ID=...
  export AWS_SECRET_ACCESS_KEY=...
  export AWS_SESSION_TOKEN=...      # if temporary creds
  export AWS_REGION=us-east-1

  # Optionally set a specific model (e.g., Claude 3.5 Haiku):
  # export BEDROCK_MODEL_ID="anthropic.claude-3-5-haiku-20241022-v1:0"

  python tools/local_macro_industry_report.py \
    --bucket my-bucket \
    --prefix research/semis/ \
    --industry "Semiconductors" \
    --region "global" \
    --horizon "next 12 months" \
    --max-bytes 60000

Output: JSON printed to stdout.
"""

import argparse
import io
import json
import os
import sys
from typing import List, Tuple

import boto3

try:
    from pypdf import PdfReader  # optional
except Exception:  # pragma: no cover
    PdfReader = None


def _read_s3_object(s3, bucket: str, key: str) -> Tuple[str, str]:
    """Return (text, source) for supported types; empty text for unsupported."""
    obj = s3.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    source = f"s3://{bucket}/{key}"
    lower = key.lower()

    if lower.endswith(".txt") or lower.endswith(".md"):
        try:
            return body.decode("utf-8", errors="ignore"), source
        except Exception:
            return body.decode("latin-1", errors="ignore"), source
    if lower.endswith(".pdf") and PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(body))
            pages = [p.extract_text() or "" for p in reader.pages]
            return "\n".join(pages), source
        except Exception:
            return "", source

    # Unsupported types silently ignored
    return "", source


def _gather_context(bucket: str, prefix: str, max_bytes: int) -> Tuple[str, list]:
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION"))
    paginator = s3.get_paginator("list_objects_v2")
    ctx_parts: List[str] = []
    citations = []
    total = 0

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            text, src = _read_s3_object(s3, bucket, key)
            if not text:
                continue
            snippet = text.strip()
            if not snippet:
                continue
            header = f"[Source] {src}"
            chunk = f"{header}\n{snippet}"
            if total + len(chunk) > max_bytes:
                remaining = max(0, max_bytes - total)
                if remaining > 0:
                    chunk = chunk[:remaining]
                    ctx_parts.append(chunk)
                    citations.append({"title": os.path.basename(key), "source": src})
                    total += len(chunk)
                return "\n\n".join(ctx_parts), citations
            ctx_parts.append(chunk)
            citations.append({"title": os.path.basename(key), "source": src})
            total += len(chunk)
    return "\n\n".join(ctx_parts), citations


def _build_prompt(industry: str, region: str, horizon: str, context: str) -> dict:
    system = (
        "You are a macro industry analyst. Using the provided context, produce a concise, "
        "executive-ready report in valid JSON matching this schema:\n"
        "{\n  \"industry\": string,\n  \"region\": string,\n  \"time_horizon\": string,\n  \"overview\": string,\n"
        "  \"key_drivers\": [string],\n  \"market_structure\": string,\n  \"policy_regulation\": string,\n  \"competitive_landscape\": string,\n"
        "  \"trends\": [string],\n  \"risks\": [string],\n  \"outlook\": string,\n  \"citations\": [{\"title\": string, \"source\": string}]\n}\n"
        "Guidelines: Base all claims on the context only. If information is missing, say \"Insufficient context\". "
        "Keep sections brief (1–3 sentences). Return only the JSON object."
    )
    human = (
        f"Industry: {industry}\nRegion: {region}\nTime horizon: {horizon}\n\nContext:\n{context}"
    )
    return {
        "messages": [
            {"role": "system", "content": [{"text": system}]},
            {"role": "user", "content": [{"text": human}]},
        ],
        "inferenceConfig": {"maxTokens": 2048, "temperature": 0.2, "topP": 0.95},
    }


def run(industry: str, region: str, horizon: str, bucket: str, prefix: str, max_bytes: int, *, local_extractive: bool=False) -> dict:
    context, cites = _gather_context(bucket, prefix, max_bytes)
    if not context:
        return {
            "industry": industry,
            "region": region,
            "time_horizon": horizon,
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

    if local_extractive or os.environ.get("LOCAL_EXTRACTIVE", "").lower() in ("1","true","yes"):
        return _extractive_summary(industry, region, horizon, context, cites)

    body = _build_prompt(industry, region, horizon, context)
    model_id = (
        os.environ.get("BEDROCK_MODEL_ID")
        or os.environ.get("MODEL_ID")
        or os.environ.get("NOVA_MODEL_ID")
        or "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    )
    inference_profile_arn = (
        os.environ.get("BEDROCK_INFERENCE_PROFILE_ARN")
        or os.environ.get("INFERENCE_PROFILE_ARN")
    )
    region_name = os.environ.get("AWS_REGION", "us-east-1")
    brt = boto3.client("bedrock-runtime", region_name=region_name)
    # Prefer Converse API; use inference profile when provided (required for some models)
    try:
        converse_args = {
            "messages": body["messages"],
            "inferenceConfig": body["inferenceConfig"],
        }
        if inference_profile_arn:
            converse_args["inferenceProfileArn"] = inference_profile_arn
        else:
            converse_args["modelId"] = model_id
        resp = brt.converse(**converse_args)
        text = resp.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
    except Exception:
        # Fallback to invoke_model
        invoke_args = {"body": json.dumps(body)}
        if inference_profile_arn:
            invoke_args["inferenceProfileArn"] = inference_profile_arn
        else:
            invoke_args["modelId"] = model_id
        im_resp = brt.invoke_model(**invoke_args)
        payload = im_resp["body"].read().decode("utf-8")
        try:
            parsed = json.loads(payload)
            text = parsed.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", payload)
        except Exception:
            text = payload

    try:
        result = json.loads(text)
    except Exception:
        # Fallback: wrap raw text
        result = {
            "industry": industry,
            "region": region,
            "time_horizon": horizon,
            "overview": text[:4000],
            "key_drivers": [],
            "market_structure": "",
            "policy_regulation": "",
            "competitive_landscape": "",
            "trends": [],
            "risks": [],
            "outlook": "",
            "citations": cites,
        }

    if not result.get("citations"):
        result["citations"] = cites
    return result


# -----------------------------
# Local extractive summarization
# -----------------------------
import re
from collections import Counter

_STOPWORDS = set(
    "the a an and or of in on at by for to from with as is are was were be been being have has had do does did this that these those it its their his her our your not no if then than into over under between after before more less most least such also however therefore thus while during among across per via about against without within according including".split()
)

def _sentences(text: str) -> list:
    # Split on sentence boundaries; keep reasonable length
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in parts if 40 <= len(s.strip()) <= 400]

def _tokens(text: str) -> list:
    return [t for t in re.findall(r"[A-Za-z][A-Za-z\-]+", text.lower()) if t not in _STOPWORDS and len(t) > 2]

def _score_sentences(sents: list) -> list:
    # Simple TF scoring
    all_tokens = []
    for s in sents:
        all_tokens.extend(_tokens(s))
    freq = Counter(all_tokens)
    scores = []
    for s in sents:
        score = sum(freq.get(t, 0) for t in _tokens(s)) / (len(s.split()) + 1)
        scores.append((score, s))
    scores.sort(reverse=True, key=lambda x: x[0])
    return [s for _, s in scores]

def _pick_by_keywords(sents: list, keywords: list, limit: int=4) -> list:
    out = []
    patt = re.compile(r"|".join(re.escape(k) for k in keywords), re.IGNORECASE)
    for s in sents:
        if patt.search(s):
            out.append(s)
        if len(out) >= limit:
            break
    return out

def _extractive_summary(industry: str, region: str, horizon: str, context: str, citations: list) -> dict:
    sents = _sentences(context)
    if not sents:
        return {
            "industry": industry,
            "region": region,
            "time_horizon": horizon,
            "overview": "Insufficient context",
            "key_drivers": [],
            "market_structure": "Insufficient context",
            "policy_regulation": "Insufficient context",
            "competitive_landscape": "Insufficient context",
            "trends": [],
            "risks": [],
            "outlook": "Insufficient context",
            "citations": citations,
        }

    ranked = _score_sentences(sents)
    overview = " ".join(ranked[:3]) if ranked else "Insufficient context"

    key_drivers = _pick_by_keywords(ranked, [
        "driver","growth","demand","cost","price","regulation","policy","subsidy","supply","incentive","efficiency","capacity"
    ])
    market_structure = (" ".join(_pick_by_keywords(ranked, [
        "market share","fragmented","consolidated","oligopoly","barrier","concentration","competition"
    ], limit=2)) or "Insufficient context")
    policy_regulation = (" ".join(_pick_by_keywords(ranked, [
        "policy","regulation","tariff","subsidy","standard","mandate","tax","compliance"
    ], limit=3)) or "Insufficient context")
    competitive_landscape = (" ".join(_pick_by_keywords(ranked, [
        "competitor","competition","players","leader","position","market share","rival"
    ], limit=3)) or "Insufficient context")
    trends = _pick_by_keywords(ranked, [
        "trend","increasing","declining","rising","growing","accelerating","decelerating","adoption"
    ], limit=4)
    risks = _pick_by_keywords(ranked, [
        "risk","challenge","headwind","uncertainty","supply chain","volatility","shortage","delay"
    ], limit=4)
    outlook = (" ".join(ranked[-2:]) if len(ranked) >= 2 else (ranked[-1] if ranked else ""))

    return {
        "industry": industry,
        "region": region,
        "time_horizon": horizon,
        "overview": overview or "Insufficient context",
        "key_drivers": key_drivers,
        "market_structure": market_structure,
        "policy_regulation": policy_regulation,
        "competitive_landscape": competitive_landscape,
        "trends": trends,
        "risks": risks,
        "outlook": outlook or "",
        "citations": citations,
        "_note": "Generated without LLM due to model access issues (extractive heuristic)."
    }


def main():
    ap = argparse.ArgumentParser(description="Local Macro Industry Report (no CDK)")
    ap.add_argument("--bucket", required=True, help="S3 bucket containing docs")
    ap.add_argument("--prefix", required=True, help="S3 key prefix for docs")
    ap.add_argument("--industry", required=True)
    ap.add_argument("--region", default="global")
    ap.add_argument("--horizon", default="next 12 months")
    ap.add_argument("--max-bytes", type=int, default=120000, help="Max context bytes")
    ap.add_argument("--local-extractive", action="store_true", help="Use local extractive summarizer (no Bedrock)")
    ap.add_argument("--model-id", help="Override Bedrock modelId (e.g., us.amazon.nova-micro-v1:0)")
    ap.add_argument("--inference-profile-arn", help="Bedrock inference profile ARN to use")
    args = ap.parse_args()

    # Optional overrides for model selection via CLI
    if args.model_id:
        os.environ["BEDROCK_MODEL_ID"] = args.model_id
    if args.inference_profile_arn:
        os.environ["BEDROCK_INFERENCE_PROFILE_ARN"] = args.inference_profile_arn

    result = run(
        industry=args.industry,
        region=args.region,
        horizon=args.horizon,
        bucket=args.bucket,
        prefix=args.prefix,
        max_bytes=args.max_bytes,
        local_extractive=args.local_extractive,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
