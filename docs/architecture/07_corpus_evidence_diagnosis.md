Diagnóstico do corpus completo e mapa de evidências
Data: 07/11/2026. Base publicada: 9f0c89afa4a50bc34c9d27e4aee29cb87d30414f.
Sem alteração de runtime, geração, embeddings novos ou testes unitários adicionais.
Método e integridade
Snapshot lido diretamente do GitHub no commit fixo: 79 chunks, dez documentos.
O digest do payload confere com snapshot_id. Os hashes dos dez arquivos físicos
conferem com a cópia local. O hash bruto do registro difere entre ambientes,
mas coincide exatamente ao converter LF para CRLF: diferença de newline Windows,
não evidência de conteúdo distinto. Não alterar snapshot/validador nesta análise.

Reexecutado BM25 existente sobre chunk.text, com a filtragem lexical efetivamente
usada pelo build_service. A consulta em inglês foi tradução manual para diagnóstico,
não uma nova política de consulta nem resultado de ablação da busca híbrida.
Os pools e saídas do LLM são os registrados na v2; não reconstruímos scores vetoriais.
Canal lexical nos quatro casos de desenvolvimento
Caso	Resultados BM25 no corpus completo
ORC-001 — compartilhamento geral	Zero
ORC-002 — DOC-005 explícita	Um: DOC-005::chunk-00001 (cabeçalho), score 5,161
ORC-003 — dados confidenciais de fornecedor em IA	Zero
ORC-004 — envio acidental a fornecedor	Zero


Consequência: no ORC-001, 003 e 004, a branch lexical atual não contribui candidatos.
No ORC-001 registrado, RRF recebe apenas o ranking vetorial, preservando sua ordem.
Isso não significa que embeddings sejam incapazes de PT→EN; significa que a
complementaridade prometida pelo híbrido não ocorre nesses casos.

Com DOC-005 explícita, BM25 encontra o identificador no cabeçalho. A indexação
lexical usa apenas o texto, não document_id de cada chunk. Não há encaminhamento
determinístico de uma referência documental explícita para todas as seções do
respectivo documento. Acrescentar o ID a todo texto de busca e filtrar pelo ID
são alternativas diferentes; não implementar ambas sem avaliar a intenção.

A tradução manual de ORC-001 ativa BM25, mas o primeiro resultado é
DOC-023::chunk-00005 (dados em IA). A tabela DOC-005::chunk-00005 fica em décimo,
com score 4,717. Tradução pode ajudar descoberta, mas não resolveu pertinência
neste replay lexical. Não concluir impacto no ranking híbrido sem seus dois ramos.
Onde a regra se perdeu no fluxo antigo
Pool inicial ORC-001 v2: DOC-005 cabeçalho em 3, objetivo em 5, transportadoras em 7,
IA em 8, tabela em 9, escopo em 14.

Aplicando a política atual de diversidade sobre essa ordem, as cinco âncoras são:
DOC-010::chunk-00005 (incidente), DOC-025::chunk-00006 (IA),
DOC-005::chunk-00001 (cabeçalho), DOC-023::chunk-00005 (IA),
DOC-006::chunk-00004 (transmissão externa).

No artefato RV016_SHARING_DIAGNOSTIC, contexto de dez trechos contém somente
cabeçalho e objetivo da DOC-005. No AFTER_CONTEXT_FIX, os 45 trechos contêm todos
os onze chunks da DOC-005. O suplemento por ranking continuava escolhendo texto
introdutório; expansão documental recuperou as regras, com bastante conteúdo extra.

