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
import functions as fx
import random
import urllib.request

s3 = boto3.client('s3')
dsm_path = '/home/vazzam/Documentos/SALME_app/DSM_5.pdf'

st.set_page_config(
    page_title=" Historia Clínica",
    page_icon="fav.png",  # EP: how did they find a symbol?
    layout="wide",
    initial_sidebar_state="collapsed",
)

escalas = ['RASS.pdf','bush y francis.pdf', 'simpson angus.pdf', 'gad7.pdf', 'sad persons.pdf', 'young.pdf', 'fab.pdf', 'assist.pdf', 'dimensional.pdf', 'psp.pdf', 'yesavage.pdf', 'phq9.pdf', 'Escala dimensional de psicosis.pdf', 'moca.pdf', 'moriski-8.pdf', 'mdq.pdf', 'calgary.pdf', 'eeag.pdf', 'madrs.pdf']
gpc = [
'SSA-222-09 Diagnostico y tratamiento de la esquizofrenia', 'IMSS 170-09 Diagnostico y tratamiento del trastorno bipolar',
'IMSS-392-10 Diagnostico y tratamiento del trastorno de ansiedad en el adulto', 'APA- Practice guideline for the treatment of patients with borderline personality disorder',
'IMSS-161-09 Diagnostico y tratamiento del trastorno depresivo en el adulto', 'IMSS-528-12 Diagnostico y manejo de los trastornos del espectro autista',
'IMSS-515-11 Diagnostico y manejo del estres post traumatico', 'SS-343-16 Diagnostico y tratamiento del consumo de marihuana en adultos en primer y segundo nivel de atención',
'SS-023-08 Prevención, detección y consejeria en adicciones para adolescentes y adultos.', 'IMSS-385-10 Diagnostico y tratamiento de los trastornos del Sueño',
'SS-666-14 Prevención, diagnóstico y manejo de la depresión prenatal', 'SS-294-10 Detección y atención de violencia de pareja en adulto',
'ss-210-09 Diagnostico y tratamiento de epilepsia en el adulto'    
]

path_folder = os.getcwd()+'/tmp/'
municipios = pd.read_csv('./data/mx.csv')
input_pdf_name = './data/HC_SALME_python.pdf'
renglon = '\n'
date = datetime.now()
date = date.strftime("%d/%m/%Y %H:%M")

st.markdown(
"""
<style>
[data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
width: 600px;
}
[data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
width: 600px;
margin-left: -600px;
}
</style>
""",
unsafe_allow_html=True
)

with st.sidebar:
    dsm_spec = st.expander('Especificadores DSM')
    with dsm_spec:
        fx.displayPDF(f'./data/especificadores.pdf')

    dsm_pdf_1 = st.expander('Criterios DSM 5 Tomo 1')
    with dsm_pdf_1:
        fx.displayPDF(f'./data/DSM_5_1.pdf')

    dsm_pdf_2 = st.expander('Criterios DSM 5 Tomo 2')
    with dsm_pdf_2:
        fx.displayPDF(f'./data/DSM_5_2.pdf')

    escalas_expander = st.expander('Clinimetrías')
    with escalas_expander:
        escala_selected = st.selectbox('Selecciona la escala:',escalas, key=342342)
        fx.displayPDF(f'./data/clinimetrias/{escala_selected}')

# st.sidebar.write(f'<p style="border-color: #FF4B4B;border-bottom-style: solid;border-radius: 4px;\
# border: 2px solid none;padding: 0px 10px 0px; margin: -75px; color: white; font-size: 45px; \
# text-style: bold;text-align:center; text-style: bold;">Apartados</p>', unsafe_allow_html=True)\

