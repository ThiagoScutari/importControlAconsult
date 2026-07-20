# Spec — Extrator de Dados de Importação → Domínio
### Contabilidade Aconsult · Mockup de validação

**Versão:** 0.5 (CONNECTA + validação de despesas — substitui a 0.4)
**Data:** 2026-07-20
**Etapa:** Validação de fluxo, extração e formato de saída. **Não** é desenvolvimento de produção. Nesta rodada o mockup vai ao ar em **VPS com URL própria** para a Larissa testar extração/exportação e dar feedback.

> **Registro de revisão `[R4]` (2026-07-20):** CONNECTA como **5º layout de fechamento**; validação de **despesas recorrentes/obrigatórias** e **reconciliação** (Σ despesas == TOTAL; numerário − total == saldo). Mudanças marcadas com `[R4]`.

> **Registro de revisão `[R3]` (2026-07-13):** decisões do arquiteto após a inspeção de código do Claude Code. Confirmado: (1) pinar deps + endurecer detector + **construir parser ALL TIME na Fatia 1**; (2) contas **em branco + aviso** (sem default chutado; de-para pré-preenche as conhecidas); (3) **conferência navegável (diff + seleção) entra na Fatia 1**. Achados de inspeção incorporados: parser ALL TIME **inexistia** no código; Passo 7 (pagamento via banco) **não implementado**; sinal da variação **invertido** vs. a planilha real; anexos/imagens caíam em "tipo não reconhecido". Entrega dividida em **Fatia 1** (destrava o teste da Larissa) e **Fatia 2** (ver Seção 13). Mudanças marcadas com `[R3]`.
**Objetivo:** provar que conseguimos (1) extrair os dados dos documentos de importação de um processo e (2) gerar os artefatos de saída (extração estruturada + lançamentos no layout do Domínio), validando o fluxo com a key user (Larissa) antes de investir em desenvolvimento.

> **Registro de revisão `[R2]` (2026-07-13):** ajustes derivados da 2ª reunião com a Larissa. Itens tocados: 1.3 (câmbio manual), 1.4 (contas manuais + formatação do nº da NF), 1.5 (regra do adiantamento), 3 (conferência navegável entra no escopo), 5 (banco manual), 6 (separação "Relação por empresa" × "dados extraídos" descartáveis), 9–12. Mudanças marcadas com `[R2]` no corpo.

> **Ponto de partida deste documento:** o **POP da Larissa** é a nossa base de conhecimento (Seção 1). Toda regra de negócio — quais documentos entram, o que se extrai de cada um, e como isso vira lançamento contábil — deriva dele. A Seção 1 é **canônica e versionada**: cada novo POP recebido é anexado ali, e o restante do spec se ajusta ao que ela disser.

---

## 1. BASE DE CONHECIMENTO — POP (fonte da verdade)

> **Como manter esta seção:** este é o repositório do conhecimento extraído dos POPs. Fonte atual: **(P1)** "Forma Correta de Envio da Documentação de Processos" e **(P2)** "POP Geral IMPORTAÇÃO", ambos da Larissa. Ao receber novos POPs, **acrescente** subitens numerados (1.x) e marque a origem `[P3]`, `[P4]`… Não sobrescrever — versionar. Onde o POP não define uma regra, marcar explicitamente como **LACUNA** (ver 1.6).

### 1.1 Taxonomia documental — o "processo completo" `[P1]`

Um processo de importação = **pasta com 6 blocos de documentos**. O operador deve enviar todos; o extrator deve reconhecê-los.

| # | Documento | Para que serve | Campos-chave a extrair |
|---|---|---|---|
| 01 | **Nota de Entrada (NF-e/DANFE)** | Lançamento do processo no sistema | Nº NF, chave, valor total, produtos, NCM, obs. (DI/Invoice no corpo), CBS/IBS quando houver |
| 02 | **DI ou DUIMP** | Conferência e contabilização | Taxa de câmbio da DI, valor a pagar ao estrangeiro, **VCMV**, tributos (II/IPI/PIS/COFINS/Siscomex), adições/itens |
| 03 | **Comercial Invoice** | Valor devido ao fornecedor no exterior | Nº invoice, moeda, valor FOB em moeda estrangeira, itens |
| 04 | **Fechamento do Despachante** (+ anexos) | Lançar custos do processo, baixar armazenagem/frete | Despesas por tipo, adiantamentos, saldo. **Anexos:** NFS-e de serviço, **CT-e**, boletos, GRU, DARE, termos AFRMM |
| 05 | **Fechamento Trading × Cliente** | Conferência final do processo | Preferir o **fechamento completo**, não só o numerário |
| 06 | **Contrato de Câmbio pago** | Baixa do fornecedor no exterior + variação cambial | Data de liquidação, taxa de câmbio, valor em moeda estrangeira e em R$, instituição financeira, vínculo com a importação |

**Regra de organização `[P1]`:** uma pasta por processo → no mockup, **um upload = um processo** (resolve o agrupamento sem casar arquivos por nome).

