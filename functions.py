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
from os.path import exists
import streamlit.components.v1 as components
import requests
from pyfiscal.generate import GenerateCURP

s3_client = boto3.resource('s3')
s3 = boto3.client('s3')

def insert_css_url(file_name, url):
    html_file = f'.html/{file_name}.html'
    css_file = f'.css/{file_name}.css'
    js_file = f'.js/{file_name}.js'
        
    if exists(f'{html_file}'):
        with open(html_file) as f:
            st.markdown(f'<p><a href="{url}" Target="_blank">{f.read()}</a></p>''', unsafe_allow_html=True)

    if exists(f'{css_file}'):
      with open(css_file) as f:
        st.markdown(f'''<style>{f.read()}</style>''', unsafe_allow_html=True)

    if exists(f'{js_file}'):
      st.write('','HOLA')
      with open(js_file, 'r') as l:
        components.html('''<div><script src="js/paisaje.js"></script></div>''')


def insert_css(file_name):
    html_file = f'.html/{file_name}.html'
    css_file = f'.css/{file_name}.css'
    js_file = f'.js/{file_name}.js'
        
    if exists(f'{html_file}'):
        with open(html_file) as f:
            st.markdown(f'{f.read()}', unsafe_allow_html=True)

    if exists(f'{css_file}'):
      with open(css_file) as f:
        st.markdown(f'''<style>{f.read()}</style>''', unsafe_allow_html=True)

    if exists(f'{js_file}'):
      st.write('','HOLA')
      with open(js_file, 'r') as l:
        components.html('''<div><script src="js/paisaje.js"></script></div>''')


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
    # st.write('',f'KEY: {origin_file_path}, FILENAME: {target_path}')
    salme_bucket.download_file(Key = target_path, Filename = origin_file_path)

# @st.cache(persist = True)
def load_mexico_cities():
    return pd.read_csv('./mx.csv')

# @st.cache()
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

# @st.cache(persist=True)
def cie_10():
    cie10 = pd.read_csv('./data/cie-10.csv', usecols=[0,6], header=0, names=['code','diagnostic'])
    cie10['code'] = cie10['diagnostic'] + ' CIE-10 ('+ cie10['code']+')'
    return cie10

def pdf_embed(url):
    st.markdown(f'''{url}''', unsafe_allow_html=True)

# def cie_11():
#     token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
#     client_id = 'cbcfad3e-70d5-4f9e-9e98-51aaec3b551d_df2d133a-0ba7-4f5d-b783-e4f28345d86b'
#     client_secret = 'obTkndgm68hS7rDW4cJaPmZWjq0RCbl0zi2CBKBsRBE='
#     scope = 'icdapi_access'
#     grant_type = 'client_credentials'


#     # get the OAUTH2 token

#     # set data to post
#     payload = {'client_id': client_id, 
#             'client_secret': client_secret, 
#             'scope': scope, 
#             'grant_type': grant_type}
            
#     # make request
#     r = requests.post(token_endpoint, data=payload, verify=False).json()
#     token = r['access_token']


#     # access ICD API

#     uri = 'https://id.who.int/icd/entity'

#     # HTTP header fields to set
#     headers = {'Authorization':  'Bearer '+token, 
#             'Accept': 'application/json', 
#             'Accept-Language': 'en',
#         'API-Version': 'v2'}
            
#     # make request           
#     r = requests.get(uri, headers=headers, verify=False)

#     # print the result
#     print (r.text)			

def calculate_age(born):
    today = datetime.now()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def calc_curp(nombres, a_paterno, a_materno, fecha_nacimiento, sexo, edo_nac):
    edo_nac = edo_nac.upper()
    #remove edo_nac accents
    edo_nac = edo_nac.replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
    
    if edo_nac == 'CIUDAD DE MEXICO':
        edo_nac = 'DISTRITO FEDERAL'
    if edo_nac == 'COAHUILA DE ZARAGOZA':
        edo_nac = 'COAHUILA'
    #string to date
    fecha_nacimiento = datetime.strptime(fecha_nacimiento, '%d%m%Y')
    #fecha_nacimiento into string
    fecha_nacimiento=fecha_nacimiento.strftime("%d-%m-%Y")
    kwargs = {
	"complete_name": f"{nombres}",
	"last_name": f"{a_paterno}",
	"mother_last_name": f"{a_materno}",
	"birth_date": f"{fecha_nacimiento}",
	"gender": f"{sexo}", 
	"city": f"{edo_nac}",
	"state_code": ""
}
    curp = GenerateCURP(**kwargs)
    data = curp.data
    return data

def medicine_extract(tx):
    tx_med = tx.splitlines(keepends=True)
    lab_position = 0
    for i in tx_med:
        # print(i)
        if '6.' in i:
            #find list position
            lab_position =  tx_med.index(i)
            # st.write(lab_position)
            break
    tx_med = tx_med[5:lab_position]
    temp_med = ''
    for i in tx_med:
        temp_med = f'{temp_med}'+i
    return temp_med