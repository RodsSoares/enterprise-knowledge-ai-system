Incremento 2 — escopo e seleção de evidências
Pré-requisito: os sete arquivos do incremento 1 e o snapshot do corpus validado.
Resultado: bundle de evidências ligado ao escopo e ao plano de cobertura.
Ainda não gera resposta e não muda ask_knowledge nem o baseline.

Revisão atual: evidence-plan/2. Para o resultado ORC-001 já executado, usar o
replay descrito ao final; não repetir toda a indexação/interpretação/busca.
Arquivos novos
- app/retrieval/evidence_unit_retriever.py: busca híbrida e cache de embeddings.
- app/orchestration/evidence_planner.py: contratos, escopo, planejamento e fluxo limitado.
- app/scripts/plan_evidence_units.py: preflight/dry-run e execução explícita.
- tests/unit/test_evidence_unit_retriever.py: ranking filtrado, cache e vetores.
- tests/unit/test_evidence_planner.py: escopo isolado, evidências e transições.
- tests/unit/test_plan_evidence_units.py: runner/cache/ledger com SDK simulado.
- docs/validation/EVIDENCE_PLANNER_IMPLEMENTATION_GUIDE.md: este guia.
Nenhum arquivo anterior precisa ser substituído. Nenhuma chamada paga foi feita
durante o desenvolvimento. Não é necessário refazer parsing ou o snapshot existente.
Validação local sem API
python -m pytest tests/unit/test_evidence_unit_retriever.py tests/unit/test_evidence_planner.py tests/unit/test_plan_evidence_units.py -q
O runner reutiliza STAGE1_RUN_CONFIG_local.json: campos de modelo de assessment,
embedding, preços, orçamento e as_of. Os campos de geração continuam obrigatórios
por compatibilidade com o carregador, mas não são utilizados nesta etapa.
Valores configurados são estimativas fornecidas pelo operador, não tarifas atuais
verificadas por este incremento. O arquivo não é alterado automaticamente.

Preflight, sem API e sem criação de cache:
python -m app.scripts.plan_evidence_units --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json --config docs/validation/STAGE1_RUN_CONFIG_local.json --question "Quais cuidados a política exige antes de compartilhar dados com um fornecedor externo?" --embedding-cache docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json --output docs/validation/EVIDENCE_PLANNER_ORC001_PLAN_local.json
dry_run significa que snapshot/configuração/cache existente passaram no preflight.
Não significa que o modelo produzirá um plano válido. A saída informa quantidade
nominal/máxima de chamadas e os limites configurados.

Execução paga explícita, após verificar o plano e o orçamento:
python -m app.scripts.plan_evidence_units --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json --config docs/validation/STAGE1_RUN_CONFIG_local.json --question "Quais cuidados a política exige antes de compartilhar dados com um fornecedor externo?" --embedding-cache docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json --output docs/validation/EVIDENCE_PLANNER_ORC001_RESULTS_local.json --execute
Não usar o mesmo nome para plano e resultado. Não apagar cache válido para repetir
perguntas: a segunda execução reutiliza embeddings documentais. Se mudar texto,
identidade de unidade ou modelo, o cache é recusado; usar novo nome após revisar.
Interrupção durante gravação pode deixar arquivo incompleto; erro de leitura não
dispara cobrança para regeneração silenciosa. Preservar o arquivo para diagnóstico.
Fluxo e contratos
1. O LLM interpreta apenas a pergunta, sem documentos/gabaritos. Condições conhecidas
   e exclusões exigem excertos exatos da pergunta. O código resolve posições.
2. O código congela o escopo e extrai referências DOC-000 explícitas. Referência
   desconhecida termina sem busca genérica. Nesta versão, referências explícitas
   restringem a busca àqueles documentos, inclusive no complemento.
3. Busca vetorial e BM25 usam o mesmo texto de busca do catálogo, filtrando antes do
   ranking. RRF usa k=60; retorna até 20 unidades, sem quota de documentos distintos.
   Scores e rankings de cada canal ficam no trace. O filtro PT/EN de palavras
   funcionais existente é aplicado somente à consulta lexical, com versão e texto
   filtrado registrados. Sem tradução lexical automática.
