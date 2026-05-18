from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import router as auth_router
from app.routes.products import router as products_router
from app.routes.recommendations import router as recommendations_router

app = FastAPI(
    title="Dynamic Pricing Intelligence Dashboard",
    description="AI powered pricing recommendations with human-in-the-loop approval",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(recommendations_router)


@app.get("/health")
def health_check():
    return {"status" : "Ok"}

