# AI Email Automation System Spec

## 1. RabbitMQ Architecture

### Exchange
- x.app2ai.direct
- x.ai2app.direct

### Queue

#### App → AI
- q.2ai.classify
- q.2ai.draft

#### AI → App
- q.2app.classify
- q.2app.draft

---

## 2. Design Principles

- Queue is separated by function
- classify = GPT
- draft = Claude
- task_type is NOT used
- draft queue uses mode field:
  - generate
  - regenerate

---

## 3. AI Responsibilities

### classify
- Domain classification
- Intent classification
- Email summarization (GPT)
- Schedule extraction (GPT)
- Email embedding (SBERT)

### draft
- Reply generation (Claude)
- Reply regeneration (Claude)
- Reply embedding (SBERT)

---

## 4. Embedding Policy

- Use fine-tuned SBERT model
- Do NOT introduce new embedding model
- Use same SBERT for:
  - classification feature
  - embedding generation

### Input

- email_embedding = SBERT(summary)
- reply_embedding = SBERT(draft_reply)

### Fallback

- If summary is poor → use (subject + body)

---

## 5. Message Schema

### classify request

```json
{
  "request_id": "...",
  "emailId": "...",
  "threadId": "...",
  "subject": "...",
  "body": "...",
  "mail_tone": "정중체"
}
classify response
{
  "request_id": "...",
  "emailId": "...",
  "classification": {
    "domain": "...",
    "intent": "..."
  },
  "summary": "...",
  "schedule_info": {},
  "email_embedding": []
}
draft request
{
  "request_id": "...",
  "mode": "generate",
  "emailId": "...",
  "subject": "...",
  "body": "...",
  "domain": "...",
  "intent": "...",
  "summary": "..."
}
draft response
{
  "request_id": "...",
  "emailId": "...",
  "draft_reply": "...",
  "reply_embedding": []
}
6. System Rules
request_id must be preserved
AI does NOT store data
Backend handles DB + similarity
AI returns JSON only
embedding must be list[float]
7. Current Decisions
SBERT is reused (fine-tuned model)
No template placeholder system
Claude generates full reply
Backend performs similarity matching