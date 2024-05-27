import streamlit as st
import pandas as pd
import numpy as np
import fitz  # PyMuPDF
import tabula
from tabula import read_pdf
from constraint import Problem
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from streamlit_js_eval import streamlit_js_eval

im = Image.open('assets/App_Icon.png')
image = Image.open("assets/3.png")
width, height = image.size


draw = ImageDraw.Draw(image)
text = "Timetable Generator"
font_path = "assets/VastShadow-Regular.ttf"
font_size = 30 
font = ImageFont.truetype(font_path, font_size)
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]

x = (width - text_width) / 2
y = (height - text_height) / 2

draw.text((x, y), text, font=font, fill=(0, 0, 0))

flag = True

footer="""<style>
a:link , a:visited{
color: blue;
background-color: transparent;
text-decoration: underline;
}

a:hover,  a:active {
color: red;
background-color: transparent;
text-decoration: underline;
}

.footer {
position: fixed;
left: 0;
bottom: 0;
width: 100%;
background-color: transparent;
color: white;
text-align: center;
}
</style>
<div class="footer">
<p></p>
<p>Made with ♥️ by Riddhi Goswami</p>
</div>
"""

def remove_header(df):
    header_row_index = df[df.iloc[:, 0] == 'COM COD'].index[0]
    df = df.drop(index=df.index[:header_row_index]).reset_index(drop=True)
    df.columns = df.iloc[0]
    df = df.drop(index=0).reset_index(drop=True)
    
    return df

def forward_fill_course_details(df):
    df['COURSE TITLE'].fillna(method='ffill', inplace=True)
    df['COURSE NO.'].fillna(method='ffill', inplace=True)
    df['CREDIT\rL P U'].fillna(method='ffill', inplace=True)
    return df

def map_days_hours_to_time_slots(day_hour_str):
    days = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'Th': 'Thursday', 'F': 'Friday', 'S': 'Saturday', 'Su': 'Sunday'}
    day_hour_list = []
    day_str = ''
    hour_str = ''
    for char in day_hour_str:
        if char.isalpha():
            if day_str and hour_str:
                day = days.get(day_str, "Unknown Day")
                for hour in hour_str:
                    slot = time_slots[day][int(hour)-1]
                    day_hour_list.append((day, slot))
                day_str = ''
                hour_str = ''
            day_str += char
        elif char.isdigit():
            hour_str += char
    if day_str and hour_str:
        day = days.get(day_str, "Unknown Day")
        for hour in hour_str:
            slot = time_slots[day][int(hour)-1]
            day_hour_list.append((day, slot))
    return day_hour_list

def clean_course_title(title):
    words = title.split()
    if 'Practical' in words:
        while words.count('Practical') > 1:
            words.remove('Practical')
        return ' '.join(words)
    else:
        return title

def no_overlap(section1, section2):
                times1 = section1[1]  
                times2 = section2[1]
                for day1, time_range1 in times1:
                    for day2, time_range2 in times2:
                        if day1 == day2:
                            start1, end1 = [int(t.replace(':', '')) for t in time_range1.split('-')]
                            start2, end2 = [int(t.replace(':', '')) for t in time_range2.split('-')]
                            if not (end1 <= start2 or start1 >= end2):
                                return False
                return True

def all_courses_no_overlap(*sections):
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            if not no_overlap(sections[i], sections[j]):
                return False
    return True
       
def highlight_practicals(df):
    try:
        merg = pd.concat([st.session_state.all_elective_df['COURSE TITLE'], st.session_state.hum['COURSE TITLE']],ignore_index=True)
        elective_titles = set(merg)
    except:
        try:
            elective_titles = st.session_state.hum['COURSE TITLE']
        except:
            try:
                elective_titles = st.session_state.all_elective_df['COURSE TITLE']
            except:
                pass
            pass
        pass
    styles_df = pd.DataFrame("", index=df.index, columns=df.columns)

    # Function to apply styles to each cell
    def apply_styles(cell, col_name, row_index):
        style = "background-color: lightgrey; color: black;"

        if "Practical" in str(cell):
            style = "background-color: lightyellow; color: black;"
            
        if "LABORATORY" in str(cell):
            style = "background-color: lightyellow; color: black;"
        
        try:
            for i in elective_titles:
                if i in str(cell):
                    style = "background-color: lightgreen; color: black;"
        
        except:
            pass

        if col_name == "Friday" and row_index >= 6:
            style = "background-color: black; color: white;"

        return style

    for col_name in df.columns:
        for row_index, cell in enumerate(df[col_name], start=1):
            styles_df.at[row_index, col_name] = apply_styles(cell, col_name, row_index)

    table_styles = [{'selector': 'th, td', 'props': [('border', '1px solid black')]}]

    return df.style.apply(lambda x: styles_df[x.name], axis=0).set_table_styles(table_styles)

