import streamlit as st
from Bio import Entrez, Medline
import google.generativeai as genai
from gtts import gTTS  # Para convertir texto a voz
from scholarly import scholarly  # Librería para buscar en Google Scholar
import os
from pathlib import Path
import streamlit as st
from Bio import Entrez, Medline
import scholarly
from gtts import gTTS
import requests
import PyPDF2
from io import BytesIO
import os
from dotenv import load_dotenv

load_dotenv()
gemini_api = os.getenv("GEMINI_API")


st.set_page_config(
    page_title=" DeepResearch",
    page_icon="fav.png",  # EP: how did they find a symbol?
    layout="centered" ,
    initial_sidebar_state="collapsed",
)
# Configurar la API key de Gemini (se recomienda usar Streamlit secrets para la clave)
genai.configure(api_key=gemini_api)

# Configurar el email para Entrez
Entrez.email = "your.email@example.com"  # Reemplaza con tu email

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
st.markdown('<div class="title-container"><h1>Deep Research</h1>', unsafe_allow_html=True)

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

# Entrada de la pregunta de investigación
def extract_text_from_pdf(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
                st.markdown(text)
            return text[:2000]  # Limitamos a 2000 caracteres
        return "N/A"
    except Exception as e:
        st.markdown(f"Error al extraer PDF: {e}")
        return f"Error al extraer PDF: {e}"

# Entrada de la pregunta de investigación
research_question = st.text_input("Introduce tu pregunta de investigación o tema de interés:")

# Entrada para definir el número de artículos a buscar por fuente
num_articles = int(st.text_input("Número de artículos a buscar por fuente:", '10'))

# Checkboxes para seleccionar fuentes
search_pubmed = st.checkbox("Buscar en PubMed", value=True)
search_scholar = st.checkbox("Buscar en Google Scholar", value=True)

# Botón para iniciar la búsqueda
if st.button("Iniciar búsqueda") and research_question and (search_pubmed or search_scholar):
    # 1. Generar consulta booleana con Gemini
    with st.spinner("Identificando términos clave con Gemini..."):
        model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')
        boolean_query_pubmed = ""
        boolean_query_scholar = ""
        
        if search_pubmed:
            prompt_terms_pubmed = (f'''
                Como experto en búsquedas médicas, mejora la siguiente pregunta para PubMed.
                Proporciona solo la pregunta mejorada en inglés, sin explicaciones adicionales.
                Pregunta: '{research_question}'
            ''')
            response_terms_pubmed = model.generate_content(prompt_terms_pubmed)
            boolean_query_pubmed = response_terms_pubmed.text.strip()
            st.write(f"Consulta PubMed generada: **{boolean_query_pubmed}**")
            
        if search_scholar:
            prompt_terms_scholar = (f'''
                Como experto en búsquedas médicas, mejora la siguiente pregunta para Google Scholar.
                Proporciona solo la pregunta mejorada en inglés, sin explicaciones adicionales.
                Pregunta: '{research_question}'
            ''')
            response_terms_scholar = model.generate_content(prompt_terms_scholar)
            boolean_query_scholar = response_terms_scholar.text.strip()
            st.write(f"Consulta Google Scholar generada: **{boolean_query_scholar}**")

    # Inicializar listas para combinar resultados
    pubmed_articles_data = []
    gs_articles_data = []
    pubmed_info_text = ""
    gs_info_text = ""

    # 2. Búsqueda en PubMed (si está seleccionada)
    if search_pubmed:
        with st.spinner("Buscando en PubMed..."):
            try:
                handle = Entrez.esearch(db="pubmed", term=boolean_query_pubmed, retmax=num_articles, retmode="xml")
                record = Entrez.read(handle)

                if record["IdList"]:
                    st.success(f"Se encontraron {len(record['IdList'])} artículos en PubMed.")
                    article_ids = record["IdList"]

                    fetch_handle = Entrez.efetch(db="pubmed", id=article_ids, rettype="medline", retmode="text")
                    medline_records = Medline.parse(fetch_handle)
                    link_handle = Entrez.elink(dbfrom="pubmed", id=article_ids, linkname="pubmed_pmc")
                    link_records = Entrez.read(link_handle)

                    article_counter = 1
                    free_full_text_urls = {}

                    for link_set in link_records:
                        pmc_links = link_set.get("LinkSetDb", [])
                        if pmc_links:
                            for link in pmc_links[0].get("Link", []):
                                pmc_id = link.get("Id")
                                if pmc_id:
                                    free_full_text_urls[link_set["IdList"][0]] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"

                    for rec in medline_records:
                        title = rec.get('TI', 'N/A')
                        abstract = rec.get('AB', 'N/A')
                        pmid = rec.get('PMID', 'N/A')
                        authors = rec.get('AU', [])
                        publication_date = rec.get('DP', 's.f.')

                        if authors:
                            citation_authors = f"{authors[0]}, et al." if len(authors) > 2 else ", ".join(authors)
                        else:
                            citation_authors = "Desconocido"
                        year = publication_date.split()[0] if publication_date != 's.f.' else "s.f."
                        apa_citation = f"{citation_authors} ({year}). {title}."
                        
                        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid != 'N/A' else 'N/A'
                        pdf_url = free_full_text_urls.get(pmid, 'N/A')
                        full_text = extract_text_from_pdf(pdf_url) if pdf_url != 'N/A' else "N/A"
                        truncated_abstract = (abstract[:150] + "...") if abstract != "N/A" and len(abstract) > 150 else abstract

                        pubmed_articles_data.append({
                            "Title": title,
                            "Abstract": truncated_abstract,
                            "Link": pubmed_url,
                            "PDF": pdf_url if pdf_url != 'N/A' else "No disponible",
                            "Source": "PubMed"
                        })
                        
                        pubmed_info_text += f"Artículo PubMed {article_counter}:\n"
                        pubmed_info_text += f"Cita APA: {apa_citation}\n"
                        pubmed_info_text += f"Abstract: {abstract}\n"
                        pubmed_info_text += f"Texto completo: {full_text}\n\n" if full_text != "N/A" else "Texto completo: No disponible\n\n"
                        article_counter += 1
                    
                    fetch_handle.close()
                    link_handle.close()
                else:
                    st.warning("No se encontraron artículos en PubMed para la consulta generada.")
            except Exception as e:
                st.error(f"Ocurrió un error durante la búsqueda en PubMed: {e}")
            finally:
                if 'handle' in locals():
                    handle.close()

    # 3. Búsqueda en Google Scholar (si está seleccionada)
    if search_scholar:
        with st.spinner("Buscando en Google Scholar..."):
            try:
                # Crear instancia de Scholarly y buscar publicaciones
                
                gs_search = scholarly.search_pubs(boolean_query_scholar)  # Método correcto en versiones recientes
                i = 0
                while i < num_articles:
                    try:
                        pub = next(gs_search)
                        bib = pub.get('bib', {})
                        title = bib.get('title', 'N/A')
                        abstract = bib.get('abstract', 'N/A')

                        authors_field = bib.get('author', 'Desconocido')
                        authors_list = authors_field if isinstance(authors_field, list) else authors_field.split(' and ')
                        citation_authors = f"{authors_list[0]}, et al." if len(authors_list) > 2 else ", ".join(authors_list)
                        year = bib.get('pub_year', 's.f.')
                        apa_citation = f"{citation_authors} ({year}). {title}."
                        gs_url = pub.get('pub_url', 'N/A')

                        pdf_url = pub.get('eprint_url', 'N/A')
                        full_text = extract_text_from_pdf(pdf_url) if pdf_url != 'N/A' else "N/A"
                        truncated_abstract = (abstract[:150] + "...") if abstract != "N/A" and len(abstract) > 150 else abstract

                        gs_articles_data.append({
                            "Title": title,
                            "Abstract": truncated_abstract,
                            "Link": gs_url,
                            "PDF": pdf_url if pdf_url != 'N/A' else "No disponible",
                            "Source": "Google Scholar"
                        })

                        gs_info_text += f"Artículo Google Scholar {i+1}:\n"
                        gs_info_text += f"Cita APA: {apa_citation}\n"
                        gs_info_text += f"Abstract: {abstract}\n"
                        gs_info_text += f"Texto completo: {full_text}\n\n" if full_text != "N/A" else "Texto completo: No disponible\n\n"
                        i += 1
                    except StopIteration:
                        break
                if gs_articles_data:
                    st.success(f"Se encontraron {len(gs_articles_data)} artículos en Google Scholar.")
                else:
                    st.warning("No se encontraron artículos en Google Scholar para la consulta generada.")
            except Exception as e:
                st.error(f"Ocurrió un error durante la búsqueda en Google Scholar: {e}")

    # 4. Combinar la información de las fuentes seleccionadas
    all_articles_data = pubmed_articles_data + gs_articles_data
    articles_info_text = pubmed_info_text + gs_info_text

    if articles_info_text:
        # 5. Generar resumen consolidado con Gemini
        with st.spinner("Generando resumen consolidado con Gemini..."):
            prompt_summary = (f'''
                            Actúa como un experto médico en investigación clínica. Con la información de los artículos científicos que te dare.
                            1. Elabora un resumen detallado que responda a la siguiente pregunta de investigación: {research_question}. 
                            2. Integra de manera natural en el texto las citas bibliográficas en formato Harvard. 
                            3. La respuesta debe estar en español, con una redacción y formato adecuados para una conversión óptima a voz mediante gTTS. 
                            4. Usa tanto los abstracts como el texto completo de los PDFs cuando esté disponible para enriquecer el resumen.
                            5. IMPORTANTE: No incluyas comentarios adicionales ni secciones de referencias.
                            
                            INFORMACIÓN DE ARTÍCULOS CIENTÍFICOS:

                            {articles_info_text}'''
            )
            model = genai.GenerativeModel('gemini-2.0-flash')
            response_summary = model.generate_content(prompt_summary)
            
        st.subheader("Resumen Consolidado")
        summary_text = response_summary.text
        st.markdown(summary_text, unsafe_allow_html=True)
        
        # Generar audio del resumen
        with st.spinner("🔊 Generando audio del resumen..."):
            tts = gTTS(text=summary_text, lang="es", tld='com.mx')
            audio_path = "resumen_audio.mp3"
            tts.save(audio_path)
            st.audio(audio_path, format="audio/mp3")

        # Guardar la información en la sesión
        st.session_state["articles_info_text"] = articles_info_text
    else:
        st.warning("No se pudo generar información de artículos para el resumen.")

# Sección para consulta adicional
if "articles_info_text" in st.session_state:
    st.markdown("---")
    st.subheader("Consulta Adicional Basada en los Abstracts y Textos Completos")
    followup_question = st.text_input("Introduce tu consulta adicional basada en los abstracts y textos completos:")
    if st.button("Buscar respuesta adicional"):
        with st.spinner("Generando respuesta con Gemini..."):
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt_followup = (
                f"Utilizando la siguiente información de artículos:\n\n{st.session_state['articles_info_text']}\n\n"
                f"Responde únicamente con el resumen de forma detallada y en español a la siguiente consulta: '{followup_question}'.\n\n"
                f"EVITA CUALQUIER OTRO COMENTARIO DISTINTO AL RESUMEN"
            )
            response_followup = model.generate_content(prompt_followup)
        
        st.subheader("Respuesta Adicional")
        followup_text = response_followup.text
        st.write(followup_text)
    
    st.subheader("Bibliografía")
    st.table(all_articles_data)
