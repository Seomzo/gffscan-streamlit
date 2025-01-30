import os
import re
import streamlit as st
from ro_parser import parse_ro_with_llm
from onetime_use_parts import SNIPPETS
from snippets_util import build_snippets_dict, find_best_snippet_for_parts, normalize_part_number

# Import the new logic from gff_processor
from gff_processor import extract_text_from_pdf, preprocess_gff_log


# Load verbiage from secrets
SUCCESSFUL_VERBIAGE = st.secrets["verbiage"]["successful_verbiage"]
UNSUCCESSFUL_VERBIAGE = st.secrets["verbiage2"]["unsuccessful_verbiage"]

# Build snippet->required_parts
ALL_SNIPPET_PARTS = build_snippets_dict(SNIPPETS)

def main():
    st.title("Claims Processing Tool (Prototype)")

    # Session states
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    if 'uploaded_ro' not in st.session_state:
        st.session_state.uploaded_ro = None

    with st.form(key='gff_form'):
        uploaded_gff = st.file_uploader("Upload GFF log PDF", type="pdf")
        uploaded_ro = st.file_uploader("Upload RO PDF", type="pdf")
        submit_button = st.form_submit_button(label='Submit')

    if submit_button:
        st.session_state.uploaded_ro = uploaded_ro
        st.session_state.uploaded_file = uploaded_gff
        st.session_state.submitted = True

        if st.session_state.submitted:
            if st.session_state.uploaded_file is not None:
                # Process GFF log if uploaded
                gff_log_text = extract_text_from_pdf(st.session_state.uploaded_file)
                if gff_log_text:
                    st.subheader("Extracted Vehicle Details and Action Messages")

                    vehicle_details, success_msgs, fail_msgs, neutral_msgs = preprocess_gff_log(
                        gff_log_text, SUCCESSFUL_VERBIAGE, UNSUCCESSFUL_VERBIAGE
                    )

                    # Display vehicle details
                    st.write("### Vehicle Details:")
                    for k, v in vehicle_details.items():
                        st.write(f"**{k}:** {v}")

                    # Display action messages
                    st.write("### Action Messages:")

                    def display_messages(messages, color):
                        for item in messages:
                            msg = item['message']
                            test_step = item.get('test_step', 'N/A')
                            job_status = item.get('job_status', 'N/A')
                            highlighted_msg = f'<span style="background-color: {color}; padding: 5px;">{msg}</span>'
                            st.markdown(
                                f'{highlighted_msg} for Test Step: **{test_step}**<br>Job Status: **{job_status}**',
                                unsafe_allow_html=True
                            )

                    # Show only successful and unsuccessful messages (highlighted)
                    display_messages(success_msgs, '#098215')  # Green for successful
                    display_messages(fail_msgs, '#f8d7da')  # Red for unsuccessful

                    # Collapsible dropdown for all messages
                    with st.expander("See All Messages"):
                        st.write("### All Action Messages:")
                        all_messages = success_msgs + fail_msgs + neutral_msgs

                        for item in all_messages:
                            msg = item['message']
                            test_step = item.get('test_step', 'N/A')
                            job_status = item.get('job_status', 'N/A')
                            st.markdown(
                                f'{msg} for Test Step: **{test_step}**<br>Job Status: **{job_status}**',
                                unsafe_allow_html=True
                            )
                else:
                    st.error("Failed to extract text from the GFF log PDF file.")

            if st.session_state.uploaded_ro is not None:
                # Process the RO file if uploaded
                ro_text = extract_text_from_pdf(st.session_state.uploaded_ro)
                if ro_text:
                    st.subheader("Repair Order - Parts Validation")
                    
                    # Extract vehicle details from the RO
                    lines = ro_text.splitlines()
                    vehicle_type = "Unknown"
                    vin = "Unknown"
                    mileage_in_out = "Unknown"

                    # Find the line containing "Vehicle:"
                    for i, line in enumerate(lines):
                        if "Vehicle" in line:
                            # Attempt to read next line as vehicle type
                            if i + 1 < len(lines):
                                vehicle_type_line = lines[i + 1].strip()
                                # If it ends with '-', append the next line
                                if vehicle_type_line.endswith('-') and (i + 2 < len(lines)):
                                    vehicle_type_line += lines[i + 2].strip()
                                vehicle_type = vehicle_type_line

                            # VIN is the next line after vehicle type
                            if i + 2 < len(lines):
                                vin_line = lines[i + 2].strip()
                                # If we merged lines for type, VIN might be i+3
                                if vehicle_type_line.endswith('-') and i + 3 < len(lines):
                                    vin_line = lines[i + 3].strip()
                                vin = vin_line

                            # Find mileage line
                            mileage_regex = re.search(
                                r'(\d{1,3},\d{3} Mi In\s*/\s*\d{1,3},\d{3} Mi Out)',
                                ro_text.replace('\n', ' ')
                            )
                            if mileage_regex:
                                mileage_in_out = mileage_regex.group(1).strip()
                            break
                    st.write(f"[DEBUG] RO text length: {len(ro_text)} characters")

                    # Display Vehicle Details
                    st.write("### Vehicle Details:-")
                    st.write(f"**Type:** {vehicle_type}")
                    st.write(f"**VIN:** {vin}")
                    st.write(f"**Mileage In/Out:** {mileage_in_out}")

                    st.write("### RO Details:-")

                    jobs_data = parse_ro_with_llm(ro_text)
                    if not jobs_data:
                        st.warning("No jobs or parts were detected by the LLM from this RO.")
                    else:
                        for job_dict in jobs_data:
                            job_name = job_dict.get("job_name", "Unknown Job")
                            description = job_dict.get("Description", "No Description")
                            tech_story = job_dict.get("tech_story", [])
                            replaced_parts = job_dict.get('parts', [])

                            st.write(f"**LLM-Extracted Job Name:** {job_name}")
                            st.write(f"**Job Description:** {description}")
                            st.write("**Tech Story:**")
                            for story in tech_story:
                                st.write(f"- {story}")
                            st.write("**Replaced Parts (LLM extracted):**")
                            for p in replaced_parts:
                                st.write(f"- {p}")

                            best_snippet, overlap = find_best_snippet_for_parts(replaced_parts, ALL_SNIPPET_PARTS)

                            if best_snippet:
                                st.write(f"**Identified Snippet**: {best_snippet} (overlap={overlap})")
                                required_set = ALL_SNIPPET_PARTS[best_snippet]
                                replaced_norm = set(normalize_part_number(rp) for rp in replaced_parts)
                                missing = required_set - replaced_norm
                                if missing:
                                    st.error(f"Missing parts: {missing}")
                                else:
                                    st.success("All required parts are present for this snippet!")
                            else:
                                st.warning("Could not match replaced parts to any known snippet. Overlap=0")
                else:
                    st.error("Failed to extract text from the RO PDF.")

        if st.session_state.uploaded_file is None and st.session_state.uploaded_ro is None:
            st.error("Please upload at least one PDF (GFF log or RO file) to proceed.")

        if st.button("Try Another"):
            st.session_state.submitted = False
            st.session_state.uploaded_file = None
            st.session_state.uploaded_ro = None
            st.experimental_rerun()

if __name__ == '__main__':
    main()