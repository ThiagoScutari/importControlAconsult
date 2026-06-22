# Spec — Extrator de Dados de Importação → Domínio
### Mockup de validação | Contabilidade Aconsult

**Versão:** 0.1 (rascunho para aprovação)
**Etapa:** Validação de fluxo, extração e formato de saída. **Não é** desenvolvimento de produção.
**Objetivo do mockup:** provar que conseguimos (1) extrair os dados dos documentos de importação e (2) entregar arquivos prontos para importação/controle, validando o fluxo com a key user antes de investir em desenvolvimento.

---

## 1. Visão geral do fluxo

```
[Upload dos PDFs do processo]  →  [Extração automática]  →  [Conferência + Middleware]  →  [Gerar arquivos]
        (1 processo por vez)        (campos do documento)     (operador completa o que             (downloads)
                                                                falta: contas, histórico, etc.)
```

Cada rodada de upload corresponde a **um processo de importação**. O operador sobe juntos os documentos daquele processo (DI **ou** DUIMP + NF de importação + Fechamento do despachante), o sistema extrai o que é legível, o operador confere e preenche os campos que não existem nos documentos, e gera os arquivos de saída.

---

## 2. Escopo do mockup

### Dentro do escopo
- Upload por arrastar/soltar (drag & drop) dos PDFs de **um processo**.
- Extração automática dos campos dos documentos suportados (seção 4).
- Suporte a **DI** e **DUIMP** (os dois modelos).
- Suporte a Nota Fiscal de Importação (DANFE de entrada).
- Suporte aos fechamentos **despadronizados TERRA** e **WIN TRADING** (os dois layouts enviados pela key user Larissa).
- Camada **Middleware**: formulário onde o operador confere os dados extraídos e insere os campos que não vêm dos documentos.
- Geração dos arquivos de saída (seção 6).

### Fora do escopo (nesta etapa)
- **Conciliação / validação de divergências** entre DI/DUIMP, NF e Fechamento → apenas extração crua.
- **Câmbio e variação cambial** (colunas S–X do controle).
- Outros layouts de fechamento além de TERRA e WIN.
- OCR de documentos escaneados (os exemplos têm camada de texto; ver seção 10).
- Integração automática com o Domínio (a importação segue **manual**, via arquivo gerado).
- Persistência/banco de dados, autenticação, multiusuário.

---

## 3. Entregáveis (arquivos de saída)

| # | Arquivo | Finalidade | Prioridade |
|---|---------|------------|------------|
| **A** | Extração estruturada (`.csv`) | Prova a extração; alimenta o controle interno de importações | **Principal** |
| **B** | Lançamentos Domínio (`.csv`/`.txt`) | Importação no Domínio — layout de partidas (igual à macro) | Exemplo proposto |
| **C** | Cadastro de fornecedor / controle interno (`.csv`) | Controle interno; reforça o valor na apresentação | Opcional (bônus) |

> Decisão (sua pergunta 1 e 2): o mockup entrega **A** como prova de extração e **B** como exemplo do destino real no Domínio (partidas). **C** entra se houver tempo, por agregar à apresentação.

---

## 4. Documentos suportados e campos extraídos

### 4.1 DUIMP (ex.: processo 1159 / `26BR0000380790-9`)
Número e versão da DUIMP; situação; CNPJ e nome do importador; tipo de importação (própria / por conta e ordem); referência interna (`1159#`); fatura/invoice (número, data, valor US$); cotação USD; FOB (R$/US$), frete (R$/US$), valor aduaneiro (R$/US$); tributos recolhidos (II, IPI, PIS, COFINS, Siscomex, total); data de registro; porto, navio, BL, chegada, armazém; país de procedência/aquisição; peso bruto/líquido e volumes; exportador estrangeiro e fabricante/produtor; itens (NCM, descrição, qtd, valor unitário/total).

