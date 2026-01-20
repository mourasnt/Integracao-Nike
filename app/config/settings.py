import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
FERNET_KEY = os.getenv("FERNET_KEY")

# Attachment storage settings
ATTACHMENTS_DIR = os.getenv("ATTACHMENTS_DIR", "attachments")
ATTACHMENT_BASE_URL = os.getenv("ATTACHMENT_BASE_URL", "/attachments")
