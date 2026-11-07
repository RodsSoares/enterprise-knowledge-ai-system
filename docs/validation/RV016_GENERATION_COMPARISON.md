RV-016 — Comparação de geração com contexto salvo
Objetivo
Isolar a interpretação das regras pelo LLM. Reutilizar exatamente a pergunta,
45 passagens, IDs e texto de RV016_SHARING_AFTER_CONTEXT_FIX.json; não
reprocessar documentos nem gerar embeddings. Nenhum parâmetro do retrieval muda.
Arquivos
Arquivo	Destino	Ação
openai_answer_provider.py	app/generation/	Substituir
compare_saved_generation.py	app/scripts/	Novo
test_saved_generation.py	tests/unit/	Novo
RV016_GENERATION_COMPARISON.md	docs/validation/	Novo


O adapter passa a aceitar instructions opcional, mantendo o prompt atual
como padrão. A aplicação normal não adota automaticamente o prompt alternativo.
Execução
python -m pytest tests/unit/test_saved_generation.py tests/unit/test_rag_service.py -q
Esperado: 26 passed. Depois, com OPENAI_API_KEY já configurada:
python -m app.scripts.compare_saved_generation --source docs/validation/RV016_SHARING_AFTER_CONTEXT_FIX.json --output docs/validation/RV016_GENERATION_COMPARISON.json
A execução faz duas chamadas pagas de geração, sequenciais:
1. current_prompt: instruções atuais, nova geração de controle.
2. conditional_prompt: mesmas instruções mais orientação geral para separar
   categorias, preservar condições/ressalvas e excluir regras de outro processo.
O modelo padrão é o identificador exato registrado no JSON de entrada
(gpt-4.1-mini-2025-04-14 neste caso). Ambos os braços usam o mesmo modelo,
contexto, schema e limite de 2.000 tokens de saída. É possível usar --model
em outra comparação, mas não misturar mudança de modelo e prompt para atribuir
causalidade a uma única variável.

A saída deve ser um arquivo novo. O relatório salva cada braço antes de
executar o próximo, com prompt completo/hash, modelo solicitado/retornado,
request_id, tokens, tempo e resposta. Falhas permanecem erros, nunca abstenções.
O contexto reconstruído é destinado apenas à geração: order e content_types
são placeholders, pois não estavam no JSON original; nenhum metadado entregue
ao modelo é alterado. A restauração verifica igualdade exata do texto renderizado,
mapa de citações e vínculo pergunta/contexto.
Como interpretar
CONTRACT_VALID indica somente formato e referências existentes, não resposta
correta. O veredito semântico permanece PENDING_HUMAN_REVIEW.

Comparar manualmente:
- requisitos distintos por classificação, sem torná-los universais;
- aprovação de IA apenas no contexto de uso em IA, sem obrigação geral indevida;
- ressalva de proteção/processo explicitamente aprovado no caso de e-mail;
- afirmações sustentadas pelos respectivos trechos;
- ausência de informações irrelevantes e de abstenção indevida;
- tokens e tempo.
Esta comparação é diagnóstica: uma amostra por braço não separa completamente
variação estocástica de efeito do prompt nem demonstra generalização. O prompt
histórico não foi registrado; por isso o controle é uma nova geração com as
instruções atuais. Não há promoção automática, juiz LLM nem gabarito inserido
nas instruções. O checklist humano acima não é enviado ao provedor.
Validação da entrega
26 testes focados aprovados no ambiente do assistente. O arquivo real recebido
foi restaurado com 45 passagens e 31.545 caracteres, preservando o request_id.
Nenhuma chamada real de API foi realizada pelo assistente. Enviar o JSON
comparativo após a execução local para revisão das duas respostas.