import streamlit as st
import json
from typing import Dict, List
import pandas as pd
import plotly.express as px
import datetime

def load_json_file(uploaded_file) -> Dict:
    """Load and parse the uploaded JSON file"""
    try:
        content = uploaded_file.read()
        return json.loads(content)
    except Exception as e:
        st.error(f"Error loading JSON file: {str(e)}")
        return None

def get_treatment_courses(data: Dict) -> List[Dict]:
    """Extract treatment courses from the JSON data"""
    courses = []
    for key, value in data.items():
        if key.startswith("course"):
            courses.append(value)
    return courses

def create_cycle_calendar(course: Dict, cycle_num: int):
    """Create a daily view calendar for a specific cycle"""
    cycle_length = course["cycle_length"]
    calendar_data = []
    
    for day in range(1, cycle_length + 1):
        day_drugs = []
        for drug in course["drugs"]:
            # Check for single day treatment
            if "day" in drug and drug["day"] == day:
                day_drugs.append({
                    "name": drug["name"],
                    "dose": drug["dose"],
                    "route": drug["route"]
                })
            # Check for multiple day treatment
            elif "days" in drug and day in drug["days"]:
                dose = drug["maintenance_dose"] if day > 1 else drug["loading_dose"]
                day_drugs.append({
                    "name": drug["name"],
                    "dose": dose,
                    "route": drug["route"]
                })
        
        calendar_data.append({
            "day": day,
            "drugs": day_drugs,
            "has_treatment": len(day_drugs) > 0
        })
    
    return calendar_data

def display_cycle_calendar(course: Dict, cycle_num: int):
    """Display the calendar view for a specific cycle"""
    calendar_data = create_cycle_calendar(course, cycle_num)
    
    # Create calendar grid
    cols = st.columns(7)
    for idx, day_data in enumerate(calendar_data):
        day = day_data["day"]
        with cols[idx % 7]:
            # Create a container for each day
            with st.container(border=True):
                # Day header
                if day_data["has_treatment"]:
                    st.markdown(f"**Day {day}** 🏥")
                else:
                    st.markdown(f"**Day {day}**")
                
                # Display treatments for the day
                if day_data["drugs"]:
                    for drug in day_data["drugs"]:
                        st.markdown(f"""
                        💊 **{drug['name']}**  
                        Dose: {drug['dose']}  
                        Route: {drug['route']}
                        """)
                else:
                    st.write("No treatments")
        
        # Add a line break after each week
        if (idx + 1) % 7 == 0:
            st.write("")

def create_treatment_timeline(courses: List[Dict]):
    """Create a Gantt chart showing all treatment phases and cycles"""
    timeline_data = []
    current_date = datetime.datetime.now()
    
    for course_idx, course in enumerate(courses):
        course_name = course["name"]
        cycle_length = course["cycle_length"]
        num_cycles = course["cycles"]
        
        if course_idx > 0:
            previous_course = courses[course_idx - 1]
            current_date += datetime.timedelta(days=previous_course["cycles"] * previous_course["cycle_length"])
        
        for cycle in range(1, num_cycles + 1):
            cycle_start = current_date + datetime.timedelta(days=(cycle-1)*cycle_length)
            
            for drug in course["drugs"]:
                # Handle single day treatments
                if "day" in drug:
                    drug_start = cycle_start + datetime.timedelta(days=drug["day"]-1)
                    drug_end = drug_start + datetime.timedelta(days=1)
                    timeline_data.append({
                        "Course": course_name,
                        "Cycle": f"Cycle {cycle}",
                        "Drug": drug["name"],
                        "Start": drug_start,
                        "Finish": drug_end
                    })
                # Handle multiple day treatments
                elif "days" in drug:
                    for day in drug["days"]:
                        drug_start = cycle_start + datetime.timedelta(days=day-1)
                        drug_end = drug_start + datetime.timedelta(days=1)
                        timeline_data.append({
                            "Course": course_name,
                            "Cycle": f"Cycle {cycle}",
                            "Drug": drug["name"],
                            "Start": drug_start,
                            "Finish": drug_end
                        })
    
    if not timeline_data:
        return None
        
    df = pd.DataFrame(timeline_data)
    
    fig = px.timeline(df, 
                     x_start="Start", 
                     x_end="Finish", 
                     y="Course",
                     color="Drug",
                     title="Treatment Timeline",
                     hover_data=["Cycle"])
    
    fig.update_layout(height=300)
    return fig

