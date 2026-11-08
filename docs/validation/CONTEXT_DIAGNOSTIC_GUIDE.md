Comparação integrada de contextos — quatro casos de desenvolvimento
Status: experimento preparado; nenhuma geração real executada pelo assistente.
Objetivo: verificar se o gerador produz respostas adequadas com evidência humana
selecionada e se trechos adicionais mudam esse comportamento. Não alterar runtime.
Desenho congelado para a primeira rodada
Gerador/instruções/limite de saída iguais em todos os braços. Quatro perguntas do
conjunto de desenvolvimento; nenhum dos seis casos reservados. O modelo é copiado
da configuração anterior, gpt-4.1-mini-2025-04-14, por continuidade experimental;
não se recomenda essa escolha como modelo futuro de produção.
Caso	Contexto mínimo por chunk	Contexto amplo
ORC-001	DOC-005 chunks 5 e 7	45 passagens do baseline salvo
ORC-002	DOC-005 chunks 5 e 7	Mesmas 45 passagens como banco de distratores
ORC-003	DOC-023 chunk 5 e DOC-012 chunk 1	Mesmas 45 + chunk da matriz: 46
ORC-004	DOC-010 chunks 4 e 5	Mesmas 45 como banco de distratores


Somente ORC-001 possui contexto amplo oriundo da recuperação real dessa pergunta.
Nos outros três, é um controle construído, não uma simulação de ranking real.
Os trechos mínimos são subconjuntos do amplo, conservando ordem relativa e texto.
As citações são renumeradas por contexto; hashes impedem misturar respostas/fontes.

“Mínimo” significa pequeno conjunto de chunks suficiente segundo revisão das
fontes, não texto perfeitamente livre de distratores: o chunk da matriz inclui
outras linhas. Não recortar ou reescrever a evidência para facilitar a resposta.
A seleção humana é controle experimental, nunca método operacional hardcoded.
O gerador não recebe gabarito, lista esperada, rótulo do braço ou critérios.

Uma amostra por braço, oito gerações. Ordem alternada entre braços para evitar
sempre executar mínimo primeiro; isso não controla toda variação nem dá evidência
estatística. Não atribuir efeito exclusivamente a tamanho: seleção também muda
composição, posição e IDs locais. Modelos e parâmetros adicionais ficam para outra
rodada somente se a primeira justificar. Provider defaults são mantidos e registrados
como tais; não se promete determinismo entre chamadas.
Instalação e verificação
Salvar o script em app/scripts, teste em tests/unit e configuração em docs/validation.
Nenhuma alteração dos módulos de produção existentes é necessária.
python -m pytest tests/unit/test_context_diagnostic.py -q
Resultado local: seis testes do experimento passaram; 58 junto dos testes de
orquestração já existentes. Validam integridade, pareamento e execução; não qualidade.
Plano sem API
python -m app.scripts.compare_evidence_contexts --snapshot docs/validation/STAGE1_CORPUS_SNAPSHOT_local.json --comparison docs/validation/STAGE1_ORC001_COMPARISON_v2_local.json --config docs/validation/CONTEXT_DIAGNOSTIC_CONFIG_local.json --output docs/validation/CONTEXT_DIAGNOSTIC_PLAN_local.json
O plano valida snapshot contra arquivos locais, todas as fontes e a resposta
baseline salva. Verifica presença dos quatro casos e monta contextos completos.
Sem --execute não importa/instancia cliente OpenAI. Não faz parsing nem embeddings.
É esperado dry_run, seguido de contagens de passagens e caracteres.
Execução explícita
python -m app.scripts.compare_evidence_contexts --snapshot docs/validation/STAGE1_CORPUS_SNAPSHOT_local.json --comparison docs/validation/STAGE1_ORC001_COMPARISON_v2_local.json --config docs/validation/CONTEXT_DIAGNOSTIC_CONFIG_local.json --output docs/validation/CONTEXT_DIAGNOSTIC_RESULTS_local.json --execute
Usa OPENAI_API_KEY do ambiente, oito gerações no máximo, zero embeddings/parsing.
Configuração mantém tarifas do experimento anterior e reserva custo máximo estimado
US$ 0,25; 400.000 tokens de entrada, 16.000 de saída, deadline 300 s. Isso é orçamento,
não previsão de consumo. A contabilização reutiliza o cliente de orçamento existente,
incluindo sua estimativa conservadora e limitações já documentadas. Falha técnica
interrompe a rodada; resultados/ledger parciais são preservados e não há retries.
Revisão única da rodada
Não decidir por CONTRACT_VALID. Para cada par, revisar:
- ORC-001/002: quatro classes corretamente diferenciadas, condições dos canais;
  não impor IA, compras ou incidentes como obrigações gerais.
- ORC-003: ferramenta/caso de uso e classificação; aprovações de Information
  Security Owner e AI Governance Owner, revisão do Data Owner conforme matriz;
  não impor fluxo de aprovação de ferramenta nova sem essa condição.
- ORC-004: parar divulgação sem destruir provas, reporte imediato, registro dos
  fatos e preservação; não orientar destinatário a apagar evidências antes de
  instrução de Segurança da Informação; seguir coordenação do incidente.
- Todos: sustentação de cada afirmação, completude material, condições preservadas,
  abstenção adequada, referências existentes, custo e tempo.
Resultado inconclusivo é permitido: mínimo insuficiente exige corrigir o mapa,
não culpar automaticamente o modelo. Mínimo funciona/amplo falha apoia foco em
seleção; ambos falham pede distinguir referência insuficiente de limitação de
instruções/modelo; ambos funcionam pede estabilidade e investigação da seleção
original. A rodada não demonstra qualidade do retrieval dos casos 002–004.

Entregar o JSON completo para uma revisão integrada. Não executar casos reservados
nem alterar prompts entre as oito chamadas. Não reindexar corpus para repetir
apenas geração.