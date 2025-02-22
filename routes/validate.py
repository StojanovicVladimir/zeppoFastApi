
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.security import HTTPBasic, HTTPBasicCredentials






from urllib.parse import unquote



router = APIRouter()
security = HTTPBasic()



from fastapi import FastAPI, Request
from urllib.parse import unquote
@router.post("/webhook/alert/{apikey}")
async def get_api_key(apikey: str, request: Request, background_tasks: BackgroundTasks):
    from tasks import validate_in_background
   # Access request data
    print("awaiting data")
    print(apikey)
    request_data = {
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "body": unquote((await request.body()).decode("utf-8"))
    }
    
    message = request_data['body']
    name = "Alert: " + apikey
    to = "null"
    validate_in_background.delay( message, name, to)
    return {"detail": "API key validated. Task will be performed in the background."}




@router.post("/validate")
def validate_api_key(message : str, name: str, to: str, background_tasks: BackgroundTasks):
    from tasks import validate_in_background
    validate_in_background.delay( message, name, to)
    return {"detail": "API key validated. Task will be performed in the background."}
    
    
