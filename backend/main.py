import os
# Disable ChromaDB telemetry before any other imports
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "False"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.web_analyzer_routes import router as web_analyzer_router
from routes.test_code_generator_routes import router as test_code_generator_router
from routes.chat_analyzer_routes import router as chat_analyzer_router
from routes.test_executor_routes import router as test_executor_router
from routes.unified_chat_routes import router as unified_chat_router
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

# Get configuration from environment
PORT = int(os.getenv('PORT', 8000))
HOST = os.getenv('HOST', '0.0.0.0')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'logs/app.log')

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)

app = FastAPI(title="Web Analyzer API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(web_analyzer_router, prefix="/api/v1")
app.include_router(test_code_generator_router, prefix="/api/v1")
app.include_router(chat_analyzer_router, prefix="/api/v1")
app.include_router(test_executor_router, prefix="/api/v1")
app.include_router(unified_chat_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
