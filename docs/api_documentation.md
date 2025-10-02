# YottaReal Chatbot Demo API

## POST /api/chat
Request:
```json
{
  "message": "How do I submit a maintenance request?",
  "session_id": "uuid-string"
}
{
  "answer": "…",
  "citations": [
    {"id": 1, "source": "leasing_faq.md"},
    {"id": 2, "source": "maintenance_procedures.md"}
  ]
}
