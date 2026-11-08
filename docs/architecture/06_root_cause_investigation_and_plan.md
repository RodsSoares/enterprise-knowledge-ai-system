Investigação integrada — recuperação, contratos e geração
Data: 07/11/2026. Status: investigação e planejamento; nenhuma implementação.
Base verificável
GitHub main consultado via connector: 055b0a8464d5895ccffe163b21deacfe9497f9da,
feat: add retrieval experiments and validation through RV-013.
Os commits locais posteriores não estavam publicados nessa consulta. Não exigir
push para investigar: distinguir código publicado, incrementos locais entregues
e execuções Windows fornecidas. Não afirmar que a árvore Windows foi inspecionada.

Fontes remotas lidas com ref fixo: arquitetura 01, HybridRetriever,
DocumentDiversifier, search_text e retrieval_metrics. Código adicional do mesmo
commit foi lido no objeto Git local: retrieval_evaluator e chunking/schemas.
Incrementos locais: evidence_context, RagService, provider, contratos de resposta,
coordinator, contratos de assessment, snapshot e comparador. Evidências runtime:
ORC-001 original e v2, incluindo requisição/saída bruta da v2.

Referência pública: https://github.com/RodsSoares/enterprise-knowledge-ai-system/tree/055b0a8464d5895ccffe163b21deacfe9497f9da
Conclusão central
Não há evidência de uma causa única chamada “recuperação ruim”. Há três falhas
encadeadas: selecionar documentos não garante selecionar suas regras; ter regras
no contexto não garante respeitar sua aplicabilidade; o novo assessor falha no
protocolo e também repete erros semânticos. Tornar o protocolo válido não demonstra
melhoria da seleção nem da resposta. Não promover a orquestração com essa evidência.
Caminho concreto de ORC-001
No pool inicial da v2, DOC-005 aparece nas posições:
Posição de chunk	Conteúdo
3	Cabeçalho da política
5	Objetivo
7	Compartilhamento com transportadoras
8	Uso relacionado a IA
9	Tabela de classificação e controles mínimos
14	Escopo


DocumentDiversifier fixa o líder e privilegia documentos distintos. Neste pool,
a primeira evidência da DOC-005 é o cabeçalho. A tabela da mesma política não é
favorecida por diversidade documental. Isso explica como um documento correto
pode estar recuperado sem a passagem decisiva entrar nas cinco âncoras.

A expansão posterior acrescentou a tabela: na v2 ela já está tanto no pool do
assessor quanto no contexto expandido do baseline. Os nove excertos produzidos
pelo assessor foram encontrados exatamente pelo resolver. Nesse caso, perda da
tabela no parsing não explica o erro posterior. Isso não certifica todo o parser.

O assessor continua classificando a seção “Use of supplier data in AI” como direct
para uma pergunta geral sobre envio a fornecedor. A resposta baseline acrescenta
requisitos de IA. Há informação correta disponível, mas aplicação inadequada.
Contratos: garantia real e garantia ausente
Fronteira	Garante	Não garante
Conteúdo normalizado → chunk	Texto, identidade, ordem e origem estrutural	Unidade semântica completa, regra aplicável, revisão documental
Chunk → ranking	Similaridade/ocorrência lexical, scores, proveniência	Resposta à intenção ou autoridade
Ranking → diversidade	Documentos distintos e líder preservado	Cobertura de requisitos ou prioridade para regras operacionais
Âncoras → contexto	Limites e texto canônico	Precisão semântica e exclusão de processos adjacentes
Assessment → validação	IDs, spans, cobertura formal, decisão consistente	Requisitos corretos ou condições verdadeiras para a pergunta
Assessment → gerador	Trechos canônicos selecionados	Política explícita para condições satisfeitas/desconhecidas/falsas
Geração → contrato	JSON e citações existentes	Entailment, completude, aplicabilidade ou autorização correta


A arquitetura 01 já distinguia similaridade de relevância contextual e previa
processamento da consulta, filtros e validação de evidência. A implementação
entregou partes dessas responsabilidades, mas a passagem entre elas não foi
validada como produto completo. Os componentes não são descartáveis; faltou
um critério de aceitação integrado para a pergunta empresarial.
Achados e grau de certeza
1. Objetivo de avaliação diferente do objetivo do produto — confirmado
retrieval_metrics mede documentos e remove IDs repetidos antes de cortar em K.
reciprocal_rank também usa a sequência de documentos únicos. Portanto, essas
métricas não devem ser lidas como ranking de passagens. Se o chamador já limita a
cinco chunks, o escopo continua sendo esses candidatos; não há base para acusar
inflação numérica de todos os relatórios sem revisar cada chamador. A lacuna
confirmada é semântica: um cabeçalho pode contar como recuperação do documento.

