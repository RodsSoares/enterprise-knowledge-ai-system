Entrega 1 — contratos mínimos e avaliação
Status: especificação v1 com contratos/coordenador offline implementados; fluxo padrão inalterado.
Escopo fechado
Adicionar avaliação de pergunta/evidências após a busca inicial, seleção de texto
canônico e no máximo uma ação complementar. Preservar o fluxo atual como baseline.
A geração desta entrega é experimental, sem selo de aprovação semântica: o
verificador de respostas pertence à entrega 2.

Não criar um módulo por contrato. Implementação prevista: contracts.py,
coordinator.py e um adapter para avaliações semânticas, reutilizando os serviços
atuais. A quantidade de arquivos deve seguir responsabilidade e coesão.
Contratos mínimos
Contrato	Conteúdo	Validação obrigatória
AssessmentRequest	schema_version, run_id, question, question_hash, snapshot_id, evidence_set_hash, passages, section_catalog	Construído pelo código; textos e metadados vêm do catálogo
QueryScope	action, sender, recipient, subject, known_conditions, unknown_conditions	Campos desconhecidos aceitam null; condições devem indicar origem na pergunta ou evidência
AssessmentResult	hashes de entrada, scope, requirements, passage_decisions, gaps, decision, lookup, clarification	Campos extras rejeitados; decisões por todos os chunks apresentados, sem duplicação
PassageDecision	chunk_id, applicability, requirement_ids, supporting_spans, reason	IDs existentes; enum direct/conditional/background/irrelevant; spans exatos
LookupRequest	kind, query ou document_id/section_ids, gap_ids	União exclusiva search/expand_document_section; sem caminho livre; seção existente
SelectedEvidence	snapshot_id, chunk_ids, conditions_to_preserve	Texto reconstruído pelo código; E1/E2 atribuídos só após seleção final
Stage1Outcome	status, answer ou clarification ou error, trace	Payload exclusivo; saída answered marcada semantic_review=not_performed


decision: sufficient, retrieve, clarify, abstain. status final: answered,
abstained, clarification_required, error, budget_exceeded. Reutilizar o contrato
StructuredAnswer para answered/abstained sem alterar seus campos.

Spans usam índices de caracteres Unicode Python, início inclusivo e fim exclusivo,
sobre o texto canônico original: 0 <= start < end <= len(text). O trecho deve
conferir exatamente. Correspondência textual não demonstra sustentação semântica.
Exigir suporte para decisões direct/conditional; não exigir excerto artificial
para irrelevant. Razões curtas servem à auditoria, sem solicitar raciocínio privado.

sufficient exige pelo menos uma passagem selecionada e cobertura declarada de
todos os requisitos materiais; o código verifica referências, não verdade lógica.
retrieve exige lacuna e ação; clarify exige pergunta material ao usuário;
abstain exige motivo. Payloads incompatíveis com a decisão devem ser rejeitados.
Passagens background/irrelevant não entram por padrão no contexto de geração.
Passagens conditional precisam levar sua condição junto ao trecho.
Execução e identidade
1. Busca inicial existente; fornecer passagens e catálogo limitado de seções.
2. Uma chamada de assessment.
3. Se retrieve: executar uma busca OU expansão e reavaliar uma vez.
4. Se sufficient: construir contexto canônico e chamar o gerador existente.
5. Caso contrário: esclarecer, abster-se ou retornar erro explícito.
Segunda solicitação de retrieval encerra como insuficiência após limite, sem
executar ferramenta adicional. Falhas de API/schema são erros operacionais.
Não converter falha técnica em falta de conhecimento.

Na entrega 1: duas chamadas LLM no caminho normal, no máximo três com reavaliação.
As três/seis chamadas da proposta arquitetural completa incluem a revisão da
entrega 2. Retries automáticos: zero. Nenhum retorno ao retrieval após geração.

O snapshot deve incluir hashes dos arquivos físicos, registro, chunks normalizados
e configuração de parsing/chunking. Registrar SHA do código separadamente.
Hashes de avaliações vinculam pergunta e conjunto exato de evidências; uma
avaliação não pode ser aplicada a outro contexto. IDs E locais não são IDs de busca.
O namespace sintético local não representa ACL multiusuário implementada.
Avaliação preparada
Arquivo: [orchestration_stage1_cases.json](../../data/ground_truth/orchestration_stage1_cases.json).
Dez casos: quatro de desenvolvimento e seis reservados. Definições congeladas
antes de ajustar prompts; execução e evidências físicas ainda pendentes.
As referências usam o corpus sintético e trechos já inspecionados. O runner deverá
confirmar sua presença no snapshot local. Documentos indicados são referências
de revisão, não um conjunto exclusivo de fontes válidas.

