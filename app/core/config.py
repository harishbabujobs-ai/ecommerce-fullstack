import os
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ecommerce_fullstack.db")
SECRET_KEY = os.getenv("SECRET_KEY", "development-only-secret-change-me-32-bytes")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
TAX_RATE = Decimal(os.getenv("TAX_RATE", "0.08"))
SHIPPING_FEE = Decimal(os.getenv("SHIPPING_FEE", "5.00"))
FREE_SHIPPING_THRESHOLD = Decimal(os.getenv("FREE_SHIPPING_THRESHOLD", "50.00"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")
    if origin.strip()
]