### 4.2 DI (ex.: processo 870 / `25/2290426-3`)
Número e data de registro da DI; CNPJ/nome do importador e adquirente; representante legal; modalidade e nº de adições; frete, VMLE, VMLD; tributos (II, IPI, PIS, COFINS, Siscomex, total); carga (manifesto, recinto, peso bruto/líquido, volumes); referência interna (`870#`), BL, navio, chegada, armazém, fatura; cotação FOB, FOB R$/US$, frete R$, valor aduaneiro R$; por adição: exportador, fabricante, NCM, INCOTERM, VCMV, peso, itens e alíquotas (II/IPI/PIS/COFINS).

### 4.3 Nota Fiscal de Importação — DANFE de entrada (ex.: NF `000.000.769`)
Número/série e data de emissão; emitente (CNPJ/razão social); destinatário (CNPJ/razão social); natureza da operação e CFOP; base e valor de ICMS; valor total dos produtos; valor total do IPI; valor total da NF; chave de acesso; informações complementares (processo, exportador, PIS/COFINS de entrada, taxa Siscomex); itens (código, descrição, NCM, CFOP, qtd, valor).

### 4.4 Fechamento TERRA (despadronizado — ex.: processo 870)
Despachante (TERRA + CNPJ); cliente (CNPJ/razão social); código interno/processo, referência (`870#`), fatura; navio, origem, destino; **lançamentos de despesas** (descrição + vencimento + valor: tarifa bancária, moto boy, AFRMM, ICMS, comissão, frete marítimo, armazenagem, impostos DI, adiantamento); retenções (PIS, COFINS, CSLL, ISS, IRRF); totais e saldo.

### 4.5 Fechamento WIN TRADING (despadronizado — ex.: ENC-153/2024.1)
Trading (WIN + CNPJ); processo, modalidade, INCOTERM; adquirente e referência; exportador; declaração e data de registro; cotação USD; FOB, frete, seguro, valor aduaneiro; **despesas detalhadas** (frete e seguro internacionais; II/PIS/COFINS/ICMS; IRPJ/CSLL s/ crédito presumido; contrato de câmbio; honorários; despacho; AFRMM; Siscomex; armazenagem; tarifa bancária); total, retenções, saldo a pagar/receber.

> Cada layout de fechamento tem um **parser próprio**, selecionado pelo CNPJ/cabeçalho do despachante.

---

## 5. Camada Middleware (input do operador)

Campos que **não existem nos documentos** e são preenchidos/confirmados pelo operador antes de gerar os arquivos:

| Campo | Origem | Observação |
|-------|--------|------------|
| Tipo de importação | Operador (lista: Própria / Conta e ordem / Encomenda) | Pode vir sugerido da DUIMP quando disponível |
| Entidade contábil | Operador | Em conta e ordem: trading **ou** adquirente — define CNPJ/contas |
| Conta contábil débito | De-para → operador | Tabela fornecedor/despesa → conta; fallback manual |
| Conta contábil crédito | De-para → operador | idem |
| Código de histórico | De-para → operador | Ex.: 25, 56, 59 (tabela de históricos do Domínio) |
| Complemento do histórico | Gerado/editável | Ex.: `PROCESSO 1159 DUIMP 26BR... NF 000.000.769` |
| Data do lançamento | Operador | Default = data da NF/registro |
| Inicia lote / Matriz-Filial / Centro de custo | Operador | Conforme regra Domínio |

**De-para (recomendado):** tabela `fornecedor estrangeiro → conta fornecedor` e `tipo de despesa → conta/histórico`, que pré-preenche o middleware e reduz digitação a cada processo. No mockup pode ser uma tabela simples e editável; a arquitetura já prevê evoluí-la.

---

## 6. Layout dos arquivos de saída

### 6.1 Saída A — Extração estruturada (`.csv`)
Uma linha por processo (visão consolidada, espelhando o controle *Relação importações*). Colunas propostas (a confirmar na reunião):

`Tipo Importação; Data NF; DI/DUIMP; Nº NF; Valor NF; Processo; Despachante; Fornecedor Estrangeiro; Fabricante; País Origem; País Aquisição; Invoice (nº); Invoice USD; Cotação/TX; FOB R$; Frete R$; Valor Aduaneiro R$; II; IPI; PIS; COFINS; Siscomex; AFRMM; ICMS; Armazenagem; Total Tributos; Peso Líquido; Volumes; Navio; BL; Chegada; Chave NF-e`