4. O planejador propõe itens de cobertura com suportes aninhados e ação exclusiva:
   complete, search, expand, clarify ou abstain. O código atribui IDs C1/C2 após
   validar. Não há reprodução de hashes nem offsets pelo modelo.
5. Uma busca ou expansão complementar pode ocorrer. A reavaliação mantém o escopo.
   Após ela, não há terceiro ciclo. Expansão inclui pai e filhos diretos do alvo;
   excesso de quantidade/tamanho falha explicitamente, sem truncamento silencioso.
6. Complete materializa apenas unidades ready citadas, atribui E1/E2 e vincula
   snapshot, escopo, plano, evidências e condições em hashes verificáveis.
O plano guarda os excertos e sua localização no reading_text; as unidades do
bundle preservam suas referências ao conteúdo canônico. Isso ainda não é um mapa
de entailment por afirmação de resposta: não há resposta neste incremento.

O escopo possui foco/tipo, condições, exclusões e referências documentais. Ainda
não decompõe participantes em campos separados. A presença de um quote não prova
que a interpretação seja correta; plano e suficiência continuam probabilísticos.
Não se exige que o modelo classifique todos os candidatos. Não selecionados são
registrados como not_selected, sem motivo semântico inventado pelo código.
Limites e custos
- Sem cache: normal = 4 chamadas (embeddings das unidades, escopo, embedding da
  consulta, plano); máximo = 6 com busca complementar e reavaliação.
- Com cache: normal = 3; máximo = 5. Expansão não demanda embedding novo.
- O LLM recebe evidências somente no planejamento. Indexar antes da interpretação
  não expõe os documentos à chamada que define o escopo.
- Até 40 candidatos após complemento; requisição até 64.000 caracteres; bundle
  até 16.000 caracteres de leitura. São limites estruturais, não limites de tokens.
- BudgetedClient existente controla consumo cumulativo de todas as chamadas,
  deadline e reservas conservadoras por chamada. Se faltar saldo para a próxima
  etapa, encerra com budget_exceeded; não garante saldo de todo o caminho antecipado.
- Zero retries automáticos. Cache de consulta vale dentro da execução; apenas os
  embeddings documentais são persistidos entre execuções.
Não há promoção automática nem estimativa de economia baseada só no bundle menor.
A próxima etapa de geração acrescentará sua própria chamada e limites ao fluxo.
Como interpretar o resultado
planned_pending_review: contrato/plano/bundle construídos, aguardando revisão
semântica. Não é resposta aprovada. clarification_required e abstained são
saídas funcionais; error, execution_failed e budget_exceeded são operacionais.
O relatório guarda requisições, escopo, pool, ações, seleção, bundle e uso observado.
Revisar se as categorias pertinentes entraram e se processos alheios ficaram fora.
Não basta contar unidades ou encontrar DOC-005.

Para ORC-001, verificar categorias e controles do compartilhamento sem impor IA.
Se isso falhar, o trace deve mostrar se a causa foi escopo, busca, seleção ou
contrato, antes de qualquer ajuste. Não há gabarito fornecido aos modelos.

Limites atuais: referência documental estrita não segue remissões para outros
documentos; governança acompanha metadados, sem resolução automática de conflitos;
não há ACL multiusuário. Não atribuir validade semântica a scores ou JSON válido.

Depois da instalação, executar também python -m pytest -q. Na entrega, os testes
de Docling dependem da máquina local; as chamadas de teste ao SDK são simuladas.
Revisão após a primeira execução real de ORC-001
A primeira execução encerrou com PlanningContractError: um item category tinha
condition=null. O schema aceitava essa combinação, mas o validador a rejeitava.
Além disso, o plano incluiu uso de dados em IA como requisito direto, apesar do
escopo geral de compartilhamento externo. Corrigir apenas o JSON não resolveria
o desvio semântico. Os cinco excertos eram exatos, e a tabela de classificação
estava na posição 4 do pool; canais aprovados estavam na posição 10.