### 1.2 Identificação do processo no mês `[P2 · Passo 1]`

- Origem: módulo Fiscal → Relatórios > Acompanhamentos > **Resumo por Acumulador** (por período).
- **Acumuladores de importação:** `57` e `1001`.
- **CFOP:** `3102` = importação **própria**; `5949` = **encomenda** (NF física com destinatário = cliente e remetente = trading).

### 1.3 Planilha de controle — colunas calculadas `[P2 · Passo 3]`

Aba "Fornecedores Estrangeiros / Controle de Importações" (uma aba por fornecedor estrangeiro). Oito campos numerados (aprox. colunas **O–W**):

| # | Campo | Origem | Fórmula |
|---|---|---|---|
| 1 | VALOR INVOICE US$ | Invoice / DI (moeda estrangeira) | — |
| 2 | TX DI | Invoice / DI | — |
| 3 | **RESULTADO EM R$** | calculado | **1 × 2** → provisão do fornecedor |
| 4 | VLR USD PG CÂMBIO | Contrato de câmbio (moeda estrangeira) | — |
| 5 | TX CÂMBIO | Contrato de câmbio | — |
| 6 | VLR PG R$ | calculado | **4 × 5** |
| 7 | VLR PG × TX DI | calculado | **4 × 2** → "o que deveria ser pago ao fornecedor" |
| 8 | **VARIAÇÃO** | calculado | **`[R3]` = campo 6 − campo 7** (VLR PG R$ − VLR PG × TX DI), conforme a coluna **X** da Relação real. O código estava com o sinal **invertido** (7 − 6) — corrigir. |

> Atenção contábil: o campo **3 (RESULTADO EM R$)** é a **provisão do fornecedor** = USD da invoice × taxa da DI. **Não** é o valor da NF nem o valor aduaneiro.

> **`[R2]` Câmbio é entrada manual:** os campos **4 (VLR USD PG CÂMBIO)** e **5 (TX CÂMBIO)** são digitados pelo operador. O contrato de câmbio quase sempre chega **depois** do restante do processo (às vezes só após o processo inteiro concluído), então raramente vem no pacote de upload. Os campos já existem no formulário de conferência; a variação (campo 8) é calculada a partir deles. Confirma a LACUNA 1.6.

### 1.4 Convenções de cadastro `[P2 · Passo 4]`

- **Conta do processo (plano de contas):** `PROCESSO + <nome conforme Fechamento/Prestação de Contas> + DI <nº DI> + NF <nº NF entrada>`.
  Ex.: `9999 - PROCESSO COT0000 DI 00/0000000-0 NF 000000`.
- **`[R2]` O número da conta do processo é MANUAL — não auto-gerar.** A Larissa cria a conta **antes**, dentro do plano de contas, como faz para cliente/fornecedor. Não há sequência de numeração que o sistema possa atribuir, e o número **não existe** no momento da extração. O sistema **monta a descrição** (padrão acima) e a oferece para cópia; o **número** é campo de input do operador. (Auto-numeração foi proposta e descartada pela key user.)
- **`[R2]`/`[R3]` Formatação do nº da NF:** a descrição da conta é **copiada** para criar a conta, então o número da NF deve ser **inteiro limpo** — sem separador de milhar **e sem zeros à esquerda**. Ex.: `... NF 2411` (não `NF 2.411` nem `NF 000.002.411`). Evidência: na Relação real a coluna **D (Nº NF)** guarda `458` (inteiro). Dois pontos de aplicação: **(a)** na Relação (Saída D), preencher a coluna D com o inteiro — a descrição da conta (coluna G) é **fórmula `CONCATENATE`**, o Excel monta sozinho; **(b)** no **histórico/complemento do Domínio** (string montada pela ferramenta), aplicar o mesmo strip.
- **NF de importação** deve ser alocada em conta de **IMPORTAÇÕES EM ANDAMENTO** (permite refazer o processo sem alterar fechamentos anteriores).
- Gerar **conta de fornecedor estrangeiro** (Fiscal → Utilitários → Alterar Cadastro de Clientes e Fornecedores → Fornecedores → Contas Contábeis) e reclassificar de "Fornecedores" para "Fornecedores estrangeiros" no Contábil.
- **`[R2]` Conta contábil do fornecedor também é MANUAL e varia por empresa.** A maioria já existe no plano de contas, mas **não é a mesma entre empresas** — logo é campo de input do operador, com de-para por empresa (Seção 5), nunca fixa/hardcoded.
- **`[R3]` Regra confirmada — "em branco + aviso" (sem default chutado):** o sistema **não** preenche contas com número fixo. O de-para por empresa **pré-preenche** as contas já conhecidas; onde não houver correspondência, o campo fica **em branco** e é emitido o aviso *"conta obrigatória não preenchida"*, **bloqueando a geração daquela partida** até o operador preencher. Remover os defaults hardcoded do código (`1177` fornecedor, `1648` conta do processo). `1633` (Importações em Andamento) pode permanecer como default **de-para por empresa** por ser estável. Desligar qualquer auto-numeração por "próximo código/sequência" (comportamento antigo visto na aba *Auditoria IMPORT* — a Larissa pediu para parar).