Os casos reservados foram escritos neste estudo e não constituem holdout cego
independente. Não usar seus resultados para ajustar prompts e continuar chamando
os mesmos casos de validação independente. Qualquer mudança de definição exige
nova versão e registro do motivo.

O gerador/assessor recebe apenas pergunta, evidências e metadados permitidos.
Nunca enviar expected_outcome, required_checks ou forbidden_behaviors. A ausência
de material radioativo está definida em canonical_facts, usado só pelo avaliador.
Comparação e rubrica
Executar baseline e candidato no mesmo snapshot, modelo gerador e parâmetros;
registrar separadamente modelo/prompt do assessor. Capturar evidências completas,
ações, hashes, consumo de todas as etapas e tempos. Contextos salvos servem para
avaliar seleção sem parsing/embeddings; não demonstram recuperação complementar.
Esta última exige catálogo completo e índice, ou replay de ferramenta explicitamente
rotulado. Não simular uma melhoria de busca usando o gabarito.

Revisão humana por caso: resultado adequado, requisitos atendidos, condições
preservadas, pertinência, suporte de cada afirmação e citações. Marcar cada item
PASS/FAIL/NOT_ASSESSABLE com trecho e motivo. Falta de evidência verificável bloqueia
aprovação, não conta como PASS. Erro crítico: autorização inventada, condição
material removida ou obrigação de outro processo apresentada como geral.

Gate para candidato experimental: todos os controles determinísticos passam;
zero erro crítico nos casos revisados; nenhuma regressão do baseline sem decisão
explícita; corrigir os desvios conhecidos de escopo; registrar qualidade e custo
por caso, sem esconder falhas em uma média. Dez casos não sustentam alegação de
confiabilidade de produção. A entrega 1 não mede falsos PASS de um revisor ausente.
Verificação funcional enxuta
Cobrir: ID/hash/spans inválidos; condições preservadas; expansão traz tabela;
segunda ação bloqueada; erro/timeout distinto de abstenção; pergunta geral responde
por categorias enquanto autorização concreta ambígua pede esclarecimento.
Adicionar um fixture isolado com instrução maliciosa em documento para verificar
que conteúdo não altera ferramentas/limites. Não modificar o corpus para esse teste.
Conflitos de autoridade devem usar metadados e textos físicos verificados; não
fabricar uma versão histórica ausente para completar cenário.
Antes de qualquer rodada paga
Confirmar SHA e suíte local; registrar snapshot; escolher explicitamente modelos
e configurar limites cumulativos de entrada/saída, deadline e custo máximo da
rodada. Esses valores permanecem pendentes: implementar offline com providers
falsos é possível, mas execução paga deve falhar se configuração estiver ausente.
Não usar preço presumido ou confidence do LLM como autorização de gasto.
Integridade do conjunto v1
SHA-256 dos bytes de orchestration_stage1_cases.json: 9d3f8915fdb72aef587633bc5085707cd56a5b1d4c233b3cd93ae7fea0e230e4.
Congelar também o snapshot e os prompts antes da execução comparativa. O hash
acima identifica definições de casos, não resultados nem aprovação do sistema.
Implementação offline dos contratos e coordenador
Este incremento implementa a máquina de estados e a fronteira de validação em:
- app/orchestration/__init__.py;
- app/orchestration/contracts.py;
- app/orchestration/coordinator.py;
- tests/unit/test_stage1_orchestration.py.
O coordenador exige execution_mode="offline" no retriever, assessor e gerador.
Essa declaração é uma convenção de integração, não sandbox ou mecanismo de
segurança. Não existe adapter pago neste incremento; não marcar componentes
reais como offline para contornar a restrição.

O assessor implementa assess(AssessmentRequest) -> str (JSON); o gerador reutiliza
generate(question, EvidenceContext) e a validação existente de StructuredAnswer.
O retriever oferece retrieve(query, top_k=20) com candidatos cujo .chunk
corresponde exatamente ao catálogo canônico. Nenhum prompt semântico foi ajustado
com os casos reservados. Os testes usam respostas simuladas; não demonstram que
um modelo identifica relevância ou suficiência corretamente.

AssessmentResult também exige schema_version e run_id iguais aos da requisição.
requirements, gaps e referências correspondentes são identificadores textuais
locais únicos. Cada condição conhecida registra source="question" ou um chunk
apresentado. O contrato verifica a origem declarada, não sua interpretação.
PassageDecision.condition é obrigatório para conditional e null nos demais
estados. O texto original completo segue ao gerador; a condição interpretada é
registrada no trace, sem substituir ou acrescentar texto à fonte canônica.

