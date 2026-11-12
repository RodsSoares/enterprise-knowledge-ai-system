# Protected MVP deployment on Render

## Scope

This is a **private demonstration** of the Streamlit frontend, not an enterprise production deployment. The application uses the committed 27-document synthetic corpus, saved evidence units and embeddings. The source documents are verified at startup; the application does not ingest new user documents.

The offline CI workflow must pass before deployment. The default model is publicly reachable; keep the cost ceilings and set a hard usage limit on the OpenAI project.

## Deploy

1. In Render, create a new **Blueprint** from `RodsSoares/enterprise-knowledge-ai-system` using branch `claude/lean-mvp-hardening` and the root `render.yaml`.
2. Set `OPENAI_API_KEY` as a secret environment variable. **Never** paste it in GitHub or commit it.
3. Set `APP_ACCESS_PASSWORD` to a unique random password of at least 16 characters, stored as a Render secret. Do not share it publicly. A blank/short password makes the app refuse access.
4. Confirm the instance type, resource availability, expected charges and the deployment branch before applying the Blueprint. The Blueprint defaults to a free instance; available plans can vary.
5. Deploy and open the Render URL. Confirm the chat opens without a login and that the protected model asks for the password.
6. Test an answer with citations, a justified abstention, a referenced-document download and an attached document. Review Render logs for startup or runtime errors.

**Deploy command:** `streamlit run app/frontend/main.py --server.address 0.0.0.0 --server.port $PORT --server.headless true`

**Health endpoint:** `/_stcore/health` (Streamlit server availability only; it does not verify OpenAI or the evidence catalog).

**Dependencies:** `requirements-deploy.txt` installs the lean runtime. The full `requirements.txt` is retained for CI, Docling parsing, and offline development.

**Default model:** `gpt-4.1-mini-2025-04-14` for economical demonstration. `gpt-6.1-sol` is available in the interface; verify the model is enabled in your API account and the price table is current before using it.

## Security and cost boundaries

Access model since RV-046: the default model is open; the password unlocks the protected model.

- **Open access to `gpt-4.1-mini`.** Anyone with the URL can ask questions and attach documents. Every question spends the API credit of the deployment.
- **Password only for protected models.** `protected_models` in `config/lean_runtime.json` (currently `gpt-6.1-sol`) require `APP_ACCESS_PASSWORD` in the sidebar. The service refuses a protected model without the unlock, independently of the interface. If the secret is unset or shorter than 16 characters, the protected model is unavailable.
- **Three cost ceilings**, all enforced before each paid call: per question, per browser session, and **per day for the whole server process** (`max_cost_per_day_usd`, USD 1.00). The daily counter is kept in memory and resets when the instance restarts, so it limits abuse but **is not an account-wide billing cap**. Set a hard monthly limit on the OpenAI project as the real ceiling.
- **Attached documents** (`.pdf`, `.docx`, `.xlsx`, `.pptx`, `.md`, `.txt`) are read in memory, embedded and searched for that session only; nothing is written to disk. Their text is sent to OpenAI. Limits: 5 files per session, 5 MB each, 300 passages. Scanned PDFs are refused. Parsing uses light libraries, not Docling, so layout-heavy files lose structure.
- **Referenced documents** can be downloaded from the app (only files listed in the verified catalog are served) or opened on GitHub through `repository_blob_url`, which points to this branch and must be updated when the branch changes.
- There is no IP rate limiting, user quota, audit log or abuse prevention beyond the ceilings above. This is **not** SSO, MFA, user management or enterprise authorization.
- Streamlit session state is ephemeral and resets after restarts or disconnects. The cost estimate is not a billing guarantee.

## Release acceptance

- [ ] GitHub Actions offline CI passed on the deployed commit.
- [ ] Render build and startup succeeded.
- [ ] The default model answers a known question with citations without a password.
- [ ] Missing/wrong password cannot select the protected model; the correct password unlocks it.
- [ ] A referenced corpus document can be downloaded and opened on GitHub.
- [ ] An attached document is indexed and answered from in its own scope.
- [ ] A question without evidence abstains.
- [ ] Two independent sessions do not share the question history or in-memory budget.
- [ ] Confirm the API account's usage limits, model availability and price table.
- [ ] Document the live URL, deployment SHA, model, test questions and outcome.

## Next steps for a production-grade service

Add SSO/identity provider, server-side rate limiting and shared quotas, centralized logging, a managed secrets policy, monitoring, access-controlled documents and a production deployment plan. Do not represent this private demo as a secure enterprise multi-tenant product.
