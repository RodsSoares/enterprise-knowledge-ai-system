RV-008 / RV-009 — Diagnóstico de reranking e replay com seleção preservada
Data: 04/11/2026
Projeto: Enterprise Knowledge AI System
Decisão: manter Hybrid v0.3 como referência; preservar a variação por faixas como candidata exploratória.
Resultado principal
O experimento RV-008 executou corretamente, reproduziu o baseline e registrou
regressão de cobertura ao reranquear o pool RRF Top-20. A análise do JSON
permitiu executar duas variações offline, reutilizando os mesmos scores.
Nenhuma chamada de embeddings ou inferência de modelo foi realizada no replay.
Métrica	Hybrid v0.3	RV-008 reranking + diversidade	RV-009 mesmos 5 chunks	RV-009 faixas 1–3 / 4–5
Hit@1	76,92%	84,62%	84,62%	92,31%
Hit@3	100%	100%	100%	100%
Hit@5	100%	100%	100%	100%
Recall@1	43,59%	55,13%	55,13%	58,97%
Recall@3	87,18%	80,77%	84,62%	87,18%
Recall@5	100%	93,59%	100%	100%
MRR	0,8846	0,9103	0,9231	0,9615


As métricas são médias sobre as mesmas 13 perguntas positivas. A definição
permanece a do RV-008: ranking de documentos distintos pela primeira ocorrência
nos cinco chunks finais. Não se trata de acurácia de respostas ou avaliação
completa de relevância de passagens.

O replay reproduziu os sete indicadores das cinco estratégias originais antes
de calcular qualquer comparação nova. O artefato original foi mantido intacto;
o resultado derivado registra seu SHA-256. O JSON original declara snapshot
estável; essa declaração não substitui uma nova auditoria do repositório Windows.
Experimentos executados
1. fixed_top5: reordenar os mesmos cinco chunks do v0.3.

O conjunto de evidências é preservado. Isso recupera Recall@5 de 100%, mas
Recall@3 cai de 87,18% para 84,62%. A variação continua classificada como
REGRESSION, sob o mesmo critério de aceitação original.

2. preserve_top3_and_top5: reordenar separadamente as posições 1–3 e 4–5.

A regra foi formulada após observar a regressão de Recall@3 no primeiro replay.
Ela usa as fronteiras de recuperação já avaliadas no projeto. Não usa IDs de
pergunta, respostas esperadas, documentos específicos ou pesos ajustados por
pergunta. Os cinco documentos são distintos em todas as seleções deste corpus;
o script exige essa condição para a variação por faixas.

O conjunto do Top-3 e o conjunto do Top-5 são preservados por construção. Dentro
de cada faixa, o score do reranker determina a ordem, com desempate estável.
O resultado melhora as métricas agregadas de primeira posição sem reduzir os
demais indicadores. A classificação é EXPLORATORY_CANDIDATE.

Limitação estrutural: um chunk originalmente na posição 4 ou 5 não pode
chegar às posições 1–3 nessa variação, mesmo que seu score seja maior. A
preservação de cobertura é uma propriedade da restrição; não comprova que o
modelo tenha aprendido a respeitar cobertura ou autoridade documental.
Efeito por pergunta
Pergunta	Primeiro documento esperado: v0.3	Mesmos 5 chunks	Faixas 1–3 / 4–5
Q05	2	1	1
Q20	1	1	1
Q21	2	1	1
Q22	1	1	1
Q23	1	1	1
Q25	1	2	2
Q26	2	1	1
Q31	1	1	1
Q32	1	1	1
Q33	1	2	1
Q34	1	1	1
Q35	1	1	1
Q36	1	1	1


Na variação por faixas, Q05, Q21 e Q26 melhoram; Q25 piora. O saldo é de dois
acertos adicionais na primeira posição: de 10/13 para 12/13. A regressão
individual da Q25 não deve ser escondida pela melhora da média.