O produto exige recuperar controles e preservar condições. Precisamos medir
cobertura dos trechos necessários, contexto irrelevante e completude da resposta.
Os resultados documentais anteriores continuam válidos para o que mediram.
2. Seleção prematura por diversidade — mecanismo confirmado no código
A regra protege o primeiro resultado mesmo se ele tratar de incidente. Prioriza
uma fonte nova antes de uma segunda passagem operacional da fonte correta.
Isso é uma escolha de produto implícita. Pode ajudar perguntas multidocumento,
mas prejudicar perguntas concentradas numa política. Sua contribuição causal
em outras perguntas precisa de ablação, não de remoção automática.
3. Canal lexical multilíngue — limitação confirmada, impacto parcial
Na v2, a consulta filtrada tem oito tokens: antes, compartilhar, cuidados, dados,
exige, externo, fornecedor, política. A interseção com os textos dos 20 chunks
apresentados é vazia. Logo esses chunks não recebem correspondência lexical
por esses tokens. Isso não prova ausência de matches nos demais 59 chunks: o
snapshot completo da máquina do usuário não foi recebido neste estudo.

O filtro remove palavras funcionais, não traduz. BM25 não oferece equivalência
semântica PT→EN. RRF soma posições, sem calibrar qualidade relativa dos canais.
Precisamos medir contribuição lexical e ramo vetorial separadamente; não assumir
que a palavra “híbrido” significa dois sinais úteis em toda pergunta.
4. Contexto amplo resolve ausência, não aplicabilidade — confirmado no caso
A expansão recuperou regras faltantes, mas também mantém documentos de IA,
compras e incidente. O assessor não demonstrou excluir adequadamente esse ruído.
Não está provado que volume, sozinho, cause o erro. Comparar contexto mínimo
correto e contexto amplo no MESMO gerador é necessário para separar capacidade
de geração de seleção e distração.
5. Requisitos derivados dos distractores — observado nas duas avaliações
Interpretação da pergunta e avaliação de evidências são feitas juntas. O assessor
vê IA/compras e incorpora isso aos próprios requisitos. Isso cria um ciclo:
evidência vizinha altera o que ele acha que precisa responder; lacunas inventadas
pedem mais material sobre um assunto que o usuário não solicitou.

Não está provado que separar em duas chamadas resolverá. Primeiro testar leitura
da pergunta antes das evidências e uma declaração de escopo estável, com mesmo
modelo. Uma etapa única só deve permanecer se preservar essa fronteira.
6. Conditional não controla inclusão — confirmado no código local
coordinator seleciona direct e conditional igualmente. O validador exige texto
para condition, mas não verifica se a condição foi afirmada pelo usuário, pode
ser apresentada como categoria geral ou pertence a processo fora de escopo.
O gerador recebe os textos integrais; condições e requisitos do assessment ficam
no trace. Uma classificação conditional não produz, por si, proteção operacional.

Também não convém excluir todo conditional: pergunta geral sobre classes de
dados precisa apresentar regras condicionais por classe. A política precisa
distinguir variação dentro do escopo de cenário adicional não solicitado.
7. Protocolo do assessor excessivamente dependente de consistência livre
Na v2: R1–R8 declarados, R9/R10 referenciados; 11/20 decisões; search com section_ids.
Essas relações atravessam campos que o schema estático não liga. O validador está
correto ao rejeitar. Pedir offsets ao modelo era atribuir trabalho determinístico
à parte probabilística; esse ponto já foi corrigido e nove quotes resolveram.