### 1.5 Algoritmo de contabilização `[P2 · Passos 5–9]`

Estrutura D/C fixa por passo (regra de negócio; contas específicas variam por cliente — ver 5. Middleware). Contas de exemplo observadas entre colchetes.

**Passo 5 — NF de entrada (dois lançamentos):**
1. `D` IMPORTAÇÕES EM ANDAMENTO [1633] · `C` Conta do Processo [1648]
   Histórico: `TRANSFERÊNCIA DE VALORES IMPORTAÇÃO EM ANDAMENTO CFM #C`
2. `D` Conta do Processo [1648] · `C` Fornecedor Estrangeiro [1177] · **Valor = campo 3 (RESULTADO EM R$)**
   Histórico: `VALOR DEVIDO FORNECEDOR #C REF. #D USD # E TAXA INVOICE #`

**Passo 6 — Despesas do processo:**
- **6.1 NF de serviço** (honorários aduaneiros / despacho / intermediação): vêm do Fiscal como `D 362 (serviço terceiros) · C Fornecedor`. Alterar o **débito 362 → conta da importação (99999)**; crédito mantém (inclusive retenções). Histórico: manter o do Fiscal + nome do processo.
- **6.2 Despesas do numerário sem NF própria** (tarifa bancária, frete, moto boy, AFRMM, frete marítimo, armazenagem…): lançamento único **vários débitos → vários créditos**. `D` Conta do Processo (uma linha por despesa, tipo no histórico) · `C` Adiantamento ao despachante.
  - **`[R2]` Captura do adiantamento:** somar todas as entradas do Fechamento cujo rótulo contenha **"adiantamento"** — aparece como *adiantamento de numerário*, *adiantamento de despachante* ou *adiantamento de pagamento*. Casar por "adiantamento" já é suficiente para totalizar. Posição varia por layout de despachante (topo ou última linha). É lançamento a **crédito** (o débito é a conta do processo).
- **6.2.2** Se a despesa já tem NF alocada → baixa `D` Fornecedor.
- **6.2.4** A diferença entre despesas do numerário e o valor efetivo do processo vai para a conta do despachante (credora ou devedora).
- **6.2.5** Saldo remanescente na conta do processo → transferência para **Estoque**: se **positivo** `D` Estoque `C` Processo; se **negativo** `D` Processo `C` Estoque. Histórico: `fechamento de processo #C` (ou `#D`).
- **`[R4]` Validação de despesas (conferência pós-parse, derivada de 6.2) — implementado.** Encerra o "despesa some em silêncio": uma despesa que o parser não capturar deixa de desaparecer sem rastro. Roda na **consolidação**, só quando há fechamento (não polui processos DUIMP+NF).
  - **Conjunto canônico de rubricas RECORRENTES**, com flag `obrigatória`:
    - **Obrigatórias:** II, IPI, PIS-Import., COFINS-Import., Siscomex, ICMS import., frete internacional/marítimo, AFRMM, despacho/honorários.
    - **Recorrentes não-obrigatórias:** armazenagem, levante, pesagem, emissão de LI/licença, tarifa bancária, IOF.
  - **Reconciliação:** Σ despesas == **TOTAL** do fechamento; e **numerário − TOTAL == SALDO**.
  - **Avisos gerados** (não bloqueiam; para o operador conferir): `despesa_divergente` (Σ ≠ TOTAL), `numerario_divergente` (numerário − total ≠ saldo), `despesa_obrigatoria_ausente` (alerta) e `despesa_recorrente_ausente` (informativo).

**Passo 7 — Pagamento do fornecedor estrangeiro (via câmbio):** — **`[R3]` NÃO implementado hoje** (o motor só gera 5.1/5.2/6.2/8). Depende do **campo de banco manual** (Seção 5) e de regra de banco por empresa → agendado para a **Fatia 2** (Seção 13).
- (a) Pagamento antecipado: `D` Fornecedor estrangeiro · `C` Adiantamento fornecedor.
- (b) Pago no andamento: `D` Fornecedor estrangeiro · `C` Banco c/c.
- **7.2 Fornecedores de serviço (despachante/fretes):** baixa junto ao 6.2.2 → `D` Fornecedor despachante · `C` Adiantamento Trading · valor = líquido da NF.

**Passo 8 — Variação cambial (campo 8 da planilha):**
- Positiva (receita): `D` Fornecedor estrangeiro · `C` `973 - VARIAÇÃO CAMBIAL ATIVA`.
- Negativa (despesa): `D` `370 - VARIAÇÕES CAMBIAIS PASSIVAS` · `C` Fornecedor estrangeiro.

**Passo 9 — Finalização (acerto empresa × despachante):**
- `D` Banco `C` Despachante (despachante devolve), **ou** `D` Despachante `C` Banco (empresa ressarce). Histórico: `Fechamento Processo 99999`.

