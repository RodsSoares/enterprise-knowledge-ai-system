# Diagnóstico específico da engenharia de chunking

Data: 07/11/2026. Escopo: código atual e snapshot publicado de 79 chunks,
com resultados RV-016, ORC-001 e comparação integrada de contextos.
Nenhuma alteração de runtime nem chamada paga. Parecer: revisão direcionada
necessária; não há fundamento para reescrever toda a ingestão ou trocar o parser.

## Componentes examinados

app/ingestion/xlsx_parser.py, ingestion/schemas.py,
app/chunking/structure_aware_chunker.py, block_serializer.py, schemas.py,
app/retrieval/search_text.py, geração do índice lexical em rag_service.py,
e testes existentes de chunking/serialização. Evidência de conteúdo:
STAGE1_CORPUS_SNAPSHOT_local.json do commit 9f0c89a e respostas de
CONTEXT_DIAGNOSTIC_RESULTS_local.json enviadas pelo usuário.

## Parecer central

A estrutura física é preservada melhor que a unidade de significado necessário
à tarefa. O chunker tem limites, seções, origem e formatos, mas não garante que
uma unidade recuperada seja uma regra autossuficiente. Isso merece revisão.
Entretanto, representação dos chunks, texto de indexação, seleção e fidelidade
do gerador são fronteiras distintas. Não atribuir todos os erros à segmentação.

## Inventário verificável

79 chunks, dez documentos. Texto mínimo 19 caracteres; máximo 1.722. Nenhum excede
1.800. Nenhum source_block_id ocorre em mais de um chunk do mesmo documento nesse
snapshot: não há indício de fragmentação de um bloco oversized no corpus observado.

DOC-005 tem onze chunks. O chunk 4 é apenas o título de classificação, com 50
caracteres; o chunk 5 é a tabela inteira, com 580. A junção com separador teria
632 caracteres, abaixo de target=1.200 e max=1.800. A separação resulta da diferença
de tipo text/table, não de necessidade de tamanho.

DOC-024 também tem um título isolado de 19 caracteres, “3. Minimum controls”.
Chunks pequenos não são automaticamente ruins; títulos sem regras não deveriam
substituir regras no contexto final apenas por similaridade.

DOC-012 possui dois chunks: matriz A1:E9 com 1.722 caracteres e controle documental
com 501. A matriz reúne oito decisões (linhas 2–9), incluindo limites financeiros,
contratação emergencial, ferramenta nova e uso de IA com dados confidenciais.
Não foi cortada por tamanho nesta execução.

## Achados por responsabilidade

### A. Agrupamento por tipo bloqueia unidade título+tabela — confirmado

_same_structure retorna false quando content_type difere, antes de comparar seção.
Isso mantém distinção técnica entre formatos, mas impede agrupamento semântico de
blocos complementares. Preservar tipo/proveniência não exige sempre separar o
conteúdo entregue ao gerador. Alternativa: unidade de seção ou agrupamento de título,
introdução e tabela com partes tipadas e fontes individuais.

Cuidado: search_text vetorial já acrescenta section_path à tabela. Portanto,
não é correto dizer que a tabela perdeu todo seu contexto de título no embedding.
O BM25 atual usa somente chunk.text, tornando a representação entre os canais
assimétrica. E o renderer da geração inclui section_path como metadado.

Efeito demonstrado: há título sozinho e tabela separada. Efeito causal de uni-los
sobre ranking/resposta ainda não foi medido. O erro de IA não pode ser imputado
somente a essa separação, pois a tabela estava disponível no contexto amplo.

### B. XLSX preserva células, mas não explicita diretamente cabeçalho→valor

XlsxParser cria um SpreadsheetBlock por planilha não vazia. Guarda coordenadas,
valores, fórmulas e intervalo. BlockSerializer transforma isso em sequência
`A1 = ...`, `C9 = ...`, `D9 = ...`. O chunker recebe texto já serializado.

A matriz mantém dados e relações reconstruíveis, mas mistura oito decisões e
exige associação de colunas distante no texto. A resposta confundiu Additional
Review (Data Owner) com Required Approval nos dois contextos, inclusive mínimo.
É plausível que essa apresentação aumente a dificuldade; não foi provado que seja
a causa exclusiva. O texto correto estava presente, portanto não é perda comprovada
de extração, nem prova de que o modelo nunca consegue interpretar essa tabela.

Revisão proposta: representação por registro/linha, com rótulos de cabeçalho e
coordenadas preservados, mais ligação à tabela inteira. Exemplo da linha 9:

- Decision Type [A9]: AI use with confidential supplier data;
- Value / Condition [B9]: Any value / any tool;
- Required Approval [C9]: Information Security Owner + AI Governance Owner;
- Additional Review [D9]: Data Owner;
- Notes [E9]: Tool and use case must be approved for the data classification.

Não resumir/interpretar por LLM nessa transformação; derivar da fonte quando a
associação estiver explicitamente disponível. Não presumir cabeçalho na primeira
linha para toda planilha: tratar cabeçalhos múltiplos, células mescladas e regiões
ambíguas; manter fallback de origem quando a associação não for confiável.
Uma projeção fiel pode ser experimentada sem descartar o modelo canônico existente.

### C. Corte de bloco oversized por caracteres — fragilidade latente confirmada

_split_oversized_block usa fatias block.text[start:start+max_chars] para todos os
tipos. Não respeita sentença, cláusula, linha, célula ou cabeçalho repetido.
Também não registra offsets do fragmento: a origem permanece o bloco inteiro.
Em documentos maiores, pode separar uma obrigação de sua condição ou uma linha
de seu cabeçalho. É necessidade de robustez, não explicação para este snapshot:
nenhum bloco original aparece dividido em múltiplos chunks aqui.