IDs da requisição poderiam ser vinculados pelo adapter em vez de copiados pelo
modelo; decisões por chunk podem ter cardinalidade imposta pelo schema; operações
podem ter alternativas exclusivas. São opções de desenho, não autorização para
implementar imediatamente. Primeiro decidir se todos esses campos são necessários.
8. Governança disponível não é governança aplicada
Registro, datas e autoridade existem; baseline não os usa. Novo assessor recebe
metadados, mas isso não equivale a regra de precedência ou ACL. Não há evidência
de que isso explique ORC-001, que já falha sem conflito documental complexo.
Não transformar essa melhoria arquitetural em solução causal do caso atual.
9. Testes passando não equivalem a tarefa resolvida
Fixtures simulam avaliações bem formadas. Provam transições, bloqueios e limites,
mas não a habilidade de um modelo em produzir avaliações adequadas. As falhas
reais mostram que precisamos de uma experiência integrada representativa, com
etapas observáveis, antes de expandir funcionalidades. Manter testes de contrato
necessários; interromper crescimento orientado apenas pela contagem de testes.
Hipóteses ainda não demonstradas
- Modelo mini insuficiente para o assessment completo.
- Contexto reduzido produz resposta melhor mantendo o modelo.
- Tradução controlada melhora BM25 sem introduzir drift.
- Reranker melhor resolve aplicabilidade sem assessor complexo.
- Metadados de título/tipo no search_text melhoram ranking das regras.
- Filtrar cabeçalhos da seleção final é melhor que expandi-los hierarquicamente.
Não escolher ferramenta, modelo maior ou framework como resposta antes de testar
qual desses mecanismos contribui. Uma única pergunta não representa todo o corpus.
Plano integrado de investigação
Fase A — especificação de sucesso e rastreio, sem chamadas pagas
Escolher quatro casos de desenvolvimento já conhecidos: compartilhamento geral,
DOC-005 explícita, uso em IA explícito e incidente. Para cada um registrar intenção,
condições fornecidas/desconhecidas, trechos necessários, fontes complementares e
conteúdo que não deve virar obrigação. Requisitos de referência ficam só na avaliação.
Revisar o texto físico antes de considerar esse mapa uma referência aprovada.

Montar uma tabela única por pergunta: regra → documento/bloco → chunk → posição
vetorial/lexical/fusão → seleção → contexto → afirmação. Usar dados salvos primeiro;
marcar ramo ausente como não observado, sem fabricar scores a partir da fusão.
Solicitar apenas o snapshot e traces que faltarem, sem pedir publicação do projeto.

Saída: diagnóstico por etapa, sem novo runtime. A mudança deve ter alvo e hipótese.
Fase B — uma experiência comparativa controlada
Mesmos quatro casos, mesmo snapshot, gerador e parâmetros. Comparar:

A. Contexto mínimo correto, selecionado por revisão humana (controle experimental).
B. Contexto amplo atual, reutilizado.
C. Seleção atual com diversidade e orçamento registrados.

Não chamar A de capacidade operacional: usa referência humana para estabelecer
se o gerador consegue responder quando recebe evidência adequada. Se A falhar,
rever geração/modelo antes de trabalhar em retrieval. Se A funcionar e B falhar,
ruído/aplicabilidade ganha suporte causal. Se C perder trechos presentes no pool,
a seleção é o alvo. Só executar variações novas não respondidas pelos artefatos.
Repetir casos críticos de forma limitada para distinguir instabilidade de efeito.
Definir custo máximo antes das chamadas; persistir embeddings e pools no runner
futuro para não pagar descoberta novamente a cada variação de seleção.
Fase C — decisão arquitetural, depois implementação coesa
Escolher a menor intervenção que resolve o gargalo observado. Possíveis decisões:
seleção por evidência com diversidade secundária; expansão de seção; tratamento
multilíngue; interpretação de escopo independente; assessor simplificado.
Não combinar todas no mesmo incremento porque inviabiliza atribuição causal.

Se assessor permanecer: separar pertinência, completude e condição; definir
como essas decisões chegam ao gerador; retirar hashes/offsets/IDs desnecessários
da responsabilidade do modelo; usar schema que expresse relações verificáveis.
Revisor de resposta e reparo só depois de verificar esse fluxo.
Fase D — aceitação funcional única
Comparar baseline e solução escolhida no conjunto de desenvolvimento e só depois
nos seis casos reservados, sem ajustar prompts com eles. Os reservados não são
holdout cego independente, pois foram projetados nesta conversa.

Registrar por caso: cobertura das regras materiais, obrigações fora de escopo,
condições omitidas, sustentação de afirmações, saída adequada, chamadas, custo e
latência. Gate: zero condição material perdida/obrigação inventada nos casos
revisados, nenhuma regressão não explicada, e melhoria identificável que justifique
custo. Amostra pequena ainda não certifica produção.
Prioridade final
Preservar ingestão, chunks canônicos, proveniência, índices, contratos estruturais
e ledger. Pausar novos prompts, retries e revisor. Primeiro provar onde a evidência
correta é perdida ou mal utilizada. Não prometer que o próximo schema resolverá
um problema que também é semântico. Não alterar código nesta investigação.