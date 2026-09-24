"""Checks that both API keys work and lists the chat models each one can use.
Never prints the keys themselves."""
import os

from dotenv import load_dotenv
from google import genai
from mistralai.client import Mistral

load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
mistral_key = os.getenv("MISTRAL_API_KEY", "").strip()

print("GEMINI_API_KEY found:", bool(gemini_key))
print("MISTRAL_API_KEY found:", bool(mistral_key))

if gemini_key:
    try:
        client = genai.Client(api_key=gemini_key)
        names = [m.name for m in client.models.list() if "gemini" in m.name]
        print(f"\nGemini OK: {len(names)} models available")
        for n in names:
            print("  ", n)
    except Exception as e:
        print("\nGemini FAILED:", type(e).__name__, str(e)[:200])

if mistral_key:
    try:
        client = Mistral(api_key=mistral_key)
        names = sorted(m.id for m in client.models.list().data)
        print(f"\nMistral OK: {len(names)} models available")
        for n in names:
            print("  ", n)
    except Exception as e:
        print("\nMistral FAILED:", type(e).__name__, str(e)[:200])