**Plano de contas / históricos observados** (referência, confirmar por cliente):
- Contas: IMPORTAÇÕES EM ANDAMENTO, Conta do Processo, Fornecedor Estrangeiro, Adiantamento a fornecedores, Despachante, Estoque, `362`, `973`, `370`.
- Códigos de histórico do Domínio vistos nos exemplos: `41` (despesa referente processo), `45`/`46` (transferência / valor devido), além de `25/56/59` da macro original.

### 1.6 LACUNAS do POP (não cobertas — exigem confirmação)

- **IBS/CBS (Reforma Tributária):** o POP descreve o regime **antigo** (PIS/COFINS + ICMS). Os documentos de 2026 já trazem **CBS/IBS** (ver Seção 8). **Regra de contabilização de CBS/IBS = a definir com a Larissa.** `[R2]` Combinado enviar as dúvidas **por escrito** à Larissa (ela responde em texto); a regra de CBS/IBS entra nesse lote de perguntas.
- **Contrato de câmbio real:** temos só o modelo do POP; sem amostra real, os campos 4–8 e o Passo 8 ficam parametrizados, não validados.
- **Layouts de fechamento além de TERRA/WIN/SYNDEX/ALL TIME/CONNECTA:** já suportados esses cinco; cada despachante novo continua sendo um parser novo.

---

## 2. Visão geral do fluxo

```
[Upload dos documentos do processo]  →  [Extração automática]  →  [Conferência + Middleware]  →  [Gerar arquivos]
        (1 processo por rodada)          (campos dos documentos)    (operador completa contas,        (downloads)
                                                                     histórico, entidade, câmbio)
```

Cada rodada de upload = **um processo** (regra 1.1). O operador sobe o pacote (NF + DI/DUIMP + Invoice + Fechamento + anexos + Contrato de Câmbio quando houver), o sistema extrai, o operador confere/completa, e gera as saídas da Seção 6.

---

## 3. Escopo do mockup

### Dentro do escopo
- Upload por arrastar/soltar dos documentos de **um processo**.
- Extração dos campos dos documentos suportados (Seção 4), guiada pela Seção 1.
- Suporte a **DI** e **DUIMP** (dois modelos) e à **NF-e de importação**.
- Suporte à **Comercial Invoice** (temos amostra real — CML Biotech).
- Suporte aos fechamentos **TERRA, WIN, SYNDEX, ALL TIME e CONNECTA** (cinco layouts com amostras reais).
- **`[R4]` Validação de despesas recorrentes/obrigatórias + reconciliação do fechamento** (Σ despesas == TOTAL; numerário − total == saldo), com avisos ao operador.
- Reconhecimento dos **anexos do fechamento**: NFS-e de serviço, CT-e/DACTE, boleto, GRU, DARE-SC, termo AFRMM, LI/anuência, BL/MTD, comprovantes de pagamento.
- **Extração de campos IBS/CBS** quando presentes nos documentos (ver Seção 8).
- Camada **Middleware** (Seção 5).
- **`[R3]` Reconhecimento de anexo/referência.** Documentos que não são um dos tipos suportados (Bill of Lading, comprovantes Pix/recibo, boleto, GRU, DARE, CT-e/DACTE, NFS-e fora de fechamento) e **PDFs só-imagem** (sem camada de texto) são classificados como **ANEXO/REFERÊNCIA** — reconhecidos e **ignorados com calma**, sem cair no parser errado nem virar "tipo não reconhecido". A leitura de dados desses anexos (OCR, CT-e/NFS-e como fonte de tributos/despesas) fica para a **Fatia 2**.
- **`[R2]`/`[R3]` Conferência navegável de divergências — ENTRA NA FATIA 1.** Quando a extração encontra divergência entre documentos (nome, valor presente num doc e ausente/zerado no outro), o operador:
  - clica no aviso e abre uma visão **diff lado a lado** — cada documento envolvido com o **campo destacado** — para localizar onde está a diferença sem sair da tela;
  - **seleciona** qual dos valores conflitantes usar (check), e o valor escolhido vai para o campo da saída.
  Isso substitui a antiga aba de "avisos" separada: a seleção do operador é a decisão. **Não** há correção/decisão automática — quem resolve é a Larissa.
- Geração das saídas (Seção 6), com os lançamentos seguindo o algoritmo 1.5.

### Fora do escopo (nesta etapa)
- **`[R2]` Auditoria/conciliação automática que resolve divergências sozinha.** A ferramenta **destaca e navega** as divergências e oferece a seleção (agora no escopo — ver acima), mas **não** decide qual valor é o correto nem "corrige" o documento; a decisão é sempre do operador.
- **Contabilização definitiva de CBS/IBS** enquanto a regra não for confirmada (extraímos e reservamos os campos; o lançamento fica parametrizável).
- Integração automática com o Domínio (importação segue **manual**, via arquivo).
- **Contrato de câmbio real** (parametrizado até recebermos amostra).
- Persistência/banco, autenticação, multiusuário.
- OCR de escaneados de baixa qualidade (alguns anexos são imagens ruins — ver Seção 10).

