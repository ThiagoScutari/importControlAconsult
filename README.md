# Extrator de Importação → Domínio (mockup)

> Um protótipo que **lê os PDFs de um processo de importação**, extrai os dados
> automaticamente, deixa o operador **conferir e completar** o que falta, e
> **gera os arquivos** prontos para o controle interno e para o sistema Domínio.

Este é um **mockup de validação de fluxo** para a contabilidade **Aconsult**.
Ele serve para mostrar à key user que a ideia funciona — **não é o sistema de
produção**. Não tem banco de dados, login, nem nada que precise ser instalado em
servidor: roda no seu computador e abre no navegador.

---

## 1. Para quem é isto e o que ele faz

Hoje, a cada importação, alguém precisa **abrir vários PDFs** (a declaração de
importação, a nota fiscal, o fechamento do despachante) e **digitar os dados à
mão** numa planilha de controle e no Domínio. É lento e dá erro.

Este mockup automatiza a parte chata:

1. Você **arrasta os PDFs** daquele processo para a tela.
2. O sistema **lê e extrai** os campos (número da DI/DUIMP, valores, tributos,
   fornecedor, navio, etc.).
3. Você **confere na tela** e preenche os poucos campos que **não existem nos
   documentos** (as contas contábeis, o histórico — a chamada camada *Middleware*).
4. Você clica em **Gerar arquivos** e baixa tudo prontinho.

---

## 2. O problema que ele resolve (e o contexto)

A importação envolve documentos de origens diferentes que **não conversam entre si**:

- **DUIMP** ou **DI** — a declaração de importação (dados oficiais, tributos).
- **Nota Fiscal de Importação** (DANFE de entrada) — número, valor, ICMS, chave.
- **Fechamento do despachante** — a "conta" das despesas (frete, AFRMM, armazenagem…).
  Cada despachante usa um layout próprio; aqui suportamos cinco: **TERRA**,
  **WIN TRADING**, **SYNDEX**, **ALL TIME** e **CONNECTA**.

O fluxo completo está ilustrado na imagem **`docs/imagem.png`**:

```
[Upload dos PDFs] → [Extração automática] → [Conferência + Middleware] → [Gerar arquivos]
   (1 processo)        (campos do documento)    (operador completa contas,    (downloads)
                                                  histórico, etc.)
```

O resultado são três arquivos (explicados na seção 5).

> **Importante:** o foco desta etapa é a **extração** dos dados. Quando há
> **divergência** entre documentos, o sistema a **sinaliza** e deixa o operador
> **navegar e escolher** o valor (conferência navegável); os campos de **câmbio**
> também são conferidos, e a variação cambial é calculada a partir deles.

---

## 3. Como instalar e rodar (passo a passo)

Pré-requisito: **Python 3.11 ou superior** instalado.

```bash
# 1. (opcional, recomendado) crie um ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. instale as dependências
pip install -r requirements.txt

# 3. rode o servidor
uvicorn backend.main:app --reload

# 4. abra no navegador
#    http://localhost:8000
```

Para rodar os **testes automatizados** (que conferem a extração contra os
exemplos reais em `assets/`):

```bash
pytest
```

---

## 4. Como usar o mockup (tutorial)

1. **Abra** `http://localhost:8000`.
2. **Arraste os PDFs** de **um único processo** para a área pontilhada
   (ou clique para escolher). Ex.: a `DUIMP 1159.pdf` + a
   `NOTA FISCAL DE IMPORTAÇÃO 1159.pdf`.
3. Clique em **Extrair dados**. O sistema identifica cada documento pelo
   conteúdo e mostra os campos extraídos.
4. **Confira os dados extraídos** (estão todos editáveis — corrija o que quiser).
   - Avisos em destaque mostram **campos não encontrados** e **divergências**
     entre documentos, sem travar o fluxo.
5. **Preencha o Middleware** — os campos que **não vêm dos PDFs**:
   tipo de importação, entidade contábil, **contas de débito/crédito**,
   **código de histórico**, complemento, data do lançamento.
   - A tabela **de-para** já pré-preenche contas/histórico a partir do
     fornecedor e do tipo de despesa (você só ajusta).
6. (Opcional) marque **Incluir Saída C**.
7. Clique em **Gerar arquivos** → o navegador baixa um **`.zip`** com as saídas.

> Você pode subir só **um** documento (ex.: só a DUIMP). O sistema não quebra —
> apenas avisa o que ficou faltando.

---

## 5. O que cada arquivo de saída significa

Ao gerar, você recebe um `.zip` com:

| Arquivo | O que é | Para quê serve |
|---------|---------|----------------|
| **`saida_A_extracao.csv`** | **Saída A** — uma linha com todos os dados do processo | Prova da extração; alimenta o controle interno de importações |
| `saida_A_rastreavel.csv` | Versão "rastreável" da A (formato `Processo;Documento;Campo;Valor;Fonte`) | Mostra **de qual documento** veio cada dado — ótimo para auditoria/apresentação |
| **`saida_B_lancamentos_dominio.csv`** e `.txt` | **Saída B** — lançamentos contábeis (partidas) no **layout da macro do Domínio** | Importação **manual** no Domínio. 10 colunas, separadas por `;`, **sem cabeçalho** |
| `saida_C_fornecedores.csv` *(se marcado)* | **Saída C** — cadastro do fornecedor estrangeiro | Controle interno / cadastro (bônus) |

