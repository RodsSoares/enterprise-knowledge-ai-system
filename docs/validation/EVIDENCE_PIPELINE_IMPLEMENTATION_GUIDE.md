Fluxo integrado de evidências — evidence-pipeline/1
Data: 08/11/2026.
Objetivo e escopo
Executar uma pergunta pelo caminho escopo → recuperação → planejamento → geração,
reutilizando os contratos e instruções já avaliados. A aplicação recebe o snapshot
e o cache documental preparados anteriormente; não recebe plano nem resposta salvos.
O gerador recebe o bundle produzido naquela execução, reconstruído antes da chamada.

Esta integração é uma CLI experimental de pergunta única (ask_evidence). O terminal
anterior (ask_knowledge) permanece disponível. Não há interface visual, histórico
conversacional, promoção automática do modelo ou avaliação semântica automática.
Arquivos novos
Caminho	Responsabilidade
app/orchestration/evidence_pipeline.py	Encadeamento das etapas usando um único BudgetedClient
app/scripts/ask_evidence.py	Preflight, parâmetros, execução explícita e relatório persistido
tests/unit/test_evidence_pipeline.py	Integração simulada, saídas funcionais, falhas e orçamento cumulativo
tests/unit/test_ask_evidence.py	CLI, preservação de entradas, cache obrigatório e persistência
docs/validation/EVIDENCE_PIPELINE_IMPLEMENTATION_GUIDE.md	Este guia


Pré-requisitos: incrementos de unidades, planejamento e geração instalados, snapshot
válido e EVIDENCE_UNIT_EMBEDDINGS_local.json preservado. Não substituir os módulos
anteriores por versões diferentes ao instalar estes cinco arquivos.
Fluxo e contratos
1. Verificar fontes físicas e arquivos de preparação contra o snapshot; reconstruir
   unidades canônicas e conferir o cache contra modelo, IDs e textos de busca.
2. Interpretar somente a pergunta. Esclarecimento encerra o fluxo antes da recuperação.
3. Recuperar candidatos com filtros documentais do escopo e embeddings de consulta.
4. Planejar com os candidatos; permitir no máximo um complemento de busca ou expansão.
5. Se houver plano completo, reconstruir e validar seu pedido, suportes e bundle por
   prepare_generation, a mesma função utilizada na geração de planos salvos.
6. Gerar a resposta com o mesmo cliente de orçamento utilizado nas etapas anteriores.
7. Validar referências/cobertura e apresentar condições e fontes pelo código existente.
O relatório contém configuração efetiva, hashes dos insumos e código, instruções,
trace do planejamento, bundle, requisição de geração, resposta, tempo e ledger único.
Checkpoints registram progresso antes da chamada e após eventos, preservando planos
já obtidos mesmo quando não há orçamento para gerar. Não há retry automático.

Saídas:
- dry_run: insumos locais verificados, sem API.
- answered_pending_review: resposta estruturalmente válida, ainda pendente de revisão semântica.
- clarification_required: pergunta de esclarecimento, sem geração posterior.
- abstained: insuficiência reconhecida no planejamento ou na geração; stage/planning/answer
  permitem distinguir a origem. Não é falha técnica nem aprovação de qualidade.
- budget_exceeded: próxima chamada não autorizada pelo orçamento ou limite excedido.
- execution_failed: falha técnica ou contratual, sem conversão artificial em abstenção.
Na API Python, insumos inválidos falham antes de chamadas e são propagados ao chamador.
Na CLI, insumos inválidos são recusados no preflight, antes da criação da saída.
Orçamento único e cache
Caminho normal: 4 chamadas (escopo, embedding da pergunta, plano e geração).
Com expansão estrutural e novo planejamento: até 5. Com busca complementar, novo
embedding e novo planejamento: até 6. Saídas antecipadas podem usar menos.

Todas as chamadas usam uma única instância de BudgetedClient. O orçamento não é
reiniciado entre planejamento e geração. O cache de consulta só vale na execução;
os embeddings documentais são reaproveitados do arquivo obrigatório.

Cache ausente, incompatível ou inválido causa falha de preflight. O runner não o apaga,
não o sobrescreve e não gera embeddings documentais como fallback.

Padrões da CLI para a execução integrada:
Parâmetro	Valor
Máximo de chamadas	6
Orçamento estimado total	USD 0,75
Tokens cumulativos de entrada	400.000
Tokens cumulativos de saída	32.000
Saída por chamada de escopo/plano	8.000
Saída por chamada de geração	8.000
Janela de execução das chamadas	240 segundos