---

## 4. Documentos suportados e campos extraídos

Guiado pela taxonomia 1.1. Resumo por tipo (campos detalhados no anexo de implementação):

- **DUIMP** (ex. 26BR0000258971-1): nº/versão, situação, importador (CNPJ/nome), tipo de importação (direta / conta e ordem), ref. despachante e cliente, invoice (nº/data/valor US$), moeda/taxa, VMCV/VMLD (US$/R$), tributos (II/IPI/PIS/COFINS/Siscomex), **CBS/IBS por item (`cClassTrib`)**, porto/navio/BL/chegada/recinto, pesos, exportador e fabricante, itens (NCM, qtd, valor).
- **DI** (ex. 26/0418027-7): nº/data registro, importador/adquirente, representante, modalidade/nº adições, frete/VMLE/VMLD, tributos, carga (manifesto/recinto/pesos), ref. interna/BL/navio/fatura, cotação e valores R$/US$, por adição (exportador, fabricante, NCM, INCOTERM, VCMV, alíquotas, LI/anuência).
- **NF-e de importação (DANFE de entrada)**: nº/série/chave, emitente/destinatário, natureza, valor produtos/total, ICMS/IPI, **CBS/IBS/IBS-UF/IBS-MUN** e demais campos da reforma quando houver, itens (NCM/CFOP/qtd/valor), obs. (DUIMP/DI, PIS/COFINS entrada, Siscomex).
- **Comercial Invoice** (ex. CML Biotech): exportador, consignee, nº invoice/data, INCOTERM, moeda, itens (NCM, batch, qtd, unit price, total), FOB total US$, condições de pagamento.
- **Fechamentos** (TERRA / WIN / SYNDEX / ALL TIME / CONNECTA): despesas por tipo, adiantamentos/numerário, tributos recolhidos, saldo credor/devedor, dados bancários. Layouts distintos → um parser por despachante.
  - **`[R4]` Layout CONNECTA ("FATURAMENTO")** — dossiê único (faturamento na pág. 1 + Extrato DUIMP + NFS-e/anexos). Ancorado em **rótulos** (o texto vem **linear** do pdfplumber, sem coordenadas):
    - **Bloco câmbio/aduaneiro:** `TAXA CAMBIAL USD <taxa>`; linhas `FOB`/`FRETE`/`SEGURO`/`TAXAS DE CE`/`VALOR ADUANEIRO` com **colunas USD e BRL** — usa-se a coluna **BRL**. A coluna à **direita do VALOR ADUANEIRO** = **numerário/adiantamento**.
    - **Tabela DESPESAS:** entre o cabeçalho `DESPESAS COBRADOR DATA DE PAGAMENTO…` e `TOTAL R$` — cada linha = descrição + cobrador (colados, só **data** e **valor BRL** são âncoras fortes), depois `TOTAL` e `SALDO`, e por fim os **dados bancários**.
  - **`[R2]` Nome do despachante às vezes vem como imagem** (caso SYNDEX) e sem tag para localizar → difícil extrair direto. **Fontes alternativas em texto:** a **fatura de serviço / "comissão aduaneira de importação"** e o cadastro **"despachante aduaneiro autorizado"** na DI/DUIMP. Prever esse fallback (ou OCR) antes de depender do campo em imagem.
  - **`[R2]` Frete por boleto:** documento de **referência apenas** — a Larissa não extrai dados dele; entra no pacote só para eventual identificação. Não é fonte de extração.
- **Anexos**: NFS-e (despachante/porto/frete), CT-e/DACTE (frete rodoviário, ICMS), GRU (Inmetro), DARE-SC (ICMS importação/diferido), termo/`débito` AFRMM, BL/MTD, comprovantes Pix/TED/boleto.
- **Contrato de câmbio** (modelo do POP): tipo/nº contrato, data, moeda, valor moeda estrangeira e nacional, taxa cambial, VET, data de liquidação, pagador/recebedor exterior, instituição.

---

## 5. Middleware (campos que não vêm dos documentos)

O extrator preenche o que é do documento; o operador confere e completa o que é **regra de negócio / plano de contas**:

| Campo | Origem | Observação |
|---|---|---|
| Entidade contábil (trading × adquirente) | Operador | Define CNPJ/contas em conta e ordem |
| Conta do Processo (nº) | Operador `[R2]` | **Descrição** montada automaticamente (1.4); **número é manual** — criado antes no plano de contas, não auto-gerado |
| Conta do Fornecedor estrangeiro (nº) `[R2]` | Operador / de-para por empresa | Manual; varia entre empresas |
| Conta / código do banco `[R2]` | Operador | Documento traz só agência+conta; a **conta contábil / código do banco** para o lançamento de pagamento é inserida pelo operador |
| Contas débito/crédito por partida | Operador / de-para | Específicas por cliente |
| Códigos de histórico | Operador / de-para | Tabela do Domínio (ex. 41/45/46) |
| Complemento do histórico | Gerado (templates 1.5) + editável | Ex.: `VALOR DEVIDO FORNECEDOR … USD … TAXA INVOICE …` |
| Data do lançamento / lote / matriz-filial / CC | Operador | Conforme regra Domínio |
| Dados do contrato de câmbio (campos 4–8) | Operador (até termos parser) | Alimenta variação cambial |
| **Tratamento CBS/IBS** | Operador (parametrizado) | Até a regra ser confirmada (1.6 / Seção 8) |

