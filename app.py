import os
import random
import json
from flask import Flask, render_template, request, redirect, url_for, session
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2
import pdfplumber
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma_chave_secreta_muito_segura_e_aleatoria_aqui_para_a_sua_aplicacao'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf'}

session_data_store = {} # Dicionário global para armazenar dados da sessão no servidor

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    Mantenha a resposta clara e focada apenas na resolução e explicação.
    **Por favor, formate sua resposta usando Markdown**, incluindo cabeçalhos, listas, negrito, itálico e blocos de código para fórmulas ou cálculos, quando apropriado.

    Exercício:
    ---
    {exercicio_texto}
    ---

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
    **Por favor, apresente cada novo exercício como uma lista numerada, formatado em Markdown, com negrito ou itálico para destacar termos importantes.**

    Exercício Original:
    ---
    {exercicio_original}
    ---

    Resolução do Exercício Original (para contexto do conceito):
    ---
    {resolucao_original}
    ---

    Por favor, formate os novos exercícios da seguinte forma em Markdown:
    1. [Texto do Exercício Similar 1, com Markdown]
    2. [Texto do Exercício Similar 2, com Markdown]
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
    if 'session_id' in session and session['session_id'] in session_data_store:
        del session_data_store[session['session_id']]
    session.clear()
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf_file' not in request.files:
        print("DEBUG: 'pdf_file' não encontrado no request.files.")
        return redirect(request.url)

    file = request.files['pdf_file']
    file_type = request.form.get('pdf_type')

    if file.filename == '':
        print("DEBUG: Nome do arquivo vazio.")
        return render_template('error.html', message="Nenhum arquivo PDF selecionado.")

    if not file or not allowed_file(file.filename):
        print(f"DEBUG: Arquivo não permitido ou ausente. Nome: {file.filename}, Permitido: {allowed_file(file.filename)}")
        return render_template('error.html', message="Tipo de arquivo não permitido (apenas PDFs) ou arquivo ausente.")

    filename = file.filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    print(f"DEBUG: Arquivo salvo em: {filepath}")

    texto_do_pdf = ""
    if file_type == 'text_only':
        print(f"DEBUG: Tentando extrair com PyPDF2 para '{filepath}'")
        texto_do_pdf = extrair_texto_pypdf2(filepath)
    elif file_type == 'mixed_content':
        print(f"DEBUG: Tentando extrair com pdfplumber para '{filepath}'")
        texto_do_pdf = extrair_texto_pdfplumber(filepath)
    elif file_type == 'scanned_book' or file_type == 'scanned_handwritten':
        print(f"DEBUG: Tentando extrair com OCR (placeholder) para '{filepath}'")
        texto_do_pdf = extrair_texto_ocr(filepath)

    print(f"DEBUG: Tipo de PDF selecionado: {file_type}")
    print(f"DEBUG: Texto do PDF (primeiros 200 chars): {texto_do_pdf[:200] if texto_do_pdf else 'Nenhum texto extraído'}")

    if not texto_do_pdf or texto_do_pdf.strip() == "Texto não extraído: OCR não implementado.":
        print(f"DEBUG: Condição de erro de extração ativada. Texto extraído: {texto_do_pdf}")
        return render_template('error.html', message="Erro ao extrair texto do PDF ou tipo de PDF não suportado ainda para OCR.")

    texto_exercicios_do_gemini = identificar_exercicios_com_gemini(texto_do_pdf, model)
    exercicios_identificados = parsear_exercicios_do_gemini(texto_exercicios_do_gemini)

    if not exercicios_identificados:
        print("DEBUG: Gemini não identificou questões.")
        return render_template('error.html', message="O Gemini não conseguiu identificar nenhuma questão no PDF.")

    current_session_id = str(uuid.uuid4())
    session['session_id'] = current_session_id

    session_data_store[current_session_id] = {
        'all_exercicios': [{'id': i, 'texto': ex, 'respondida': False, 'resolucao': None, 'similares': []} for i, ex in enumerate(exercicios_identificados)], # NOVO: Adiciona campos para resolucao e similares aqui
        'exercicios_respondidos_ids': []
    }
    print(f"DEBUG: Dados da sessão armazenados em session_data_store[{current_session_id}]")

    print("DEBUG: Redirecionando para select_questions.")
    return redirect(url_for('select_questions'))


