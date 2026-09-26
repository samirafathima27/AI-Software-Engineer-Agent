import os

from dotenv import load_dotenv
from groq import Groq


# Load local .env variables when running locally.
load_dotenv()


MODEL = "qwen/qwen3.8-27b"


def get_groq_api_key() -> str | None:
    """
    Get the Groq API key.

    Priority:
    1. Local environment variable / .env
    2. Streamlit Secrets when deployed
    """

    # Local development
    api_key = os.getenv("GROQ_API_KEY")

    if api_key:
        return api_key

    # Streamlit Community Cloud
    try:
        import streamlit as st

        api_key = st.secrets.get("GROQ_API_KEY")

        if api_key:
            return api_key

    except Exception:
        # Streamlit may not be available when running
        # the project from the command line.
        pass

    return None


def get_groq_client() -> Groq:
    """
    Create and return the Groq client.
    """

    api_key = get_groq_api_key()

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. "
            "For local development, add it to .env. "
            "For Streamlit Cloud, add it to Streamlit Secrets."
        )

    return Groq(api_key=api_key)


def ask_llm(prompt: str, max_tokens: int = 700) -> str:
    """
    Text-only LLM call.

    No native tools are passed to Groq.
    Python controls all tools.
    """

    client = get_groq_client()

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