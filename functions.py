import altair as alt
import streamlit as st
import pandas as pd
import numpy as np
import time
import datetime as dt
from datetime import date, datetime 
import pandas as pd
from dateutil.relativedelta import relativedelta # to add days or years
from fdfgen import forge_fdf
import PyPDF2
from PyPDF2 import PdfFileReader, PdfFileWriter
import pdfrw
from fillpdf import fillpdfs
import base64
import os
from streamlit_timeline import timeline
import boto3
import sys
import subprocess
import webbrowser


def calculateAge(birthDate): 
    hoy = datetime.now()
    hoy = hoy.strftime("%d%m%Y")
    today_day = hoy[0:2]
    today_month = hoy[2:4]
    today_year = hoy[4:]
    day = birthDate[0:2]
    month = birthDate[2:5]
    year = birthDate[4:]
    edad = int(today_year) - int(year) - ((int(today_month), int(today_day)) < (int(month), int(day)))
    return edad


def open_chrome(pdf_file):
    """
    Open a PDF file in a new tab in chrome
    """
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', pdf_file))
    elif os.name == 'nt':
        os.startfile(pdf_file)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', pdf_file))


def s3_upload(bucket_name, file_path, key_obj_path):
    salme_bucket = s3_client.Bucket(bucket_name)
    bucket_file_path = file_path
    key_object = key_obj_path
    salme_bucket.upload_file(bucket_file_path, key_object)

def s3_download(bucket_name, target_path, origin_file_path):
    salme_bucket = s3_client.Bucket(bucket_name)
    bucket_file_path = target_path
    st.write('',f'KEY: {origin_file_path}, FILENAME: {target_path}')
    salme_bucket.download_file(Key = target_path, Filename = origin_file_path)

@st.cache(persist = True)
def load_mexico_cities():
    return pd.read_csv('./mx.csv')

@st.cache()
def municipios():
    df = load_mexico_cities()
    estados = st.multiselect('Estados', df['admin_name'].unique(), key=0)
    ciudades = df[df['admin_name'].isin(estados)]['city']
    ciudades = st.selectbox('',ciudades)


def f_nacimiento():
    #format = 'DD MMM, YYYY'  # format output
    start_date = dt.date(year=1920,month=1,day=1)-relativedelta(years=2)  #  I need some range in the past
    end_date = dt.datetime.now().date()
    max_days = end_date-start_date
    #slider = st.date_input('Fecha de nacimiento: ', key=93423)#min_value=start_date, value=end_date, max_value=end_date, key=000)
    fecha = fecha
    return(fecha)

def displayPDF(file):
    # Opening file from file path
    with open(file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')

    # Embedding PDF in HTML
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1400" type="application/pdf"></iframe>'
    # Displaying File
    st.markdown(pdf_display, unsafe_allow_html=True)

@st.cache(persist=True)
def cie_10():
    cie10 = pd.read_csv('./data/cie-10.csv', usecols=[0,6], header=0, names=['code','diagnostic'])
    cie10['code'] = cie10['diagnostic'] + ' CIE-10 ('+ cie10['code']+')'
    return cie10