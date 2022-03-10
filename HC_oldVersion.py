
import streamlit as st
import pandas as pd
import numpy as np
import time
#from cie.cie10 import CIECodes
import datetime as dt
from datetime import date
import pandas as pd
from dateutil.relativedelta import relativedelta # to add days or years
from fdfgen import forge_fdf
import PyPDF2
from PyPDF2 import PdfFileReader, PdfFileWriter
#from PyPDF2 import PdfFileWriter
import pdfrw
from fillpdf import fillpdfs
import base64
st.set_page_config(layout="wide")



@st.cache(persist=True, suppress_st_warning=True)
def age_calc(birthDate):
    today = date.today()
    age = today.year - birthDate.year - ((today.month, today.day) < (birthDate.month, birthDate.day))
    return age

def load_mexico_cities():
    return pd.read_csv('./mx.csv')

def municipios():
    df = load_mexico_cities()
    estados = st.multiselect('Estados', df['admin_name'].unique(), key=0)
    ciudades = df[df['admin_name'].isin(estados)]['city']
    ciudades = st.selectbox('',ciudades)


def f_nacimiento():
    format = 'DD MMM, YYYY'  # format output
    start_date = dt.date(year=1920,month=1,day=1)-relativedelta(years=2)  #  I need some range in the past
    end_date = dt.datetime.now().date()
    max_days = end_date-start_date
    slider = st.slider('Fecha de nacimiento: ', min_value=start_date, value=end_date, max_value=end_date,format=format)
    fecha = slider
    return(fecha)
# @st.cache(persist=True)

