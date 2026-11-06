RV-010 — Revisão das evidências e próximo diagnóstico
Decisão
O RV-010 reproduziu o baseline e mostrou ganho de ordenação em A e B.
O reranker com preservação de prefixo permanece como componente experimental.
O retrieval v0.3 continua como padrão enquanto investigamos as lacunas de
recuperação e de seleção de passagens.

Esta revisão foi feita pelo assistente a partir do JSON completo e das
passagens de referência congeladas. Não substitui revisão humana independente.
Não houve geração de respostas nem avaliação de citações neste experimento.
Evidência verificada
Fonte: docs/validation/RV010_LIVE_RESULTS.json, preservada sem alterações.
SHA-256 canônico do conteúdo JSON:
800b8b74d4210e1ee37999055e3cf76293e471f224d9a07f49f88943590a700a
O arquivo registra 25 perguntas, 125 pares pontuados e snapshot estável.
Recalculamos as métricas por pergunta e por grupo a partir dos chunks
efetivamente selecionados. Todas coincidiram com os resultados registrados.
As seleções de A coincidiram com RV-008, e as ordens restritas coincidiram com
RV-009. O maior delta registrado entre scores atuais e anteriores em A foi
aproximadamente 0,0000023842, sem alterar as ordens restritas.
Métrica	A: v0.3	A: prefix_preserved	B: v0.3	B: prefix_preserved
Hit@1	0,7692	0,9231	0,5833	0,8333
Hit@3	1,0000	1,0000	0,8333	0,8333
Hit@5	1,0000	1,0000	0,8333	0,8333
Recall@1	0,4359	0,5897	0,5000	0,7083
Recall@3	0,8718	0,8718	0,7500	0,7500
Recall@5	1,0000	1,0000	0,7917	0,7917
MRR	0,8846	0,9615	0,6944	0,8333


A ganhou acerto na primeira posição em Q05, Q21 e Q26 e perdeu em Q25.
B ganhou em B04, B07 e B10, sem perdas de Hit@1.
A preservação de Hit/Recall@3 e @5 é uma propriedade da restrição sobre os
documentos selecionados; não demonstra recuperação de evidências adicionais.

A média de pontuação foi 0,7815 s em A e 0,6725 s em B. Comparada com a média
de 2,6404 s de A no RV-008, a redução observada foi de 70,4%. Essa é uma
comparação entre execuções com cinco e vinte pares por pergunta, não um
benchmark controlado de infraestrutura.
Documentos e passagens medem coisas diferentes
O Hit@1 atual considera a identidade do documento. Um chunk introdutório do
documento esperado pode contar como acerto mesmo sem conter a regra solicitada.
A revisão dos trechos encontrou esse problema em B09 e B11, além de evidências
parciais em B05 e B07.
Pergunta	Hit@1 restrito	Grupos de referência no Top-5	Revisão do conteúdo selecionado
B01	0	0/1	DOC-012 ausente; faltam os papéis exigidos para o contrato de R$ 350 mil.
B02	1	0/2	DOC-012 ausente; DOC-022 foi recuperado pelo trecho de onboarding, sem a regra de contratação emergencial.
B03	1	1/1	Trecho distingue relevância histórica de autoridade atual.
B04	1	1/1	Trecho descreve preservação de evidências e proíbe instruir exclusão antes da orientação de Segurança da Informação.
B05	1	0/2	Controles gerais de transmissão e restrição a e-mail desprotegido aparecem; faltam os trechos que explicitam a condição de exceção para e-mail.
B06	0	0/1	DOC-022 ausente; falta a distinção explícita entre desempenho e risco do fornecedor.
B07	1	1/2	Responsabilidade humana e aprovação formal aparecem; falta a passagem sobre segurança não tornar a saída da IA autoritativa.
B08	1	1/1	Passagem de credenciais proibidas e controle de acesso presente.
B09	1	0/1	DOC-025 foi recuperado pelo propósito geral; faltam propriedade intelectual, mudanças do serviço e requisitos de saída.
B10	1	1/1	Treinamento de gestores e atualização anual condicional presentes.
B11	1	0/1	DOC-007 foi recuperado pela hierarquia entre autoridades diferentes; falta a regra para conflitos no mesmo nível de autoridade.
B12	1	1/1	Passagem com autorização e mecanismo para dados Restricted presente.


- Todos os grupos de referência presentes: B03, B04, B08, B10 e B12 — 5/12.
- Cobertura parcial dos grupos: B07 — 1/2.
- Nenhum grupo de referência presente: B01, B02, B05, B06, B09 e B11.
- Grupos encontrados: 6/15, ou 40,00% quando somados entre perguntas.
- Média das frações por pergunta: 45,83%.
Os rótulos de passagens não são exaustivos. Uma passagem alternativa pode
conter evidência válida, como parte dos controles recuperados em B05. Portanto,
essas porcentagens são diagnósticos de cobertura das referências definidas;
não são uma taxa de respostas corretas nem uma nova métrica de aprovação.
Q25: relevância temática e regra diretamente aplicável
O cross-encoder colocou DOC-006::chunk-00008 em primeiro, com score 6,2007.
Esse trecho remete conflitos à Document Governance Policy e diz que documentos
de menor autoridade não podem enfraquecer requisitos de segurança.

