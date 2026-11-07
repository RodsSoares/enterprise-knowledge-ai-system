RV-016 — Primeiro fluxo RAG com LLM no terminal
Entrega
Fluxo: documentos físicos → ingestão/chunks → embeddings + BM25 → RRF →
diversidade → contexto RV-014 → Responses API → contrato RV-015 → resposta
com trechos e referências. Não importa módulos de testes nem usa rankings
congelados para responder. O índice é construído uma vez por sessão e
reutilizado para perguntas independentes; não há histórico conversacional.
Arquivo	Destino
openai_answer_provider.py	app/generation/openai_answer_provider.py
rag_service.py	app/generation/rag_service.py
ask_knowledge.py	app/scripts/ask_knowledge.py
test_rag_service.py	tests/unit/test_rag_service.py
RV016_IMPLEMENTATION_GUIDE.md	docs/validation/RV016_IMPLEMENTATION_GUIDE.md


A entrega inicial adicionou os arquivos acima. A correção de contexto descrita
ao final também atualiza app/retrieval/evidence_context.py. A composição
da demonstração opta pelo filtro lexical, sem reranker; não altera defaults do
HybridRetriever. Recupera o pool fundido de 20 antes da diversidade Top-5 e
expande documentos curtos selecionados com ShortDocumentContextBuilder.
O EvidenceContextBuilder original do RV-014 continua disponível sem alteração
de sua política de seleção.
Testar sem API
python -m pytest tests/unit/test_rag_service.py -q
Esperado após a correção: 19 passed. A integração usa retrieval real com embeddings e
geração simulados na fronteira externa. Cobre seleção/contexto, referências,
abstenção, falhas, respostas incompletas, recusa do provedor e terminal.
Não comprova qualidade semântica nem compatibilidade de uma chamada real.
Executar com API
Usar a .venv do projeto, com as dependências já instaladas. A CLI lê
OPENAI_API_KEY do ambiente; não carrega .env automaticamente. Se a chave
já está configurada na sessão, não é necessário configurá-la novamente.
Não enviar a chave ao chat nem salvá-la nos arquivos do projeto.
python -m app.scripts.ask_knowledge
Padrões: corpus data/source/corporate_repository, embedding
text-embedding-3-small, geração gpt-4.1-mini. Alterar o modelo por
--model ou OPENAI_MODEL, usando um modelo disponível na conta que suporte
Responses e Structured Outputs. Não há fallback automático de modelo.

O programa lista a configuração, processa documentos físicos com nomes
DOC-numero_nome, indexa e abre o prompt Pergunta (/sair):.
A primeira inicialização pode carregar recursos do Docling/OCR. Nesta versão,
fechar e reabrir o processo repete parsing e embeddings do corpus. Para evitar
esse custo durante a exploração, usar várias perguntas na mesma sessão.

Cada pergunta chama embeddings para a query e, se houver contexto, uma geração.
Essas chamadas são pagas pela conta de API. Perguntas não compartilham memória.
O provedor usa timeout de 60 segundos e zero retries automáticos. Uma falha
encerra esta CLI com erro, sem apresentá-la como abstenção de conhecimento.

Para salvar uma resposta e as evidências para revisão:
python -m app.scripts.ask_knowledge --question "Quais cuidados a política exige antes de compartilhar dados com um fornecedor externo?" --output docs/validation/RV016_ANSWER_01.json
O arquivo de saída deve ser novo; o programa recusa sobrescrever arquivos.
O JSON contém pergunta, resposta, contexto integral, referências, modelo
retornado pelo provedor, usage e tempo da pergunta (exclui indexação inicial).
Não registra tokens ou custo monetário dos embeddings nesta versão.
Revisão prática
Na sessão interativa, testar três perguntas, conferindo os trechos exibidos:
1. Uma pergunta coberta: cuidados antes de compartilhar dados com fornecedor.
2. Uma pergunta que exige combinar regras: como proceder diante de documentos
   conflitantes de igual autoridade.
3. Uma pergunta deliberadamente fora do corpus: qual foi o lucro líquido real
   da empresa no último trimestre. Sem evidência correspondente, esperar
   abstenção; isso precisa ser observado, não é garantido pelo schema.
Enviar as respostas e fontes ou o JSON salvo. A avaliação deve verificar se
cada afirmação está sustentada, se referências relevantes ficaram ausentes e
se a abstenção foi adequada. Não confundir JSON aceito com resposta correta.
Limites explícitos
- A ausência de contexto força abstenção sem LLM. Com contexto, a decisão de
  insuficiência é do LLM e ainda precisa de avaliação; retrieval vetorial
  normalmente retorna candidatos mesmo para perguntas fora do corpus.