def generate_csv(df):
    csv = df.to_csv(index=False)
    return csv.encode()

def generate_timetable(uploaded_file, timetable_placeholder, download_button_placeholder, course_details_placeholder, flag1 = False):
    doc = fitz.open(stream=uploaded_file.read(), filetype='pdf')
    num_pages = len(doc)
    doc.close()

    tables = read_pdf(uploaded_file, pages='all', multiple_tables=True)
    if tables:
        df = remove_header(tables[0])
        column_names = df.columns
        for i in range(1, num_pages):
            temp_df = tables[i]
            temp_df.columns = column_names
            df = pd.concat([df, temp_df], ignore_index=True)
        
        df = df.drop('COM COD', axis=1)
        df = forward_fill_course_details(df)
        df = df.dropna(subset=['DAYS/  HOURS'])
        df['TIME SLOTS'] = df['DAYS/  HOURS'].apply(map_days_hours_to_time_slots)
        humanities = df[df['COURSE NO.'].str.startswith('HSS')]
        disp_elec = df[
            (
                (df['COURSE NO.'].str.startswith('CS') | df['COURSE NO.'].str.startswith('MATH') | 
                df['COURSE NO.'].isin(['BITS F312', 'BITS F416', 'BITS F452', 'BITS F464']))
                & ~df['COURSE NO.'].isin(first_year_first_semester_requirements)
                & ~df['COURSE NO.'].isin(first_year_second_semester_requirements)
                & ~df['COURSE NO.'].isin(second_year_first_semester_requirements) 
                & ~df['COURSE NO.'].isin(second_year_second_semester_requirements) 
                & ~df['COURSE NO.'].isin(third_year_first_semester_requirements) 
                & ~df['COURSE NO.'].isin(third_year_second_semester_requirements)
            )
            & ~df['COURSE TITLE'].str.contains('Practical')
        ]

        
        if st.session_state.year == "First Year":
            if st.session_state.semester == "First Semester":
                compulsory_df = df[df['COURSE NO.'].isin(first_year_first_semester_requirements)]
            elif st.session_state.semester == "Second Semester":
                compulsory_df = df[df['COURSE NO.'].isin(first_year_second_semester_requirements)]
        
        elif st.session_state.year == "Second Year":
            if st.session_state.semester == "First Semester":
                compulsory_df = df[df['COURSE NO.'].isin(second_year_first_semester_requirements)]
                st.session_state.hum = humanities
            elif st.session_state.semester == "Second Semester":
                compulsory_df = df[df['COURSE NO.'].isin(second_year_second_semester_requirements)]
                all_elective_df = df[df['COURSE NO.'].isin(second_year_second_semester_elective)]
                st.session_state.all_elective_df = all_elective_df
                st.session_state.hum = humanities
        
        elif st.session_state.year == "Third Year":
            if st.session_state.semester == "First Semester":
                compulsory_df = df[df['COURSE NO.'].isin(third_year_first_semester_requirements)]
                all_elective_df = disp_elec
                st.session_state.all_elective_df = disp_elec
                st.session_state.hum = humanities
            elif st.session_state.semester == "Second Semester":
                compulsory_df = df[df['COURSE NO.'].isin(third_year_second_semester_requirements)]
                all_elective_df = disp_elec
                st.session_state.all_elective_df = disp_elec
                st.session_state.hum = humanities
                
        
        elif st.session_state.year == "Fourth Year":
            compulsory_df = []
            all_elective_df = disp_elec
            st.session_state.all_elective_df = disp_elec
            st.session_state.hum = humanities
        
        try:
            compulsory_df.reset_index(drop=True, inplace=True)
            for index, row in compulsory_df.iterrows():
                if index == 0:
                    continue
                
                if row['COURSE TITLE'] == 'Practical':
                    prev_course_title = compulsory_df.at[index - 1, 'COURSE TITLE']
                    compulsory_df.at[index, 'COURSE TITLE'] = prev_course_title + ' Practical'

            compulsory_df['COURSE TITLE'] = compulsory_df.apply(lambda row: clean_course_title(row['COURSE TITLE']), axis=1)
            st.session_state.initial_df = compulsory_df
        
        except:
            pass
        
        try:
            if 'constraints' in st.session_state and st.session_state['constraints']:
                for selected_course, selected_section in st.session_state['constraints'].items():
                    enforced_course_id = selected_course
                    enforced_section = selected_section

                    compulsory_df = compulsory_df[~((compulsory_df['COURSE TITLE'] == enforced_course_id) &
                                                    (compulsory_df['SEC'] != enforced_section))]

            else:
                pass
        except:
            if 'constraints' in st.session_state and st.session_state['constraints']:
                for selected_course, selected_section in st.session_state['constraints'].items():
                    enforced_course_id = selected_course
                    enforced_section = selected_section

                    compulsory_df = disp_elec[~((disp_elec['COURSE TITLE'] == enforced_course_id) &
                                                    (disp_elec['SEC'] != enforced_section))]

            else:
                pass
            
        if st.session_state.electives:
            if st.session_state.hum is not None:
                    try:
                        all_elective_df = pd.concat([st.session_state.hum, all_elective_df], ignore_index=True)
                    except:
                        all_elective_df = st.session_state.hum
            elective_dfs = []
            all_elec = []

            for selected_elec, selected_elec_section in st.session_state['electives'].items():
                enforced_elec_id = selected_elec
                enforced_elec_section = selected_elec_section
                temp_df = all_elective_df[(all_elective_df['COURSE TITLE'] == enforced_elec_id) &
                                                (all_elective_df['SEC'] == enforced_elec_section)]
                elective_dfs.append(temp_df)
                
                temp_df = all_elective_df[(all_elective_df['COURSE TITLE'] == enforced_elec_id)]
                all_elec.append(temp_df)
            
            all_elec = pd.concat(all_elec, ignore_index=True)
            st.session_state.merged_df = pd.concat([st.session_state.initial_df, all_elec], ignore_index=True)
            try:
                merged_df = pd.concat([compulsory_df, all_elec], ignore_index=True)
            except:
                merged_df = all_elec
            elective_df = pd.concat(elective_dfs, ignore_index=True)
            st.session_state.enforced_elective = elective_df
        else:
            pass
            
        if compulsory_df is None:
            st.info("All constraints can't be statisfied ⚠️")
            pass
        
        else:
            st.session_state.compulsory_df = compulsory_df
            problem = Problem()
            

            course_sections = {}
            
            try:

                for _, row in compulsory_df.iterrows():
                    course_id = row['COURSE TITLE']
                    section = row['SEC']
                    time_slots = row['TIME SLOTS']

                    if course_id not in course_sections:
                        course_sections[course_id] = []

                    course_sections[course_id].append((section, time_slots))
                    
            except:
                pass
             
            if st.session_state.electives:   
                for _, row in elective_df.iterrows():
                    elec_course_id = row['COURSE TITLE']
                    elec_section = row['SEC']
                    time_slots = row['TIME SLOTS']

                    if elec_course_id not in course_sections:
                        course_sections[elec_course_id] = []

                    course_sections[elec_course_id].append((elec_section, time_slots))
                    
            for course_id, sections in course_sections.items():
                problem.addVariable(course_id, sections)

            problem.addConstraint(all_courses_no_overlap, list(course_sections.keys()))

            solution = problem.getSolution() #SOLUTION

            if solution:
                if flag1:
                    pass
                else:
                    st.write("\n\n")
                    st.success("Successfully generated timetable")
            else:
                st.warning("No possible schedule found that satisfies all your constraints.")
                return

            course_map = {}
            for course, details in solution.items():
                section, times = details
                for day_time in times:
                    day, time = day_time
                    section = int(section)
                    course_info = f"{course} (Sec {section})"
                    if (day, time) not in course_map:
                        course_map[(day, time)] = course_info
                    else:
                        course_map[(day, time)] += " / " + course_info
                        
            time_slots = {
                'Monday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00', '12:05-12:55', '1:00-1:50', '1:55-2:45', '2:50-3:40'],
                'Tuesday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00', '12:05-12:55', '1:00-1:50', '1:55-2:45', '2:50-3:40'],
                'Wednesday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00', '12:05-12:55', '1:00-1:50', '1:55-2:45', '2:50-3:40'],
                'Thursday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00', '12:05-12:55', '1:00-1:50', '1:55-2:45', '2:50-3:40'],
                'Friday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00']
            }
            
            num_days = len(time_slots)
            max_slots = max(len(slots) for slots in time_slots.values())
            timetable = np.full((num_days, max_slots), '', dtype=object)

            days_list = list(time_slots.keys())
            all_slots = set(slot for day_slots in time_slots.values() for slot in day_slots)
            slots_list = sorted(all_slots)

            for day_idx, (day, slots) in enumerate(time_slots.items()):
                for slot_idx, slot in enumerate(slots):
                    if (day, slot) in course_map:
                        timetable[day_idx, slot_idx] = course_map[(day, slot)]
                    else:
                        timetable[day_idx, slot_idx] = ''

            timetable_transposed = timetable.T
            timetable_df = pd.DataFrame(timetable_transposed, columns=list(time_slots.keys()))
            timetable_df.index = range(1, len(timetable_df) + 1)
            
            styled_df = highlight_practicals(timetable_df)
            html = styled_df.to_html()
            timetable_placeholder.markdown(html, unsafe_allow_html=True)
            st.write("\n\n")
            
            col1, col2, col3, col4, col5 = download_button_placeholder.columns([1, 1, 1, 1, 1])
            slot_numbers = list(range(1, 10))
            timetable_df.insert(0, 'Days', slot_numbers)
            csv = generate_csv(timetable_df)
            col3.download_button(label="Download Timetable 📚", data=csv, file_name="timetable.csv", mime="text/csv")
            
            data = []
            for course, details in solution.items():
                section_number = details[0]
                
                if st.session_state.electives:
                    filtered_df = merged_df[(merged_df['SEC'] == section_number) & (merged_df['COURSE TITLE'] == course)]['INSTRUCTOR-IN-CHARGE/ Instructor']
                else:
                    filtered_df = compulsory_df[(compulsory_df['SEC'] == section_number) & (compulsory_df['COURSE TITLE'] == course)]['INSTRUCTOR-IN-CHARGE/ Instructor']
                try:
                    instructor_name = filtered_df.iloc[0]
                except:
                    instructor_name = " "
                if 'Practical' in course:
                    section_number = 'P' + str(int(section_number))
                     
                else:
                    section_number = 'L' + str(int(section_number))
                data.append({'Course': course, 'Section': section_number, 'Instructor': instructor_name})
            
            course_details_placeholder.table(data)
            
            st.write("\n\n")

