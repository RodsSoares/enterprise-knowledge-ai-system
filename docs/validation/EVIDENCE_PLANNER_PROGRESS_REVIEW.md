Checkpoint — unidades de evidência e planejamento orientado ao escopo
Registro: 08/11/2026. Projeto: Enterprise Knowledge AI System.
Decisão deste checkpoint
Os incrementos de representação de evidências e planejamento estão implementados
como fluxo experimental separado do terminal de respostas. A revisão assistida dos
planos ORC-001 a ORC-004 produzidos com gpt-6.1-sol encontrou evidências adequadas
para avançar à integração da geração. Não há promoção automática do modelo nem
aprovação de respostas finais: estas ainda não foram geradas neste fluxo.

O status dos artefatos continua planned_pending_review, com
semantic_review=not_performed. A avaliação descrita neste documento é uma revisão
assistida externa dos resultados salvos; não é um avaliador semântico implementado
na aplicação, nem uma homologação independente.
Problema que orientou a revisão
Encontrar o documento correto ou validar o formato das citações não assegurava uma
resposta correta. O fluxo anterior podia recuperar títulos e referências gerais,
expandir o contexto para dezenas de trechos e aplicar regras de outro processo.
Compartilhamento de dados com fornecedores era confundido com uso de dados de
fornecedores em IA. Também ocorreram confusão entre aprovação e revisão adicional,
perda de condições e cobertura incompleta das ações de incidente.

O diagnóstico está documentado nos arquivos de arquitetura 06 a 09. O presente
checkpoint registra a implementação e os experimentos subsequentes; não substitui
aqueles documentos nem atribui toda a causa ao chunking ou ao modelo.
O que foi implementado
Incremento 1 — representação estrutural
- Unidades de evidência com identidade, revisão da fonte, seção, papel estrutural,
  referências ao conteúdo canônico e textos de busca e leitura.
- Preservação de tabelas, cabeçalhos e contexto de seção; linhas de planilha com
  rótulos e coordenadas explícitos. Cabeçalhos da matriz são declarados e revisados,
  vinculados ao hash do arquivo, em vez de inferidos silenciosamente.
- Snapshot verificável, separado do contrato anterior de retrieval.
- Materialização controlada, sem truncamento silencioso; unidades que exigem
  revisão não podem ser usadas como evidência final pronta.
O snapshot utilizado contém 10 documentos, 113 unidades e 107 unidades pesquisáveis.
O cache documental contém 107 vetores de 1.536 dimensões. Estrutura preservada não
constitui garantia automática de atomicidade ou suficiência semântica.
Incremento 2 — escopo, recuperação e planejamento
- Interpretação da pergunta sem documentos ou gabaritos, com condições e exclusões
  ancoradas em trechos da própria pergunta; o escopo é congelado antes do plano.
- Referências documentais explícitas restringem a busca antes do ranking.
- Recuperação vetorial e lexical com fusão RRF, sem quota de documentos distintos;
  cache documental verificável e rastreamento dos candidatos.
- Plano de cobertura com suportes exatos, condições e ligação à pergunta.
- Contrato evidence-plan/2, distinguindo itens direct e category; condições
  obrigatórias para categorias, mas condições também são permitidas em itens diretos.
- Fluxo limitado a um complemento de busca ou expansão; esclarecimento e abstenção
  são saídas funcionais. Orçamento e consumo são registrados.
- Bundle ligado ao snapshot, escopo, plano e evidências por hashes; citações recebem
  identificadores determinísticos na materialização.
- Replay de planejamento permite reaproveitar requisições salvas sem refazer parsing,
  embeddings documentais ou recuperação. Comparações via terminal não alteraram a
  configuração original nem tornaram o modelo experimental padrão do produto.
O contrato valida estrutura e existência dos excertos. Não prova que um excerto
seja aplicável à pergunta ou que a cobertura seja suficiente.
Experimentos ORC-001
Pergunta: quais cuidados são exigidos antes de compartilhar dados com fornecedor externo?
Execução	Observação da revisão	Custo estimado registrado (USD)
Mini, execução inicial	Erro contratual: categoria com condição nula; também havia seleção indevida de IA	0.00373306
Mini, replay v2	Contrato válido, mas IA e incidente continuaram como requisitos diretos	0.00438640
GPT-4.1, comparação	Removeu IA/incidente, mas ainda atribuiu controles não sustentados à categoria Internal	0.02093200
GPT-6.1 Sol, comparação	Preservou classificações, controles e condições; sem impor IA/incidente	0.02900800


As comparações de modelo em ORC-001 mantiveram a requisição de planejamento:
pergunta, escopo, candidatos e ordem, instruções, schema e limite de saída.
Cada comparação consumiu uma chamada de planejamento. A execução inicial e o replay
v2 não isolam apenas o modelo, pois o contrato e as instruções foram revisados.