No replay livre dos mesmos cinco chunks, Recall@3 piora em Q32 (2/3 → 1/3) e
Q33 (1 → 1/2), enquanto melhora em Q34 (1/2 → 1). A variação por faixas preserva
o Recall@3 original de cada pergunta.
Revisão qualitativa das evidências
Caso	Evidência observada no JSON	Interpretação
Q21 — informações confidenciais	DOC-006::chunk-00003, “2. Confidential information”, é promovido acima de regras específicas de compartilhamento com transportadoras.	O novo líder contém a classificação solicitada. O ganho é sustentado pelo conteúdo do trecho.
Q26 — versão vigente de fornecedores	DOC-022::chunk-00003, “2. Current policy version”, informa versão 3.0, vigência e estado ativo. Substitui no topo um trecho sobre incidente com fornecedor.	O novo líder responde diretamente à pergunta no corpus de teste.
Q25 — conflito entre SOP e política	O modelo atribui 6,2007 a DOC-006::chunk-00008, que remete à Document Governance Policy, e 3,1322 a DOC-007::chunk-00007, que estabelece diretamente a prevalência da política.	O primeiro trecho é relacionado, mas a regra direta está no segundo. A seleção do Top-1 ainda precisa de revisão de relevância e autoridade.
Q32 — aprovações para IA com dados de fornecedores	DOC-012::chunk-00001 contém as linhas A8:E9 com responsáveis e revisões de aprovação. No RV-008, fica abaixo do guia de treinamento e sai do Top-5.	O reranking amplo perde evidência complementar específica. Preservar a seleção recupera o trecho.
Q33 — requisitos de segurança para IA	DOC-024::chunk-00005 enumera controles concretos; DOC-006::chunk-00006 descreve requisitos do ambiente. O RV-008 prioriza treinamento e propósito de governança, removendo DOC-006 do Top-5.	Há preferência por trechos tematicamente relacionados sobre evidências mais diretamente operacionais nesta pergunta. Isso não prova uma causa geral ligada a idioma ou formato.


Essas observações são uma revisão qualitativa dos trechos presentes no artefato,
não um novo golden set de relevância por passagem e não uma revisão humana
independente. Q05 recupera a matriz de aprovação, mas uma resposta futura deve
respeitar os tipos de contratação e condições da matriz.
Verificação de truncamento
A tokenização foi reproduzida com o tokenizer.json da revisão fixada
1427fd652930e4ba29e8149678df786c240d8825 e tokenizers==0.23.2, usando as perguntas
originais, a representação build_search_text e os tokens especiais do par.
- Pares verificados: 260 (13 perguntas × 20 candidatos).
- Limite configurado: 512 tokens.
- Maior par observado: 456 tokens, Q32 / DOC-012::chunk-00001.
- Pares acima do limite: 0.
Essa reprodução não identificou truncamento como explicação para as perdas de
Q32 ou Q33. Ela não é uma captura dos tensores da execução original. Os detalhes
por par, a versão do tokenizer e o hash do arquivo estão no resultado RV-009.
Nenhum peso do modelo foi carregado nessa verificação; somente o tokenizer.
Validação de código
Foram aprovados 116 testes locais, sendo 17 novos testes do replay e 99
testes já disponíveis de reranking, adapter, fusion, hybrid retrieval e
document diversity. Ambiente local de preparação: Python 3.12.14 / pytest 9.2.0.
Isso não equivale a uma nova execução da suíte completa no Windows do projeto;
o último resultado informado pelo usuário continua sendo 429 testes aprovados.

Os testes verificam preservação dos conjuntos, ordenação e desempates,
independência das respostas esperadas, recusa de scores inválidos, consistência
das métricas originais, rejeição de snapshot instável e imutabilidade da entrada.
Arquivos e reprodução
Arquivo	Destino relativo ao repositório
smoke_reranking_replay.py	tests/smoke/smoke_reranking_replay.py
test_reranking_replay.py	tests/unit/test_reranking_replay.py
RV009_REPLAY_RESULTS.json	docs/validation/RV009_REPLAY_RESULTS.json
RV009_ANALYSIS.md	docs/validation/RV009_ANALYSIS.md


O original docs/validation/RV008_RESULTS.json deve permanecer disponível.
Para validar e reproduzir o replay em outro arquivo, sem APIs ou inferência:
python -m pytest tests/unit/test_reranking_replay.py -q
python -m tests.smoke.smoke_reranking_replay --output docs/validation/RV009_REPLAY_RESULTS_local.json
A reprodução padrão usa somente a biblioteca padrão Python. O argumento
opcional --tokenizer-json permite repetir também a auditoria de tokenização
com um arquivo local da mesma revisão; ela requer tokenizers. Nenhum download
é iniciado pelo script. Sem esse argumento, o novo relatório omite apenas a
auditoria de tokenização, preservando o replay completo das métricas.
Decisão de continuidade
O Hybrid v0.3 permanece a referência. O RV-008 e o replay livre dos cinco chunks
não satisfazem o critério original. A variação por faixas merece validação
adicional, sem promoção automática nem mudança dos critérios após o resultado.

Antes de torná-la uma configuração de produção, validar perguntas novas com
evidências esperadas definidas independentemente e executar uma comparação real
pontuando apenas os cinco chunks selecionados. Essa execução é necessária para
medir latência e possíveis diferenças numéricas de batching. Não é válido
estimar seu tempo como um quarto do tempo observado no pool de vinte.

Q25 permanece um caso obrigatório de revisão. As regras de autoridade,
supersessão e validade temporal continuam fora do que esses scores e métricas
por documento demonstram. Q29/abstenção, grounding e citações permanecem etapas
posteriores de avaliação.