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

Regras:
- Não invente função mecânica se o usuário não pediu.
- Se for suporte, encaixe, carga ou peça prática, trate como funcional.
- Se for escultura, personagem, animal ou arte, trate como artístico/decorativo.
- Se o pedido for vago, escolha uma interpretação plausível e imprimível.
- O campo "objeto" deve ser curto e útil para virar nome de arquivo.
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
- Para suporte de celular, pense em centro de gravidade, trava frontal, encosto, ângulo e base.
- Para animais/decorativos, pense em silhueta reconhecível, corpo, cabeça, membros, asas, olhos ou detalhes simples.
- Para caixas/organizadores, pense em espessura de parede, cavidade, abertura e cantos arredondados.

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
# 4. AGENTE CAD PARAMÉTRICO AVANÇADO
# ===============================
def cad_agent(data, engineering):
    system = """
Você é um modelador 3D profissional especialista em OpenSCAD, design industrial e impressão 3D.

Sua missão é transformar requisitos técnicos em um modelo 3D imprimível, funcional e visualmente coerente.

Gere SOMENTE código OpenSCAD válido.
Não use markdown.
Não explique nada.
Não use bibliotecas externas.

MENTALIDADE:
- Pense como um modelador 3D humano.
- Entenda a intenção antes de modelar.
- Preserve a função do objeto.
- Preserve a aparência pedida pelo usuário.
- Não transforme tudo em cubo.
- Não simplifique demais.
- Não gere apenas símbolo ou bloco abstrato quando o usuário pedir um objeto reconhecível.
- Se o pedido for amplo, crie uma versão funcional e imprimível plausível.

REGRAS DE MODELAGEM:
- Use medidas em milímetros.
- Use módulos quando o modelo tiver várias partes.
- Use union(), difference(), hull(), translate(), rotate(), scale(), mirror(), cylinder(), sphere() e cube() quando fizer sentido.
- Use hull() para criar formas orgânicas e arredondadas.
- Use difference() para furos, encaixes, cavidades e alívios.
- Use mirror() para simetria quando o objeto pedir isso.
- Use $fn adequado para curvas suaves.
- Evite superfícies infinitamente finas.
- Evite partes soltas desconectadas, salvo se o objeto for propositalmente multipartes.
- Crie espessura mínima compatível com FDM.
- Para objetos funcionais, crie reforços, travas, base, apoios ou encaixes quando necessário.
- Para objetos decorativos/artísticos, preserve silhueta e elementos visuais principais.
- Para suportes, pense em inclinação, centro de gravidade, trava frontal e estabilidade.
- Para caixas/organizadores, pense em paredes, cavidades, espessura e abertura.
- Para animais/personagens, pense em corpo, cabeça, membros, silhueta e detalhes básicos reconhecíveis.
- Para peças mecânicas, pense em tolerância, folga, parede, furo e resistência.

IMPRESSÃO 3D:
- Nem todo objeto precisa de base plana.
- Se uma forma artística exigir suporte, isso é permitido.
- Se suportes forem necessários, reduza ao máximo overhangs extremos.
- Não force base plana se isso destruir o design.
- Oriente mentalmente o objeto para ser impresso com o menor risco possível.
- Crie geometrias conectadas e sólidas.
- O OpenSCAD deve compilar.

QUALIDADE:
- O resultado deve parecer com o pedido.
- O resultado deve ser imprimível.
- O resultado deve ser funcional quando houver função.
- O resultado deve ser melhor que um bloco genérico.

SAÍDA:
Retorne apenas o código OpenSCAD final.
"""
    user = {
        "pedido_interpretado": data,
        "engenharia": engineering,
        "instrucoes_finais": [
            "Gere um modelo coerente com o objeto solicitado.",
            "Não limite a resposta a templates fixos.",
            "Crie geometria paramétrica plausível.",
            "Se o objeto for complexo, faça uma versão simplificada, mas reconhecível e imprimível.",
            "Não use comentários longos.",
            "Não retorne JSON.",
            "Não retorne explicação.",
            "Retorne somente OpenSCAD."
        ]
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
- Compilação provável no OpenSCAD.
- Correspondência com o pedido.
- Peças conectadas quando necessário.
- Espessura mínima.
- Orientação de impressão.
- Necessidade de suporte aceitável.
- Não reprovar apenas por não ter base plana.
- Reprove se o código parecer genérico demais para o pedido.
- Reprove se um pedido artístico virar só cubos simples sem silhueta reconhecível.
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
- Se o validador disse que não parece atender ao pedido, aumente a correspondência visual.
- Se for suporte, mantenha funcionalidade real.
- Se for objeto artístico, melhore silhueta e detalhes reconhecíveis.
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

Leve em conta:
- Tipo do objeto.
- Se é funcional ou decorativo.
- Se precisa de suporte.
- Orientação de impressão recomendada.
- Material recomendado.
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
            "CAD avançado",
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