O resultado positivo com Sol é evidência direcional de capacidade do planejador sob
esses insumos. Uma execução por configuração não mede variância nem demonstra
superioridade geral, estabilidade ou causalidade exclusiva do modelo.
Revisão dos três novos casos
ORC-002 a ORC-004 executaram o fluxo normal com Sol tanto na interpretação do escopo
quanto no planejamento, reutilizando o cache documental. São perguntas diferentes;
não constituem uma comparação controlada com o escopo congelado de ORC-001.
Caso	Revisão semântica assistida	Unidades selecionadas	Caracteres de leitura	Custo estimado (USD)
ORC-002	Respeitou DOC-005 e a exclusão de IA; separou Public, Internal, Confidential e Restricted; condicionou transportadoras e exceções	4	1.452	0.02862074
ORC-003	Exigiu Information Security Owner + AI Governance Owner; distinguiu Additional Review do Data Owner; preservou ferramenta e caso de uso aprovados	2	697	0.02686658
ORC-004	Cobriu reporte, interrupção quando viável, registro, preservação, não apagar evidências sem orientação e cumprimento das instruções; preservou coordenação e condições	3	1.109	0.03225044


Caracteres são a soma de reading_text das unidades selecionadas, sem separadores
de apresentação. Não são tokens nem medida de qualidade ou economia ponta a ponta.

Fontes selecionadas: ORC-002, DOC-005; ORC-003, DOC-006 e DOC-012; ORC-004, DOC-006
e DOC-010. A aprovação de ferramenta/caso de uso não equivale à mera contratação de
um produto. No incidente, não se exigiu acionamento indiscriminado de todas as áreas.

Total dos três casos: 9 chamadas, custo estimado USD 0.08773776. Por caso:
interpretação do escopo, embedding da consulta e planejamento. Não houve novos
embeddings documentais, parsing ou geração de resposta. Valores são estimativas
calculadas pelas tarifas configuradas nos relatórios, não extratos de faturamento.
Verificações e limites da evidência
Na revisão de ORC-002 a ORC-004 foram verificados offline:
- integridade do snapshot e reconstrução das unidades a partir do conteúdo canônico;
- correspondência dos excertos e offsets ao texto de leitura;
- reconstrução dos bundles e equivalência dos hashes aos resultados salvos;
- revisão do conteúdo dos planos contra os suportes e o escopo das perguntas.
A verificação do snapshot usou o conteúdo canônico salvo. Não é uma nova validação
dos arquivos físicos presentes na máquina Windows do operador.

Testes de código têm escopo separado da revisão semântica:
- Operador: 725 passed, 4 warnings, suíte completa após o incremento 1.
- Ambiente de revisão, 08/11/2026: 57 passed, testes de unidades de evidência,
  snapshot, retriever, planner e runner; SDK simulado, sem chamadas pagas.
- O resultado de 725 testes não é apresentado como execução completa posterior a
  todas as revisões do incremento 2. Docling não está instalado neste ambiente de revisão.
Os quatro casos são de desenvolvimento e já orientaram decisões. Não são um conjunto
cego. Referências documentais estritas ainda não seguem remissões automaticamente;
governança acompanha metadados, sem resolução automática de conflitos ou ACL multiusuário.
Próximo incremento e critérios de aceitação
Integrar a geração ao bundle experimental sem substituir silenciosamente o baseline.
O contrato da resposta deve vincular pergunta, escopo, plano e evidências. Reaproveitar
somente o contrato antigo de citações não cobre esse vínculo.

A avaliação deve verificar:
1. Citações existentes e rastreáveis ao bundle efetivamente usado.
2. Afirmações sustentadas, sem obrigações adicionais inventadas.
3. Preservação das condições, exceções, exclusões e da diferença entre aprovação e revisão.
4. Cobertura das necessidades relevantes do plano, sem tornar o plano uma autoridade
   superior às fontes: discrepâncias devem ser sinalizadas, não reproduzidas.
5. Abstenção ou esclarecimento quando necessário e custo/latência do fluxo completo.
Primeiro revisar respostas finais nos casos de desenvolvimento. Depois congelar a
configuração candidata e avaliar os casos reservados antes de promover qualquer modelo
ou fluxo. Não criar ciclos ilimitados de revisão nem declarar maturidade de produção
com base nesses quatro planos.
Artefatos de suporte
Arquivos em docs/validation/, preservando as execuções originais:
- EVIDENCE_UNITS_SNAPSHOT_local.json
- EVIDENCE_UNITS_CONFIG.json
- EVIDENCE_PLANNER_ORC001_RESULTS_local.json
- EVIDENCE_PLANNER_ORC001_REPLAY_RESULTS_local.json
- EVIDENCE_PLANNER_ORC001_GPT41_RESULTS_local.json
- EVIDENCE_PLANNER_ORC001_GPT61SOL_RESULTS_local.json
- EVIDENCE_PLANNER_ORC002_GPT61SOL_RESULTS_local.json
- EVIDENCE_PLANNER_ORC003_GPT61SOL_RESULTS_local.json
- EVIDENCE_PLANNER_ORC004_GPT61SOL_RESULTS_local.json
O cache EVIDENCE_UNIT_EMBEDDINGS_local.json permanece um artefato operacional local;
não é necessário incluí-lo no commit documental. Configurações locais de execução
não são promovidas a configurações padrão por este checkpoint.