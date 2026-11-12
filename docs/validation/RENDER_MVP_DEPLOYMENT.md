# Protected MVP deployment on Render

## Scope

This is a **private demonstration** of the Streamlit frontend, not an enterprise production deployment. The application uses the committed 27-document synthetic corpus, saved evidence units and embeddings. The source documents are verified at startup; the application does not ingest new user documents.

The offline CI workflow must pass before deployment. Do not deploy the app publicly without the access gate.

## Deploy

1. In Render, create a new **Blueprint** from `RodsSoares/enterprise-knowledge-ai-system` using branch `claude/lean-mvp-hardening` and the root `render.yaml`.
2. Set `OPENAI_API_KEY` as a secret environment variable. **Never** paste it in GitHub or commit it.
3. Set `APP_ACCESS_PASSWORD` to a unique random password of at least 16 characters, stored as a Render secret. Do not share it publicly. A blank/short password makes the app refuse access.
4. Confirm the instance type, resource availability, expected charges and the deployment branch before applying the Blueprint. The Blueprint defaults to a free instance; available plans can vary.
5. Deploy and open the Render URL. Confirm the login screen appears *before* any model calls.
6. After logging in, test an answer with citations, a justified abstention, and the session cost ceiling. Review Render logs for startup or runtime errors.

**Deploy command:** `streamlit run app/frontend/main.py --server.address 0.0.0.0 --server.port $PORT --server.headless true`

**Health endpoint:** `/_stcore/health` (Streamlit server availability only; it does not verify OpenAI or the evidence catalog).

**Dependencies:** `requirements-deploy.txt` installs the lean runtime. The full `requirements.txt` is retained for CI, Docling parsing, and offline development.

**Default model:** `gpt-4.1-mini-2025-04-14` for economical demonstration. `gpt-6.1-sol` is available in the interface; verify the model is enabled in your API account and the price table is current before using it.

## Security and cost boundaries

- Access is gated by a shared demonstration password. This is **not** SSO, MFA, user management or enterprise authorization.
- Password checking happens before initializing the OpenAI client. Secrets are not stored in the repository.
- Each Streamlit session has its own `KnowledgeService`, question embedding cache, and tracked cost ceiling. A separate browser session can have a separate budget; **this is not an account-wide billing cap**.
- There is no robust IP rate limiting, user quotas, audit log or abuse prevention. Restrict access to a small trusted group and monitor API usage. For broader exposure, use an upstream identity-aware proxy and server-side shared budgets.
- `autoDeployTrigger: off` prevents every commit from automatically redeploying the public service. Trigger subsequent deploys deliberately.
- Streamlit session state is ephemeral and resets after restarts or disconnects. The cost estimate is not a billing guarantee.

## Release acceptance

- [ ] GitHub Actions offline CI passed on the deployed commit.
- [ ] Render build and startup succeeded.
- [ ] Missing/wrong password cannot access the RAG or make API calls.
- [ ] Correct password allows answering a known question with citations.
- [ ] A question without evidence abstains.
- [ ] Two independent sessions do not share the question history or in-memory budget.
- [ ] Confirm the API account's usage limits, model availability and price table.
- [ ] Document the live URL, deployment SHA, model, test questions and outcome.

## Next steps for a production-grade service

Add SSO/identity provider, server-side rate limiting and shared quotas, centralized logging, a managed secrets policy, monitoring, access-controlled documents and a production deployment plan. Do not represent this private demo as a secure enterprise multi-tenant product.
