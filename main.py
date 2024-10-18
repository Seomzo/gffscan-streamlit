import os
import re
import streamlit as st
from PyPDF2 import PdfReader

# Load verbiage from secrets
SUCCESSFUL_VERBIAGE = st.secrets["verbiage"]["successful_verbiage"]
UNSUCCESSFUL_VERBIAGE = st.secrets["verbiage2"]["unsuccessful_verbiage"]

def extract_text_from_pdf(pdf_file):
    try:
        pdf = PdfReader(pdf_file)
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF file: {e}")
        return None

def extract_vehicle_details(text):
    vehicle_details = {}
    patterns = {
        'Brand': r"Brand:\s*(.+)",
        'Type': r"Type:\s*(.+)",
        'Model Year': r"Model year:\s*(.+)",
        'VIN': r"VIN.*?:\s*([A-Z0-9]+)",
        'Engine': r"Engine code:\s*(.+)",
        'Odometer Reading': r"Odometer reading \(km\):\s*([0-9]+)",
        'Time Required (TU)': r"Time required \(TU\):\s*(.+)",
        'Log Status': r"Log status:\s*(.+)"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            vehicle_details[key] = match.group(1).strip()
    return vehicle_details

def extract_action_messages(text):
    action_messages = []
    lines = text.splitlines()
    ignore_phrases = [
        "Test step:", 
        "Please wait...", 
        "NO NOTE", 
        "Note the following boundary conditions:", 
        "Parameters:", 
        "NOTE:", 
        "Please wait.",
        "Data for the diagnosis log:",
        "MSG_OH_SOD_KuehlsystemBefuellenEntlueften",
        "CM designation: EV_MUStd4CTSA T_001",
        "With this test program the following test steps will be performed:",
        "Service:",
        "CM designation:",
        "Action:",
        "Ignition cycle:",
        "- Switch on the ignition.",
        "Result: OK",
        "MSG_OT_SOD",
        "Version:",
        "Date:"
    ]

    current_control_module = None
    current_job_status = None

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Update current control module
        control_module_match = re.match(r"Control module:\s*(.+)", line_stripped)
        if control_module_match:
            current_control_module = control_module_match.group(1)

        # Update current job status
        job_status_match = re.match(r"Job status:\s*(.+)", line_stripped)
        if job_status_match:
            current_job_status = job_status_match.group(1)

        # Check for action message
        if re.match(r"Action:\s+Message", line_stripped):
            # Capture the next two lines
            message_lines = []
            for j in range(1, 3):  # Get next two lines
                if i + j < len(lines):
                    next_line = lines[i + j].strip()
                    # Normalize the text
                    next_line = next_line.replace('-', '').strip()
                    # Filter out unwanted messages
                    if next_line and not any(phrase.lower() in next_line.lower() for phrase in ignore_phrases):
                        message_lines.append(next_line)
            if message_lines:
                # Combine the message lines
                full_message = ' '.join(message_lines)
                # Store the message with associated control module and job status
                action_messages.append({
                    'message': full_message,
                    'control_module': current_control_module,
                    'job_status': current_job_status
                })
    return action_messages

def preprocess_gff_log(text):
    vehicle_details = extract_vehicle_details(text)
    action_messages = extract_action_messages(text)
    successful_messages = []
    unsuccessful_messages = []
    neutral_messages = []

    for item in action_messages:
        msg = item['message']
        matched = False
        # Check for successful verbiage
        for verbiage in SUCCESSFUL_VERBIAGE:
            if verbiage.lower().strip() in msg.lower():
                successful_messages.append(item)
                matched = True
                break
        if not matched:
            # Check for unsuccessful verbiage
            for verbiage in UNSUCCESSFUL_VERBIAGE:
                if verbiage.lower().strip() in msg.lower():
                    unsuccessful_messages.append(item)
                    matched = True
                    break
        if not matched:
            neutral_messages.append(item)
    return vehicle_details, successful_messages, unsuccessful_messages, neutral_messages

def main():
    st.title("GFF Log Processor")

    # Upload the PDF file
    uploaded_file = st.file_uploader("Upload GFF log PDF", type="pdf")

    if uploaded_file is not None:
        gff_log_text = extract_text_from_pdf(uploaded_file)

        if gff_log_text:
            st.subheader("Extracted Vehicle Details and Action Messages")

            vehicle_details, successful_messages, unsuccessful_messages, neutral_messages = preprocess_gff_log(gff_log_text)

            # Display vehicle details
            st.write("### Vehicle Details:")
            for key, value in vehicle_details.items():
                st.write(f"**{key}:** {value}")

            # Display action messages with highlighting only on the action message
            st.write("### Action Messages:")
            for item in successful_messages:
                msg = item['message']
                control_module = item['control_module'] or 'N/A'
                job_status = item['job_status'] or 'N/A'

                # Highlight only the action message
                highlighted_msg = f'<span style="background-color: #d4edda;">{msg}</span>'

                st.markdown(
                    f'{highlighted_msg} for Control Module: **{control_module}**<br>Job Status: **{job_status}**',
                    unsafe_allow_html=True
                )

            for item in unsuccessful_messages:
                msg = item['message']
                control_module = item['control_module'] or 'N/A'
                job_status = item['job_status'] or 'N/A'

                # Highlight only the action message
                highlighted_msg = f'<span style="background-color: #f8d7da;">{msg}</span>'

                st.markdown(
                    f'{highlighted_msg} for Control Module: **{control_module}**<br>Job Status: **{job_status}**',
                    unsafe_allow_html=True
                )

            for item in neutral_messages:
                msg = item['message']
                control_module = item['control_module'] or 'N/A'
                job_status = item['job_status'] or 'N/A'

                # Display without highlighting
                st.markdown(
                    f'{msg} for Control Module: **{control_module}**<br>Job Status: **{job_status}**',
                    unsafe_allow_html=True
                )
        else:
            st.error("Failed to extract text from the GFF log PDF file.")
            
if __name__ == '__main__':
    main()