Os limites locais são 40 passagens, 64.000 caracteres da requisição de avaliação,
32.000 caracteres do contexto de geração e 30 segundos entre fronteiras de
execução. Nenhum limite permite truncar silenciosamente uma seção expandida.
O deadline é verificado antes/depois das chamadas síncronas; não cancela uma
chamada bloqueada. O adapter real precisará de timeout por chamada e orçamento
cumulativo de tokens/custo antes de habilitar execução paga.

O trace registra requisições/resultados de assessment e ações executadas. Seu
snapshot é explicitamente canonical_chunks_only: inclui conteúdo e proveniência
dos chunks, mas ainda NÃO inclui arquivos físicos, configuração nem registro.
A integração do manifest completo e do DocumentRegistry permanece pendente.
A saída mantém semantic_review="not_performed"; não apresentar como validada
semanticamente. O serviço atual e a CLI continuam sem mudanças.
Validação local
python -m pytest tests/unit/test_stage1_orchestration.py -q
python -m pytest -q
Resultado direcionado no ambiente de desenvolvimento: 29 passed. Os cenários
incluem seleção canônica, expansão com tabela, busca complementar, rejeição da
segunda busca, esclarecimento/abstenção, falhas de contrato/provedor, limites e
recusa de ferramenta não autorizada. O fixture de instrução maliciosa verifica
o bloqueio determinístico de ações; não comprova resistência semântica do LLM.

Próximo incremento funcional: conectar catálogo/registro e manifest, implementar
adapter semântico com orçamento e runner comparativo; então executar os dez casos
congelados. A entrega 1 completa ainda depende desses componentes e avaliação.

Regressão disponível: 586 passed em 2,76 s, excluindo os oito arquivos dependentes
de Docling/integração indisponíveis neste ambiente. Não substitui a suíte completa Windows.
Integração do registro, adapter e comparador — incremento seguinte
Esta seção substitui as limitações de integração do incremento offline acima.
O fluxo padrão ask_knowledge continua inalterado e nenhum modelo foi executado
para validar qualidade nesta entrega.
Arquivos
- app/orchestration/snapshot.py: manifest de arquivos físicos, registro,
  metadados, chunks, versões de dependências e hashes do código de ingestão.
- app/orchestration/live_provider.py: avaliação estruturada, wrappers e
  orçamento compartilhado por embeddings, baseline e candidato.
- app/orchestration/coordinator.py: aceita execução real somente com opção
  explícita, snapshot validado e o mesmo cliente de orçamento nos três adapters.
- app/scripts/compare_stage1_orchestration.py: prepara snapshot sem API e executa
  um par baseline/candidato, com dry-run padrão e resultado pendente de revisão.
- tests/unit/test_stage1_live.py: integração com SDK falso, sem rede.
- docs/validation/STAGE1_RUN_CONFIG.example.json: modelo de configuração;
  preços null são intencionais e impedem execução antes do preenchimento.
O snapshot é verificado contra os arquivos locais e o registro antes da execução.
Uma alteração exige prepará-lo novamente. Hashes detectam divergência, não fornecem
assinatura/autenticidade. O manifest referencia caminhos relativos à raiz do repo;
execute os comandos dessa raiz. O parser mantém os defaults atuais, com hashes e
versões registrados; não se promete reprodução bit a bit entre plataformas.

O assessor recebe metadados tipados serializados por passagem e a data as_of.
Isso disponibiliza versão, status e autoridade, mas não implementa autorização
multiusuário nem uma regra automática de precedência. O gerador continua recebendo
os trechos originais, sem transformar o registro em conteúdo de evidência.
Preparar uma vez, sem embeddings nem geração
python -m pytest tests/unit/test_stage1_orchestration.py tests/unit/test_stage1_live.py -q
python -m app.scripts.compare_stage1_orchestration prepare --output docs/validation/STAGE1_CORPUS_SNAPSHOT_local.json
A preparação usa parsing local (pode baixar modelos de parsing/OCR), captura o
registro e salva todos os chunks. Não requer OPENAI_API_KEY. O mesmo snapshot é
reutilizado pelas comparações seguintes, sem refazer parsing.
Configuração explícita e prévia
Copiar o exemplo para docs/validation/STAGE1_RUN_CONFIG_local.json. Preencher
modelos e preços por milhão de tokens conforme a conta/provedor, ajustar as_of
e escolher limites da rodada. Os números do exemplo são limites de planejamento,
não estimativas de custo nem autorização de execução. Se um modelo for usado nos
dois papéis, basta uma entrada dele no mapa de preços.