**Layout da Saída B** (igual à macro `Sub Gerar()`):

```
Data;Cód.Conta Débito;Cód.Conta Crédito;Valor;Cód.Histórico;Complemento Histórico;Inicia Lote;Matriz/Filial;CC Débito;CC Crédito
```

Exemplo de linha gerada:
```
30/04/2026;5210;805;1595,46;59;PROCESSO 870 ... - AFRMM;;;;
```

> **Saída B saiu vazia?** Toda partida do POP usa a **conta do processo** — sem o código dela
> nada é lançado, e o CSV do Domínio sai sem uma única linha (spec §1.4 [R3]: o sistema não
> inventa número de conta). Informe no bloco *Middleware* o campo **“Conta do Processo — número”**
> *ou* a linha `conta_processo` da tabela **Plano de contas do processo** (a tabela tem
> precedência). Para as partidas dos Passos 5.2 e 6.2, informe também `fornecedor_estrangeiro`
> e `adiantamento_despachante`. A tela avisa em vermelho quais contas estão faltando e destaca
> os campos; a lista completa também vai no `AVISOS.txt` do zip.

---

## 6. Estrutura de pastas

```
.
├── assets/                  # PDFs de exemplo (usados como fixtures dos testes)
├── docs/                    # imagem.png — o fluxo ilustrado
├── backend/                 # o "cérebro" (Python/FastAPI)
│   ├── main.py              # app + rotas (/extract, /generate, /) + serve o front
│   ├── models.py            # schemas dos dados (Pydantic)
│   ├── pdf_utils.py         # ler texto do PDF + converter números/datas BR
│   ├── detector.py          # descobre o tipo do documento pelo conteúdo
│   ├── extractors/          # um extrator por tipo de documento
│   │   ├── comum.py         # bloco compartilhado entre DI e DUIMP
│   │   ├── duimp.py · di.py · nota_fiscal.py
│   │   └── fechamento_terra.py · fechamento_win.py · fechamento_syndex.py
│   │       · fechamento_alltime.py · fechamento_connecta.py
│   ├── consolidador.py      # junta os documentos em 1 registro de processo
│   ├── depara.py            # tabela de-para (fornecedor/despesa → conta/histórico)
│   └── outputs.py           # gera os CSVs A, B e C
├── frontend/                # a tela (HTML/CSS/JS puro)
│   ├── index.html · app.js · styles.css
├── tests/                   # testes automatizados (pytest)
├── requirements.txt
└── README.md
```

---

## 7. O que está e o que não está no escopo

**Está no escopo:**
- Upload por arrastar/soltar de vários PDFs de **um processo**.
- Extração de **DUIMP**, **DI**, **NF de Importação**, e dos fechamentos
  **TERRA**, **WIN TRADING**, **SYNDEX**, **ALL TIME** e **CONNECTA**.
- Camada **Middleware** (operador confere e completa) com **de-para**.
- **Validação de despesas do fechamento:** rubricas recorrentes/obrigatórias +
  reconciliação (Σ despesas == TOTAL; numerário − total == saldo), com avisos ao operador.
- **Conferência navegável de divergências** entre documentos (diff + seleção do valor)
  e **campos de câmbio** para conferência, com a variação cambial calculada a partir deles.
- Geração das **Saídas A, B e C**.

**NÃO está no escopo (por enquanto):**
- **Conciliação automática que decide sozinha** as divergências — a navegação e a
  seleção do valor existem; a *correção/decisão automática* não.
- **Parser do contrato de câmbio real** — o câmbio é **entrada manual** (middleware)
  e a variação é calculada a partir dele; o contrato em si ainda não é lido.
- Outros layouts de fechamento além de TERRA, WIN, SYNDEX, ALL TIME e CONNECTA.
- **OCR** de documentos escaneados (os exemplos têm camada de texto).
- Integração automática com o Domínio — a importação segue **manual** (anexar o arquivo).
- Banco de dados, login, multiusuário.

---

## 8. Limitações conhecidas e próximos passos

**Limitações:**
- Os extratores foram calibrados nos exemplos reais de `assets/`. PDFs com
  layout muito diferente (ou escaneados, sem texto) podem não ser lidos.
- Os fechamentos são **despadronizados** — o maior risco de extração. Campos
  como "navio/origem/destino" do TERRA são lidos por aproximação.
- A tabela **de-para** é um *seed* pequeno (alguns fornecedores/despesas de
  exemplo). Em produção viraria uma tabela editável por cliente.
- As colunas da Saída A e o layout exato da Saída B ainda devem ser
  **confirmados na reunião** com a key user.

**Próximos passos sugeridos:**
1. Validar o fluxo e os arquivos com a key user (Larissa).
2. Confirmar a lista final de colunas e o plano de contas/históricos (de-para).
3. Definir a regra de **entidade contábil** em conta e ordem (trading × adquirente).
4. Evoluir para produção: parsers mais robustos, de-para em banco, OCR e,
   eventualmente, conciliação de divergências.

> Este mockup é **descartável** — ele prova o fluxo, mas **não dita** a
> arquitetura final do produto.
