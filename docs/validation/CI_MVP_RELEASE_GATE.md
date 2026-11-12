# CI do MVP — validação antes do merge

**Branch de implementação:** `claude/lean-mvp-hardening`  
**Workflow:** `.github/workflows/ci.yml`  
**Objetivo:** ter uma verificação reproduzível e sem custos de API antes de integrar o MVP à `main`.

## Gatilhos e execução

- `push` na `main` ou em `claude/lean-mvp-hardening`.
- Pull Requests com destino à `main`.
- Execução manual em **Actions → CI - Enterprise Knowledge MVP → Run workflow**.
- Runner Ubuntu 24.04, Python 3.12, instalação de versões fixadas em `requirements.txt`.
- Permissões mínimas (`contents: read`), timeout de 40 minutos e cancelamento de execuções anteriores da mesma referência.
- A variável `OPENAI_API_KEY` é definida como vazia. **Nenhum benchmark pago ou teste com LLM real** é executado no CI.

## Verificações obrigatórias

1. `python -m pytest tests/unit tests/integration -q`: testes de contratos, recuperação, geração, serviços e parsers.
2. `python -m app.scripts.audit_corpus_content --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_27DOC.json`: bloqueia conteúdo do harness de avaliação nos trechos pesquisáveis.
3. Validação offline do relatório `RV045_LEAN_EVALUATION_RESULTS.json`: exige 46 identificadores únicos, correspondência com `answer_criteria.yaml` e campos de resultado presentes.

**Escopo importante:** a terceira verificação confirma apenas a integridade do resultado arquivado. Ela **não** reexecuta o Golden Set com `gpt-6.1-sol` nem autentica semanticamente as respostas. O resultado observado permanece 45/46 em uma execução, complementado pela auditoria em `RV045_SEMANTIC_AUDIT_46_CASES.md`.

## Critérios de promoção para a main

- [ ] Workflow concluído com sucesso na branch de origem.
- [ ] Pull Request revisada, incluindo mudanças nos 27 documentos-fonte e no catálogo/embeddings regenerados.
- [ ] Smoke test manual do Streamlit e do `KnowledgeService`, incluindo uma resposta correta, uma pergunta sem evidências e uma pergunta com restrição documental. A captura de tela do MVP é apenas ilustrativa.
- [ ] Confirmar que não há credenciais, dados empresariais reais ou artefatos locais sensíveis entre os arquivos alterados.
- [ ] Fazer o merge pela Pull Request, preservando a auditoria e a documentação.

## Depois da promoção

Habilitar uma regra de proteção da `main` para exigir Pull Request e a verificação **Offline tests and corpus checks (Python 3.12)** com sucesso. A configuração de proteção da branch ocorre nas configurações do GitHub e depende das permissões do proprietário.

**Nota de segurança:** não adicionar `OPENAI_API_KEY` ao workflow básico. Testes pagos e repetibilidade do Golden Set devem utilizar uma execução separada, com aprovação explícita, controle de custos e resultados arquivados.