Não confundir descoberta (tabela no pool) com seleção (tabela fora das âncoras)
e interpretação (regra de IA aplicada ao cenário errado).
Mapa de evidências de desenvolvimento
Mapa baseado no conteúdo do snapshot, sem promover estas referências a runtime.
A referência é uma unidade de regra; um documento inteiro não é gabarito suficiente.
Caso	Escopo	Núcleo necessário	Complementos condicionais	Desvio a evitar
ORC-001	Cuidados prévios gerais para envio externo	DOC-005::chunk-00005, quatro classes; chunk-00007, canais	chunk-00009 se abordar exceções; DOC-006 para proteção específica de dados de clientes	Transformar IA, compras ou incidente em obrigação geral
ORC-002	Mesma necessidade, com fonte explicitamente DOC-005 e exclusão de IA	DOC-005::chunk-00005 e chunk-00007	chunk-00009 apenas se pertinente	Responder com objetivo/título ou introduzir IA
ORC-003	Aprovações para dados confidenciais de fornecedor em IA	DOC-023::chunk-00005 e DOC-012::chunk-00001, linha 9	DOC-023::chunk-00006 e matriz linha 8 se for ferramenta nova	Confundir aprovação de ferramenta nova com aprovação de uso de dados
ORC-004	Divulgação acidental já ocorrida	DOC-010::chunk-00004 e chunk-00005	chunk-00003 para gatilho; chunk-00006 apenas se perguntar encerramento	Responder só com prevenção ou mandar destruir evidências


ORC-003 ilustra dependência multidocumento legítima: matriz identifica Information
Security Owner + AI Governance Owner, com revisão do Data Owner; tool/use case
aprovados para a classificação. Essa linha não autoriza generalizar para todo envio
externo. ORC-004 precisa das ações imediatas, não só do parágrafo supplier disclosure.
Unidade semântica que precisamos preservar
Para cada regra: ação, objeto, destinatário, condição, obrigação/proibição e fonte.
Exemplo: usar dados confidenciais de fornecedor EM IA → aprovações específicas.
Compartilhar dados COM fornecedor não satisfaz automaticamente essa condição.

Pergunta geral admite ramificações internas (public/internal/confidential/restricted).
Não admite introduzir outro processo como requisito geral (comprar ferramenta,
tratar incidente). Portanto, conditional sozinho é insuficiente: precisa distinguir
categoria interna ao pedido de cenário adicional não solicitado.
Controle de contexto proposto, ainda sem geração
Para ORC-001, tabela e canais da DOC-005 formam um controle mínimo de duas passagens,
1.829 caracteres no renderer atual. O contexto expandido observado tinha 45
passagens e 31.545 caracteres. A redução do controle é cerca de 94,2%, mas não é
melhoria demonstrada de resposta nem cobertura universal. Regras de exceção
podem ser um terceiro trecho em variante explicitamente definida.

O controle deve apresentar as quatro classes, não resumir tudo a confidencial.
Public: aprovado para uso público/canal empresarial aprovado. Internal: necessidade
legítima/canal gerenciado. Confidential: destinatário autorizado, finalidade aprovada,
canal seguro/plataforma controlada, acesso aos destinatários. Restricted: autorização
explícita aplicável, mecanismo restrito e autorização documentada.
O que já podemos concluir e o que falta
Confirmado: canal lexical vazio em três perguntas; referência DOC-005 aponta só
para cabeçalho no BM25; tabela presente no pool mas perdida no contexto antigo;
expansão recupera tabela; assessor v2 aplica IA indevidamente e falha no contrato.

Ainda não demonstrado: qualidade do gerador com contexto mínimo; efeito causal
do tamanho/ordem; recuperação dos trechos necessários nos outros três casos;
melhor política multilíngue; qual modelo executa bem o assessment simplificado.
Não é necessário novo parser ou banco vetorial para testar essas hipóteses.
Próxima experiência integrada, antes de implementação
Quatro casos de desenvolvimento, mesma versão de corpus e gerador. Fixar mapa
humano acima e comparar contexto mínimo com contexto amplo. Reutilizar contexto
salvo e evitar nova indexação só para avaliar geração. Registrar condições,
completude, obrigações fora de escopo, fontes, tokens e latência por caso.

Se contexto mínimo falha, investigar geração/modelo. Se mínimo funciona e amplo
falha, priorizar seleção/aplicabilidade. Depois testar mudanças de retrieval,
com rankings vetorial e lexical registrados separadamente, numa rodada integrada.
Não combinar tradução, novo modelo, reranking e novo schema simultaneamente.

Para DOC-005 explícita, planejar tratamento de referência documental como restrição
ou preferência conforme intenção, sem regra hardcoded para essa política. Para
pergunta geral, relevância de regra precede diversidade documental. Estas são
hipóteses de desenho para avaliação, não mudanças implementadas.