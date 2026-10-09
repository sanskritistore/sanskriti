"""
Audiences मॉड्यूल — Custom Audience (ग्राहक phone list targeting)

09-10 user का खुद का idea: "software में column हो जिसमें 1-1000 phone
numbers डालें और उन पर ads चले"। Meta का Custom Audience feature यही
करता है — numbers SHA256 hash होकर Meta जाते हैं, Meta उन्हीं लोगों को
ad दिखाता है (और बाद में Lookalike से उन जैसे लाखों नए लोग)।
"""

from app.modules.audiences.routes import router

__all__ = ["router"]
