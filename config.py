import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Environment
ENV = os.getenv("ENV", "development")
IS_PRODUCTION = ENV == "production"

# Secret Key
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkeyone2talk-dev-only")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./votes.db")

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "4040"))
