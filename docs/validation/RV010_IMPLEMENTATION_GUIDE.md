RV-010 — Reranking com inferência real sobre cinco chunks
Ponto de partida
O RV-009 foi reproduzido no ambiente local: 17 testes aprovados. A política
preserve_top3_and_top5 alcançou Hit@1 de 0,9231, MRR de 0,9615,
Recall@3 de 0,8718 e Recall@5 de 1,0000 nas 13 perguntas positivas do conjunto A.
Ela continua sendo uma candidata exploratória: a regra foi definida depois de
examinar os resultados dessas mesmas perguntas.

O RV-010 verifica o comportamento com inferência real, pontuando somente os
cinco chunks selecionados pelo v0.3. Acrescenta 12 perguntas novas, congeladas
antes de consultar seus scores, e apresenta A e B separadamente.
Arquivos e destinos
Copie os arquivos abaixo para a raiz relativa indicada no repositório
enterprise-knowledge-ai-system.
Arquivo	Destino no repositório
prefix_preserving_selector.py	app/retrieval/prefix_preserving_selector.py
reranking_challenge_b.json	data/ground_truth/reranking_challenge_b.json
smoke_prefix_reranking_live.py	tests/smoke/smoke_prefix_reranking_live.py
test_prefix_preserving_selector.py	tests/unit/test_prefix_preserving_selector.py
test_prefix_reranking_live.py	tests/unit/test_prefix_reranking_live.py
RV010_IMPLEMENTATION_GUIDE.md	docs/validation/RV010_IMPLEMENTATION_GUIDE.md


São seis arquivos novos. O experimento usa os módulos já instalados nos
RV-008 e RV-009, além do corpus e dos arquivos de ground truth existentes.
Mantenha o RV008_RESULTS.json original em docs/validation/.
Desenho do experimento
1. Recriar os mesmos 79 chunks de dez documentos e os índices compartilhados.
2. Recuperar candidatos com vector + BM25 + RRF e selecionar cinco com o
   DocumentDiversifier, mantendo a configuração v0.3.
3. Pontuar apenas esses cinco chunks com o cross-encoder já utilizado,
   preservando modelo, revisão, comprimento máximo e formato do texto.
4. Comparar três ordens sobre o mesmo conjunto de chunks: hybrid_v03,
   unconstrained_top5 e prefix_preserved.
5. Na última ordem, separar os três primeiros documentos distintos do baseline
   dos demais e ordenar por score dentro de cada grupo. Empates mantêm a ordem
   original. Para cinco documentos distintos, isso equivale aos grupos 1–3 e 4–5.
6. Reportar métricas e latência separadamente para A, com 13 perguntas, e B,
   com 12 perguntas novas.
Essa restrição preserva o conjunto de evidências e o conjunto dos três primeiros
documentos. Por construção, preserva as métricas documentais Hit/Recall@3 e @5
em relação ao baseline do próprio grupo. A avaliação relevante para o reranking
é se Hit@1 e MRR melhoram e se os primeiros trechos são adequados e autoritativos.
Preservar documentos não demonstra que uma resposta ou citação esteja correta.

O módulo novo é opcional. O HybridRetriever e a configuração padrão continuam
com o comportamento existente.
Perguntas novas e limites da evidência
B cobre os dez documentos e contém referências a passagens que sustentam os
rótulos. As perguntas e os rótulos foram elaborados por IA a partir de passagens
do mesmo corpus; a revisão humana independente está pendente. B é um conjunto
prospectivo neste experimento, não um holdout externo cego nem uma validação de
generalização para novos documentos. Seu baseline só será conhecido após a execução.

A cobertura dos grupos de passagens de referência é um diagnóstico não exaustivo.
Outros chunks podem conter evidência válida; cobertura baixa exige revisão.
Como os três braços usam o mesmo conjunto selecionado, essa cobertura em Top-5
é igual entre eles.

O JSON B tem um hash canônico congelado, também registrado no script:
f52739b380f00778291aef65d8fdc4be3181a6e9acea92c4f26f5ab3d8cb2b3a
Indentação, CRLF e BOM UTF-8 não alteram a validação semântica desse JSON.
Alterações nas perguntas ou nos rótulos exigem uma nova definição explícita de
experimento; não ajuste B depois de ver os scores para obter aprovação.
O corpus e os três arquivos YAML de ground truth precisam manter os bytes
registrados no RV-008. O experimento também verifica a identidade e o conteúdo
das passagens de referência e detecta alterações nos arquivos monitorados
durante a execução.
Execução no PowerShell
Com a .venv ativa e o terminal na raiz do repositório:
python -m pytest tests/unit/test_prefix_preserving_selector.py tests/unit/test_prefix_reranking_live.py -q
Resultado esperado: 22 testes aprovados. Depois:
python -m tests.smoke.smoke_prefix_reranking_live --output docs/validation/RV010_LIVE_RESULTS.json
O segundo comando faz chamadas reais de embeddings à OpenAI, usando a
configuração de ambiente existente, e inferência local do cross-encoder.
Não adiciona um novo provedor nem uma nova dependência de modelo. Os pesos
da revisão fixada serão reutilizados se já estiverem no cache. O dispositivo
padrão é CPU.

Uma execução completa pontua 125 pares em 25 chamadas ao scorer, além dos
embeddings necessários. O script mede o tempo de pontuar cinco chunks; não
pressupõe uma redução proporcional em relação aos vinte chunks do RV-008.
O tempo de carregar o modelo e o tempo de retrieval são registrados separadamente.
Como ler o resultado
Resultado	Significado
INPUT_CHANGED_DURING_RUN	Arquivos monitorados mudaram durante a execução; não usar a comparação como evidência estável.
BASELINE_DRIFT	A não reproduziu as métricas ou a seleção original do v0.3; investigar a diferença antes de comparar.
REGRESSION	A política restrita piorou alguma métrica acompanhada em A ou B.
READY_FOR_REVIEW	As verificações passaram e não houve regressão nas métricas acompanhadas; revisar ganhos, rótulos e passagens.


READY_FOR_REVIEW também pode ocorrer sem ganho em B. Consulte as comparações
de cada grupo: IMPROVEMENT, NO_FIRST_RANK_GAIN ou REGRESSION. Nenhum resultado
promove automaticamente a política para produção.

Para A, o JSON também compara a ordem com o replay e registra a diferença entre
os scores atuais de cinco pares e os scores anteriores de vinte pares. Diferenças
numéricas ou de ordem precisam ser examinadas com a versão e o dispositivo
registrados. Q25 continua exigindo revisão de autoridade documental; a regra
de preservação não corrige automaticamente o julgamento do cross-encoder.

Envie o resumo do terminal e o arquivo completo
docs/validation/RV010_LIVE_RESULTS.json para a análise seguinte. A avaliação de
abstenção, respostas e citações permanece pendente.
Validação da entrega
- 22 novos testes unitários aprovados.
- 138 testes aprovados no subconjunto do projeto disponível para esta entrega.
- CLI de ajuda verificada sem carregar modelos ou chamar APIs.
- A suíte completa do repositório Windows não foi executada neste ambiente.
- A execução real das 25 perguntas ainda não foi realizada; não há métricas
  novas de qualidade ou latência a declarar.
  