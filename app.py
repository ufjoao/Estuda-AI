import os
import random # Novo import para a seleção aleatória
import json # Novo import para lidar com dados JSON na sessão
from flask import Flask, render_template, request, redirect, url_for, session # Importar 'session'
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2
import pdfplumber

app = Flask(__name__)
# !!! IMPORTANTE: Use uma chave secreta forte e única em produção !!!
app.config['SECRET_KEY'] = 'uma_chave_secreta_muito_segura_e_aleatoria_aqui_para_a_sua_aplicacao'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf'}

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('models/gemini-2.0-flash')

# --- Funções de extração de texto (mantidas) ---
def extrair_texto_pypdf2(caminho_pdf):
    texto_completo = ""
    try:
        with open(caminho_pdf, 'rb') as arquivo:
            leitor_pdf = PyPDF2.PdfReader(arquivo)
            for pagina in leitor_pdf.pages:
                texto_completo += pagina.extract_text() + "\n"
    except Exception as e:
        print(f"Erro ao extrair texto com PyPDF2: {e}")
        return None
    return texto_completo

def extrair_texto_pdfplumber(caminho_pdf):
    texto_completo = ""
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for page in pdf.pages:
                texto_completo += page.extract_text(x_tolerance=2, y_tolerance=2) + "\n"
    except Exception as e:
        print(f"Erro ao extrair texto com pdfplumber: {e}")
        return None
    return texto_completo

def extrair_texto_ocr(caminho_pdf):
    print("Função OCR ainda não implementada. Use um PDF digital para testar.")
    return "Texto não extraído: OCR não implementado."

# --- Funções de interação com Gemini (mantidas) ---
def identificar_exercicios_com_gemini(texto_completo_do_pdf, model_gemini):
    prompt_identificacao = f"""
    Dado o seguinte texto extraído de um documento, identifique e extraia todas as questões ou exercícios.
    Para cada questão identificada, forneça apenas o texto da questão, sem as soluções ou explicações.
    Liste as questões em uma lista numerada.

    Formato de saída desejado:
    1. [Texto da primeira questão]
    2. [Texto da segunda questão]
    ...

    Se não houver questões claras, responda 'Nenhuma questão encontrada.'.

    TEXTO:
    ---
    {texto_completo_do_pdf}
    ---
    """
    try:
        response = model_gemini.generate_content(prompt_identificacao)
        return response.text
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini para identificar exercícios: {e}")
        return "ERRO_NA_IDENTIFICACAO"

def parsear_exercicios_do_gemini(texto_gemini):
    exercicios_parseados = []
    if texto_gemini == "ERRO_NA_IDENTIFICACAO" or "Nenhuma questão encontrada." in texto_gemini:
        return []

    linhas = texto_gemini.strip().split('\n')
    for linha in linhas:
        if linha.strip().startswith(tuple(f"{i}." for i in range(1, 100))):
            partes = linha.split('.', 1)
            if len(partes) > 1:
                exercicios_parseados.append(partes[1].strip())
            else:
                exercicios_parseados.append(linha.strip())
        else:
            if exercicios_parseados:
                exercicios_parseados[-1] += "\n" + linha.strip()

    exercicios_parseados = [ex.strip() for ex in exercicios_parseados if ex.strip()]
    return exercicios_parseados

def resolver_exercicio_com_gemini(exercicio_texto, model_gemini):
    prompt_resolucao = f"""
    Resolva o seguinte exercício e explique cada passo detalhadamente, como se estivesse ensinando alguém.
    Mantenha a resposta clara e focada apenas na resolução e explicação:

    {exercicio_texto}

    Certifique-se de mostrar todos os cálculos e a lógica por trás de cada etapa.
    """
    try:
        response = model_gemini.generate_content(prompt_resolucao)
        return response.text
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini para este exercício: {e}")
        return "Não foi possível gerar a resolução para este exercício."

def gerar_exercicios_similares_com_gemini(exercicio_original, resolucao_original, model_gemini, quantidade=2):
    prompt_similares = f"""
    Com base no seguinte exercício e sua resolução, crie {quantidade} novos exercícios que abordem o mesmo conceito
    ou tipo de problema, mas com valores, cenários ou dados diferentes.
    Não inclua as soluções para os novos exercícios.
    Apresente cada novo exercício como uma lista numerada clara.

    Exercício Original:
    ---
    {exercicio_original}
    ---

    Resolução do Exercício Original (para contexto do conceito):
    ---
    {resolucao_original}
    ---

    Por favor, formate os novos exercícios da seguinte forma:
    1. [Texto do Exercício Similar 1]
    2. [Texto do Exercício Similar 2]
    ...
    """
    try:
        response = model_gemini.generate_content(prompt_similares)
        return response.text
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini para gerar exercícios similares: {e}")
        return "Não foi possível gerar exercícios similares."

# --- ROTAS FLASK ---

