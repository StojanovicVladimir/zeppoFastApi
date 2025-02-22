from fastapi import FastAPI, Depends
from routes import router as routes_router


app = FastAPI()

app.include_router(routes_router)
