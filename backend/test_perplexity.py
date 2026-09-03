import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="YOUR_PERPLEXITY_KEY",
    base_url="https://api.perplexity.ai"
)

async def main():
    response = await client.chat.completions.create(
        model="sonar-pro",
        messages=[
            {
                "role": "user",
                "content": "Say Hello"
            }
        ]
    )

    print(response.choices[0].message.content)

asyncio.run(main())