def clear_multi():
    st.session_state.multiselect = []
    return

def create_divider(width, height, line_color, line_height):
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.line((0, height // 2, width, height // 2), fill=line_color, width=line_height)
    return image

time_slots = {
    'Monday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00', '12:05-12:55', '1:00-1:50', '1:55-2:45', '2:50-3:40'],
    'Tuesday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00', '12:05-12:55', '1:00-1:50', '1:55-2:45', '2:50-3:40'],
    'Wednesday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00', '12:05-12:55', '1:00-1:50', '1:55-2:45', '2:50-3:40'],
    'Thursday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00', '12:05-12:55', '1:00-1:50', '1:55-2:45', '2:50-3:40'],
    'Friday': ['7:30-8:20', '8:25-9:15', '9:20-10:10', '10:15-11:05', '11:10-12:00'],
}

if 'year' not in st.session_state:
    st.session_state.year = None
if 'semester' not in st.session_state:
    st.session_state.semester = None
if 'discipline' not in st.session_state:
    st.session_state.discipline = None
if 'constraints' not in st.session_state:
    st.session_state.constraints = {}
if 'electives' not in st.session_state:
    st.session_state.electives = {}
if 'compulsory_df' not in st.session_state:
    st.session_state.compulsory_df = None
if 'all_elective_df' not in st.session_state:
    st.session_state.all_elective_df = None
