import os
import re
import time
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from services.ai_service import extrair_cep_da_imagem
from services.cep_service import extrair_ceps_texto
from services.route_service import gerar_link_google_maps


BASE_DIR = Path(__file__).resolve().parent

# Detecta Render (PORT costuma existir lá)
IS_RENDER = bool(os.getenv("RENDER")) or bool(os.getenv("PORT"))

# Upload seguro: no Render use /tmp (gravável). Local pode ser pasta do projeto.
UPLOAD_FOLDER = Path("/tmp/uploads") if IS_RENDER else (BASE_DIR / "temp_uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Debug (deixe por enquanto)
print("IS_RENDER:", IS_RENDER)
print("UPLOAD_FOLDER:", str(UPLOAD_FOLDER))
print("OPENAI_API_KEY carregada?", bool(os.getenv("OPENAI_API_KEY")))

app = Flask(__name__)

BASE_ENDERECO = "Rua Angical, Guarulhos, SP, Brasil"
geolocator = Nominatim(user_agent="rota_inteligente_v1")


# ---------- HELPERS ----------

def _limpar_endereco(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\b(n[º°o]?\.?)\s*", "", s, flags=re.IGNORECASE)

    # remove bairro para GEOCODE
    if " - " in s:
        s = s.split(" - ", 1)[0].strip()

    s = re.sub(r"\s*,\s*", ", ", s).strip(" ,")
    return s


def formatar_para_google_maps(endereco: str) -> str:
    s = (endereco or "").strip()
    s = re.sub(r"\s+", " ", s)

    # remove nº
    s = re.sub(r"\b(n[º°o]?\.?)\s*", "", s, flags=re.IGNORECASE)

    # troca hífen por vírgula (Google prefere)
    s = s.replace(" - ", ", ")

    s = re.sub(r"\s*,\s*", ", ", s).strip(" ,")

    # garante SP + Brasil
    if "brasil" not in s.lower():
        if re.search(r"\bsp\b", s.lower()):
            s = f"{s}, Brasil"
        else:
            s = f"{s}, São Paulo, SP, Brasil"

    return s


def ordenar_da_mais_longe_para_perto(origem_texto, destinos):
    loc_origem = geolocator.geocode(origem_texto, timeout=15)
    if not loc_origem:
        print("❌ Não consegui localizar a origem:", origem_texto)
        return []

    origem = (loc_origem.latitude, loc_origem.longitude)
    lista_final = []

    for destino_original in destinos:
        destino = _limpar_endereco(destino_original)

        distancia = 0
        loc = None

        tentativas = [
            f"{destino}, São Paulo, SP, Brasil",
            f"{destino}, SP, Brasil",
            f"{destino}, Brasil",
        ]

        for q in tentativas:
            try:
                loc = geolocator.geocode(q, timeout=15)
                if loc:
                    break
            except Exception as e:
                print("⚠️ erro geocode:", e)

            time.sleep(0.8)

        if loc:
            ponto = (loc.latitude, loc.longitude)
            distancia = geodesic(origem, ponto).km
        else:
            print("❌ Nominatim NÃO achou:", destino_original)

        lista_final.append({
            "endereco": destino_original,
            "distancia": distancia
        })

        time.sleep(1.1)

    lista_final.sort(key=lambda x: x["distancia"], reverse=True)
    return lista_final


# ---------- ROTAS ----------

@app.route("/", methods=["GET", "POST"])
def index():
    link_maps = None
    erro = None
    lista_ordenada = []

    if request.method == "POST":
        print("\n📩 POST RECEBIDO")
        print("📂 files keys:", list(request.files.keys()))

        destinos = []

        # ---- TEXTO ----
        texto = request.form.get("ceps", "")
        if texto.strip():
            extraidos = extrair_ceps_texto(texto)
            print("📄 TEXTO EXTRAÍDO:", extraidos)
            destinos.extend(extraidos)

        # ---- IMAGENS ----
        fotos = request.files.getlist("fotos[]")
        print("📸 qtd fotos:", len(fotos), "| nomes:", [f.filename for f in fotos])

        for foto in fotos:
            if not foto or not foto.filename:
                continue

            nome_seguro = secure_filename(foto.filename)

            # salva usando Path (e converte pra str onde precisa)
            caminho = UPLOAD_FOLDER / nome_seguro
            foto.save(str(caminho))

            try:
                resultado = extrair_cep_da_imagem(str(caminho))
                print("🧠 IA retorno:", resultado)

                if resultado and len(resultado.strip()) > 8:
                    destinos.append(resultado.strip())

            except Exception as e:
                print("❌ ERRO IA:", e)

            finally:
                try:
                    caminho.unlink(missing_ok=True)  # apaga arquivo
                except Exception:
                    pass

        destinos = list(dict.fromkeys(destinos))
        print("📌 destinos finais:", destinos)

        if not destinos:
            erro = "Nenhum endereço foi identificado nas fotos/texto."
        else:
            lista_ordenada = ordenar_da_mais_longe_para_perto(BASE_ENDERECO, destinos)

            destinos_maps = [formatar_para_google_maps(d["endereco"]) for d in lista_ordenada[:9]]
            link_maps = gerar_link_google_maps(destinos_maps, BASE_ENDERECO)

    return render_template(
        "index.html",
        link_maps=link_maps,
        erro=erro,
        lista_ordenada=lista_ordenada
    )


@app.route("/limpar")
def limpar():
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
