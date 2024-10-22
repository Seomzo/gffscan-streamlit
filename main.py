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

# def extract_vehicle_details(text):
#     vehicle_details = {}
#     patterns = {
#         'Brand': r"Brand:\s*(.+)",
#         'Status': r"Status:\s*(.+)",
#         'Model Year': r"Model year:\s*(.+)",
#         'VIN': r"VIN.*?:\s*([A-Z0-9]+)",
#         'Engine': r"Engine code:\s*(.+)",
#         'Odometer Reading': r"Odometer reading \(km\):\s*([0-9]+)",
#         'Time Required (TU)': r"Time required \(TU\):\s*(.+)",
#         'Log Status': r"Log status:\s*(.+)"
#     }
#     for key, pattern in patterns.items():
#         match = re.search(pattern, text)
#         if match:
#             vehicle_details[key] = match.group(1).strip()
#     return vehicle_details

def extract_vehicle_details(text):
    vehicle_details = {}

    # Extract Brand
    brand_match = re.search(r"Brand:\s*(.+)", text)
    if brand_match:
        vehicle_details['Brand'] = brand_match.group(1).strip()
    
    # Extract Type
    type_match = re.search(r"Type:\s*(.+)", text)
    if type_match:
        vehicle_details['Type'] = type_match.group(1).strip()
    
    # Extract Model/Year
    model_year_match = re.search(r"Model year:\s*(.+)", text)
    if model_year_match:
        vehicle_details['Model Year'] = model_year_match.group(1).strip()

    # Extract VIN
    vin_match = re.search(r"VIN.*?:\s*([A-Z0-9]+)", text)
    if vin_match:
        vehicle_details['VIN'] = vin_match.group(1).strip()

    # Extract Engine
    engine_match = re.search(r"Engine code:\s*(.+)", text)
    if engine_match:
        vehicle_details['Engine'] = engine_match.group(1).strip()

    # Extract Odometer Reading
    odometer_match = re.search(r"Odometer reading \(km\):\s*([0-9]+)", text)
    if odometer_match:
        vehicle_details['Odometer Reading'] = odometer_match.group(1).strip()

    # Extract Time Required
    time_required_match = re.search(r"Time required \(TU\):\s*(.+)", text)
    if time_required_match:
        vehicle_details['Time Required (TU)'] = time_required_match.group(1).strip()
    
    # extract log status
    log_status_match = re.search(r"Log status:\s*(.+)", text)
    if log_status_match:
        vehicle_details['Log Status'] = log_status_match.group(1).strip()


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
        "Date:",
        "https://www.vwhub.com/gff",
        "Please wait",
        "Please leave the ignition switched",
        "The ignition is switched on...",
        "The ignition is switched off..."
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

    # Initialize session state variables
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False

    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None

    # Use a form to group the file uploader and submit button
    with st.form(key='gff_form'):
        uploaded_file = st.file_uploader("Upload GFF log PDF", type="pdf")
        submit_button = st.form_submit_button(label='Submit')

    if submit_button:
        if uploaded_file is not None:
            st.session_state.uploaded_file = uploaded_file
            st.session_state.submitted = True
        else:
            st.error("Please upload a GFF log PDF file before submitting.")

    # Process the file if submitted
    if st.session_state.submitted:
        gff_log_text = extract_text_from_pdf(st.session_state.uploaded_file)

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

        # Add a "Try Another" button
        if st.button("Try Another"):
            # Reset session state variables
            st.session_state.submitted = False
            st.session_state.uploaded_file = None
            st.experimental_rerun()

if __name__ == '__main__':
    main()