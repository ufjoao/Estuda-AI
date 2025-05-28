import os
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2 # Ou pdfplumber, ou pymupdf, conforme sua escolha

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configura a chave da API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Escolhe o modelo Gemini
model = genai.GenerativeModel('models/gemini-2.0-flash') # Confirmamos que este modelo funciona para você

def extrair_texto_pdf(caminho_pdf):
    """Extrai todo o texto de um arquivo PDF."""
    texto_completo = ""
    try:
        with open(caminho_pdf, 'rb') as arquivo:
            leitor_pdf = PyPDF2.PdfReader(arquivo)
            for pagina in leitor_pdf.pages:
                texto_completo += pagina.extract_text() + "\n" # Adiciona quebra de linha entre páginas
    except Exception as e:
        print(f"Erro ao extrair texto do PDF: {e}")
        return None
    return texto_completo

def identificar_exercicios_com_gemini(texto_completo_do_pdf, model_gemini):
    """
    Usa o Gemini para identificar, extrair e formatar os exercícios.
    """
    # AQUI ESTÁ A PARTE CHAVE DA SUA IDEIA: O PROMPT PARA O GEMINI
    prompt_identificacao = f"""
    Dado o seguinte texto extraído de um documento, identifique e extraia todas as questões ou exercícios.
    Para cada questão identificada, forneça apenas o texto da questão, sem as soluções ou explicações.
    Liste as questões em uma lista numerada.

    Formato de saída desejado:
    1. [Texto da primeira questão]
    2. [Texto da segunda questão]
    3. [Texto da terceira questão]
    ...

    Se não houver questões claras, responda 'Nenhuma questão encontrada.'.

    TEXTO:
    ---
    {texto_completo_do_pdf}
    ---
    """
    print("\n--- Enviando texto para o Gemini para identificação de exercícios ---")
    print(f"Texto inicial (primeiros 200 caracteres): {texto_completo_do_pdf[:200]}...")

    try:
        response = model_gemini.generate_content(prompt_identificacao)
        return response.text
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini para identificar exercícios: {e}")
        return "ERRO_NA_IDENTIFICACAO"

def parsear_exercicios_do_gemini(texto_gemini):
    """
    Analisa a saída do Gemini para extrair uma lista de exercícios.
    Assume que o Gemini retornou uma lista numerada.
    """
    exercicios_parseados = []
    if texto_gemini == "ERRO_NA_IDENTIFICACAO" or "Nenhuma questão encontrada." in texto_gemini:
        return []

    linhas = texto_gemini.strip().split('\n')
    for linha in linhas:
        # Acha linhas que começam com "número. "
        if linha.strip().startswith(tuple(f"{i}." for i in range(1, 100))): # Suporta até 99 exercícios
            # Remove o "número. " do início da linha
            partes = linha.split('.', 1) # Divide apenas na primeira ocorrência do ponto
            if len(partes) > 1:
                exercicios_parseados.append(partes[1].strip())
            else: # Caso a linha seja só um número e ponto, ou tenha outro formato
                exercicios_parseados.append(linha.strip())
        else: # Se não for uma linha numerada, pode ser continuação do exercício anterior
            if exercicios_parseados: # Se já tem algum exercício, adiciona como continuação
                exercicios_parseados[-1] += "\n" + linha.strip()
            # Senão, ignora a linha (pode ser introdução, etc.)

    # Refinamento: remover linhas vazias extras e espaços em branco
    exercicios_parseados = [ex.strip() for ex in exercicios_parseados if ex.strip()]
    return exercicios_parseados


def resolver_exercicio_com_gemini(exercicio_texto, model_gemini):
    """Envia um exercício ao Gemini para resolução."""
    prompt_resolucao = f"""
    Resolva o seguinte exercício e explique cada passo detalhadamente, como se estivesse ensinando alguém.
    Mantenha a resposta clara e focada apenas na resolução e explicação:

    {exercicio_texto}

    Certifique-se de mostrar todos os cálculos e a lógica por trás de cada etapa.
    """
    print(f"\n--- Enviando o exercício para resolução pelo Gemini ---")
    print(f"Exercício: {exercicio_texto[:100]}...") # Mostra apenas o início do exercício

    try:
        response = model_gemini.generate_content(prompt_resolucao)
        return response.text
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini para este exercício: {e}")
        return "Não foi possível gerar a resolução para este exercício."

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    caminho_do_pdf = input("Por favor, digite o caminho completo do arquivo PDF: ")

    texto_do_pdf = extrair_texto_pdf(caminho_do_pdf)

    if texto_do_pdf:
        # 1. Gemini identifica e formata os exercícios
        texto_exercicios_do_gemini = identificar_exercicios_com_gemini(texto_do_pdf, model)

        # 2. Nosso código Python parseia a saída do Gemini
        exercicios_identificados = parsear_exercicios_do_gemini(texto_exercicios_do_gemini)

        if exercicios_identificados:
            print(f"\n--- {len(exercicios_identificados)} Exercício(s) Identificado(s) pelo Gemini ---")
            for i, exercicio in enumerate(exercicios_identificados):
                print(f"\n--- Processando Exercício {i+1} ---")
                print(f"Texto da Questão:\n{exercicio}")

                # 3. Para cada exercício identificado, Gemini gera a resolução
                resolucao = resolver_exercicio_com_gemini(exercicio, model)
                print(f"\n--- Resolução Gemini para o Exercício {i+1} ---")
                print(resolucao)
                print("\n" + "="*50 + "\n") # Separador para o próximo exercício
        else:
            print("\nO Gemini não conseguiu identificar questões com o padrão esperado.")
            print("Verifique o texto do PDF e o prompt de identificação.")
    else:
        print("\nNão foi possível processar o PDF ou o texto está vazio.")