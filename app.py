import os
import streamlit as st
import pdfplumber
import docx
from fpdf import FPDF
from pathlib import Path

# API configuration
import google.generativeai as genai

os.environ["GOOGLE_API_KEY"] = 'AIzaSyA_8HmyRV7aJydgGR56CDgI_EXuJ7qn3cM'  
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("models/gemini-1.5-pro")

UPLOAD_FOLDER = 'uploads/'
RESULTS_FOLDER = 'results/'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path):
    ext = file_path.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        with pdfplumber.open(file_path) as pdf:
            text = ''.join([page.extract_text() for page in pdf.pages])
        return text
    elif ext == 'docx':
        doc = docx.Document(file_path)
        text = ' '.join([para.text for para in doc.paragraphs])
        return text
    elif ext == 'txt':
        try:
            with open(file_path, 'r', encoding='utf-8') as file:  
                return file.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='ISO-8859-1') as file:
                return file.read()
    return None

def Question_mcqs_generator(input_text, num_questions):
    prompt = f"""
    You are an AI assistant helping the user generate multiple-choice questions (MCQs) based on the following text:
    '{input_text}'
    Please generate {num_questions} MCQs from the text. Each question should have:
    - A clear question
    - Four answer options (labeled A, B, C, D)
    - The correct answer clearly indicated
    Format:
    ## MCQ
    Question: [question]
    A) [option A]
    B) [option B]
    C) [option C]
    D) [option D]
    Correct Answer: [correct option]
    """
    response = model.generate_content(prompt).text.strip()
    return response

def Short_notes_generator(input_text, num_notes):
    prompt = f"""
    You are an AI assistant helping the user generate concise and meaningful short notes based on the following text:
    '{input_text}'
    Please generate {num_notes} short notes. Each note should be concise, clear, and summarize key points from the text.
    Format:
    ## Note [index]
    [Short Note]
    """
    response = model.generate_content(prompt).text.strip()
    return response

def save_to_file(content, filename):
    results_path = os.path.join(RESULTS_FOLDER, filename)
    with open(results_path, 'w') as f:
        f.write(content)
    return results_path

def create_pdf(content, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for section in content.split("##"):
        if section.strip():
            pdf.multi_cell(0, 10, section.strip())
            pdf.ln(5)  

    pdf_path = os.path.join(RESULTS_FOLDER, filename)
    pdf.output(pdf_path)
    return pdf_path

# Load external CSS and JavaScript
css_path = Path("static/css/focus.css").read_text()
js_path = Path("static/js/focus.js").read_text()

st.markdown(f"<style>{css_path}</style>", unsafe_allow_html=True)
st.markdown(f"<script>{js_path}</script>", unsafe_allow_html=True)

st.title("QuizzyBee")
st.write("Upload a file and generate multiple-choice questions (MCQs) or short notes automatically!")

uploaded_file = st.file_uploader("Upload your document (PDF, TXT, DOCX):", type=['pdf', 'txt', 'docx'])

generation_type = st.radio("What do you want to generate?", ("MCQs", "Short Notes"))

num_items = st.slider("How many items do you want?", min_value=1, max_value=20, value=5, step=1)

# Focus Mode HTML injection
focus_mode_html = """
<div id="focusMode">
    <h1>Focus Mode Activated</h1>
    <div id="pomodoroTimer">
        <h2 id="timer">25:00</h2>
    </div>
    <button onclick="exitFocusMode()">Exit Focus Mode</button>
</div>
"""

# Inject Focus Mode Button
st.markdown(
    '<button onclick="enterFocusMode()">Enter Focus Mode</button>',
    unsafe_allow_html=True,
)
st.markdown(focus_mode_html, unsafe_allow_html=True)

if uploaded_file is not None:
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    text = extract_text_from_file(file_path)

    if text:
        if 'generated_content' not in st.session_state:
            with st.spinner(f"Generating {generation_type}..."):
                if generation_type == "MCQs":
                    content = Question_mcqs_generator(text, num_items)
                else:
                    content = Short_notes_generator(text, num_items)

                st.session_state.txt_filename = f"generated_{generation_type.lower()}_{uploaded_file.name.rsplit('.', 1)[0]}.txt"
                st.session_state.pdf_filename = f"generated_{generation_type.lower()}_{uploaded_file.name.rsplit('.', 1)[0]}.pdf"
                save_to_file(content, st.session_state.txt_filename)
                create_pdf(content, st.session_state.pdf_filename)

                st.session_state.generated_content = content
                st.session_state.uploaded_file_name = uploaded_file.name
                st.success(f"{generation_type} generated successfully!")

        else:
            content = st.session_state.generated_content  

        st.write(f"Here are the generated {generation_type}:")

        for section in content.split("##"):
            if section.strip():
                lines = section.strip().splitlines()
                for line in lines:
                    st.markdown(line)
                st.markdown("---")

        if st.button(f"Regenerate {generation_type}"):
            with st.spinner(f"Generating new {generation_type}..."):
                if generation_type == "MCQs":
                    content = Question_mcqs_generator(text, num_items)
                else:
                    content = Short_notes_generator(text, num_items)

                save_to_file(content, st.session_state.txt_filename)
                create_pdf(content, st.session_state.pdf_filename)

                st.session_state.generated_content = content
                st.success(f"New {generation_type} generated successfully!")

        st.write("Download options:")
        st.download_button(label="Download as TXT",
                           data=open(os.path.join(RESULTS_FOLDER, st.session_state.txt_filename)).read(),
                           file_name=st.session_state.txt_filename)
        st.download_button(label="Download as PDF",
                           data=open(os.path.join(RESULTS_FOLDER, st.session_state.pdf_filename), 'rb').read(),
                           file_name=st.session_state.pdf_filename, mime='application/pdf')
