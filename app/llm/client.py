import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env file")


client = Groq(api_key=api_key)

MODEL = "qwen/qwen3.8-27b"


def ask_llm(prompt: str, max_tokens: int = 700) -> str:
    """
    Text-only LLM call.

    No native tools are passed to Groq.
    Python controls all tools.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a concise AI software engineer. "
                    "Do not call tools. "
                    "Do not invent tools. "
                    "Follow the requested output format exactly. "
                    "Be concise."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.1,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content or ""