# st.sidebar.write('<html><head><style>\
# ul {list-style-type: none;\
#   margin: -5px;\
#   padding: -10px;\
#   overflow: hidden;\
#   background-color: rgb(19, 23, 32);\
# }\
# li {float: center;}li a {display: block;\
#   font-size:15px;\
#   text-align: left;\
#   padding: 5px 5px 5px 10px;\
#   text-decoration: none;\
# }li a:hover:not(.active) {\
#   background-color: #FF4B4B;\
#   text-decoration:none\
# }.active {\
#   background-color: #04AA6D;\
# }\
# </style>\
# </head>\
# <body><ul>\
# <li><a href="#ficha-de-identificaci-n"><b style=color:white;>Ficha de identificación</b></a></li>\
# <li><a href="#motivo-de-consulta"><b style=color:white;>Motivo de consulta</b></a></li>\
# <li><a href="#padecimiento-actual"><b style=color:white;>Padecimiento actual</b></a></li>\
# <li><a href="#antecedentes-heredo-familiares"><b style=color:white;>Antecedentes heredofamiliares</b></a></li>\
# <li><a href="#antecedentes-personales-patol-gicos"><b style=color:white;>Antecedentes personales patológicos</b></a></li>\
# <li><a href="#antecedentes-personales-no-patol-gicos"><b style=color:white;>Antecedentes personales no patológicos</b></a></li>\
# <li><a href="#consumo-de-sustancias"><b style=color:white;>Consumo de sustancias</b></a></li>\
# <li><a href="#resultados-de-estudios-de-laboratorio-y-gabinete"><b style=color:white;>Laboratoriales</b></a></li>\
# <li><a href="#exploraci-n-f-sica"><b style=color:white;>Exploración física</b></a></li>\
# <li><a href="#examen-mental"><b style=color:white;>Examen mental</b></a></li>\
# <li><a href="#diagn-sticos"><b style=color:white;>Diagnósticos</b></a></li>\
# <li><a href="#pron-stico-y-clinimetr-a"><b style=color:white;>Pronóstico y clinimetría</b></a></li>\
# <li><a href="#visualizar-escalas"><b style=color:orange;>Escalas</b></a></li>\
# <li><a href="#tratamiento"><b style=color:white;>Tratamiento</b></a></li>\
# <li><a href="#an-lisis"><b style=color:white;>Análisis</b></a></li>\
# </ul></body>\
# </html>',unsafe_allow_html=True)

main_col1, main_col2 = st.columns([0.05,0.95])
with main_col1:
    main_img = st.image('brain.png',width=50)
with main_col2:
    "# Historia clínica de psiquiatría"

main_form = st.form('main_form')
with main_form:
    st.header("Ficha de identificación")
    col1,col2,col3 = st.columns([0.6,0.2,0.2])

    with col1:
        curp = st.text_input("CURP: ")
    with col2:
        no_expediente = st.text_input("No. expediente: ")
    with col3:
        #format = 'DD MMM, YYYY'
        date = st.text_input("Fecha: ",date)
        #date_str = date.strftime("%d/%m/%Y")

    col4, col5, col6, col7 = st.columns([0.3,0.25,0.25,0.2])
    with col4:
        nombre = st.text_input('Nombre(s): ')
    with col5:
        apellido_paterno = st.text_input('Apellido paterno: ')
    with col6:
        apellido_materno = st.text_input('Apellido materno: ')
        nombre_completo = f'{nombre} {apellido_paterno} {apellido_materno}'

    with col7:
        sexo = st.radio('Sexo:', ['Hombre','Mujer'])
        binary_sexo = 0
        if sexo == 'Hombre':
            mujer = 'Off'
            hombre = 'Yes'
        else:
            mujer = 'Yes'
            hombre = 'Off'
            ## Range selector


    col8, col9, col10,col11 = st.columns([0.40,0.15,0.25,0.15])

    with col8:

        f_nacimiento = st.date_input("Fecha de nacimiento aaaa/mm/dd:",dt.datetime(1980,11,2),key='f_nacimiento')
        f_nacimiento = f_nacimiento.strftime("%d%m%Y")



    with col9:
        edad = st.text_input('Edad:',f'{fx.calculateAge(f_nacimiento)+1}')#st.text_input('Edad: ', '0')
    with col10:
        df = municipios
        edo_nac = st.selectbox('Edo. Nacimiento:', df['admin_name'].unique(), key=44)

    with col11:
        ciudades = st.selectbox('Ciudad de nacimiento: ',df['city'].unique())

