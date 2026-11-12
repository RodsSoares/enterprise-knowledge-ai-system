# Auditoria semântica — Golden Set RV-045

**Enterprise Knowledge AI System** — branch `claude/lean-mvp-hardening`  
**Revisão:** 12/11/2026  
**Escopo:** 46 respostas do RV-045, confrontadas com o catálogo canônico normalizado dos 27 documentos e com `answer_criteria.yaml`.

## Resultado

- **Placar determinístico original:** 45/46 (97.83%).
- **Aprovação na revisão semântica estrita:** 40/46 (86.96%), usando nota ≥9/10 e ausência de erro crítico.
- **Das 45 respostas aprovadas deterministicamente:** 40/45 (88.89%) receberam nota ≥9.
- **Média das 46 notas:** 9,6/10 (julgamento editorial, não estatística de acurácia populacional).
- **Abaixo de 9:** Q17, Q20, Q31, Q32, Q35, ORC-001.
- **Checagem estrutural:** 452 ocorrências de citações no corpo, 272 entradas de fontes, nenhum alias citado sem entrada no rodapé e nenhuma seção listada ausente do catálogo normalizado. Isso não comprova entailment das citações.

## Critério de avaliação

Pontuação combina: (1) aderência semântica às evidências; (2) fidelidade das citações e autoridade documental; (3) completude das obrigações e exceções materiais; (4) relevância e aderência ao escopo da pergunta; (5) calibragem de esclarecimento/abstenção. Nota ≥9 = recomendada como aprovada para este conjunto, sujeita à revisão externa futura. Nota 7–8,9 = revisão recomendada, embora os fatos principais possam estar corretos. Nota <7 = problema grave.

**Limitação importante:** Esta revisão examinou o catálogo normalizado (`EVIDENCE_UNITS_SNAPSHOT_27DOC.json`), não uma inspeção visual independente de cada arquivo original. O arquivo RV-045 é uma versão resumida das execuções, sem o payload integral de retrieval e o mapa original de aliases. Trechos foram confrontados com documentos e seções exibidos nas respostas e presentes no catálogo; não foi verificada a identidade criptográfica de cada alias. Houve apenas uma execução por pergunta, sem teste de estabilidade ou holdout. Não interpretar as notas como certificação de produção.

## Avaliação caso a caso

