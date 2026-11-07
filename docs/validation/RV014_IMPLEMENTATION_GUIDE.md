RV-014 — Guia de implementação do Context Builder
Projeto: Enterprise Knowledge AI System.

Experimento offline sobre o catálogo e rankings congelados do RV-011, com as seleções filtradas auditadas do RV-013. A decisão de manter filtered_only como controle está documentada em [RV013_ANALYSIS.md](RV013_ANALYSIS.md). Nenhuma configuração de produção foi promovida.
O que o Context Builder acrescenta
EvidenceContextBuilder prepara as evidências que uma futura camada de geração poderá receber:
1. Preserva os cinco chunks selecionados pelo filtro + RRF + diversidade, na mesma ordem. Esses chunks são as âncoras.
2. Percorre o pool original de 20 candidatos na ordem de fusion rank e acrescenta até um trecho por documento já selecionado.
3. Limita o contexto a dez chunks e 12.000 caracteres, incluindo metadados e formatação JSON.
4. Mantém o texto integral de cada trecho. Se as âncoras não couberem, lança ContextBudgetError; não as trunca ou descarta silenciosamente. Um complemento grande demais é ignorado, permitindo testar um posterior menor.
5. Atribui IDs locais E1, E2, etc. e mantém documento, chunk, arquivo, blocos de origem, seção, páginas, slides e planilhas. Scores e papéis de seleção ficam fora do texto entregue ao futuro LLM.
O limite de um trecho por documento se aplica aos acréscimos. Se a seleção inicial tiver dois chunks do mesmo documento, ambos são preservados. O builder recebe somente candidatos e limites: não recebe pergunta, gabarito, IDs esperados ou labels de referência.

O orçamento é de caracteres Unicode, não de tokens. Na integração com um LLM, será necessário contabilizar tokens para o modelo escolhido e reservar espaço para instruções, pergunta e resposta. JSON delimita os dados, mas não constitui uma barreira de segurança contra prompt injection.
Resultado do RV-014
Comparação pareada sobre as mesmas 25 seleções filtradas do RV-013:
Medida	Cinco âncoras	Contexto expandido
Chunks por pergunta — média A+B	5,00	8,72
Caracteres renderizados — média A+B	4.473	7.247
Caracteres renderizados — máximo A+B	5.546	8.300
B — cobertura macro das passagens de referência	87,5%	100,0%
B — grupos de referência encontrados	13/15	15/15
B — perguntas com todas as referências	10/12	12/12
Seleções originais preservadas em ordem	25/25	25/25


A expansão aumenta o volume total de caracteres em 62,0%. Portanto, o ganho de cobertura usa mais contexto; não é uma melhoria medida com o mesmo orçamento de cinco chunks. Hit@k, Recall@k e MRR da seleção original permanecem inalterados.
Caso	Complemento recuperado	Evidência disponível
B07	DOC-024::chunk-00007 — E8	Controles de segurança não tornam a saída de IA autoritativa; revisão humana continua necessária.
B11	DOC-007::chunk-00007 — E6	Conflitos entre documentos de igual autoridade exigem avaliar vigência, escopo e relações de substituição antes de escalar.


As referências são não exaustivas e os grupos A/B já foram usados no desenvolvimento. 100% de cobertura em B não significa 100% de respostas corretas. O grupo A não possui labels de passagem neste experimento. Não houve geração de respostas, avaliação de citações/entailment ou teste independente de generalização.

O flag BASELINE_DRIFT de RV-011/B11 permanece registrado. Esta comparação usa o mesmo snapshot RV-011 nos dois braços; ela não resolve nem apaga a divergência histórica com RV-010.
Arquivos e destinos no repositório
Arquivo	Destino
evidence_context.py	app/retrieval/evidence_context.py
test_evidence_context.py	tests/unit/test_evidence_context.py
test_evidence_context_replay.py	tests/unit/test_evidence_context_replay.py
smoke_evidence_context_replay.py	tests/smoke/smoke_evidence_context_replay.py
Este guia	docs/validation/RV014_IMPLEMENTATION_GUIDE.md
Resultado de referência	docs/validation/RV014_CONTEXT_REPLAY_RESULTS.json


São arquivos novos. Os módulos dos incrementos RV-008 a RV-013 continuam sendo usados; não é necessário substituir o HybridRetriever, ativar o filtro globalmente ou alterar o reranker.

O smoke requer os JSONs existentes RV-008, RV-010, RV-011 e RV-013, além de data/ground_truth/reranking_challenge_b.json. Não precisa do resultado RV-012 _local: recomputa seus controles e os compara às seleções do RV-013. O hash do arquivo RV-012 local não é apresentado como revalidado.
Executar no PowerShell
Na raiz do projeto, com a .venv ativa, depois de copiar os quatro arquivos Python:
python -m pytest tests/unit/test_evidence_context.py tests/unit/test_evidence_context_replay.py -q
python -m tests.smoke.smoke_evidence_context_replay --output docs/validation/RV014_CONTEXT_REPLAY_RESULTS_local.json
Resultado esperado: 50 testes aprovados. O smoke deve mostrar:
RV-013 audited from saved scores: MIXED_RESULTS_REVIEW_REQUIRED; no model inference.

Group A | n=13 | original top-5 unchanged
anchors_only: mean chunks=5.00; mean characters=4290
expanded_context: mean chunks=8.69; mean characters=6980

Group B | n=12 | original top-5 unchanged
anchors_only: mean chunks=5.00; mean characters=4672; reference coverage=0.8750; groups=13/15
expanded_context: mean chunks=8.75; mean characters=7537; reference coverage=1.0000; groups=15/15
O veredito é CONTEXT_CANDIDATE_FOR_REVIEW. Não há downloads de pesos, chamadas de embeddings ou de geração/reranking. Os fingerprints do resultado local podem diferir por caminhos e arquivos presentes; os valores acima são os resultados comparáveis.

Validação preliminar reproduzida em 06/11/2026 no ambiente do assistente: 50 testes do incremento aprovados e 487 testes aprovados no recorte disponível; replay completo dos 25 casos concluído. A suíte completa ficou bloqueada pela ausência do Docling em oito módulos de testes. Esses resultados não substituem a validação no ambiente Windows do projeto. Após incorporar o incremento, a regressão completa pode ser executada com python -m pytest -q.
Ponto de integração futura
O pool deve ser preservado antes da seleção final por diversidade. O HybridRetriever atual não foi modificado por este incremento. Exemplo para o ponto em que os candidatos fundidos e selecionados já estão disponíveis:
from app.retrieval.evidence_context import EvidenceContextBuilder

builder = EvidenceContextBuilder(
    max_chunks=10,
    max_characters=12000,
    max_additional_per_document=1,
)
context = builder.build(selected=selected_chunks, candidate_pool=fused_top20)
evidence_text = context.text
citation_lookup = context.citations
E1, E2, etc. são identificadores locais a esse contexto. O mapa permite resolver a origem de uma citação; ainda não verifica se uma resposta é sustentada pelo trecho. Também não implementa permissões, decisão de vigência ou aplicação automática da hierarquia documental.

Depois da reprodução local, o próximo incremento é conectar esse contrato à camada de resposta estruturada e validar referências existentes, sustentação das afirmações e abstention quando a evidência for insuficiente. A avaliação de respostas precisa incluir casos novos e prospectivos.