#     #===================== DOMICILSemaforización y tiempo de espera estimado *
# Rojo (emergencia) tiempo de espera INMEDIATO
# Naranja (urgencia calificada) tiempo de espera 0 A 30 MIN
# Amarillo (urgencia no calificada) tiempo de espera 30 A 60 MIN

    st.subheader('Domicilio')
    col12, col13, col14,col15, col16 = st.columns([0.20,0.35,0.10,0.10,0.15])

    with col12:
        tipo_vialidad = st.selectbox('Tipo de vialidad: ', ['Calle', 'Andador', 'Avenida', 'Privada', 'Carretera', 'Brecha','Circuito'])

    with col13:
        dom_vialidad = st.text_input('Nombre de vialidad:')

    with col14:
        dom_no_ext = st.text_input('Número exterior:')

    with col15:
        dom_no_int = st.text_input('Interior:')

    with col16:
        cp = st.text_input('Código postal:')  

    col17, col18, col19,col20= st.columns([0.20,0.30,0.25,0.25])

    with col17:
        dom_tipo_asentamiento = st.selectbox('Tipo de asaentamiento: ', ['Colonia', 'Fraccionamiento', 'Coto', 'Privada', 'Ranchería', 'Comunidad', 'Pueblo','Villa'])

    with col18:
        dom_asentamiento = st.text_input('Nombre del asentamiento:')

    with col19:
        dom_edo = st.selectbox('Entidad federativa:', df['admin_name'].unique(), key=4412)

    with col20:
        dom_cd = st.selectbox('Municipio:',df['city'].unique(), key=789271)


    col21, col22, col23,col24, col25 = st.columns([0.15,0.15,0.20,0.30,0.15])

    with col21:


        escolaridad_arr = ['Ninguna', 'Primaria', 'Secundaria', 'Bachillerato', 'Licenciatura', 'Posgrado']
        escolaridad = st.selectbox('Escolaridad: ', escolaridad_arr)


    with col22:
        edo_civil = st.selectbox('Estado civil: ', ['Soltero', 'Casado', 'Unión libre','Divorciado', 'Viudo', 'Separado'])

    with col23:
        religion = st.text_input('Religión:')

    with col24:
        ocupacion = st.text_input('Ocupación habitual:')

    with col25:
        trabajo_arr = ['Empleado', 'Desempleado', 'Subempleado']

        trabajo = st.selectbox('Estatus laboral actual: ', trabajo_arr)

    col26, col27, col28,col29= st.columns([0.20,0.30,0.05,0.25])

    with col26:
        indigena_options = ['indigena_no','indigena_si']
        indigena_arr = ['No', 'Sí']
        indigena = st.selectbox('¿Se considera indígena?: ', indigena_arr)

    with col27:
        ss_arr = ['NINGUNA', 
            'IMSS', 'ISSSTE', 'SEDENA', 'SEMAR', 'IMSS-PROSPERA', 'PEMEX', 
            'SEGURO POPULAR', 'OTRA', 'SE IGNORA', 'NO ESPECIFICADO']
        seg_social = st.selectbox('Afiliación a servicios de salud: ', ss_arr)

    with col28:
        referido_options = ['referido_no','referido_si']
        referido_arr = ['No', 'Sí']
        referido = st.radio('Referido:', referido_arr)

    with col29:
        inst_ref = st.text_input('Institución que refiere: ')

    col30, col31, col32 = st.columns([0.40,0.30,0.30])
    with col30:
        responsable_nombre = st.text_input('Nombre del responsable:')

    with col31:
        responsable_tel = st.text_input('Teléfono:')

    with col32:
        responsable_parentesco = st.text_input('Parentesco:')


    st.header('Motivo de consulta')
    mc_consulta = st.expander('La razón por la que acuden a valoración')
    with mc_consulta:   
        mc = st.text_area('',height=120)  

    st.header('Padecimiento actual')
    padecimiento = st.expander('Inicio, curso, tendencia, desencadenantes, agravantes, síntomas clave, síntomas actuales')
    with padecimiento:
        pepa = st.text_area('',height=200)

    st.header('Antecedentes Heredo Familiares')

    AHF = st.expander('Llenar antecedentes personales heredofamiliares')
    with AHF:

        col33, edad_padres,col34 = st.columns([0.15,0.05,0.70])
        with col33:
            ahf_padre = st.selectbox('Padre', ['vivo','finado','desconocido'])
            ahf_madre = st.selectbox('Madre', ['viva','finada','desconocida'])

        with edad_padres:
            ahf_edad_padre = st.text_input('edad')
            ahf_edad_madre = st.text_input('edad',key='edad_padre')
        with col34:
            ahf_padre_ant = st.text_input('Antecedentes: ', 'sin antecedentes de relevancia',key='ant_padre')
            ahf_madre_ant = st.text_input('Antecedentes: ', 'sin antecedentes de relevancia',key='ant_madre')
        
        col35, col36, col37 = st.columns([0.3,0.3,0.4])

        with col35:
            ahf_hermanos = st.text_area('Hermanos: ','Antecedentes patológicos negados',height=50,key='Hermanos')
        with col36:
            ahf_hijos = st.text_area('Hijos:','Antecedentes patológicos negados',height=50,key='Hijos')
        with col37:
            ahf_otros = st.text_area('Otros:','Antecedentes patológicos negados',height=50,key='Otros')



        st.subheader('Antecedentes Familiares Psiquiátricos')
        ahf_psiquiatricos = st.text_area('','Negados',key='fam_psiq', height=30)
        padre_merge = f'Padre {ahf_padre} de {ahf_edad_padre} años: {ahf_padre_ant}'
        madre_merge = f'Madre {ahf_madre} de {ahf_edad_madre} años: {ahf_madre_ant}'
        padres_merge = f'{padre_merge}. {renglon}{madre_merge}'
        ahf_merge = f'{padres_merge}. {renglon}Hermanos: {ahf_hermanos}.{renglon}Hijos: {ahf_hijos}.\
                    {renglon}Otros:{ahf_otros}.{renglon}ANTECEDENTES FAMILIARES PSIQUIÁTRICOS:{renglon}{ahf_psiquiatricos}.'

    st.header('Antecedentes Personales Patológicos')
    APP = st.expander('Llenar antecedentes personales Patológicos')
    with APP:
        col38, col39, col40 = st.columns([0.33,0.33,0.33])
        with col38:
            app_alergias = st.text_area('Alergias','Negadas', height=20, key='Alergias')
        with col39:
            app_qx = st.text_area('Cirugías/Fracturas','Negadas', height=20, key='qx_fx')
        with col40:
            app_tce = st.text_area('TCE/Convulsiones','Negados', height=20, key='tec_conv')

        col41,  col42, col43 = st.columns([0.33,0.33,0.33])
        with col41:
            app_transfusiones = st.text_area('Transfusiones','Negadas',height=20, key='Transusiones')
        with col42:
            app_infecciosas = st.text_area('Enfermedades Infecciosas','Negadas',height=20, key='Infecciosas')
        with col43:
            app_cronicas = st.text_area('Enfermedades Crónico-degenerativas','Negadas',height=20, key='cronicas')

        col44, col45 = st.columns([0.5,0.5])

        with col44:
            app_otras = st.text_area('Otras','Negadas',height=20,key='Otras')

        with col45:
            app_medicamentos = st.text_area('Medicamentos','Negados',height=20,key='Medicamentos')


        st.subheader('Antecedentes Personales Psiquiátricos')
        app_psiquiatricos = st.text_area('','Negados') 
        
        app_merge = f'Alergias: {app_alergias}, Transfusiones: {app_transfusiones}, Cirugías/Fracturas: {app_qx}, TCE/Convulsiones: {app_tce}, Enfermedades infecciosas: {app_infecciosas}, Enfermedades crónico-degenerativas: {app_cronicas}{renglon}OTRAS: {app_otras}{renglon}MEDICAMENTOS: {app_medicamentos}{renglon}>>>>>>>ANTECEDENTES PSIQUIÁTRICOS:<<<<<<<{renglon}{app_psiquiatricos}.'


    st.header('Antecedentes Personales No Patológicos')

    APNP = st.expander('Llenar antecedentes personales no Patológicos')
    with APNP:
        col46, col47, col48, col49 = st.columns([0.2,0.2,0.2,0.2])
        with col46:
            apnp_vive_con = st.text_input('¿Con quién vive?','con ',key='vive_con')
        with col47:
            apnp_tipo_vivienda = st.selectbox('Tipo de vivienda:',['casa','departamento','calle'],key='tipo_vivienda')
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
            apnp_agua = st.selectbox('consumo de agua:',['adecuado','pobre','elevado'],key='agua')

        with col53:
            apnp_ejercicio = st.selectbox('actividad física',['nula','2-3 días/semana','>3 días/semana'],key='ejercicio')

        with col54:
            apnp_baño = st.selectbox('baño y cambio de ropa',['diario','1-2 veces por semana','3 veces por semana', 'nunca'],key='ejercicio')

        col55, col56, col57, col58 = st.columns([0.25,0.25,0.25,0.25])
        with col55:
            apnp_sexual = st.selectbox('Orientación sexual:',['heterosexual','homosexual','pansexual','asexual', 'no referida'],key='orientacion_sex')

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
            apnp_vacunas = st.text_input('Inumizaciones:','Completas para la edad',key='vacunas')

        with col61:
            apnp_ago = st.text_input('AGO:','No aplica',key='ago')
            if apnp_ago == 'No aplica':
                apnp_ago = ''
            else:
                apnp_ago = f'AGO: {apnp_ago}'

        apnp_anexo_hosp = st.text_input('Anexiones u hospitalizaciones:',"Negadas",key='hospi')
        apnp_merge = f'Vive {apnp_vive_con}, en {apnp_tipo_vivienda} en un medio {apnp_medio_vivienda} {apnp_vivienda_servicios}.{renglon}Se alimenta {apnp_no_comidas} al día de {apnp_cal_comidas} calidad. Tiene un {apnp_agua} consumo de agua. Su actividad física es {apnp_ejercicio}. Su orientación sexual referida es {apnp_sexual}. Viajes recientes: {apnp_viajes}. Convivencia con animales: {apnp_animales}. Exposición a biomasa, solventes, agroquímicos u otros: {apnp_exposicion}. Tatuajes o perforaciones: {apnp_tatuajes}. Vacunas: {apnp_vacunas}{renglon}{apnp_ago}{renglon}HOSPITALIZACIONES/ANEXIONES: {apnp_anexo_hosp}.'


        st.header('Interrogatorio por aparato y sistemas')
        ipas = st.text_input('', 'Preguntados y negados')

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

        col70, col71 = st.columns([0.5,0.5])
        with col70:
            labs_prev = st.text_area('Estudios previos:','No se cuenta con paracínicos previos',key='prev_labs')
        with col71:
            labs_nvos = st.text_area('Paraclínicos solicitados:','BH, QS, EGO, PFH, PERFIL TIROIDEO, PERFIL LIPÍDICO, PERFIL TOXICOLÓGICO, VIH, VDRL',key='nvos_labs')
        labs_merge = f'LABORATORIALES PREVIOS:{renglon}{labs_prev}.{renglon}{renglon}LABORATORIALES SOLICITADOS: {renglon}{labs_nvos}.'


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
            ef_hidratación = st.selectbox('Hidratación:', ['buen','regular','mal'], key='hifratacion')
        with color:
            ef_color = st.selectbox('Coloración mucosa/tegumentos:', ['normal','con palidez','con tinte ictérico'], key='color')
        ef_merge = f'Paciente {ef_somatotipo} en {ef_apariencia} estado general y {ef_hidratación} estado de hidratación.'
        st.subheader('Somatometría y signos vitales')
        col72, col73, col74, col75, col76, col77 = st.columns([0.15,0.15,0.15,0.15,0.15,0.15])
        with col72:
            peso = st.number_input('Peso (kg)',key=710)
            

        with col73:
            talla = st.number_input('Talla (cm)',key=712)


        with col74:
            imc = 0
            if peso >0 and talla > 0:
                talla_mts = talla/100
                imc = peso/(talla_mts*talla_mts)
                imc = "{:.2f}".format(round(imc, 2))
            ta = st.text_input('Presión arterial:',f'{random.randint(100,130)}/{random.randint(66,78)}',key=87)
        with col75:
            fc = st.text_input('Frecuencia cardiaca:',f'{random.randint(68,88)}',key=88)
        with col76:
            fr = st.text_input('Frecuencia respiratoria:',f'{random.randint(17,21)}',key=89)
        with col77:
            temp = st.text_input('Temperatura:',f'{random.randint(362,369)/10}',key=90)

        st.subheader('Examen físico')
        alteraciones = '<p style="color:Red; font-size: 25px;">¿Alteraciones?</p>'
        st.markdown(alteraciones, unsafe_allow_html=True)

        col78, col79, col80, col81, col82, col83  = st.columns([0.05,0.2,0.05,0.2,0.05,0.2])
        
        alteraciones_arr = ['No', 'Sí']

        cabeza_options = ['cabeza_no','cabeza_si']
        cuello_options = ['cuello_no','cuello_si']   
        cardio_options = ['cardio_no','cardio_si']        
        abdomen_options = ['abdomen_no','abdomen_si']        
        brazos_options = ['brazos_no','brazos_si']       
        piernas_options = ['piernas_no','piernas_si']        
        genital_options = ['genital_no','genital_si']        



        with col78:
            #st.write('¿Alteraciones?')
            cabeza = st.radio('Cabeza: ', alteraciones_arr, key=1487)
            abdomen = st.radio('Abdomen:',alteraciones_arr, key=554)
            #st.write(cabeza)

        
        with col79:
            alt_cabeza = st.text_input('', key=1488)
            alt_abdomen = st.text_input('', key=140)

        with col80:
            cuello = st.radio('Cuello: ', alteraciones_arr, key=1489)
            extremidades_sup = st.radio('Extremidades superiores:',alteraciones_arr, key=555)   
        with col81:
            alt_cuello = st.text_input('', key=1490)
            alt_extremidades_sup = st.text_input('', key=141)

        with col82:
            cardio = st.radio('Cardiopulmonar: ', alteraciones_arr, key=1491)
            extremidades_inf = st.radio('Extremidades inferiores:',alteraciones_arr, key=7555)   
        with col83:
            alt_cardio = st.text_input('', key=1492)
            alt_extremidades_inf = st.text_input('', key=1504)
    
        col_genitales, genitales_input = st.columns([0.05,0.5])
        with col_genitales:
            genitales = st.radio('Genitales:',alteraciones_arr, key=556) 
        with genitales_input:    
            alt_genitales = st.text_input('', key=142)
        

        alteraciones_dict = {
        'Cabeza':  alt_cabeza,
        'Cuello':  alt_cuello,
        'Cardiopulmonar':  alt_cardio,
        'Abdomen': alt_abdomen,
        'Extremidades superiores':  alt_extremidades_sup,
        'Extremidades inferiores': alt_extremidades_inf,
        'Genitales':alt_genitales, 
        }
        
        alteraciones_ingreso = ''
        for key in alteraciones_dict:# range(len(alteraciones_dict)):
            if alteraciones_dict[key] !='':
                alteraciones_ingreso = f'{alteraciones_ingreso}{key}: {alteraciones_dict[key]}{renglon}'
                st.write(alteraciones_ingreso)
            else:
                alteraciones_ingreso = f'{alteraciones_ingreso}{key}: sin alteraciones{renglon}'

        ef_alteraciones = f'{alt_cabeza}{renglon}{alt_cuello}{renglon}{alt_cardio}{renglon}{alt_abdomen}{renglon}{alt_extremidades_sup}{renglon}{alt_extremidades_inf}{renglon}{alt_genitales}'
    st.write()
    st.header('Examen mental')
    em_template = f'Encuentro a {nombre.title()} con buena higiene y aliño, edad aparente y real concordantes, vestimenta acorde al clima, alerta, orientado, cooperador y sin alteraciones\
        psicomotrices y/o condcuta alucinada. Se refiere de ánimo "mas o menos (sic {nombre.title()}), afecto eutímico. Discurso espontáneo, fluído,\
        coherente, congruente, de velocidad y volumen noramles con una latencia de respsuuesta conservada. Pensamiento lineal sin expresar ideas delirantes,\
        suicidas, homicidas o alteraciones de la sensopercepción. Parcial introspección, juicio dentro del marco de la realidad y buen control de impulsos.'

    EM = st.expander('Apariencia, actitud, psicomotricidad, ánimo, afecto, lenguaje, pensamiento, introspección, juicio y control de impulsos')
    with EM:
        examen_mental = st.text_area('', key='ex_mental')

    main_button = st.form_submit_button('Guardar historia clínica')
    if main_button:
        st.success('Se han guardado los cambios')