Os testes existentes com sequências de A comprovam comprimentos e origem, não
preservação de significado. Revisão deve usar texto/tabelas representativos e
verificar continuidade e rastreabilidade; não multiplicar testes de contagem.

### D. Papel estrutural se perde no contrato de chunk

TextBlock possui kind e parent_id. RetrievalChunk preserva section_path e
source_block_ids, mas não leva kind/parent_id explicitamente. _content_type
reduz heading/paragraph/list à categoria text. O consumidor pode inferir papel
pelo texto ou consultar a fonte, mas não recebe uma classificação estrutural
confiável no próprio contrato. Isso dificulta distinguir título, regra e introdução
sem heurísticas ou LLM.

Uma revisão precisa considerar papel do trecho e vínculo de seção/tabela. Não
atribuir rótulos jurídicos/semânticos por regex como se fossem metadados originais.

### E. Identidade documental não acompanha cada texto de busca

RetrievalChunk já possui document_id; a falha é na projeção para indexação. BM25
recebe chunk.text, onde DOC-005 só aparece no cabeçalho. O vetor recebe seção+texto,
mas não um envelope documental completo. Isso explica o único hit lexical do
ORC-002. Não precisa mudar limites ou duplicar conteúdo canônico para corrigir.

Alternativas a comparar: enriquecer representação de busca com identidade/título;
usar referência documental explícita como filtro/preferência conforme intenção.
É fronteira de busca, não motivo para reescrever o chunker.

### F. Seleção posterior amplifica limitações, mas não é chunking

Diversidade fixa cinco documentos e preserva o líder. Cabeçalho da DOC-005 vence
a entrada da tabela como âncora. O contexto original tinha apenas cabeçalho e
objetivo; a expansão trouxe todas as onze passagens. Uma unidade melhor pode
ajudar, mas não corrige uma política de seleção que prioriza diversidade sobre
cobertura. Tratar seleção e chunking como responsabilidades distintas.

### G. Chunking não explica omissão e transformação de obrigações sozinho

ORC-001 mínimo com tabela/canais cobriu quatro classes. ORC-002 mínimo recebeu
a mesma tabela, mas omitiu públicos/internos. ORC-003 mudou revisão para aprovação
com a matriz disponível. ORC-004 mínimo omitiu explicitar seguir instruções do
responsável, embora essa frase estivesse no chunk. Essas evidências mostram
problemas de uso/completude mesmo após recuperação de informação adequada.

## O que preservar

- Separação entre parser, representação canônica e chunker.
- Evidência original e proveniência de documento/bloco/página/planilha.
- Serialização determinística e identidade contextual verificável.
- Seções como sinal estrutural; tabelas pequenas preservadas com cabeçalhos.
- Possibilidade de diferentes projeções sem alterar a fonte.
- Testes de integridade e de limites com significado claro.

## Decisões recomendadas

| Prioridade | Revisão | Evidência | Validação necessária |
|---|---|---|---|
| Alta | Projeção tabular por linha com cabeçalho explícito | Confusão de papéis na matriz, oito decisões no mesmo chunk | Mesma evidência/modelo: aprovação versus revisão preservadas |
| Alta | Associação título/introdução/tabela e unidades de seção | DOC-005 chunks 4/5 separados apesar de 632 caracteres juntos | Recuperar regra sem expandir documento inteiro |
| Alta | Papel estrutural e relação pai/filho no contrato ou catálogo | kind/parent não seguem explicitamente no chunk | Seleção identifica título como navegação, não resposta |
| Alta, fora do chunker | Referência documental no fluxo de busca | BM25 DOC-005 encontra só cabeçalho | Referência explícita acessa regras pertinentes |
| Média, robustez | Fragmentação por estrutura e offsets | Fatias arbitrárias no fallback, não acionadas no snapshot | Caso grande preserva linhas/cabeçalhos/condições |
| Não justificada | Aumentar/diminuir globalmente 1200/1800 | Tabela título cabem e matriz nem foi cortada | Não alterar sem hipótese específica |

## Plano de revisão coeso

Definir primeiro duas representações: canônica auditável e projeção para
recuperação/geração. A segunda deve ser derivável e ligada à primeira, sem inventar
regras. Não impor a mesma unidade física ao índice e ao contexto: pode-se buscar
um registro e entregar registro+cabeçalhos/condições da seção.

Para esta entrega, incluir projeção fiel da matriz e agrupamento de seções curtas,
com rastreabilidade e critério único de avaliação ponta a ponta. Medir efeitos
separadamente na mesma rodada: fonte/representação, posição no pool, seleção,
resposta e preservação das condições. Manter baseline imutável e os casos reservados.
Não implantar heurística especial para DOC-005 ou Data Owner.

Antes de declarar correção, verificar os quatro casos já conhecidos: cobertura de
classes, exclusão de processos alheios, distinção revisão/aprovação e completude
de ações. Usar casos grandes adicionais apenas para o fallback quando revisado.
Uma resposta boa isolada não comprova que a representação resolveu a causa.

Mudanças de granulação alteram IDs baseados em ordem e exigem novo snapshot e
reindexação das representações alteradas. Não reutilizar embeddings antigos para
texto novo, nem comparar chunks por número como se fossem semanticamente estáveis.
Usar versão de representação + documento/bloco/linha para mapear antes/depois.
O corpus bruto e os resultados anteriores devem permanecer preservados.

## Conclusão

Merece revisão dirigida. A engenharia atual é estruturalmente consciente, mas
não consistentemente orientada à unidade de regra e à leitura de relações tabulares.
O maior retorno provável está nas projeções e relações entre blocos, não na troca
de parser nem em ajustar um número global de caracteres. Essa revisão é parte da
solução; fidelidade do gerador e seleção continuam sendo critérios independentes.
