import os
from groq import Groq
print("groq:", __import__("groq").__version__)
import httpx
print("httpx:", httpx.__version__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
print("OK: Groq client constructed")
