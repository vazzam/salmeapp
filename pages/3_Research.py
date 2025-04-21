import streamlit as st
from pathlib import Path
import logging
from datetime import date, datetime
from typing import List, Dict, Optional
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
from Bio import Entrez, Medline
import os
import re
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
from gtts import gTTS
import base64
from metapub import PubMedFetcher, FindIt
# Configure logging

# Configuración inicial de Streamlit
st.set_page_config(
    page_title="Deep Research",
    page_icon="fav.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
def procesar_texto(texto):
    patron = r"^```(.*?)```$"
    coincidencia = re.search(patron, texto, re.DOTALL)
    
    return coincidencia.group(1) if coincidencia else texto

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
    with open('style_deepsrch.css', 'r') as f:
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

summary_css = """
<style>
.summary-container {
    background-color: #1e1e1e;
    border-radius: 10px;
    padding: 20px;
    margin-top: 20px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    color: #e0e0e0;
    font-family: 'Arial', sans-serif;
    line-height: 1.6;
}
.summary-container h2 {
    color: #ffffff;
    font-size: 24px;
    margin-bottom: 15px;
    border-bottom: 2px solid #4caf50;
    padding-bottom: 5px;
}
.summary-container p {
    margin: 10px 0;
    font-size: 20px;
    text-align: justify;
}
.summary-container strong {
    color: #4caf50;
}
.summary-container a {
    color: #81d4fa;
    text-decoration: none;
}
.summary-container a:hover {
    text-decoration: underline;
}
</style>
"""

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('pubmed_scraper.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Configurar la API de Gemini
genai.configure(api_key="AIzaSyCZdZpNxhDBGIVEQQkbVPNFVT8uNbF_mJY")

# Configurar el email para Entrez
Entrez.email = "your.email@example.com"  # Reemplaza con tu email



# Inicializar session_state si no existe
if "summaries" not in st.session_state:
    st.session_state["summaries"] = []
if "articles_info_text" not in st.session_state:
    st.session_state["articles_info_text"] = ""

# Clases del Código 2
class PubMedClient:
    def __init__(self, email: str):
        self.email = email
        Entrez.email = email
        
    def search(self, query: str, start_date: str, end_date: str, num_papers: int) -> List[Dict]:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y/%m/%d")
            end_date = end_date if end_date else date.today().strftime("%Y/%m/%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%Y/%m/%d")

            handle = Entrez.esearch(db='pubmed', term=query, retmax=num_papers, sort='relevance', mindate=start_date, maxdate=end_date, datetype='pdat')
            results = Entrez.read(handle)
            handle.close()

            if not results['IdList']:
                return []

            # Obtener detalles de los artículos, incluyendo DOIs
            handle = Entrez.efetch(db='pubmed', id=','.join(results['IdList']), retmode='xml')
            papers = Entrez.read(handle)
            handle.close()

            formatted_results = []
            for i, paper in enumerate(papers['PubmedArticle']):
                try:
                    article = paper['MedlineCitation']['Article']
                    pub_date = article['Journal']['JournalIssue']['PubDate']
                    year = pub_date.get('Year', '')
                    month = pub_date.get('Month', '01')
                    day = pub_date.get('Day', '01')
                    if month.isalpha():
                        month = datetime.strptime(month[:3], '%b').strftime('%m')
                    date_obj = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                    
                    # Extraer DOI si está disponible
                    doi = 'N/A'
                    if 'ELocationID' in article:
                        for loc in article['ELocationID']:
                            if loc.attributes.get('EIdType') == 'doi':
                                doi = loc
                                break
                    
                    formatted_results.append({
                        'title': article.get('ArticleTitle', 'No title available'),
                        'abstract': article.get('Abstract', {}).get('AbstractText', ['No abstract available'])[0],
                        'authors': [f"{author.get('LastName', '')}, {author.get('ForeName', '')}" for author in article.get('AuthorList', [])],
                        'publication_date': f"{year}/{month}/{day}",
                        'date_obj': date_obj.isoformat(),
                        'year': year,
                        'pubmed_id': paper['MedlineCitation']['PMID'],
                        'doi': doi,  # Nuevo campo para el DOI
                        'relevance_order': i,
                        'citations': 0
                    })
                except Exception as e:
                    logger.error(f"Error parsing paper: {e}")
                    continue
            return formatted_results
        except Exception as e:
            logger.error(f"Error in PubMed search: {e}")
            return []

class DownloadTracker:
    def __init__(self):
        self.downloads = []
        
    def add_download(self, status: str, paper_info: dict, message: str, filename: Optional[str] = None):
        download_entry = {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'paper_title': paper_info.get('title', 'Unknown Title'),
            'year': paper_info.get('year', 'N/A'),
            'pmid': paper_info.get('pubmed_id', 'N/A'),
            'url': f"https://pubmed.ncbi.nlm.nih.gov/{paper_info.get('pubmed_id', '')}/",
            'summary': message,
            'filename': filename
        }
        self.downloads.append(download_entry)
        
    def get_downloads(self):
        return sorted(self.downloads, key=lambda x: x['timestamp'], reverse=True)



class PDFDownloader:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        self.fetcher = PubMedFetcher()  # Inicializar el fetcher de metapub

    def try_metapub_download(self, pubmed_id: str, doi: str, filename: str) -> Dict:
        """Intenta descargar el PDF usando el método FindIt de metapub."""
        try:
            # Usar FindIt para localizar el artículo con el PMID
            st.write(doi)
            findit_result = FindIt(doi=doi)
            
            if findit_result and findit_result.url:
                pdf_response = requests.get(findit_result.url, headers=self.headers, allow_redirects=True)
                pdf_response.raise_for_status()
                
                # Verificar si la respuesta es un PDF
                content_type = pdf_response.headers.get('content-type', '').lower()
                if 'application/pdf' in content_type:
                    target_path = self.output_dir / f"{filename}.pdf"
                    counter = 1
                    while target_path.exists():
                        target_path = self.output_dir / f"{filename}_{counter}.pdf"
                        counter += 1
                    with open(target_path, 'wb') as f:
                        f.write(pdf_response.content)
                    return {
                        'success': True,
                        'message': f'Successfully downloaded via metapub (FindIt) to {target_path.name}',
                        'filename': target_path.name
                    }
                else:
                    return {
                        'success': False,
                        'message': f'FindIt URL ({findit_result.url}) did not provide a PDF (Content-Type: {content_type})',
                        'filename': None
                    }
            else:
                return {'success': False, 'message': 'No URL found via metapub FindIt', 'filename': None}
        except Exception as e:
            logger.error(f"Error downloading with metapub FindIt for PMID {pubmed_id}: {str(e)}")
            return {'success': False, 'message': f'metapub FindIt download error: {str(e)}', 'filename': None}

    def try_pmc_download(self, pmcid: str, filename: str) -> Dict:
        # Método existente, sin cambios
        try:
            pmc_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
            response = requests.get(pmc_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            pdf_link = soup.select_one('a[href*="pdf/main.pdf"]')
            if not pdf_link:
                return {'success': False, 'message': 'No PDF link found on PMC', 'filename': None}
            pdf_url = pdf_link['href']
            if pdf_url.startswith('/'):
                pdf_url = f"https://pmc.ncbi.nlm.nih.gov{pdf_url}"
            pdf_response = requests.get(pdf_url, headers=self.headers, allow_redirects=True)
            pdf_response.raise_for_status()
            if pdf_response.headers.get('content-type', '').lower() == 'application/pdf':
                target_path = self.output_dir / f"{filename}.pdf"
                counter = 1
                while target_path.exists():
                    target_path = self.output_dir / f"{filename}_{counter}.pdf"
                    counter += 1
                with open(target_path, 'wb') as f:
                    f.write(pdf_response.content)
                return {'success': True, 'message': f'Successfully downloaded from PMC to {target_path.name}', 'filename': target_path.name}
            return {'success': False, 'message': 'Invalid PDF response from PMC', 'filename': None}
        except Exception as e:
            logger.error(f"Error downloading from PMC {pmcid}: {str(e)}")
            return {'success': False, 'message': f'PMC download error: {str(e)}', 'filename': None}

    def try_scihub_download(self, url: str, filename: str, doi: str) -> Dict:
        # Método existente, sin cambios
        try:
            scihub_url = f"https://sci-hub.se/{doi}"
            response = requests.get(scihub_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            pdf_iframe = soup.find('iframe')
            if pdf_iframe:
                pdf_url = pdf_iframe['src']
                if pdf_url.startswith('//'):
                    pdf_url = 'https:' + pdf_url
                elif pdf_url.startswith('/'):
                    pdf_url = 'https://sci-hub.se' + pdf_url
            else:
                save_button = soup.find('button', onclick=True)
                if save_button:
                    onclick_content = save_button.get('onclick', '')
                    match = re.search(r"location\.href='(.*?)'", onclick_content)
                    if match:
                        pdf_url = match.group(1)
                        if pdf_url.startswith('//'):
                            pdf_url = 'https:' + pdf_url
                        elif pdf_url.startswith('/'):
                            pdf_url = 'https://sci-hub.se' + pdf_url
                        else:
                            pdf_url = pdf_url
                    else:
                        return {'success': False, 'message': 'No downloadable PDF link found on Sci-Hub', 'filename': None}
                else:
                    return {'success': False, 'message': 'No PDF or save button found on Sci-Hub', 'filename': None}
            pdf_response = requests.get(pdf_url, headers=self.headers, allow_redirects=True)
            pdf_response.raise_for_status()
            if 'application/pdf' in pdf_response.headers.get('content-type', '').lower():
                target_path = self.output_dir / f"{filename}.pdf"
                counter = 1
                while target_path.exists():
                    target_path = self.output_dir / f"{filename}_{counter}.pdf"
                    counter += 1
                with open(target_path, 'wb') as f:
                    f.write(pdf_response.content)
                return {
                    'success': True,
                    'message': f'Successfully downloaded from Sci-Hub to {target_path.name}',
                    'filename': target_path.name
                }
            else:
                return {'success': False, 'message': 'Response was not a PDF', 'filename': None}
        except Exception as e:
            logger.error(f"Error downloading from Sci-Hub with requests: {str(e)}")
            return {'success': False, 'message': f'Sci-Hub download error: {str(e)}', 'filename': None}

    def download_paper(self, url: str, doi: str, filename: str, pmcid: Optional[str] = None, pubmed_id: Optional[str] = None) -> Dict:
        """Intenta descargar el PDF priorizando metapub con FindIt, luego PMC y finalmente Sci-Hub."""
        # Extraer pubmed_id de la URL si no se proporciona explícitamente
        if not pubmed_id and url:
            pubmed_id_match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/', url)
            pubmed_id = pubmed_id_match.group(1) if pubmed_id_match else None

        # 1. Intentar con metapub usando FindIt con PMID
        if pubmed_id:
            metapub_result = self.try_metapub_download(pubmed_id, doi, filename)
            if metapub_result['success']:
                return metapub_result
            logger.info(f"metapub FindIt download failed for PMID {pubmed_id}, trying next method")

        # 2. Intentar con PMC si hay PMCID
        if pmcid:
            pmc_result = self.try_pmc_download(pmcid, filename)
            if pmc_result['success']:
                return pmc_result
            logger.info(f"PMC download failed for {pmcid}, trying Sci-Hub")

        # 3. Intentar con Sci-Hub como último recurso si hay DOI
        if doi != 'N/A':
            return self.try_scihub_download(url, filename, doi)
        
        return {'success': False, 'message': 'No download method succeeded (missing PMID, PMCID, or valid DOI)', 'filename': None}

class CitationFetcher:
    def __init__(self):
        self.session = requests.Session()

    def get_citation_count(self, pubmed_id: str) -> int:
        try:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"
            response = self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            citation_elem = soup.find('span', {'class': 'citations-list-total'})
            if citation_elem:
                count = re.search(r'\d+', citation_elem.text)
                return int(count.group()) if count else 0
            return 0
        except Exception as e:
            logger.error(f"Error fetching citations for {pubmed_id}: {e}")
            return 0

# Inicializar componentes
download_tracker = DownloadTracker()
pubmed_client = PubMedClient("your.email@example.com")
pdf_downloader = PDFDownloader(Path("downloads"))
citation_fetcher = CitationFetcher()

# Funciones auxiliares
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def extract_text_from_pdf_url(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            pdf_reader = PdfReader(BytesIO(response.content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text[:2000]  # Limitamos a 2000 caracteres
        return "N/A"
    except Exception as e:
        logger.error(f"Error extracting PDF from URL {url}: {e}")
        return "N/A"

def extract_text_from_pdf_file(pdf_path: Path) -> str:
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text
        
        # Buscar el inicio de la sección "References" (o variaciones comunes)
        ref_patterns = [
            r'\bReferences\b\s*[\n\r]+',  # "References" seguido de salto de línea
            r'\bREFERENCES\b\s*[\n\r]+',  # Mayúsculas
            r'\bBibliography\b\s*[\n\r]+',  # Alternativa menos común
            r'\bReferencias\b\s*[\n\r]+',  # En español, por si acaso
        ]
        
        # Encontrar la primera coincidencia de la sección de referencias
        for pattern in ref_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Cortar el texto hasta antes de "References"
                text = text[:match.start()]
                break
        
        # Eliminar líneas residuales que puedan quedar después del corte (como números o texto incompleto)
        text = "\n".join(line for line in text.splitlines() if line.strip() and not line.strip().isdigit())
        
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""

def generate_summary_with_gemini(text: str, research_question: str) -> str:
    model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')
    prompt = f"""
    Como experto en análisis de literatura científica, genera un resumen conciso del siguiente texto, preferentemente y de ser posible
    orientado a responder la pregunta de investigación: '{research_question}'. 
    Enfócate en cómo el contenido responde a la pregunta, omitiendo detalles irrelevantes. 
    Limita el resumen a 150-250 palabras.
    Texto: '{text[:4000]}'
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating summary with Gemini: {e}")
        return "No summary available due to processing error."

def generate_full_summary(articles_info_text: str, summaries: List[str], research_question: str) -> str:
    model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    combined_content = articles_info_text + "\n\n" + "\n\n".join(summaries)
    prompt = f"""
    Asume el rol de un especialista en medicina con experiencia en investigación clínica y revisión sistemática de literatura científica. Basándote exclusivamente en los artículos científicos proporcionados:

    Sintetiza un informe técnico de 800-1000 palabras que responda con precisión a la pregunta: '{research_question}'.
    El informe debe:

    Estar redactado en español académico-médico
    Seguir una estructura lógica (introducción, desarrollo de hallazgos clave, conclusiones)
    Integrar datos cuantitativos relevantes cuando estén disponibles
    Señalar el nivel de evidencia de las afirmaciones principales
    Identificar posibles limitaciones metodológicas en los estudios analizados


    Utiliza tanto la información de los abstracts como de los textos completos proporcionados.
    Mantén un tono objetivo y analítico, evitando generalizaciones no respaldadas por los datos.
    Prioriza la información más reciente y la de mayor calidad metodológica.
    No incluyas: referencias bibliográficas, comentarios metacognitivos, aclaraciones sobre tu funcionamiento, ni contenido no relacionado directamente con la pregunta.

    Información: '{combined_content}'
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating full summary with Gemini: {e}")
        return "No full summary available due to processing error."

# CSS para tarjetas en tema oscuro
card_css = """
<style>
.card {
    background-color: #2b2b2b;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    transition: transform 0.2s;
    color: #e0e0e0;
}
.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.5);
}
.card-title {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
    margin-bottom: 5px;
}
.card-info {
    font-size: 14px;
    color: #bbbbbb;
    margin: 2px 0;
}
.card-abstract {
    font-size: 13px;
    color: #999999;
    margin-top: 10px;
    line-height: 1.4;
}
</style>
"""

# Interfaz y lógica principal
def main():
    # Header con logo
    logo_path = Path('vitalia.png')
    if logo_path.exists():
        logo_base64 = get_base64_image(logo_path)
        st.markdown(f"""
        <div class="app-header">
            <div class="logo-container">
                <img src="data:image/png;base64,{logo_base64}" class="logo" alt="Logo">
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Logotipo no encontrado.")

    # st.title("Deep Research")

    with st.sidebar:
        st.header("Parámetros de Búsqueda")
        research_question = st.text_input("Pregunta de investigación o tema de interés:")
        num_abstracts = int(st.text_input("Número de abstracts a buscar:", '10'))
        num_downloads = int(st.text_input("Número de artículos a descargar:", '5'))
        start_date = st.date_input("Fecha de inicio", value=date(2020, 1, 1))
        end_date = st.date_input("Fecha de fin", value=date.today(), max_value=date.today())
        sort_by = st.selectbox("Ordenar por", ["relevance", "date", "citations"])

    if st.button("Iniciar búsqueda") and research_question:
        with st.spinner("Generando consulta con Gemini..."):
            model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
            prompt_terms_pubmed = f'''
            Como especialista en informática biomédica y estrategias de búsqueda en literatura médica:

            1. Analiza la siguiente pregunta clínica: '{research_question}'

            2. Desarrolla una estrategia de búsqueda avanzada para PubMed que:
            - Identifique y utilice los términos MeSH específicos y relevantes
            - Incorpore sinónimos clave y variaciones terminológicas
            - Utilice subheadings MeSH apropiados para aumentar precisión
            - Combine adecuadamente operadores booleanos (AND, OR, NOT)
            - Emplee operadores de truncamiento (*) cuando sea beneficioso
            - Incluya filtros de campo estratégicos [Title/Abstract], [Publication Type], etc.
            - Aplique delimitadores temporales si son relevantes para la pregunta

            3. La estrategia debe equilibrar:
            - Sensibilidad (para capturar toda la evidencia relevante)
            - Especificidad (para minimizar resultados irrelevantes)
            - Adaptación a la jerarquía de evidencia científica aplicable a la pregunta

            4. Proporciona únicamente la cadena de búsqueda final en inglés, en texto plano, sin comentarios adicionales, sin etiquetas markdown, y lista para copiar directamente en PubMed.

            Tu respuesta debe contener exclusivamente la cadena de búsqueda, sin explicaciones previas ni posteriores.
            '''
            response_terms_pubmed = model.generate_content(prompt_terms_pubmed)
            boolean_query_pubmed = response_terms_pubmed.text.strip()
            st.write(f"Consulta PubMed generada: **{boolean_query_pubmed}**")

        # Búsqueda de abstracts
        with st.spinner("Buscando abstracts en PubMed..."):
            results = pubmed_client.search(boolean_query_pubmed, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), num_abstracts)
            if not results:
                st.warning("No se encontraron resultados.")
            else:
                with ThreadPoolExecutor(max_workers=5) as executor:
                    citation_futures = {executor.submit(citation_fetcher.get_citation_count, paper['pubmed_id']): i for i, paper in enumerate(results)}
                    for future in concurrent.futures.as_completed(citation_futures):
                        i = citation_futures[future]
                        try:
                            results[i]['citations'] = future.result()
                        except Exception as e:
                            logger.error(f"Error fetching citations: {e}")
                if sort_by == 'date':
                    results.sort(key=lambda x: x['date_obj'], reverse=True)
                elif sort_by == 'citations':
                    results.sort(key=lambda x: x['citations'], reverse=True)
                st.session_state['results'] = results
                st.success(f"Se encontraron {len(results)} abstracts.")

        # Generar articles_info_text desde los abstracts
        articles_info_text = ""
        for i, paper in enumerate(results):
            authors = ", ".join(paper['authors']) if paper['authors'] else "Desconocido"
            apa_citation = f"{authors} ({paper['year']}). {paper['title']}."
            articles_info_text += f"Artículo {i+1}:\nCita APA: {apa_citation}\nAbstract: {paper['abstract']}\n\n"
        st.session_state["articles_info_text"] = articles_info_text

    # Mostrar resultados
    if 'results' in st.session_state and st.session_state['results']:
        st.header("Resultados de la Búsqueda")
        st.markdown(card_css, unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        for i, paper in enumerate(st.session_state['results'][:num_downloads]):  # Limitar a num_downloads para tarjetas
            card_html = f"""
            <div class="card">
                <div class="card-title">{paper['title']} ({paper['year']})</div>
                <div class="card-info"><strong>DOI:</strong> {(paper['doi'])}</div>
                <div class="card-info"><strong>Authors:</strong> {', '.join(paper['authors'])}</div>
                <div class="card-info"><strong>Publication Date:</strong> {paper['publication_date']}</div>
                <div class="card-info"><strong>Citations:</strong> {paper['citations']}</div>
                <div class="card-abstract"><strong>Abstract:</strong> {paper['abstract']}</div>
            </div>
            """
            if i % 2 == 0:
                with col1:
                    st.markdown(card_html, unsafe_allow_html=True)
                    if st.button("Descargar PDF", key=f"download_{paper['pubmed_id']}"):
                        with st.spinner("Descargando PDF..."):
                            result = pdf_downloader.download_paper(
                                url=f"https://pubmed.ncbi.nlm.nih.gov/{paper['pubmed_id']}/",
                                filename=f"paper_{paper['pubmed_id']}",
                                doi=f"{paper['doi']}"
                            )
                            status = 'successful' if result['success'] else 'failed'
                            download_tracker.add_download(status, paper, result['message'], result['filename'] if result['success'] else None)
                            if result['success']:
                                st.success(result['message'])
                                file_path = pdf_downloader.output_dir / result['filename']
                                with open(file_path, 'rb') as f:
                                    st.download_button("Descargar archivo", data=f, file_name=result['filename'], mime="application/pdf", key=f"download_file_{paper['pubmed_id']}")
                            else:
                                st.error(result['message'])
            else:
                with col2:
                    st.markdown(card_html, unsafe_allow_html=True)
                    if st.button("Descargar PDF", key=f"download_{paper['pubmed_id']}"):
                        with st.spinner("Descargando PDF..."):
                            result = pdf_downloader.download_paper(
                                url=f"https://pubmed.ncbi.nlm.nih.gov/{paper['pubmed_id']}/",
                                filename=f"paper_{paper['pubmed_id']}",
                                doi=f"{paper['doi']}"
                            )
                            status = 'successful' if result['success'] else 'failed'
                            download_tracker.add_download(status, paper, result['message'], result['filename'] if result['success'] else None)
                            if result['success']:
                                st.success(result['message'])
                                file_path = pdf_downloader.output_dir / result['filename']
                                with open(file_path, 'rb') as f:
                                    st.download_button("Descargar archivo", data=f, file_name=result['filename'], mime="application/pdf", key=f"download_file_{paper['pubmed_id']}")
                            else:
                                st.error(result['message'])

        if st.button("Descargar todos los artículos"):
            with st.spinner("Descargando artículos..."):
                failed_downloads = []
                summaries = []
                for paper in st.session_state['results'][:num_downloads]:
                    result = pdf_downloader.download_paper(
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{paper['pubmed_id']}/",
                        doi=f"{paper['doi']}",
                        filename=f"paper_{paper['pubmed_id']}",
                        pubmed_id=paper['pubmed_id']
                    )
                    status = 'successful' if result['success'] else 'failed'
                    download_tracker.add_download(status, paper, result['message'], result['filename'] if result['success'] else None)
                    if result['success']:
                        st.success(f"Descargado: {paper['title']} - {result['message']}")
                        file_path = pdf_downloader.output_dir / result['filename']
                        pdf_text = extract_text_from_pdf_file(file_path)
                        # st.write(f'TEXTO EXTRAÍDO: {pdf_text}')
                        if pdf_text:
                            summary = generate_summary_with_gemini(pdf_text, research_question)
                            summaries.append(f"Resumen de '{paper['title']}': {summary}")
                    else:
                        # Añadir URL de PubMed a los fallidos
                        failed_downloads.append({
                            'Title': paper['title'],
                            'PubMed ID': paper['pubmed_id'],
                            'Reason': result['message'],
                            'PubMed URL': f"https://pubmed.ncbi.nlm.nih.gov/{paper['pubmed_id']}/"
                        })
                
                st.session_state["summaries"] = summaries
                if failed_downloads:
                    st.subheader("Artículos no descargados")
                    failed_df = pd.DataFrame(failed_downloads)
                    # Mejorar presentación de la tabla con CSS
                    st.dataframe(failed_df.style.set_properties(**{
                        'background-color': '#4a2e2e',
                        'border-color': '#ef9a9a',
                        'padding': '8px',
                        'text-align': 'left',
                        'color': '#e0e0e0'
                    }).set_table_styles([
                        {'selector': 'th', 'props': [('background-color', '#f44336'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center')]},
                        {'selector': 'td', 'props': [('border-bottom', '1px solid #555')]}
                    ]))
                else:
                    st.success("Todos los artículos descargados con éxito!")

                # Generar resumen completo con estilo mejorado
                if st.session_state["articles_info_text"] or st.session_state["summaries"]:
                    with st.spinner("Generando resumen completo..."):
                        full_summary = generate_full_summary(st.session_state["articles_info_text"], st.session_state["summaries"], research_question)
                        # full_summary = procesar_texto(full_summary)
                        st.markdown(summary_css, unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="summary-container">
                            <h2>Resumen Completo</h2>
                            {full_summary}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("No hay suficiente información para generar un resumen completo.")

    # if st.button("Mostrar historial de descargas"):
    #     downloads = download_tracker.get_downloads()
    #     if downloads:
    #         st.dataframe(pd.DataFrame(downloads))
    #     else:
    #         st.info("No hay descargas aún.")

    # Consulta adicional
    st.markdown("---")
    st.subheader("Consulta Adicional")
    followup_question = st.text_input("Consulta adicional basada en abstracts y textos completos:")
    if st.button("Buscar respuesta adicional"):
        with st.spinner("Generando respuesta..."):
            model = genai.GenerativeModel('gemini-2.0-flash')
            combined_content = st.session_state["articles_info_text"] + "\n\n" + "\n\n".join(st.session_state["summaries"])
            prompt_followup = (
                f"Utilizando la siguiente información de artículos:\n\n{combined_content}\n\n"
                f"Responde únicamente con el resumen de forma detallada y en español a la siguiente consulta: '{followup_question}'.\n\n"
                f"EVITA CUALQUIER OTRO COMENTARIO DISTINTO AL RESUMEN"
            )            
            response_followup = model.generate_content(prompt_followup)
            st.subheader("Respuesta Adicional")
            st.write(response_followup.text)

if __name__ == "__main__":
    main()