# dsm_form = st.form('dsm_form')
# with dsm_form:
#     # dsm_expander = st.expander('Consultar DSM 5')
#     # with dsm_expander:
#     image_dsm = st.image('dsm_portada.jpg', width=100)
#     dsm_button = st.form_submit_button('Consultar DSM 5')    
#     if dsm_button:
#         st.download_button('Descargar', 'data/DSM_5.pdf')

form_dx = st.form('form_dx')
with form_dx:

    dx_header, dsm = st.columns([0.5,0.5])
    with dx_header:
        st.header('Diagnósticos')
    # with dsm:
    #     DSM_cat = st.expander('DSM')
    #     with DSM_cat:
    #         fx.displayPDF(f'./data/DSM_5.pdf')



    DX = st.expander('Físicos, psiquiátricos, personalidad, psicosocial')
    with DX:
        cie10 = fx.cie_10()
        lista_problemas = st.multiselect('Seleccionar diagnósticos', cie10['code'])
        str_dx = ''
        for i in range(len(lista_problemas)):
            # st.write('',lista_problemas[i],key=4561+i)
            str_dx = f'{str_dx}{i+1}. {lista_problemas[i]}{renglon}'
        dxs = st.text_area('Lista de diagnósticos:',str_dx,height=250)
    st.header('Guía de práctica clínica')
    guia = st.multiselect('',gpc,)
    st.header('Pronóstico y clinimetría')
    exp_pron = st.expander('Establezca el pronóstico y clinemtrias que apliquen')
    with exp_pron:
        pronostico = st.text_input('Pronóstico:','Reservado para la vida y la función')
        clinimetria = st.text_area('Clinimetría:')

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

        try:
            lista_problemas = lista_problemas[0]
        except:
            lista_problemas = []


        if manejo == 'Hospitalario':
            indicaciones = f'1. Ingreso a  con brazalete .{renglon}2. Condición: .{renglon}3. Diagnóstico: {lista_problemas}.{renglon}4. Pronóstico: {pronostico}.{renglon}5. MEDICAMENTOS:{renglon}-{renglon}6. Laboratoriales: {labs_nvos}.{renglon}7. SVPT,CGE, Vigilancia continua y reporte de eventualidades.{renglon}8. valoración por medicina general.'
        tx = st.text_area('',indicaciones,height=200,key=3483169)
        #============================ ANALISIS
    st.header('Análisis')
    exp_analisis = st.expander('Análisis del caso')
    with exp_analisis:
        analisis = st.text_area('',height=300, key=3290)
    tx_button = st.form_submit_button('Guarde cambios')
    if tx_button:
        st.success('Se han guardado los cambios')

