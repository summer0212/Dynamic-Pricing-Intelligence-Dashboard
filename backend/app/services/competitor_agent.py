"""
Competitor Agent — searches the web for live competitor prices and extracts them via LLM.

Uses DuckDuckGo's HTML endpoint (via requests + lxml) to fetch search results,
then passes the raw snippets to Groq's llama-3.1-8b-instant for structured
data extraction.

Flow:
  1. GET https://html.duckduckgo.com/html/?q=buy {product} price India
  2. Parse titles + snippets from the HTML response
  3. Feed raw text → ChatGroq with structured output → List[{competitor, price}]
  4. Returns clean list of dicts for the caller to save to DB

Why requests + lxml instead of the duckduckgo-search / ddgs package?
  - `duckduckgo-search` was renamed to `ddgs` (old package returns 0 results)
  - `ddgs` requires TLS 1.3 which Python 3.9 + macOS LibreSSL doesn't support
  - Direct HTTP to DuckDuckGo's HTML endpoint works on any Python version
"""
import logging
from typing import List, Dict, Any

import requests
from lxml import html as lxml_html
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings

logger = logging.getLogger(__name__)


# ─── Pydantic Schema for Structured Output ─────────────────────────

class ExtractedCompetitorPrice(BaseModel):
    competitor_name: str = Field(
        description="The name of the store or website selling the product "
                    "(e.g., Amazon, Flipkart, Croma, Reliance Digital)"
    )
    price: float = Field(
        description="The numeric selling price extracted from the search results in INR"
    )

class CompetitorPriceList(BaseModel):
    prices: List[ExtractedCompetitorPrice] = Field(
        description="A list of competitor prices found. Max 5."
    )


# ─── LLM Setup ─────────────────────────────────────────────────────

def _get_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0,  # Zero temp for strict data extraction tasks
        api_key=settings.GROQ_API_KEY,
    ).with_structured_output(CompetitorPriceList)


# ─── Web Search via DuckDuckGo HTML ────────────────────────────────

def _search_duckduckgo(query: str, max_results: int = 5) -> str:
    """
    Search DuckDuckGo via its HTML endpoint and return formatted results.
    This avoids the TLS 1.3 / SSL issues with the ddgs Python package.
    """
    response = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        timeout=10,
    )
    response.raise_for_status()

    tree = lxml_html.fromstring(response.content)
    results = tree.xpath('//div[contains(@class, "web-result")]')

    lines = []
    for result in results[:max_results]:
        title_el = result.xpath('.//a[@class="result__a"]')
        snippet_el = result.xpath('.//a[@class="result__snippet"]')

        title = title_el[0].text_content().strip() if title_el else ""
        snippet = snippet_el[0].text_content().strip() if snippet_el else ""

        if title:
            lines.append(f"Title: {title}\nSnippet: {snippet}")

    return "\n\n".join(lines)


# ─── Main Agent Function ───────────────────────────────────────────

def scrape_competitor_prices(product_name: str) -> List[Dict[str, Any]]:
    """
    Agent that uses DuckDuckGo to search the web for a product and extract
    live competitor prices.

    Returns a list of dicts: [{"competitor_name": str, "price": float}]
    """
    logger.info(f"Triggering Competitor Agent for: {product_name}")

    # 1. Execute Web Search
    search_query = f"buy {product_name} price India"
    logger.info(f"Searching web with query: {search_query}")

    try:
        search_results = _search_duckduckgo(search_query)

        if not search_results.strip():
            logger.warning(f"No search results found for: {search_query}")
            return []

        logger.debug(f"Search results: {search_results[:500]}")
    except Exception as e:
        logger.error(f"Search tool failed: {e}")
        return []

    # 2. Extract structured data with LLM
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a precise pricing data extraction agent. 
Your job is to read raw web search snippets and extract competitor pricing data.
Follow these strict rules:
1. Only extract prices from valid stores (Amazon, Flipkart, Croma, Vijay Sales, etc.).
2. Extract the price in INR. Convert formatted strings (e.g., ₹24,999) to raw floats (24999.0).
3. Do not invent or hallucinate data. Only extract if explicitly mentioned in the text.
4. If no clear price is found, return an empty list."""),
        ("human", "Here are the search results for the query '{query}':\n\n{results}\n\nExtract the competitor prices.")
    ])

    chain = prompt | _get_llm()

    try:
        extracted: CompetitorPriceList = chain.invoke({
            "query": search_query,
            "results": search_results,
        })

        # Convert Pydantic objects to a simple list of dictionaries
        result_list = []
        for item in extracted.prices:
            if item.price > 0:  # Sanity check to avoid bad data
                result_list.append({
                    "competitor_name": item.competitor_name,
                    "price": item.price,
                })

        logger.info(
            f"Agent successfully extracted {len(result_list)} competitor prices "
            f"for {product_name}"
        )
        return result_list

    except Exception as e:
        logger.error(f"LLM extraction failed for {product_name}: {e}")
        return []
