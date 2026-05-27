import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from duckduckgo_search import DDGS

from app.config import settings

logger = logging.getLogger(__name__)

# --- Pydantic Schema for Structured Output ---
class ExtractedCompetitorPrice(BaseModel):
    competitor_name: str = Field(description="The name of the store or website selling the product (e.g., Amazon, Flipkart, Croma, Reliance Digital)")
    price: float = Field(description="The numeric selling price extracted from the search results in INR")

class CompetitorPriceList(BaseModel):
    prices: List[ExtractedCompetitorPrice] = Field(description="A list of competitor prices found. Max 5.")

# --- LLM Setup ---
def _get_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0, # Zero temp for strict data extraction tasks
        api_key=settings.GROQ_API_KEY,
    ).with_structured_output(CompetitorPriceList)

def scrape_competitor_prices(product_name: str) -> List[Dict[str, Any]]:
    """
    Agent that uses DuckDuckGo to search the web for a product and extract live competitor prices.
    Returns a list of dicts: [{"competitor_name": str, "price": float}]
    """
    logger.info(f"Triggering Competitor Agent for: {product_name}")
    
    # 1. Execute Web Search Tool
    search_query = f"buy {product_name} price India"
    logger.info(f"Searching web with query: {search_query}")
    
    try:
        results = DDGS().text(search_query, max_results=5)
        # Format the results into a single string for the LLM
        search_results = "\n\n".join([
            f"Title: {r.get('title')}\nSnippet: {r.get('body')}" 
            for r in results
        ])
        logger.debug(f"Search results: {search_results}")
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
            "results": search_results
        })
        
        # Convert Pydantic objects to a simple list of dictionaries
        result_list = []
        for item in extracted.prices:
            if item.price > 0: # Sanity check to avoid bad data
                result_list.append({
                    "competitor_name": item.competitor_name,
                    "price": item.price
                })
        
        logger.info(f"Agent successfully extracted {len(result_list)} competitor prices for {product_name}")
        return result_list
        
    except Exception as e:
        logger.error(f"LLM extraction failed for {product_name}: {e}")
        return []
