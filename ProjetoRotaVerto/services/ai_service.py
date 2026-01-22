import os
import base64
from openai import OpenAI

def _get_client() -> OpenAI:
    """
    Cria o client somente quando necessário.
    Isso evita quebrar o deploy no Render quando a OPENAI_API_KEY ainda não está setada.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não está definida no ambiente.")
    return OpenAI(api_key=api_key)


def extrair_cep_da_imagem(caminho_imagem: str) -> str | None:
    """
    Lê a imagem e pede pra IA retornar SOMENTE:
    'RUA X, nºY - BAIRRO, CIDADE, UF'
    ou None se falhar.
    """
    try:
        client = _get_client()

        with open(caminho_imagem, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        prompt = (
            "Você vai ler uma guia 'ORDEM DE COLETA'.\n"
            "Retorne APENAS o ENDEREÇO DE COLETA (logradouro + número) e o BAIRRO.\n"
            "Formate assim exatamente:\n"
            "RUA ..., nº... - BAIRRO, SAO PAULO, SP\n\n"
            "Regras:\n"
            "- NÃO escreva mais nada.\n"
            "- NÃO inclua CEP.\n"
            "- NÃO inclua 'Endereço Coleta' no texto.\n"
            "- Se não achar, retorne vazio.\n"
        )

        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{img_b64}",
                        },
                    ],
                }
            ],
        )

        texto = (resp.output_text or "").strip()

        if not texto:
            return None

        # garante que retorna só uma linha
        texto = texto.splitlines()[0].strip()

        # evita retornos esquisitos
        if len(texto) < 8:
            return None

        return texto

    except Exception as e:
        print("❌ Erro IA (ai_service):", e)
        return None
