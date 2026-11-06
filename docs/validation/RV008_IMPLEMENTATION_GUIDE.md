# RV-008 — Reranking Layer v0.1

Projeto: Enterprise Knowledge AI System  
Data: 04/11/2026  
Estado: implementação e testes locais concluídos; benchmark com modelo e corpus real pendente.

## Ponto de retomada

O RV-007 validou Hybrid PT + DocumentDiversifier em 10 documentos, 79 chunks e
13 perguntas positivas. O baseline registrado tem Hit@1 de 76,9%, Hit@3 de
100%, Recall@5 de 100% e MRR de 0,8846. Esses números medem recuperação por
documento; ainda não validam respostas, citações ou suficiência dos trechos.

A auditoria fornecida registra HEAD `45a5a2c` e alterações do v0.3 ainda sem
commit naquele snapshot. Ela fez descoberta de 379 testes, sem executá-los.
O registro de validação informa uma execução anterior de 379 testes aprovados
e quatro warnings. Não foi possível confirmar um commit posterior.

## Arquivos e destinos

Todos os arquivos desta entrega são novos. Salve-os nestes caminhos relativos
à raiz de `enterprise-knowledge-ai-system`:

| Arquivo | Destino |
|---|---|
| `reranker.py` | `app/retrieval/reranker.py` |
| `cross_encoder_scorer.py` | `app/retrieval/cross_encoder_scorer.py` |
| `test_reranker.py` | `tests/unit/test_reranker.py` |
| `test_cross_encoder_scorer.py` | `tests/unit/test_cross_encoder_scorer.py` |
| `smoke_reranking_experiment.py` | `tests/smoke/smoke_reranking_experiment.py` |
| `RV008_IMPLEMENTATION_GUIDE.md` | `docs/validation/RV008_IMPLEMENTATION_GUIDE.md` |

## Comportamento implementado

1. Recuperar Top-20 vetorial e Top-20 lexical com a pergunta original em português.
2. Formar o pool RRF Top-20, com `k=60`.
3. Pontuar cada par pergunta/trecho com um cross-encoder local.
4. Ordenar pelo score do reranker; empates preservam a ordem de entrada.
5. Comparar Top-5 reranqueado com e sem diversificação por documento.