if 'merged_df' not in st.session_state:
    st.session_state.merged_df = None
if 'selected_course' not in st.session_state:
    st.session_state.selected_course = None
if 'selected_section' not in st.session_state:
    st.session_state.selected_section = None
if 'selected_elective' not in st.session_state:
    st.session_state.selected_elective = None
if 'selected_elec_section' not in st.session_state:
    st.session_state.selected_elec_section = None
if 'initial_df' not in st.session_state:
    st.session_state.initial_df = None
if 'enforced_elective' not in st.session_state:
    st.session_state.enforced_elective = None
if 'hum' not in st.session_state:
    st.session_state.hum = None
if 'selected_hum' not in st.session_state:
    st.session_state.selected_hum = None
if 'multiselect' not in st.session_state:
    st.session_state.multiselect = []
    
year_options = ["First Year", "Second Year", "Third Year", "Fourth Year"]
semester_options = ["First Semester", "Second Semester"]
discipline_options = ["Computer Science (CS)", "Electrical Engineering (EEE)",
                      "Electronics and Communication (ECE)", "Chemical Engineering (Chem)",
                      "Civil Engineering (Civil)"]

first_year_first_semester_requirements = ('BIO F110', 'BIO F111', 'BITS F110', 'BITS F112', 'CHEM F110', 'CHEM F111', 'CS F111', 'MATH F111')
first_year_second_semester_requirements = ('BITS F111', 'EEE F111', 'MATH F112', 'MATH F113', 'ME F112', 'PHY F110', 'PHY F111')