pdf_file_name = input_pdf_name
def fill_form(data_dict, pdf_file_name, out_file_name=None):
    if out_file_name is None:
        out_file_name = pdf_file_name

    pdf_reader = PdfFileReader(pdf_file_name)
    pdf_writer = PdfFileWriter()
    st.write(data_dict)


    for field in pdf_reader.getFormTextFields().items():
        key = field[0]
        value = data_dict.get(key)
        st.write(key,' ',str(value))
        st.write(type(key),' ',type(value))
        st.write(key+' '+str(value))
        if value:
            pdf_writer.updatePageFormFieldValues(pdf_reader.getPage(0), {key: value})

    with open(out_file_name, 'wb') as out:
        pdf_writer.write(out)

#==========================================================
ANNOT_KEY = '/Annots'
ANNOT_FIELD_KEY = '/T'
ANNOT_VAL_KEY = '/V'
ANNOT_RECT_KEY = '/Rect'
SUBTYPE_KEY = '/Subtype'
WIDGET_SUBTYPE_KEY = '/Widget'

pdf_template = input_pdf_name
pdf_output = "outputHC.pdf"
def fill_pdf(input_pdf_path, output_pdf_path, data_dict):
    template_pdf = pdfrw.PdfReader(input_pdf_path)
    for page in template_pdf.pages:
        annotations = page[ANNOT_KEY]
        for annotation in annotations:
            if annotation[SUBTYPE_KEY] == WIDGET_SUBTYPE_KEY:
                if annotation[ANNOT_FIELD_KEY]:
                    key = annotation[ANNOT_FIELD_KEY][1:-1]
                    if key in data_dict.keys():
                        if type(data_dict[key]) == bool:
                            if data_dict[key] == True:
                                annotation.update(pdfrw.PdfDict(
                                    AS=pdfrw.PdfName('Yes')))
                        else:
                            annotation.update(
                                pdfrw.PdfDict(V='{}'.format(data_dict[key]))
                            )
                            annotation.update(pdfrw.PdfDict(AP=''))
    template_pdf.Root.AcroForm.update(pdfrw.PdfDict(NeedAppearances=pdfrw.PdfObject('true')))  # NEW
    pdfrw.PdfWriter().write(output_pdf_path, template_pdf)
    st.success('SE CREÓ PDF')