`CandidateReranker` recebe um `PairScorer` injetável. O código de ordenação não
depende de PyTorch, Transformers, chamadas de API ou de um modelo específico.
O adaptador inicial usa `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, multilíngue,
fixado na revisão `1427fd652930e4ba29e8149678df786c240d8825`.

Cada `RerankedCandidate` preserva o `FusedCandidate` original em `source`:

| Campo | Significado |
|---|---|
| `source.score` / `source.rank` | Score RRF e posição na fusão original |
| `score` / `rerank_rank` | Logit do cross-encoder e posição antes da diversificação |
| `rank` | Posição na seleção final |
| `chunk` | O mesmo chunk original, incluindo texto, ID e proveniência |

O score do reranker não é uma probabilidade. Falhas do modelo e scores inválidos
interrompem a execução de forma explícita. Não há substituição silenciosa pelo
baseline. O HybridRetriever atual continua sendo a implementação de referência.

## Executar os testes

Na raiz do repositório, com a `.venv` ativa:

```powershell
python -m pytest tests/unit/test_reranker.py tests/unit/test_cross_encoder_scorer.py -q
python -m pytest -q
```

Validação realizada na preparação: **99 testes aprovados**, incluindo os dois
arquivos novos e os testes recuperados de candidate fusion, hybrid retriever e
document diversifier. Ambiente desta execução: Python 3.12.14 e pytest 9.2.0.
Os testes do adaptador simulam a fronteira com Transformers/PyTorch; não executam
os pesos do modelo. A suíte completa do seu repositório e o Python 3.14.6 do
ambiente registrado na auditoria ainda precisam da execução local acima.

## Executar o experimento real

A auditoria registra `torch==2.14.1` e `transformers==5.18.0` instalados na sua
`.venv`. O adaptador reutiliza essas bibliotecas; não usa SentenceTransformers.
Verifique o ambiente e execute:

```powershell
python -c "import torch, transformers; print('torch:', torch.__version__); print('transformers:', transformers.__version__)"
python -m tests.smoke.smoke_reranking_experiment
```

A primeira execução baixa os pesos públicos do modelo (aproximadamente 471 MB)
e arquivos do tokenizer. Depois o reranking roda localmente, em CPU por padrão.
A etapa de embeddings utiliza a configuração OpenAI já existente e requer
`OPENAI_API_KEY`, com consumo da API. O benchmark incorpora documentos uma vez
e calcula uma query embedding por pergunta, compartilhando candidatos entre
todas as estratégias. Não faça upgrade geral da `.venv` apenas para este teste;
um erro de compatibilidade deve ser analisado a partir do traceback.

O par pergunta/trecho tem limite de 512 tokens. Apenas o trecho pode ser
truncado; uma pergunta sem espaço restante para evidência gera erro explícito.
O JSON mantém o texto original completo para inspeção. Essa inspeção também deve
considerar que o modelo pode ter recebido apenas o início de um trecho longo.

O relatório será escrito em `docs/validation/RV008_RESULTS.json`. Uma nova
execução substitui esse arquivo; use `--output` para preservar execuções:

```powershell
python -m tests.smoke.smoke_reranking_experiment --output docs/validation/RV008_RESULTS_cpu.json
```

## Comparação e critérios

As cinco estratégias usam o mesmo corpus e os mesmos pools por pergunta:

| Chave no relatório | Estratégia |
|---|---|
| `vector` | Vetorial Top-5 |
| `hybrid_v02` | RRF Top-5 |
| `hybrid_v03` | RRF + diversidade Top-5, baseline RV-007 |
| `reranked` | RRF Top-20 → reranker → Top-5 |
| `reranked_diverse` | RRF Top-20 → reranker → diversidade → Top-5 |

O relatório reutiliza a definição do avaliador atual: ranking de documentos
distintos pela primeira ocorrência nos cinco chunks finais. Assim, Hit@3 e MRR
seguem esse ranking de documentos; não devem ser reinterpretados como posição
do trecho exato. Nenhuma métrica de relevância de passagem é inventada.

O gate exige reprodução dos sete indicadores do v0.3, ausência de regressão
nesses indicadores e melhora em Hit@1 ou MRR. Resultados possíveis:

- `BASELINE_DRIFT`: o baseline não foi reproduzido; investigar antes de comparar.
- `REGRESSION`: pelo menos uma métrica piorou.
- `NO_FIRST_RANK_GAIN`: Hit@1 e MRR não melhoraram.
- `READY_FOR_PASSAGE_REVIEW`: houve ganho sem regressão medida; revisar os trechos.
- `INPUT_CHANGED_DURING_RUN`: código, corpus ou ground truth mudou durante a execução.

Concluir o script significa que o experimento terminou, não que o reranker foi
aprovado. Nenhuma configuração é promovida automaticamente. O relatório registra
modelo/revisão, versões instaladas, hashes dos insumos, métricas, IDs dos chunks,
scores RRF e reranker, referências de origem e tempo por pergunta.

## Revisão após a execução

Enviar o resumo do terminal e `RV008_RESULTS.json` para analisar ganhos e perdas
por pergunta. Revisar principalmente Q05, Q21 e Q26 (a primeira posição no
baseline híbrido), além de Q20 e Q34 (cobertura complementar recuperada no v0.3).
Verificar também perguntas que precisam de mais de um trecho do mesmo documento.

Somente os resultados reais justificam registrar RV-008 como aprovado em
`RETRIEVAL_VALIDATION.md` ou integrar um reranker por padrão. Q29, geração,
citações, autoridade e validade temporal continuam em etapas separadas.

## Referências técnicas

- [Model card oficial: mmarco-mMiniLMv2](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1)
- [Revisão fixada do modelo](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1/commit/1427fd652930e4ba29e8149678df786c240d8825)
- [Arquivos e tamanho dos pesos](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1/tree/1427fd652930e4ba29e8149678df786c240d8825)
- [Documentação de cross-encoders](https://www.sbert.net/docs/cross_encoder/usage/usage.html)
