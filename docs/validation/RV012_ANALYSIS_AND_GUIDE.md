RV-012 — Filtro lexical e replay das evidências
Resultado e decisão
O replay offline do RV-011 confirmou que correspondências lexicais fracas
estavam deslocando evidências relevantes na fusão. Um filtro de palavras
gramaticais aplicado somente à consulta BM25 melhorou as métricas documentais
em A e B, preservando a diversificação e o limite de cinco chunks.

A implementação é um componente opcional. A candidata para a próxima
validação real é filtered_hybrid_diverse. O HybridRetriever existente mantém
seus defaults. O reranking não foi executado nem simulado neste replay.

A/B já foram inspecionados durante o desenho desta correção; ambos são
conjuntos de desenvolvimento para ela. Os resultados abaixo são exploratórios,
não uma validação independente ou uma garantia de respostas corretas.
B11: o que mudou entre RV-010 e RV-011
Os quatro primeiros chunks ficaram iguais. A quinta posição mudou:
Execução	Quinto chunk
RV-010	DOC-005::chunk-00011
RV-011	DOC-022::chunk-00010


Os dois trechos têm o mesmo texto e a mesma seção de controle documental.
Nenhum contém a regra solicitada por B11. As métricas documentais da pergunta
permaneceram iguais, e a passagem de referência DOC-007::chunk-00007 continuou
fora da seleção final.

No RV-011, os scores vetoriais dos dois chunks foram aproximadamente
0,400421599 e 0,400473919. Vários avisos idênticos também aparecem empatados.
Isso descreve a sensibilidade observada na fronteira da seleção. A origem da
diferença numérica entre execuções não foi estabelecida: o RV-010 não guardou
os scores vetoriais brutos nem os embeddings.

O flag BASELINE_DRIFT do RV-011 foi preservado. O RV-012 usa as listas do
próprio RV-011 como baseline pareado para todas as alternativas. O resultado
também apresenta B_matching_rv010, com as onze perguntas B cuja seleção
reproduziu exatamente o RV-010, para deixar B11 identificável.
Perda de evidência confirmada
Caso / passagem	Posição vector	Posição após RRF	Resultado no v0.3
B01 — matriz de aprovação	1	6	Fora dos cinco finais
B02 — política de contratação	1	9	Entrou outro trecho de DOC-022
B02 — matriz de aprovação	2	11	Fora dos cinco finais
B05 — restrição de e-mail	1	2	Entrou outro trecho de DOC-006
B06 — desempenho e risco	1	6	Fora dos cinco finais
B09 — due diligence	1	3	Entrou a introdução de DOC-025
B11 — conflito no mesmo nível	2	2	Entrou a hierarquia de DOC-007


Em B01, B02 e B06, trechos favorecidos pela fusão tinham correspondências
literais baseadas em palavras como "a" ou "do". Um candidato presente em vector
e BM25 recebe contribuição das duas listas no RRF, mesmo quando a coincidência
lexical é pouco informativa. O filtro remove esses termos antes de calcular
os scores e selecionar o Top-20 lexical.

B11 mostra uma causa adicional: sem resultados BM25 positivos, o chunk correto
já estava em segundo no ranking vetorial. A seleção que prioriza documentos
distintos escolheu apenas o primeiro chunk de DOC-007.
Implementação
app/retrieval/lexical_query_filter.py acrescenta:
- filter_lexical_query: utiliza o tokenizer já existente e remove uma lista
  inicial de 136 palavras gramaticais PT/EN, mantida no próprio projeto.
- FilteredLexicalRetriever: envolve o adaptador lexical existente; se não
  restarem termos, retorna uma lista lexical vazia para a fusão usar vector.
- Preservação de números, identificadores como DOC-012 e ISO-27001, siglas e
  termos de negação, como não, not, no, sem e without.
A pergunta original continua sendo enviada ao retriever vetorial. O corpus,
os comprimentos de documentos e o cálculo de IDF do índice lexical permanecem
iguais. Não há tradução, geração de novas consultas, ajuste de pesos nem
remoção de hits depois do corte Top-20.

Versão da política: pt_en_function_words_v1.
SHA-256 canônico da lista ordenada de termos:
d179093e1bfeb461b3f52c70f8d4319337cc9c027bf9e37cdd3149838f06cd48
A lista é uma heurística inicial do projeto. Não contém question IDs,
document IDs nem regras por resposta esperada. Os rótulos entram apenas na
avaliação após a recuperação.
Comparação pareada, sem reranking
Todas as alternativas usam cinco chunks finais e o mesmo ranking vetorial
salvo. A lista lexical é recalculada sobre os mesmos 79 textos.
Alternativa	A Hit@1	A Recall@5	B Hit@1	B Recall@5	B cobertura média das referências
hybrid_v03	76,92%	100,00%	58,33%	79,17%	45,83%
vector_diverse	76,92%	100,00%	100,00%	100,00%	87,50%
filtered_hybrid_diverse	84,62%	100,00%	100,00%	100,00%	87,50%
filtered_hybrid_top5	84,62%	92,31%	100,00%	95,83%	95,83%


