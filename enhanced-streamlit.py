import streamlit as st
import anthropic
import json
import pandas as pd
from PyPDF2 import PdfReader
import io
import re
from datetime import datetime
import streamlit.components.v1 as components

def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'current_regimen' not in st.session_state:
        st.session_state.current_regimen = {
            'diagnosis': '',
            'regimen_name': '',
            'phases': {
                'Phase 1': {
                    'pretreatment': [],
                    'chemotherapy': [],
                    'targeted_therapy': [],
                    'cycle_details': {}
                },
                'Phase 2': {
                    'pretreatment': [],
                    'chemotherapy': [],
                    'targeted_therapy': [],
                    'cycle_details': {}
                }
            }
        }
    
    if 'active_view' not in st.session_state:
        st.session_state.active_view = "chat"

def process_pdf_with_claude(file_content):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    
    prompt = """Extract the following information from this chemotherapy order template:
    1. Diagnosis
    2. Treatment regimen name
    3. Pre-treatment medications (name, dose, route, timing)
    4. Chemotherapy medications (name, dose, route, infusion time)
    5. Targeted therapy details
    6. Cycle information
    
    Format the response as JSON with this structure:
    {
        "diagnosis": "string",
        "regimen_name": "string",
        "phase1": {
            "pretreatment": [{
                "name": "string",
                "dose": "string",
                "route": "string",
                "timing": "string"
            }],
            "chemotherapy": [{
                "name": "string",
                "dose": "string",
                "route": "string",
                "infusion_time": "string"
            }],
            "targeted_therapy": [{
                "name": "string",
                "dosing": [{
                    "week": "string",
                    "dose": "string",
                    "route": "string",
                    "infusion_time": "string"
                }]
            }]
        }
    }
    
    PDF Content:
    {file_content}
    """
    
    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

def update_regimen_data(extracted_data):
    try:
        # Update basic information
        st.session_state.current_regimen['diagnosis'] = extracted_data.get('diagnosis', '')
        st.session_state.current_regimen['regimen_name'] = extracted_data.get('regimen_name', '')
        
        # Update Phase 1 data
        if 'phase1' in extracted_data:
            phase1_data = extracted_data['phase1']
            st.session_state.current_regimen['phases']['Phase 1'] = {
                'pretreatment': phase1_data.get('pretreatment', []),
                'chemotherapy': phase1_data.get('chemotherapy', []),
                'targeted_therapy': phase1_data.get('targeted_therapy', []),
                'cycle_details': phase1_data.get('cycle_details', {})
            }
        
        return True
    except Exception as e:
        st.error(f"Error updating regimen data: {str(e)}")
        return False

def create_react_component():
    # Create JSON data for React component
    component_data = {
        'diagnosis': st.session_state.current_regimen['diagnosis'],
        'regimen_name': st.session_state.current_regimen['regimen_name'],
        'phase1': st.session_state.current_regimen['phases']['Phase 1']
    }
    
    # Inject data into React component
    react_code = f"""
    <script>
        window.regimen_data = {json.dumps(component_data)};
    </script>
    """
    
    components.html(react_code, height=0)

def display_regimen_data():
    st.subheader("Current Regimen Data")
    
    # Display basic information
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Diagnosis", st.session_state.current_regimen['diagnosis'], key='diagnosis')
    with col2:
        st.text_input("Regimen Name", st.session_state.current_regimen['regimen_name'], key='regimen_name')
    
    # Create tabs for phases
    phase_tabs = st.tabs(["Phase 1", "Phase 2"])
    
    for i, phase in enumerate(["Phase 1", "Phase 2"]):
        with phase_tabs[i]:
            phase_data = st.session_state.current_regimen['phases'][phase]
            
            # Pre-treatment medications
            st.markdown("##### Pre-treatment Medications")
            if phase_data['pretreatment']:
                df_pretreat = pd.DataFrame(phase_data['pretreatment'])
                edited_pretreat = st.data_editor(
                    df_pretreat,
                    num_rows="dynamic",
                    hide_index=True
                )
                # Update data if edited
                if not df_pretreat.equals(edited_pretreat):
                    st.session_state.current_regimen['phases'][phase]['pretreatment'] = edited_pretreat.to_dict('records')
            
            # Chemotherapy medications
            st.markdown("##### Chemotherapy")
            if phase_data['chemotherapy']:
                df_chemo = pd.DataFrame(phase_data['chemotherapy'])
                edited_chemo = st.data_editor(
                    df_chemo,
                    num_rows="dynamic",
                    hide_index=True
                )
                # Update data if edited
                if not df_chemo.equals(edited_chemo):
                    st.session_state.current_regimen['phases'][phase]['chemotherapy'] = edited_chemo.to_dict('records')
            
            # Targeted therapy
            st.markdown("##### Targeted Therapy")
            if phase_data['targeted_therapy']:
                for therapy in phase_data['targeted_therapy']:
                    st.markdown(f"###### {therapy['name']}")
                    df_dosing = pd.DataFrame(therapy['dosing'])
                    edited_dosing = st.data_editor(
                        df_dosing,
                        num_rows="dynamic",
                        hide_index=True
                    )
                    # Update data if edited
                    if not df_dosing.equals(edited_dosing):
                        therapy['dosing'] = edited_dosing.to_dict('records')

def main():
    st.title("Chemotherapy Regimen Assistant")
    
    # Initialize session state
    initialize_session_state()
    
    # Create React component with current data
    create_react_component()
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        view = st.radio("Select View", ["Chat", "Data View"])
        st.session_state.active_view = view.lower()
        
        # File upload
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file:
            with st.spinner("Processing PDF..."):
                pdf_reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text()
                
                # Process with Claude
                extracted_data = process_pdf_with_claude(pdf_text)
                if extracted_data:
                    if update_regimen_data(extracted_data):
                        st.success("Successfully extracted regimen data")
                        # Recreate React component with updated data
                        create_react_component()
    
    # Main content area
    if st.session_state.active_view == "chat":
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask about the regimen..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Get Claude response
            response = get_claude_response(prompt)
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        display_regimen_data()

def get_claude_response(prompt):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    
    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        st.error(f"Error getting response: {str(e)}")
        return None

if __name__ == "__main__":
    main()