**De-para (recomendado):** `fornecedor estrangeiro → conta`, `tipo de despesa → conta/histórico`, `despachante → contas`. Pré-preenche o middleware e "aprende" a cada processo. No mockup pode ser tabela simples e editável; arquitetura já prevê evoluí-la.

---

## 6. Layout dos arquivos de saída

### 6.1 Saída A — Extração estruturada / "dados extraídos" (`.csv`) — **descartável, mensal `[R2]`**
Uma linha por processo, incluindo colunas 1–8 da planilha (Seção 1.3) e os blocos de tributos federais **e** os campos da reforma. **`[R2]` Correção de entendimento:** esta saída é **descartável** — serve apenas para **importar no Domínio** os processos **daquele fechamento** (os 2/10/N processos do mês). A Larissa **não guarda** esta aba. O artefato que ela mantém com histórico é a **Relação das Importações** (Seção 6.4). Campos:
`Tipo Importação; Data NF; DI/DUIMP; Nº NF; Valor NF; Processo; Despachante; Fornecedor Estrangeiro; Fabricante; País Origem; País Aquisição; Invoice (nº); Invoice USD; TX DI; Resultado R$; USD PG Câmbio; TX Câmbio; VLR PG R$; VLR PG × TX DI; Variação; FOB R$; Frete R$; Valor Aduaneiro R$; II; IPI; PIS; COFINS; CBS; IBS-UF; IBS-MUN; Siscomex; AFRMM; ICMS; Armazenagem; Total Tributos; Peso Líquido; Volumes; Navio; BL; Chave NF-e`

> Opcional (auditoria/rastreio): versão longa `Processo; Documento; Campo; Valor; Fonte`.

### 6.2 Saída B — Lançamentos Domínio (partidas)
Layout **idêntico ao da macro** `Sub Gerar()` (`lanctos.txt`), separado por `;`, **sem cabeçalho** no arquivo final, uma linha por partida gerada pelo algoritmo 1.5:
```
Data;Cód.Conta Débito;Cód.Conta Crédito;Valor;Cód.Histórico;Complemento Histórico;Inicia Lote;Matriz/Filial;Centro Custo Débito;Centro Custo Crédito
```
Contas, histórico e lote vêm do middleware/de-para (Seção 5). As partidas de CBS/IBS entram condicionadas à regra confirmada (Seção 8).

### 6.3 Saída C — Cadastro de fornecedor / controle interno (`.csv`, opcional)
`Código Exportador; Nome Exportador Estrangeiro; Endereço; País Aquisição; Nome Fabricante/Produtor; País Origem; Relação Exportador×Fabricante; Vinculação Comprador×Vendedor`.

### 6.4 Saída D — Relação das Importações (persistente, **por empresa**) `[R2]`

**Este é o artefato de controle que a Larissa mantém** — corrige o entendimento anterior de "planilha consolidada com filtro por empresa".

- **Um arquivo por empresa** (uma contabilidade / um plano de contas). **Não** há visão consolidada cruzando empresas; a Larissa **não faz comparativo entre empresas**.
- **Acumula histórico** de vários anos no mesmo arquivo (ex.: 2024→2027 juntos). A ferramenta deve **acrescentar** as linhas dos novos processos ao arquivo existente e **preservar** o que já está lá — **não regerar do zero**.
- Cada linha já traz a **informação do lançamento** e os campos 1–8 (Seção 1.3). Serve para conferir se o processo foi **pago por completo**, se sobrou **saldo**, se há **fornecedor em aberto**, e evita recalcular **variação cambial** na mão.
- **`[R3]` Estrutura real da planilha (inspecionada):** o arquivo `CONTROLE IMPORTAÇÕES / FORNECEDORES ESTRANGEIROS.xlsx` tem 4 abas — **"Relação importações"** (a que importa: 1 linha por processo, blocos por ano), **"Dados Extraidos"** (Processo/Documento/Campo/Valor/Fonte — a descartável), **"Auditoria IMPORT"** (log) e "Planilha1" (vazia). A aba "Relação importações" tem colunas **A–X**:
  - **Entrada (preencher):** A TIPO IMPORTAÇÃO · B DATA NOTA ENTRADA · C DI/DUIMP · D Nº NF (inteiro limpo) · E Valor NF · F Conta contábil DOMÍNIO · L despachante · M PROCESSO(nº) · N CONTA CONTÁBIL FORNECEDOR · O fornecedor estrangeiro · P (1) INVOICE USD · Q (2) TX DI · S Contrato Câmbio nº · T (4) VLR USD PG CÂMBIO · U (5) TX CÂMBIO.
  - **Fórmula (NÃO tocar — copiar para baixo):** G DESCRIÇÃO (=CONCATENATE) · H · R (3)=P×Q · V (6)=T×U · W (7)=T×Q · **X (8)=V−W**.