@app.route('/')
def index():
    # Limpa a sessão ao iniciar uma nova interação
    session.clear()
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf_file' not in request.files:
        return redirect(request.url)

    file = request.files['pdf_file']
    file_type = request.form.get('pdf_type')

    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        texto_do_pdf = ""
        if file_type == 'text_only':
            texto_do_pdf = extrair_texto_pypdf2(filepath)
        elif file_type == 'mixed_content':
            texto_do_pdf = extrair_texto_pdfplumber(filepath)
        elif file_type == 'scanned_book' or file_type == 'scanned_handwritten':
            texto_do_pdf = extrair_texto_ocr(filepath) # Ainda é um placeholder

        if not texto_do_pdf or texto_do_pdf.strip() == "Texto não extraído: OCR não implementado.":
            return render_template('error.html', message="Erro ao extrair texto do PDF ou tipo de PDF não suportado ainda para OCR.")

        # O Gemini identifica TODAS as questões aqui, sem resolver ainda
        texto_exercicios_do_gemini = identificar_exercicios_com_gemini(texto_do_pdf, model)
        exercicios_identificados = parsear_exercicios_do_gemini(texto_exercicios_do_gemini)

        if not exercicios_identificados:
            return render_template('error.html', message="O Gemini não conseguiu identificar nenhuma questão no PDF.")

        # Armazena todas as questões identificadas na sessão
        # Precisamos de um formato que possa ser serializado em JSON
        # Armazenamos como { 'id': index, 'texto': texto_questao, 'respondida': False }
        session['all_exercicios'] = [{'id': i, 'texto': ex, 'respondida': False} for i, ex in enumerate(exercicios_identificados)]
        session['exercicios_respondidos_ids'] = [] # Lista para controle de IDs respondidos

        # Redireciona para a página de seleção de questões
        return redirect(url_for('select_questions'))
    else:
        return render_template('error.html', message="Tipo de arquivo não permitido ou arquivo ausente.")


@app.route('/select_questions', methods=['GET', 'POST'])
def select_questions():
    if 'all_exercicios' not in session:
        return redirect(url_for('index')) # Redireciona se não houver exercícios na sessão

    all_exercicios = session['all_exercicios']
    num_total_exercicios = len(all_exercicios)
    exercicios_disponiveis = [ex for ex in all_exercicios if not ex['respondida']]
    num_disponiveis = len(exercicios_disponiveis)

    if request.method == 'POST':
        num_questions_str = request.form.get('num_questions')
        selection_mode = request.form.get('selection_mode')

        try:
            num_questions_to_resolve = int(num_questions_str)
            if not (1 <= num_questions_to_resolve <= num_disponiveis):
                raise ValueError("Número de questões inválido.")
        except ValueError:
            return render_template('select_questions.html',
                                   all_exercicios=all_exercicios,
                                   num_disponiveis=num_disponiveis,
                                   error="Por favor, insira um número válido de questões (entre 1 e {}).".format(num_disponiveis))

        exercicios_para_resolver_agora = []
        if selection_mode == 'sequential':
            # Seleciona as primeiras 'num_questions_to_resolve' questões não respondidas
            for ex in all_exercicios:
                if not ex['respondida'] and len(exercicios_para_resolver_agora) < num_questions_to_resolve:
                    exercicios_para_resolver_agora.append(ex)
        elif selection_mode == 'random':
            # Seleciona aleatoriamente 'num_questions_to_resolve' questões não respondidas
            exercicios_para_resolver_agora = random.sample(exercicios_disponiveis, num_questions_to_resolve)

        # Atualiza o status de 'respondida' e a lista de IDs respondidos na sessão
        ids_para_marcar_como_respondidas = [ex['id'] for ex in exercicios_para_resolver_agora]
        for ex in all_exercicios:
            if ex['id'] in ids_para_marcar_como_respondidas:
                ex['respondida'] = True
                session['exercicios_respondidos_ids'].append(ex['id'])

        session['all_exercicios'] = all_exercicios # Salva o estado atualizado
        session['exercicios_respondidos_ids'] = list(set(session['exercicios_respondidos_ids'])) # Remove duplicatas

        # Processa apenas as questões selecionadas
        resultados_atuais = []
        for exercicio_info in exercicios_para_resolver_agora:
            exercicio_original = exercicio_info['texto']
            resolucao_original = resolver_exercicio_com_gemini(exercicio_original, model)

            exercicios_similares_raw = gerar_exercicios_similares_com_gemini(exercicio_original, resolucao_original, model, quantidade=2)
            exercicios_similares_parsed = parsear_exercicios_do_gemini(exercicios_similares_raw)

            resultados_similares = []
            for similar_ex in exercicios_similares_parsed:
                resolucao_similar = resolver_exercicio_com_gemini(similar_ex, model)
                resultados_similares.append({
                    'texto': similar_ex,
                    'resolucao': resolucao_similar
                })

            resultados_atuais.append({
                'id': exercicio_info['id'] + 1, # ID + 1 para começar do 1 na exibição
                'original': exercicio_original,
                'resolucao_original': resolucao_original,
                'similares': resultados_similares
            })

        # Redireciona para a página de resultados com as questões resolvidas AGORA
        return render_template('results.html',
                               results=resultados_atuais,
                               num_exercicios_total=num_total_exercicios,
                               num_exercicios_disponiveis=len([ex for ex in all_exercicios if not ex['respondida']]),
                               exercicios_respondidos_ids=session['exercicios_respondidos_ids'])

    return render_template('select_questions.html',
                           all_exercicios=all_exercicios,
                           num_disponiveis=num_disponiveis)


# Nova rota para exibir exercícios já respondidos (opcional, para visualização do progresso)
@app.route('/answered_questions')
def answered_questions():
    if 'all_exercicios' not in session or 'exercicios_respondidos_ids' not in session:
        return redirect(url_for('index'))

    all_exercicios = session['all_exercicios']
    answered_ids = session['exercicios_respondidos_ids']

    answered_list = [ex for ex in all_exercicios if ex['id'] in answered_ids]

    return render_template('answered_questions.html', answered_list=answered_list)


if __name__ == '__main__':
    app.run(debug=True)