fillpdfs.get_form_fields(pdf_template)

aviso_alergias = ''

if app_alergias != '':
    aviso_alergias = f'Alergias: {app_alergias}'


data_dict = {
    "1 CURP":curp,
    "expediente":no_expediente,
    "fecha":date,
    "Nombres":nombre,
    "Primer apellido":apellido_paterno,
    "Segundo apellido":apellido_materno,
    "f_nacimiento":f_nacimiento,
    "Años":str(edad),
    "Hombre":hombre,
    "Mujer": mujer,
    'edad': int(edad),
    'edo_nac': edo_nac,
    'tipo_vialidad': tipo_vialidad,
    'nombre_vialidad': dom_vialidad,
    'no_ext': dom_no_ext,
    'no_int': dom_no_int,
    'cp': cp,
    'tipo_asentamiento': dom_tipo_asentamiento,
    'nombre_asentamiento': dom_asentamiento,
    'municipio': dom_cd,
    'edo_dom': dom_edo,
    'Ninguna': 'Off',
    'Primaria': 'Off',
    'Secundaria': 'Off',
    'Bachillerato': 'Off',
    'Licenciatura': 'Off',
    'Posgrado': 'Off',
    'edo_civil': edo_civil,
    'religion': religion,
    'indigena_si': 'Off',
    'indigena_no': 'Off',
    'ocupacion': ocupacion,
    'NINGUNA': 'Off',
    'IMSS': 'Off',
    'ISSSTE': 'Off',
    'SEDENA': 'Off',
    'SEMAR': 'Off',
    'IMSS-PROSPERA': 'Off',
    'PEMEX': 'Off',
    'SEGURO POPULAR': 'Off',
    'OTRA': 'Off',
    'SE IGNORA': 'Off',
    'NO ESPECIFICADO': 'Off',
    'referido_si': 'Off',
    'referido_no': 'Off',
    'Empleado': 'Off',
    'Desempleado': 'Off',
    'Subempleado': 'Off',
    'institucion': inst_ref,
    'responsable': responsable_nombre,
    'responsable_tel': responsable_tel,
    'responsable_parentesco': responsable_parentesco,
    'mc': mc,
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
    'ta': ta,
    'fc': f'{fc} lpm',
    'fr': f'{fr} rpm',
    'temp': f'{temp} °C',
    'cabeza_si': 'Off',
    'cuello_si': 'Off',
    'abdomen_si': 'Off',
    'cardio_si': 'Off',
    'abdomen_si': 'Off',
    'brazos_si': 'Off',
    'piernas_si': 'Off',
    'genital_si': 'Off',
    'cabeza_no': 'Off',
    'cuello_no': 'Off',
    'cardio_no': 'Off',
    'abdomen_no': 'Off',
    'brazos_no': 'Off',
    'piernas_no': 'Off',
    'genital_no': 'Off',
    'ef_alteraciones': ef_alteraciones,
    'em': examen_mental,
    'dx': dxs,
    'tx': tx,
    'pronostico': pronostico,
    'clinimetria': clinimetria,
    'analisis': analisis,
    'nombre': nombre_completo,
    'expediente15': no_expediente,
    'fecha16': date,
    'ef': f'{ef_merge} | FC: {fc} lpm, FR: {fr} rpm, TA: {ta} mmHg, Temperatura: {temp} °C | Peso: {peso} kg, Talla: {talla} cm, IMC: {imc}',
    'presentacion': f'{nombre_completo}, {sexo} de {edad} años, nacido el {f_nacimiento}, oriundo y residente de {ciudades}, {edo_nac}. {edo_civil}, de religión {religion}, con estudios de {escolaridad} quien se desempeña como {ocupacion} y actualmente esta {trabajo}.',
    'mc17': mc,
    'pa18': pepa,
    'ahf19': ahf_merge,
    'apnp20': apnp_merge,
    'app_2': app_merge,
    'ipas21': ipas,
    'sustancias22': sustancias_merge,
    'ef23': alteraciones_ingreso,
    'em23': examen_mental,
    'analisis24': analisis,
    'labs25': labs_merge,
    'dx26': str_dx,
    'clinimetria27': clinimetria,
    'pronostico28': pronostico,
    'tx29': tx,
    'alergia_1': aviso_alergias,
    'alergia_2': aviso_alergias,
    'alergia_3': aviso_alergias,
    'guia': guia,


    }

