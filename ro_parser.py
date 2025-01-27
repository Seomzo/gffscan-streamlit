
from openai import OpenAI
import streamlit as st
import json



def parse_ro_with_llm(ro_text: str) -> list:
    """
    Sends the entire ro_text to an LLM (e.g., gpt-4o-mini, GPT-4, or GPT-3.5).
    Returns a list of dicts: [{'job_name': '...', 'parts': [...]}], or [] if none found.
    """
    key = st.secrets["OPENAI_KEY"]["OPENAI_API_KEY"]
    client = OpenAI(api_key=key)
    
    print("\n[DEBUG] parse_ro_with_llm:")
    print(f"    RO text sample (first 500 chars): {ro_text[:500]!r}")
    print(f"    RO text length: {len(ro_text)}")

    prompt = f"""
    You are an expert at reading vehicle repair orders (RO).
    Extract the parts and list them in json format.
    example in RO demlimited by ''': '''C. MECDIAG REFERRING TO RO354148 LOW COOLANT WARNING LIGHT
    Warranty Pay $0.00'''
    Output should look like this:
    "jobs": [MECDIAG], "Description": [REFERRING TO RO354148 LOW COOLANT WARNING
    LIGHT], "parts": ["N-908-514-01 Head Gasket 1", "N-911-455-02 Bolt 4"]
    Return only valid JSON in this structure:

    {{
      "jobs": [
         {{
           "job_name": "string",
           "Description": "string",
           "parts": ["string","string",...]
         }},
         ...
      ]
    }}

    If no parts, use an empty list for that job.
    Please do not output any additional commentary beyond the JSON.

    --- RO TEXT START ---
    {ro_text}
    --- RO TEXT END ---
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1500
        )

        # 4) Debug: Show raw response from LLM
        raw_json_str = completion.choices[0].message.content.strip()
        print(f"\n[DEBUG] LLM raw response:\n{raw_json_str}")

        if raw_json_str.startswith("```"):
            raw_json_str = raw_json_str.lstrip("```")
            raw_json_str = raw_json_str.rstrip("```")
            raw_json_str = raw_json_str.replace("json\n", "").replace("json", "")

        # 5) Parse JSON
        parsed_json = json.loads(raw_json_str)
        jobs_data = parsed_json.get("jobs", [])

        print(f"[DEBUG] Jobs data extracted: {jobs_data}")

        return jobs_data

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON decode failed: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] parse_ro_with_llm encountered an exception: {e}")
        return []