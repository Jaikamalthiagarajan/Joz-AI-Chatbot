from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def generate_response(question: str, personal_data: str, policy_context: str):

    prompt = f"""
You are an intelligent HR assistant.

You can answer using TWO sources:

1. Employee Personal Data
2. HR Policy Context

Follow these STRICT rules:

1. If the question is about an employee's leave balance or personal information,
   answer ONLY using Employee Personal Data.

2. If the question is about company rules, policies, or leave entitlement rules,
   answer using HR Policy Context.

3. If BOTH sources are relevant, combine them naturally.

4. If HR Policy Context is EMPTY:
   - DO NOT mention policy
   - DO NOT say anything about missing policy
   - Answer ONLY using Employee Personal Data

5. If the answer is NOT present in BOTH sources:
   respond EXACTLY with:
   The policy does not contain this information.

6. NEVER include phrases like:
   - "The policy does not contain this information"
   - "No information found in policy"
   UNLESS rule 5 applies.

7. Keep the answer short, professional, and clear.

---

User Question:
{question}

Employee Personal Data:
{personal_data}

HR Policy Context:
{policy_context}

Answer:
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "temperature": 0.1
        }
    )

    return response.text.strip()