second_year_first_semester_requirements = ('CS F213', 'CS F214', 'CS F215', 'CS F222', 'MATH F211')
second_year_second_semester_requirements = ('BITS F225', 'CS F211', 'CS F212', 'CS F241')
second_year_second_semester_elective = ('ECON F211', 'MGTS F211')

third_year_first_semester_requirements = ('CS F301', 'CS F342', 'CS F351', 'CS F372')
third_year_first_semester_elective = ('ECON F211', 'MGTS F211')
third_year_second_semester_requirements = ('CS F363', 'CS F303', 'CS F364')
third_year_second_semester_elective = ('ECON F211', 'MGTS F211')


st.set_page_config(layout="wide", page_title="Timetable Generator", page_icon = im)
st.image(image, use_column_width=True)
col1, col2 = st.columns([10,2])
col2.write("\n\n")
col2.image("assets/blah3.gif", use_column_width=True)

col1.markdown("""### Welcome to Your Very Own Timetable Application! 
Exclusively for BITS Students! ✨ Do you find it difficult to understand the academic timetable shared by 
the college?   
Or you're just too lazy to find out which electives you can choose? Look no further!  

This application provides a dynamic and interactive way to create your own timetable completely based on 
which discipline, year you're in.  
Navigate through your schedule, explore different courses, and plan your semester more effectively.

##### Features:

Interactive Timetable: Create a timetable based on your electives, section constraints  
Course Details: Click on any course to see detailed information including 
instructor names, room numbers, and session timings. (coming soon ✨)""")

if 'form_submitted' not in st.session_state:
    st.session_state['form_submitted'] = False

with st.form("academic_info_form"):
    st.subheader("Please enter the following academic information:")

    st.session_state.year = st.radio("Select Year", options=year_options, horizontal=True)
    st.session_state.semester = st.radio("Select Semester", options=semester_options, horizontal=True)
    st.caption("For First Year: If you're in Bio sem, choose First Semester, else choose Second Semester")
    st.session_state.discipline = st.selectbox("Select Discipline", options=discipline_options)
    uploaded_file = st.file_uploader("Upload the academic calendar you've received", type="pdf")
    st.write('\n\n')
    col1, col2, col3, col4, col5= st.columns([1,1,1,1,1])
    submitted = col2.form_submit_button("Generate Timetable")
    refresh = col4.form_submit_button("  Refresh Session ")
    
if refresh:
    streamlit_js_eval(js_expressions="parent.window.location.reload()")

timetable_placeholder = st.empty()  
st.write("\n\n")
download_button_placeholder = st.empty() 
course_details_placeholder = st.empty()  

