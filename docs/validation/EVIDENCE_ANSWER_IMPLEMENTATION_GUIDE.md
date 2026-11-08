Incremento 3 — geração vinculada ao plano de evidências
Data: 08/11/2026. Contrato: evidence-answer/1.
Entrega
Adicionar cinco arquivos, individualmente, nos caminhos abaixo:
Caminho	Responsabilidade
app/generation/evidence_answer.py	Reconstrução do plano/bundle, contrato de resposta, chamada ao provedor e apresentação
app/scripts/generate_evidence_answer.py	CLI de geração a partir de plano salvo, dry-run e orçamento de uma chamada
tests/unit/test_evidence_answer.py	Integridade de origem, referências, condições e limites do contrato
tests/unit/test_generate_evidence_answer.py	Execução simulada, orçamento, preservação de entradas e registro de falhas
docs/validation/EVIDENCE_ANSWER_IMPLEMENTATION_GUIDE.md	Este guia


Este incremento conecta a geração à saída real do planejador por meio do artefato
salvo. Não substitui ask_knowledge nem implementa ainda uma sessão única que execute
recuperação, planejamento e resposta. O contrato permite avaliar primeiro a passagem
plano → resposta sem repetir indexação ou modificar o experimento de planejamento.
Contrato e comportamento
Antes de qualquer chamada, a aplicação reconstrói as unidades do snapshot, valida o
escopo ancorado na pergunta, o último pedido de planejamento, seus metadados, o plano
completo e o bundle. Alteração de textos, offsets ou vínculos causa falha no preflight.
Usa o conteúdo canônico salvo: não revalida os PDFs/XLSX físicos atuais, não faz parsing
nem embeddings, e não consulta gabaritos.

O formato compacto de terminal_model_comparison de ORC-001 é aceito explicitamente:
seus metadados e a data as_of vêm da requisição salva, validados contra o snapshot.
Os limites estruturais atuais são aplicados à admissão desse formato; não são
apresentados como orçamento histórico recuperado. Não é necessário editar o JSON antigo.

O request_id da geração vincula pergunta, escopo, snapshot, bundle, metadados,
instruções e schema. Ele detecta incompatibilidades; não é autenticação.

A resposta estruturada contém request_id, status, claims e abstention_reason.
Cada afirmação tem texto, UM coverage_id e uma lista de citation_ids. Para answered:
- cada item de cobertura precisa aparecer ao menos uma vez;
- citações devem pertencer aos suportes daquele item, não apenas ao contexto geral;
- campos extras, referências repetidas, textos vazios e identidades incompatíveis
  são rejeitados;
- as condições do plano são acrescentadas pelo código na apresentação, junto a cada
  afirmação, inclusive quando um item direct possui condição;
- as fontes citadas são exibidas e preservadas no relatório.
O modelo pode abster-se: claims vazio e razão não vazia. O prompt orienta abstenção
quando o plano não se sustenta nas fontes ou existem conflitos/lacunas. Não se deve
forçar uma resposta para satisfazer a cobertura estrutural.

O validador não comprova entailment ou correção semântica. Um texto contraditório
com IDs corretos ainda pode passar. Existe um teste que demonstra esse limite.
A apresentação da condição não comprova que o texto da afirmação a respeita.
O resultado de uma resposta válida é answered_pending_review, com
semantic_review=not_performed. Abstenções também devem ser revisadas quanto à adequação.

Recusa do provedor, resposta incompleta, erro de contrato e falha operacional não
viram abstenção de evidência. A execução registra a falha e o consumo disponível;
não repete automaticamente. Saídas existentes nunca são sobrescritas.
Validação de código
python -m pytest tests/unit/test_evidence_answer.py tests/unit/test_generate_evidence_answer.py -q
python -m pytest -q
No ambiente de desenvolvimento desta entrega: 30 testes novos aprovados; regressão
executável de 702 testes aprovada. Foram excluídos os testes dependentes de Docling,
que não está instalado nesse ambiente. A suíte completa deve ser executada na
máquina local com Docling; 702 não é a contagem esperada para essa máquina.

