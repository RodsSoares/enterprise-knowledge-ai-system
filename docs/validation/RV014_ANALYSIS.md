RV-014 — Análise e validação local
Data: 06/11/2026. Projeto: Enterprise Knowledge AI System.
Evidências
- Rodrigo executou os testes específicos: 50 passed.
- Regressão completa no Windows: 576 passed, 4 warnings in 72.63s.
- Artefato inspecionado: RV014_CONTEXT_REPLAY_RESULTS_local.json.
- SHA-256 dos bytes recebidos: 103ee72a57f59e9907169ec6063761d84efe75e8969112951642692f48e9cd7b.
- Status: OFFLINE_CONTEXT_REPLAY_COMPLETE; snapshot estável.
- Decisão registrada: CONTEXT_CANDIDATE_FOR_REVIEW; sem promoção automática.
- Zero novas chamadas de embeddings ou inferência.
Os campos groups, overall, questions, rv013_audit e drift_from_rv010 coincidem
integralmente com o replay de referência executado no ambiente do assistente.
Os fingerprints de execução não foram tratados como equivalentes entre ambientes.
Foram verificados nos 25 contextos: preservação das âncoras em ordem, ausência
de chunks duplicados, documentos selecionados preservados, limite de dez
chunks, limite de 12.000 caracteres e correspondência entre metadados no
JSON renderizado e o mapa de referências.
Resultados
Medida	Âncoras	Contexto expandido
Média de chunks A+B	5,00	8,72
Média de caracteres A+B	4.473,44	7.247,04
Máximo de caracteres A+B	5.546	8.300
Cobertura macro das referências em B	87,5%	100%
Grupos de referência recuperados em B	13/15	15/15
Perguntas B com todas as referências	10/12	12/12


As seleções Top-5 permanecem intactas nas 25 perguntas. A expansão recupera
as referências faltantes em B07 e B11. O volume total de caracteres cresce
62,0%; não é uma comparação com orçamento igual de cinco chunks.
Avisos da regressão
Todos os quatro avisos foram emitidos durante
test_doc_005_is_parsed_from_physical_corpus, na integração PDF/Docling.
Origem no log	Aviso	Tratamento
Serialização Pydantic / opções OCR	force_full_page_ocr depreciado; mensagem indica mode=OcrMode.FULL_PAGE	Registrar manutenção de compatibilidade do OCR
Pipeline PDF do Docling	generate_table_images depreciado; mensagem indica imagens de página e TableItem.get_image()	Revisar configuração na manutenção de ingestão
RapidOCR do Docling	Acesso a rec_font_path depreciado	Acompanhar compatibilidade das dependências
Convolução PyTorch	padding='same' pode exigir cópia com zero-padding	Possível custo adicional de memória/processamento; sem falha neste teste


São três DeprecationWarning e um UserWarning. O log não mostra falha de
parsing nem regressão de testes. Não se atribui a causa desses avisos ao
Context Builder; não foram suprimidos nem alteradas dependências nesta etapa.
A decisão exata sobre migrações requer inspecionar as configurações e versões
da ingestão, em trabalho separado.
Decisão e limites
O RV-014 está reproduzido localmente e revisado como componente experimental
de montagem de contexto. Manter filtered_only como controle e o reranker
experimental: RV-013 continua MIXED_RESULTS_REVIEW_REQUIRED.

Cobertura de referências não comprova correção das respostas ou sustentação
semântica das citações. A/B são conjuntos de desenvolvimento; A não possui
labels de passagens neste experimento. A divergência histórica RV-011/B11
permanece registrada. O orçamento usa caracteres, não tokens. Permissões,
vigência e precedência documental não são aplicadas por este componente.

Próxima etapa: contrato de resposta estruturada sobre EvidenceContext,
validação de IDs de citação e comportamento de abstenção. A sustentação das
afirmações deve ser avaliada separadamente; IDs existentes não a garantem.
Não houve promoção da configuração padrão, commit ou publicação nesta revisão.