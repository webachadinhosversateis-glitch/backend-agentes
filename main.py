from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import subprocess
import uuid
import os
import json
import re

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ask_ai(system, user, json_mode=False):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"} if json_mode else None,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.25
    )
    return response.choices[0].message.content


def clean_scad(text):
    text = re.sub(r"```openscad", "", text, flags=re.I)
    text = re.sub(r"```scad", "", text, flags=re.I)
    text = re.sub(r"```", "", text)
    return text.strip()


def generate_filename(data, prompt):
    base = data.get("objeto") or prompt or "modelo_gerado"

    base = base.lower()
    base = base.replace("ç", "c")
    base = base.replace("ã", "a").replace("á", "a").replace("à", "a")
    base = base.replace("é", "e").replace("ê", "e")
    base = base.replace("í", "i")
    base = base.replace("ó", "o").replace("õ", "o").replace("ô", "o")
    base = base.replace("ú", "u")

    base = re.sub(r"[^a-z0-9]+", "_", base)
    base = base.strip("_")
    base = base[:50]

    if not base:
        base = "modelo_gerado"

    return f"{base}.stl"


# ===============================
# 1. AGENTE INTERPRETADOR
# ===============================
def interpretation_agent(prompt):
    system = """
Você é um agente interpretador para uma plataforma de modelagem 3D por IA.

Sua função é transformar o pedido do usuário em requisitos técnicos claros.

Retorne JSON com:
{
  "objeto": "",
  "funcao": "",
  "tipo": "decorativo|funcional|mecanico|artistico",
  "estilo": "",
  "partes_obrigatorias": [],
  "dimensoes_estimadas_mm": {},
  "material_recomendado": "PLA|PETG|ABS|TPU|Resina",
  "precisao": "basico|otimizado|profissional",
  "complexidade": "baixo|medio|alto",
  "observacoes": []
}

Não invente função mecânica se o usuário não pediu.
Se for suporte, encaixe, carga ou peça prática, trate como funcional.
Se for escultura, personagem, animal ou arte, trate como artístico/decorativo.
"""
    result = ask_ai(system, prompt, json_mode=True)
    return json.loads(result)


# ===============================
# 2. AGENTE MONETIZAÇÃO
# ===============================
def monetization_agent(data):
    base = 10

    if data.get("complexidade") == "medio":
        base += 30
    elif data.get("complexidade") == "alto":
        base += 70
    else:
        base += 10

    if data.get("precisao") == "profissional":
        base += 60
    elif data.get("precisao") == "otimizado":
        base += 30
    else:
        base += 10

    if data.get("tipo") in ["funcional", "mecanico"]:
        base += 25

    return base


# ===============================
# 3. AGENTE ENGENHARIA
# ===============================
def engineering_agent(data):
    system = """
Você é um engenheiro mecânico especialista em impressão 3D FDM.

Analise os requisitos do objeto e defina como ele deve ser modelado para funcionar.

Importante:
- Nem todo objeto precisa de base plana.
- Alguns modelos podem ter partes suspensas, desde que a orientação de impressão ou suportes sejam previstos.
- Não force base plana se isso destruir o design.
- Para peça funcional, priorize resistência, encaixe e estabilidade.
- Para peça artística, preserve forma visual sem tornar impossível de imprimir.

Retorne JSON:
{
  "espessura_minima_mm": 2.0,
  "tolerancia_encaixe_mm": 0.3,
  "precisa_suporte": true/false,
  "tipo_suporte": "",
  "orientacao_impressao": "",
  "riscos": [],
  "correcoes_necessarias": [],
  "criterios_validacao": []
}
"""
    result = ask_ai(system, json.dumps(data, ensure_ascii=False), json_mode=True)
    return json.loads(result)


# ===============================
# 4. AGENTE CAD PARAMÉTRICO
# ===============================
def cad_agent(data, engineering):
    system = """
Você é um modelador 3D especialista em OpenSCAD e impressão 3D.

Gere SOMENTE código OpenSCAD válido.

Você deve agir como um modelador 3D real:
- Entender forma, função, estética e impressão.
- Não limitar tudo a cubos.
- Usar cube, cylinder, sphere, hull, union, difference, minkowski, rotate, translate, scale quando fizer sentido.
- Criar volumes reconhecíveis quando o pedido for animal, objeto, suporte, decoração ou peça funcional.
- Não obrigar base plana em tudo.
- Se precisar de suporte, o modelo pode exigir suporte, mas informe isso via geometria/estrutura adequada.
- Evite partes soltas sem conexão estrutural.
- Use espessura mínima adequada.
- Medidas em milímetros.
- O modelo deve compilar no OpenSCAD.
- Não use bibliotecas externas.
- Não escreva explicações.
- Não use markdown.
- Retorne apenas OpenSCAD.

Crie um modelo melhor possível dentro das limitações do OpenSCAD.
"""
    user = {
        "requisitos": data,
        "engenharia": engineering
    }

    scad = ask_ai(system, json.dumps(user, ensure_ascii=False))
    return clean_scad(scad)


