RV-013 — Filtro lexical com inferência real do reranker
Objetivo
O RV-012 foi reproduzido no ambiente local: 22 testes aprovados e métricas
iguais às do replay entregue. O RV-013 mede se acrescentar o cross-encoder
ao retrieval filtrado melhora a ordenação o suficiente para justificar sua
presença nessa composição.

O controle é filtered_hybrid_diverse do RV-012: Hit@1 de 0,8462 em A e 1,0000
em B, com Recall@5 de 1,0000 em ambos. Não reutilizamos o v0.3 como controle
principal, pois isso esconderia uma possível perda em relação ao filtro sozinho.
O que é real e o que é reutilizado
- Os rankings vetoriais e os 79 chunks são os registrados no RV-011.
- BM25, filtro, RRF e diversificação são recalculados; a seleção de cinco
  chunks precisa coincidir exatamente com o RV-012 local antes da inferência.
- O cross-encoder faz inferência real sobre esses cinco chunks por pergunta.
- São 25 perguntas: 13 de A e 12 de B, reportadas separadamente.
- Uma execução completa faz 25 chamadas ao scorer, com 125 pares ao todo.
- Não há chamadas à API de embeddings nem parsing dos documentos.
É uma avaliação de inferência real sobre retrieval congelado, não uma nova
execução end-to-end de ingestion e embeddings. A/B são conjuntos de
desenvolvimento para a composição; não representam validação independente.
Comparações
Braço	Comportamento
filtered_only	Mantém a ordem produzida pelo filtro + RRF + diversificação.
filtered_reranked	Ordena livremente os mesmos cinco chunks pelo cross-encoder.
filtered_prefix_preserved	Ordena dentro dos grupos dos três primeiros documentos e dos dois restantes.


O scorer recebe a pergunta original, sem o filtro lexical. Os textos usam
build_search_text, como nos experimentos anteriores. Os scores de RRF, os
scores do reranker e a proveniência dos trechos são registrados separadamente.

Modelo: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1.
Revisão: 1427fd652930e4ba29e8149678df786c240d8825.
Configuração: CPU por padrão, batch_size=8 e max_length=512.

A preservação dos documentos Top-3 mantém as métricas documentais desse corte
por construção. A cobertura das referências em Top-5 também permanece igual
nos três braços, pois todos recebem o mesmo conjunto de chunks.
Assim, B07 e B11 continuarão com referências ausentes. Essa pendência exige
uma alteração posterior na seleção de passagens, não apenas na ordem.
Arquivos
Arquivo	Pasta no repositório
smoke_filtered_reranking.py	tests/smoke/
test_filtered_reranking.py	tests/unit/
RV013_IMPLEMENTATION_GUIDE.md	docs/validation/


São três arquivos novos. Os componentes existentes continuam inalterados.
Os inputs padrão são:
- docs/validation/RV008_RESULTS.json
- docs/validation/RV010_LIVE_RESULTS.json
- docs/validation/RV011_CANDIDATE_TRACE.json
- docs/validation/RV012_LEXICAL_REPLAY_RESULTS_local.json
- data/ground_truth/reranking_challenge_b.json
O flag BASELINE_DRIFT do RV-011 e a diferença de B11 ficam registrados na
proveniência. A comparação atual utiliza a mesma seleção congelada em todos
os braços e não reclassifica a execução anterior.
Execução
Com a .venv ativa, na raiz do projeto:
python -m pytest tests/unit/test_filtered_reranking.py -q
Resultado esperado: 18 testes aprovados. Depois:
python -m tests.smoke.smoke_filtered_reranking --output docs/validation/RV013_FILTERED_RERANK_RESULTS.json
O script valida os inputs antes de carregar o modelo. Os pesos da revisão
fixada serão reutilizados se estiverem no cache. Não requer novas dependências
além das já usadas nos experimentos anteriores.

Opcionalmente, é possível executar apenas a validação dos inputs:
python -m tests.smoke.smoke_filtered_reranking --validate-only
Esse modo termina sem carregar o cross-encoder e sem gerar resultados de
inferência. O modo padrão já inclui essa validação automaticamente.
Interpretação da decisão
Decisão	Interpretação
INPUT_CHANGED_DURING_RUN	Inputs ou código monitorado mudaram durante a execução.
REGRESSION_KEEP_FILTER_ONLY	A composição restrita piorou alguma métrica agregada em A ou B; manter o filtro sozinho como candidato nesta comparação.
MIXED_RESULTS_REVIEW_REQUIRED	Não houve perda agregada, mas alguma pergunta piorou; revisar os casos antes de escolher a composição.
CANDIDATE_FOR_REVIEW	Houve ganho agregado sem regressões documentais individuais nas métricas acompanhadas; revisar evidência e latência.
NO_MEASURED_GAIN_KEEP_FILTER_ONLY	O reranker não acrescentou ganho mensurado de Hit@1/MRR; o candidato sem ele evita esse custo de inferência.


O JSON mostra as regressões individuais separadamente das médias. Uma perda
em Q25, por exemplo, não fica escondida por ganhos em outras perguntas.
Nenhuma decisão altera automaticamente a configuração padrão do sistema.

O tempo de carregar o modelo fica separado do tempo de pontuar cada conjunto
de cinco chunks. Os tempos de inferência serão os efetivamente medidos na
execução local; não estimamos resultados antes de executar o modelo.

Envie o resumo do terminal e RV013_FILTERED_RERANK_RESULTS.json. A análise
seguinte deve decidir sobre a composição e manter identificadas as pendências
de cobertura de passagens, respostas, citações e abstenção.
Validação desta entrega
- 18 novos testes aprovados.
- 196 testes aprovados no subconjunto disponível do projeto.
- CLI de ajuda verificada.
- Preparação real dos inputs executada com os arquivos fornecidos: as 25
  seleções filtradas reproduziram o RV-012, sem chamadas de modelos ou APIs.
- Inferência real do RV-013 e suíte completa do repositório Windows pendentes
  de execução no ambiente do usuário.
Não há métricas novas do cross-encoder a declarar nesta entrega.