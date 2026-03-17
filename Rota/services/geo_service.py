import requests
import time

HEADERS = {
    "User-Agent": "ProjetoRotaVerto/1.0 (contato@exemplo.com)"
}

def buscar_lat_lng(endereco):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": endereco,
        "format": "json",
        "limit": 1
    }

    for tentativa in range(3):  # retry automático
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)

            if r.status_code == 200 and r.json():
                data = r.json()[0]
                return float(data["lat"]), float(data["lon"])

        except requests.exceptions.RequestException:
            time.sleep(2)  # espera antes de tentar de novo

    return None, None


def geocodificar_ceps(lista_ceps):
    resultados = {}

    for cep in lista_ceps:
        try:
            r = requests.get(
                f"https://viacep.com.br/ws/{cep}/json/",
                headers=HEADERS,
                timeout=10
            )

            if r.status_code != 200:
                continue

            data = r.json()
            if "erro" in data:
                continue

            endereco = f"{data['logradouro']}, {data['localidade']}, {data['uf']}"
            lat, lng = buscar_lat_lng(endereco)

            if lat is not None and lng is not None:
                resultados[cep] = {
                    "endereco": endereco,
                    "lat": lat,
                    "lng": lng
                }

            time.sleep(2)  # MUITO importante (anti-bloqueio)

        except requests.exceptions.RequestException:
            continue

    return resultados
