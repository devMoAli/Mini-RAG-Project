from fastapi import FastAPI
from routes import base, data, nlp
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings
from contextlib import asynccontextmanager
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    settings = get_settings()

    # 1. Setup Clients
    app.mongodb_connection = AsyncIOMotorClient(settings.MONGODB_URI)
    app.database_client = app.mongodb_connection[settings.MONGODB_DB_NAME]
    # Test the connection on startup 
    try:
        await app.database_client.command("ping")
        print("✅ MongoDB Connected Successfully")
    except Exception as e:
        print(f"❌ MongoDB Connection Failed: {e}")
    llm_factory = LLMProviderFactory(settings)
    vectordb_factory = VectorDBProviderFactory(settings)

    app.generation_client = llm_factory.create(provider=settings.GENERATION_BACKEND)
    app.embedding_client = llm_factory.create(provider=settings.EMBEDDING_BACKEND)

    app.vectordb_client = vectordb_factory.create(provider=settings.VECTORDB_BACKEND)
    app.vectordb_client.connect()

   
    app.state.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )

    
    app.template_parser = app.state.template_parser

    yield

    # --- SHUTDOWN ---
    app.mongodb_connection.close()
    app.vectordb_client.disconnect()


# Initialize App
app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    health_results = {
        "status": "active",
        "database": "disconnected",
        "llm_server": "checking...",
    }

    try:
        # 1. Check MongoDB
        await app.database_client.command("ping")
        health_results["database"] = "connected"

        # 2. Generic LLM Check
        if app.generation_client.client:
            health_results["llm_server"] = "initialized"

        return health_results

    except Exception as e:
        health_results["status"] = "error"
        health_results["error_type"] = type(e).__name__
        health_results["message"] = str(e)
        return health_results


app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