> Opcional: gerar também uma versão **rastreável** (formato longo) `Processo; Documento; Campo; Valor; Fonte`, útil para auditoria da extração.

### 6.2 Saída B — Lançamentos Domínio (partidas)
Layout **idêntico ao da macro** `Sub Gerar()` (arquivo `lanctos.txt`), separado por `;`, **sem cabeçalho** no arquivo final:

```
Data;Cód.Conta Débito;Cód.Conta Crédito;Valor;Cód.Histórico;Complemento Histórico;Inicia Lote;Matriz/Filial;Centro Custo Débito;Centro Custo Crédito
```

Exemplo de linha (modelo da própria planilha):
```
45822;12374;805;286876,72;25;REF. ACERTO PAGAMENTOS FORNECEDOR;;;;
```
As contas (débito/crédito), histórico e lote vêm do **middleware/de-para** (seção 5).

### 6.3 Saída C — Cadastro de fornecedor / controle interno (`.csv`, opcional)
`Código Exportador; Nome Exportador Estrangeiro; Endereço; País Aquisição; Nome Fabricante/Produtor; País Origem; Relação Exportador×Fabricante; Vinculação Comprador×Vendedor` (campos disponíveis na DUIMP/DI).

---

## 7. Premissas e decisões confirmadas
- Importação no Domínio = **layout de partidas** (lançamentos contábeis), igual à macro atual.
- Saída A é a prova de extração; Saída B é o exemplo do destino real.
- **DI e DUIMP** suportados; NF de importação suportada.
- Fechamentos: apenas **TERRA** e **WIN TRADING** por enquanto.
- Conciliação de divergências e câmbio: **fora** desta etapa.
- Contas/histórico/entidade contábil: preenchidos via **middleware** (não extraíveis).
- Importação no Domínio permanece **manual** (anexar o arquivo gerado).
- `SecurityData_1782083140.xlsx`: anexado por engano, será removido (ignorado).

---

## 8. Stack
- **Mockup (validação):** aplicação web leve (front-end), extração de texto dos PDFs no próprio navegador, parsers por layout, formulário de conferência/middleware e geração dos `.csv`/`.txt` para download. Sem back-end — fácil de compartilhar e validar.
- **Produção (pós-aprovação):** a definir; provavelmente API (FastAPI) com parsers robustos, de-para em banco e tratamento de OCR. **O mockup é descartável** e não dita a arquitetura final.

---

## 9. Critérios de aceite (validação)
1. Operador sobe os PDFs de um processo (DUIMP **ou** DI + NF + Fechamento) e o sistema extrai os campos da seção 4 corretamente para os exemplos 870 e 1159.
2. O operador completa o middleware e gera a **Saída A** (extração) coerente com os documentos.
3. O sistema gera um exemplo da **Saída B** no layout de partidas do Domínio.
4. Fluxo validado pela key user → segue para desenvolvimento.

---

## 10. Riscos / pontos de atenção
- **Fechamentos despadronizados** são o maior risco de extração: cada despachante muda o layout. Mitigação: um parser por layout, começando por TERRA e WIN.
- Os PDFs de exemplo têm **camada de texto** (extração direta funciona). Fechamentos escaneados exigiriam OCR — fora desta etapa, mas previsto para produção.
- **Conta e ordem**: a entidade contábil correta depende do operador (trading × adquirente); o mockup não decide isso sozinho.

---

## 11. Itens a confirmar na reunião
- Lista final de campos da Saída A.
- Tabela de históricos e plano de contas (de-para) por cliente.
- Regra de entidade contábil em conta e ordem.
- Se a Saída C (cadastro de fornecedor) entra na apresentação.

---

## 12. Próximos passos
1. Aprovação deste spec.
2. Construir o mockup funcional (upload → extração → middleware → geração).
3. Gerar `.csv` de exemplo a partir dos processos 870 e 1159 anexados.
4. Apresentação/validação com a key user.
