Revisão da geração a partir de planos de evidência — ORC-001 a ORC-004
Data do registro: 08/11/2026. Contrato: evidence-answer/1.
Modelo solicitado e retornado nas quatro gerações: gpt-6.1-sol.
Resultado e decisão
As quatro respostas de desenvolvimento foram consideradas adequadas nesta revisão
assistida contra os planos e as fontes fornecidas. Não foram identificados, nessas
execuções, os desvios anteriores de inclusão indevida de IA, confusão entre aprovação
e revisão, perda de condições ou omissão das ações materiais de incidente.

Há evidência suficiente para avançar à integração em uma única execução de pergunta,
recuperação, planejamento e geração. Não há promoção automática de modelo nem
conclusão de prontidão para produção.

O status original dos quatro relatórios permanece answered_pending_review, com
semantic_review=not_performed. A aplicação não executou uma avaliação semântica:
este documento registra a revisão assistida externa realizada posteriormente.
Os JSONs originais não foram modificados para parecerem automaticamente aprovados.
Escopo do experimento
Cada execução recebeu um plano completo já salvo, reconstruído contra o snapshot
canônico, e realizou uma única chamada de geração. Não houve parsing, busca, novos
embeddings, interpretação de escopo ou replanejamento nestas quatro execuções.

Foram mantidos modelo, instruções de geração, schema e limite de saída de 8.000 tokens.
Cada caso possuía seu próprio orçamento de uma chamada e USD 0,25, sem orçamento
compartilhado entre os processos. A reserva de dry-run não equivale ao consumo real.

A entrada vincula pergunta, escopo, snapshot, plano, evidências e metadados. Cada
claim refere-se a um coverage_id e às citações dos suportes daquele item. A aplicação
apresenta as condições do plano junto às afirmações, em vez de depender de sua
reprodução pelo gerador. Isso melhora a preservação estrutural, mas não prova que o
texto gerado respeita semanticamente as condições.
Revisão por caso
Caso	Pedido	Resultado da revisão assistida
ORC-001	Cuidados antes de compartilhar dados com fornecedor externo	Separou as quatro classificações e seus controles. Restringiu regras de transportadoras e exceções às respectivas condições. Não acrescentou IA nem resposta a incidente.
ORC-002	Requisitos segundo DOC-005, com exclusão explícita de IA	Respeitou o documento solicitado e a exclusão. Preservou os controles de Public, Internal, Confidential e Restricted, além das condições de transportadoras e exceções.
ORC-003	Aprovações para usar dados confidenciais de fornecedor em IA	Identificou Information Security Owner e AI Governance Owner como aprovadores e Data Owner como revisão adicional. Exigiu aprovação tanto da ferramenta quanto do caso de uso.
ORC-004	Ações após envio acidental de dados confidenciais a fornecedor	Cobriu reporte imediato, interrupção quando viável, registro, preservação de evidências, não instruir exclusão antes de orientação e cumprimento das instruções. Preservou a coordenação de Segurança da Informação e a condição de materialidade.


Fontes utilizadas: ORC-001/002, DOC-005; ORC-003, DOC-012 e DOC-006;
ORC-004, DOC-010 e DOC-006. A revisão considerou os textos das fontes e o escopo,
não apenas a presença desses documentos ou a validade do JSON.

Observação de apresentação: em ORC-002, os nomes das classificações nas condições
permanecem em inglês, como no plano. É uma questão de localização da apresentação,
sem alteração identificada do sentido. Não houve ajuste de código ou prompt entre
os quatro resultados para corrigir esse aspecto.
Consumo registrado
Caso	Afirmações	Unidades de evidência	Tokens de entrada	Tokens de saída	Custo estimado USD
ORC-001	7	4	4244	467	0.013158
ORC-002	7	4	4435	474	0.013610
ORC-003	3	2	3044	240	0.008488
ORC-004	8	3	4192	444	0.012824


Total: 4 chamadas, 15.915 tokens de entrada, 1.625 tokens de saída,
custo estimado USD 0.048080. ORC-002 a ORC-004 somaram USD 0,034922.

