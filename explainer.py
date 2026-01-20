"""Query result explanation module."""
from typing import List, Dict, Any, Optional
from google import genai


def generate_explanation(
    client: genai.Client,
    model_id: str,
    question: str,
    sql: str,
    sample_rows: List[Dict[str, Any]],
    temperature: float = 0.3,
    timeout_seconds: float = 10.0,
) -> str:
    """
    Generate a natural language explanation of query results.
    
    Args:
        client: GenAI client instance
        model_id: Model identifier
        question: Original user question
        sql: Executed SQL query
        sample_rows: Sample of result rows (up to 5)
        temperature: LLM temperature
        timeout_seconds: Request timeout
    
    Returns:
        Explanation string (up to ~200 words)
    """
    sample_json = str(sample_rows[:5])
    
    prompt = f"""You are a helpful data analyst. Provide a concise, plain-English explanation of the results.
Keep it under 150 words. Be specific about numbers and trends.

User question:
{question}

SQL executed:
{sql}

Sample of result rows:
{sample_json}

Explanation:"""
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=500,
            )
        )
        return (getattr(response, "text", "") or "").strip()
    except Exception as e:
        return f"(Explanation unavailable: {e})"