- **`[R3]` Mecanismo no mockup (sem backend — ver Seção 11):** o operador **sobe a Relação atual** da empresa (`.xlsx`); a ferramenta **insere uma linha nova** na aba "Relação importações" sob o bloco do ano, preenchendo **só as colunas de entrada** e **preservando as fórmulas** e as demais abas; devolve o arquivo para download. **`openpyxl`** é dependência. **Chave de identidade = o próprio arquivo** que o operador sobe (é por empresa).

---

## 7. Corpus de teste (documentos reais disponíveis)

| Processo / Ref | Importador · Modalidade | Despachante (layout) | Regime | Documentos presentes | Kit completo? |
|---|---|---|---|---|---|
| **SY1453/26 · 2025ECX067** (DUIMP 26BR0000258971-1) | ENCATEX · Direta | **SYNDEX** | IBS/CBS **+** PIS/COFINS | NF-e 2.411, DUIMP, fechamento + NFS-e porto/despachante, DARE-SC, AFRMM, CT-e Nextrans + boleto, recibos, Pix/TED | Sem **Invoice** e sem **contrato de câmbio** |
| **26/0058 · CML-EXP-PI-51/25-26** (DI 26/0418027-7) | ALL LAB · Direta (imp=adq) | **ALL TIME** + Rhenus | PIS/COFINS (reduzido 0%) | DI (2 adições), **Invoice CML Biotech**, Packing List, BL/MTD, LI Anvisa, fechamento + NFS-e, DARE-SC, AFRMM, armazenagem JBS, Best Frete, comprovantes | Sem **contrato de câmbio** |
| **982# · HKYCMOBR982** | ZINLOG p/ CMO · Conta e ordem | **TERRA** | — | Fechamento TERRA, GRU Inmetro | Parcial (amostra de layout) |
| **0020-26 · TMP260120ID-01** (Duimp 26BR0000775592-0) | TIMPTRADE · Direta | **CONNECTA** | PIS/COFINS | Dossiê único de 20 p. (faturamento pág.1 + Extrato DUIMP + NFS-e/anexos) | Dossiê combinado; sem NF/DUIMP standalone |
| **1159# / 870#** (rodadas anteriores) | ZINLOG-CMO / INFINITY | TERRA / WIN | — | DUIMP+NF / DI+TERRA / WIN | Parcial |

**Cobertura obtida:** DI + DUIMP; **cinco layouts de fechamento** (TERRA/WIN/SYNDEX/ALL TIME/CONNECTA); duas modalidades (direta / conta e ordem); Invoice real; ampla amostra de anexos.
**Gap remanescente:** nenhum processo com **contrato de câmbio real**; documentos adicionais a receber (fora deste chat).

---

## 8. Reforma Tributária (IBS/CBS) — ano de transição

**Fato:** em 2026 os documentos coexistem em dois regimes. A DUIMP/NF-e da ENCATEX trazem **CBS e IBS** (NF-e: `CBS`, `IBS-UF`, `IBS-MUN`; item da DUIMP com `cClassTrib 000001 - tributadas integralmente pelo IBS e CBS`) **junto** com PIS/COFINS. A DI (modelo antigo) traz apenas PIS/COFINS.

**Decisão:** **considerar IBS/CBS no escopo** — o extrator **captura e reserva** os campos da reforma sempre que presentes, e a Saída A já os inclui (Seção 6.1).

**Pendência (LACUNA 1.6):** o POP descreve o regime antigo; a **regra de contabilização do CBS/IBS** (contas, históricos, partidas) **precisa ser confirmada com a Larissa**. Até lá, os lançamentos de CBS/IBS na Saída B ficam **parametrizáveis** no middleware (não hardcoded), para não travar o piloto nem antecipar regra incorreta.

---

## 9. Premissas e decisões confirmadas
- **POP = base de conhecimento canônica** (Seção 1), versionada a cada novo POP.
- Importação no Domínio = **layout de partidas** (igual à macro atual).
- Saída A = prova de extração; Saída B = destino real (partidas); C = opcional.
- **DI e DUIMP** suportados; NF de importação suportada; **Invoice** suportada.
- Fechamentos suportados: **TERRA, WIN, SYNDEX, ALL TIME, CONNECTA**.
- `[R4]` **Validação de despesas do fechamento implementada:** rubricas recorrentes/obrigatórias + reconciliação (Σ despesas == TOTAL; numerário − total == saldo), emitindo avisos ao operador.
- **Um upload = um processo.**
- Contas/histórico/entidade contábil: via **middleware/de-para** (não extraíveis).
- **IBS/CBS extraídos e reservados**; contabilização a confirmar.
- Importação no Domínio permanece **manual**.
- `[R2]` **Nº das contas (processo e fornecedor) e câmbio (USD/taxa) são manuais** — nada auto-gerado; nº da NF na descrição da conta **sem separador de milhar**.
- `[R2]` **Conferência navegável de divergências (diff + seleção) está no escopo**; auditoria automática que decide sozinha, não.
- `[R2]` **Relação das Importações = artefato persistente por empresa** (append, com histórico); a extração "dados extraídos" é descartável/mensal.
- `[R2]` Mockup vai para **VPS com URL** para a Larissa testar e dar feedback.
- `SecurityData_1782083140.xlsx`: anexado por engano — ignorado.

