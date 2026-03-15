# Deploy: Fly.io (Backend) + Vercel (Frontend)

Follow these steps in order. You will need:
- **Fly.io** account + `flyctl` installed
- **Vercel** account (GitHub login)
- Your **API key** (Bytez, OpenAI, or Google) for the chatbot LLM

---

## Part 1: Deploy backend on Fly.io

### 1.1 Install Fly CLI (if not done)

**Windows (PowerShell):**
```powershell
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

**macOS/Linux:**
```bash
curl -L https://fly.io/install.sh | sh
```

Then log in:
```bash
fly auth login
```
(Opens browser; sign in with your Fly.io account.)

### 1.2 Create the app and set secrets

From the **project root** (where `fly.toml` and `Dockerfile` are):

```bash
cd c:\Users\HP\genai-gitlab-chatbot
```

**First time – launch the app (creates app on Fly.io):**
```bash
fly launch --no-deploy
```
- When asked “Copy configuration from existing app?” → **No**
- When asked “Choose an app name” → use `gitlab-handbook-chatbot` or your choice
- Choose your preferred **region** (e.g. `iad` for Virginia)

**Set your API key and provider** (use the one you use locally, e.g. Bytez):

**If using Bytez:**
```bash
fly secrets set LLM_PROVIDER=bytez
fly secrets set BYTEZ_API_KEY=YOUR_BYTEZ_KEY_HERE
```

**If using OpenAI:**
```bash
fly secrets set LLM_PROVIDER=openai
fly secrets set OPENAI_API_KEY=sk-your-openai-key-here
```

**If using Google Gemini:**
```bash
fly secrets set LLM_PROVIDER=google
fly secrets set GOOGLE_API_KEY=your-google-api-key-here
```

**Optional but recommended (embeddings):**
```bash
fly secrets set EMBEDDINGS_PROVIDER=sentence_transformers
```

### 1.3 Deploy the backend

```bash
fly deploy
```

Wait for the build and deploy to finish. Then get your backend URL:

```bash
fly status
```

Or open the app in the browser:

```bash
fly open
```

Your backend URL will be like: **`https://gitlab-handbook-chatbot.fly.dev`**  
Copy this URL; you need it for Vercel.

### 1.4 (Optional) Run ingest on Fly.io so the bot has data

If the vector store is empty, the bot will say “I cannot find this information.” To populate it once:

```bash
fly ssh console
```

In the console:
```bash
cd /app
python -m backend.ingest
python -m backend.embeddings
exit
```

Note: Without a persistent volume, this data is lost on the next deploy. For a permanent store, you can add a Fly volume and mount it at `/app/vector_store` (see comments in `fly.toml`).

---

## Part 2: Deploy frontend on Vercel

### 2.1 Connect the repo to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in (e.g. with GitHub).
2. Click **Add New…** → **Project**.
3. **Import** the repo `chakrinani/gitlab-handbook-chatbot`.
4. Before deploying, set **Root Directory**:
   - Click **Edit** next to “Root Directory”.
   - Set to **`frontend`** and confirm.

### 2.2 Set environment variable

1. In the same project settings, open **Environment Variables**.
2. Add:
   - **Name:** `VITE_API_URL`
   - **Value:** your Fly.io backend URL (e.g. `https://gitlab-handbook-chatbot.fly.dev`)
   - No trailing slash.
3. Save.

### 2.3 Build and deploy

- **Build Command:** `npm run build` (default is usually fine).
- **Output Directory:** `dist` (default for Vite).
- Click **Deploy**.

When the build finishes, Vercel gives you a URL like:  
**`https://gitlab-handbook-chatbot.vercel.app`**

---

## Part 3: Test the deployment

1. Open the **Vercel URL** in your browser.
2. Ask: “What is GitLab's product strategy?”
3. If you see “I cannot find this information,” run the ingest step in **1.4** (or add a volume and re-run ingest after deploy).

---

## Quick reference

| Step        | Where   | What to do |
|------------|---------|------------|
| Backend    | Fly.io  | `fly launch --no-deploy`, set secrets, `fly deploy` |
| Backend URL| Fly.io  | e.g. `https://gitlab-handbook-chatbot.fly.dev` |
| Frontend   | Vercel  | Root = `frontend`, env `VITE_API_URL` = backend URL |
| Frontend URL | Vercel | e.g. `https://gitlab-handbook-chatbot.vercel.app` |

---

## Credentials you need to provide

When you’re ready, set these on Fly.io (and optionally in Vercel only if you add backend there later):

1. **LLM:**  
   - Bytez: `BYTEZ_API_KEY`  
   - Or OpenAI: `OPENAI_API_KEY`  
   - Or Google: `GOOGLE_API_KEY`
2. **Provider:**  
   - `LLM_PROVIDER=bytez` or `openai` or `google`

Use **Fly.io secrets** (as in 1.2) so you never commit keys to the repo.