O controle vector_diverse mostra quanto a remoção do ruído lexical contribui
em B. O híbrido filtrado preserva o benefício lexical observado em A, incluindo
a consulta com o termo SOP em Q25, e supera esse controle em Hit@1 de A.

Para filtered_hybrid_diverse:
- A: Hit@1 de 10/13 para 11/13; MRR de 0,8846 para 0,9231.
- B: Hit@1 de 7/12 para 12/12; MRR de 0,6944 para 1,0000.
- Nenhuma das métricas documentais acompanhadas regrediu, inclusive quando
  comparadas individualmente por pergunta contra o baseline RV-011.
- B: perguntas com todos os grupos de referência presentes passaram de 5/12
  para 10/12; grupos encontrados passaram de 6/15 para 13/15.
- A cobertura média por pergunta passou de 45,83% para 87,50%.
- Excluindo B11, a cobertura média filtrada foi 95,45% nas onze perguntas
  restantes; a comparação completa continua reportada separadamente.
Cobertura de referências é um diagnóstico não exaustivo. Esses números não
medem a correção de respostas geradas. O Hit@1 aqui é documental.
Pendências e alternativa rejeitada
B07 ainda não recuperou a passagem DOC-024::chunk-00007 sobre revisão humana
da saída da IA. B11 ainda escolhe a hierarquia em vez de incluir a regra de
conflito no mesmo nível. São lacunas de seleção de passagens, apesar do Hit@1
documental correto.

Desligar a diversificação recuperou a referência de B11, mas reduziu Recall@5
em Q20, Q34 e B07. Por isso, filtered_hybrid_top5 não foi selecionado como
substituto geral. Uma etapa posterior deverá tratar múltiplas passagens úteis
por documento sem perder a cobertura documental necessária.

O resultado de A com filtro, 84,62%, não deve ser comparado como se fosse o
resultado da composição filtro + reranker. O RV-010 chegou a 92,31% com
reranking sobre outra seleção. Vários chunks mudaram com o filtro e não têm
scores daquele experimento. A composição precisa de uma medição própria.
Arquivos e execução local
Arquivo	Pasta no repositório
lexical_query_filter.py	app/retrieval/
test_lexical_query_filter.py	tests/unit/
smoke_lexical_filter_replay.py	tests/smoke/
test_lexical_filter_replay.py	tests/unit/
RV012_LEXICAL_REPLAY_RESULTS.json	docs/validation/
RV012_ANALYSIS_AND_GUIDE.md	docs/validation/


Mantenha RV008_RESULTS.json, RV010_LIVE_RESULTS.json e RV011_CANDIDATE_TRACE.json
em docs/validation/, e a definição B em data/ground_truth/. O script utiliza
também os helpers já instalados nos incrementos anteriores.

Na raiz do repositório, com a .venv ativa:
python -m pytest tests/unit/test_lexical_query_filter.py tests/unit/test_lexical_filter_replay.py -q
São 22 novos testes. Em seguida, reproduza o replay:
python -m tests.smoke.smoke_lexical_filter_replay --output docs/validation/RV012_LEXICAL_REPLAY_RESULTS_local.json
Esse comando é totalmente offline: não recria embeddings, não carrega o
cross-encoder e não reparsa documentos. Primeiro verifica o catálogo, os
rankings, os scores, os componentes do RRF e a seleção original; depois
compara as quatro alternativas. Os resultados esperados são os da tabela
acima. O JSON completo desta entrega já foi gerado a partir do arquivo enviado.

O novo componente pode ser integrado no ponto em que vector e lexical já
foram construídos, criando um retriever candidato separado:
from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.document_diversifier import DocumentDiversifier
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.lexical_query_filter import FilteredLexicalRetriever

candidate_retriever = HybridRetriever(
    vector_retriever=vector,
    lexical_retriever=FilteredLexicalRetriever(lexical),
    fusion=ReciprocalRankFusion(k=60),
    candidate_depth=20,
    document_diversifier=DocumentDiversifier(),
)
Esse exemplo pressupõe os objetos vector e lexical já existentes no código.
Os arquivos entregues não substituem automaticamente a configuração padrão.
Validação e rastreabilidade
O replay foi executado e concluiu as verificações de rankings e scores do
RV-011. O hash canônico do trace usado é:
00179fb0e687cd79cb0e855bd2d96df2a97e0138d63401aea01b289e381c2ecd
22 novos testes passaram; o subconjunto disponível do projeto totalizou
178 testes aprovados. A CLI de ajuda também foi verificada. Os testes de
integração locais exercitam o wrapper com o HybridRetriever e um índice BM25
real, verificando que a consulta vetorial permanece inalterada.

A suíte completa do repositório Windows e a combinação real do filtro com
o reranker não foram executadas neste ambiente. Nenhum arquivo de resultado
enviado pelo usuário foi alterado, e nenhuma configuração foi promovida.