Custos calculados pelas tarifas configuradas de USD 2 por milhão de tokens de entrada
e USD 10 por milhão de saída. São estimativas dos relatórios, não extratos de
faturamento nem confirmação de preços atuais. Não incluem ingestão, embeddings,
planejamento, experimentos anteriores ou eventual nova execução integrada.
Verificações de integridade
As quatro execuções foram verificadas offline:
1. Reconstrução das unidades a partir do snapshot canônico salvo.
2. Reconstrução do escopo, último pedido de planejamento, plano completo e bundle.
3. Correspondência entre a requisição de geração e os insumos reconstruídos.
4. Validação das claims, IDs de cobertura e referências aos suportes de cada item.
5. Correspondência da apresentação salva às condições do plano e à resposta validada.
6. Correspondência do hash da requisição da API ao ledger e da saída bruta à resposta.
Essa verificação não reabre nem revalida os arquivos físicos na máquina Windows.
Hashes detectam inconsistências, não autenticam arquivos. Referências válidas não
comprovam entailment: um texto incorreto ainda pode citar uma evidência existente.
Testes de software
O operador executou a suíte completa com 787 passed, 4 warnings in 76.89s,
incluindo a integração com Docling. Os avisos reportados referem-se às depreciações
de OCR/imagens de tabela/fontes e ao padding do PyTorch, já observados anteriormente.

Na entrega de código, o ambiente de revisão executou 30 testes novos e uma regressão
de 702 testes, excluindo os dependentes de Docling, indisponível naquele ambiente.
A execução completa de 787 testes pelo operador complementa essa limitação.
Testes de contrato e mocks não medem qualidade das respostas do LLM.
Limites e próxima etapa
- Uma amostra por caso, em quatro perguntas de desenvolvimento já conhecidas.
- Revisão assistida, sem avaliação independente ou medição de variância.
- O gerador recebeu planos produzidos anteriormente; o encadeamento completo em uma
  única execução ainda não foi validado.
- Não houve teste novo de casos reservados, conflitos documentais, ACL ou governança
  automática nesta etapa.
- O formato condicionado e rastreável ainda pode ser refinado para apresentação ao
  usuário; esse refinamento não deve remover condições ou alterar o significado.
Próxima sequência: integrar o fluxo com orçamento cumulativo e rastreamento entre
etapas; preservar saídas de abstenção/esclarecimento e erros operacionais distintos;
verificar os casos de desenvolvimento no fluxo integrado; congelar a configuração
candidata e então avaliar os casos reservados. Alterações posteriores à avaliação
reservada devem ser registradas para não transformar esse conjunto em teste de desenvolvimento.
Artefatos e proveniência
Resultados em docs/validation/, com os nomes abaixo. Os hashes SHA-256 identificam
os bytes recebidos e revisados; conversão de finais de linha pode mudar o hash de
arquivo sem mudar o conteúdo JSON.
Resultado	SHA-256 do arquivo revisado
EVIDENCE_ANSWER_ORC001_GPT61SOL_RESULTS_local.json	94fed083b61951d204cb418271a05ef92337932b69e840ba371305ca992e326a
EVIDENCE_ANSWER_ORC002_GPT61SOL_RESULTS_local.json	247f6474775597e627716632d6855d7131429d96b3b124e91b3404a06cf9f948
EVIDENCE_ANSWER_ORC003_GPT61SOL_RESULTS_local.json	3b0b1cb19cc802659033397580c5b855f636f82ac377d7c85f8fe400e0b3f194
EVIDENCE_ANSWER_ORC004_GPT61SOL_RESULTS_local.json	e8b87503206b836e420eb7b68e10f28b287ad88530f3a18f276ba2f44652df3a


Insumos: EVIDENCE_UNITS_SNAPSHOT_local.json e os quatro
EVIDENCE_PLANNER_ORC00N_GPT61SOL_RESULTS_local.json correspondentes.
O dry-run inicial está em EVIDENCE_ANSWER_ORC001_GPT61SOL_PLAN_local.json.

Documentos relacionados:
- [Guia de implementação](EVIDENCE_ANSWER_IMPLEMENTATION_GUIDE.md)
- [Checkpoint de unidades e planejamento](EVIDENCE_PLANNER_PROGRESS_REVIEW.md)
- [Desenho da revisão orientada a evidências](../architecture/09_evidence_oriented_revision_design.md)
Este registro complementa o checkpoint de planejamento, preservando seu caráter
histórico. Nenhum resultado anterior foi sobrescrito.