---

## 10. Riscos e observações
- **Maior risco de extração:** layouts de fechamento (4 distintos) e a qualidade dos escaneados (alguns anexos vêm como imagem de baixa resolução — ex. prestações da ALL TIME e comprovantes bancários; podem exigir OCR ou conferência manual).
- **Contrato de câmbio ausente** nos pacotes reais → variação cambial validada só via modelo.
- **Regra CBS/IBS não confirmada** → único ponto que pode alterar a Saída B.
- Documentos adicionais da Larissa a receber por outro canal → podem trazer novos despachantes/layouts.
- **`[R2]` Nome do despachante em imagem** (SYNDEX, sem tag) → depende de fonte alternativa em texto (fatura de comissão aduaneira / cadastro da DI) ou OCR.
- **`[R2]` Bug ativo — erro de extração em alguns PDFs.** Durante a demo, alguns PDFs (do mesmo tipo dos que funcionam) passaram a **falhar na extração** / não importar campos que existem no documento. **Bloqueia o teste da Larissa** — corrigir antes do deploy na VPS (ver Seção 12).

---

## 11. Stack (mockup)
Aplicação web leve: upload/drag-and-drop, extração de texto dos PDFs no cliente, parsers por layout (guiados pela Seção 1), formulário de conferência/middleware com de-para, e geração dos `.csv`/`.txt` para download. Sem backend persistente nesta etapa.

**`[R2]` Deploy:** o mockup é publicado em **VPS com URL própria** para a Larissa acessar pelo navegador e rodar extração/exportação sozinha. Continua **sem banco/persistência**: o histórico da **Relação das Importações** (Seção 6.4) é mantido pelo padrão **upload da Relação atual → append → download** — a persistência fica no arquivo da própria empresa, não no servidor.

---

## 12. Próximos passos
1. **`[R2]` Corrigir o bug de extração de PDFs** (Seção 10) — pré-requisito para o teste da Larissa.
2. **`[R2]` Aplicar os ajustes `[R2]`** (contas manuais + formatação do nº da NF; câmbio/banco manuais; captura do adiantamento; conferência navegável com diff + seleção; separação Relação por empresa × dados extraídos).
3. **`[R2]` Subir o mockup na VPS** e disponibilizar a **URL** para a Larissa testar extração/exportação e dar feedback.
4. **`[R2]` Enviar as perguntas por escrito** à Larissa (inclui a **regra de contabilização IBS/CBS**; ela responde em texto).
5. Receber os **documentos adicionais** e os **próximos POPs** (anexar à Seção 1).
6. Obter um **contrato de câmbio real** (valida campos 4–8 e Passo 8).
7. Gerar A + B de exemplo a partir de um processo real completo (ENCATEX é o candidato mais rico).
8. Próxima reunião de validação: **sexta à tarde (~16h)**.

---

## 13. Fatias de entrega `[R3]`

**Fatia 1 — destrava o teste da Larissa na VPS:**
1. Bug de extração: **pinar deps** (pdfplumber/pdfminer.six), **endurecer o detector** + categoria **ANEXO/REFERÊNCIA** (incl. só-imagem), **construir o parser ALL TIME**.
2. Correções baratas: **nº da NF limpo** (sem milhar/zeros à esquerda), **sinal da variação** (6−7), **contas sem default** (em branco + aviso; de-para por empresa).
3. **Adiantamento:** somar todas as linhas com "adiantamento" como crédito do Passo 6.2 + expor na conferência.
4. **Conferência navegável** (diff clicável + seleção do valor → campo de saída → rastreável na Saída A).
5. **Relação (Saída D):** upload → append de 1 linha na aba "Relação importações" (preservando fórmulas/abas) → download.
6. **Empacotar para VPS** (ASGI de produção + proxy/HTTPS; limite de upload; deps pinadas).

**Fatia 2 — após feedback da Larissa:**
- **Passo 7** (pagamento do fornecedor via banco) + **campo de banco manual**.
- **OCR / fontes alternativas do despachante** (fatura de comissão aduaneira; cadastro da DI) e leitura de anexos-imagem (Pix/BL escaneados).
- **Parsers de anexo** que são fonte de dado (CT-e → ICMS/frete; NFS-e de serviço → Passo 6.1; DARE/GRU/AFRMM → tributos).
- **Regra de contabilização CBS/IBS** (após resposta escrita da Larissa).
