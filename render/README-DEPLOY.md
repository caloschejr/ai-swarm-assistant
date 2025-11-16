# Deploying to Render (one-click from iPhone)

This guide helps you deploy the repository to Render with minimal steps so you can do it from an iPhone.

1. Open the Render dashboard on your iPhone and sign in (or sign up):
   https://dashboard.render.com/

2. Click "New" -> "Web Service" -> "Connect a repository" and choose:
   - Repository: `caloschejr/ai-swarm-assistant`
   - Branch: `main`

3. For Environment, choose: Docker
   Render will use the Dockerfile in the repository to build the service.

4. Important environment variables (add these in the Render UI under Environment):
   - `DISABLE_RAY` = `1`        # use single-container mode (recommended)
   - If you plan to use OpenAI, add `OPENAI_API_KEY` as a secret

5. Click "Create Web Service". Render will build and deploy the service.

After the build completes your service will be reachable via the Render-provided URL.

Notes
- Using `DISABLE_RAY=1` ensures the app runs in a single container without the Ray cluster dependency.
- For small-scale testing this is sufficient; for production you should consider a managed Ray cluster or separate model-serving infra.
