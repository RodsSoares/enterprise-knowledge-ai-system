Diagnóstico integrado: contexto mínimo versus amplo
Data: 07/11/2026. Fonte: CONTEXT_DIAGNOSTIC_RESULTS_local.json fornecido pelo usuário.
Status: oito gerações concluídas; revisão semântica assistida, não avaliação humana
independente. Modelo gpt-4.1-mini-2025-04-14; uma amostra por braço/caso.
Nenhuma chamada nova na análise. Aplicação não alterada.
Síntese
Contexto mínimo ajudou ORC-001, mas não garantiu completude em ORC-002 nem fidelidade
de papéis em ORC-003. ORC-004 teve resultados úteis nos dois braços, com diferença
de completude. O experimento não sustenta nem “basta reduzir contexto” nem “o modelo
não funciona”. Há falhas distintas de seleção, cobertura e interpretação de obrigações.

Todos os oito resultados são contract_valid. Isso não equivale a oito respostas
semanticamente aprovadas. Os critérios abaixo vêm do guia prévio e dos textos
canônicos efetivamente enviados ao modelo.
Revisão por caso
ORC-001 — cuidados gerais antes de compartilhar
Mínimo: cobre public/internal/confidential/restricted, destinatário/finalidade,
controles por classe, autorização documentada para restritos e restrição sobre
email corporativo isolado. Não introduz IA. Resultado adequado ao mapa da pergunta,
com alguma redundância entre afirmações sobre confidencialidade.

Amplo: concentra-se em confidenciais e omite regras específicas de públicos,
internos e restritos. Acrescenta duas afirmações de IA não solicitadas. Na afirmação
sobre dados do fornecedor em IA, generaliza aprovação de segurança/governança,
embora a fonte estabeleça a exigência adicional especificamente para confidenciais.
A última afirmação também troca uma restrição de uso por linguagem sobre impedir
que o produto aceite dados automaticamente, que não é um controle técnico explicitado
nesses termos pelas fontes. Contexto amplo é inferior neste par observado.
ORC-002 — DOC-005 explícita, excluindo IA
Mínimo: responde sobre confidenciais e restritos e canais; não inclui IA. Omite
públicos/internos e não explicita limitação de acesso aos destinatários pretendidos,
apesar de essas regras estarem na tabela fornecida. Não satisfaz toda a cobertura
estabelecida no diagnóstico prévio para uma pergunta sem classe especificada.

Amplo: respeita exclusão de IA, cobre confidenciais/restritos e acrescenta regras
para transportadoras e exceções, mantendo a condição textual de transportadora.
Esses dois temas têm fontes que o mínimo não recebeu, portanto não usar sua ausência
no mínimo como falha de geração. Ainda omite regras específicas de públicos/internos;
a primeira afirmação apresenta autorização de destinatário de forma ampla demais.

Conclusão: os dois braços são incompletos segundo a rubrica. Não declarar vitória
do mínimo por ser mais curto nem do amplo por ter mais itens. O pedido mais explícito
parece ter ajudado a evitar IA nesta amostra, mas não prova efeito causal universal.
ORC-003 — aprovações de dados confidenciais de fornecedor em IA
Evidência decisiva: DOC-012::chunk-00001, linha 9.
Required Approval = Information Security Owner + AI Governance Owner.
Additional Review = Data Owner.
Notes = ferramenta e caso de uso aprovados para a classificação.

Mínimo, afirmação 2: diz que é necessária aprovação do dono dos dados. A fonte
atribui revisão, não aprovação. Isso inventa autoridade de aprovação e é erro
material de governança. Afirmação 3 também usa “uso ou ferramenta” onde a fonte
exige ferramenta/caso de uso aprovados; não relaxar a conjunção operacional.

Amplo, afirmação 5: diz que decisões podem requerer aprovação do Proprietário dos
Dados, conforme a matriz. A citação não sustenta essa aprovação. A modalização
“podem” não resolve a troca de papel. Inclui ainda fluxo de ferramentas novas,
com condição explícita, embora a pergunta não diga que a ferramenta é nova.

Conclusão: falha material nos dois braços. A relação coluna→valor estava disponível,
mas não foi preservada pelo gerador. Não há evidência de perda no parser neste
artefato; avaliar apresentação de tabela e instruções/modelo, sem supor que uma
nova normalização resolverá automaticamente.
ORC-004 — divulgação acidental
Mínimo: cobre interrupção da divulgação sem destruir evidências, reporte imediato,
registro de fatos, preservação e proibição de instruir exclusão antes de orientação.
Explica coordenação por Segurança da Informação. Não explicita o último passo
“seguir instruções de contenção, notificação e remediação do responsável”, presente
no texto enviado. Útil e sem desvio material observado, com ressalva de completude.