DOC-007::chunk-00007, com score 3,1322, contém a regra diretamente solicitada:
uma política corporativa vigente prevalece sobre um SOP conflitante. O trecho
permaneceu na seleção, mas foi deslocado da primeira para a segunda posição.
Isso explica a regressão documental de Q25 sem classificar o primeiro trecho
como inteiramente irrelevante. A revisão de autoridade permanece necessária.
Hipótese a investigar no BM25
As perguntas estão em português e as passagens em inglês. O tokenizer lexical
atual compara tokens literais e não faz tradução nem remoção de stopwords.
Nos cinco trechos selecionados de B02, a única interseção literal com a pergunta
foi o token "a". Em B09, as interseções nos trechos selecionados foram "do" ou
nenhum token. Em B11, não houve interseção literal nos cinco trechos finais.

Esses fatos justificam investigar colisões entre palavras comuns dos dois
idiomas. Ainda não estabelecem quanto o BM25 contribuiu para cada falha:
o RV-010 não registrou seus rankings nem os componentes do RRF. Também não
podemos concluir, com esse JSON, se os chunks corretos estavam abaixo do Top-20,
foram cortados pela fusão ou perderam espaço na seleção final.
RV-011: rastrear a perda antes de alterar a recuperação
O novo script mantém os mesmos parâmetros: vector e BM25 com profundidade 20,
RRF k=60, pool fundido de vinte e seleção diversificada de cinco chunks.
Captura os rankings completos para diagnóstico, mas apenas os vinte primeiros
de cada método alimentam o baseline. Não executa o cross-encoder.

O resultado conterá:
- Catálogo dos 79 chunks, com texto e proveniência.
- Ranking vector completo e todos os resultados BM25 com score positivo.
- Tokens compartilhados em cada resultado BM25.
- Componentes vector e lexical de cada score RRF.
- União dos candidatos, corte de vinte e seleção final de cinco.
- Posição dos documentos esperados e dos grupos de passagens de referência.
- Comparação da seleção final com RV-010 para cada uma das 25 perguntas.
Os rótulos são usados apenas no diagnóstico depois da recuperação. Eles não
influenciam os rankings. O catálogo e os rankings permitirão analisar mudanças
de fusão e seleção posteriormente sem repetir inferência do cross-encoder.
Código por alvo	Interpretação
SELECTED	Pelo menos uma passagem aceitável do alvo chegou ao Top-5.
OUTSIDE_RETRIEVER_TOP20	Nenhuma passagem do alvo entrou nos primeiros vinte de vector ou BM25.
FUSION_TOP20_CUTOFF	O alvo estava na união, mas ficou fora dos vinte primeiros após RRF.
SAME_DOCUMENT_OTHER_PASSAGE_SELECTED	O alvo estava no pool de vinte; entrou outro trecho do mesmo documento.
FINAL_TOP5_SELECTION	O alvo estava no pool, mas ficou fora da seleção final sem outro trecho desse documento.


O diagnóstico de um grupo usa qualquer alternativa aceita pelos rótulos.
Ausência no ranking lexical significa ausência de score BM25 positivo; não
significa ausência do chunk no corpus.
Arquivos desta entrega
Arquivo	Pasta no repositório
smoke_candidate_trace.py	tests/smoke/
test_candidate_trace.py	tests/unit/
RV010_PASSAGE_REVIEW.md	docs/validation/
RV010_REVIEW_RESULTS.json	docs/validation/


Os dois últimos arquivos já documentam a revisão offline realizada aqui.
Os arquivos de entrada RV008_RESULTS.json, RV010_LIVE_RESULTS.json e
reranking_challenge_b.json devem permanecer nos destinos anteriores.

Na raiz do repositório, com a .venv ativa, execute primeiro:
python -m pytest tests/unit/test_candidate_trace.py -q
São 18 testes novos. Depois:
python -m tests.smoke.smoke_candidate_trace --output docs/validation/RV011_CANDIDATE_TRACE.json
Esse comando recompõe o corpus e usa a API de embeddings já configurada,
incluindo uma solicitação de embedding por pergunta. O parsing pode carregar
seus próprios modelos. Não há chamadas ao cross-encoder nem mudanças nas
configurações de retrieval. Não há novas dependências.

Envie o resumo do terminal e RV011_CANDIDATE_TRACE.json. TRACE_COMPLETE significa
que o snapshot se manteve estável e as 25 seleções finais reproduziram o RV-010.
BASELINE_DRIFT e INPUT_CHANGED_DURING_RUN exigem investigar diferenças antes
de atribuir as perdas à execução original.

Opcionalmente, a revisão offline pode ser reproduzida com:
python -m tests.smoke.smoke_candidate_trace --review-only --output docs/validation/RV010_REVIEW_RESULTS.json
Esse modo usa somente os JSONs salvos, sem embeddings ou carregamento de modelos.
Validação da entrega
18 novos testes passaram. O subconjunto disponível do projeto totalizou
156 testes aprovados, e a ajuda da CLI foi verificada. A revisão offline foi
executada sobre o JSON enviado pelo usuário e gerou RV010_REVIEW_RESULTS.json.
A suíte completa do repositório Windows e a captura real do RV-011 não foram
executadas neste ambiente. Não há resultado de RV-011 a declarar nesta entrega.
