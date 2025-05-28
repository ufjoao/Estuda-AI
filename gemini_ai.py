import os
import google.generativeai as genai

# Configura a chave da API a partir da variável de ambiente
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Escolhe o modelo Gemini (pode ser "gemini-pro" para texto, "gemini-pro-vision" para texto e imagem)
model = genai.GenerativeModel('gemini-pro')

# Texto para enviar ao Gemini
texto_para_gemini = "O que é inteligência artificial?"

# Envia o prompt ao Gemini
print(f"Enviando ao Gemini: '{texto_para_gemini}'")
response = model.generate_content(texto_para_gemini)

# Imprime a resposta do Gemini
print("\nResposta do Gemini:")
print(response.text)