@app.route('/select_questions', methods=['GET', 'POST'])
def select_questions():
    current_session_id = session.get('session_id')
    if not current_session_id or current_session_id not in session_data_store:
        print("DEBUG: select_questions - ID de sessão não encontrado ou inválido. Redirecionando para index.")
        return redirect(url_for('index'))

    session_data = session_data_store[current_session_id]
    all_exercicios = session_data['all_exercicios']
    exercicios_respondidos_ids = session_data['exercicios_respondidos_ids']

    num_total_exercicios = len(all_exercicios)
    exercicios_disponiveis = [ex for ex in all_exercicios if not ex['respondida']]
    num_disponiveis = len(exercicios_disponiveis)

    if request.method == 'POST':
        num_questions_str = request.form.get('num_questions')
        selection_mode = request.form.get('selection_mode')

        print(f"DEBUG: select_questions - POST recebido. Questões a resolver: {num_questions_str}, Modo: {selection_mode}")

        try:
            num_questions_to_resolve = int(num_questions_str)
            if not (1 <= num_questions_to_resolve <= num_disponiveis):
                raise ValueError("Número de questões inválido.")
        except ValueError:
            print(f"DEBUG: select_questions - Valor de questões inválido: {num_questions_str}")
            return render_template('select_questions.html',
                                   all_exercicios=all_exercicios,
                                   num_disponiveis=num_disponiveis,
                                   error="Por favor, insira um número válido de questões (entre 1 e {}).".format(num_disponiveis))

        exercicios_para_resolver_agora = []
        if selection_mode == 'sequential':
            for ex in all_exercicios:
                if not ex['respondida'] and len(exercicios_para_resolver_agora) < num_questions_to_resolve:
                    exercicios_para_resolver_agora.append(ex)
        elif selection_mode == 'random':
            exercicios_para_resolver_agora = random.sample(exercicios_disponiveis, num_questions_to_resolve)

        print(f"DEBUG: select_questions - {len(exercicios_para_resolver_agora)} exercícios selecionados para resolução.")

        resultados_atuais = []
        for i, exercicio_info in enumerate(exercicios_para_resolver_agora):
            print(f"DEBUG: select_questions - Iniciando processamento do exercício {i+1}/{num_questions_to_resolve} (ID: {exercicio_info['id']}).")
            exercicio_original = exercicio_info['texto']

            # NOVO: Verifica se a resolução já existe para evitar chamadas duplicadas
            if exercicio_info['resolucao'] is None:
                print(f"DEBUG: select_questions - Chamando Gemini para resolver o exercício original (ID: {exercicio_info['id']}).")
                resolucao_original = resolver_exercicio_com_gemini(exercicio_original, model)
                exercicio_info['resolucao'] = resolucao_original # Salva a resolução no objeto do exercício
                print(f"DEBUG: select_questions - Resolução original do exercício (ID: {exercicio_info['id']}) concluída.")
            else:
                resolucao_original = exercicio_info['resolucao']
                print(f"DEBUG: select_questions - Resolução do exercício (ID: {exercicio_info['id']}) já existente.")


            # NOVO: Removendo a geração de exercícios similares AUTOMATICAMENTE
            # exercicios_similares_raw = gerar_exercicios_similares_com_gemini(exercicio_original, resolucao_original, model, quantidade=2)
            # exercicios_similares_parsed = parsear_exercicios_do_gemini(exercicios_similares_raw)
            # print(f"DEBUG: select_questions - Geração de similares para o exercício (ID: {exercicio_info['id']}) concluída. Encontrados {len(exercicios_similares_parsed)} similares.")

            # resultados_similares = []
            # for j, similar_ex in enumerate(exercicios_similares_parsed):
            #     print(f"DEBUG: select_questions - Chamando Gemini para resolver o exercício similar {j+1} do original (ID: {exercicio_info['id']}).")
            #     resolucao_similar = resolver_exercicio_com_gemini(similar_ex, model)
            #     print(f"DEBUG: select_questions - Resolução do similar {j+1} concluída.")
            #     resultados_similares.append({
            #         'texto': similar_ex,
            #         'resolucao': resolucao_similar
            #     })
            # exercicio_info['similares'] = resultados_similares # Salva os similares no objeto do exercício

            # Marcar o exercício como respondido e adicionar ao controle de IDs
            if not exercicio_info['respondida']:
                exercicio_info['respondida'] = True
                exercicios_respondidos_ids.append(exercicio_info['id'])

            resultados_atuais.append({
                'id': exercicio_info['id'] + 1,
                'original': exercicio_original,
                'resolucao_original': resolucao_original,
                'similares': exercicio_info['similares'] # Agora virá vazio, ou preenchido sob demanda futura
            })
        
        print(f"DEBUG: select_questions - Todas as {len(resultados_atuais)} resoluções concluídas. Renderizando results.html.")
        
        # Garante que as atualizações sejam salvas de volta no dicionário global (aponta para o mesmo objeto, mas explicitando)
        session_data_store[current_session_id]['all_exercicios'] = all_exercicios
        session_data_store[current_session_id]['exercicios_respondidos_ids'] = list(set(exercicios_respondidos_ids))


        return render_template('results.html',
                               results=resultados_atuais,
                               num_exercicios_total=num_total_exercicios,
                               num_exercicios_disponiveis=len([ex for ex in all_exercicios if not ex['respondida']]),
                               exercicios_respondidos_ids=session_data_store[current_session_id]['exercicios_respondidos_ids'])

    print("DEBUG: select_questions - Método GET. Renderizando select_questions.html.")
    return render_template('select_questions.html',
                           all_exercicios=all_exercicios,
                           num_disponiveis=num_disponiveis)