Consumo registrado naquela execução: quatro chamadas, custo estimado de
US$ 0,00373306 pelas tarifas configuradas. Cache verificado: 107 vetores de 1.536
dimensões. Esses dados são resultados históricos, não previsão da próxima chamada.

Mudanças delimitadas:
1. Schema com alternativas direct/category. A alternativa category exige string
   em condition; null agora é proibido tanto no schema quanto no validador. String
   vazia também é rejeitada localmente, com localização explícita do campo.
2. Cada item inclui scope_link: trecho exato da pergunta e explicação curta da
   relação entre a regra e a ação solicitada. O código calcula o intervalo do trecho.
3. Instruções distinguem identidade de entidades de identidade do processo, pedem
   categorias separadas quando controles diferem e preservam condição de exceção.
4. Bundle/relatório passam a declarar evidence-plan/2. Relatórios antigos são
   preservados; a rotina de replay lê a requisição antiga, não aprova seu plano.
5. O runner ganha replay de uma única chamada, mantendo os insumos originais.
scope_link melhora rastreabilidade e exige uma decisão explícita do modelo; NÃO
comprova equivalência semântica. Uma regra de IA pode ainda ser classificada
erroneamente com um trecho válido da pergunta. O teste de contrato documenta esse
limite. Não há filtro por palavra IA, lista de documentos proibidos ou gabarito.
O prompt e o schema mudam juntos: o experimento avalia essa intervenção conjunta,
não isola o efeito de cada alteração. O ganho semântico permanece não demonstrado.
Instalação desta revisão
Substituir somente estes cinco arquivos por suas versões completas:
- app/orchestration/evidence_planner.py
- app/scripts/plan_evidence_units.py
- tests/unit/test_evidence_planner.py
- tests/unit/test_plan_evidence_units.py
- docs/validation/EVIDENCE_PLANNER_IMPLEMENTATION_GUIDE.md
Os arquivos de chunking, snapshot, cache e retrieval permanecem compatíveis.
python -m pytest tests/unit/test_evidence_planner.py tests/unit/test_plan_evidence_units.py tests/unit/test_evidence_unit_retriever.py -q
Replay sem repetir etapas anteriores
Dry-run:
python -m app.scripts.plan_evidence_units --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json --config docs/validation/STAGE1_RUN_CONFIG_local.json --replay-source docs/validation/EVIDENCE_PLANNER_ORC001_RESULTS_local.json --output docs/validation/EVIDENCE_PLANNER_ORC001_REPLAY_PLAN_local.json
Execução de UMA chamada paga de planejamento:
python -m app.scripts.plan_evidence_units --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json --config docs/validation/STAGE1_RUN_CONFIG_local.json --replay-source docs/validation/EVIDENCE_PLANNER_ORC001_RESULTS_local.json --output docs/validation/EVIDENCE_PLANNER_ORC001_REPLAY_RESULTS_local.json --execute
Não passar --question nem --embedding-cache no modo replay. Ele reutiliza a pergunta,
o escopo validado, candidatos, ordem, metadados e alvos de expansão da requisição
inicial. Antes de cobrar, reconstrói essa requisição a partir do snapshot e compara
os conteúdos. Modelo, as_of e limite de saída devem coincidir com a execução original.
Campos alterados ou referências desconhecidas causam falha no preflight.

O orçamento efetivo é limitado a uma chamada; não há parsing, novos embeddings,
nova interpretação de escopo, busca ou geração de resposta. Se o planejador solicitar
complemento, a saída será replay_requires_lookup e a operação não será executada.
Isso é um experimento isolado do planejador, não uma execução ponta a ponta.

Após executar, revisar: quatro classificações e controles pertinentes; canais
aprovados; condições preservadas; nenhum requisito do processo de IA imposto.
Exceções, se incluídas, precisam permanecer condicionais. Um JSON válido sozinho
não é sucesso. Se repetir o desvio, não acrescentar campos indefinidamente: comparar
a capacidade do modelo sob o mesmo contexto antes de ampliar a arquitetura.

A requisição real enviada foi reconstruída offline com sucesso: 20 candidatos,
escopo e ordem preservados. Não houve chamada paga durante esta revisão.