| Caso | Nota / 10 | Parecer | Fundamentação resumida |
|---|---:|---|---|
| Q01 | 9,4 | Aprovação estrita | **Escalonamento e substituição de transportadora:** Sequência e autoridades corretas; reserva do verificador sobre DOC-007 é adjacente. |
| Q02 | 10,0 | Aprovação estrita | **Prazos por categoria:** Standard, Express, Critical e ressalvas contratuais conferem com DOC-001. |
| Q03 | 10,0 | Aprovação estrita | **Documentos de homologação:** Cobertura integral dos oito itens de DOC-008, incluindo condições. |
| Q04 | 10,0 | Aprovação estrita | **Alçadas de contratação emergencial:** Três faixas e respectivas aprovações conferem com a matriz DOC-012. |
| Q05 | 9,5 | Aprovação estrita | **Limite sem diretoria:** Apresenta corretamente contratos padrão e exceção de contratação emergencial; prolixidade moderada. |
| Q06 | 10,0 | Aprovação estrita | **Classificação de entrega crítica:** Quatro gatilhos, registro e exclusão de simples urgência corretos. |
| Q07 | 10,0 | Aprovação estrita | **Entrega crítica atrasada:** Escalonamento imediato, 30/60 minutos, recuperação e encerramento corretos. |
| Q08 | 9,8 | Aprovação estrita | **KPIs das transportadoras:** Cinco métricas, cadências e responsáveis alinhados com dicionário de KPIs. |
| Q09 | 9,4 | Aprovação estrita | **Cálculo do OTIF:** Fórmula e denominador corretos; detalha SLAs além da pergunta. |
| Q10 | 10,0 | Aprovação estrita | **Meta de OTIF vigente:** 97% a partir de 2026-01-01 sustentado pela política ativa. |
| Q11 | 10,0 | Aprovação estrita | **Mudança da meta de OTIF:** Distingue 95%/97%, data, aprovação e ausência de motivo explicitado: boa calibração. |
| Q12 | 10,0 | Aprovação estrita | **Cláusulas de penalidade:** Atlas e Nova com penalidades; Orion sem penalidade; percentuais corretos. |
| Q13 | 10,0 | Aprovação estrita | **Comparação Atlas/Nova:** Bases de cálculo, tetos e exceção de força maior corretamente comparados. |
| Q14 | 10,0 | Aprovação estrita | **Exceção de força maior:** Prazo de 24 horas e limites de força maior corretamente contextualizados. |
| Q15 | 10,0 | Aprovação estrita | **Critérios de alto risco:** Quatro gatilhos e ressalva de que três semanas de SLA não implicam alto risco automático. |
| Q16 | 9,8 | Aprovação estrita | **SLA três semanas:** Ações semanais e consequências corretas; regra de exceção cobrada pelo verificador não é material. |
| Q17 | 7,2 | Revisão recomendada | **Incidente “semelhante”:** A pergunta não identifica o incidente de comparação. Relata eventos reais, mas afirma semelhança sem referencial; deveria esclarecer. |
| Q18 | 9,5 | Aprovação estrita | **Decisões após incidente grave:** Vincula R003, comitê, checklist, escalonamento e ações; alguns detalhes de tracker tornam a resposta longa. |
| Q19 | 10,0 | Aprovação estrita | **Pendência “daquele incidente”:** Pede corretamente identificar R001 ou R003 antes de afirmar pendências. |
| Q20 | 8,0 | Revisão recomendada | **Políticas para dados com transportadoras:** Descreve DOC-005 e menciona Information Security Policy, mas omite citação direta ao DOC-006, requerida para rastreabilidade multi-política. |
| Q21 | 10,0 | Aprovação estrita | **Informações confidenciais:** Categorias extraídas fielmente de DOC-006. |
| Q22 | 9,4 | Aprovação estrita | **Enviar dados de cliente por e-mail:** Condições corretas e política antiga não apresentada como vigente; abertura “pode” pode exigir leitura cautelosa. |
| Q23 | 10,0 | Aprovação estrita | **Vazamento acidental:** Ações imediatas, preservação de evidência, reporte e fechamento sustentados por DOC-010. |
| Q24 | 10,0 | Aprovação estrita | **Divergência SOP/política:** Conflito histórico, precedência e exceções corretamente fundamentados. |
| Q25 | 10,0 | Aprovação estrita | **Precedência de política:** Hierarquia DOC-007 e exceções corretamente expressas. |
| Q26 | 10,0 | Aprovação estrita | **Versão da política de fornecedores:** DOC-022 v3.0 e vigência corretos. |
| Q27 | 9,8 | Aprovação estrita | **Documento de 2024 ambíguo:** Trata explicitamente os dois documentos possíveis, sem supor qual foi indicado. |
| Q28 | 9,7 | Aprovação estrita | **Comparativo políticas de transportes:** Diferencia mudanças confirmadas de diferenças apenas documentais; não inventa SLAs antigos. |
| Q29 | 10,0 | Aprovação estrita | **Transporte radioativo:** Abstenção correta na ausência de política no universo controlado. |
| Q30 | 10,0 | Aprovação estrita | **Seleção de transportadora:** Pede características da operação e preserva responsabilidade humana. |
| Q31 | 8,8 | Revisão recomendada | **IA para contratos de fornecedores:** Núcleo normativo correto; adiciona treinamento, novas ferramentas e seleção de fornecedores além do necessário. |
| Q32 | 8,4 | Revisão recomendada | **Aprovações de IA com fornecedores:** Aprovações corretas, mas amplia para todas categorias de compartilhamento, análise contratual e exceções sem pedido. |
| Q33 | 9,1 | Aprovação estrita | **Requisitos de segurança em IA:** Cobertura ampla e fonte normativa sólida; excesso de regras adjacentes reduz concisão, mas pergunta é ampla. |
| Q34 | 10,0 | Aprovação estrita | **Aprovação de ferramenta de IA:** AI Governance Owner, revisões e condições especiais corretas. |
| Q35 | 8,8 | Revisão recomendada | **Dados confidenciais em IA:** Resposta condicional correta, mas 21 itens incluem vários processos acessórios; reserva sobre incidentes não é omissão central. |
| Q36 | 9,8 | Aprovação estrita | **Treinamento para IA:** Trilha obrigatória e módulos por função alinhados ao DOC-026. |
| ORC-001 | 8,2 | Revisão recomendada | **Cuidados gerais antes de compartilhar:** Controles DOC-005 corretos, mas volta a introduzir várias obrigações condicionais de IA e fornecedores, ampliando o escopo. |
| ORC-002 | 9,6 | Aprovação estrita | **Compartilhamento sem IA:** Respeita exclusão explícita de IA e cobre classificações e controles; acrescenta transportadoras condicionalmente. |
| ORC-003 | 9,4 | Aprovação estrita | **IA com fornecedor confidencial:** Aprovações de Information Security e AI Governance mais revisão de Data Owner corretas; contexto adicional não central. |
| ORC-004 | 10,0 | Aprovação estrita | **Envio acidental de dados:** Orienta imediatamente notificar, preservar evidência e seguir instruções de contenção. |
| ORC-005 | 9,4 | Aprovação estrita | **Quatro classificações de compartilhamento:** Compara categorias e canais corretamente; menção condicional de IA é lateral. |
| ORC-006 | 10,0 | Aprovação estrita | **Permissão para enviar arquivo:** Não autoriza sem saber conteúdo, classificação e aprovações; pede esclarecimentos seguros. |
| ORC-007 | 10,0 | Aprovação estrita | **Política de radioativo:** Abstenção correta, sem inventar política específica. |
| ORC-008 | 10,0 | Aprovação estrita | **SOP pode criar exceção?:** Resposta curta, exata e corretamente respaldada. |
| ORC-009 | 10,0 | Aprovação estrita | **Exceção técnica de e-mail:** Preserva hipótese de aprovação explícita e condições de envio seguro de DOC-006. |
| ORC-010 | 9,2 | Aprovação estrita | **Compra de IA autoriza dados?:** Não automático corretamente sustentado; detalhamento vai além de sim/não, mas mantém condicionantes. |

