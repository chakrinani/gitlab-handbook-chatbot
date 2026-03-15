# Example Queries and Testing Guide

Use these to verify the chatbot and RAG pipeline.

---

## Example Queries

### Strategy and direction
- *"What is GitLab's product strategy?"*
- *"What are GitLab's strategic priorities?"*
- *"How does GitLab plan its roadmap?"*

### Remote work and culture
- *"How does GitLab handle remote work?"*
- *"What is GitLab's engineering culture?"*
- *"What are GitLab's values?"*
- *"How does GitLab support work-life balance?"*

### Processes
- *"How does GitLab do code review?"*
- *"What is GitLab's approach to async communication?"*
- *"How does GitLab handle onboarding?"*

### Specific topics
- *"What is the direction for DevSecOps?"*
- *"How does GitLab approach security?"*
- *"What is GitLab's pricing strategy?"*

---

## Testing Steps

1. **Health check**
   ```bash
   curl http://localhost:8000/health
   ```
   Expected: `{"status":"ok","service":"genai-gitlab-chatbot"}`

2. **Chat (curl)**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d "{\"message\":\"What is GitLab's product strategy?\",\"history\":[]}"
   ```
   Expected: JSON with `answer`, `sources` (array of `{url, title}`), `confidence`, `follow_up_suggestions`.

3. **UI**
   - Open http://localhost:5173
   - Type: *"What is GitLab's product strategy?"*
   - Confirm: answer appears, source links are present and open handbook/direction pages, loading state shows then clears.

4. **Follow-up**
   - Ask a follow-up in the same thread, e.g. *"How does that affect engineering?"*
   - Confirm the answer stays on topic and still cites sources when possible.

5. **Out-of-scope**
   - Ask: *"What's the weather today?"*
   - Confirm the bot redirects to GitLab documentation or says it can only answer from the handbook.

6. **Not in docs**
   - Ask something very specific that may not be in the scraped docs.
   - Confirm the bot says something like *"I cannot find this information in the GitLab handbook."* and does not invent an answer.