#================== ESCOLARIDAD OPCIONES
for i in range(len(escolaridad_arr)):
    if escolaridad == escolaridad_arr[i]:
        data_dict[escolaridad_arr[i]] = 'Yes'
#================== INDIGENA OPCIONES
for j in range(len(indigena_arr)):
    if indigena == indigena_arr[j]:
        data_dict[indigena_options[j]] = 'Yes'
#==================== SS OPCIONES
for i in range(len(ss_arr)):
    if seg_social == ss_arr[i]:
        data_dict[ss_arr[i]] = 'Yes'
#==================== REFERIDO OPCIONES
for j in range(len(referido_arr)):
    if referido == referido_arr[j]:
        data_dict[referido_options[j]] = 'Yes'
#===================== TRABAJO OPCIONES
for i in range(len(trabajo_arr)):
    if trabajo == trabajo_arr[i]:
        data_dict[trabajo_arr[i]] = 'Yes'

#===========================================
#       EXPLORACIÓN FÍSICA
#===========================================
for j in range(len(alteraciones_arr)):
    if cabeza == alteraciones_arr[j]:
        data_dict[cabeza_options[j]] = 'Yes'
#===========================================
for j in range(len(alteraciones_arr)):
    if cuello == alteraciones_arr[j]:
        data_dict[cuello_options[j]] = 'Yes'
