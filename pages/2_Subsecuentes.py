
import streamlit as st
import pandas as pd
from datetime import date, datetime 
import pandas as pd
from fdfgen import forge_fdf
import os
from streamlit_timeline import timeline
import boto3
import functions as fx
import ex_mental as em
import random
import app_functions as afx
import pymongo
from pymongo import MongoClient
import re
from pathlib import Path
from streamlit.components.v1 import html
import os
from dotenv import load_dotenv

load_dotenv()
mongodb_uri = os.getenv("MONGODB_URI")

st.set_page_config(
    page_title=" Subsecuentes",
    page_icon="fav.png",  # EP: how did they find a symbol?
    layout="wide",
    initial_sidebar_state="collapsed",
)
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
    <script>
        window.addEventListener('scroll', function() {{
            const header = document.querySelector('.app-header');
            const app = document.querySelector('.stApp');
            if (window.scrollY > 50) {{
                header.classList.add('scrolled');
                app.classList.add('scrolled');
            }} else {{
                header.classList.remove('scrolled');
                app.classList.remove('scrolled');
            }}
        }});
    </script>
""", unsafe_allow_html=True)
st.markdown('<div class="title-container"><h1>Nota subsecuente</h1>', unsafe_allow_html=True)

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
        <!-- Botón Consulta Subsecuente -->
        <a href="Subsecuentes" class="icon-button" target="_self">
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


uri = mongodb_uri
client = MongoClient(uri)
db = client['expedinente_electronico'] #base de datos
pacientes = db['pacientes'] #colección

s3 = boto3.client('s3')
dsm_path = '/home/vazzam/Documentos/SALME_app/DSM_5.pdf'



path_folder = os.getcwd()+'/tmp/'
municipios = pd.read_csv('./data/mx.csv')
pdf_template = './data/HC_SALME_python.pdf'
renglon = '\n'
date = datetime.now()
date = date.strftime("%d/%m/%Y %H:%M")

if 'ta' not in st.session_state:
    st.session_state.ta = ''

# main_col1, main_col2 = st.columns([0.05,0.95])
# with main_col1:
#     main_img = st.image('brain.png',width=50)
# with main_col2:
#     "# Notas subsecuentes"

b_col4, b_col5, b_col6= st.columns([0.33,0.33,0.33])

with b_col4:
    st.session_state.bus_nombre = st.text_input('Nombre(s): ')
with b_col5:
    st.session_state.bus_apellido_paterno = st.text_input('Apellido paterno: ')
with b_col6:
    st.session_state.bus_apellido_materno = st.text_input('Apellido materno: ')

query_field = ['nombres', 'primer apellido', 'segundo apellido']
query_val = [st.session_state.bus_nombre, st.session_state.bus_apellido_paterno, st.session_state.bus_apellido_materno]
projection = { '_id': 1, "nombres": 1, 'primer apellido': 1, "segundo apellido": 1}

# criteria = {'nombres': {"$regex": query_val[0],"$options": "i"}, 'primer apellido': {"$regex":query_val[1], "$options": "i"},'segundo apellido': {"$regex":query_val[2], "$options": "i"}}
criteria = afx.data_format(query_field, query_val)
doc_id = None
if st.session_state.bus_nombre != '':
    if st.session_state.bus_nombre!= '':    
        paciente = afx.search_collection(pacientes, criteria, all_info=True)
        # st.write(paciente)
        if len(paciente) > 1:
        #===============================================================
        #FILTRADO POR FECHAS DE NACIEMIENTO EN CASO DE DOS PACIENTES DE MISMO NOMBRE
            nombres = []
            id_arr = []
            for i in range(len(paciente)):
                if i == 0:
                    usr = paciente[i]['nombres'] + ' ' + paciente[i]['primer apellido'] + ' ' + paciente[i]['segundo apellido']
                    nombres.append(paciente[i]['nombres'] + ' ' + paciente[i]['primer apellido'] + ' ' + paciente[i]['segundo apellido'])
                    # st.text(usr)
                    usr_id = paciente[i]['_id']
                    usr_dict = {usr:usr_id}
                else:
                # doc_field[i] = paciente[i]['nombres'] + ' ' + paciente[i]['segundo apellido'] + ' ' + paciente[i]['primer apellido']
                    nombres.append(paciente[i]['nombres'] + ' ' + paciente[i]['primer apellido'] + ' ' + paciente[i]['segundo apellido'])#paciente[i]['generales']['nacimiento']['fecha'])
                    id_arr.append(paciente[i]['_id'])
                    usr = paciente[i]['nombres'] + ' ' + paciente[i]['primer apellido'] + ' ' + paciente[i]['segundo apellido']
                    usr_id = paciente[i]['_id']
                    usr_dict[usr] = usr_id

            paciente_name = st.selectbox('Selecciona un paciente', nombres)
            index = nombres.index(paciente_name)
            paciente = [paciente[index]]
            # st.text(index)
            criteria['_id'] = usr_dict[paciente_name]
            doc_id = criteria['_id']
            # st.header(doc_id)
            # st.text('Este es el id del paciente seleccionado')
            # st.text(criteria['_id'])
        #================================================================
        elif len(paciente) == 1:
            doc_id = paciente[0]['_id']
            # st.text(paciente)

        # doc_field = afx.doc_field(db, 'pacientes', criteria, projection)
        # st.text(doc_field)

        # with st.sidebar:
        #     st.markdown(f'''**Fecha de primera consulta:** :orange[**{fecha}**]''')
        #     st.markdown(f'''**Edad:** :orange[**{edad}**] años  | |  **Lugar y fecha de nacimiento:** :orange[**{fnac}**] en :orange[**{cd_nac}**], :orange[**{edo_nac}**]''')

        #     escalas_expander = st.expander('Clinimetrías')
        #     with escalas_expander:
        #         escala_selected = st.selectbox('Selecciona la escala:',afx.stored_data('escalas'), key=342342)
        #         fx.displayPDF(f'./data/clinimetrias/{escala_selected}')
        if len(paciente) == 0:
            st.text('No se encontró registro del paciente')
            st.stop()

        current_patient = str(paciente[0])
        # st.text(paciente[0])

        st.subheader(paciente[0]['nombres'] + ' ' + paciente[0]['primer apellido'] + ' ' + paciente[0]['segundo apellido'])
        fecha = paciente[0]['fecha']
        fnac = paciente[0]['generales']['nacimiento']['fecha']
        edad = paciente[0]['generales']['edad']#, disabled=True)#st.text_input('Edad: ', '0'
        current_age = afx.calculate_age(datetime.strptime(paciente[0]['generales']['nacimiento']['fecha'], '%d%m%Y'))
        day = fnac[:2]
        month = fnac[2:4]
        year = fnac[4:]
        fnac = f"{day}/{month}/{year}"
        cd_nac= paciente[0]['generales']['nacimiento']['lugar']['ciudad']
        edo_nac = paciente[0]['generales']['nacimiento']['lugar']['estado']
        # st.markdown(f'''**Fecha de primera consulta:** :orange[**{fecha}**]''')
        # st.markdown(f'''**Edad:** :orange[**{edad}**] años  | |  **Lugar y fecha de nacimiento:** :orange[**{fnac}**] en :orange[**{cd_nac}**], :orange[**{edo_nac}**]''')
        identificacion = st.expander('FICHA IDENTIFICACÓN')
        consultas_previas = len(paciente[0]['consultas'])
        fecha_consulta_1 = paciente[0]['consultas'][0]['fecha']
        primera_consulta = f'{fecha_consulta_1}'

        last_note, total_notes = afx.last_note(consultas_previas, paciente, primera_consulta)
        with st.sidebar:
            st.subheader(paciente[0]['nombres'] + ' ' + paciente[0]['primer apellido'] + ' ' + paciente[0]['segundo apellido'])
            st.markdown(f'''**Edad:** :orange[**{current_age}**] años{renglon}{renglon}**Nacimiento:** :orange[**{fnac}**] en :orange[**{cd_nac}**], :orange[**{edo_nac}**]''')

            st.markdown(f'''**No. de consultas:** :orange[**{total_notes}**]''')
            st.markdown(f'''**Primera consulta:** :orange[**{fecha}**]''')
            st.markdown(f'''**Última consulta:** :orange[**{last_note}**]''')

            # escalas_expander = st.expander('Clinimetrías')
            # with escalas_expander:
            #     escala_selected = st.selectbox('Selecciona la escala:',afx.stored_data('escalas'), key=342342)
            #     fx.displayPDF(f'./data/clinimetrias/{escala_selected}')
        with identificacion:
            col1,col2,col3 = st.columns([0.6,0.2,0.2])
            
            with col1:
                st.session_state.curp = st.text_input("CURP: ", paciente[0]['generales']['1 CURP'])
            with col2:
                st.session_state.no_expediente = st.text_input("No. expediente: ",paciente[0]['expediente'])
            with col3:
                #format = 'DD MMM, YYYY'
                st.session_state.date = st.text_input("Fecha: ",paciente[0]['fecha'])
                #date_str = date.strftime("%d/%m/%Y")

            col4, col5, col6, col7, col7_2 = st.columns([0.2,0.10,0.20,0.25,0.25])
            with col4:
                # st.session_state.f_nacimiento = st.date_input("Fecha de nacimiento aaaa/mm/dd:",dt.datetime(1980,11,2),key='f_nacimiento_2')
                st.session_state.f_nacimiento = st.text_input('Fecha de nacimiento:',paciente[0]['generales']['nacimiento']['fecha'])
                # st.session_state.f_nacimiento = datetime.strptime(st.session_state.f_nacimiento, '%d/%m/%Y')
                # temp_date = st.session_state.f_nacimiento
                # st.session_state.f_nacimiento = st.session_state.f_nacimiento.strftime("%d%m%Y")
            with col5:
                st.session_state.edad = st.text_input('Edad:',paciente[0]['generales']['edad'], disabled=True)#st.text_input('Edad: ', '0')
            with col6:
                gen = ''
                if paciente[0]['generales']['hombre'] == "Yes":
                    gen = 'Hombre'
                else:
                    gen = 'Mujer'

                genero = ''
                st.session_state.sexo = st.text_input('Sexo:', gen)
                binary_sexo = 0
                if st.session_state.sexo == 'Hombre':
                    mujer = 'Off'
                    hombre = 'Yes'
                    genero = 'H'
                elif st.session_state.sexo == 'Mujer':
                    mujer = 'Yes'
                    hombre = 'Off'
                    genero = 'M'
                    ## Range selector

            with col7:
                st.session_state.ciudades = st.text_input('Ciudad de nacimiento: ',paciente[0]['generales']['nacimiento']['lugar']['ciudad'])

            with col7_2:
                st.session_state.edo_nac = st.text_input('Estado de nacimiento: ',paciente[0]['generales']['nacimiento']['lugar']['estado'])
                

            st.subheader('Domicilio')
            col12, col13, col14,col15, col16 = st.columns([0.20,0.35,0.10,0.10,0.15])

            with col12:
                st.session_state.tipo_vialidad = st.text_input('Tipo de vialidad: ', paciente[0]['generales']['Domicilio']['tipo_vialidad'])

            with col13:
                st.session_state.dom_vialidad = st.text_input('Nombre de vialidad:', paciente[0]['generales']['Domicilio']['nombre_vialidad'])

            with col14:
                st.session_state.dom_no_ext = st.text_input('Número exterior:', paciente[0]['generales']['Domicilio']['no_ext'])

            with col15:
                st.session_state.dom_no_int = st.text_input('Interior:', paciente[0]['generales']['Domicilio']['no_int'])

            with col16:
                st.session_state.cp = st.text_input('Código postal:',paciente[0]['generales']['Domicilio']['cp'])  

            col17, col18, col19,col20, col_tel = st.columns([0.20,0.25,0.20,0.20,0.15])

            with col17:
                st.session_state.dom_tipo_asentamiento = st.text_input('Tipo de asaentamiento: ', paciente[0]['generales']['Domicilio']['tipo_asentamiento'])

            with col18:
                st.session_state.dom_asentamiento = st.text_input('Nombre del asentamiento:', paciente[0]['generales']['Domicilio']['nombre_asentamiento'])

            with col19:
                st.session_state.dom_cd = st.text_input('Municipio:',paciente[0]['generales']['Domicilio']['municipio'])
                #st.session_state.dom_edo = st.text_input('Entidad federativa:',df['admin_name'].unique(), key=4412)

            with col20:
                st.session_state.dom_edo = st.text_input('Entidad federativa:',paciente[0]['generales']['Domicilio']['edo_dom'])
                #st.session_state.dom_cd = st.selectbox('Municipio:',df['city'].unique(), key=789271)
            with col_tel:
                tel = st.text_input('Teléfono:', paciente[0]['generales']['telefono'],key=87011)


            col21, col22, col23,col24, col25 = st.columns([0.15,0.15,0.20,0.30,0.15])

            with col21:

                st.session_state.escolaridad = st.text_input('Escolaridad: ', paciente[0]['generales']['generalidades']['escolaridad'])

            with col22:
                st.session_state.edo_civil = st.text_input('Estado civil: ', paciente[0]['generales']['generalidades']['edo_civil'])

            with col23:
                st.session_state.religion = st.text_input('Religión: ',paciente[0]['generales']['generalidades']['religion'])#,key='religion')
                #st.session_state.religion = st.text_input('Religión:')

            with col24:
                st.session_state.ocupacion = st.text_input('Ocupación habitual:',paciente[0]['generales']['generalidades']['empleo']['ocupación'])

            with col25:

                st.session_state.trabajo = st.text_input('Estatus laboral actual: ', paciente[0]['generales']['generalidades']['empleo']['estado actual'])

            col26, col27, col28,col29= st.columns([0.20,0.20,0.15,0.25])

            with col26:

                st.session_state.etnia = st.text_input('Etnia: ', paciente[0]['generales']['generalidades']['indigena'])

            with col27:

                st.session_state.seg_social = st.text_input('Afiliación a servicios de salud: ', paciente[0]['generales']['generalidades']['ss'])

            with col28:

                st.session_state.referido = st.text_input('Referencia:', paciente[0]['generales']['generalidades']['referencia'])

            with col29:
                st.session_state.inst_ref = st.text_input('Institución que refiere: ')

            col30, col31, col32 = st.columns([0.40,0.30,0.30])
            with col30:
                st.session_state.responsable_nombre = st.text_input('Nombre del responsable:', paciente[0]['generales']['generalidades']['familiar']['responsable'])

            with col31:
                st.session_state.responsable_tel = st.text_input('Teléfono:', paciente[0]['generales']['generalidades']['familiar']['responsable_tel'])

            with col32:
                st.session_state.responsable_parentesco = st.text_input('Parentesco:', paciente[0]['generales']['generalidades']['familiar']['responsable_parentesco'])




        #=====================================================================================================

        # st.header('Antecedentes')

        antecedentes_exp = st.expander('ANTECEDENTES')
        with antecedentes_exp:
        
            col33, edad_padres,col34 = st.columns([0.15,0.05,0.70])
            with col33:
                ahf_padre = paciente[0]['antecedentes']['ahf']['padre']['vivo']
                ahf_madre = paciente[0]['antecedentes']['ahf']['madre']['vivo']

            with edad_padres:
                ahf_edad_padre = paciente[0]['antecedentes']['ahf']['padre']['edad']
                ahf_edad_madre = paciente[0]['antecedentes']['ahf']['madre']['edad']
            with col34:
                ahf_padre_ant = paciente[0]['antecedentes']['ahf']['padre']['antecedentes']
                ahf_madre_ant = paciente[0]['antecedentes']['ahf']['madre']['antecedentes']
            
            col35, col36, col37 = st.columns([0.3,0.3,0.4])

            with col35:
                ahf_hermanos = paciente[0]['antecedentes']['ahf']['hermanos']
            with col36:
                ahf_hijos = paciente[0]['antecedentes']['ahf']['hijos']
            with col37:
                ahf_otros = paciente[0]['antecedentes']['ahf']['otros']

            ahf_psiquiatricos = paciente[0]['antecedentes']['ahf']['psiquiátricos']    
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

            app_alergias = paciente[0]['antecedentes']['app']['alergias']
            app_qx = paciente[0]['antecedentes']['app']['cirugías']
            app_tce = paciente[0]['antecedentes']['app']['tce']
            app_transfusiones = paciente[0]['antecedentes']['app']['transfusiones']
            app_infecciosas = paciente[0]['antecedentes']['app']['infecciosas']
            app_cronicas = paciente[0]['antecedentes']['app']['crónicas']
            app_otras = paciente[0]['antecedentes']['app']['otras']
            app_medicamentos = paciente[0]['antecedentes']['app']['medicamentos']
            app_psiquiatricos = paciente[0]['antecedentes']['app']['psiquiátricos']
            apnp_anexo_hosp = paciente[0]['antecedentes']['app']['anexiones/hospitalizaciones']
            app_merge = f'Alergias: {app_alergias},\nTransfusiones: {app_transfusiones},\nCirugías/Fracturas: {app_qx},\nTCE/Convulsiones: {app_tce},\nEnfermedades infecciosas: {app_infecciosas},\nEnfermedades crónico-degenerativas: {app_cronicas}{renglon}OTRAS: {app_otras}{renglon}MEDICAMENTOS: {app_medicamentos}{renglon}>>>>>>>ANTECEDENTES PSIQUIÁTRICOS:<<<<<<<{renglon}{app_psiquiatricos}.{renglon}Anexiones/Hosp: {apnp_anexo_hosp}'

            apnp_vive_con = paciente[0]['antecedentes']['apnp']['vivienda']['cohabita']
            apnp_tipo_vivienda = paciente[0]['antecedentes']['apnp']['vivienda']['tipo vivienda']
            apnp_medio_vivienda = paciente[0]['antecedentes']['apnp']['vivienda']['medio']
            apnp_vivienda_servicios = paciente[0]['antecedentes']['apnp']['vivienda']['servicios']
            apnp_no_comidas = paciente[0]['antecedentes']['apnp']['hábitos']['no comidas']
            apnp_cal_comidas = paciente[0]['antecedentes']['apnp']['hábitos']['alimentación']
            apnp_agua = paciente[0]['antecedentes']['apnp']['hábitos']['hidratación']
            apnp_ejercicio = paciente[0]['antecedentes']['apnp']['hábitos']['ejercicio']
            apnp_baño = paciente[0]['antecedentes']['apnp']['hábitos']['higiene']
            apnp_sexual = paciente[0]['antecedentes']['apnp']['sexuales']['preferencia']
            apnp_viajes = paciente[0]['antecedentes']['apnp']['exposiciones']['viajes']
            apnp_animales = paciente[0]['antecedentes']['apnp']['exposiciones']['zoonosis']
            apnp_exposicion = paciente[0]['antecedentes']['apnp']['exposiciones']['particulas']
            apnp_tatuajes = paciente[0]['antecedentes']['apnp']['exposiciones']['tatuajes']
            apnp_vacunas = paciente[0]['antecedentes']['apnp']['vacunas']
            apnp_ago = paciente[0]['antecedentes']['apnp']['sexuales']['ago']
            apnp_merge = f'Vive {apnp_vive_con}, en {apnp_tipo_vivienda} en un medio {apnp_medio_vivienda} {apnp_vivienda_servicios}.{renglon}Se alimenta {apnp_no_comidas} al día de {apnp_cal_comidas} calidad. Tiene un {apnp_agua} consumo de agua. Su actividad física es {apnp_ejercicio}. Su orientación sexual referida es {apnp_sexual}. Viajes recientes: {apnp_viajes}. Convivencia con animales: {apnp_animales}. Exposición a biomasa, solventes, agroquímicos u otros: {apnp_exposicion}. Tatuajes o perforaciones: {apnp_tatuajes}. Vacunas: {apnp_vacunas}{renglon}{apnp_ago}{renglon}HOSPITALIZACIONES/ANEXIONES: {apnp_anexo_hosp}.'    
        
            sust_tabaco = paciente[0]['antecedentes']['sustancias']['tabaco']
            sust_alcohol = paciente[0]['antecedentes']['sustancias']['alcohol']
            sust_cannabis = paciente[0]['antecedentes']['sustancias']['cannabis']
            sust_cocaina = paciente[0]['antecedentes']['sustancias']['cocaina']
            sust_cristal = paciente[0]['antecedentes']['sustancias']['cristal']
            sust_solventes = paciente[0]['antecedentes']['sustancias']['solventes']
            sust_alucinogenos = paciente[0]['antecedentes']['sustancias']['alucinogenos']
            sust_otras = paciente[0]['antecedentes']['sustancias']['otras']
            sustancias_merge = f'Tabaco: {sust_tabaco}.{renglon}Alcohol: {sust_alcohol}.{renglon}Cannabis: {sust_cannabis}.{renglon}Cocaína: {sust_cocaina}.'
            sustancias_merge2 = f'Cristal: {sust_cristal}.{renglon}Solventes: {sust_solventes}.{renglon}Alucinógenos: {sust_alucinogenos}.{renglon}Otras:{sust_otras}.'
            labs_prev = paciente[0]['antecedentes']['sustancias']['otras']
            
            fecha_consulta_1 = paciente[0]['consultas'][0]['fecha']
            ultima_consulta = paciente[0]['consultas'][-1]['fecha']
            mc = paciente[0]['consultas'][0]['motivo']
            pa = paciente[0]['consultas'][0]['pepa']
            ef_somatotipo = paciente[0]['consultas'][0]['ef']['general']['somatotipo']
            ef_apariencia = paciente[0]['consultas'][0]['ef']['general']['edo general']
            ef_hidratacion = paciente[0]['consultas'][0]['ef']['general']['hidratacion']
            ef_color = paciente[0]['consultas'][0]['ef']['general']['color']
            ef_merge = f'Paciente {ef_somatotipo} en {ef_apariencia} estado general y {ef_hidratacion} estado de hidratación.'

            peso = paciente[0]['consultas'][0]['ef']['somatometria']['peso']
            talla = paciente[0]['consultas'][0]['ef']['somatometria']['talla']
            imc = paciente[0]['consultas'][0]['ef']['somatometria']['imc']
            ta  = paciente[0]['consultas'][0]['ef']['signos vitales']['ta']
            fc = paciente[0]['consultas'][0]['ef']['signos vitales']['fc']
            fr = paciente[0]['consultas'][0]['ef']['signos vitales']['fr']
            temp = paciente[0]['consultas'][0]['ef']['signos vitales']['temp']
            somato_sv_merge = f'Peso: {peso}kg | Talla: {talla} cm | IMC: {imc} | FC: {fc} lpm | FR: {fr} rpm | TA: {ta} mmHg'

            alt_cabeza = paciente[0]['consultas'][0]['ef']['exploración']['cabeza']
            alt_abdomen = paciente[0]['consultas'][0]['ef']['exploración']['abdomen']
            alt_cuello = paciente[0]['consultas'][0]['ef']['exploración']['cuello']
            alt_extremidades_sup = paciente[0]['consultas'][0]['ef']['exploración']['brazos']
            alt_cardio = paciente[0]['consultas'][0]['ef']['exploración']['cardio']
            alt_extremidades_inf = paciente[0]['consultas'][0]['ef']['exploración']['piernas']
            alt_genitales = paciente[0]['consultas'][0]['ef']['exploración']['genital']
            alt_otras = paciente[0]['consultas'][0]['ef']['exploración']['otras']
            alteraciones_merge = f'CABEZA: {afx.check_ef(alt_cabeza)}, CUELLO: {afx.check_ef(alt_cuello)}, CARDIOPULMONAR: {afx.check_ef(alt_cardio)}, ABDOMEN: {afx.check_ef(alt_abdomen)}, BRAZOS: {afx.check_ef(alt_extremidades_sup)}, PIERNAS: {afx.check_ef(alt_extremidades_inf)}, GENITALES: {afx.check_ef(alt_genitales)}, OTRAS: {afx.check_ef(alt_otras)}'

            em = paciente[0]['consultas'][0]['em']

            labs_prev = paciente[0]['consultas'][0]['laboratoriales']['previos']
            labs_nvos = paciente[0]['consultas'][0]['laboratoriales']['nuevos']

            dx = paciente[0]['consultas'][0]['dx']
            pronostico = paciente[0]['consultas'][0]['pronostico']
            clinimetria = paciente[0]['consultas'][0]['clinimetrias']['general']
            manejo = paciente[0]['consultas'][0]['manejo']
            tx = paciente[0]['consultas'][0]['tx']
            analisis = paciente[0]['consultas'][0]['analisis']




            ant_col_1, ant_col_2 = st.columns([0.5,0.5])
            
            with ant_col_1:
                st.text_area('ANTECEDENTES HEREDOFAMILIARES',ahf_merge, height=220)
                st.text_area('ANTECEDENTES PERSONALES NO PATOLÓGICOS', apnp_merge, height=220)
            with ant_col_2:
                st.text_area('ANTECEDENTES PERSONALES PATOLÓGICOS', app_merge, height=220)
                st.text_area('IPAS', paciente[0]['antecedentes']['ipas'], height=220)

            ant_col_1b, ant_col_2b = st.columns([0.5,0.5])
            with ant_col_1b:
                st.text_area('SUSTANCIAS', sustancias_merge, height=120)
            with ant_col_2b:
                st.text_area('', sustancias_merge2, height=120)


            consultas = len(paciente[0]['consultas'])
            primera_consulta = f'{fecha_consulta_1}{renglon}{renglon}MC: {mc}{renglon}{renglon}PA: {pa}{renglon}{renglon}EXAMEN MENTAL{renglon}{renglon}{em}{renglon}{renglon}EXPLORACIÓN FÍSICA{renglon}{renglon}{somato_sv_merge}{renglon}{renglon}{ef_merge}{renglon}{alteraciones_merge}{renglon}{renglon}LABORATORIALES{renglon}- Previos: {labs_prev}{renglon}- Solicitados: {labs_nvos}{renglon}{renglon}DIAGNÓSTICO(S){renglon}{renglon}{dx}{renglon}{renglon}PRONÓSTICO: {pronostico}{renglon}{renglon}{clinimetria}{renglon}{renglon}ANÁLISIS{renglon}{renglon}{analisis}TRATAMIENTO{renglon}{renglon}{tx}'
            

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


    #===========================================================================================
    # BÚSQUEDA Y SELECCIÓN DE CONSULTAS PREVIAS
    #===========================================================================================

    consultas_previas = len(paciente[0]['consultas'])
    # st.write(consultas_previas)
    notes_no = afx.note_show(consultas_previas, paciente, primera_consulta)
    st.subheader('Historial del paciente')
    generar_resumen = st.button('Generar Resumen', icon='🤖')
    if generar_resumen:
            summary, graph_code = afx.resumen_paciente(current_patient)
            # st.text(summary)
            st.markdown(summary)
            html(graph_code, height=500, scrolling=True)
    st.markdown('---')
    st.subheader('Pregunta sobre tu paciente')
    chat_exp = st.text_input('')
    preguntar = st.button('Preguntar', icon='🤔')
    if preguntar:
        respuesta_chat = afx.chat_expediente(chat_exp, current_patient)
        st.markdown(respuesta_chat)

        # st.markdown(respuesta_chat, unsafe_allow_html=True)
    transcripcion = afx.audio_recorder_transcriber('subsecuente')
    nota_evol = st.form('nota_evol')
    with nota_evol:

        evol_header, dsm = st.columns([0.5,0.5])
        with evol_header:
            st.header('Nota de evolución')    

    #=====================================================================================================
    #FORMULARIO DE NUEVA NOTA
    #=====================================================================================================
        re_tx = re.sub(r'>.+?<<<<', '', tx)
        evol_date = st.text_input('Fecha:', date)
        nota_dx_pres = ''
        nota_tx_pres = ''
        temp_dx = dx.replace('\n', ' ')        
        temp_re_tx = re_tx.replace('\n', ' ') 
        edad_pres = afx.calculate_age(datetime.strptime(paciente[0]['generales']['nacimiento']['fecha'], '%d%m%Y'))   
        if consultas_previas >= 2:
            nota_dx_pres = paciente[0]['consultas'][-1]['dx'].replace('\n', ' ')
            nota_tx_pres = paciente[0]['consultas'][-1]['plan'].replace('\n', ' ')

        if consultas_previas >= 2:
            presentacion = st.text_area('Presentación', f'{gen} de {edad_pres} años con diagnóstico previo de {nota_dx_pres} con {consultas_previas} consulta(s) previa(s) siendo la última el pasado {ultima_consulta} y esquema de tratamiento: {nota_tx_pres}')
        else:
            presentacion = st.text_area('Presentación', f'{gen} de {edad_pres} años con diagnóstico previo de {temp_dx} con {consultas_previas} consulta(s) previa(s) siendo la última el pasado {fecha_consulta_1} y esquema de tratamiento: {temp_re_tx}')
        subjetivo = st.text_area('Subjetivo', transcripcion)
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

        objetivo = st.text_area('Objetivo')
        st.markdown('Clinimetrias')
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
        if consultas_previas >= 2:
            # st.text('IGUAL O MÁS DE 3 CONSULTAS')
            dx = st.text_area('Diagnóstico', nota_dx_pres)
        else:
            dx = st.text_area('Diagnóstico', dx)
        analisis = st.text_area('Análisis')
        st.subheader(f'Alergias: {app_alergias}')  
        if consultas_previas >= 2:      
            plan = st.text_area('Plan', nota_tx_pres)
        else:
            plan = st.text_area('Plan', re_tx)

        dx_button = st.form_submit_button('Guardar nota')
        if dx_button:
            nva_nota = {'fecha': date,
                        'presentacion':presentacion,
                        'subjetivo': subjetivo,
                        'objetivo': objetivo,
                        'peso': peso,
                        'talla': talla,
                        'fc': fc,
                        'fr': fr,
                        'ta': ta,
                        'temp': temp,
                        'clinimetrias':
                            {
                                'phq9': phq9,
                                'gad7': gad7,
                                'sadpersons': sadpersons,
                                'young': young,
                                'mdq': mdq,
                                'asrs': asrs,
                                'otras_clini': otras_clini,
                            },
                        'dx': dx,
                        'analisis': analisis,
                        'plan': plan
                        }
            pacientes.update_one({"_id": doc_id},{"$push": {"consultas": nva_nota}})
            st.success('Se han guardado los cambios')




    aviso_alergias = ''
    if app_alergias != '':
        aviso_alergias = f'Alergias: {app_alergias}'

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