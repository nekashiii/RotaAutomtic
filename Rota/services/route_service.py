import urllib.parse

def gerar_link_google_maps(destinos, origem):
    # A base do link para rotas
    base_url = "https://www.google.com/maps/dir/"
    
    # Codifica a origem (ex: seu CEP de Guarulhos)
    link = base_url + urllib.parse.quote(origem) + "/"
    
    for destino in destinos:
        # IMPORTANTE: Se o destino for o CNPJ lido, removemos caracteres que o Maps
        # pode confundir como separadores de rota (como a barra '/' ou pontos)
        # O CNPJ 09.067.201/0001-80 vira 09067201000180
        destino_limpo = destino.replace(".", "").replace("/", "").replace("-", "")
        
        # Adicionamos ao link de forma que o Maps entenda como UM ÚNICO destino
        link += urllib.parse.quote(destino_limpo) + "/"
        
    return link