# --- Rota para gerar exercícios similares sob demanda ---
@app.route('/generate_similar/<int:exercise_id>', methods=['POST'])
def generate_similar(exercise_id):
    current_session_id = session.get('session_id')
    if not current_session_id or current_session_id not in session_data_store:
        return redirect(url_for('index'))

    session_data = session_data_store[current_session_id]
    all_exercicios = session_data['all_exercicios']

    # Encontra o exercício pelo ID (lembre-se que o ID no session_data_store começa do 0)
    exercicio_info = next((ex for ex in all_exercicios if ex['id'] == exercise_id - 1), None)

    if exercicio_info and exercicio_info['resolucao']:
        print(f"DEBUG: Gerando similares para o exercício ID {exercise_id}")
        exercicios_similares_raw = gerar_exercicios_similares_com_gemini(exercicio_info['texto'], exercicio_info['resolucao'], model, quantidade=2)
        exercicios_similares_parsed = parsear_exercicios_do_gemini(exercicios_similares_raw)

        resultados_similares = []
        for j, similar_ex in enumerate(exercicios_similares_parsed):
            print(f"DEBUG: Chamando Gemini para resolver o exercício similar {j+1} do original (ID: {exercise_id}).")
            resolucao_similar = resolver_exercicio_com_gemini(similar_ex, model)
            resultados_similares.append({
                'texto': similar_ex,
                'resolucao': resolucao_similar
            })
        
        exercicio_info['similares'] = resultados_similares # Armazena os similares no objeto do exercício

        # Como os dados do exercício_info estão sendo atualizados, o session_data_store
        # já refletirá as mudanças (pois é um dicionário e objetos são passados por referência)
        # return redirect(url_for('results')) # Talvez redirecionar para a página de resultados ou uma visualização específica
        # Por enquanto, vamos retornar um JSON simples, mas a UX aqui precisará de mais atenção no front-end.
        return json.dumps({
            'status': 'success',
            'exercise_id': exercise_id,
            'similares': resultados_similares
        }), 200, {'Content-Type': 'application/json'}
    else:
        print(f"DEBUG: Falha ao gerar similares para o exercício ID {exercise_id}. Resolução não encontrada.")
        return json.dumps({
            'status': 'error',
            'message': 'Exercício ou resolução não encontrada para gerar similares.'
        }), 400, {'Content-Type': 'application/json'}


@app.route('/answered_questions')
def answered_questions():
    current_session_id = session.get('session_id')
    if not current_session_id or current_session_id not in session_data_store:
        return redirect(url_for('index'))

    session_data = session_data_store[current_session_id]
    all_exercicios = session_data['all_exercicios']
    exercicios_respondidos_ids = session_data['exercicios_respondidos_ids']

    answered_list = [ex for ex in all_exercicios if ex['id'] in exercicios_respondidos_ids]

    return render_template('answered_questions.html', answered_list=answered_list)


if __name__ == '__main__':
    app.run(debug=True)