## Principais achados e prioridades

### 1. Q17 — referência ambígua tratada como fato

A pergunta “Houve algum incidente semelhante anteriormente?” não identifica o evento de referência. A resposta traz fatos corretos de R001 e R003, mas começa afirmando “Sim” sem estabelecer o que seria semelhante. Uma resposta mais segura pediria qual evento deve ser comparado, ou apresentaria explicitamente os incidentes apenas como exemplos documentados, sem concluir a semelhança.

### 2. Q20 — falha de rastreabilidade multi-documento

Cita a Data Sharing Policy (DOC-005) e **menciona** a Information Security Policy; contudo, não traz citação direta de DOC-006. A questão exige as duas políticas, e os controles de transmissão externa/confidencialidade de DOC-006 são relevantes. Não se trata de uma alucinação grave, mas de suporte documental incompleto.

### 3. ORC-001, Q31, Q32 e Q35 — expansão indevida do contexto

O pipeline tende a transcrever controles de processos adjacentes (governança de IA, compras, treinamento e usos contratuais), mesmo quando não são essenciais à pergunta. As condições em geral são corretamente introduzidas por “se”, mas a resposta perde foco e pode transmitir a impressão de que tudo faz parte do fluxo primário. Ajustar relevância e concisão sem excluir exceções materiais.

### 4. Reservas de verificador potencialmente excessivas

- Q01: exige explicitar regra geral DOC-007 de resolução de conflitos, embora a pergunta trate de substituição de transportadora.
- Q16: exige regra genérica de exceções, embora a pergunta trate da escalada após três semanas.
- Q35: exige incidente de segurança hipotético, embora a pergunta trate de autorização prévia para inserir dados.

Nenhuma dessas reservas, isoladamente, demonstra erro factual da resposta. Precisam de julgamento de materialidade alinhado à pergunta.

## Recomendações

1. Congelar o RV-045 como baseline sem reescrever os critérios olhando apenas os seis casos.
2. Criar um holdout independente, especialmente para referência ambígua, aplicação de múltiplas políticas e tentação de incluir fluxos adjacentes.
3. Manter o verificador por afirmação, mas exigir suporte documental explícito para regras provenientes de documentos diferentes.
4. Testar resumos mais concisos sem perder condicionantes necessários; medir redução de claims irrelevantes por pergunta.
5. Repetir os 46 testes com diferentes sementes/execuções e registrar custos, variância e julgamento humano externo.

## Fontes de reprodução

- [Resultados RV-045](https://github.com/RodsSoares/enterprise-knowledge-ai-system/blob/claude/lean-mvp-hardening/docs/validation/RV045_LEAN_EVALUATION_RESULTS.json)
- [Corpus normalizado RV-045](https://github.com/RodsSoares/enterprise-knowledge-ai-system/blob/claude/lean-mvp-hardening/docs/validation/EVIDENCE_UNITS_SNAPSHOT_27DOC.json)
- [Critérios do Golden Set](https://github.com/RodsSoares/enterprise-knowledge-ai-system/blob/claude/lean-mvp-hardening/data/ground_truth/answer_criteria.yaml)
- [Documentação da branch RV-045](https://github.com/RodsSoares/enterprise-knowledge-ai-system/blob/claude/lean-mvp-hardening/docs/architecture/20_rv045_clean_corpus_and_mvp_interface.md)
