import os
import google.generativeai as genai
from dotenv import load_dotenv # Se você estiver usando .env

# Carrega as variáveis do arquivo .env, se aplicável
load_dotenv()

# --- ADICIONE ESTAS LINHAS PARA DEPURAR ---
api_key_from_env = os.getenv("GOOGLE_API_KEY")
print(f"Valor lido de GOOGLE_API_KEY (os.getenv): {api_key_from_env}")

# Tenta ler diretamente de os.environ (isso vai falhar se não estiver lá, mas é para depurar)
try:
    api_key_from_environ = os.environ["GOOGLE_API_KEY"]
    print(f"Valor lido de GOOGLE_API_KEY (os.environ): {api_key_from_environ}")
except KeyError:
    print("GOOGLE_API_KEY NÃO ENCONTRADA em os.environ. Está configurada no sistema?")
# --- FIM DAS LINHAS DE DEPURACAO ---


# Configura a chave da API a partir da variável de ambiente
# A linha que está causando o erro agora está protegida pelo if abaixo
if api_key_from_env:
    genai.configure(api_key=api_key_from_env)
else:
    print("ERRO: A chave da API 'GOOGLE_API_KEY' não foi encontrada. Por favor, configure-a.")
    exit() # Interrompe o script se a chave não for encontrada

# Escolhe o modelo Gemini
model = genai.GenerativeModel('models/gemini-2.0-flash')

# Restante do seu código...
# --- Texto do Exercício (Exemplo - Você substituirá isso pelo texto do seu PDF) ---
texto_do_exercicio = """
Exercício: Calcule o valor de x na equação 2x + 5 = 15.
"""

# --- Prompt para o Gemini resolver e explicar ---
prompt_para_gemini = f"""
Resolva o seguinte exercício e explique cada passo detalhadamente, como se estivesse ensinando alguém:

{texto_do_exercicio}

Certifique-se de mostrar todos os cálculos e a lógica por trás de cada etapa.
"""

print("--- Enviando o exercício para o Gemini ---")
print(f"Exercício: {texto_do_exercicio.strip()}")

# Envia o prompt ao Gemini
try:
    response = model.generate_content(prompt_para_gemini)

    # Imprime a resposta do Gemini
    print("\n--- Resolução do Gemini ---")
    print(response.text)

except Exception as e:
    print(f"\nOcorreu um erro ao chamar a API do Gemini: {e}")
    print("Verifique sua chave de API e sua conexão com a internet.")