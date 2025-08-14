import os
# Disable ChromaDB telemetry before importing
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_SERVER_TELEMETRY"] = "False"
os.environ["CHROMA_CLIENT_TELEMETRY"] = "False"
os.environ["POSTHOG_DISABLED"] = "True"
os.environ["ANALYTICS_DISABLED"] = "True"

# Disable Hugging Face tokenizers parallelism to avoid forking warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Set ChromaDB model caching directory
chroma_db_path = os.getenv("CHROMA_DB", "db/chromadb")
os.environ["CHROMA_CACHE_DIR"] = os.path.join(chroma_db_path, "chroma_models")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import unified_chat_routes, streaming_routes
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Browser AI Agent API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(unified_chat_routes.router, prefix="/api/v1", tags=["chat"])
app.include_router(streaming_routes.router, tags=["streaming"])

@app.get("/")
async def root():
    return {"message": "Browser AI Agent API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
