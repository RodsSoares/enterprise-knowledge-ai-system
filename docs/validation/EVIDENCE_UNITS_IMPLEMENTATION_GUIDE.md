Incremento 1 — unidades estruturais e catálogo candidato
Base publicada examinada: 01e0858d745731cc5f66bcc9ea90d41330393bce.
Desenho: docs/architecture/09_evidence_oriented_revision_design.md.
Status: implementação experimental de representação, preparação e índice lexical.
Não é uma promoção do novo fluxo de respostas e não comprova ganho semântico.
Instalação
Adicionar os sete arquivos, cada um no caminho indicado. Todos são novos;
nenhum arquivo do baseline precisa ser substituído neste incremento.
Arquivo	Responsabilidade
app/chunking/evidence_units.py	Contratos, construtor estrutural, referências e montagem atômica
app/chunking/evidence_snapshot.py	Serialização canônica, catálogo versionado, reconstrução e BM25
app/scripts/prepare_evidence_units.py	Preparação local e verificação de fontes/configuração
docs/validation/EVIDENCE_UNITS_CONFIG.json	Configuração estrutural, sem respostas ou regras de negócio
tests/unit/test_evidence_units.py	Agrupamento, tabelas, papéis, fragmentos, origem e limites
tests/unit/test_evidence_snapshot.py	Reconstrução, mudanças de fonte e matriz física real
docs/validation/EVIDENCE_UNITS_IMPLEMENTATION_GUIDE.md	Este guia e limites da entrega


Executar na raiz do projeto, com a .venv ativa. Não são necessárias dependências
novas; preparação do corpus completo usa Docling/openpyxl já usados no projeto.
python -m pytest tests/unit/test_evidence_units.py tests/unit/test_evidence_snapshot.py -q
Preparar o corpus completo, sem embeddings ou chamadas OpenAI:
python -m app.scripts.prepare_evidence_units --output docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json
Depois, conferir o snapshot sem repetir parsing:
python -m app.scripts.prepare_evidence_units --verify docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json
Inspeção opcional do índice lexical, também sem API:
python -m app.scripts.prepare_evidence_units --verify docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json --query "DOC-005 classification"
O comando não sobrescreve resultados. Para repetir preparação, escolher outro nome.
O resultado informa unidades, quantidade pesquisável, status e hash; o snapshot
contém textos, relações, blocos canônicos, configuração, metadados e proveniência.
catalog_valid indica integridade estrutural, não qualidade da resposta.

Concluir a validação local com a suíte do projeto:
python -m pytest -q
O que foi implementado
- Seções contíguas com caminho explícito podem combinar texto e tabela. Se couber,
  o conjunto é a unidade pesquisável; tabela filha permanece como alvo rastreável.
- Cabeçalhos isolados são navegação, não unidades de regra pesquisáveis.
- Tabelas pequenas ficam inteiras. Tabelas grandes com cabeçalhos podem ser
  localizadas por registro; cada registro conserva cabeçalhos, legenda e textos
  da seção antes/depois da tabela, incluindo possíveis notas.
- Planilhas configuradas são representadas por registro com rótulo, coordenada de
  cabeçalho e coordenada do valor. Fórmula é preservada como fórmula, sem cálculo.
- Texto grande é separado apenas em fronteiras de parágrafo; offsets apontam ao
  texto original. Fragmentos exigem revisão de contexto antes de uso automático.
  Uma cláusula indivisível grande permanece inteira e é marcada como excedente.
- Identidades incorporam documento, SHA-256 físico, versão de representação,
  fontes, conteúdo e relações; não reutilizam o ordinal do chunk antigo.
- O catálogo persiste blocos tipados e reconstrói as unidades para verificar que
  projeções armazenadas correspondam ao construtor e à configuração atuais.
- O texto de busca contém identidade/título/seção/conteúdo. O BM25 existente é
  reutilizado. O texto fica disponível para futura indexação vetorial, que ainda
  não é executada neste incremento.
O agrupamento é estrutural: não garante unidade normativa perfeita. Não há inferência
de que uma regra seja aplicável à pergunta. A montagem não traz automaticamente
todos os registros de uma tabela ao selecionar um deles; seleção por categorias
fica para o planejador. max_chars mede texto de leitura, não tokens nem tamanho
do futuro prompt completo.
Por que existe configuração da matriz
O contrato atual de planilha preserva células, mas não declara cabeçalhos. Inferir
que a primeira linha sempre seja cabeçalho repetiria o problema de interpretação.
A configuração explicita a estrutura das duas folhas da DOC-012 publicada:
Approval Matrix, A1:E1; Document Control, A1:B1. Não contém aprovações esperadas,
IDs de perguntas ou regras especiais para Data Owner.

A declaração está vinculada ao SHA-256 da fonte. Mudança no arquivo exige revisão
da estrutura, não apenas substituir o hash para ignorar a verificação. O construtor
confere rótulos, coordenadas, retângulo completo e ausência de células descartadas.
O preparador rejeita folhas declaradas com células mescladas. Planilha sem declaração
fica como região unresolved_structure, sem associações inventadas.

Esse modo é deliberadamente conservador: planilhas esparsas, tabelas múltiplas,
cabeçalhos hierárquicos e regiões com notas fora do retângulo ainda precisam de
modelagem estrutural. Não será declarado suporte genérico a esses casos.
Leitura dos status
Status	Significado
ready	Representação disponível; não significa aprovação semântica
oversized	Unidade preservada, maior que o limite; não indexada por este construtor
unresolved_structure	Região mantida para localização/revisão, sem associação confiável de cabeçalhos
fragment_requires_review	Parágrafo localizável, mas contexto da regra completa ainda precisa ser resolvido
no_text	Fonte preservada, sem projeção textual pesquisável


Combinações como unresolved_structure:oversized preservam ambas as limitações.
materialize aceita apenas ready e falha atomicamente se exceder o limite total.
Um snapshot pode conter unidades não prontas: sua existência é visível e não vira
silenciosamente uma resposta. O preparador falha se não houver unidade pesquisável.
Compatibilidade, validação e próximos passos
Formato novo: evidence-catalog/2.0; representação: evidence-units/1.
Não enviar esse arquivo ao comparador Stage1 antigo. Os contratos RetrievalChunk,
EvidenceContext, snapshot v1 e ask_knowledge permanecem no baseline.

Verificado no ambiente de desenvolvimento: testes novos, regressão disponível sem
Docling e preparação/verificação da DOC-012 física. O XLSX produziu 18 unidades:
dois pais de planilha e 16 registros, sendo oito decisões e oito itens de controle
documental. Isso não é métrica de recall ou melhoria na resposta.

Docling não está instalado no ambiente de entrega; a execução física do corpus
completo e a suíte que dele depende precisam ser realizadas na máquina local.
Nenhuma chamada paga foi feita. A validade de hashes não autentica fontes; snapshots
devem ser tratados como artefatos controlados, não como conteúdo assinado.

Os próximos incrementos conectam catálogo, escopo e seleção, depois geração e
avaliação integrada. Não há revisor LLM, tradução automática ou alteração de modelo
nesta entrega. Se a nova representação deixar a resposta errada, o diagnóstico
continua distinguindo busca, seleção e fidelidade da geração.