#===========================================
for j in range(len(alteraciones_arr)):
    if cardio == alteraciones_arr[j]:
        data_dict[cardio_options[j]] = 'Yes'      
#===========================================
for j in range(len(alteraciones_arr)):
    if abdomen == alteraciones_arr[j]:
        data_dict[abdomen_options[j]] = 'Yes'
#===========================================
for j in range(len(alteraciones_arr)):
    if extremidades_sup == alteraciones_arr[j]:
        data_dict[brazos_options[j]] = 'Yes'
#===========================================
for j in range(len(alteraciones_arr)):
    if extremidades_inf == alteraciones_arr[j]:
        data_dict[piernas_options[j]] = 'Yes'
#===========================================
for j in range(len(alteraciones_arr)):
    if genitales == alteraciones_arr[j]:
        data_dict[genital_options[j]] = 'Yes'

st.subheader('Visualizar escalas')

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

# escala_expander = st.expander('Visor de escalas')
# with escala_expander:

#     escala_selected = st.selectbox('Selecciona la escala:',escalas, key=342342)
#     fx.displayPDF(f'./data/clinimetrias/{escala_selected}')



gen_pdf = st.button('Generar archivo PDF')
if gen_pdf:
    temp_pdf = fillpdfs.write_fillable_pdf(pdf_template, f'{nombre_completo}.pdf', data_dict)
    # st.balloons()
    st.write(f'{nombre_completo}')

    hc_name = f'{nombre_completo}.pdf'
    fx.s3_upload('salme',hc_name, f'salme/hc/{nombre_completo}.pdf')
    hc_pdf = fx.s3_download('salme', f'salme/hc/{nombre_completo}.pdf', hc_name)
    response = s3.generate_presigned_url('get_object',\
        Params={'Bucket': 'salme','Key': f'salme/hc/{nombre_completo}.pdf'},\
                ExpiresIn=240)
    progress_bar = st.progress(0)
    for i in range(100):
        # Update progress bar.
        progress_bar.progress(i + 1)
        time.sleep(0.05)
    st.success(f'Se ha creado el archivo PDF: {nombre_completo}.pdf')
    fx.insert_css_url('download_button', response)

    # st.write(f'{fx.cie_11}')