if (submitted and uploaded_file is None):
    st.warning("Please upload timetable provided by college")
        
if (submitted and uploaded_file is not None):
    st.session_state['form_submitted'] = True
    st.success(f"You have selected: {st.session_state.year}, {st.session_state.semester}, {st.session_state.discipline}.")
    if st.session_state.discipline != "Computer Science (CS)" and st.session_state.year != 'First Year':
        st.warning("Not yet implemented 😭")
        flag = False
    else:
        flag = True
        st.session_state.constraints = {}
        st.session_state.electives = {}
        st.session_state.constraints = {}
        st.session_state.compulsory_df = None
        st.session_state.all_elective_df = None
        st.session_state.merged_df = None
        st.session_state.selected_course = None
        st.session_state.selected_section = None
        st.session_state.selected_elective = None
        st.session_state.selected_elec_section = None
        st.session_state.initial_df = None
        st.session_state.enforced_elective = None
        st.session_state.hum = None
        
        generate_timetable(uploaded_file,timetable_placeholder, download_button_placeholder, course_details_placeholder)

st.write('\n\n')       
divider_image = create_divider(800, 2, 'white', 1)
st.image(divider_image, use_column_width=True)
st.write('\n\n')
mymsg2 = st.empty()
st.write('\n\n')

if st.session_state.form_submitted is not None and st.session_state.all_elective_df is not None and flag and st.session_state.year != 'Third Year' and st.session_state.year != 'Fourth Year':
    ele = st.session_state.all_elective_df
    if st.session_state.all_elective_df is not None:
        st.subheader("Add electives?")
        st.caption("⚠️ You can choose only one")
        electives_title = np.sort(ele["COURSE TITLE"].unique())
        selected_elective = st.radio("Select an elective:", electives_title, horizontal=True, key="selected_elective")

        if selected_elective:
            filtered_df2 = ele[ele["COURSE TITLE"] == selected_elective]
            available_sections2 = filtered_df2["SEC"].unique().astype(int)
            selected_elec_section = st.selectbox("Select a section:", available_sections2, key="selected_elec_section")
    else:
        selected_elective = ""
        selected_elec_section = ""


    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    if col4.button("Clear All Electives"):
        if 'electives' in st.session_state:
            st.session_state.electives = {}
        if 'selected_elective' not in st.session_state:
            st.session_state.selected_elective = None
        if 'selected_elec_section' not in st.session_state:
            st.session_state.selected_elec_section = None
        generate_timetable(uploaded_file,timetable_placeholder, download_button_placeholder, course_details_placeholder, True)
    
    if col2.button("Add Electives and Generate"):
        if 'electives' in st.session_state:
            st.session_state.electives = {}
        st.session_state.electives[selected_elective] = selected_elec_section
        mymsg2.write("")
        elective_list = "\n".join([f"- **{course}**: Sec {section}" for course, section in st.session_state.electives.items()])
        content = f"#### Electives Chosen:\n{elective_list}"
        mymsg2.markdown(content)
        
        elective_titles = st.session_state.all_elective_df['COURSE TITLE'].unique()
        keys_to_remove = [key for key in st.session_state.constraints.keys() if key in elective_titles]
        for key in keys_to_remove:
            del st.session_state.constraints[key]
        
        generate_timetable(uploaded_file,timetable_placeholder, download_button_placeholder, course_details_placeholder)

    st.write('\n\n')        

