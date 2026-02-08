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

# Cloudflare R2
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")
R2_ENABLED = bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME)
