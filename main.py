from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import uuid
import os
import json
import re

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ask_ai(system, user, json_mode=False):
    if not client:
        raise Exception("OPENAI_API_KEY não encontrada no Railway")

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
    base = base.strip("_")[:50]

    if not base:
        base = "modelo_gerado"

    return f"{base}.stl"


def fallback_scad(prompt):
    prompt = prompt.lower()

    if "borboleta" in prompt:
        return """
        $fn = 64;

        module wing_left() {
            hull() {
                translate([-25, 0, 2]) scale([1.6, 1.0, 0.18]) sphere(r=18);
                translate([-45, 22, 2]) scale([1.1, 0.8, 0.18]) sphere(r=12);
                translate([-43, -22, 2]) scale([1.1, 0.8, 0.18]) sphere(r=12);
            }
        }

        module wing_right() {
            mirror([1, 0, 0]) wing_left();
        }

        union() {
            wing_left();
            wing_right();

            translate([0, 0, 2])
                scale([0.35, 1.6, 0.25])
                sphere(r=18);

            translate([0, 30, 4])
                sphere(r=6);

            translate([-5, 36, 5])
                rotate([0, 0, 25])
                cylinder(h=18, r=1.2);

            translate([5, 36, 5])
                rotate([0, 0, -25])
                cylinder(h=18, r=1.2);
        }
        """

    return """
    union() {
        cube([80, 60, 5]);
        translate([0, 42, 5])
            rotate([65, 0, 0])
            cube([80, 5, 85]);
        translate([0, 8, 5])
            cube([80, 8, 12]);
    }
    """


def interpretation_agent(prompt):
    if not client:
        return {
            "objeto": prompt,
            "funcao": "modelo 3D",
            "tipo": "funcional" if "suporte" in prompt.lower() else "decorativo",
            "estilo": "",
            "partes_obrigatorias": [],
            "dimensoes_estimadas_mm": {},
            "material_recomendado": "PLA",
            "precisao": "basico",
            "complexidade": "baixo",
            "observacoes": ["Fallback sem IA"]
        }

    system = """
Você é um agente interpretador para uma plataforma de modelagem 3D por IA.
Retorne JSON:
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
O campo objeto deve ser curto e bom para nome de arquivo.
"""
    result = ask_ai(system, prompt, json_mode=True)
    return json.loads(result)


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


def engineering_agent(data):
    if not client:
        return {
            "espessura_minima_mm": 2.0,
            "tolerancia_encaixe_mm": 0.3,
            "precisa_suporte": False,
            "tipo_suporte": "",
            "orientacao_impressao": "base na mesa",
            "riscos": [],
            "correcoes_necessarias": [],
            "criterios_validacao": []
        }

    system = """
Você é engenheiro especialista em impressão 3D FDM.
Analise função, resistência, orientação, suportes e imprimibilidade.
Nem todo objeto precisa de base plana. Não destrua o design.
Retorne JSON:
{
  "espessura_minima_mm": 2.0,
  "tolerancia_encaixe_mm": 0.3,
  "precisa_suporte": true,
  "tipo_suporte": "",
  "orientacao_impressao": "",
  "riscos": [],
  "correcoes_necessarias": [],
  "criterios_validacao": []
}
"""
    result = ask_ai(system, json.dumps(data, ensure_ascii=False), json_mode=True)
    return json.loads(result)


def cad_agent(data, engineering):
    if not client:
        return fallback_scad(data.get("objeto", ""))

    system = """
Você é um modelador 3D profissional especialista em OpenSCAD, design industrial e impressão 3D.

Gere SOMENTE código OpenSCAD válido.
Não use markdown. Não explique. Não use bibliotecas externas.

Pense como modelador humano:
- preserve forma, função e aparência;
- não transforme tudo em cubo;
- crie silhueta reconhecível;
- use módulos;
- use union(), difference(), hull(), translate(), rotate(), scale(), mirror(), cylinder(), sphere(), cube();
- use hull() para curvas orgânicas;
- use difference() para furos, encaixes e cavidades;
- use mirror() para simetria;
- use $fn para curvas suaves;
- evite partes soltas;
- use espessura compatível com FDM;
- se for funcional, crie reforços, travas, apoios ou encaixes;
- se for suporte de celular, crie encosto inclinado, trava frontal, estabilidade e espaço para cabo quando fizer sentido;
- nem todo objeto precisa de base plana;
- se precisar de suporte no fatiador, tudo bem, mas reduza overhang extremo;
- o OpenSCAD deve compilar.
"""
    user = {
        "pedido_interpretado": data,
        "engenharia": engineering,
        "objetivo": "modelo reconhecível, imprimível e funcional quando houver função"
    }

    scad = ask_ai(system, json.dumps(user, ensure_ascii=False))
    return clean_scad(scad)


def validation_agent(scad_code, data, engineering):
    if not client:
        return {"valido": True, "problemas": [], "melhorias": [], "parece_atender_pedido": True, "motivo": "Fallback"}

    system = """
Você é validador técnico de OpenSCAD para impressão 3D.
Retorne JSON:
{
  "valido": true,
  "problemas": [],
  "melhorias": [],
  "parece_atender_pedido": true,
  "motivo": ""
}
Não reprove apenas por não ter base plana.
Reprove se for genérico demais ou não parecer atender ao pedido.
"""
    payload = {"scad": scad_code, "requisitos": data, "engenharia": engineering}
    result = ask_ai(system, json.dumps(payload, ensure_ascii=False), json_mode=True)
    return json.loads(result)


def correction_agent(scad_code, data, engineering, validation, compile_error=None):
    if not client:
        return fallback_scad(data.get("objeto", ""))

    system = """
Você é corretor de OpenSCAD.
Retorne SOMENTE código OpenSCAD.
Corrija sintaxe, partes soltas, baixa correspondência visual e erro de compilação.
Não simplifique para cubo. Preserve intenção original.
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


def slicer_agent(data, engineering):
    if not client:
        return {
            "material": "PLA",
            "altura_camada": "0.20 mm",
            "infill": "15%",
            "paredes": "3 loops",
            "suportes": "se necessário",
            "orientacao": "base na mesa",
            "observacoes": []
        }

    system = """
Você é especialista em Bambu Studio, Cura e PrusaSlicer.
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
    payload = {"requisitos": data, "engenharia": engineering}
    result = ask_ai(system, json.dumps(payload, ensure_ascii=False), json_mode=True)
    return json.loads(result)


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
        "filename": filename,
        "ia_ativa": bool(client)
    }

    return stl, metadata, filename


@app.get("/")
def home():
    return {
        "status": "online",
        "ia_ativa": bool(client),
        "mensagem": "API IA 3D multiagente funcionando"
    }


@app.get("/agente")
def agente():
    return {
        "status": "ok",
        "ia_ativa": bool(client),
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
                "X-IA-Ativa": str(metadata["ia_ativa"]),
                "Access-Control-Expose-Headers": "Content-Disposition, X-Tokens-Used, X-Model-Type, X-Precision, X-Filename, X-IA-Ativa"
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