if st.session_state.form_submitted is not None and st.session_state.all_elective_df is not None and flag and (st.session_state.year == 'Third Year' or st.session_state.year == 'Fourth Year'):
    ele = st.session_state.all_elective_df
    if st.session_state.all_elective_df is not None:
        st.subheader("Add electives?")
        st.caption("⚠️ You can choose multiple")
        electives_title = np.sort(ele["COURSE TITLE"].unique()) if ele["COURSE TITLE"].unique().size > 0 else []
        selected_elective = st.multiselect("Select electives:", electives_title, key="multiselect")

    else:
        selected_elective = ""
        selected_elec_section = ""


    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    if col4.button("Clear All Electives ", on_click=clear_multi):
        if 'selected_electives' not in st.session_state:
            st.session_state.selected_electives = []
        if 'electives' in st.session_state:
            st.session_state.electives = {}
        if 'selected_elective' not in st.session_state:
            st.session_state.selected_elective = None
        if 'selected_elec_section' not in st.session_state:
            st.session_state.selected_elec_section = None
        elective_list = "\n".join([f"- **{course}**: Sec {section}" for course, section in st.session_state.electives.items()])
        content = f"#### Electives Chosen:\n{elective_list}"
        mymsg2.markdown(content)
        generate_timetable(uploaded_file, timetable_placeholder, download_button_placeholder, course_details_placeholder, True)
    
    if col2.button("Add Electives and Generate "):
        if 'electives' in st.session_state:
            st.session_state.electives = {}
        for i in selected_elective:
            st.session_state.electives[i] = 1
        mymsg2.write("")
        elective_list = "\n".join([f"- **{course}**: Sec {section}" for course, section in st.session_state.electives.items()])
        content = f"#### Electives Chosen:\n{elective_list}"
        mymsg2.markdown(content)
        
        elective_titles = st.session_state.all_elective_df['COURSE TITLE'].unique()
        keys_to_remove = [key for key in st.session_state.constraints.keys() if key in elective_titles]
        for key in keys_to_remove:
            del st.session_state.constraints[key]
        
        generate_timetable(uploaded_file,timetable_placeholder, download_button_placeholder, course_details_placeholder)
        
if st.session_state.form_submitted is not None and st.session_state.hum is not None and flag and (st.session_state.year == 'Third Year' or st.session_state.year == 'Fourth Year'):
    humanities = st.session_state.hum
    st.subheader("Add humanities electives?")
    st.caption("⚠️ You can choose multiple")
    electives_title = np.sort(humanities["COURSE TITLE"].unique())
    selected_hum = st.radio("Select a humanities elective:", electives_title, horizontal=True, key="selected_hum")

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    if col4.button("Clear All Hum Electives"):
        if 'selected_hum' not in st.session_state:
            st.session_state.selected_hum = None
        for i in electives_title:
            if i in st.session_state.electives.keys():
                del st.session_state.electives[i]
        elective_list = "\n".join([f"- **{course}**: Sec {section}" for course, section in st.session_state.electives.items()])
        content = f"#### Electives Chosen:\n{elective_list}"
        mymsg2.markdown(content)
        generate_timetable(uploaded_file, timetable_placeholder, download_button_placeholder, course_details_placeholder, True)
    
    if col2.button("Add Hum Electives and Generate"):
        st.session_state.electives[selected_hum] = 1
        mymsg2.write("")
        elective_list = "\n".join([f"- **{course}**: Sec {section}" for course, section in st.session_state.electives.items()])
        content = f"#### Electives Chosen:\n{elective_list}"
        mymsg2.markdown(content)
       
        try: 
                elective_titles = st.session_state.all_elective_df['COURSE TITLE'].unique()
                keys_to_remove = [key for key in st.session_state.constraints.keys() if key in elective_titles]
                for key in keys_to_remove:
                    del st.session_state.constraints[key]
        except:
            pass
        
        generate_timetable(uploaded_file, timetable_placeholder, download_button_placeholder, course_details_placeholder)
    
    st.write('\n\n')
    divider_image = create_divider(800, 2, 'white', 1)
    st.image(divider_image, use_column_width=True)
    st.write('\n\n') 

