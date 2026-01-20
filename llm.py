"""LLM integration module for SQL generation."""
from typing import Optional
from google import genai


def init_genai_client(api_key: str) -> genai.Client:
    """Initialize and return a Google GenAI client."""
    return genai.Client(api_key=api_key)


def generate_sql(
    client: genai.Client,
    model_id: str,
    question: str,
    schema_context: str,
    temperature: float = 0.2,
    timeout_seconds: float = 10.0,
) -> str:
    """
    Generate SQL from a natural language question using an LLM.
    
    Args:
        client: GenAI client instance
        model_id: Model identifier (e.g., "gemini-1.5-flash")
        question: User's natural language question
        schema_context: Schema description for context
        temperature: LLM temperature (lower = more deterministic)
        timeout_seconds: Request timeout
    
    Returns:
        Generated SQL string (normalized)
    """
    prompt = f"""You are a senior data analyst.
Convert the user question into a SINGLE safe SQL SELECT query.

Rules:
- ONLY SELECT statements
- NO comments
- NO markdown
- Use ONLY provided schema
- Return ONLY raw SQL

Schema:
{schema_context}

Question:
{question}
"""
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=1024,
            )
        )
        raw = getattr(response, "text", "").strip()
        return normalize_sql(raw)
    except Exception as e:
        raise RuntimeError(f"LLM generation failed: {e}")


def normalize_sql(output: str) -> str:
    """
    Normalize LLM output by removing code fences, labels, and trailing semicolons.
    """
    import re
    
    s = output.strip()
    
    # Strip markdown code fences
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"\s*```\s*$", "", s)
    
    # Remove "SQL:" prefix
    s = re.sub(r"^SQL\s*:\s*", "", s, flags=re.IGNORECASE)
    s = s.strip()
    
    # Remove trailing semicolon
    if s.endswith(";"):
        s = s[:-1].strip()
    
    return s
