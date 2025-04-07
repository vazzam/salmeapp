import random
from datetime import date, datetime 
import streamlit as st
from unidecode import unidecode
from pymongo import MongoClient
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from openai import OpenAI
import google.generativeai as genai
import re
import pyaudio
import threading
import io
import wave
from pydub import AudioSegment
from streamlit_mic_recorder import mic_recorder
# openai.api_key = "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"
genai.configure(api_key="AIzaSyCZdZpNxhDBGIVEQQkbVPNFVT8uNbF_mJY")
# RAND BLOOD PRESSURE VALUES

def rand_ta():
    ta = f'{random.randint(100,130)}/{random.randint(66,78)}'
    return ta

def procesar_texto(texto):
    patron = r"^```(.*?)```$"
    coincidencia = re.search(patron, texto, re.DOTALL)
    
    return coincidencia.group(1) if coincidencia else texto

#ALMACEN DATOS FIJOS
# @st.cache_data
def stored_data(name):
    
    data = {
            'escalas': ['RASS.pdf','bush y francis.pdf', 'simpson angus.pdf', 'gad7.pdf', 'sad persons.pdf', 'young.pdf', 'fab.pdf', 'assist.pdf', 'dimensional.pdf', 'psp.pdf', 'yesavage.pdf', 'phq9.pdf', 'Escala dimensional de psicosis.pdf', 'moca.pdf', 'moriski-8.pdf', 'mdq.pdf', 'calgary.pdf', 'eeag.pdf', 'madrs.pdf'],
            'gpc': ['SSA-222-09 Diagnostico y tratamiento de la esquizofrenia', 'IMSS 170-09 Diagnostico y tratamiento del trastorno bipolar',
            'IMSS-392-10 Diagnostico y tratamiento del trastorno de ansiedad en el adulto', 'APA- Practice guideline for the treatment of patients with borderline personality disorder',
            'IMSS-161-09 Diagnostico y tratamiento del trastorno depresivo en el adulto', 'IMSS-528-12 Diagnostico y manejo de los trastornos del espectro autista',
            'IMSS-515-11 Diagnostico y manejo del estres post traumatico', 'SS-343-16 Diagnostico y tratamiento del consumo de marihuana en adultos en primer y segundo nivel de atención',
            'SS-023-08 Prevención, detección y consejeria en adicciones para adolescentes y adultos.', 'IMSS-385-10 Diagnostico y tratamiento de los trastornos del Sueño',
            'SS-666-14 Prevención, diagnóstico y manejo de la depresión prenatal', 'SS-294-10 Detección y atención de violencia de pareja en adulto',
            'ss-210-09 Diagnostico y tratamiento de epilepsia en el adulto',
            'IMSS-465-11 Prevención, diagnóstico y tratamiento del DELIRIUM en el adulto mayor hospitalizado'    
            ]
        }
    return data[name]


# Configurar cliente OpenAI compatible con deepinfra
client = OpenAI(
    api_key="8EQlNuXZiBBmZKRo7SxklJyjnWgsDbHm",  # Reemplaza con tu clave real
    base_url="https://api.deepinfra.com/v1/openai",
)
# def resumen_paciente(datos):
#     model = genai.GenerativeModel('gemini-2.0-flash')
#     response = model.generate_content(f'''INSTRUCCIONES: Actúa como un especialista médico y elabora un resumen conciso del expediente clínico proporcionado, siguiendo estrictamente la estructura solicitada.

#                                         FORMATO: 
#                                         - Presenta la información en una tabla con las columnas: Fecha, Evolución y síntomas, Hallazgos clínicos, Análisis médico y Tratamiento.
#                                         - Utiliza terminología médica apropiada manteniendo un tono profesional.
#                                         - Enfatiza y detalla más extensamente la última consulta, mientras que las anteriores deberán ser más breves y concisas.

#                                         ESTRUCTURA REQUERIDA:
#                                         1. Encabezado: Nombre completo, edad y ocupación del paciente
#                                         2. Motivo de la consulta inicial
#                                         3. Antecedentes médicos relevantes: Historia médica previa significativa para el caso actual
#                                         4. Tabla cronológica de consultas que incluya para cada visita:
#                                         - Fecha exacta
#                                         - Síntomas reportados (con citas textuales del paciente cuando estén disponibles)
#                                         - Resumen muy breve de los hallazgos más relevantes durante la consulta
#                                         - Resumen del análisis médico de la consulta
#                                         - Plan de tratamiento y recomendaciones

#                                         ELEMENTOS ADICIONALES:
#                                         - Si el expediente contiene valores registrados de escalas de valoración (GAF, PHQ-9, GAD-7, MDQ, etc), genera una tabla cronológica con las fechas y resultados correspondientes.

#                                         EXPEDIENTE CLÍNICO:
#                                         {datos}'''
#                                     )
#     resumen = response.text + '---'
#     return resumen

html_ex = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evolución de Escalas Clinimétricas y Peso</title>
    <style>
        body {
            background-color: transparent;
            margin: 0;
            padding: 40px;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #fff;
        }
        .frame {
            background: linear-gradient(145deg, rgba(44, 44, 44, 0.9), rgba(37, 37, 37, 0.9));
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
            padding: 30px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            max-width: 2100px;
            margin: 0 auto;
            flex-wrap: nowrap;
            overflow-x: auto;
        }
        .chart-container {
            width: 400px;
            height: 300px;
            background: transparent;
            position: relative;
            border-radius: 12px;
            padding: 15px;
            transition: all 0.3s ease;
            flex-shrink: 0;
        }
        .chart-container:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
        }
        canvas {
            background: transparent !important;
            border-radius: 10px;
        }
        ::-webkit-scrollbar {
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(51, 51, 51, 0.5);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(85, 85, 85, 0.7);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(119, 119, 119, 0.9);whius
        }
    </style>
</head>
<body>
    <div class="frame">
        <div class="chart-container">
            <canvas id="phq9Chart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="gad7Chart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="gafChart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="mdqChart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="weightChart"></canvas>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const chartConfig = {
            type: 'line',
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { 
                            color: 'rgba(255, 255, 255, 0.05)',
                            borderColor: 'rgba(255, 255, 255, 0.2)'
                        },
                        ticks: { 
                            color: '#e0e0e0',
                            font: { size: 12, weight: '500' }
                        }
                    },
                    y: {
                        grid: { 
                            color: 'rgba(255, 255, 255, 0.05)',
                            borderColor: 'rgba(255, 255, 255, 0.2)'
                        },
                        ticks: { 
                            color: '#e0e0e0',
                            font: { size: 12, weight: '500' }
                        }
                    }
                },
                plugins: {
                    legend: {
                        labels: { 
                            color: '#ffffff',
                            font: { size: 16, weight: '600' },
                            padding: 20,
                            boxWidth: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleFont: { size: 14, weight: '600' },
                        bodyFont: { size: 12 },
                        cornerRadius: 10,
                        padding: 12,
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }
                },
                elements: {
                    line: {
                        tension: 0.5,
                        borderWidth: 3,
                        fill: false,
                        spanGaps: true
                    },
                    point: {
                        radius: 6,
                        hoverRadius: 9,
                        backgroundColor: '#fff',
                        borderWidth: 2
                    }
                },
                animation: {
                    duration: 1800,
                    easing: 'easeOutExpo'
                }
            }
        };

        const data = {
            labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
            phq9: [10, null, 8, null, 6, 5],
            gad7: [8, 9, null, 6, null, 4],
            gaf: [60, null, 65, 70, null, 75],
            mdq: [null, 5, 3, null, 3, 2],
            weight: [70, 71, null, 70, null, 69]
        };

        new Chart(document.getElementById('phq9Chart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'PHQ-9',
                    data: data.phq9,
                    borderColor: '#ff6b6b',
                    pointBackgroundColor: '#ff6b6b',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });

        new Chart(document.getElementById('gad7Chart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'GAD-7',
                    data: data.gad7,
                    borderColor: '#4ecdc4',
                    pointBackgroundColor: '#4ecdc4',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });

        new Chart(document.getElementById('gafChart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'GAF',
                    data: data.gaf,
                    borderColor: '#45b7d1',
                    pointBackgroundColor: '#45b7d1',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });

        new Chart(document.getElementById('mdqChart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'MDQ',
                    data: data.mdq,
                    borderColor: '#96c93d',
                    pointBackgroundColor: '#96c93d',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });

        new Chart(document.getElementById('weightChart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Peso (kg)',
                    data: data.weight,
                    borderColor: '#ffa502',
                    pointBackgroundColor: '#ffa502',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });
    </script>
