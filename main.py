import os
import re
import streamlit as st
from PyPDF2 import PdfReader
from verbiage import SUCCESSFUL_VERBIAGE

# Define verbiage
SUCCESSFUL_VERBIAGE = st.secrets["verbiage"]["successful_verbiage"]

# Function to extract text from a PDF
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

# Function to extract vehicle details
def extract_vehicle_details(text):
    vehicle_details = {}
    brand_match = re.search(r"Brand:\s*(.+)", text)
    if brand_match:
        vehicle_details['Brand'] = brand_match.group(1).strip()
    
    type_match = re.search(r"Type:\s*(.+)", text)
    if type_match:
        vehicle_details['Type'] = type_match.group(1).strip()
    
    model_year_match = re.search(r"Model year:\s*(.+)", text)
    if model_year_match:
        vehicle_details['Model Year'] = model_year_match.group(1).strip()

    vin_match = re.search(r"VIN.*?:\s*([A-Z0-9]+)", text)
    if vin_match:
        vehicle_details['VIN'] = vin_match.group(1).strip()

    engine_match = re.search(r"Engine code:\s*(.+)", text)
    if engine_match:
        vehicle_details['Engine'] = engine_match.group(1).strip()

    odometer_match = re.search(r"Odometer reading \(km\):\s*([0-9]+)", text)
    if odometer_match:
        vehicle_details['Odometer Reading'] = odometer_match.group(1).strip()

    time_required_match = re.search(r"Time required \(TU\):\s*(.+)", text)
    if time_required_match:
        vehicle_details['Time Required (TU)'] = time_required_match.group(1).strip()

    log_status_match = re.search(r"Log status:\s*(.+)", text)
    if log_status_match:
        vehicle_details['Log Status'] = log_status_match.group(1).strip()

    return vehicle_details

# Function to extract action messages
def extract_action_messages(text):
    action_messages = set()
    lines = text.splitlines()
    ignore_phrases = [
        "Test step: ", 
        "Please wait...", 
        "NO NOTE", 
        "- Note the following boundary conditions:", 
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
        "MSG_OT_SOD"
    ]
    
    for i, line in enumerate(lines):
        if re.match(r"Action:\s+Message", line.strip()):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not re.match(r"Action:\s+Message", next_line) and not any(phrase in next_line for phrase in ignore_phrases):
                    action_messages.add(next_line)
    return list(action_messages)

# Function to preprocess the log
def preprocess_gff_log(text):
    vehicle_details = extract_vehicle_details(text)
    action_messages = extract_action_messages(text)
    matching_messages = []
    
    for msg in action_messages:
        for verbiage in SUCCESSFUL_VERBIAGE:
            if verbiage.lower().strip() in msg.lower():
                matching_messages.append(msg)
                break
    
    return vehicle_details, action_messages, matching_messages

# Streamlit UI for file upload and processing
def main():
    st.title("GFF Log Processor")

    # Upload the PDF file
    uploaded_file = st.file_uploader("Upload GFF log PDF", type="pdf")

    if uploaded_file is not None:
        gff_log_text = extract_text_from_pdf(uploaded_file)

        if gff_log_text:
            st.subheader("Extracted Vehicle Details and Action Messages")
            
            vehicle_details, action_messages, matching_messages = preprocess_gff_log(gff_log_text)

            # Display vehicle details
            st.write("### Vehicle Details:")
            for key, value in vehicle_details.items():
                st.write(f"**{key}:** {value}")
            
            # Display action messages
            st.write("### Action Messages:")
            for msg in action_messages:
                if msg in matching_messages:
                    st.markdown(f'<span style="background-color: yellow;">{msg}</span>', unsafe_allow_html=True)
                else:
                    st.write(msg)
        else:
            st.error("Failed to extract text from the GFF log PDF file.")

if __name__ == '__main__':
    main()