Amplo: cobre esses passos, inclusive seguir instruções do responsável, e acrescenta
regra apoiada na fonte de não ocultar ou resolver independentemente sem reportar.
Há repetição de reporte. Resultado adequado ao cenário nesta amostra.
Consumo observado
Braço, quatro respostas	Entrada	Saída	Total	Custo estimado	Soma de latências
Mínimo	3.548	899	4.447	US$ 0,0028576	11,24 s
Amplo	28.444	1.292	29.736	US$ 0,0134448	13,42 s
Rodada	31.992	2.191	34.183	US$ 0,0163024	24,66 s


Redução agregada no braço mínimo: aproximadamente 85% dos tokens totais e 79% do
custo estimado. São contas com as tarifas configuradas, não extrato de cobrança.
Latência não foi consistentemente menor: ORC-001 mínimo levou 4,38 s e amplo 4,18 s.
Não projetar desempenho operacional a partir de oito chamadas.
Limites e inferência causal
Só ORC-001 tem contexto amplo oriundo da recuperação real da própria pergunta.
Os demais usam banco de distratores controlado; ORC-003 acrescenta a matriz.
Todos os mínimos são subconjuntos canônicos dos amplos, mas texto/posição/IDs
variam e não houve repetições. Portanto, efeito de tamanho não foi isolado de
composição, ordem ou variabilidade do modelo. Não usar percentuais de acurácia
ou testes estatísticos com esse desenho. Gabaritos não foram enviados ao gerador.

O mínimo contém chunks completos, não uma seleção perfeitamente atômica: a matriz
tem várias linhas e papéis. Isso limita a conclusão “nem contexto puro funciona”.
A conclusão sustentada é que dois chunks relevantes não impediram troca de papéis.
Decisão de arquitetura
Há evidência suficiente para planejar uma entrega funcional coesa, mas não para
ativar a orquestração completa nem promover automaticamente um modelo.
1. Seleção: preservar escopo e referências documentais explícitas; priorizar regras
   operacionais sobre cabeçalhos; expansão por seção quando necessária; diversidade
   como preferência subordinada à cobertura, não meta fixa de cinco documentos.
   A tradução lexical é hipótese separada: não incorporá-la junto sem medição.
2. Aplicabilidade e cobertura: representar as condições da regra sem tratá-las
   como fatos do usuário; distinguir categoria dentro do pedido de outro processo.
   Pergunta geral deve cobrir as classes pertinentes, sem presumir confidencialidade.
   O plano de evidências precisa informar necessidades de resposta, não apenas entregar
   um conjunto menor de chunks. Um mapa humano de avaliação nunca pode virar contexto
   oculto de produção.
3. Fidelidade da geração: preservar verbo, papel, condição e modalidade. Em tabelas,
   revisão não pode virar aprovação, destinatário não vira aprovador, “e” não vira “ou”.
   A captura estrutural de origem não demonstra preservação semântica. Validar esse
   critério junto da resposta final e não apenas aceitar IDs de citação existentes.
   Não corrigir isso com regra especial para Data Owner ou DOC-012.
4. Protocolo: simplificar o assessor e atribuir ao código identidade, cardinalidade,
   resolução de excertos e exclusividade de operações. Mas schema válido não garante
   que requisitos, classificação de pertinência ou resposta estejam corretos.
Próximo passo delimitado
Fechar o desenho da entrega com esses quatro critérios antes de escrever código.
Manter baseline e corpus fixos. Implementar uma alteração coesa e comparar os quatro
casos ponta a ponta, registrando também pool→seleção→resposta. A aceitação inclui:
ORC-001/002 sem obrigações de IA e com classes pertinentes; ORC-003 sem aprovação
inventada para Data Owner; ORC-004 sem perda dos passos materiais de contenção.

Não precisa nova rodada diagnóstica ampla para confirmar que há múltiplas falhas.
A próxima avaliação deve ser da intervenção planejada, com critérios fixos e
repetições limitadas nos casos críticos. Casos reservados permanecem intocados.
Se a fidelidade de papéis continuar falhando, comparar representação/instruções/modelo
sob evidência idêntica antes de acrescentar revisor/loops autônomos.