As reservas usam bytes mais margem, não um tokenizer exato; custos são estimados
com preços fornecidos. O preflight verifica insumos, tipos e preços, mas não garante
saldo para todos os caminhos, cujo conteúdo só será conhecido durante a execução.
Cada chamada é admitida pelo orçamento cumulativo antes do envio.

O arquivo Stage1 de configuração é lido para recuperar as_of, modelo de embedding e
seus preços. Modelo de escopo/plano/geração, preços desse modelo, limites por chamada
e orçamento integrado são sobrescritos apenas em memória pelos argumentos/padrões
acima. A configuração efetiva completa fica no relatório; o arquivo original não muda.
Não usar o nome do modelo de embedding como modelo de geração.
Instalação e testes
python -m pytest tests/unit/test_evidence_pipeline.py tests/unit/test_ask_evidence.py -q
python -m pytest -q
Validação desta entrega: 18 testes novos aprovados; 720 testes aprovados na
regressão disponível, excluindo os dependentes de Docling não instalado no ambiente.
O resultado anterior de 787 testes completos é anterior a esta integração. Executar
a suíte completa na máquina do operador para validar a versão integrada.

Os testes exercitam execução normal, esclarecimento, documento ausente, abstenção em
ambas as etapas, erro do gerador, citações inválidas, limites cumulativos de chamadas,
tokens e custo, busca complementar e recusa de segundo complemento. Todos usam SDK
simulado, sem avaliar qualidade de LLM nem efetuar chamadas pagas.

Também foi executado preflight com snapshot e cache reais. Os hashes de preparação
provenientes do Windows exigiram uma cópia temporária do registry/config com CRLF;
o conteúdo correspondia ao local com LF. O repositório e os artefatos originais não
foram alterados. A verificação permaneceu estrita, sem ignorar hashes.
Primeiro dry-run integrado — ORC-001
Executar na raiz do projeto:
python -m app.scripts.ask_evidence --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json --embedding-cache docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json --config docs/validation/STAGE1_RUN_CONFIG_local.json --question "Quais cuidados a política exige antes de compartilhar dados com um fornecedor externo?" --model gpt-6.1-sol --input-price 2 --output-price 10 --output docs/validation/EVIDENCE_PIPELINE_ORC001_GPT61SOL_PLAN_local.json
Os preços 2/10 USD por milhão reproduzem a configuração dos experimentos anteriores;
não são confirmação de tarifa atual. Verificar o valor aplicável à conta antes da
execução paga e ajustar os argumentos se necessário.

Dry-run verifica apenas a preparação. Diferentemente da geração de planos salvos,
a chamada integrada reinterpretará a pergunta e recuperará/planejará novamente.
Os resultados podem diferir mesmo com o mesmo modelo e instruções.

Após revisar o dry-run, execução paga explícita:
python -m app.scripts.ask_evidence --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json --embedding-cache docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json --config docs/validation/STAGE1_RUN_CONFIG_local.json --question "Quais cuidados a política exige antes de compartilhar dados com um fornecedor externo?" --model gpt-6.1-sol --input-price 2 --output-price 10 --output docs/validation/EVIDENCE_PIPELINE_ORC001_GPT61SOL_RESULTS_local.json --execute
Não reutilizar nomes de saída existentes. OPENAI_API_KEY permanece apenas no ambiente.
Nenhuma execução real desse fluxo foi realizada durante a implementação.
Critérios para avançar
Revisar o fluxo integrado de ORC-001 e depois os demais casos de desenvolvimento:
correção do escopo, evidências selecionadas, cobertura, condições, citações e resposta.
Comparar com [a revisão de geração anterior](EVIDENCE_ANSWER_RESULTS_REVIEW.md), sem
presumir que as evidências ou respostas serão idênticas. Avaliar também o custo total,
que inclui escopo e planejamento; não compará-lo diretamente ao custo de geração isolada.

Após validar a integração, congelar os hashes/configuração candidata e avaliar os
casos reservados. Não consultar gabaritos para construir pedidos de runtime, nem
ajustar silenciosamente instruções entre casos reservados. Não apresentar JSON válido,
quantidade de testes ou cobertura de IDs como prova de sustentação semântica.