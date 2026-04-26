from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, time, requests, re

# A SUA CHAVE DA TRIPO ESTÁ AQUI
TRIPO_API_KEY = "tsk_yM5te_C_T33v2KfSuCX_IdMDELB2hKzdyL5RnX_aJp5"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# TRIPO 3D NATIVE INTEGRATION
# ==========================================
def generate_tripo_model(prompt):
    headers = {
        "Authorization": f"Bearer {TRIPO_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Passo 1: Enviar o pedido para a Tripo3D
    payload = {
        "type": "text_to_model",
        "prompt": prompt
    }
    
    print(f"🚀 Enviando prompt para Tripo3D: '{prompt}'")
    create_res = requests.post("https://api.tripo3d.ai/v2/openapi/task", headers=headers, json=payload)
    
    if create_res.status_code != 200:
        raise Exception(f"Erro ao iniciar tarefa na Tripo: {create_res.text}")
        
    task_id = create_res.json().get("data", {}).get("task_id")
    if not task_id:
        raise Exception("A API da Tripo não retornou um ID de tarefa.")
        
    print(f"⏳ Tarefa {task_id} criada. Aguardando a IA esculpir a malha...")
    
    # Passo 2: Polling - Ficar checando a cada 2 segundos se a IA já terminou
    model_url = None
    for attempt in range(60): # Espera no máximo 120 segundos
        time.sleep(2)
        poll_res = requests.get(f"https://api.tripo3d.ai/v2/openapi/task/{task_id}", headers=headers)
        
        if poll_res.status_code != 200:
            continue
            
        data = poll_res.json().get("data", {})
        status = data.get("status")
        
        if status == "success":
            model_url = data.get("result", {}).get("model", {}).get("url")
            break
        elif status in ["failed", "cancelled", "unknown"]:
            raise Exception("A geração do modelo falhou nos servidores da Tripo3D.")
            
    if not model_url:
        raise Exception("Tempo limite esgotado. A Tripo demorou muito para responder.")
        
    # Passo 3: Fazer o download do arquivo .glb final
    print(f"✅ Modelo pronto! Baixando malha colorida...")
    glb_response = requests.get(model_url)
    if glb_response.status_code != 200:
        raise Exception("Erro ao baixar o arquivo GLB da Tripo3D.")
        
    return glb_response.content

# ==========================================
# ROTAS DO FASTAPI
# ==========================================
@app.get("/")
def home():
    return {"status": "online", "modo": "tripo3d_genai_native"}

@app.post("/gerar")
async def gerar(req: Request):
    try:
        body = await req.json()
        prompt = body.get("prompt", "")
        if not prompt:
            return JSONResponse(status_code=400, content={"erro": "Você precisa escrever algo."})
        
        glb_data = generate_tripo_model(prompt)
        
        filename = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")[:30] + ".glb"
        return Response(
            content=glb_data, 
            media_type="model/gltf-binary", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        print("Erro Servidor:", str(e))
        return JSONResponse(status_code=500, content={"erro": str(e)})


@app.post("/melhorar-prompt")
async def route_improve_prompt(req: Request):
    try:
        data = await req.json()
        prompt_original = data.get("prompt", "")
        
        # A Tripo3D gera modelos BEM melhores se o prompt estiver em inglês e for bem descritivo
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            system_msg = "Você é um tradutor especialista em Midjourney/Tripo3D. Pegue o pedido do usuário e transforme num prompt em INGLÊS focado em textura, estilo e material (ex: 'A highly detailed 3D model of a...', '8k resolution', 'physically based rendering'). Retorne APENAS o prompt em inglês."
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt_original}
                ],
                temperature=0.4
            )
            sugestao = resp.choices[0].message.content.replace("\"", "")
            return JSONResponse({"sugestao": sugestao})
        else:
            sugestao = f"A highly detailed 3D model of {prompt_original}, 8k resolution, realistic textures"
            return JSONResponse({"sugestao": sugestao})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
