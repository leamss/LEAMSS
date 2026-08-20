import os
import json
import httpx
from openai import AsyncOpenAI


async def extract_state_nomination_excel(state: str, excel_text: str):
    """
    Reads a State Nomination Excel workbook (already converted to text)
    and asks Perplexity AI to extract structured occupation data.
    """

    api_key = os.getenv("PERPLEXITY_API_KEY")

    if not api_key:
        raise Exception("PERPLEXITY_API_KEY not configured")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai",
        http_client=httpx.AsyncClient(verify=False, timeout=60)
    )

    system_prompt = """
You are an Australian Migration Expert.

Read the uploaded Excel workbook.

Extract every occupation.

Return ONLY valid JSON.

Return this format exactly:

{
  "occupations": [
    {
      "anzsco": "",
      "occupation": "",
      "minimum_points": "",
      "visa_190": true,
      "visa_491": true,
      "priority": "",
      "status": "",
      "notes": ""
    }
  ]
}

Do not explain anything.
Do not return markdown.
Only JSON.
"""

    user_prompt = f"""
State: {state}

Workbook:

{excel_text}
"""

    response = await client.chat.completions.create(
        model="sonar",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.2,
        max_tokens=4000,
    )

    text = response.choices[0].message.content.strip()

    if text.startswith("```"):
        text = text.strip("`")

        if text.lower().startswith("json"):
            text = text.split("\n", 1)[1]

    return json.loads(text)