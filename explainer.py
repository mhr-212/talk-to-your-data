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
    
    # Try fallback models for explanation too
    models_to_try = [model_id, "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro", "gemini-1.0-pro"]
    
    last_error = None
    for model in models_to_try:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=500,
                )
            )
            return (getattr(response, "text", "") or "").strip()
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            # If 404/400, try next model
            if "404" in error_str or "not found" in error_str or "not supported" in error_str:
                continue
            # If quota exhausted, stop trying
            if "429" in error_str or "exhausted" in error_str:
                return "AI daily quota exceeded. (You are on the free tier). The results above are still accurate!"
            continue
            
    return f"(Explanation unavailable: {str(last_error)})"
