
import re
from openai import OpenAI
import streamlit as st
import json

key = st.secrets["OPENAI_KEY"]["OPENAI_API_KEY"]

def parse_vehicle_details(ro_text: str):
    lines = ro_text.splitlines()
    vehicle_type = "Unknown"
    vin = "Unknown"
    mileage_in_out = "Unknown"

    for i, line in enumerate(lines):
        if "Vehicle" in line:
            if i + 1 < len(lines):
                vehicle_type_line = lines[i + 1].strip()
                if vehicle_type_line.endswith('-') and (i + 2 < len(lines)):
                    vehicle_type_line += lines[i + 2].strip()
                    # Then VIN is at i+3
                    if i + 3 < len(lines):
                        vin_line = lines[i + 3].strip()
                    else:
                        vin_line = "Unknown"
                else:
                    # VIN is at i+2
                    if i + 2 < len(lines):
                        vin_line = lines[i + 2].strip()
                    else:
                        vin_line = "Unknown"
                vehicle_type = vehicle_type_line
                vin = vin_line

                # Look for mileage
                mileage_regex = re.search(
                    r'(\d{1,3},\d{3} Mi In\s*/\s*\d{1,3},\d{3} Mi Out)',
                    ro_text.replace('\n', ' ')
                )
                if mileage_regex:
                    mileage_in_out = mileage_regex.group(1).strip()
            break

    return vehicle_type, vin, mileage_in_out


def parse_ro_with_llm(ro_text: str) -> list:
    """
    Sends the entire ro_text to an LLM (e.g., gpt-4o-mini, GPT-4, or GPT-3.5).
    Returns a list of dicts: [{'job_name': '...', 'parts': [...]}], or [] if none found.
    """
    client = OpenAI(api_key=key)
    
    print("\n[DEBUG] parse_ro_with_llm:")
    print(f"    RO text sample (first 500 chars): {ro_text[:500]!r}")
    print(f"    RO text length: {len(ro_text)}")

    prompt = f"""
    You are an expert mechanic speciliazing in reading vehicle repair orders (RO) and understanding the work that was done to the vehicle.
    youre job is to extract all the work details that was done to the vehicle, as well as, the parts changed and list them in json format.
    an RO can have multiple Jobs, each job starts with a letter and a period. ex: "A., B., C., F., G., etc."
    all of the work steps should be listed in tech story. Write out every step of the work that was done to the vehicle from the RO. usually a tech story starts witn a number and a period. ex: "1., 2., 3., 4., 5., etc." or it could be a short sentence ending with a period or even a short stence followed by "Labor $" here is a short example of some variations of different kinds of tech stories: '''2.  THE  CORRESPONDING  REPAIRS  WERE  MADE,  ON  THE  SUSPENSION  TIRES,  RIMS  AND  STEERING  RACK,TIRES, SHOCKS, SUB FRAME, ALIGNMENT, AXLE, DRIVE TEST WAS PERFORMED. TIRE2 -REPLACE TWO TIRES Labor $50.00'''
    I want you to basically write out the entire RO as it is. Leave out any Customer details, Billing details, Service Advisor, dealership details, or any dealership management system details.
   
    
    this is an example from an RO demlimited by ''': '''C. MECDIAG REFERRING TO RO354148 LOW COOLANT WARNING
    LIGHT
    Warranty Pay $0.00
    Job added by WILLIAM PERRY on Tue Nov 19, 2024 | 8:50 AM
    MECDIAG -MECHANICAL DIAGNOSTIC Labor $0.00
    1. REPLACED COOLANT PUMP GASKET REMOVED THE AIR BOX AND AIR BOX DUCTING REMOVED THE
    CHARGE PIPE REMOVED THE BATTERY ANED BATTERY TRAY REMOVED THE UNDER TRAY AND DRAINED
    THE COOLANT REMOVED THE FUEL LINES AND EVAP LINES REMOVED THE COOLANT LINES FROM THE
    WATER PUMP REMOVED THE VACUUM LINES FROM THE TOOTH BELT GUARD REMOVED THE TOOTH BELT
    GUARD REMOVED THE TOOTH BELT SPROCKET REMOVED THE WATER PUMP INSTALLED NEW GASKET WITH
    NEW HARDWARE TORQUED TO SPEC INSTALLED ALL PARTS IN REVERSE ORDER AND PERFORMED COOLANT
    FILL AND BLEED
    2. REPLACED THE TURBO PCV PIPE REMOVED THE CHARGE PIPE REMOVED THE TURBO TO PCV LINE AND
    INSTALLED NEW LINE INSTALLED THE CHARGE PIPE WITH NEW CLIP AND O RING
    3. COOLANT PUMP TOOTH BELT
    4. REPLACED HEX NUTS FOR THE BALL JOINT ON THE LOWER CONTROL ARM
    5. PERFORMED COOLANT FILL AND BLEED
    6. GFF 191506295
    Parts $0.00
    04E-121-605-M - TOOTH BELT 1
    05E-103-474-E - VENTHOSE 1
    05E-121-119 - WASHER 1
    N-912-332-01 - HEX. NUT 3'''

    The Output should look like this:
    "jobs": [C. MECDIAG REFERRING TO RO354148 LOW COOLANT WARNING
    LIGHT], "Description": [MECDIAG -MECHANICAL DIAGNOSTIC],
    "Tech Story":[
    "1. REPLACED COOLANT PUMP GASKET REMOVED THE AIR BOX AND AIR BOX DUCTING REMOVED THE
    CHARGE PIPE REMOVED THE BATTERY ANED BATTERY TRAY REMOVED THE UNDER TRAY AND DRAINED
    THE COOLANT REMOVED THE FUEL LINES AND EVAP LINES REMOVED THE COOLANT LINES FROM THE
    WATER PUMP REMOVED THE VACUUM LINES FROM THE TOOTH BELT GUARD REMOVED THE TOOTH BELT
    GUARD REMOVED THE TOOTH BELT SPROCKET REMOVED THE WATER PUMP INSTALLED NEW GASKET WITH
    NEW HARDWARE TORQUED TO SPEC INSTALLED ALL PARTS IN REVERSE ORDER AND PERFORMED COOLANT
    FILL AND BLEED",
    "2. REPLACED THE TURBO PCV PIPE REMOVED THE CHARGE PIPE REMOVED THE TURBO TO PCV LINE AND
    INSTALLED NEW LINE INSTALLED THE CHARGE PIPE WITH NEW CLIP AND O RING",
    "3. COOLANT PUMP TOOTH BELT",
    "4. REPLACED HEX NUTS FOR THE BALL JOINT ON THE LOWER CONTROL ARM",
    "5. PERFORMED COOLANT FILL AND BLEED",
    "6. GFF 191506295"] 
    "parts": ["04E-121-605-M / TOOTH BELT / 1", "05E-103-474-E / VENTHOSE / 1", "05E-121-119 / WASHER / 1 ", "N-912-332-01 / HEX. NUT / 3"]
    Return only valid JSON in this structure:

    {{
      "jobs": [
         {{
           "job_name": "string",
           "Description": "string",
           "tech_story": ["string","string",...],
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
            max_tokens=3000
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
    