if st.session_state.form_submitted is not None and st.session_state.hum is not None and flag and st.session_state.year != 'Third Year' and st.session_state.year != 'Fourth Year':
    humanities = st.session_state.hum
    st.subheader("Add humanities electives?")
    st.caption("⚠️ You can choose only one")
    electives_title = np.sort(humanities["COURSE TITLE"].unique())
    selected_hum = st.radio("Select a humanities elective:", electives_title, horizontal=True, key="selected_hum")

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    if col4.button("Clear All Hum Electives"):
        if 'selected_hum' not in st.session_state:
            st.session_state.selected_hum = None
        for i in electives_title:
            if i in st.session_state.electives.keys():
                del st.session_state.electives[i]
        elective_list = "\n".join([f"- **{course}**: Sec {section}" for course, section in st.session_state.electives.items()])
        content = f"#### Electives Chosen:\n{elective_list}"
        mymsg2.markdown(content)
        generate_timetable(uploaded_file, timetable_placeholder, download_button_placeholder, course_details_placeholder, True)
    
    if col2.button("Add Hum Electives and Generate"):
        for i in electives_title:
            if i in st.session_state.electives.keys():
                del st.session_state.electives[i]
        st.session_state.electives[selected_hum] = 1
        mymsg2.write("")
        elective_list = "\n".join([f"- **{course}**: Sec {section}" for course, section in st.session_state.electives.items()])
        content = f"#### Electives Chosen:\n{elective_list}"
        mymsg2.markdown(content)
       
        try: 
                elective_titles = st.session_state.all_elective_df['COURSE TITLE'].unique()
                keys_to_remove = [key for key in st.session_state.constraints.keys() if key in elective_titles]
                for key in keys_to_remove:
                    del st.session_state.constraints[key]
        except:
            pass
        
        generate_timetable(uploaded_file, timetable_placeholder, download_button_placeholder, course_details_placeholder)
    
    st.write('\n\n')
    divider_image = create_divider(800, 2, 'white', 1)
    st.image(divider_image, use_column_width=True)
    st.write('\n\n') 
    
if st.session_state.form_submitted is not None and st.session_state.compulsory_df is not None and flag:
    compul_df = st.session_state.initial_df
    merged_df = st.session_state.merged_df
    st.subheader("Need to choose a particular section for a course? 🤔")
    try:
        mymsg = st.empty()
        constraints_list = "\n".join([f"- **{course}**: Sec {section}" for course, section in st.session_state.constraints.items()])
        content = f" ✨ Current Constraints:\n{constraints_list}"
        mymsg.markdown(content)

        if st.session_state.electives:
            available_courses = np.sort(merged_df["COURSE TITLE"].unique())
            selec_course = st.radio("Select a course:", available_courses, horizontal=True, key="selec_course")

            if selec_course:
                filtered_df2 = merged_df[merged_df["COURSE TITLE"] == selec_course]
                available_sections = filtered_df2["SEC"].unique().astype(int)
                selec_section = st.selectbox("Select a section:", available_sections, key="selec_section")
                
        else:
            available_courses = np.sort(compul_df["COURSE TITLE"].unique())
            selec_course = st.radio("Select a course:", available_courses, horizontal=True, key="selec2_course")

            if selec_course:
                filtered_df = compul_df[compul_df["COURSE TITLE"] == selec_course]
                available_sections = filtered_df["SEC"].unique().astype(int)
                selec_section = st.selectbox("Select a section:", available_sections, key="selec2_section")

        col_1, col_2, col_4, col_6 = st.columns([1, 3, 3, 3])
        if col_4.button("Clear All Constraints"):
            if 'constraints' in st.session_state:
                st.session_state.constraints = {}
            if 'selected_course' in st.session_state:
                del st.session_state.selected_course
            if 'selected_section' in st.session_state:
                del st.session_state.selected_section
            generate_timetable(uploaded_file, timetable_placeholder, download_button_placeholder, course_details_placeholder, True)
            
        if col_6.button("Clear All Classes"):
            if 'constraints' in st.session_state:
                st.session_state.constraints = {}
            if 'selected_course' in st.session_state:
                del st.session_state.selected_course
            if 'selected_section' in st.session_state:
                del st.session_state.selected_section
            if 'electives' in st.session_state:
                st.session_state.electives = {}
            if 'selected_elective' not in st.session_state:
                st.session_state.selected_elective = None
            if 'selected_elec_section' not in st.session_state:
                st.session_state.selected_elec_section = None
            if 'selected_hum' not in st.session_state:
                st.session_state.selected_hum = None
            
            st.rerun()
        
        if col_2.button("Apply and Generate Timetable"):
            if 'constraints' not in st.session_state:
                st.session_state.constraints = {}
            st.session_state.constraints[selec_course] = selec_section
            mymsg.write("")
            constraints_list = "\n".join([f"- **{course}**: Sec {section}" for course, section in st.session_state.constraints.items()])
            content = f" ✨ Updated Constraints:\n{constraints_list}"
            mymsg.markdown(content)
            generate_timetable(uploaded_file, timetable_placeholder, download_button_placeholder, course_details_placeholder)
    except:
        st.info("No available courses")
        
st.markdown(footer,unsafe_allow_html=True)
