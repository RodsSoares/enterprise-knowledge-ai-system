RV-015 — Contrato de respostas estruturadas
Escopo
Primeiro contrato determinístico entre EvidenceContext e uma futura camada de
respostas. Não executa LLM, não decide suficiência semântica e não altera o
retrieval. Usa apenas biblioteca padrão e o componente já validado no RV-014.
Arquivos
Arquivo	Destino
answer_contract.py	app/generation/answer_contract.py
test_answer_contract.py	tests/unit/test_answer_contract.py
RV015_IMPLEMENTATION_GUIDE.md	docs/validation/RV015_IMPLEMENTATION_GUIDE.md


Criar app/generation/ se necessário. O projeto usa namespace packages;
este incremento não exige um __init__.py novo.
Contrato
A resposta contém exatamente request_id, status, claims e
abstention_reason. Cada claim contém exatamente text e citation_ids.
- answered: pelo menos uma afirmação, cada uma com referências existentes
  e sem IDs repetidos; abstention_reason deve ser null.
- abstained: nenhuma afirmação e motivo textual não vazio.
- Contexto vazio exige abstenção. Contexto não vazio permite abstenção;
  presença de trechos não comprova suficiência para responder.
- request_id_for(question, context) vincula pergunta e evidência renderizada
  por SHA-256. IDs E1/E2 são locais, portanto a resposta de outro contexto é
  rejeitada. O hash não é autenticação nem proteção contra conteúdo fabricado.
- parse_answer aceita um único objeto JSON, sem Markdown ou texto externo;
  rejeita campos extras, chaves duplicadas e constantes NaN/Infinity.
- validate_answer valida um dict já decodificado. Usar parse_answer para
  saída textual de um futuro provedor, preservando a checagem de chaves duplicadas.
- O resultado é um dataclass imutável com tuplas de claims/referências.
  Construir o dataclass diretamente não valida nada: a fronteira pública de
  aceitação é parse_answer/`validate_answer`.
Não há campo livre de resposta separado dos claims para evitar conteúdo
adicional sem referências estruturadas. Motivos de abstenção ainda precisam
de avaliação semântica; não são considerados afirmações validadas.
Exemplo de integração (sem modelo)
import json
from app.generation.answer_contract import request_id_for, parse_answer

# question e context são os objetos reais da requisição atual.
request_id = request_id_for(question, context)
raw = json.dumps({
    "request_id": request_id,
    "status": "abstained",
    "claims": [],
    "abstention_reason": "Não há evidência suficiente para responder.",
}, ensure_ascii=False)
answer = parse_answer(raw, question=question, context=context)
O exemplo é uma resposta construída manualmente para demonstrar o contrato,
não uma classificação automática de suficiência.
Validação local
Com .venv ativa, na raiz:
python -m pytest tests/unit/test_answer_contract.py -q
python -m pytest tests/unit/test_evidence_context.py tests/unit/test_evidence_context_replay.py tests/unit/test_answer_contract.py -q
Esperado: 44 passed e 94 passed, respectivamente. Depois:
python -m pytest -q
Se a base permanecer em 576 testes e apenas estes 44 forem acrescentados,
o total esperado é 620 testes. Trata-se de previsão; registrar o resultado
efetivamente obtido no Windows. Não é necessário repetir o replay RV-014,
pois seus componentes e inputs não foram modificados.
Limites e próximo incremento
Os testes usam casos sintéticos determinísticos, incluindo contexto vazio,
abstenção com contexto, citações inválidas, troca de pergunta/contexto,
proveniência inconsistente e JSON malformado. Um teste demonstra explicitamente
que uma afirmação contraditória com ID existente passa na checagem estrutural.
Isso documenta um limite, não um resultado de groundedness.

Esta entrega não mede acurácia de respostas, qualidade da abstenção,
entailment ou resistência a prompt injection. Não inclui resposta parcial,
políticas de acesso, tokens, integração OpenAI nem UI. Falhas de contrato
geram AnswerContractError; não são silenciosamente convertidas em abstenção.

Após validação local: preparar a interface do provedor, instruções de geração
com evidências e avaliação de respostas/citações em casos controlados novos.
Manter as métricas de contrato separadas das métricas semânticas.