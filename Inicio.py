# import altair as alt
import streamlit as st
import pandas as pd
import time
from datetime import date, datetime 
from fdfgen import forge_fdf
from fillpdf import fillpdfs
import os
from streamlit_timeline import timeline
import boto3
import functions as fx
import ex_mental as em
import random
import app_functions as afx
from streamlit.components.v1 import html
from pathlib import Path
import os
from dotenv import load_dotenv
from app_functions import (
    get_audio_recorder_html,
    process_audio_data,
    initialize_audio_system,
    WhisperTranscriber
)

# Al inicio de tu app
load_dotenv()
mongodb_uri = os.getenv("MONGODB_URI")
gemini_api = os.getenv("GEMINI_API")
deepinfra_api = os.getenv("DEEPINFRA_API")

st.set_page_config(
    page_title=" Historia Clínica",
    page_icon="fav.png",  # EP: how did they find a symbol?
    layout="wide",
    initial_sidebar_state="collapsed",
)


if 'audio_initialized' not in st.session_state:
    st.session_state.audio_initialized = initialize_audio_system()


def get_base64_image(image_path):
    import base64
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()
logo_path = Path('vitalia.png')

if logo_path.exists():
    logo_base64 = get_base64_image(logo_path)
else:
    logo_base64 = ""  # Si no hay logo, usa una cadena vacía o placeholder
    st.warning("Logotipo no encontrado en la ruta especificada.")

def load_css():
    with open('style.css', 'r') as f:
        css = f.read()
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

def load_js():
    with open('javascript.js', 'r') as f:
        js = f.read()
    st.markdown(f'<style>{js}</style>', unsafe_allow_html=True)

# Llama a la función al principio de tu app
load_css()

# load_js()
# st.markdown("""
#     <div class="app-header">
#         <h1>Historia clínica</h1>
#     </div>
# """, unsafe_allow_html=True)

st.markdown(f"""
    <div class="app-header">
        <div class="logo-container">
            <img src="data:image/png;base64,{logo_base64}" class="logo" alt="Logo">
        </div>
        
    </div>
    
""", unsafe_allow_html=True)
st.markdown('<div class="title-container"><h1>Historia Clínica</h1>', unsafe_allow_html=True)


s3 = boto3.client('s3')
dsm_path = '/home/vazzam/Documentos/SALME_app/DSM_5.pdf'