def displayPDF(file):
    # Opening file from file path
    with open(file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')

    # Embedding PDF in HTML
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1400" type="application/pdf"></iframe>'
    # Displaying File
    st.markdown(pdf_display, unsafe_allow_html=True)

def displayPDF_2(file):
    # Opening file from file path
    with open(file, "rb") as f:
        base64_pdf = f.read()

    # Embedding PDF in HTML
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1400" type="application/pdf"></iframe>'
    # Displaying File
    st.markdown(pdf_display, unsafe_allow_html=True)



input_pdf_name = 'HC_SALME_python.pdf'

#cie = CIECodes()
renglon = '\n'

cie10 = pd.read_csv('cie-10.csv', usecols=[0,6], header=0, names=['code','diagnostic'])
cie10['code'] = cie10['diagnostic'] + ' CIE-10 ('+ cie10['code']+')'

#estados = ['Aguascalientes','Baja California','Baja California Sur','Campeche','Chiapas','Chihuahua','Coahuila de Zaragoza','Colima','Ciudad de México','Durango','Guanajuato','Guerrero','Hidalgo','Jalisco','Estado de Mexico','Michoacan de Ocampo','Morelos','Nayarit','Nuevo Leon','Oaxaca','Puebla','Queretaro de Arteaga','Quintana Roo','San Luis Potosi','Sinaloa','Sonora','Tabasco','Tamaulipas','Tlaxcala','Veracruz de Ignacio de la Llave','Yucatan','Zacatecas']

"# Historia clínica de psiquiatría"
st.header("Ficha de identificación")
ficha = '<p style="color:Blue; font-size: 25px;">Ficha de identificación?</p>'


col1,col2,col3 = st.columns([0.6,0.2,0.2])

with col1:
    curp = st.text_input("CURP: ")
with col2:
    no_expediente = st.text_input("No. expediente: ")
with col3:
    format = 'DD MMM, YYYY'
    date = st.date_input("Fecha: ")
    date_str = date.strftime("%d/%m/%Y")

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
    f_nacimiento = f_nacimiento()
with col9:
    edad = st.number_input('Edad: ', age_calc(f_nacimiento))
with col10:
    df = load_mexico_cities()
    edo_nac = st.multiselect('Edo. Nacimiento:', df['admin_name'].unique(), key=44)

with col11:
    ciudades = df[df['admin_name'].isin(edo_nac)]['city']
    ciudades = st.selectbox('Cd. de nacimiento:',ciudades,key='cds')

#===================== DOMICILIO 

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
    dom_tipo_asentamiento = st.selectbox('Tipo de asaentamiento: ', ['Colonia', 'Coto', 'Privada', 'Ranchería', 'Comunidad', 'Pueblo','Villa'])

with col18:
    dom_asentamiento = st.text_input('Nombre del asentamiento:')

with col19:
    dom_edo = st.multiselect('Estado:', df['admin_name'].unique(), key=741)

with col20:
    dom_cd = df[df['admin_name'].isin(dom_edo)]['city']
    dom_cd = st.selectbox('Municipio:',dom_cd,key='domcds')


col21, col22, col23,col24, col25 = st.columns([0.15,0.15,0.20,0.30,0.15])

with col21:


    escolaridad_arr = ['Ninguna', 'Primaria', 'Secundaria', 'Bachillerato', 'Licenciatura', 'Posgrado']
    escolaridad = st.selectbox('Escolaridad: ', escolaridad_arr)
    # for i in range(len(escolaridad_arr)):
    #     st.write(escolaridad_arr[i])

    #     if escolaridad == escolaridad_arr[i]:
    #         st.write('AQUIIIIIIIIIIIIIIII')
    #         st.write('Coincide - ',escolaridad_arr[i])
    #         esc_dict[escolaridad_arr[i]] = 'Yes'
    #         st.write(esc_dict[escolaridad_arr[i]])


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
form_mc_consulta = st.form('form_mo_consulta')
with form_mc_consulta:
    mc_consulta = st.expander('La razón por la que acuden a valoración')
    with mc_consulta:   
        mc = st.text_area('',height=120)  
    mc_button = st.form_submit_button('Guarde cambios')
    if mc_button == True:
        st.success('Se han guardado los cambios') 

st.header('Padecimiento actual')
form_padecimiento_actual = st.form('form_padecimiento_actual')
with form_padecimiento_actual:
    padecimiento = st.expander('Inicio, curso, tendencia, desencadenantes, agravantes, síntomas clave, síntomas actuales')
    with padecimiento:
        pepa = st.text_area('',height=200)
    padecimiento_button = st.form_submit_button('Guarde cambios')
    if padecimiento_button == True:
        st.success('Se han guardado los cambios')

st.header('Antecedentes Heredo Familiares')

form_AHF = st.form('form_AHF')
with form_AHF:
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
            ahf_hermanos = st.text_area('Hermanos: ','Negados',height=50,key='Hermanos')
        with col36:
            ahf_hijos = st.text_area('Hijos:','Negados',height=50,key='Hijos')
        with col37:
            ahf_otros = st.text_area('Otros:','Negados',height=50,key='Otros')



        st.subheader('Antecedentes Familiares Psiquiátricos')
        ahf_psiquiatricos = st.text_area('','Negados',key='fam_psiq', height=30)
        padre_merge = f'Padre {ahf_padre} de {ahf_edad_padre} años: {ahf_padre_ant}'
        madre_merge = f'Madre {ahf_madre} de {ahf_edad_madre} años: {ahf_madre_ant}'
        padres_merge = f'{padre_merge}. {renglon}{madre_merge}'
        ahf_merge = f'{padres_merge}. {renglon}Hermanos: {ahf_hermanos}.{renglon}Hijos: {ahf_hijos}.\
                    {renglon}Otros:{ahf_otros}.{renglon}ANTECEDENTES FAMILIARES PSIQUIÁTRICOS:{renglon}{ahf_psiquiatricos}.'


    AHF_button = st.form_submit_button('Guarde cambios')
    if AHF_button == True:
        st.success('Se han guardado los cambios')

st.header('Antecedentes Personales Patológicos')
form_APP = st.form('form_APP')
with form_APP:

    APP = st.expander('Llenar antecedentes personales Patológicos')
    with APP:
        col38, col39, col40 = st.columns([0.33,0.33,0.33])
        with col38:
            app_alergias = st.text_area('Alergias','Negados', height=20, key='Alergias')
        with col39:
            app_qx = st.text_area('Cirugías/Fracturas','Negados', height=20, key='qx_fx')
        with col40:
            app_tce = st.text_area('TCE/Convulsiones','Negados', height=20, key='tec_conv')

        col41,  col42, col43 = st.columns([0.33,0.33,0.33])
        with col41:
            app_transfusiones = st.text_area('Transfusiones','Negados',height=20, key='Transusiones')
        with col42:
            app_infecciosas = st.text_area('Enfermedades Infecciosas','Negados',height=20, key='Infecciosas')
        with col43:
            app_cronicas = st.text_area('Enfermedades Crónico-degenerativas','Negados',height=20, key='cronicas')

        col44, col45 = st.columns([0.5,0.5])

        with col44:
            app_otras = st.text_area('Otras','Negados',height=20,key='Otras')

        with col45:
            app_medicamentos = st.text_area('Medicamentos','Negados',height=20,key='Medicamentos')


        st.subheader('Antecedentes Personales Psiquiátricos')
        app_psiquiatricos = st.text_area('','Negados') 
        
        app_merge = f'Alergias: {app_alergias}, Transfusiones: {app_transfusiones}, Cirugías/Fracturas: {app_qx}, TCE/Convulsiones: {app_tce}, Enfermedades infecciosas: {app_infecciosas}, Enfermedades crónico-degenerativas: {app_cronicas}{renglon}OTRAS: {app_otras}{renglon}MEDICAMENTOS: {app_medicamentos}{renglon}>>>>>>>ANTECEDENTES PSIQUIÁTRICOS:<<<<<<<{renglon}{app_psiquiatricos}.'


    APP_button = st.form_submit_button('Guarde cambios')
    if APP_button == True:
        st.success('Se han guardado los cambios')


st.header('Antecedentes Personales No Patológicos')
form_APNP = st.form('form_APNP')
with form_APNP:
    APNP = st.expander('Llenar antecedentes personales no Patológicos')
    with APNP:
        col46, col47, col48, col49 = st.columns([0.2,0.2,0.2,0.2])
        with col46:
            apnp_vive_con = st.selectbox('Vive con: ',['solo','con padre(s)','con conyuge',
                        'con hermano(s)','con hijo(s)'],key='vive_con')
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
            apnp_baño = st.selectbox('baño y cambio de ropa',['diario','1-2 veces por semana','3 veces por semana'],key='ejercicio')

        col55, col56, col57, col58 = st.columns([0.25,0.25,0.25,0.25])
        with col55:
            apnp_sexual = st.selectbox('Orientación sexual:',['heterosexual','homosexual','pansexual','asexual'],key='orientacion_sex')

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
    APNP_button = st.form_submit_button('Guarde cambios')
    if APNP_button == True:
        st.success('Se han guardado los cambios')


st.header('Consumo de sustancias')

form_sustancias = st.form('form_sustancias')
with form_sustancias:
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

    sust_button = st.form_submit_button('Guarde cambios')
    if sust_button == True:
        st.success('Se han guardado los cambios')


st.header('Resultados de estudios de laboratorio y gabinete')

form_labs = st.form('form_labs')
with form_labs:

    laboratoriales = st.expander('Estudios paraclínicos previos y solicitados')

    with laboratoriales:

        col70, col71 = st.columns([0.5,0.5])
        with col70:
            labs_prev = st.text_area('Estudios previos:','No se cuenta con paracínicos previos',key='prev_labs')
        with col71:
            labs_nvos = st.text_area('Paraclínicos solicitados:','BH, QS, EGO, PFH, PERFIL TIROIDEO, PERFIL LIPÍDICO, PERFIL TOXICOLÓGICO, VIH, VDRL',key='nvos_labs')
        labs_merge = f'LABORATORIALES PREVIOS:{renglon}{labs_prev}.{renglon}{renglon}LABORATORIALES SOLICITADOS: {renglon}{labs_nvos}.'
    labs_button = st.form_submit_button('Guarde cambios')
    if labs_button == True:
        st.success('Se han guardado los cambios')


st.header('Exploración física')
form_ef = st.form('form_ef')
with form_ef:
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
            ta = st.text_input('Presión arterial:',key=87)
        with col75:
            fc = st.text_input('Frecuencia cardiaca:',key=88)
        with col76:
            fr = st.text_input('Frecuencia respiratoria:',key=89)
        with col77:
            temp = st.text_input('Temperatura:',key=90)

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
            st.write(cabeza)

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


        ef_alteraciones = f'{alt_cabeza}{renglon}{alt_cuello}{renglon}{alt_cardio}{renglon}{alt_abdomen}{renglon}{alt_extremidades_sup}{renglon}{alt_extremidades_inf}{renglon}{alt_genitales}'
    ef_button = st.form_submit_button('Guarde cambios')
    if ef_button == True:
        st.success('Se han guardado los cambios')



st.header('Examen mental')
form_em = st.form('examen_mental')
with form_em:
    EM = st.expander('Apariencia, actitud, psicomotricidad, ánimo, afecto, lenguaje, pensamiento, introspección, juicio y control de impulsos')
    with EM:
        examen_mental = st.text_area('', key='ex_mental')
    em_button = st.form_submit_button('Guarde cambios')
    if em_button == True:
        st.success('Se han guardado los cambios')

st.header('Diagnósticos')
DX = st.expander('Físicos, psiquiátricos, personalidad, psicosocial')
with DX:
    lista_problemas = st.multiselect('Seleccionar diagnósticos', cie10['code'])
    str_dx = ''
    for i in range(len(lista_problemas)):
        # st.write('',lista_problemas[i],key=4561+i)
        str_dx = f'{str_dx}{i+1}. {lista_problemas[i]}{renglon}'
    st.text_area('Lista de diagnósticos:',str_dx,height=250)
st.header('Pronóstico y clinimetría')
form_pron = st.form('form_pron')
with form_pron:
    exp_pron = st.expander('Establezca el pronóstico y clinemtrias que apliquen')
    with exp_pron:
        pronostico = st.text_input('Pronóstico:','Reservado para la vida y la función')
        clinimetria = st.text_input('Clinimetría:')
    pron_button = st.form_submit_button('Guarde los cambios')
    if pron_button:
        st.success('Se han guardado los cambios')
#============================ TRATAMIENTO
st.header('Tratamiento')
expander_tx = st.expander('Plan para el paciente')
with expander_tx:
    tx_option, tx_col = st.columns([0.2,0.8])
    with tx_option:
        manejo = st.selectbox('', ['Ambulatorio','Hospitalización'])
    with tx_col:
        indicaciones = ''

        try:
            lista_problemas = lista_problemas[0]
        except:
            lista_problemas = []


        if manejo == 'Hospitalización':
            indicaciones = f'1. Ingreso a unidades.{renglon}2. Condición: .{renglon}3. Diagnóstico: {lista_problemas}.{renglon}4. Pronóstico: {pronostico}.{renglon}5. MEDICAMENTOS:{renglon}-{renglon}6. Laboratoriales: {labs_nvos}.{renglon}7. SVPT,CGE, Vigilancia continua y reporte de eventualidades.{renglon}8. valoración por medicina general.'
        tx = st.text_area('',indicaciones,height=200)
#============================ ANALISIS
st.header('Análisis')
form_analisis = st.form('form_analisis')
with form_analisis:
    exp_analisis = st.expander('Análisis del caso')
    with exp_analisis:
        analisis = st.text_area('analisis')
    analisis_button = st.form_submit_button('Guarde los cambios')
    if analisis_button:
        st.success('Se han guardado los cambios')




pdf_file_name = input_pdf_name
def fill_form(data_dict, pdf_file_name, out_file_name=None):
    if out_file_name is None:
        out_file_name = pdf_file_name

    pdf_reader = PdfFileReader(pdf_file_name)
    pdf_writer = PdfFileWriter()
    st.write(data_dict)

    # for page in range(pdf_reader.getNumPages()):
    #     pdf_writer.addPage(pdf_reader.getPage(page))

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

# def fill_form_with_data(data_dict, pdf_file_name, out_file_name=None):
#     if out_file_name is None:
#         out_file_name = pdf_file_name

#     pdf_reader = PdfFileReader(pdf_file_name)
#     pdf_writer = PdfFileWriter()

#     for page in range(pdf_reader.getNumPages()):
#         pdf_writer.addPage(pdf_reader.getPage(page))

#     for field in pdf_reader.getFormTextFields().items():
#         key = field[0]
#         value = data_dict.get(key)
#         if value:
#             pdf_writer.updatePageFormFieldValues(pdf_reader.getPage(0), {key: value})

#     with open(out_file_name, 'wb') as out:
#         pdf_writer.write(out)



# def fill():
#     pdf_file_name = 'Plantilla HC SALME.pdf'
#     out_file_name = 'test.pdf'
#     data_dict = {
#         "1 CURP":curp,
#         "expediente":no_expediente,
#         "fecha":date_str,
#         "Nombres":nombre,
#         "Primer apellido":apellido_paterno,
#         "Segundo apellido":apellido_materno,
#         "f_nacimiento":date_str,
#         "Años":str(edad)
#     }


#     fill_form(data_dict, pdf_file_name, out_file_name)
#     st.write(data_dict['Nombres'])
#     st.write(data_dict['expediente'])

# fill_but = st.button('fill pdf')
# if fill_but:
#     fill()
#     st.success('Se han guardado los cambios')
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
    st.success('SE CREO PDF')
# data_dict = {
#     "1 CURP":curp,
#     "2. NÚMERO DE EXPEDIENTE":no_expediente,
#     "3 FECHA DE ELABORACIÓN":date_str,
#     "Nombres":nombre,
#     "Primer apellido":apellido_paterno,
#     "Segundo apellido":apellido_materno,
#     "Mes":'',
#     "Años":edad,
#     'Hombre':2
# }

# PDF_BUTTON = st.button('Llenar formulario PDF')
# if PDF_BUTTON:
#     fill()
#     st.success('Se han guardado los cambios')
#     st.write(nombre)
#     fill_pdf(pdf_template, pdf_output, data_dict)

# pdftk Plantilla HC SALME.pdf dump_data_fields output fields.txt
fillpdfs.get_form_fields(pdf_template)

# returns a dictionary of fields
# Set the returned dictionary values a save to a variable
# For radio boxes ('Off' = not filled, 'Yes' = filled)

data_dict = {
    "1 CURP":curp,
    "expediente":no_expediente,
    "fecha":date_str,
    "Nombres":nombre,
    "Primer apellido":apellido_paterno,
    "Segundo apellido":apellido_materno,
    "f_nacimiento":date_str,
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
    'dx': str_dx,
    'tx': tx,
    'pronostico': pronostico,
    'clinimetria': clinimetria,
    'analisis': analisis,
    'nombre': nombre_completo,
    'expediente15': no_expediente,
    'fecha16': date_str,
    'ef': f'{ef_merge} | FC: {fc} lpm, FR: {fr} rpm, TA: {ta} mmHg, Temperatura: {temp} °C | Peso: {peso} kg, Talla: {talla} cm, IMC: {imc}',
    'presentacion': f'{nombre_completo}, {sexo} de {edad} años, oriunda y residente de {ciudades}, {edo_nac}. {edo_civil}, {religion}, con estudios de {escolaridad} quien se dedica al {ocupacion} y actualmente esta {trabajo}.',
    'mc17': mc,
    'pa18': pepa,
    'ahf19': ahf_merge,
    'apnp20': apnp_merge,
    'app_2': app_merge,
    'ipas21': ipas,
    'sustancias22': sustancias_merge,
    'em23': examen_mental,
    'analisis24': analisis,
    'labs25': labs_merge,
    'dx26': str_dx,
    'clinimetria27': clinimetria,
    'pronostico28': pronostico,
    'tx29': tx,




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
# if cabeza == 'Sí':
#     st.write('aquiiiii',cabeza)
#     data_dict['cabeza_no'] = 'Off'
#     data_dict['cabeza_si'] = 'Yes'


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


gen_pdf = st.button('Generar archivo PDF')
if gen_pdf:
    fillpdfs.write_fillable_pdf(pdf_template, f'{nombre_completo}.pdf', data_dict)
    st.success(f'Se ha creado el archivo PDF: {nombre_completo}.pdf')
    st.balloons()
    displayPDF(f'{nombre_completo}.pdf')
    # displayPDF('DSM_5.pdf')



# pylint: disable=line-too-long
def display_pdf(file_path, height=None, width=None):
    """
    display a pdf in a streamlit app
    """
    # pylint: disable=line-too-long
    st.markdown("### PDF file")
    with open(file_path, 'rb') as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    if height is None:
        height = 1000

    if width is None:
        width = 600
    file_pdf_path = 'file://DSM_5.pdf'

    st.markdown(f'<iframe src={file_pdf_path} seamless id="PageContent_Iframe"></iframe>', unsafe_allow_html=True)