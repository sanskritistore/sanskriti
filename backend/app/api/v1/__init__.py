"""
API v1 - संस्कृति का versioned API पैकेज

main.py यहीं से api_router लेता है (सभी मॉड्यूल जुड़े हुए)।
"""
from app.api.v1.router import api_router

__all__ = ["api_router"]