</body>
</html>'''


def resumen_paciente(datos):
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(f'''INSTRUCCIONES: Actúa como un especialista médico y elabora un resumen conciso del expediente clínico proporcionado, 
                                        seguido del código HTML para visualizar gráficamente la evolución de las escalas clinimétricas registradas.
                                        RESUMEN DE EXPEDIENTE CLÍNICO
                                          - Presenta la información en una tabla con las columnas: Fecha, Evolución y síntomas, Hallazgos clínicos, Análisis médico y Tratamiento.
                                          - Utiliza terminología médica apropiada manteniendo un tono profesional.
                                          - Enfatiza y detalla más extensamente la última consulta, mientras que las anteriores deberán ser más breves y concisas.

                                          ESTRUCTURA REQUERIDA:
                                          1. Encabezado: Nombre completo, edad y ocupación del paciente
                                          2. Motivo de la consulta inicial
                                          3. Antecedentes médicos relevantes: Historia médica previa significativa para el caso actual
                                          4. Tabla cronológica de consultas que incluya para cada visita:
                                          - Fecha exacta
                                          - Síntomas reportados (con citas textuales del paciente cuando estén disponibles)
                                          - Resumen muy breve de los hallazgos más relevantes durante la consulta
                                          - Resumen del análisis médico de la consulta
                                          - Plan de tratamiento y recomendaciones
                                          5. Utiliza escritura markdown para resaltar títulos y subtítulos
                                          
                                          EXPEDIENTE CLÍNICO:
                                          {datos}
                                        
                                        GRÁFICAS DE CLINIMETRÍAS
                                        
                                        Si el expediente contiene valores registrados de escalas de valoración (GAF, PHQ-9, GAD-7, MDQ, etc.),
                                        genera código HTML para visualizar la evolución de los puntajes de las escalas clinimétricas registradas junto con el peso del paciente.
                                        Crea una gráfica individual para cada conjunto de valores y muéstralas dentro de un marco que contenga todas las gráficas generadas.
                                        Solo incluye gráficos de los parámetros con más de 2 valores registrados.
                                        La escala de cada gráfica debe comenzar en 0 y terminar en el valor máximo de la escala correspondiente.
                                        Si faltan valores entre dos mediciones registradas, la línea debe unir directamente los puntos existentes sin considerar los valores ausentes como 0.
                                        Evita explicaciones adicionales sobre el código html o las gŕaficas generadas.
                                        Usa la siguiente plantilla HTML como base:
                                        {html_ex}
                                        '''
                                    )
    html_code = re.search(r'```html(.*?)```', response.text, re.DOTALL)
    if html_code:
        html_code = html_code.group(1).strip()
    else:
        html_code = ""

# Extraer el resto del texto (todo lo demás)
    resumen = re.sub(r'```html(.*?)```', '', response.text, flags=re.DOTALL).strip()
    resumen = re.sub(r'```markdown(.*?)', '', resumen, flags=re.DOTALL).strip()
    
    # resumen = re.search(r'```(.*?)```', resumen, re.DOTALL)
    # if resumen:
    #     resumen = resumen.group(1).strip()
    # else:
    #     resumen = resumen

    # st.text(resumen)
    return resumen, html_code

def chat_expediente(pregunta, expediente):
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(f'''INSTRUCCIONES: Actúa como un especialista médico y responde la pregunta sobre el expediente clínico proporcionado, siguiendo estrictamente la estructura solicitada.

                                        FORMATO: 
                                        - Presenta la información de una forma breve, precisa y concisa con un formato de fácil lectura e interpretación en pocas líneas
                                        - Utiliza terminología médica apropiada manteniendo un tono profesional.
                                        PREGUNTA:
                                        {pregunta}
                                        EXPEDIENTE CLÍNICO:
                                        {expediente}'''
                                    )
    respuesta = response.text
    return respuesta


def audio_recorder_transcriber(nota: str):
    """Función reutilizable para grabar, segmentar y transcribir audio desde el navegador."""
    
    def split_audio(audio_data: io.BytesIO, segment_duration_ms: int = 300000):  # 10 minutos por segmento
        """Divide el audio en fragmentos menores."""
        try:
            audio = AudioSegment.from_wav(audio_data)
            duration_ms = len(audio)
            segments = []
            for start_ms in range(0, duration_ms, segment_duration_ms):
                end_ms = min(start_ms + segment_duration_ms, duration_ms)
                segment = audio[start_ms:end_ms]
                segment_io = io.BytesIO()
                segment.export(segment_io, format="webm")  # Mantener WAV para simplicidad
                segment_io.seek(0)
                segments.append(segment_io)
            return segments
        except Exception as e:
            st.error(f"Error al segmentar el audio: {str(e)}")
            return None

    def transcribe_audio(audio_data):
        """Transcribe el audio segmentado."""
        try:
            # segments = split_audio(audio_data)
            # if not segments:
            #     return None
            
            # full_transcription = ""
            # for i, segment in enumerate(segments):
            #     st.write(f"Procesando segmento {i + 1} de {len(segments)}...")
            #     segment_size_mb = len(segment.getvalue()) / (1024 * 1024)
            #     if segment_size_mb > 25:
            #         st.warning(f"El segmento {i + 1} ({segment_size_mb:.2f} MB) excede el límite de 25 MB. Ajusta la duración.")
            #         continue
                
            response = client.audio.transcriptions.create(
                model="openai/whisper-large-v3-turbo",
                file=("audio.wav", audio_data, "audio/wav"),
                language="es"
            )
            
            # st.write(response.text)
            if response.text:
                summarized = resumen_transcripcion(response.text, nota)
                st.success("Transcripción completa exitosa")
                return summarized
            return None
        except Exception as e:
            st.error(f"Error al transcribir: {str(e)}")
            return None

    def resumen_transcripcion(transcripcion, nota):
        model = genai.GenerativeModel('gemini-2.0-flash')
        if nota == "primera":
            response = model.generate_content(f'''
                INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento de un paciente basándote en la transcripción de consulta proporcionada. Ten en cuenta que la transcripción es producto de una conversación entre el médico y el paciente, por lo que deberás identificar correctamente quién está hablando en cada intervención para asegurar una reconstrucción precisa y coherente del relato clínico.

                OBJETIVO: Redactar la evolución del padecimiento del paciente, desde su inicio hasta el estado actual, integrando únicamente la información clínica relevante extraída de las intervenciones del paciente durante la consulta.

                FORMATO REQUERIDO:
                - Idioma español
                - Texto en párrafos continuos (sin viñetas ni subtítulos), sin salto doble de línea
                - Extensión mínima de 300 a 400 palabras
                - Lenguaje técnico apropiado para documentación clínica
                - Escrito en tercera persona

                INCLUIR:
                - Antecedentes relevantes del padecimiento
                - Cronología detallada de síntomas y manifestaciones
                - Cambios en la severidad e intensidad a lo largo del tiempo
                - Factores desencadenantes o exacerbantes identificados
                - Estado actual del paciente

                OMITIR:
                - Toda información que no corresponda a la evolución del padecimiento del paciente, incluyendo sugerencias terapéuticas realizadas o propuestas durante la consulta
                - Información personal no relevante para la evolución
                - Recomendaciones o plan de tratamiento
                - Juicios de valor
                - Diagnósticos
                - Análisis sobre el caso
                - Resúmenes al final del texto

                IMPORTANTE: Dado que la transcripción incluye tanto preguntas del médico como respuestas del paciente, considera únicamente los fragmentos en los que el paciente describe su experiencia subjetiva. Ignora las intervenciones del médico excepto cuando sirvan para contextualizar una respuesta del paciente.

                ESTRUCTURA TU RESPUESTA SIGUIENDO ESTILO DE LOS EJEMPLOS A CONTINUACIÓN:

                        Ejemplo 1:
                        “Cuadro actual de aproximadamente 11 meses de evolución, de inicio insidioso, curso continuo y tendiente al empeoramiento, en el contexto de un trastorno depresivo recurrente que evoluciona hacia un trastorno depresivo persistente, desencadenado por conflictos en la relación con el padre de su hijo y agravado por dependencia emocional, aislamiento social y dificultades económicas.
                        Por interrogatorio directo, la paciente refiere que desde entonces comenzó con estado de ánimo predominantemente deprimido, tendencia al llanto, apatía con pérdida del interés por actividades que previamente disfrutaba dejando de arreglarse, maquillarse y salir con amigas. Presenta hiporexia con pérdida de 8 kg en aproximadamente 7 meses con fluctuaciones en el peso; hay insomnio mixto con múltiples despertares para verificar a su hijo. Se agregaron problemas de concentración con olvidos frecuentes incluyendo la administración de medicamentos, enlentecimiento psicomotriz y fatiga.

                        Hay pensamientos persistentes de culpa relacionados con su embarazo y la percepción de "decepcionar" a sus padres, así como ideas de minusvalía "no sirvo para nada", "soy una mantenida", "les he fallado". Se añadieron pensamientos pasivos de muerte "sería mejor no estar" aunque sin ideación suicida estructurada. Presenta ansiedad con predominio de pensamientos catastróficos en relación a su familia, cefalea tipo migraña y estreñimiento.

                        Hace aproximadamente 6 meses inició tratamiento con duloxetina 60mg/día notando mejoría parcial de síntomas aunque sin remisión completa. Hace un mes, tras descubrir una presunta infidelidad de su expareja, presenta exacerbación de síntomas depresivos con deterioro en autocuidado llegando a espaciar el baño hasta por una semana, mayor aislamiento social y inicio de consumo diario de alcohol (3 cervezas) como mecanismo de afrontamiento.

                        Los síntomas han impactado significativamente en su funcionalidad, presentando deterioro en el autocuidado, dificultad para realizar las actividades de rehabilitación de su hijo y aislamiento social. Por lo anterior y el aumento de los síntomas ansiosos así como la perdida de motivación que decide acudir a consulta.”

                        Ejemplo 2:
                        “En el contexto de una historia de múltiples episodios depresivos, inicia su padecimiento actual en abril 2023 de forma insidiosa, continua y tendiente al empeoramiento sin un desencadenante aparente y agravado por deprivación académica, dificultades económicas, conflictos de pareja. Según refiere, desde entonces, comenzó con un estado de ánimo predominantemente deprimido, tendencia al llanto, apatía con perdida del interés por actividades que previamente daban placer dejándo de disfrutar sus actividades del día dejándo de asear su casa y descuidando su autocuidado. A lo anterior se añadieron hiporexia con perdida de entre 6 y 7 kg en 6 messes; hay insomnio mixto con latencia de conciliación de unas 2 horasy al menos 3 despertares; dificultades para la concentración con perdida de objetos y dificultad para mantener el hilo de conversaciones; enlentecimiento psicomotriz. Ha notado la presencia de pensamientos de culpa, minusvalía y pasivos de muerte "me siento insuficiente... siento que no le intereso a nadie, me rechazan y he pensado en mejor desaparecer [sic paciente]". A lo anterior se añadieron ansiedad flotante, nerviosísmo, cervicodorsalgia, aislamiento y episodios de pánico con sensación de ahogo, malestar torácico y síntomas vegetativos de 10-15 minutos de duración y que han ido incrementado en frecuencia de 1-2 / semana a 1-2 por día. Refiere que de junio a agosto presentó acoasmas fugaces con impacto en ánimo incrementando síntomas de ansiedad. En este contexto hace 1 mes, tras discutir con su madre, de forma impulsiva y con intención suicida, tomó unos 7ml de solución de clonazepam 2.5mg/ml sin necesidad de manejo intrahospitalario. Por lo anterior fue valorada hace 10 días en CEB en donde prescribieron fluoxetina con mejoría subjetiva referidade 10%. Por lo anterior es que decide acudir a valoración.”

                        Ejemplo 4:
                        “El episodio actual se da en el contexto de un patrón de conducta de inicio en la adolescencia tardía, persistentemente desadaptativo e inflexible caracterizado por sensación de vacío crónico, inestabilidad en la relaciones interpesonales y de emociones  con consecuentes conflictos con los padres y parejas; miedo al abandono que le ha condicionado mantenerse en una relación marcada por la violencia; ideas sobrevaloradas referenciales y distorsiones de la autoimagen; también ha presentado pobre tolerancia a la frustración que le conicionaron episodios de desregulación emociona con la presencia de ira desporporcionada e ipmulsividad que le generan conducta autolesivas como método de afrontamiento (cutting) y reactivación de pensamientos de muerte. Padecimiento de alrededor de 9 meses de inicio insidioso, continuo y tendiente al empeoramiento desencadenado por la muerte de la abuela y agravado por desempleo y separación del conyuge. Desde entonces ha presentado un estado de ánimo persistentemente triste, tendiente al llanto espontáneo; insomnio de inicio con latencia de conciliación de hasta 4 horas en asociación a rumiaciones entorno a su situación de pareja;  enlentecimiento psicomotor, problemas para la concentración con múltipls olvidos; hiporexia con perdida de 15 kg en un par de meses; además ha prsentado pensamientos de culpa, minusvalía y pasivos de muerte "Es mi culpa que me haya tratado así, me he fallado... a veces he pensado en no querer depesrtar pero pienso en mis hijos y pasa [sic]". De forma paralela ha presentado ansiedad flotante, cervicodorsalgia, nerviosísmo, inquietud motriz y paroxismos de exacerbación síntomas que se acompañan de descarga adrenérgica con sensación de muerte o perder el control. Hace 2 días, de forma impulsiva, tras ver su expareja con otra persona, presentó tentativa suicida abortada mediante flebotomía "me detienen mis hijos... fue el impuso en ese rato [sic]”

                        TEXTO A RESUMIR:
                        {transcripcion}
            ''')
        elif nota == 'primera_paido':
            response = model.generate_content(f'''
            INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento de un paciente basándote en la transcripción de consulta proporcionada. Ten en cuenta que la transcripción es producto de una conversación entre el médico y el paciente, por lo que deberás identificar correctamente quién está hablando en cada intervención para asegurar una reconstrucción precisa y coherente del relato clínico.

            OBJETIVO: Redactar la evolución del padecimiento del paciente, desde su inicio hasta el estado actual, integrando únicamente la información clínica relevante extraída de las intervenciones del paciente durante la consulta.

            FORMATO REQUERIDO:
            - Idioma español
            - Texto en párrafos continuos (sin viñetas ni subtítulos), sin salto doble de línea
            - Extensión mínima de 300 a 400 palabras
            - Lenguaje técnico apropiado para documentación clínica
            - Escrito en tercera persona

            INCLUIR:
            - Antecedentes relevantes del padecimiento
            - Cronología detallada de síntomas y manifestaciones
            - Cambios en la severidad e intensidad a lo largo del tiempo
            - Factores desencadenantes o exacerbantes identificados
            - Estado actual del paciente

            OMITIR:
            - Toda información que no corresponda a la evolución del padecimiento del paciente, incluyendo sugerencias terapéuticas realizadas o propuestas durante la consulta
            - Información personal no relevante para la evolución
            - Recomendaciones o plan de tratamiento
            - Juicios de valor
            - Diagnósticos
            - Análisis sobre el caso
            - Resúmenes al final del texto

            IMPORTANTE: Dado que la transcripción incluye tanto preguntas del médico como respuestas del paciente, considera únicamente los fragmentos en los que el paciente describe su experiencia subjetiva. Ignora las intervenciones del médico excepto cuando sirvan para contextualizar una respuesta del paciente.

            ESTRUCTURA TU RESPUESTA SIGUIENDO ESTILO DE LOS EJEMPLOS A CONTINUACIÓN:

            EJEMPLO NÚMERO 1
            Se refiere una menor que proviene de una familia integrada, el padre era director de una secundaria, muere hace 3 años, era alcohólico. Ella refiere que tenia una relacion muy distante con el padre, "no me decía hija, me decía niña", muy pobre convivencia e interacción afectiva. Ella se ha caracterizado desde siempre de ser una niña solitaria, pocas amistades, en la escuela pobre convivencia, pero ya para 5to año con unas amigas hizo un video porno animado haciendom alución a un par de compañeros, lo que provocó que la condicionaran, y también le rompió un huevo de confeti a una maestra y tuvo un reporte. Ella señala que tuvo varios cambios de primaria por el trabajo de la madre como intendente y le toca pandemia de covid en 6to, por lo que ingresa a mitad de secundaria y mismo comportamiento de aislamiento, ella acepta que poco hizo, poco trabajó y logró terminarla y actualmente en preparatoria, ella dice que faltan mucho los maestros, que no tiene amigas y que por eso dejó de ir, así que termina con 64 y 3 materias reprobadas. La madre la refiere depresiva, siempre aislada en su habitación, no habla con nadie, irritable, intolerante, agresiva, no tolera indicaciones, tiene su habitación sucia, come mucho pues no tiene nada que hacer, se la pasa viendo videos, series, videojuegos, se dice estar ansiosa, pues piensa mucho las cosas, onicofagia, se muerde las mucosas de la boca, se siente de ánimo "regular, seria, pensativa", niega ideas de muerte o suicidio, alguna vez en 5to año y por los problemas que tuvo. Por estar en sus pensamientos no pone atención en nada y la madre se enoja pues no hace lo que le pide. Hace un mes van a psicología y esta pide que venga a psiquiatría para ser medicada. 

            EJEMPLO NÚMERO 2
            Menor que es identificado desde el kinder como muy inquieto, pero ahora que entra a primaria totralmente un cuadro caracterizado por inatención, disperso, inquieto, no trabaja en clase pues se la pasa parado y platicando, se sale del salón, muy rudo en su trato con sus compañeros, empuja o pelea, libros y cuadernos maltratados, mochila desorgaizada, pierde sus artículos escolares. En casa muy dificil para que haga las tareas, se enoja y se le tiene que presionar y vigilar, todo el tiempo en movimiento, en la comida, se levanta constantemente, se le tiene que corregir constantemente, se le castiga, tiene momentos en que es contestón, grosero, desobediente, no mide los peligros, en la calle se le tiene que vigilar pues se cruza las calles, presenta enuresis 5x30, en la socialización si convive pero termina peleando o haciendo trampa en los juegos pues no sabe perder y llora mucho. La maestra yua no lo aguanta en el salón, por eso lo deriva a esta institución. 

            EJEMPLO NÚMERO 3
            Menor identificado desde la primaria con toda la sintomatología de hiperactividad, inatención, impulsividad, disperso, inatento, no trabajar, cuadernos y libros maltratados, mochila desorganizada, reportes constantes, en casa dificil para hacer tareas, no se le dio la atención y si se le generaban multiples regaños y sanciones, un hijo menor con diferencia con su hermana de 15 años, padres muy incompatibles por lo que vivió en medio muy disfuncional, el hermano mayor de 32a con tratamiento en salme, por lo que también es violento, ingresa a secundaria y aunado a la adolescencia totalmente disfuncional, no trabajar, no hacer tareas, distraído, fuera del salón y debuta en el consumo de multiples sustancias, ingresa a preparatoria y definitivamente abandona por el consumo principalmente de cocaína, asi pues que no estudia. Acude a psicología en varias ocasiones y a psiquiatría, le dijeron que tenía depresión y ansiedad y le dieron sertralina 50mg-d. Hace 5 meses vive con el padre porque pelea mucho con la madre, pero igual con el padre, miente de todo, exagera todo, le aumenta a todo, coamete hurtosmenores en la tienda de la madre como golosinas o algun billete de 20 pesos, ayer se disgustaron porque ya desconfían mucho de él y se tardó en un mandado y se pelearon, y se puso alterado, golpeando paredes, diciendo que quería morirse, el señala que siente una gran necesidad de consumir sustancias pero que sabe que no puede, se siente desesperado por salir a consumir asi que ayer consumió thc y clonazepam 1.5mg, y al no consumir siente que ya no existe nada que para que está. Acuden a urgencias y les dicen que se esperen a la cita de psiquiatria infantil.
                
            EJEMPLO NÚMERO 4
            Menor que proviene de familia disfuncional y desintegrada, se separan los padres, de principio se queda con la madre y el hermano, pero se señala que la mamá llevaba una vida sin responsabilidades, primero se va el hijo con el padre y hace 5 años la menor se va también con el padre, pues aparentemente presenció situaciones de tipo sexual y se la lleva el padre y está en juicio la custodia. Desde que la menor está en kinder se presentran los reportes de conducta y se hacen totalmente evidentes en primaria, inatención, dispersa, hiperactividad, impulsividad, peleonera, no trabajar en clase, bajas calificaciones, siempre de pie, platicando. En casa muy dificil para hacer las tareas, se le tienen que decir muchas ocasiones, y por lo tanto se enoja y hace berrinches y con ello se rasguña la cara, se azota en el suelo, se golpeó la cabeza y se hizo una herida, vive con el padre y la pareja del padre con su hija adolescente, con la madrastra es muy rebelde y con el padre ñmuy modocita, asi que el padre la tiene con superprotección, por lo que no tiene ni reglas ni normas, en la secundaria que acaba de ingresar ya están los reportes, y ademas de peleas con niñas mucho mas grandes que ella y las calificaciones fueron de 6 y 7 en todas las materias y por ello es que la traen a valoración.

            EJEMPLO NÚMERO 5
            Menor que proviene de familia desintegrada y disfuncional, la madre refiere que el padre la dejaba encerrada con su hija mayor, y el se iba a trabajar o a bailar o salir con sus amigos y amigas. Le dejaba de forma muy específica que tenía que hacer y que quería de comer y como prepararlo, fueron 5 años de esta forma de vida y al final decide ella separarse, la madre se queda con la custodia de la niña y el padre la visita o bien la menor va algunos fines de semana a casa de él, ella refiere que ya sentía cierto acercamiento por parte de él, y a los 10a ya hay tocamientos en varias ocasiones y finalmente termina en una presunta penetración, el padre la amenaza que si habla, "me iba a ir peor", por ello no lo dice e inicia con sintomatología caracterizada por tristeza, miedo, ansiedad, temblor, inquietud, sueño con pesadillas "tenía como un bloqueo", asi como presenta ideas suicidas por diversas situaciones como sentir a la madre distante de ella, por lo que sucedía con el padre, sentimiento de culpabilidad, pensó en el harocamiento sin ninguna planificación o intento. Refiere que por estar pensando primero en todos los problemas familiares y posterior por el presunto abordaje sexual, siempre muy distraída enla escuela, incluso pensaba que nno quería estudiar, por lo que siempre con muy bajas calificaciones, sin reportes de conducta. El 25 de noviembre 2024 la menor finalamente abre el tema con una tía, pues llegaba la fecha en que tendría que ir otra vez con el padre, la tía se lo dice a la madre y van a ciudad niñez en donde se interpone una denuncia, fue valorada por ginecobstetrica y psicología y que buscaran atención en psiquiatría y por eso están en la consulta. En este momento no dan ningun tipo de sintomatología pues ella refiere que una vez que lo dijo, cambió todo, se siente mejor, incluso en la escuela ya puede estudiar y tiene califs de 9 y 10.
                
            EJEMPLO NÚMERO 6
            Masculino escolar, procedente de familia desintegrada por dinámica de violencia y padre consumidor de metanfetaminas; con antecedente de gesta patológica, de nacimiento prematuro y bajo peso al nacer, por desprendimiento prematuro de placenta y múltiples patologías asociadas a la prematurez incluida la patología de base que motiva que acudan a consulta. Tras 2 años de múltiples manejos médicos y quirúrgicos inicia su terapie en crit- teletón donde reicbió terapia física con notoria mejoría motriz, comenzando con sedestación, gateo y bipedestación asistida y emisión de bisilabos. Hace un año la madre se percata del inicio de episodios de irriitabilidad con heteroagresividad y alteraciones del patrón de sueño con insomnio de inicio "se enojaba mucho, nos mordía, pellizcaba, no dejaba de llorar" sic. Madre. Es por lo anterior que fue valorado por el psiquiatra de dicha institución quien no dio diagnóstico e inició manejo a base de 0.5mg de risperidona con mejoría sustantiva en cuanto a lo conductual, cediendo irritabilidad, heteroagresividad y mejora en el patrón del sueño. Hace 4 meses es que la madre nota que de forma progresiva la irritabilidad, heteroagresividad y rabietas fueron en incremento por lo que en ausencia actual del servicio de psiquiatría en el crit, deciden acudir a nuestra institución parar valoración.

            EJEMPLO NÚMERO 7
            Menor que proviene de familia monoparental, segunda hija de madre añosa, la hermana mayor actualamente tiene 26a, se desarrolla dentro de la casa de la abuela materna, quien es una mujer rigida, estricta, regañona, y por otro lado la madre también muy estricta, lo que hace una niña muy ansiosa y preocupada, tiene un largo historial de la primaria, la cambiaron en 3 ocasiones, siempre porque fue sensible que si un maestro u otro le hablaban fuerte, que en ocasiones ella recoanoce era su persepción, en otras era real, esta inestabilidad genera que tenga bajas calificaciones, entre 6 y 7. Refiere que hace un año es que se hacen mas evidentes los sintomas afectivos que hasta entonces eran fluctuantes, ella refiere que como desencadenantes son los cambios de escuela, la abuela y su trato, la muerte del abuelo materno que era su figura paterna, conoce al padre y llevan una relacion irregular que ya ahora es nula, ella presenta sentimientos de soledad, no se expresa, no cuenta sus cosas, sentimiento de que en su casa la hacen a un lado, mala apreciacion de su aspecto personal, labilidad emocional, llora de todo, miedo al que dirán. Refiere que tiene eventos de sonambulismo 3 bien reconocidos y hace 22 días presentó dengue y tuvo hipertermia muy marcada y unmomento de estado delirante por lo mismo en la madugada, se salió de la casa, caminó varias calles y se regresó al su casa, la estuvieron buscando y la abuela por su carácter la regaño, que porque hacía eso, que porque se había salido en la madrugada y como la madre estaba en usa, la mujer se sentía responsable de todo. También refiere sintomatología de macropsias y alucinaciones quinestésicas. De forma especifica refiere sintomatología depresiv caracterizada por llanto, aislamiento, no hablar, no salir, sentirse incomprendida, desesperación, de ansiedad onicofagia, se quita la paiel de los dedos (padrastros), se truena los dedos, mueve constantemente los pies. Tuvo problemas en la secundaria por una amistad que le estimuló a no entrar a clases y por ello la reportaron. En casa irritable, contestona, malmodienta, no hace sus quehaceres, dificil para su aseo personal.

            EJEMPLO NÚMERO 8
            Hombre escolar, nacido en méxico y criado en eeuu desde los 2 años hasta hace 6 meses. Proviene de una familia integrada, aunque temporalmente separada por la permanencia del padre en eeuu hasta el siguiente mes. La familia está compuesta por la madre, quien es ama de casa, el padre, técnico en aire acondicionado, y un hermano menor de 3 años; es el mayor de 2 hermanos. Se le refiere como un menor aplicado en la escuela con buen desempeño académico, aunque impulsivo, poco tolerante a la frustración y con un patrón de sueño caracterizado por despertares prematuros (4 am). A partir de su ingreso a la primaria, se hicieron evidentes la dificultad para atender indicaciones de la madre, particularmente en actividades que le resultan tediosas, pérdida y descuido de los útiles escolares y una tendencia a la desorganización, principalmente manifiesta en el orden de su habitación. La sintomatología que los motiva a acudir hoy a consulta inició durante el curso de 2o. De primaria, cuando tras un malentendido entre una compañera y él, la madre de esta lo abordó extraoficial y unilateralmente con aparentes amenazas. A partir de entonces, se le comenzó a notar constantemente ansioso/temeroso, tendiente al retraimiento y con disminución de la interacción social, notablemente nervioso con inquietud constante y chupeteo de región perioral, desarrollando una dermatosis como consecuencia. Se observó el incremento de la irritabilidad, oposicionismo y hostigamiento hacia el hermano menor. Por lo anterior y a petición del menor, decidieron cambiar su lugar de residencia a méxico en junio del 2024, permaneciendo el padre en eeuu. La ausencia del padre a quien refiere extrañar; el proceso de adaptación por el cambio cultural, dinámica escolar, residencia con la abuela con quien tiene una relación de conflicto, acentuaron la sintomatología descrita, particularmente la irritabilidad y negativismo "es lo que más tiene, le digo que haga algo y a todo reniega, dice que porque él... También le trae mucho coraje a su hermano y se la pasa molestándolo" sic. Madre. Es por lo anterior que deciden acudir a valoración.

            EJEMPLO NÚMERO 9
            El menor tiene el historial que desde prescolar es reportado por inquietud, pero ya en primaria el cuadro es evidente, es un niño inatento, disperso, inquieto, platica, se levanta, deja trabajos incompletos, pierde artículos escolares e incluso ropa, descuidado con el uniforme, se ensucia, es muy poco tolerante con sus compañeros, pelea con ellos, no quiere que hagan ruido, lo que genera ciertas riñas, y por su intolerancia y que quiere corregir a todos ya lo apartan,él se da cuenta de esto, hacen equipos y no lo eligen, pobre concentración, trae la mochila revuelta, este ciclo se ha hecho mas evidente el cuadro por las exigencias propias del 3er año. En casa muy dificil para hacer las tareas, se le tiene que decir muchas veces, y se tarda mucho en terminar cualquier tarea, lo mismo sucede con el aseo personal, sus quehaceres, en la comida está inquieto, no puede hacer mas de una iandicación, come mas o menos bien pero se la pasa platidando en la comida, tiene muy poca tolerancia a todo, siempre dice que se siente "humillado", suele pelear con su hermana de 11a, la socialización es regular, conlal madre se enoa mucho, el estado de ánimo dice que "neutro", se siente ansioso reflejado por estres, irritabilidad, enojo, dice que por estar solo en la escuela, refiere insomnio intermedio, en alguna ocasión llegó a pensar en morir para ir a ver a su papá que murió hace 4 años por covid. La madre lo lleva a un centro llamado cade, se ve el rsumen que les dieron, atendido por un psiquiatra general y una medico general, le prescribieron mfd lp de 20mg 1-0-0, y risperidona 0.25mg-d, se le dio durante un mes, la madre vio muy poca respuesta, y en la escuela con el dx. Que les dieron de tdah mixto bajaron la tensión y bajaron los reportes, por costos ya que subieron la consulta a 1450 pesos y el medicamento, pues mejor ya lo trae a esta institución.

            EJEMPLO NÚMERO 10
            Menor que proviene de familia estructurada, con el padre una relación un poco rispida porque el mismo acepta que está irritable, el cuadro tiene origen desde la infancia, pues padeció leucemia y en la primaria fue victima de acoso escolar por no tener pelo y usar cubrebocas, se fueron a vivir a durango pero regresan a arandas y refiere fue un cambio muy busco para el, tanto por la escuela como por los compañeros, por lo que es muy solitario, poco sociable, en casa se aisla, no habla con la familia se la pasa en el celular jugando, videojuegos de armas y defensas. Pero el dice que hace un año esto se hace muy evidente, se siente con astenia, adinamia, hiporexia, insomnio importante, miedos e inseguridades, afecto hipotímico, llega a pensar en la muerte y el suicido, pensando en el ahorcamaiento o cortarse, sin ningun intento de por medio, refiere sientomatología ansiosa como taquicardia, temblor, dolor precordial, cefalea, dolor de espalda, se siente irritable, intolerante, contesta mal, onicofagia, hiperhidrosis, la madre refiere que muchas noches llega a la habitación de ellos y se duerme con ellos, se le ve con labilidad emocional y llanto, así mismo hace 7 meses termino con la novia y eso también le afectó, escasa relación con sus hermanos mayores, si con su hermana, con la madre bien, pues pasa mucho tiempo en casa con ella, pero acepta que puede llegar a ser grosero con ella. No estudia pero si trabaja, se llega a ir con el padre a trabajar como albañil.

            EJEMPLO NÚMERO 11
            Menor que proviene de familia disfuncional y desintegrada, por infidelidad mutua de ambos padres hace 4a, a raíz de esto y teniendo ella 10a inicia con tristeza, astenia, ideas suicidas, cuadro que fue progresando al empeoramiento y la cronicidad, anhedonia, alteracion grave del sueño, ausentismo escolar, irritabilidad, intolerancia, malas contestaciones, bajan las calificaciones progresivamente, y tiene ya 3 intentos suicidas, cortes en extremidades e ingesta de medicamentos, en junio 2024 inclso estuvo 24 horas ingresaada en la clinica 45, referida por el Centro Médico de Occidente que solo la valoró y la refirió y no la ha visto en ningun momento tratamaiento tampoco ninguno, asi pues aue el cuadro oscilante entre ansiedad y sintomatología depresiva, actualamente refiere sed de aire, labialiadd emocional, llanto, ultimo pensamaiento suicida ayer, sin factor desencadenante, llegan ya de forma intrusiva, el sueño sigue mal y refiere que las ideas en general es porque siente que "no encaja", no habla con la gente y sentimiento de soledad.

            TEXTO A RESUMIR:
            {transcripcion}
        ''')
            
        else:
            response = model.generate_content(f'''
            INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta una nueva nota de la evolución clínica del paciente entre la consulta previa y la actual, basándote en la transcripción de la consulta proporcionada. Considera que dicha transcripción corresponde a una conversación entre el médico y el paciente, por lo que deberás identificar con claridad quién interviene en cada momento, extrayendo exclusivamente la información clínica relevante que proviene del testimonio del paciente para asegurar una redacción precisa y coherente.

            OBJETIVO: Redactar una nota de evolución clínica del paciente que abarque los cambios y continuidad en la presentación de síntomas, desde la última valoración hasta la fecha actual.

            FORMATO REQUERIDO:
            - Idioma español
            - Texto en párrafos continuos (sin viñetas ni subtítulos), sin salto doble de línea
            - Extensión mínima de 300 a 400 palabras
            - Lenguaje técnico apropiado para documentación clínica
            - Escrito en tercera persona

            INCLUIR:
            - Antecedentes relevantes del padecimiento
            - Cronología detallada de síntomas y manifestaciones (cognitivos, emocionales, ansiosos, afectivos o anímicos, del sueño, del apetito y adherencia al tratamiento)
            - Cambios en la severidad e intensidad de los síntomas a lo largo del tiempo
            - Factores desencadenantes o exacerbantes identificados por el paciente
            - Estado actual del paciente

            OMITIR:
            - Cualquier información que no forme parte de la evolución clínica del padecimiento
            - Sugerencias o intervenciones terapéuticas expresadas por el médico durante la consulta actual
            - Información personal no relevante
            - Recomendaciones o planes de tratamiento
            - Juicios de valor
            - Diagnósticos
            - Análisis o interpretaciones clínicas
            - Resúmenes finales

            IMPORTANTE: Dado que la transcripción incluye tanto las preguntas del médico como las respuestas del paciente, enfoca tu atención exclusivamente en las intervenciones del paciente que aporten información clínica relevante. Utiliza las preguntas del médico solo como guía para contextualizar las respuestas del paciente, sin incluirlas de forma directa.

            ESTRUCTURA TU RESPUESTA SIGUIENDO ESTILO DE LOS EJEMPLOS DE NOTAS DE EVOLUCIÓN A CONTINUACIÓN:

            Ejemplo 1: “Se encuentra clínicamente estable, su ánimo lo refiere como mayoritariamente bien, salvo los primeros días a partir de que fue despedida, hecho que logró afrontar sin mayores complicaciones; se sintió apoyada por sus padres. Se encuentra buscando empleo, ha tenido entrevistas con adecuado desempeño y "segura" de sí misma; en ciernes entrevista que más le llama la atención. En cuanto a ansiedad ha presentado algunos síntomas asociados al estatus de la relación con su novio de la que en ocasiones se siente con culpa. Refiere un patrón de sueño fragmentado por las micciones nocturnas, 2 por noche. En cuanto al incremento de la dosis de MFD no notó tanto cambio, probablemente, por el contexto laboral. Se queja de hiporexia con impacto ponderal de 3kg en 3 semanas. El consumo de cannabis ha disminuido al igual que el craving.”

            Ejemplo 2: “La paciente refiere que hacia el mes de diciembre después de entre 1 a 2 meses de haber suspendido la sertralina por "sentirse bien" comenzó con irritabilidad por lo que acudió a psicología con mejoría sustancial. Acude el día de hoy porque desde hace 2 meses ha notado anhedonia, llanto espontáneo, hiperfagia con aumento de peso lo que impacta de forma negativa en su ánimo. Ha tenido apatía, pérdida de interés, ha dejado de cocinar, lavar su ropa, fatiga, ha perdido el interés en su arreglo, baja en la líbido, pensamientos pasivos de muerte, culpa, minusvalía con recriminación a sí misma y tendencia al aislamiento. Comienza con insomnio de conciliación; hipoprosexia. No ha presentado síntomas ansiosos.”

            Ejemplo 3: “Refiere que no ha notado cambios sustantivos respecto a la valoración previa salvo que ya ha tenido iniciativa para avanzar en los pendientes personales y encomendados. Por ejemplo hoy que no tuvo clase se puso a aspirar y lavar la alfombra de su cuarto, plan que tenía 2 meses en planes "antes me hubiera puesto hacer otra cosa". Ha tenido dificultades para despertar e ir a hacer ejercicio. Continúa con dificultades para conciliar el sueño aunque puede estar asociado a que, aunque se va a dormir a las 10pm, lo hace mientras está en videollamada con su novia. Una vez conciliado el sueño no despierta por las madrugadas y despierta hacia las 6:40 am para sus actividades, buen patrón alimenticio y de sueño. En lo escolar se siente un poco más social con mayor participación en clase e interacción con sus compañeros; en lo atencional ha mejorado sustantivamente en buena medida a que ha adoptado cambios como despejarse previo clase "voy al baño me mojo la cara, voy por una bebida y ya me enfoco mejor (sic)". En relación a la reducción de lorazepam no notó cambio alguno. Dice sentirse emocionado porque lo visitará su novia dentro de 1 mes. He disfrutado jugar XBOX, lavar los carros y cocinar.”

            Ejemplo 4: “Acude paciente refiriéndo continuar con estabilidad de sus síntomas, es decir, con la disminución de la ansiedad y síntomas depresivos además de la casi ausencia de los pensamientos de culpa/minusvalía (los de muerte están ausentes); sin embargo refiere que algunos días, los menos, ha tenido algunas bajas en el estado de ánimo sin una causa identificada. Adecuada adherencia al tratamiento, patrón de sueño y alimenticio. También ha notado menos "fastidio" por estar haciendo su trabajo además de menor irritabilidad, mayor energía con mejor concentración y rendimiento en su empleo. En cuanto a la ansiedad casi han desaparecido las rumiaciones ansiógenas y cuando estas se presentan logra identificarlas y darles cauce. Continúa con actividad física a base de rutina dentro de casa con una frecuencia de 3 días por semana durante 40 minutos. Subjetivamente califica su estado de ánimo de un 8-9/10.”

            TEXTO A RESUMIR:
            {transcripcion}
        ''')
        return response.text


    # Inicializar estado
    if "audio_data" not in st.session_state: 
        st.session_state["audio_data"] = None
    if "transcripcion" not in st.session_state:
        st.session_state["transcripcion"] = ""
    if "is_recording" not in st.session_state:
        st.session_state["is_recording"] = False

    # Interfaz
    col1, col2 = st.columns(2)
    with col1:
        st.text('')
        audio_value =  mic_recorder(
        start_prompt="Toma nota 💬",
        stop_prompt="Detener 🟥",
        just_once=False,
        use_container_width=True,
        format="webm",
        callback=None,
        args=(),
        kwargs={},
        key=None
    )
        if audio_value:
            st.audio(audio_value['bytes'])
        if audio_value and not st.session_state["is_recording"]:
            st.session_state["audio_data"] = audio_value['bytes']
            st.session_state["is_recording"] = True
            # st.success("Grabación iniciada")

    with col2:
        if st.button("Transcribir...", use_container_width=True, icon='🔮'):
            if st.session_state["audio_data"]:
                st.session_state["is_recording"] = False
                # st.success("Grabación detenida")
                with st.spinner("Segmentando y transcribiendo..."):
                    transcripcion = transcribe_audio(st.session_state["audio_data"])
                    if transcripcion:
                        st.session_state["transcripcion"] = transcripcion
                        st.session_state["audio_data"] = None

    if st.session_state["is_recording"]:
        st.write("Tomando nota...")

    return st.session_state["transcripcion"]

def calculate_age(born):
    today = datetime.now()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def clin_merge(scale):
    if scale != '':
        return f' {scale}, '
    else:
        return ''

def radio_check(var):
    if var != '':
        return 'Yes'
    else:
        return ''
    
def update_dict(dic,var):
    dic.update({var:'Yes',})

def id_gen():
    now = datetime.now()
    date_id = now.strftime('%d%m%y%H%M%S')
    return int(date_id)
# @st.cache_data
def ensure_index(action, collection, index_name, index_key):
    """
    Ensure that a specified index exists on a collection. If the index does not
    exist, create it using the specified index key.

    :param action: Must be an str an lets us to 'delete' or 'create' an index.
    :param collection: The MongoDB collection to ensure the index on.
    :param index_name: The name of the index to check/create.
    :param index_key: A dictionary of field names and sort orders to use as the index key.
    """
    if action == 'create':
        # Check if the index exists
        if index_name not in [idx['name'] for idx in collection.list_indexes()]:
            # If the index does not exist, create it
            collection.create_index(index_key, name=index_name)
            print(f"Created index '{index_name}' on collection '{collection.name}'")
        else:
            print(f"Index '{index_name}' already exists on collection '{collection.name}'")
    else:
        collection.drop_index(index_name)
        print(f'Index {index_name} has been deleted')
# @st.cache_data
def search_collection(collection, criteria, all_info = True):
    """
    Search a MongoDB collection for documents that match a set of criteria.

    :param collection: The MongoDB collection to search.
    :param criteria: A dictionary of search criteria.
    :return: A list of all documents in the collection that match the criteria.
    """
    results = []
    if all_info:
        for document in collection.find(criteria):
            results.append(document)
        return results
    else:
        for document in collection.find(criteria,{'_id': 0, 'nombres':1,'primer apellido':1,'segundo apellido':1,'generales.nacimiento.fecha': 1}):
            results.append(document)
        return results
    st.write(results)

def unidecode_except(string):
    # Replace all characters except for the ones in the exception list
    exceptions = ['ñ','1','2','3','4','5','6','7','8','9','0',]
    replaced_string = ''
    for c in string:
        if c in exceptions:
            replaced_string += c
        else:
            replaced_string += unidecode(c)

    return replaced_string

def data_format(field, val):
    """
    :param field: Debe ser array
    :param val: Debe ser array
    """
    for i in range(len(val)):
        val[i]= unidecode_except(val[i])

    # print(val)    

    temp_ar = {}
    for i in range(len(field)):
        temp_ar[field[i]] = {"$regex": val[i],"$options": "i"}
        # print(f'{i}. {temp_ar}')
    # print(temp_ar['nombres'])
    return temp_ar

def doc_field( database_name, collection_name, filter, projection):
    # Set up a MongoDB client and database
    db = database_name
    
    # Set up a collection in the database
    collection = db[collection_name]
    
    # Find all matching documents with the specified fields
    documents = collection.find(filter, projection)
    
    # Loop through the documents and return the specified fields
    results = []
    for document in documents:
        result = {}
        for field in projection:
            result[field] = document[field]
        results.append(result)
    return results

def buscar_clientes(nombre, apellido_paterno, apellido_materno):
    # crear una conexión con la base de datos
    db = ['expedinente electronico']
    collection = db['pacientes']

    # buscar coincidencias usando los parámetros de búsqueda
    resultados = collection.find({
        'nombre': nombre,
        'apellido_paterno': apellido_paterno,
        'apellido_materno': apellido_materno
    }, {
        '_id': 0,
        'generales.fecha_nacimiento': 1
    })

    # retornar los resultados de la búsqueda junto con la fecha de nacimiento
    return [r for r in resultados]

def check_ef(var):
    if var == "":
        var = 'sin alteraciones'
    return var

def note_show(consultas_previas, paciente, nota):
    renglon = '\n'
    evol = st.expander('CONSULTAS PREVIAS', expanded=True)
    with evol:
        # st.subheader(consultas_previas)
        fechas_citas = []                       
        for i in range(consultas_previas):
            fechas_citas.insert(0,paciente[0]['consultas'][i]['fecha'])
            # fechas_citas = sorted(fechas_citas, key=lambda x: datetime.strptime(x, "%d/%m/%Y %H:%M"), reverse=True)
        fecha_nota_prev = st.selectbox('Seleccione fecha de citas previas:', fechas_citas)
        for consulta in paciente[0]["consultas"]:
            if consulta["fecha"] == fecha_nota_prev:
                if consulta['fecha'] == fechas_citas[-1]: # Se coteja si es la consulta de primera vez
                    #Es consulta de primera vez
                    st.subheader('Consulta de primera vez')
                    # st.write(consulta)
                    st.text_area('', nota, height=300)
                else:
                    # st.write("Se encontró una consulta en la fecha buscada:")
                    # st.write(consulta)
                    prev_cons = consulta

                    consulta_anterior = ('##### '+prev_cons['fecha'] + renglon + renglon + #'- ' +
                                            '> ' + prev_cons['presentacion'].replace('\n', ' ') + renglon + '- ' + 
                                            prev_cons['subjetivo'] + renglon + renglon + 
                                            '- '+'SOMATOMETRÍA Y SIGNOS VITALES:' + renglon + 
                                            'FC: ' + prev_cons['fc'] + ' lpm' + ' | ' +  'FR: ' + prev_cons['fr'] + ' rpm' + ' | ' + 'TA: ' + prev_cons['ta'] + ' mmHg' + ' | ' + ' ------- ' + 'PESO: ' +  str(prev_cons['peso']) + ' ' + 'kg' + '  ' + 'TALLA: ' + str(prev_cons['talla']) + ' ' + 'cm' + renglon + renglon + '- ' +
                                            prev_cons['objetivo'] + renglon + renglon + 
                                            'PHQ-9: '+ prev_cons['clinimetrias']['phq9'] + ' ' + ' |   ' + 
                                            'GAD-7: '+ prev_cons['clinimetrias']['gad7'] + ' ' + ' |   ' +
                                            'SADPERSONS: '+ prev_cons['clinimetrias']['sadpersons'] + ' ' + ' |   ' +
                                            'YOUNG: '+ prev_cons['clinimetrias']['young'] + ' ' + ' |   ' +
                                            'MDQ: '+ prev_cons['clinimetrias']['mdq'] + ' ' + ' |   ' +
                                            'ASRS: '+ prev_cons['clinimetrias']['asrs'] + ' ' + ' |   ' +
                                            'OTRAS: '+ prev_cons['clinimetrias']['otras_clini'] + ' ' + ' |   ' + renglon + renglon +     
                                            '##### '+ 'ANÁLISIS: ' + renglon +prev_cons['analisis'] + renglon + renglon +
                                            '##### '+ 'PLAN: ' + renglon + prev_cons['plan'] + renglon + '--- '
                                #  prev_cons['objetivo'] + renglon + 
                                #  prev_cons[''] + renglon + 
                                #  prev_cons[''] + renglon + 
                                #  prev_cons[''] + renglon + 
                                    ) #f'{consulta}{renglon}{renglon}MC: {mc}{renglon}PA: {pa}{renglon}{renglon}EXAMEN MENTAL{renglon}{renglon}{em}{renglon}{renglon}EXPLORACIÓN FÍSICA{renglon}{renglon}{somato_sv_merge}{renglon}{renglon}{ef_merge}{renglon}{alteraciones_merge}{renglon}{renglon}LABORATORIALES{renglon}- Previos: {labs_prev}{renglon}- Solicitados: {labs_nvos}{renglon}{renglon}DIAGNÓSTICO(S){renglon}{renglon}{dx}{renglon}{renglon}PRONÓSTICO: {pronostico}{renglon}{renglon}{clinimetria}{renglon}{renglon}ANÁLISIS{renglon}{renglon}{analisis}TRATAMIENTO{renglon}{renglon}{tx}'
                    # st.subheader(f'Consulta subsecuente No: {consultas_previas}')
                    # nota_revisada = st.text_area('', consulta_anterior, height=450)
                    st.markdown(consulta_anterior)
    return fechas_citas[-1]

def last_note(consultas_previas, paciente, nota):
    renglon = '\n'
    fechas_citas = []                       
    for i in range(consultas_previas):
        fechas_citas.append(paciente[0]['consultas'][i]['fecha'])
    
    return fechas_citas[-1], len(fechas_citas)


def mongo_intial():
    uri = "mongodb+srv://jmvz_87:grmUXwQNW7o4hv2N@stl.hnzdf.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['expedinente_electronico'] #base de datos
    pacientes = db['pacientes'] #colección
    ensure_index('create',pacientes,'nombre_apellidos', [('nombres', 1), ('primer apellido', -1), ('segundo appelido', 1)])
    return client, pacientes

def mongo_connect():
    uri = "mongodb+srv://jmvz_87:grmUXwQNW7o4hv2N@stl.hnzdf.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['expedinente_electronico'] #base de datos
    pacientes = db['pacientes'] #colección
    ensure_index('create',pacientes,'nombre_apellidos', [('nombres', 1), ('primer apellido', -1), ('segundo appelido', 1)])
    return client

# def gdrive_up(local_file, final_name):
#     g_login = GoogleAuth()
#     g_login.LocalWebserverAuth()
#     drive = GoogleDrive(g_login)
#     file_name = local_file
#     gfile = drive.CreateFile({'parents': [{'id': '1ESHu5ZblpwcCI5PrHP-80YrQ-NPiH7nm'}], 'title': final_name})
#     # Read file and set it as the content of this instance.
#     gfile.SetContentFile(file_name)
#     gfile.Upload()
#     print(file_name)
#     # gfile.GetContentFile(file_name)
#     print('---------DESPUES DE LEER ARCHIVO')
#     file_url = 'https://drive.google.com/file/d/' + gfile['id'] + '/view'
#     return file_url

def gdrive_up(local_file, final_name):
    gauth = GoogleAuth()
    scope = ['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/drive.file','https://www.googleapis.com/auth/drive.appdata']
    # gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name('./service_account.json',scope)
    gauth.service_account_json = 'service_account.json'
    print(gauth)
    drive = GoogleDrive(gauth)
    file_name = local_file
    gfile = drive.CreateFile({'parents': [{'id': '1ESHu5ZblpwcCI5PrHP-80YrQ-NPiH7nm'}], 'title': final_name})
    # Read file and set it as the content of this instance.
    gfile.SetContentFile(file_name)
    gfile.Upload()
    print(file_name)
    # gfile.GetContentFile(file_name)
    print('---------DESPUES DE LEER ARCHIVO')
    file_url = 'https://drive.google.com/file/d/' + gfile['id'] + '/view'
    return file_url

# def chatgpt(data, summary_lenght, model = 'chat'):
#     prompt = f'Actúa como un experto médico especialista en pisuiatría y ayúdame a hacer un resumen a forma de párrafo de no más de 10 líneas con los principales antecedentes del paciente y finallmente organiza en una tabla cada una de las consultas con los principales síntomas y tratamientos: {data}'
#     if model == 'chat':
#             response = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo-16k",
#             messages=[{"role": "user", "content": f'{prompt}'}
#                 ])
#             return response.choices[0]['message']['content']