# ===============================
# 5. AGENTE VALIDADOR
# ===============================
def validation_agent(scad_code, data, engineering):
    system = """
Você é um validador técnico de modelos OpenSCAD para impressão 3D.

Analise o código e os requisitos.

Retorne JSON:
{
  "valido": true/false,
  "problemas": [],
  "melhorias": [],
  "parece_atender_pedido": true/false,
  "motivo": ""
}

Critérios:
- Compilação provável no OpenSCAD
- Correspondência com o pedido
- Peças conectadas quando necessário
- Espessura mínima
- Orientação de impressão
- Necessidade de suporte aceitável
- Não reprovar apenas por não ter base plana
"""
    payload = {
        "scad": scad_code,
        "requisitos": data,
        "engenharia": engineering
    }

    result = ask_ai(system, json.dumps(payload, ensure_ascii=False), json_mode=True)
    return json.loads(result)


# ===============================
# 6. AGENTE CORRETOR
# ===============================
def correction_agent(scad_code, data, engineering, validation, compile_error=None):
    system = """
Você é um agente corretor de OpenSCAD.

Corrija o código mantendo o pedido original.

Regras:
- Retorne SOMENTE código OpenSCAD.
- Não use markdown.
- Corrija erro de sintaxe, geometria ruim, partes soltas e baixa correspondência visual.
- Não simplifique demais.
- Não transforme tudo em cubo.
- Preserve a intenção do usuário.
- Se houver erro de compilação, corrija.
"""
    payload = {
        "scad_atual": scad_code,
        "requisitos": data,
        "engenharia": engineering,
        "validacao": validation,
        "erro_compilacao": compile_error
    }

    corrected = ask_ai(system, json.dumps(payload, ensure_ascii=False))
    return clean_scad(corrected)


# ===============================
# 7. AGENTE SLICER
# ===============================
def slicer_agent(data, engineering):
    system = """
Você é especialista em Bambu Studio, Cura e PrusaSlicer.

Gere configurações recomendadas de impressão.

Retorne JSON:
{
  "material": "",
  "altura_camada": "",
  "infill": "",
  "paredes": "",
  "suportes": "",
  "orientacao": "",
  "observacoes": []
}
"""
    payload = {
        "requisitos": data,
        "engenharia": engineering
    }

    result = ask_ai(system, json.dumps(payload, ensure_ascii=False), json_mode=True)
    return json.loads(result)


# ===============================
# GERAR STL REAL
# ===============================
def generate_stl(scad_code):
    name = str(uuid.uuid4())
    scad_file = f"/tmp/{name}.scad"
    stl_file = f"/tmp/{name}.stl"

    with open(scad_file, "w", encoding="utf-8") as f:
        f.write(scad_code)

    result = subprocess.run(
        ["openscad", "-o", stl_file, scad_file],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(result.stderr)

    with open(stl_file, "rb") as f:
        return f.read()


# ===============================
# PIPELINE COMPLETO
# ===============================
def run_pipeline(prompt):
    data = interpretation_agent(prompt)
    tokens = monetization_agent(data)
    engineering = engineering_agent(data)

    scad = cad_agent(data, engineering)
    validation = validation_agent(scad, data, engineering)

    if not validation.get("valido") or not validation.get("parece_atender_pedido"):
        scad = correction_agent(scad, data, engineering, validation)

    try:
        stl = generate_stl(scad)
    except Exception as compile_error:
        scad = correction_agent(scad, data, engineering, validation, str(compile_error))
        stl = generate_stl(scad)

    slicer = slicer_agent(data, engineering)
    filename = generate_filename(data, prompt)

    metadata = {
        "tokens": tokens,
        "objeto": data.get("objeto", ""),
        "tipo": data.get("tipo", ""),
        "complexidade": data.get("complexidade", ""),
        "precisao": data.get("precisao", ""),
        "slicer": slicer,
        "filename": filename
    }

    return stl, metadata, filename


# ===============================
# ROTAS
# ===============================
@app.get("/")
def home():
    return {
        "status": "online",
        "mensagem": "API IA 3D multiagente funcionando"
    }


@app.get("/agente")
def agente():
    return {
        "status": "ok",
        "agentes": [
            "interpretação",
            "monetização",
            "engenharia",
            "CAD",
            "validação",
            "correção",
            "slicer",
            "exportação STL"
        ]
    }


@app.post("/gerar")
async def gerar(req: Request):
    body = await req.json()
    prompt = body.get("prompt", "")

    try:
        stl, metadata, filename = run_pipeline(prompt)

        return Response(
            content=stl,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Tokens-Used": str(metadata["tokens"]),
                "X-Model-Type": metadata["tipo"],
                "X-Precision": metadata["precisao"],
                "X-Filename": filename,
                "Access-Control-Expose-Headers": "Content-Disposition, X-Tokens-Used, X-Model-Type, X-Precision, X-Filename"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "erro": "Falha ao gerar STL",
                "detalhe": str(e)
            }
        )


# ===============================
# START
# ===============================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
  
