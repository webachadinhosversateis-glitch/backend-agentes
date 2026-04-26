from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json, re, asyncio
import urllib.request
import urllib.error

TRIPO_API_KEY = "tsk_yM5te_C_T33v2KfSuCX_IdMDELB2hKzdyL5RnX_aJp5"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def generate_tripo_model(prompt):
    url = "https://api.tripo3d.ai/v2/openapi/task"
    headers = {
        "Authorization": f"Bearer {TRIPO_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = json.dumps({
        "type": "text_to_model",
        "prompt": prompt
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            create_res = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise Exception(f"Erro na API Tripo: {e.read().decode('utf-8')}")
        
    task_id = create_res.get("data", {}).get("task_id")
    if not task_id:
        raise Exception("API não retornou ID de tarefa.")
        
    print(f"Tarefa {task_id} criada.")
    
    model_url = None
    poll_url = f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"
    poll_req = urllib.request.Request(poll_url, headers=headers, method="GET")
    
    for attempt in range(60):
        await asyncio.sleep(2)
        try:
            with urllib.request.urlopen(poll_req) as poll_res:
                data = json.loads(poll_res.read().decode("utf-8")).get("data", {})
                status = data.get("status")
                
                if status == "success":
                    model_url = data.get("result", {}).get("model", {}).get("url")
                    break
                elif status in ["failed", "cancelled", "unknown"]:
                    raise Exception("A geração do modelo falhou.")
        except Exception:
            continue
            
    if not model_url:
        raise Exception("Tempo limite esgotado.")
        
    try:
        with urllib.request.urlopen(model_url) as glb_response:
            return glb_response.read()
    except Exception as e:
        raise Exception("Erro ao baixar o arquivo GLB.")

@app.get("/")
def home():
    return {"status": "online"}

@app.post("/gerar")
async def gerar(req: Request):
    try:
        body = await req.json()
        prompt = body.get("prompt", "")
        if not prompt:
            return JSONResponse(status_code=400, content={"erro": "Prompt vazio."})
        
        glb_data = await generate_tripo_model(prompt)
        
        filename = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")[:30] + ".glb"
        return Response(
            content=glb_data, 
            media_type="model/gltf-binary", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})

@app.post("/melhorar-prompt")
async def route_improve_prompt(req: Request):
    try:
        data = await req.json()
        prompt_original = data.get("prompt", "")
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            system_msg = "Você é tradutor. Transforme em prompt em INGLÊS focado em textura (ex: 'A highly detailed 3D model...'). Retorne SÓ o texto."
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt_original}],
                temperature=0.4
            )
            return JSONResponse({"sugestao": resp.choices[0].message.content.replace("\"", "")})
        else:
            return JSONResponse({"sugestao": f"A highly detailed 3D model of {prompt_original}, 8k resolution"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
