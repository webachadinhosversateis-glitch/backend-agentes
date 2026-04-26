from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess, uuid, os, re

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
    except:
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
        raise Exception("API Key não configurada no Railway.")
    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"} if json_mode else None,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.2
    )
    return resp.choices[0].message.content

# ==========================================
# AGENTE 1: INTERPRETADOR (Projetista)
# ==========================================
def agent_interpreter(user_prompt):
    print("🤖 Agente 1: Projetando as formas...")
    system = "Você é um Engenheiro Chefe 3D. Receba o pedido do usuário e converta em instruções matemáticas cruas para um programador OpenSCAD. Diga exatamente quais formas primitivas (cubos, esferas, cilindros, polígonos) usar e quais são os tamanhos em milímetros. Foque na estabilidade e em evitar partes flutuantes."
    return ask_ai(system, user_prompt, json_mode=False)

# ==========================================
# AGENTE 2: PROGRAMADOR (Coder OpenSCAD)
# ==========================================
def agent_scad_coder(math_instructions):
    print("🤖 Agente 2: Escrevendo o código...")
    system = """Você é um programador OpenSCAD rigoroso.
Regras Críticas:
1. Retorne APENAS o código OpenSCAD puro. Sem formatação Markdown. Sem textos explicativos.
2. NUNCA use módulos que não existem. Use apenas primitivas básicas (cube, sphere, cylinder, polyhedron).
3. Para objetos não-geométricos (como facas, chaves, espadas), combine `polyhedron` (para as lâminas) e `cylinder` (para os cabos).
4. Garanta que todas as partes estão coladas usando `translate()`. Não deixe peças voando!"""
    code = ask_ai(system, math_instructions, json_mode=False)
    # Limpa a formatação caso a IA teime em usar markdown
    code = re.sub(r"```[a-z]*", "", code).replace("```", "").strip()
    return code

# ==========================================
# AGENTE 3: CORRETOR DE BUGS (Debugger)
# ==========================================
def agent_error_fixer(bad_code, error_log):
    print("🤖 Agente 3: Encontrei um erro. Corrigindo...")
    system = "Você é um depurador OpenSCAD sênior. O código abaixo tentou compilar mas deu Erro de Sintaxe (Syntax Error). Conserte o código, garanta que chaves e parênteses fecham corretamente. Retorne APENAS o código OpenSCAD corrigido."
    prompt = f"CÓDIGO COM ERRO:\n{bad_code}\n\nERRO DO COMPILADOR:\n{error_log}"
    code = ask_ai(system, prompt, json_mode=False)
    return re.sub(r"```[a-z]*", "", code).replace("```", "").strip()

# ==========================================
# MOTOR DE COMPILAÇÃO
# ==========================================
def compile_scad(scad_code):
    name = str(uuid.uuid4())
    scad_file = f"/tmp/{name}.scad"
    stl_file = f"/tmp/{name}.stl"

    with open(scad_file, "w", encoding="utf-8") as f:
        f.write(scad_code)

    result = subprocess.run(["openscad", "-o", stl_file, scad_file], capture_output=True, text=True)
    
    if result.returncode != 0:
        return False, result.stderr
        
    if not os.path.exists(stl_file) or os.path.getsize(stl_file) == 0:
        return False, "Erro: O arquivo STL gerado está vazio (A matemática do modelo criou um objeto vazio ou invisível)."

    with open(stl_file, "rb") as f:
        data = f.read()
    return True, data

# ==========================================
# PIPELINE DA GERAÇÃO MULTI-AGENTES
# ==========================================
def run_agentic_pipeline(user_prompt):
    math_instructions = agent_interpreter(user_prompt)
    scad_code = agent_scad_coder(math_instructions)
    
    max_retries = 3
    for tentativa in range(max_retries):
        success, result = compile_scad(scad_code)
        if success:
            return result # STL gerado com sucesso
        else:
            error_log = result
            print(f"Erro na tentativa {tentativa + 1}. Chamando o Agente 3...")
            if tentativa < max_retries - 1:
                scad_code = agent_error_fixer(scad_code, error_log)
            else:
                raise Exception(f"A equipe de Agentes falhou após {max_retries} tentativas. Último erro OpenSCAD: {error_log}")

# ==========================================
# ROTAS DO FASTAPI
# ==========================================
@app.get("/")
def home():
    return {"status": "online", "modo": "multi_agent_zero_shot"}

@app.post("/gerar")
async def gerar(req: Request):
    try:
        body = await req.json()
        prompt = body.get("prompt", "")
        
        stl_data = run_agentic_pipeline(prompt)
        
        filename = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")[:30] + ".stl"
        return Response(content=stl_data, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})

@app.post("/melhorar-prompt")
async def route_improve_prompt(req: Request):
    try:
        data = await req.json()
        prompt_original = data.get("prompt", "")
        system_msg = "Você é um engenheiro de modelagem 3D. Reescreva a ideia do usuário em 1 ou 2 frases extremamente detalhadas, focando nas dimensões métricas, simetria e geometria."
        sugestao = ask_ai(system_msg, prompt_original)
        return JSONResponse({"sugestao": sugestao})
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
