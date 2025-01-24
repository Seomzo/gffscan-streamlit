import re
from PyPDF2 import PdfReader

def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        pdf = PdfReader(pdf_file)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        print(f"[ERROR] PDF read: {e}")
        return None

def extract_vehicle_info_block(text: str) -> str:
    pattern = re.compile(
        r"Vehicle Information\s*(.*?)\s*(?=ASAM project name|Diagnostic Session)",
        re.DOTALL
    )
    match = pattern.search(text)
    if match:
        return match.group(1)
    return ""

def parse_vehicle_info_lines(block: str) -> dict:
   
    details = {}
    lines = block.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("Brand:"):
            brand_val = line.split("Brand:", 1)[1].strip()
            details["Brand"] = brand_val
        
  
        elif line.startswith("Type:"):
            
            rest = line.split("Type:", 1)[1].strip()
            
            my_match = re.search(r"Model year:\s*(.*)", rest)
            if my_match:
                details["Model Year"] = my_match.group(1).strip()
                # e.g. "Type: Model year: 2022 (N)"
            else:
                # If we see something like "Type: ABC" then
                details["Type"] = rest

        # 3) line with "Model year:" if it stands alone
        elif "Model year:" in line:
            # e.g. "Model year: 2022 (N)"
            my_val = line.split("Model year:", 1)[1].strip()
            details["Model Year"] = my_val

        
        elif line.startswith("Version:"):
            # e.g. "Version: Sedan"
            version_val = line.split("Version:", 1)[1].strip()
            details["Version"] = version_val

            
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                if (not next_line.startswith("Engine code:")
                    and not next_line.startswith("VIN (")
                    and "Odometer reading" not in next_line
                    and "ASAM" not in next_line
                    and "Model year:" not in next_line
                    and "Type:" not in next_line):
                    # We'll assume it might be "CL - Taos..."
                    details["Type"] = next_line
                    i += 1  # skip the next line since we consumed it

        elif line.startswith("Engine code:"):
            eng_val = line.split("Engine code:", 1)[1].strip()
            details["Engine"] = eng_val

        elif "VIN (automatic):" in line:
            vin_val = line.split("VIN (automatic):", 1)[1].strip()
            details["VIN"] = vin_val
        elif "VIN (manual):" in line:
            pass

        elif "Odometer reading (km):" in line:
            od_val = line.split("Odometer reading (km):", 1)[1].strip()
            details["Odometer Reading"] = od_val
        
        i += 1

    return details

def extract_vehicle_details(text: str) -> dict:
    details = {}
    block = extract_vehicle_info_block(text)
    if block:
        parsed = parse_vehicle_info_lines(block)
        details.update(parsed)

    tu_match = re.search(r"Time required \(TU\):\s*(\d+)", text)
    if tu_match:
        details["Time Required (TU)"] = tu_match.group(1).strip()

    return details


def extract_action_messages(text: str):
    ignore_phrases = [
        "Test step:", "Please wait...", "NO NOTE", 
        "Note the following boundary conditions:", "Parameters:", 
        "NOTE:", "Please wait.",
        "Data for the diagnosis log:", "MSG_OH_SOD_KuehlsystemBefuellenEntlueften",
        "CM designation: EV_MUStd4CTSA T_001", "With this test program the following test steps will be performed:",
        "Service:", "CM designation:", "Action:", "Ignition cycle:",
        "- Switch on the ignition.", "Result: OK", "MSG_OT_SOD",
        "Version:", "Date:", "https://www.vwhub.com/gff",
        "Please wait", "Please leave the ignition switched",
        "The ignition is switched on...", "The ignition is switched off..."
    ]

    action_messages = []
    lines = text.splitlines()
    current_test_step = None
    current_job_status = None
    
    test_step_pattern = re.compile(r"(?:-?\s*)?Test step:\s*(.+)")
    job_status_pattern = re.compile(r"Job Status:\s*(\w+)")

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Capture test step using improved pattern
        test_step_match = test_step_pattern.search(line_stripped)
        if test_step_match:
            current_test_step = test_step_match.group(1).strip()

        # Capture job status if available
        job_status_match = job_status_pattern.search(line_stripped)
        if job_status_match:
            current_job_status = job_status_match.group(1).strip()

        # Check for action messages and associate with the current test step
        if re.match(r"Action:\s+Message", line_stripped):
            message_lines = []
            for j in range(1, 3):  # Capture next two lines
                if i + j < len(lines):
                    next_line = lines[i + j].strip()
                    if next_line and not any(phrase.lower() in next_line.lower() for phrase in ignore_phrases):
                        message_lines.append(next_line)

            if message_lines:
                full_message = ' '.join(message_lines)
                action_messages.append({
                    'message': full_message,
                    'test_step': current_test_step if current_test_step else 'Unknown',
                    'job_status': current_job_status if current_job_status else 'N/A'
                })

    return action_messages
    # for i, line in enumerate(lines):
    #     line_stripped = line.strip()

    #     test_step_match = re.match(r"Test step:\s*(.+)", line_stripped)
    #     if test_step_match:
    #         current_test_step = test_step_match.group(1).strip()
        
    #     # End of a test section
    #     if line_stripped.startswith("Test step: Return"):
    #         current_test_step = None

    #     # Capture job status within a control module block
    #     if "Control module communication (UDS)" in line_stripped:
    #         for j in range(i + 1, min(i + 6, len(lines))):  # Scan next few lines for status
    #             job_status_match = re.search(r"Job Status:\s*(.+)", lines[j])
    #             if job_status_match:
    #                 current_job_status = job_status_match.group(1).strip()

    #     # Check for action messages
    #     if re.match(r"Action:\s+Message", line_stripped):
    #         message_lines = []
    #         for j in range(1, 4):  # Get up to the next three lines
    #             if i + j < len(lines):
    #                 next_line = lines[i + j].strip()
    #                 if not any(phrase.lower() in next_line.lower() for phrase in ignore_phrases):
    #                     message_lines.append(next_line)

    #         if message_lines:
    #             # Combine the message lines
    #             full_message = ' '.join(message_lines)

    #             # Store the message with associated test step and job status
    #             action_messages.append({
    #                 'message': full_message,
    #                 'test_step': current_test_step if current_test_step else "Unknown",
    #                 'job_status': current_job_status
    #             })

    # return action_messages

def preprocess_gff_log(text: str, successful_verbiage, unsuccessful_verbiage):
    vehicle_details = extract_vehicle_details(text)
    action_msgs = extract_action_messages(text)

    successful_messages = []
    unsuccessful_messages = []
    neutral_messages = []

    for item in action_msgs:
        msg = item['message']
        matched = False
        # successful
        for verbiage in successful_verbiage:
            if verbiage.lower().strip() in msg.lower():
                successful_messages.append(item)
                matched = True
                break
        if matched:
            continue

        # unsuccessful
        for verbiage in unsuccessful_verbiage:
            if verbiage.lower().strip() in msg.lower():
                unsuccessful_messages.append(item)
                matched = True
                break
        if not matched:
            neutral_messages.append(item)

    return vehicle_details, successful_messages, unsuccessful_messages, neutral_messages