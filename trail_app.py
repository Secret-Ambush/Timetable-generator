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


def remove_header(df):
    header_row_index = df[df.iloc[:, 0] == 'COM COD'].index[0]
    df = df.drop(index=df.index[:header_row_index]).reset_index(drop=True)
    df.columns = df.iloc[0]
    df = df.drop(index=0).reset_index(drop=True)
    
    return df

def generate_timetable(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype='pdf')
    
    num_pages = len(doc)
    doc.close()

    tables = read_pdf(uploaded_file, pages='all', multiple_tables=True)
    try:
        if tables:
            df = remove_header(tables[0])
            column_names = df.columns
            for i in range(1, num_pages):
                temp_df = tables[i]
                temp_df.columns = column_names
                df = pd.concat([df, temp_df], ignore_index=True)
                print("********************************")
                print(i)
    except Exception as E:
        pass
      
st.set_page_config(layout="wide", page_title="Timetable Generator")      
            
uploaded_file = st.file_uploader("Upload the academic calendar you've received", type="pdf")
if uploaded_file:
    generate_timetable(uploaded_file)