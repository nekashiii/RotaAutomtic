import base64
import os
import json
from openai import OpenAI

client = OpenAI()


def _guess_mime(path: str) -> str:
    ext = os.path.splitext(path.lower())[1]
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    # fallback seguro
    return "image/jpeg"


def _to_data_url(path: str) -> str:
    mime = _guess_mime(path)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _parse_json_loose(txt: str):
    if not txt:
        return None
    txt = txt.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(txt)
    except Exception:
        # tenta extrair o primeiro JSON no meio do texto
        a = txt.find("{")
        b = txt.rfind("}")
        if a != -1 and b != -1 and b > a:
            try:
                return json.loads(txt[a:b + 1])
            except Exception:
                return None
    return None


def extrair_cep_da_imagem(caminho_img: str) -> str | None:
    """
    Retorna uma string pronta pro Google Maps no formato:
    "LOGRADOURO, NUMERO - BAIRRO, SAO PAULO, SP"
    ou None.
    """
    try:
        data_url = _to_data_url(caminho_img)

        prompt = """
Você vai receber uma foto de uma guia de coleta (ordem de coleta).

Tarefa:
- Encontre o campo "Endereço Coleta" (pode aparecer como "Endereco Coleta").
- Extraia APENAS:
  1) logradouro + número
  2) bairro (linha logo abaixo)

Responda SOMENTE em JSON neste formato:
{
  "logradouro_numero": "RUA GANGES, 635",
  "bairro": "VILA CARRAO"
}

Regras:
- Ignore CNPJ, telefone, datas, destinatário, CEP, cidade/UF.
- Se não encontrar com segurança, responda: null
"""

        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    # ✅ formato correto: input_image com image_url (data URL)
                    {"type": "input_image", "image_url": data_url},
                ],
            }],
            temperature=0,
        )

        txt = (resp.output_text or "").strip()
        if not txt or txt.lower() == "null":
            return None

        obj = _parse_json_loose(txt)
        if not obj:
            return None

        logradouro_numero = (obj.get("logradouro_numero") or "").strip()
        bairro = (obj.get("bairro") or "").strip()

        if len(logradouro_numero) < 6 or len(bairro) < 3:
            return None

        # ✅ pronto pro Maps (você já limita pra SP no geocoder depois)
        return f"{logradouro_numero} - {bairro}, SAO PAULO, SP"

    except Exception as e:
        print("❌ Erro IA (ai_service):", e)
        return None