def main():
    st.set_page_config(
        page_title="Treatment Regimen Planner",
        page_icon="💊",
        layout="wide"
    )

    st.title("Treatment Regimen Planner")

    # File uploader
    uploaded_file = st.file_uploader("Upload Regimen JSON file", type=['json'])
    
    if not uploaded_file:
        st.info("Please upload a JSON file to view the regimen details.")
        return

    # Load data
    data = load_json_file(uploaded_file)
    if not data:
        return

    # Get treatment courses
    courses = get_treatment_courses(data)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Treatment Calendar", "Regimen Overview", "Timeline"])

    with tab1:
        st.header("Treatment Calendar")
        
        # Course and cycle selection
        col1, col2 = st.columns(2)
        with col1:
            course_idx = st.selectbox(
                "Select Treatment Course",
                range(len(courses)),
                format_func=lambda x: f"Course {x+1}: {courses[x]['name']}"
            )
        
        selected_course = courses[course_idx]
        
        with col2:
            cycle_num = st.selectbox(
                "Select Cycle",
                range(1, selected_course["cycles"] + 1),
                format_func=lambda x: f"Cycle {x}"
            )
        
        # Display cycle information
        st.subheader(f"Course {course_idx + 1} - Cycle {cycle_num} Schedule")
        st.info(f"""
        Course: {selected_course['name']}  
        Cycle Length: {selected_course['cycle_length']} days  
        Total Cycles in Course: {selected_course['cycles']}
        """)
        
        # Display calendar
        display_cycle_calendar(selected_course, cycle_num)
        
        # Display supportive care
        st.subheader("Supportive Care")
        with st.container(border=True):
            for care in selected_course["supportive_care"]:
                st.write(f"• {care}")

    with tab2:
        st.header("Regimen Overview")
        
        # Display indication
        st.subheader("Indication")
        st.info(data["indication"])
        
        # Display courses
        for course_idx, course in enumerate(courses, 1):
            with st.expander(f"Course {course_idx}: {course['name']}", expanded=True):
                st.write(f"**Duration:** {course['cycles']} cycles of {course['cycle_length']} days")
                
                st.write("**Drug Schedule:**")
                for drug in course["drugs"]:
                    if "day" in drug:
                        st.write(f"• {drug['name']} ({drug['dose']}) - {drug['route']} on Day {drug['day']}")
                    elif "days" in drug:
                        st.write(f"• {drug['name']}")
                        st.write(f"  - Loading: {drug['loading_dose']} - {drug['route']}")
                        st.write(f"  - Maintenance: {drug['maintenance_dose']} - {drug['route']}")
                        st.write(f"  - Days: {', '.join(map(str, drug['days']))}")
                
                if "maintenance_trastuzumab" in course:
                    st.write("\n**Maintenance Trastuzumab:**")
                    st.write(f"• Duration: {course['maintenance_trastuzumab']['duration']} weeks")
                    st.write(f"• Dose: {course['maintenance_trastuzumab']['dose']}")
                
                st.write("\n**Supportive Care:**")
                for care in course["supportive_care"]:
                    st.write(f"• {care}")

    with tab3:
        st.header("Treatment Timeline")
        timeline_fig = create_treatment_timeline(courses)
        if timeline_fig:
            st.plotly_chart(timeline_fig, use_container_width=True)

    # Add download button for JSON
    st.sidebar.header("Download Data")
    json_str = json.dumps(data, indent=2)
    st.sidebar.download_button(
        label="Download JSON",
        data=json_str,
        file_name="regimen_data.json",
        mime="application/json"
    )

if __name__ == "__main__":
    main()