path_folder = os.getcwd()+'/tmp/'
municipios = pd.read_csv('./data/mx.csv')
pdf_template = './data/HC_SALME_python.pdf'
renglon = '\n'
date = datetime.now()
date = date.strftime("%d/%m/%Y %H:%M")
header_html = f"""
<div class="app-header">
        <div class="logo-container">
            <img src="data:image/png;base64,{logo_base64}" class="logo" alt="Logo">
        </div>
    <div class="header-icon-container">
        <!-- Botón Home -->
        <a href="/" class="icon-button" target="_self">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
            </svg>
        </a>
        <!-- Botón Consulta Subsecuentes -->
        <a href="/Subsecuentes" class="icon-button" target="_self">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M19 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 16H7v-2h10v2zm0-4H7v-2h10v2zm0-4H7V9h10v2z"/>
            </svg>
        </a>
        <!-- Botón Búsqueda IA -->
        <a href="/Research" class="icon-button">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
            </svg>
        </a>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)
if 'ta' not in st.session_state:
    st.session_state.ta = ''


# --- Inicialización de st.session_state ---

# Ficha de Identificación
if 'curp' not in st.session_state:
    st.session_state.curp = ''  # CURP deshabilitado
if 'no_expediente' not in st.session_state:
    st.session_state.no_expediente = ''
if 'date' not in st.session_state:
    st.session_state.date = datetime.now().strftime("%d/%m/%Y %H:%M")  # Fecha actual por defecto
if 'nombre' not in st.session_state:
    st.session_state.nombre = ''
if 'apellido_paterno' not in st.session_state:
    st.session_state.apellido_paterno = ''
if 'apellido_materno' not in st.session_state:
    st.session_state.apellido_materno = ''
if 'sexo' not in st.session_state:
    st.session_state.sexo = 'Hombre'  # Valor por defecto
if 'f_nacimiento' not in st.session_state:
    st.session_state.f_nacimiento = '11/01/2000'  # Fecha por defecto (string)
if 'f_nacimiento_str' not in st.session_state:  # Para guardar la fecha como string
    st.session_state.f_nacimiento_str = ''
if 'edad' not in st.session_state:
    st.session_state.edad = '' # String vacio. Se calcula despues
if 'ciudades' not in st.session_state:
    st.session_state.ciudades = ''  # O un valor por defecto si tienes una lista de ciudades
if 'edo_nac' not in st.session_state:
    st.session_state.edo_nac = ''   # O un valor por defecto
if 'tipo_vialidad' not in st.session_state:
    st.session_state.tipo_vialidad = 'Calle'  # Valor por defecto
if 'dom_vialidad' not in st.session_state:
    st.session_state.dom_vialidad = ''
if 'dom_no_ext' not in st.session_state:
    st.session_state.dom_no_ext = ''
if 'dom_no_int' not in st.session_state:
    st.session_state.dom_no_int = ''
if 'cp' not in st.session_state:
    st.session_state.cp = ''
if 'dom_tipo_asentamiento' not in st.session_state:
    st.session_state.dom_tipo_asentamiento = 'Colonia' # Valor por defecto
if 'dom_asentamiento' not in st.session_state:
    st.session_state.dom_asentamiento = ''
if 'dom_cd' not in st.session_state:
    st.session_state.dom_cd = '' # O un valor por defecto.
if 'dom_edo' not in st.session_state:
    st.session_state.dom_edo = ''  # O un valor por defecto.
if 'escolaridad' not in st.session_state:
    st.session_state.escolaridad = 'Ninguna' # Valor por defecto
if 'edo_civil' not in st.session_state:
    st.session_state.edo_civil = 'Soltero' # Valor por defecto
if 'religion' not in st.session_state:
    st.session_state.religion = 'católica'# Valor por defecto
if 'ocupacion' not in st.session_state:
    st.session_state.ocupacion = ''
if 'trabajo' not in st.session_state:
    st.session_state.trabajo = 'Empleado'  # Valor por defecto
if 'etnia' not in st.session_state:
     st.session_state.etnia = 'mestizo'
if 'seg_social' not in st.session_state:
    st.session_state.seg_social = 'NINGUNA'  # Valor por defecto
if 'referido' not in st.session_state:
    st.session_state.referido = 'no referido'  # Valor por defecto
if 'inst_ref' not in st.session_state:
    st.session_state.inst_ref = ''
if 'responsable_nombre' not in st.session_state:
    st.session_state.responsable_nombre = ''
if 'responsable_tel' not in st.session_state:
    st.session_state.responsable_tel = ''
if 'responsable_parentesco' not in st.session_state:
    st.session_state.responsable_parentesco = ''


# Motivo de Consulta y Padecimiento Actual
if 'mc' not in st.session_state:
    st.session_state.mc = ''
# Antecedentes Personales No Patológicos
if 'apnp_vive_con' not in st.session_state:
    st.session_state.apnp_vive_con = ''
if 'apnp_tipo_vivienda' not in st.session_state:
    st.session_state.apnp_tipo_vivienda = 'casa'
if 'apnp_medio_vivienda' not in st.session_state:
    st.session_state.apnp_medio_vivienda = 'urbano'
if 'apnp_vivienda_servicios' not in st.session_state:
    st.session_state.apnp_vivienda_servicios = 'con agua, luz y drenaje'
if 'apnp_no_comidas' not in st.session_state:
    st.session_state.apnp_no_comidas = '3'
if 'apnp_cal_comidas' not in st.session_state:
    st.session_state.apnp_cal_comidas = 'buena'
if 'apnp_agua' not in st.session_state:
    st.session_state.apnp_agua = 'adecuado'
if 'apnp_ejercicio' not in st.session_state:
    st.session_state.apnp_ejercicio = 'nula'
if 'apnp_baño' not in st.session_state:
    st.session_state.apnp_baño = 'diario'
if 'apnp_sexual' not in st.session_state:
    st.session_state.apnp_sexual = 'heterosexual'
if 'apnp_viajes' not in st.session_state:
    st.session_state.apnp_viajes = ''
if 'apnp_animales' not in st.session_state:
    st.session_state.apnp_animales = ''
if 'apnp_exposicion' not in st.session_state:
    st.session_state.apnp_exposicion = ''
if 'apnp_tatuajes' not in st.session_state:
    st.session_state.apnp_tatuajes = ''
if 'apnp_vacunas' not in st.session_state:
    st.session_state.apnp_vacunas = ''
if 'apnp_ago' not in st.session_state:  # AGO / Ant. Sexuales
    st.session_state.apnp_ago = ''
if 'apnp_anexo_hosp' not in st.session_state:
    st.session_state.apnp_anexo_hosp = ""

# Interrogatorio por Aparato y Sistemas
if 'ipas' not in st.session_state:
    st.session_state.ipas = ''

# Consumo de Sustancias
if 'sust_tabaco' not in st.session_state:
    st.session_state.sust_tabaco = ''
if 'sust_alcohol' not in st.session_state:
    st.session_state.sust_alcohol = ''
if 'sust_cannabis' not in st.session_state:
    st.session_state.sust_cannabis = ''
if 'sust_cocaina' not in st.session_state:
    st.session_state.sust_cocaina = ''
if 'sust_cristal' not in st.session_state:
    st.session_state.sust_cristal = ''
if 'sust_solventes' not in st.session_state:
    st.session_state.sust_solventes = ''
if 'sust_alucinogenos' not in st.session_state:
    st.session_state.sust_alucinogenos = ''
if 'sust_otras' not in st.session_state:
    st.session_state.sust_otras = ''
if 'labs_prev' not in st.session_state:
    st.session_state.labs_prev = ""

# Exploración Física
if 'ef_somatotipo' not in st.session_state:
    st.session_state.ef_somatotipo = 'mesomorfo'
if 'ef_apariencia' not in st.session_state:
    st.session_state.ef_apariencia = 'buen'
if 'ef_hidratacion' not in st.session_state:
    st.session_state.ef_hidratacion = 'buen'
if 'ef_color' not in st.session_state:
    st.session_state.ef_color = 'normal'
if 'peso' not in st.session_state:
    st.session_state.peso = 0.0 # Usar float para peso
if 'talla' not in st.session_state:
    st.session_state.talla = 0.0  # Usar float para talla
if 'imc' not in st.session_state:
    st.session_state.imc = 0.0 #Calculado
if 'ta' not in st.session_state:
    st.session_state.ta = ''
if 'fc' not in st.session_state:
    st.session_state.fc = ''
if 'fr' not in st.session_state:
    st.session_state.fr = ''
if 'temp' not in st.session_state:
    st.session_state.temp = ''

if 'alt_cabeza' not in st.session_state:
    st.session_state.alt_cabeza = ""
if 'alt_abdomen' not in st.session_state:
    st.session_state.alt_abdomen = ""
if 'alt_cuello' not in st.session_state:
    st.session_state.alt_cuello = ""
if 'alt_extremidades_sup' not in st.session_state:
    st.session_state.alt_extremidades_sup = ""
if 'alt_cardio' not in st.session_state:
    st.session_state.alt_cardio = ""
if 'alt_extremidades_inf' not in st.session_state:
    st.session_state.alt_extremidades_inf = ""
if 'alt_genitales' not in st.session_state:
    st.session_state.alt_genitales = ""
if 'alt_otras' not in st.session_state:
    st.session_state.alt_otras = ""

# Examen Mental
if 'examen_mental' not in st.session_state:
     st.session_state.examen_mental = ""

# Diagnósticos, Pronóstico, Clinimetría, Tratamiento, Análisis
#   Se inicializan dentro de sus respectivos formularios.  Buena práctica.
if 'gaf' not in st.session_state:
    st.session_state.gaf = ""
if 'phq9' not in st.session_state:
    st.session_state.phq9 = ""
if 'gad7' not in st.session_state:
    st.session_state.gad7 = ""
if 'sadpersons' not in st.session_state:
    st.session_state.sadpersons = ""
if 'young' not in st.session_state:
    st.session_state.young = ""
if 'mdq' not in st.session_state:
    st.session_state.mdq = ""
if 'asrs' not in st.session_state:
    st.session_state.asrs = ""
if 'otras_clini' not in st.session_state:
    st.session_state.otras_clini = ""
if 'pronostico' not in st.session_state:
    st.session_state.pronostico = ""
if 'labs_nvos' not in st.session_state:
    st.session_state.labs_nvos = ""
if 'analisis' not in st.session_state:
    st.session_state.analisis = ""
    



# with st.sidebar:

#     escalas_expander = st.expander('Clinimetrías')
#     with escalas_expander:
#         escala_selected = st.selectbox('Selecciona la escala:',afx.stored_data('escalas'), key=342342)
#         fx.displayPDF(f'./data/clinimetrias/{escala_selected}')



ficha_ID = st.form('ficha_ID')
with ficha_ID:
    ("Ficha de identificación")
    col1,col2,col3 = st.columns([0.6,0.2,0.2])

    with col1:
        st.session_state.curp = st.text_input("CURP: ", disabled=True)
    with col2:


        st.session_state.no_expediente = st.text_input("No. expediente: ")
    with col3:
        #format = 'DD MMM, YYYY'
        st.session_state.date = st.text_input("Fecha: ",date)
        #date_str = date.strftime("%d/%m/%Y")

    col4, col5, col6, col7 = st.columns([0.3,0.25,0.25,0.2])
    with col4:
        st.session_state.nombre = st.text_input('Nombre(s): ')
    with col5:
        st.session_state.apellido_paterno = st.text_input('Apellido paterno: ')
    with col6:
        st.session_state.apellido_materno = st.text_input('Apellido materno: ')
        nombre_completo = f'{st.session_state.nombre} {st.session_state.apellido_paterno} {st.session_state.apellido_materno}'

    with col7:
        genero = ''
        st.session_state.sexo = st.radio('Sexo:', ['Hombre','Mujer'])
        binary_sexo = 0
        if st.session_state.sexo == 'Hombre':
            mujer = ''
            hombre = 'Yes'
            genero = 'H'
        else:
            mujer = 'Yes'
            hombre = ''
            genero = 'M'
            ## Range selector


    col8, col9, col10,col11 = st.columns([0.40,0.15,0.25,0.15])

    with col8:

        # st.session_state.f_nacimiento = st.date_input("Fecha de nacimiento aaaa/mm/dd:",dt.datetime(1980,11,2),key='f_nacimiento_2')
        st.session_state.f_nacimiento = st.text_input('Fecha de nacimiento (dd/mm/yyyy): ', '11/01/2000',key='f_nac')
        # st.date_input('fecha', format="DD.MM.YY")
        # For date validation
        if len(st.session_state.f_nacimiento) != 10:
            st.markdown("""
            <div style="background-color: #FEE2E2; padding: 1rem; border-radius: 0.5rem; color: #991B1B;">
                <strong>Error:</strong> El formato de la fecha de nacimiento es incorrecto. Utilice el formato dd/mm/yyyy (ej. 02/12/1989). Actualiza la app y reintenta
            </div>
            """, unsafe_allow_html=True)
            st.stop()
        st.session_state.f_nacimiento = datetime.strptime(st.session_state.f_nacimiento, '%d/%m/%Y')
        temp_date = st.session_state.f_nacimiento
        st.session_state.f_nacimiento = st.session_state.f_nacimiento.strftime("%d%m%Y")

    with col9:
        st.session_state.edad = st.text_input('Edad:',f'{afx.calculate_age(temp_date)}', disabled=True)#st.text_input('Edad: ', '0')
    with col10:
        df = municipios
        st.session_state.ciudades = st.selectbox('Ciudad de nacimiento: ',df['city'].unique())

    with col11:
        st.session_state.edo_nac = st.selectbox('Edo. Nacimiento:', df['admin_name'].unique(), key=44)
        #st.session_state.ciudades = st.selectbox('Ciudad de nacimiento: ',df['city'].unique())
    if st.session_state.nombre != '':
        try:
            st.session_state.curp = fx.calc_curp(st.session_state.nombre,st.session_state.apellido_paterno,st.session_state.apellido_materno,
            st.session_state.f_nacimiento, genero, st.session_state.edo_nac)
        except:
            st.session_state.curp = ''
        st.write(st.session_state.curp)

    st.subheader('Domicilio')
    col12, col13, col14,col15, col16 = st.columns([0.20,0.35,0.10,0.10,0.15])

    with col12:
        st.session_state.tipo_vialidad = st.selectbox('Tipo de vialidad: ', ['Calle', 'Andador', 'Avenida', 'Privada', 'Carretera', 'Brecha','Circuito'])

    with col13:
        st.session_state.dom_vialidad = st.text_input('Nombre de vialidad:')

    with col14:
        st.session_state.dom_no_ext = st.text_input('Número exterior:')

    with col15:
        st.session_state.dom_no_int = st.text_input('Interior:')

    with col16:
        st.session_state.cp = st.text_input('Código postal:')  

    col17, col18, col19,col20, col_tel = st.columns([0.20,0.25,0.20,0.20,0.15])

    with col17:
        st.session_state.dom_tipo_asentamiento = st.selectbox('Tipo de asaentamiento: ', ['Colonia', 'Fraccionamiento', 'Coto', 'Privada', 'Ranchería', 'Comunidad', 'Pueblo','Villa', 'Ranchería'])

    with col18:
        st.session_state.dom_asentamiento = st.text_input('Nombre del asentamiento:')

    with col19:
        st.session_state.dom_cd = st.selectbox('Municipio:',df['city'].unique(), key=789271)
        #st.session_state.dom_edo = st.selectbox('Entidad federativa:',df['admin_name'].unique(), key=4412)

    with col20:
        st.session_state.dom_edo = st.selectbox('Entidad federativa:',df['admin_name'].unique(), key=4412)
        #st.session_state.dom_cd = st.selectbox('Municipio:',df['city'].unique(), key=789271)
    with col_tel:
        tel = st.text_input('Teléfono:', key=87011)


    col21, col22, col23,col24, col25 = st.columns([0.15,0.15,0.20,0.30,0.15])

    with col21:

        escolaridad_arr = ['Ninguna', 'Primaria', 'Secundaria', 'Bachillerato', 'Licenciatura', 'Posgrado']
        st.session_state.escolaridad = st.selectbox('Escolaridad: ', escolaridad_arr)

    with col22:
        st.session_state.edo_civil = st.selectbox('Estado civil: ', ['Soltero', 'Casado', 'Unión libre','Divorciado', 'Viudo', 'Separado'])

    with col23:
        st.session_state.religion = st.selectbox('Religión: ',['católica','cristiana','judía','mormona','islam', 'otra', 'ninguna','no referida'])#,key='religion')
        #st.session_state.religion = st.text_input('Religión:')

    with col24:
        st.session_state.ocupacion = st.text_input('Ocupación habitual:')

    with col25:
        trabajo_arr = ['Empleado', 'Desempleado', 'Subempleado']

        st.session_state.trabajo = st.selectbox('Estatus laboral actual: ', trabajo_arr)

    col26, col27, col28,col29= st.columns([0.20,0.20,0.15,0.25])

    with col26:
        indigena_options = ['indigena_no','indigena_si']
        indigena_arr = ['mestizo', 'indígena']
        st.session_state.etnia = st.selectbox('Etnia: ', indigena_arr)

    with col27:
        ss_arr = ['NINGUNA', 
            'IMSS', 'ISSSTE', 'SEDENA', 'SEMAR', 'IMSS-PROSPERA', 'PEMEX', 
            'SEGURO POPULAR', 'OTRA', 'SE IGNORA', 'NO ESPECIFICADO']
        st.session_state.seg_social = st.selectbox('Afiliación a servicios de salud: ', ss_arr)

    with col28:
        referido_options = ['referido_no','referido_si']
        referido_arr = ['no referido', 'referido']
        st.session_state.referido = st.selectbox('Referencia:', referido_arr)

    with col29:
        st.session_state.inst_ref = st.text_input('Institución que refiere: ')

    col30, col31, col32 = st.columns([0.40,0.30,0.30])
    with col30:
        st.session_state.responsable_nombre = st.text_input('Nombre del responsable:')

    with col31:
        st.session_state.responsable_tel = st.text_input('Teléfono:')

    with col32:
        st.session_state.responsable_parentesco = st.text_input('Parentesco:')

    form_ID_button = st.form_submit_button('Guardar ficha de identificación')
    if form_ID_button:
        date_chr = len(st.session_state.f_nacimiento)#.split("/")
        st.success('Se han guardado los cambios')
transcripcion = afx.audio_recorder_transcriber_v2('primera', deepinfra_api)
#=====================================================================================================
# transcripcion = afx.audio_recorder_transcriber()
iepa_form = st.form('iepa_form')
with iepa_form:

    st.header('Motivo de consulta')
    mc_consulta = st.expander('La razón por la que acuden a valoración')
    with mc_consulta:   
        st.session_state.mc = st.text_area('',height=120)  

    st.header('Padecimiento actual')
    padecimiento = st.expander('Inicio, curso, tendencia, desencadenantes, agravantes, síntomas clave, síntomas actuales')
    with padecimiento:
        
        pepa = st.text_area('', transcripcion, height=200)
    iepa_form_button = st.form_submit_button('Guarde el padecimiento actual')
    if iepa_form_button:
        st.success('Se han guardado los cambios')

        
antecedentes_form = st.form('antecedentes_form')
with antecedentes_form:          

    st.header('Antecedentes Heredo Familiares')

    AHF = st.expander('Llenar antecedentes personales heredofamiliares')
    with AHF:

        col33, edad_padres,col34 = st.columns([0.15,0.05,0.70])
        with col33:
            ahf_padre = st.selectbox('Padre', ['vivo','finado','desconocido'])
            ahf_madre = st.selectbox('Madre', ['viva','finada','desconocida'])

        with edad_padres:
            ahf_edad_padre = st.text_input('edad',key=123)
            ahf_edad_madre = st.text_input('edad',key='edad_padre')
        with col34:
            ahf_padre_ant = st.text_input('Antecedentes: ', 'sin antecedentes de relevancia',key='ant_padre')
            ahf_madre_ant = st.text_input('Antecedentes: ', 'sin antecedentes de relevancia',key='ant_madre')
        
        col35, col36, col37 = st.columns([0.3,0.3,0.4])

        with col35:
            ahf_hermanos = st.text_area('Hermanos: ','antecedentes patológicos negados',height=70,key='Hermanos')
        with col36:
            ahf_hijos = st.text_area('Hijos:','antecedentes patológicos negados',height=70,key='Hijos')
        with col37:
            ahf_otros = st.text_area('Otros:','antecedentes patológicos negados',height=70,key='Otros')



        st.subheader('Antecedentes Familiares Psiquiátricos')
        ahf_psiquiatricos = st.text_area('','Negados',key='fam_psiq', height=70)    
        if ahf_edad_padre == '':
            padre_merge = f'Padre {ahf_padre} de edad no referida: {ahf_padre_ant}'
        else:
            padre_merge = f'Padre {ahf_padre} de {ahf_edad_padre} años: {ahf_padre_ant}'
        if ahf_edad_madre == '':
            madre_merge = f'Madre {ahf_madre} de edad no especificada: {ahf_madre_ant}'
        else:
            madre_merge = f'Madre {ahf_madre} de {ahf_edad_madre} años: {ahf_madre_ant}'

        padres_merge = f'{padre_merge}. {renglon}{madre_merge}'
        ahf_merge = f'{padres_merge}. {renglon}Hermanos: {ahf_hermanos}.{renglon}Hijos: {ahf_hijos}.\
                    {renglon}Otros:{ahf_otros}.{renglon}ANTECEDENTES FAMILIARES PSIQUIÁTRICOS:{renglon}{ahf_psiquiatricos}.'

    st.header('Antecedentes Personales Patológicos')
    APP = st.expander('Llenar antecedentes personales Patológicos')
    with APP:
        col38, col39, col40 = st.columns([0.33,0.33,0.33])
        with col38:
            app_alergias = st.text_area('Alergias','Negadas', height=70, key='Alergias')
        with col39:
            app_qx = st.text_area('Cirugías/Fracturas','Negadas', height=70, key='qx_fx')
        with col40:
            app_tce = st.text_area('TCE/Convulsiones','Negados', height=70, key='tec_conv')

        col41,  col42, col43 = st.columns([0.33,0.33,0.33])
        with col41:
            app_transfusiones = st.text_area('Transfusiones','Negadas',height=70, key='Transusiones')
        with col42:
            app_infecciosas = st.text_area('Enfermedades Infecciosas','Negadas',height=70, key='Infecciosas')
        with col43:
            app_cronicas = st.text_area('Enfermedades Crónico-degenerativas','Negadas',height=70, key='cronicas')

        col44, col45 = st.columns([0.5,0.5])

        with col44:
            app_otras = st.text_area('Otras','Negadas',height=70,key='Otras')

        with col45:
            app_medicamentos = st.text_area('Medicamentos','Negados',height=70,key='Medicamentos')


        st.subheader('Antecedentes Personales Psiquiátricos')
        app_psiquiatricos = st.text_area('','Negados')  
        apnp_anexo_hosp = st.text_input('Anexiones u hospitalizaciones:',"Negadas",key='hospi')
        
        app_merge = f'Alergias: {app_alergias}, Transfusiones: {app_transfusiones}, Cirugías/Fracturas: {app_qx}, TCE/Convulsiones: {app_tce}, Enfermedades infecciosas: {app_infecciosas}, Enfermedades crónico-degenerativas: {app_cronicas}{renglon}OTRAS: {app_otras}{renglon}MEDICAMENTOS: {app_medicamentos}{renglon}>>>>>>>ANTECEDENTES PSIQUIÁTRICOS:<<<<<<<{renglon}{app_psiquiatricos}.'


    st.header('Antecedentes Personales No Patológicos')

    APNP = st.expander('Llenar antecedentes personales no Patológicos')
    with APNP:
        col46, col47, col48, col49 = st.columns([0.2,0.2,0.2,0.2])
        with col46:
            apnp_vive_con = st.text_input('¿Con quién vive?','con ',key='vive_con')
        with col47:
            apnp_tipo_vivienda = st.selectbox('Tipo de vivienda:',['casa','departamento','calle','albergue'],key='tipo_vivienda')
        with col48:
            apnp_medio_vivienda = st.selectbox('en medio:',['urbano','semiurbano','rural'],key='medio_vivienda')
        with col49:
            apnp_vivienda_servicios = st.selectbox('servicios:',['con agua, luz y drenaje','sin todos los servicios'],key='servicios')

        col50, col51, col52, col53, col54 = st.columns([0.2,0.2,0.2,0.2,0.2])
        with col50:
            apnp_no_comidas = st.text_input('No. comidas al día:','3',key='no_comidas')

        with col51:
            apnp_cal_comidas = st.selectbox('calidad y cantidad de alimentación:',['buena', 'regular', 'mala'],key='calidad_alim')

        with col52:
            apnp_agua = st.selectbox('consumo de agua:',['adecuado', 'regular','pobre','elevado'],key='agua')

        with col53:
            apnp_ejercicio = st.selectbox('actividad física',['nula','2-3 días/semana','>3 días/semana', 'todos los días'],key='ejercicio')

        with col54:
            apnp_baño = st.selectbox('baño y cambio de ropa',['diario','1-2 veces por semana','3 veces por semana', 'diario', 'nunca'],key='ejercicios')

        col55, col56, col57, col58 = st.columns([0.25,0.25,0.25,0.25])
        with col55:
            apnp_sexual = st.selectbox('Orientación sexual:',['heterosexual','bisexual','homosexual','pansexual','asexual', 'no referida'],key='orientacion_sex')

        with col56:
            apnp_viajes = st.text_input('Viajes:','Negados',key='viajes')

        with col57:
            apnp_animales = st.text_input('Convivencia con animales','Negados',key='animales')

        with col58:
            apnp_exposicion = st.text_input('Exp. a biomasa, solventes, agroquímicos, etc.','Negados',key='')

        col59, col60, col61 = st.columns([0.33,0.33,0.33])

        with col59:
            apnp_tatuajes = st.text_input('Tatuajes o perforaciones:','Negados',key='tatuajes')

        with col60:
            apnp_vacunas = st.text_input('Inumizaciones:','Completas para la edad y con esquema de Sars-Cov-2: completo',key='vacunas')

        with col61:
            if genero == 'H':
                apnp_ago = st.text_input('ANT. SEXUALES','IVSA:, PS:',key='ago')
            else:
                apnp_ago = st.text_input('AGO:','Menarca: , IVSA: , PS: , FUM: , Ciclos: regulares 28x3, G:0 P:0 C:0 A:0, Anticoncepción: ninguna', key='ago')
            apnp_ago = f'AGO: {apnp_ago}'

        apnp_merge = f'Vive {apnp_vive_con}, en {apnp_tipo_vivienda} en un medio {apnp_medio_vivienda} {apnp_vivienda_servicios}.{renglon}Se alimenta {apnp_no_comidas} al día de {apnp_cal_comidas} calidad. Tiene un {apnp_agua} consumo de agua. Su actividad física es {apnp_ejercicio}. Su orientación sexual referida es {apnp_sexual}. Viajes recientes: {apnp_viajes}. Convivencia con animales: {apnp_animales}. Exposición a biomasa, solventes, agroquímicos u otros: {apnp_exposicion}. Tatuajes o perforaciones: {apnp_tatuajes}. Vacunas: {apnp_vacunas}{renglon}{apnp_ago}{renglon}HOSPITALIZACIONES/ANEXIONES: {apnp_anexo_hosp}.'


        st.header('Interrogatorio por aparato y sistemas')
        ipas = st.text_area('', 'Preguntados y negados', key='IPAS')

    st.header('Consumo de sustancias')


    cons_sustancias = st.expander('Edad de inicio, patrón y fecha de último consumo')
    with cons_sustancias:

        col62, col63, col64, col65 = st.columns([0.25,0.25,0.25,0.25,])
        with col62:
            sust_tabaco = st.text_area('Tabaco:','Negadas',key='Tabaco')

        with col63:
            sust_alcohol = st.text_area('Alcohol:','Negadas',key='alcohol')

        with col64:
            sust_cannabis = st.text_area('Cannabis','Negadas',key='cannabis')

        with col65:
            sust_cocaina = st.text_area('Cocaína','Negadas',key='cocaina')


        col66, col67, col68, col69 = st.columns([0.25,0.25,0.25,0.25,])
        with col66:
            sust_cristal = st.text_area('Cristal:','Negadas',key='cristal')

        with col67:
            sust_solventes = st.text_area('Solventes:','Negadas',key='solventes')

        with col68:
            sust_alucinogenos = st.text_area('Alucinógenos:','Negadas',key='alucinogenos')

        with col69:
            sust_otras = st.text_area('Otras:','Negadas',key='otros')
        sustancias_merge = f'Tabaco: {sust_tabaco}.{renglon}Alcohol: {sust_alcohol}.{renglon}Cannabis: {sust_cannabis}.{renglon}Cocaína: {sust_cocaina}.{renglon}Cristal: {sust_cristal}.{renglon}Solventes: {sust_solventes}.{renglon}Alucinógenos: {sust_alucinogenos}.{renglon}Otras:{sust_otras}.'



    st.header('Resultados de estudios de laboratorio y gabinete')
    laboratoriales = st.expander('Estudios paraclínicos previos y solicitados')
    with laboratoriales:
        labs_prev = st.text_area('Estudios previos:','No se cuenta con paracínicos previos',key='prev_labs')

    st.header('Exploración física')
    EF = st.expander('Evaluación física del paciente')
    with EF:
        st.subheader('Estado general y apariencia')

        somatotipo, apariencia, hidratacion, color = st.columns([0.25, 0.25, 0.25, 0.25,]) 
        with somatotipo:
            ef_somatotipo = st.selectbox('Somatotipo:', ['mesomorfo','ectomorfo','endomorfo'], key='somatotipo')
        with apariencia:
            ef_apariencia = st.selectbox('Edo. general:', ['buen','regular','mal'], key='edo_general')
        with hidratacion:
            ef_hidratacion = st.selectbox('Hidratación:', ['buen','regular','mal'], key='hifratacion')
        with color:
            ef_color = st.selectbox('Coloración mucosa/tegumentos:', ['normal','con palidez','con tinte ictérico'], key='color')
        ef_merge = f'Paciente {ef_somatotipo} en {ef_apariencia} estado general y {ef_hidratacion} estado de hidratación.'
        st.subheader('Somatometría y signos vitales')
        col72, col73, col74, col75, col76, col77 = st.columns([0.15,0.15,0.15,0.15,0.15,0.15])
        with col72:
            peso = float(st.text_input('Peso (kg)','0.0',key=710))
            

        with col73:
            talla = float(st.text_input('Talla (cm)','0.0',key=712))


        with col74:
            imc = 0
            if peso >0 and talla > 0:
                talla_mts = talla/100
                imc = peso/(talla_mts*talla_mts)
                imc = "{:.2f}".format(round(imc, 2))

            if st.session_state.ta == '':
                # st.write('empty')

                st.session_state.ta = st.text_input('Presión arterial:',afx.rand_ta(),key=87)
            else:
                # st.write('not empty')
                st.session_state.ta  = st.text_input('Presión arterial:',st.session_state.ta,key=8747)
        with col75:
            fc = st.text_input('Frecuencia cardiaca:',f'{random.randint(68,88)}',key=88)
        with col76:
            fr = st.text_input('Frecuencia respiratoria:',f'{random.randint(17,21)}',key=89)
        with col77:
            temp = st.text_input('Temperatura:',f'{random.randint(362,369)/10}',key=90)

        st.subheader('Examen físico')
        alteraciones = '<p style="color:Red; font-size: 25px;">¿Alteraciones?</p>'
        st.markdown(alteraciones, unsafe_allow_html=True)

        col78, col79, col80 = st.columns([.33,.33,.33])
        with col78:
            alt_cabeza = st.text_input('Cabeza', key=1488)
            alt_abdomen = st.text_input('Abdomen', key=140)
        with col79 :
            alt_cuello = st.text_input('Cuello', key=1490)
            alt_extremidades_sup = st.text_input('Brazos', key=141)
        with col80:
            alt_cardio = st.text_input('Cardiopulmonar', key=1492)
            alt_extremidades_inf = st.text_input('Piernas', key=1504)

        col_genitales, col_otras = st.columns([0.5,0.5])
        with col_genitales:
            alt_genitales = st.text_input('Genitales', key=142)
        with col_otras:
            alt_otras = st.text_input('Otras', key=1478012)

        alteraciones_dict = {
        'Cabeza':  alt_cabeza,
        'Cuello':  alt_cuello,
        'Cardiopulmonar':  alt_cardio,
        'Abdomen': alt_abdomen,
        'Extremidades superiores':  alt_extremidades_sup,
        'Extremidades inferiores': alt_extremidades_inf,
        'Genitales':alt_genitales, 
        'Otras': alt_otras
        }
        
        alteraciones_ingreso = ''
        for key in alteraciones_dict:# range(len(alteraciones_dict)):
            if alteraciones_dict[key] !='':
                alteraciones_ingreso = f'{alteraciones_ingreso}{key}: {alteraciones_dict[key]}{renglon}'
                st.write(alteraciones_ingreso)
            else:
                alteraciones_ingreso = f'{alteraciones_ingreso}{key}: sin alteraciones{renglon}'

        ef_alteraciones = f'{alt_cabeza}{renglon}{alt_cuello}{renglon}{alt_cardio}{renglon}{alt_abdomen}{renglon}{alt_extremidades_sup}{renglon}{alt_extremidades_inf}{renglon}{alt_genitales}{renglon}{alt_otras}'
    st.write()
    st.header('Examen mental')
    em_options = ['Normal','Depresión', 'Ansiedad', 'Mania', 'Psicosis']

    EM = st.expander('Apariencia, actitud, psicomotricidad, ánimo, afecto, lenguaje, pensamiento, introspección, juicio y control de impulsos')
    with EM:
        em_template = st.selectbox('Seleccionar plantilla', em_options, key=1587)
        # st.write(f'{em.em(em_template,st.session_state.nombre.title())}')
        sel_em = em.em(em_template,st.session_state.nombre.title())
        examen_mental = st.text_area('Lista de plantillas de examen mental:',f'{str(sel_em)}',height=250)
        

    antecedentes_form_button = st.form_submit_button('Guardar historia clínica')
    if antecedentes_form_button:

        st.success('Se han guardado los cambios')

form_dx = st.form('form_dx')
with form_dx:

    dx_header, dsm = st.columns([0.5,0.5])
    with dx_header:
        st.header('Diagnósticos')

    DX = st.expander('Físicos, psiquiátricos, personalidad, psicosocial')
    with DX:
        cie10 = fx.cie_10()
        lista_problemas = st.multiselect('Seleccionar diagnósticos', cie10['code'])
        str_dx = ''
        for i in range(len(lista_problemas)):
            # st.write('',lista_probl emas[i],key=4561+i)
            str_dx = f'{str_dx}{i+1}. {lista_problemas[i]}{renglon}'
        dxs = st.text_area('Lista de diagnósticos:',str_dx,height=250)
    st.header('Guía de práctica clínica')
    guia = st.multiselect('',afx.stored_data('gpc'),)
    st.header('Pronóstico y clinimetría')
    exp_pron = st.expander('Establezca el pronóstico y clinemtrias que apliquen')
    with exp_pron:
        col_gaf, col_phq9, col_gad7, col_sadpersons, col_young, col_mdq, col_asrs = st.columns([0.14,0.14,0.14,0.14,0.14,0.14,0.14])
        with col_gaf:
            gaf = st.text_input('GAF')
        with col_phq9:
            phq9 = st.text_input('PHQ-9')
        with col_gad7:
            gad7 = st.text_input('GAD-7')
        with col_sadpersons:
            sadpersons = st.text_input('SADPERSONS')
        with col_young:
            young = st.text_input('YOUNG')
        with col_mdq:
            mdq = st.text_input('MDQ')
        with col_asrs:
            asrs = st.text_input('ASRS')
        otras_clini = st.text_input('Otras:')

        clinimetria = f'GAF:{afx.clin_merge(gaf)}PHQ-9{afx.clin_merge(phq9)}GAD-7:{afx.clin_merge(gad7)}SADPERSONS:{afx.clin_merge(sadpersons)}YOUNG:{afx.clin_merge(young)}MDQ:{afx.clin_merge(mdq)}OTRAS:{afx.clin_merge(otras_clini)}ASRS:{afx.clin_merge(asrs)}'

        pronostico = st.text_input('Pronóstico:','Reservado para la vida y la función')


    st.subheader('Tipo de manejo:')
    manejo = st.selectbox('', ['Ambulatorio','Hospitalario'])
    dx_button = st.form_submit_button('Guardar cambios')
    if dx_button:
        st.success('Se han gurdado los cambios')
    
#============================ TRATAMIENTO

form_tx = st.form('form_tx')
with form_tx:
    st.header('Tratamiento')
    expander_tx = st.expander('Plan para el paciente')
    with expander_tx:

        indicaciones = ''
        tx_med = ''

        try:
            lista_problemas = lista_problemas[0]
        except:
            lista_problemas = []

        main_dx = lista_problemas

        if manejo == 'Hospitalario':
            indicaciones = f'1. Ingreso a  con brazalete .{renglon}2. Condición: .{renglon}3. Diagnóstico: {lista_problemas}.{renglon}4. Pronóstico: {pronostico}.{renglon}5. MEDICAMENTOS:{renglon}-{renglon}6. Laboratoriales: VER SOLICITUD.{renglon}7. SVPT,CGE, Vigilancia continua y reporte de eventualidades.{renglon}8. Valoración por medicina general.{renglon}***** GRACIAS *****'
            tx = st.text_area('',f'{indicaciones}\n',height=200,key=3483169)
        else:
            tx = st.text_area('',f'{indicaciones}\n>>>> SE DAN DATOS DE ALARMA Y CITA ABIERTA A URGENCIAS <<<<',height=200,key=34839169)
        labs_nvos = st.text_area('Paraclínicos solicitados:','BH, QS, EGO, PFH, PERFIL TIROIDEO, PERFIL LIPÍDICO, PERFIL TOXICOLÓGICO, VIH, VDRL',key='nvos_labs')
        labs_merge = f'LABORATORIALES PREVIOS:{renglon}{labs_prev}.{renglon}{renglon}LABORATORIALES SOLICITADOS: {renglon}{labs_nvos}.'
        
        #============================ ANALISIS
    st.header('Análisis')
    exp_analisis = st.expander('Análisis del caso')
    with exp_analisis:
        analisis = st.text_area('',height=300, key=3290)
    tx_button = st.form_submit_button('Guarde cambios')
    if tx_button:
        st.success('Se han guardado los cambios')

aviso_alergias = ''
if app_alergias != '':
    aviso_alergias = f'Alergias: {app_alergias}'


data_dict = {
    "1 CURP":st.session_state.curp,
    "expediente":st.session_state.no_expediente,
    "fecha":st.session_state.date,
    "Nombres":st.session_state.nombre,
    "Primer apellido":st.session_state.apellido_paterno,
    "Segundo apellido":st.session_state.apellido_materno,
    "f_nacimiento":st.session_state.f_nacimiento,
    'dia': temp_date.strftime("%d"),
    'mes': temp_date.strftime("%m"),
    'año': temp_date.strftime("%y"),
    "Años":str(st.session_state.edad),
    "Hombre":hombre,
    "Mujer": mujer,
    'edad': int(st.session_state.edad),
    'edo_nac': st.session_state.edo_nac,
    'tipo_vialidad': st.session_state.tipo_vialidad,
    'nombre_vialidad': st.session_state.dom_vialidad,
    'no_ext': st.session_state.dom_no_ext,
    'no_int': st.session_state.dom_no_int,
    'cp': st.session_state.cp,
    'tipo_asentamiento': st.session_state.dom_tipo_asentamiento,
    'nombre_asentamiento': st.session_state.dom_asentamiento,
    'municipio': st.session_state.dom_cd,
    'edo_dom': st.session_state.dom_edo,
    'edo_civil': st.session_state.edo_civil,
    'religion': st.session_state.religion,
    'ocupacion': st.session_state.ocupacion,
    'institucion': st.session_state.inst_ref,
    'responsable': st.session_state.responsable_nombre,
    'responsable_tel': st.session_state.responsable_tel,
    'responsable_parentesco': st.session_state.responsable_parentesco,
    'mc': st.session_state.mc,
    'pa': pepa,
    'ahf': ahf_merge,
    'ap': app_merge,
    'apnp': apnp_merge,
    'ipas': ipas,
    'sustancias': sustancias_merge,
    'labs': labs_merge,
    'edo_general': ef_merge,
    'peso': f'{peso} kg',
    'talla': f'{talla} cm',
    'imc': imc,
    'ta': st.session_state.ta,
    'fc': f'{fc} lpm',
    'fr': f'{fr} rpm',
    'temp': f'{temp} °C',
    'cabeza_si': afx.radio_check(alt_cabeza),
    'cuello_si': afx.radio_check(alt_cuello),
    'abdomen_si': afx.radio_check(alt_abdomen),
    'cardio_si': afx.radio_check(alt_cardio),
    'brazos_si': afx.radio_check(alt_extremidades_sup),
    'piernas_si': afx.radio_check(alt_extremidades_inf),
    'genital_si': afx.radio_check(alt_genitales),
    'ef_alteraciones': ef_alteraciones,
    'em': examen_mental,
    'dx': dxs,
    'main_dx': main_dx,
    'tx': tx,
    'tx_med': f'{fx.medicine_extract(tx)}',
    'pronostico': pronostico,
    'clinimetria': clinimetria,
    'analisis': analisis,
    'nombre': nombre_completo,
    'expediente15': st.session_state.no_expediente,
    'fecha16': date,
    'ef': f'{ef_merge} | FC: {fc} lpm, FR: {fr} rpm, TA: {st.session_state.ta} mmHg, Temperatura: {temp} °C | Peso: {peso} kg, Talla: {talla} cm, IMC: {imc}\n',
    'presentacion': f'{nombre_completo}, {st.session_state.sexo} de {st.session_state.edad} años, nacido el {st.session_state.f_nacimiento}, oriundo y residente de {st.session_state.ciudades}, {st.session_state.edo_nac}. {st.session_state.edo_civil}, de religión {st.session_state.religion}, con estudios de {st.session_state.escolaridad} quien se desempeña como {st.session_state.ocupacion} y actualmente esta {st.session_state.trabajo}.',
    'ef23': alteraciones_ingreso,
    'alergia_1': aviso_alergias,
    'alergia_2': aviso_alergias,
    'alergia_3': aviso_alergias,
    'guia': guia,
    'sex_ref': st.session_state.sexo,


    }

afx.update_dict(data_dict,st.session_state.escolaridad)
afx.update_dict(data_dict,st.session_state.seg_social)
afx.update_dict(data_dict,st.session_state.referido)
afx.update_dict(data_dict,st.session_state.trabajo)
afx.update_dict(data_dict,st.session_state.etnia)

# Data de paciente para db mongo
# st.write(afx.id_gen())
paciente = {
    "id":afx.id_gen(),
    "expediente":st.session_state.no_expediente,
    "fecha":st.session_state.date,
    "nombres":st.session_state.nombre,
    "primer apellido":st.session_state.apellido_paterno,
    "segundo apellido":st.session_state.apellido_materno,
    'generales': 
    {
        "hombre":hombre,
        "mujer": mujer,
        'nacimiento': 
        {
            'fecha': st.session_state.f_nacimiento,
            'lugar': 
            {
                'ciudad': st.session_state.ciudades,
                'estado': st.session_state.edo_nac,
            },
        },
        'edad': int(st.session_state.edad),
        "1 CURP":st.session_state.curp,
        'Domicilio': 
        {
            'tipo_vialidad': st.session_state.tipo_vialidad,
            'nombre_vialidad': st.session_state.dom_vialidad,
            'no_ext': st.session_state.dom_no_ext,
            'no_int': st.session_state.dom_no_int,
            'cp': st.session_state.cp,
            'tipo_asentamiento': st.session_state.dom_tipo_asentamiento,
            'nombre_asentamiento': st.session_state.dom_asentamiento,
            'municipio': st.session_state.dom_cd,
            'edo_dom': st.session_state.dom_edo,
        },
        'telefono': tel,
        'generalidades': 
        {
            'escolaridad': st.session_state.escolaridad,
            'edo_civil': st.session_state.edo_civil,
            'religion': st.session_state.religion,
            'indigena': st.session_state.etnia,
            'ocupacion': st.session_state.ocupacion,
            'ss': st.session_state.seg_social,
            'referencia': st.session_state.referido,
            'empleo': 
            {
                'estado actual': st.session_state.trabajo,
                'ocupación': st.session_state.ocupacion,
            },
            'familiar': 
            {
                'responsable': st.session_state.responsable_nombre,
                'responsable_tel': st.session_state.responsable_tel,
                'responsable_parentesco': st.session_state.responsable_parentesco,  
            },

        },

    },
    'antecedentes': 
    {
        'ahf': 
        {
            'padre': 
            {
                'vivo': ahf_padre,
                'edad': ahf_edad_padre,
                'antecedentes': ahf_padre_ant,
            },
            'madre': 
            {
                'vivo': ahf_madre,
                'edad': ahf_edad_madre,
                'antecedentes': ahf_madre_ant,
            },
            'hermanos': ahf_hermanos,
            'hijos': ahf_hijos,
            'otros': ahf_otros,
            'psiquiátricos': ahf_psiquiatricos,
        },
        'app': 
        {
            'alergias': app_alergias,
            'cirugías': app_qx,
            'tce': app_tce,
            'transfusiones': app_transfusiones,
            'infecciosas': app_infecciosas,
            'crónicas': app_cronicas,
            'otras': app_otras,
            'medicamentos': app_medicamentos,
            'psiquiátricos': app_psiquiatricos,
            'anexiones/hospitalizaciones': apnp_anexo_hosp,
        },
        'apnp': 
        {
            'vivienda': 
            {
                'cohabita': apnp_vive_con,
                'tipo vivienda': apnp_tipo_vivienda,
                'medio': apnp_medio_vivienda,
                'servicios':apnp_vivienda_servicios,              
            },
            'hábitos': 
            {
                'no comidas': apnp_no_comidas,
                'alimentación': apnp_cal_comidas,
                'hidratación': apnp_agua,
                'higiene': apnp_baño,
                'ejercicio': apnp_ejercicio,
            },
            'exposiciones': 
            {
                'viajes': apnp_viajes,
                'zoonosis': apnp_animales,
                'particulas': apnp_exposicion,
                'tatuajes': apnp_tatuajes,                
            },
            'vacunas': apnp_vacunas,
            'sexuales': 
            {
                'preferencia': apnp_sexual,
                'ago': apnp_ago,
            },
        },
        'ipas': ipas,
        'sustancias': 
        {
            'tabaco': sust_tabaco,
            'alcohol': sust_alcohol ,
            'cannabis': sust_cannabis ,
            'cocaina': sust_cocaina ,
            'cristal': sust_cristal ,
            'solventes': sust_solventes ,
            'alucinogenos': sust_alucinogenos,
            'otras': sust_otras,
        },
    },
    'consultas': 
    [   
        {
            'fecha':st.session_state.date,
            'motivo': st.session_state.mc,
            'pepa': pepa,
            'ef': {
                'general': 
                {
                    'somatotipo': ef_somatotipo,                        
                    'edo general': ef_apariencia,                    
                    'hidratacion': ef_hidratacion,                    
                    'color': ef_color,                     
                },
                'somatometria': 
                {
                    'peso': peso,
                    'talla': talla,
                    'imc': imc,
                },
                'signos vitales': 
                {
                    'fc': fc,                    
                    'fr': fr,
                    'ta': st.session_state.ta,
                    'temp': temp,                    
                },
                'exploración': 
                {
                    'cabeza': alt_cabeza,
                    'cuello': alt_cuello,
                    'cardio': alt_cardio,
                    'abdomen': alt_abdomen,
                    'brazos': alt_extremidades_sup,
                    'piernas': alt_extremidades_inf,
                    'genital': alt_genitales,                    
                    'otras': alt_otras,                                       
                },
            },
            'em': examen_mental,
            'laboratoriales': 
            {
                'previos': labs_prev,
                'nuevos': labs_nvos,
            },
            'dx': dxs,
            'gpc': guia,            
            'pronostico': pronostico,
            'clinimetrias': 
            {
                'general': clinimetria,
                'PHQ-9': phq9,                
                'GAD-7': gad7,
                'SADPERSONS': sadpersons,
                'YOUNG': young,
                'MDQ': mdq,
                'otras': otras_clini,            
            },
            'manejo': manejo,
            'tx': tx,
            'analisis': analisis,
        },
    ]
}

sections_dict = {'Ficha de identificación':'#ficha-de-identificaci-n' ,
                'Motivo de consulta':"#motivo-de-consulta" ,
                'Padecimiento actual':"#padecimiento-actual" ,
                'Antecedentes heredofamiliares':"#antecedentes-heredo-familiares" ,
                'Antecedentes personales patológicos':"#antecedentes-personales-patol-gicos" ,
                'Antecedentes personales no patológicos':"#antecedentes-personales-no-patol-gicos" ,
                'Consumo de sustancias':"#consumo-de-sustancias" ,
                'Laboratoriales':"#resultados-de-estudios-de-laboratorio-y-gabinete" ,
                'Exploración física':"#exploraci-n-f-sica" ,
                'Examen mental':"#examen-mental" ,
                'Diagnósticos':"#diagn-sticos" ,
                'Pronóstico y clinimetría':"#pron-stico-y-clinimetr-a" ,
                'Escalas':"#visualizar-escalas" ,
                'Tratamiento':"#tratamiento" ,
                'Análisis':"#an-lisis"
                }


css_code = '<style>ul{\
  list-style-type: none;\
  margin: 0;\
  padding: 0;\
  overflow: hidden;\
  background-color: #333;}li {\
  float: left;}li a {\
  display: block;\
  color: white;\
  text-align: center;\
  padding: 14px 16px;\
  text-decoration: none;}li a:hover:not(.active) {\
  background-color: #111;}.active {\
  background-color: #04AA6D;}</style>'

gen_pdf = st.button('Generar archivo PDF')
if gen_pdf:

    fillpdfs.get_form_fields(pdf_template)
    temp_pdf = fillpdfs.write_fillable_pdf(pdf_template, f'{nombre_completo}.pdf', data_dict)
    # st.balloons()
    st.write(f'{nombre_completo}')

    hc_name = f'{nombre_completo}.pdf'
    local_file = f'{nombre_completo}.pdf'
    # response = afx.gdrive_up(local_file, hc_name)
    
    #========================= ACTIVAR CÓDIGO COMENTADO SI SE QUIERE REACTIVAR ALMACENAMIENTO DE ARCHIVOS EN AWS
    fx.s3_upload('salme',hc_name, f'salme/hc/{nombre_completo}.pdf')
    hc_pdf = fx.s3_download('salme', f'salme/hc/{nombre_completo}.pdf', hc_name)
    response = s3.generate_presigned_url('get_object',\
        Params={'Bucket': 'salme','Key': f'salme/hc/{nombre_completo}.pdf'},\
                ExpiresIn=240)
    client, pacientes = afx.mongo_intial(mongodb_uri)
    pacientes.insert_one(paciente)
    client.close()
    progress_bar = st.progress(0)
    for i in range(100):
        # Update progress bar.
        progress_bar.progress(i + 1)
        time.sleep(0.025)
    st.success(f'Se ha creado el archivo PDF: {nombre_completo}.pdf')
    fx.insert_css_url('download_button', response)

wake_lock_script = """
<script>
let wakeLock = null;
const requestWakeLock = async () => {
    try {
        wakeLock = await navigator.wakeLock.request('screen');
        console.log('Wake Lock activado');
    } catch (err) {
        console.log('Error al activar Wake Lock: ', err);
    }
};
requestWakeLock();
</script>
"""

# Inyectar el script en la app
html(wake_lock_script)
