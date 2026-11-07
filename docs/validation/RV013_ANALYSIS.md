RV-013 — Análise e decisão
Projeto: Enterprise Knowledge AI System.

Fonte: RV013_FILTERED_RERANK_RESULTS.json, executado localmente por Rodrigo. A auditoria offline reutiliza os scores registrados, sem nova inferência. Nenhuma configuração de produção foi promovida.
Decisão sobre o RV-013
Manter filtered_only como base deste próximo experimento e deixar o reranker como opção experimental. A composição com preservação de prefixo melhora a média do grupo A, mas rebaixa uma pergunta e adiciona latência. Isso não invalida o modelo: documenta o custo e a perda individual dessa composição neste conjunto.
Medida	Filtro	Filtro + prefixo preservado
A — Hit@1	0,8462 (11/13)	0,9231 (12/13)
A — MRR	0,9231	0,9615
A — Recall@3	0,8718	0,8718
A — Recall@5	1,0000	1,0000
B — Hit@1 / MRR	1,0000 / 1,0000	1,0000 / 1,0000
B — Recall@5	1,0000	1,0000
B — cobertura macro das passagens de referência	0,8750	0,8750


No grupo A, Q05 e Q21 melhoram no primeiro resultado; Q25 piora. Em Q25, DOC-006::chunk-00008, que remete à precedência documental, fica acima de DOC-007::chunk-00007, que contém a regra explícita de conflito. O primeiro trecho tem relação com o assunto, mas desloca a regra diretamente aplicável.

O reranking sem preservação de prefixo também rebaixa Recall@3 em A. No grupo B, ele melhora Recall@3 de 0,9583 para 1,0000, sem ganho em Hit@1/MRR. Nenhuma reordenação dos mesmos cinco chunks recupera as passagens ausentes em B07 e B11.

Latências medidas no ambiente Windows, apenas para scoring: média de 0,917 s em A e 1,263 s em B. Carregamento do modelo: 25,47 s, contabilizado separadamente. Não são latências totais do RAG. Os scores brutos não são probabilidades de confiança.

O novo replay reproduz ordens, métricas, perdas individuais e proveniência do RV-013 usando seus scores salvos. O veredito continua MIXED_RESULTS_REVIEW_REQUIRED. Não há nova inferência nesse procedimento.
Próxima etapa
A montagem de contexto é tratada separadamente no [guia do RV-014](RV014_IMPLEMENTATION_GUIDE.md).