Os quatro relatórios reais GPT61SOL foram aceitos pelo preflight e os bundles foram
reconstruídos: ORC-001 (7 itens/4 unidades), ORC-002 (7/4), ORC-003 (3/2), ORC-004 (8/3).
Nenhuma resposta real foi gerada durante a implementação; zero chamadas pagas.
Primeiro experimento: ORC-001
Usar o mesmo modelo do planejamento candidato facilita avaliar a nova etapa antes
de comparar modelos menores. Isto é uma escolha experimental, não promoção ao padrão.
As tarifas 2/10 USD por milhão abaixo reproduzem as tarifas configuradas nos
experimentos anteriores. Não são uma consulta atual de preços. O operador deve
ajustá-las caso os valores aplicáveis à conta sejam diferentes.

Dry-run, sem chamada à API:
python -m app.scripts.generate_evidence_answer --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json --source docs/validation/EVIDENCE_PLANNER_ORC001_GPT61SOL_RESULTS_local.json --model gpt-6.1-sol --input-price 2 --output-price 10 --output docs/validation/EVIDENCE_ANSWER_ORC001_GPT61SOL_PLAN_local.json
O preflight também verifica a reserva do orçamento. O limite padrão é uma chamada,
8.000 tokens de saída, 120.000 de entrada, USD 0,25 e deadline de 180 segundos. A
reserva usa bytes mais margem como aproximação conservadora, não tokenização exata
nem promessa de faturamento. No dry-run de ORC-001, a reserva estimada foi USD 0,13306;
isso não é o custo real esperado. O uso real estará no resultado após execução.

Após conferir o dry-run, execução de UMA chamada paga de geração:
python -m app.scripts.generate_evidence_answer --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json --source docs/validation/EVIDENCE_PLANNER_ORC001_GPT61SOL_RESULTS_local.json --model gpt-6.1-sol --input-price 2 --output-price 10 --output docs/validation/EVIDENCE_ANSWER_ORC001_GPT61SOL_RESULTS_local.json --execute
OPENAI_API_KEY precisa estar configurada localmente. Não há parsing, busca,
reinterpretação de escopo, replanejamento ou embeddings nessa execução. Modelo,
preços, limite de saída e orçamento podem ser alterados no terminal, sem editar os
arquivos individuais. Use novo nome de saída para cada experimento.
Revisão da resposta antes de avançar
- ORC-001/002: classificações separadas, canais adequados, transportadoras e exceções
  condicionais; nenhum requisito de IA ou resposta a incidente imposto ao compartilhamento.
- ORC-003: Information Security Owner e AI Governance Owner como aprovadores,
  Data Owner como revisão adicional; ferramenta e caso de uso aprovados.
- ORC-004: reporte, contenção quando viável, registro, preservação, não apagar
  evidências sem orientação e cumprimento das instruções; respeitar coordenação.
- Em todos: afirmações sustentadas pelos trechos citados e cobertura real, sem
  obrigações inventadas ou condições transformadas em fatos do usuário.
Depois de ORC-001 revisado, os demais planos podem usar o mesmo comando, trocando
os identificadores no source/output. Não é necessário repetir os experimentos de
planejamento. Somente após avaliar a geração deve-se integrar a execução completa
e congelar a configuração para os casos reservados.
Atualização de validação — 08/11/2026
Após a entrega, o operador executou a suíte completa: 787 passed, 4 warnings em
76,89 s, incluindo Docling. Em seguida, gerou respostas reais para ORC-001 a
ORC-004, uma chamada por caso. As quatro foram consideradas adequadas na revisão
assistida contra as fontes; custo estimado total de geração: USD 0,048080.

Os status automáticos permanecem answered_pending_review; esta revisão externa
não é um avaliador semântico da aplicação. O relato acima de zero chamadas pagas
refere-se à implementação, anterior às execuções realizadas pelo operador.

Ver [revisão dos resultados](EVIDENCE_ANSWER_RESULTS_REVIEW.md) para evidências,
limitações, consumo por caso e critérios da próxima etapa. Não é necessário repetir
as chamadas já concluídas para instalar esta atualização documental.