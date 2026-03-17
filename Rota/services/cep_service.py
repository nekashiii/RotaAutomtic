import re

def extrair_ceps_texto(texto):
    """
    Transforma o texto da caixa de entrada em uma lista de endereços.
    Aceita tanto CEPs quanto nomes de ruas completos.
    """
    if not texto:
        return []
    
    # Divide por linha, remove espaços extras e ignora linhas vazias
    linhas = [linha.strip() for linha in texto.split('\n') if len(linha.strip()) > 3]
    
    return linhas