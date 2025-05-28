import PyPDF2
import os # Para manipulação de caminhos de arquivo

def extrair_texto_pdf(caminho_pdf):
    """
    Extrai texto de um arquivo PDF.

    Args:
        caminho_pdf (str): O caminho para o arquivo PDF.

    Returns:
        str: O texto extraído do PDF, ou None se ocorrer um erro.
    """
    try:
        texto_completo = ""
        with open(caminho_pdf, 'rb') as arquivo_pdf: # 'rb' = read binary
            leitor_pdf = PyPDF2.PdfReader(arquivo_pdf)
            num_paginas = len(leitor_pdf.pages)
            print(f"O PDF tem {num_paginas} página(s).")

            for pagina_num in range(num_paginas):
                pagina = leitor_pdf.pages[pagina_num]
                texto_completo += pagina.extract_text()
        return texto_completo
    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado em '{caminho_pdf}'")
        return None
    except Exception as e:
        print(f"Ocorreu um erro ao ler o PDF: {e}")
        return None

if __name__ == "__main__":
    # Pede ao usuário para fornecer o caminho do PDF
    caminho_do_arquivo_pdf = input("Por favor, insira o caminho completo para o arquivo PDF: ")

    # Exemplo de como validar se o caminho é para um arquivo PDF (opcional, mas bom)
    if not caminho_do_arquivo_pdf.lower().endswith(".pdf"):
        print("O caminho fornecido não parece ser de um arquivo PDF. Certifique-se de que termina com '.pdf'")
    elif not os.path.isfile(caminho_do_arquivo_pdf):
         print(f"O arquivo especificado não foi encontrado em: {caminho_do_arquivo_pdf}")
    else:
        print(f"\nExtraindo texto de: {caminho_do_arquivo_pdf}\n")
        texto_extraido = extrair_texto_pdf(caminho_do_arquivo_pdf)

        if texto_extraido:
            print("\n--- Texto Extraído ---")
            print(texto_extraido)
            print("----------------------\n")

            # Opcional: Salvar o texto em um arquivo .txt
            nome_arquivo_saida = "texto_extraido_do_pdf.txt"
            with open(nome_arquivo_saida, "w", encoding="utf-8") as f_out:
                f_out.write(texto_extraido)
            print(f"Texto também salvo em: {nome_arquivo_saida}")