Não há preço embutido nem escolha automática de modelo. O modelo de geração é
idêntico nos dois braços; o assessor pode usar outro modelo configurado. O custo
reportado é estimado pelos preços fornecidos, sem descontos de cache ou créditos.
python -m app.scripts.compare_stage1_orchestration run --source docs/validation/STAGE1_CORPUS_SNAPSHOT_local.json --case ORC-001 --config docs/validation/STAGE1_RUN_CONFIG_local.json --output docs/validation/STAGE1_ORC001_PLAN_local.json
Sem --execute, apenas valida e grava o plano: zero chamadas API. O arquivo de
saída deve ser novo. Não colocar credenciais no JSON.

Após revisar o plano, a execução paga é explicitamente solicitada por:
python -m app.scripts.compare_stage1_orchestration run --source docs/validation/STAGE1_CORPUS_SNAPSHOT_local.json --case ORC-001 --config docs/validation/STAGE1_RUN_CONFIG_local.json --output docs/validation/STAGE1_ORC001_COMPARISON_local.json --execute
OPENAI_API_KEY é necessária somente para essa execução. O comando processa um
caso, não a suíte inteira. Use primeiro os quatro casos de desenvolvimento;
preserve os seis reservados até congelar prompt/modelos.
Limites, comparabilidade e avaliação
O índice vetorial e BM25 é construído uma vez por comparação. A busca inicial é
compartilhada, garantindo pool idêntico e evitando segundo embedding da pergunta.
O baseline mantém o builder atual de expansão; o candidato recebe o pool e faz
assessment. Busca complementar pode gerar um embedding novo; expansão de seção
não exige embeddings. Não há cache persistente de embeddings entre comandos.

Uma execução normal realiza cinco chamadas pagas: embedding do corpus, embedding
da pergunta, geração baseline, assessment e geração candidata. O máximo estrutural
é sete com busca complementar e reavaliação. Repetir o mesmo query usa o cache local.
O índice é custo compartilhado, e o ledger registra todas as chamadas da rodada.

Antes de cada chamada é reservada uma estimativa conservadora de entrada (bytes
UTF-8 do payload mais 8.192 de margem), saída máxima e custo correspondente. Essa
reserva não é tokenização exata nem garantia de faturamento: o consumo real pode
ser diferente. Usage acima da reserva bloqueia chamadas seguintes e encerra a
rodada. Usage ausente/falha mantém a reserva inteira, marca falha e bloqueia
continuação. A margem pode barrar uma chamada que caberia com contagem exata.

O deadline é cumulativo e determina o timeout de cada chamada, limitado a 60 s;
retries zero. O candidato não recebe nova cota após o baseline. Falha no baseline
encerra o par e deve ser registrada como comparação incompleta, não vitória do
candidato. Limites de caracteres continuam protegendo contextos e assessments.

O resultado registra prompts, hash do schema, hashes do código, configuração,
snapshot, pergunta, respostas, trace e ledger. O ledger é salvo antes e depois
de cada chamada para preservar reservas/consumo em caso de interrupção. A API
não recebe gabaritos, critérios esperados ou perguntas de outros casos.

executed_pending_review indica execução concluída, não qualidade aprovada.
Erros operacionais retornam execution_failed e código de saída 1. Comparar as
respostas com a rubrica já definida; semantic_review=not_performed permanece
correto, pois o revisor de afirmações pertence à entrega 2.

Validação deste incremento: 46 testes direcionados aprovados; regressão disponível
603 passed em 2,94 s, com os mesmos oito arquivos de Docling/integração excluídos.
Todas as chamadas nos testes usam SDK falso. Nenhum resultado semântico real foi produzido.
Ajuste após a primeira execução ORC-001
Ver [diagnóstico da execução](../validation/STAGE1_ORC001_ANALYSIS.md).
O primeiro assessment falhou por IDs inconsistentes, decisões incompletas,
offsets incorretos e suficiência contraditória com lacunas. Também apresentou
erros semânticos; a resposta não foi promovida nem corrigida automaticamente.

A fronteira externa de LiveAssessor agora recebe supporting_spans somente com
text. resolve_assessment_quotes localiza cada excerto exato e único no chunk
canônico e calcula start/end. O contrato interno e o assessor offline mantêm
spans completos. Não há correção de IDs, relevância ou suficiência nessa conversão.
A requisição é registrada antes de avaliar, inclusive quando o resultado falha;
AssessmentContractError registra mensagem segura no trace. Os demais erros
continuam expondo apenas tipo, sem conteúdo potencialmente sensível do provedor.

O exemplo FakeSDK acompanha o novo schema externo. A avaliação salva original não
pode ser reenviada como se obedecesse ao schema novo. Prompt/schema alterados são
registrados na próxima execução. Testes direcionados: 52 passed, sem chamadas API.