- Recusa da API, timeout, output incompleto e contrato inválido são erros
  distintos de abstenção. Não há reparo silencioso ou nova tentativa.
- Limites: 4.000 caracteres na pergunta, 32.000 no contexto renderizado,
  até 60 chunks e 2.000 tokens de saída. Caracteres não equivalem a tokens;
  ainda não há orçamento dinâmico de entrada específico por modelo.
- Instruções pedem uso exclusivo das evidências. Isso não é uma barreira
  comprovada contra prompt injection nem validação semântica de citações.
- Sem ACL, aplicação automática de vigência/autoridade, memória, cache
  persistente ou frontend. Uso inicial no corpus sintético do projeto.
Fontes de implementação
- Structured Outputs
- GPT-4.1 mini
Consultadas em 06/11/2026. Adapter usa responses.create com text.format
json_schema estrito e store=False, seguido da validação local RV-015.
Nenhuma chamada real foi executada pelo assistente nesta entrega.
Correção após primeira execução real
O diagnóstico RV016_SHARING_DIAGNOSTIC.json mostrou dez trechos, dos quais
apenas dois do DOC-005: título/metadados e Purpose. A tabela de classificação
(chunk 5), os canais aprovados (chunk 7) e as exceções (chunk 9) não estavam
no contexto. A resposta também confundiu compartilhamento COM fornecedores
com uso de dados DE fornecedores em IA. O log não contém o pool completo:
não se afirma em que posição esses trechos ficaram antes da seleção.

A correção trata os dois pontos:
- Montagem: preservar âncoras e acrescentar todos os chunks dos documentos
  selecionados cujo texto total tenha até 6.000 caracteres. Acrescentar um
  documento inteiro ou registrar que não coube; não selecionar apenas os
  primeiros fragmentos até o limite. Não há IDs ou perguntas específicos na
  lógica. Documentos maiores mantêm no máximo um suplemento por ranking.
- Limites globais: 60 chunks e 32.000 caracteres renderizados, contando
  metadados. A ordem de prioridade dos documentos segue as âncoras. A expansão
  é completa apenas em relação aos chunks do catálogo fornecido, não uma
  garantia de parsing perfeito. Nenhum documento não selecionado é introduzido.
- Proveniência: trechos de expansão carregam o chunk canônico e papel
  parent_document, sem scores/ranks de retrieval inventados. O JSON de saída
  inclui papéis, tamanho do contexto e motivos de omissão.
- Instruções do LLM: preservar direção, condições e momento da ação; não
  importar automaticamente regras de IA ou incidentes para outra situação.
A expansão é uma solução inicial para o corpus de documentos curtos. Não é
uma política validada para documentos longos ou escala de produção. Ela
fornece mais evidência, mas também pode introduzir mais distrações e aumentar
custo/latência; o efeito semântico precisa ser medido na nova execução.

Verificação offline: reconstruídas as cinco âncoras do diagnóstico usando o
catálogo RV-011; os textos dos dez trechos recebidos coincidem com esse catálogo.
Não se recomputou retrieval nem se chamou LLM. Nesta reconstrução, a expansão
incluiu os chunks 5, 7 e 9 de DOC-005, sem omissões por orçamento. O contexto
passou de 10 para 45 trechos e de 7.222 para 31.545 caracteres (4,37 vezes).
Isto é evidência de montagem de contexto, não resultado de uma nova resposta.

Substituir quatro arquivos: evidence_context.py, rag_service.py,
openai_answer_provider.py, test_rag_service.py; atualizar este guia.
O ask_knowledge.py entregue anteriormente permanece compatível.
python -m pytest tests/unit/test_rag_service.py tests/unit/test_evidence_context.py tests/unit/test_evidence_context_replay.py tests/unit/test_answer_contract.py -q
python -m app.scripts.ask_knowledge --question "Quais cuidados a política exige antes de compartilhar dados com um fornecedor externo?" --output docs/validation/RV016_SHARING_AFTER_CONTEXT_FIX.json
Esperado nos testes: 113 passed. A segunda linha chama APIs reais e exige
arquivo de saída novo. Comparar com o diagnóstico anterior: requisitos por
classificação, condições explicitadas, ausência de regras de IA indevidas,
citações sustentadas, tokens e tempo. Não é necessário digitar um DOC-ID.

Validação sem API nesta correção: 19 testes de integração focada, 113 com os
contratos/contexto anteriores. A resposta corrigida real ainda está pendente.