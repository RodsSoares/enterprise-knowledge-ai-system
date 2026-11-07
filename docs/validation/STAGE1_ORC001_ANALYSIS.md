ORC-001 — primeira execução da orquestração
Fonte: STAGE1_ORC001_COMPARISON_local.json, fornecido pelo usuário.
Status: EXECUTION_FAILED / AssessmentContractError; candidato não gerou resposta.
Resultado observado
As quatro chamadas API concluíram: embeddings do corpus, embedding da pergunta,
geração baseline e assessment. O ledger registra 19.614 tokens de entrada e 1.646
de saída, com custo estimado de US$ 0,00889156 pelos preços configurados. Não houve
excesso de orçamento, timeout ou recusa da API no registro. usage.failed=false
refere-se à camada de chamadas, não à aceitação do contrato do assessor.

O baseline respondeu, mas voltou a generalizar aprovação de Segurança da Informação
e Governança de IA para dados confidenciais de fornecedores sem preservar o uso
em IA. Isso permanece erro semântico conhecido, não melhoria validada.
Violações da avaliação salva
1. requirements contém strings como R1: Verificar autorização..., enquanto
   requirement_ids usa apenas R1. O contrato exige identidade exata. Pela ordem
   do validador atual, essa é a primeira violação que bloqueia o resultado.
2. O pool inicial contém 20 chunks; há decisões para apenas quatro. Os demais
   16 não foram explicitamente classificados.
3. As quatro citações são cópias exatas de trechos presentes no contexto baseline,
   mas os offsets retornados estão incorretos:
Chunk	Intervalo declarado	Comprimento real do excerto
DOC-005::chunk-00005	0–334	580
DOC-023::chunk-00005	0–320	369
DOC-023::chunk-00006	0–269	260
DOC-006::chunk-00004	0–222	263


4. decision=sufficient convive com quatro lacunas não vazias e sem suporte
   declarado para todos os requisitos.
5. Semanticamente, a avaliação presume dados confidenciais/restritos numa pergunta
   geral e classifica regras de uso de IA como diretamente aplicáveis. Não basta
   reparar a forma para aprovar esse resultado.
A primeira execução não salvou a requisição completa do assessment antes de sua
validação. Este diagnóstico usa a resposta bruta, a lista inicial de IDs e textos
do baseline; não se apresenta como replay integral de uma requisição reconstruída.
Correção
O adapter agora pede apenas excertos exatos ao LLM. O código calcula índices Unicode
sobre o chunk canônico. Excertos ausentes, vazios ou ambíguos são rejeitados; não
há busca aproximada nem substituição de texto. A schema externa passa a representar
cada supporting_span como {text}; o contrato interno mantém {start,end,text}.

O prompt explicita identificadores puros (R1, G1), decisão para cada chunk,
lacunas incompatíveis com sufficient e distinção entre condição da fonte e fato
da pergunta. A requisição é registrada antes da chamada e o motivo da falha de
contrato aparece no trace. Nenhuma classificação, cobertura ou suficiência é
corrigida automaticamente. Não se adicionam chamadas de reparo.

Testes direcionados: 52 passed com providers falsos. A evidência semântica nova
continua pendente. O snapshot físico pode ser reutilizado: não houve alteração
em documentos, registro, parsing ou chunking. Uma nova comparação exige nome novo
de saída e chamadas pagas; não foi executada pelo assistente.
Segunda execução — v2
Fonte: STAGE1_ORC001_COMPARISON_v2_local.json, fornecido pelo usuário.
Status: EXECUTION_FAILED / AssessmentContractError / Unknown requirement.

A requisição completa agora está no trace. Replay offline da requisição e da
resposta bruta reproduziu Unknown requirement, sem chamadas API. Os nove
excertos foram encontrados exatamente e receberam offsets calculados pelo código.
Controle	Primeira execução	v2
Identificadores declarados	IDs misturados com descrições	R1 a R8, formato corrigido
Integridade das referências	Referências diferentes das declarações	R9/R10 usados mas não declarados
Cobertura das decisões	4/20	11/20
Excertos/offsets	Quatro offsets incorretos	Nove excertos exatos resolvidos pelo código
Decisão/lacunas	sufficient com lacunas	retrieve com lacunas
Tipo de ação	Nenhuma	search com quatro section_ids: união inválida
Escopo	Inclui IA indevidamente	Ainda inclui IA e compras como requisitos da pergunta geral


O request foi validado localmente apenas como replay da execução salva. Nenhuma
correção de requisitos, inclusão de decisões ausentes ou limpeza de lookup foi
aplicada para forçar aceitação. O candidato não chegou à geração.

Uso v2: quatro chamadas; 19.831 tokens de entrada e 2.058 de saída; custo estimado
US$ 0,00963756. Somadas as duas execuções, US$ 0,01852912. Estes valores são os
cálculos registrados com as tarifas configuradas, não extrato de faturamento.

O baseline continua incluindo uso em IA na resposta à pergunta geral. Há alguma
melhora formal na interpretação do assessor (subject=dados, classificação
não presumida), mas ele ainda seleciona DOC-023::chunk-00005 como direct e cria
lacunas de compras/IA sem necessidade demonstrada. Não há resposta candidata
para comparar qualidade final nem evidência de melhoria geral da arquitetura.
Decisão de engenharia
Não repetir uma terceira rodada baseada apenas em mais instruções. A interface
atual deixa relações estruturais demais sob responsabilidade do modelo. Próximo
incremento: restringir o schema por requisição para exigir uma decisão por chunk,
separar os formatos de search e expand_document_section em alternativas exclusivas,
e simplificar a declaração/referência dos requisitos, evitando IDs livres sem
vínculo estrutural. Validar essas restrições offline antes de nova execução paga.

Essas mudanças tratam falhas de contrato; não resolvem automaticamente relevância,
aplicabilidade ou suficiência. Preservar a revisão humana e o status experimental.
Não adicionar reparos silenciosos nem promover o fluxo após mera aceitação JSON.