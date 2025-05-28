import os
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2 # Ou pdfplumber, ou pymupdf, conforme sua escolha

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configura a chave da API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Escolhe o modelo Gemini (modelos Flash são ideais para custo/velocidade)
# Continue usando models/gemini-2.0-flash pois funcionou bem para você.
model = genai.GenerativeModel('models/gemini-2.0-flash')

def extrair_texto_pdf(caminho_pdf):
    """Extrai todo o texto de um arquivo PDF."""
    texto_completo = ""
    try:
        with open(caminho_pdf, 'rb') as arquivo:
            leitor_pdf = PyPDF2.PdfReader(arquivo)
            for pagina in leitor_pdf.pages:
                texto_completo += pagina.extract_text() + "\n"
    except Exception as e:
        print(f"Erro ao extrair texto do PDF: {e}")
        return None
    return texto_completo

def identificar_exercicios_com_gemini(texto_completo_do_pdf, model_gemini):
    """
    Usa o Gemini para identificar, extrair e formatar os exercícios.
    """
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
    """Envia um exercício ao Gemini para resolução."""
    prompt_resolucao = f"""
    Resolva o seguinte exercício e explique cada passo detalhadamente, como se estivesse ensinando alguém.
    Mantenha a resposta clara e focada apenas na resolução e explicação:

    {exercicio_texto}

    Certifique-se de mostrar todos os cálculos e a lógica por trás de cada etapa.
    """
    print(f"\n--- Enviando o exercício para resolução pelo Gemini ---")
    print(f"Exercício: {exercicio_texto[:100]}...")

    try:
        response = model_gemini.generate_content(prompt_resolucao)
        return response.text
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini para este exercício: {e}")
        return "Não foi possível gerar a resolução para este exercício."

# NOVA FUNÇÃO PARA GERAR EXERCÍCIOS SIMILARES
def gerar_exercicios_similares_com_gemini(exercicio_original, resolucao_original, model_gemini, quantidade=3):
    """
    Usa o Gemini para criar exercícios similares com base no original e sua resolução.
    """
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
    3. [Texto do Exercício Similar 3]
    ...
    """
    print(f"\n--- Gerando {quantidade} exercícios similares com Gemini ---")
    print(f"Baseado em: {exercicio_original[:50]}...")

    try:
        response = model_gemini.generate_content(prompt_similares)
        return response.text
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini para gerar exercícios similares: {e}")
        return "Não foi possível gerar exercícios similares."

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

                # 4. (NOVO) Gerar exercícios similares
                exercicios_similares_raw = gerar_exercicios_similares_com_gemini(exercicio, resolucao, model, quantidade=2) # Gerar 2 similares por exemplo
                # Podemos usar a mesma lógica de parsear se a saída for numerada
                exercicios_similares_parsed = parsear_exercicios_do_gemini(exercicios_similares_raw)

                if exercicios_similares_parsed:
                    print(f"\n--- Exercícios Similares para o Exercício {i+1} ---")
                    for j, similar_ex in enumerate(exercicios_similares_parsed):
                        print(f"  {j+1}. {similar_ex}")
                else:
                    print("\n  Não foi possível gerar ou parsear exercícios similares.")

                print("\n" + "="*50 + "\n") # Separador para o próximo exercício
        else:
            print("\nO Gemini não conseguiu identificar questões com o padrão esperado.")
            print("Verifique o texto do PDF e o prompt de identificação.")
    else:
        print("\nNão foi possível processar o PDF ou o texto está vazio.")

        exercicios_similares_raw = gerar_exercicios_similares_com_gemini(exercicio, resolucao, model, quantidade=2) # Gerar 2 similares por exemplo
exercicios_similares_parsed = parsear_exercicios_do_gemini(exercicios_similares_raw)

if exercicios_similares_parsed:
    print(f"\n--- Exercícios Similares para o Exercício {i+1} ---")
    for j, similar_ex in enumerate(exercicios_similares_parsed):
        print(f"  {j+1}. {similar_ex}")
        # NOVO: Resolver o exercício similar gerado
        resolucao_similar = resolver_exercicio_com_gemini(similar_ex, model)
        print(f"\n  --- Resolução para o Exercício Similar {j+1} ---")
        print(resolucao_similar)
else:
    print("\n  Não foi possível gerar ou parsear exercícios similares.")

print("\n" + "="*50 + "\n") # Separador para o próximo exercício