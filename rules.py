from textwrap import dedent
from functools import lru_cache



PLANTAS = [
    "ARACATUBA", "BENTO", "BLUMENAU", "ESHOP", "FORTALEZA", "ITUPEVA",
    "MARANGUAPE", "PACAJUS", "PIRAPETINGA", "PORTO FELIZ", "SAQUAREMA", "UBERABA"
]

SCHEMA_INFO = {

    "BI_OTIF": {
        "descricao": "Base de desempenho OTIF (On Time In Full) — mede pontualidade e completude das entregas",
        "colunas": {
            "PLANTA": "Código ou nome da planta de produção",
            "CIDADE": "Cidade onde o pedido foi produzido ou entregue",
            "ANO": "Ano de referência do pedido ou entrega",
            "MES": "Mês de referência (1 a 12)",
            "NUMERO": "Número do pedido",
            "CODCLI": "Código do cliente no sistema",
            "LOJACLI": "Loja ou filial do cliente",
            "NOME_CLI": "Nome do cliente",
            "CNPJ_CLIENTE": "CNPJ do cliente",
            "COD_PRODUTO": "Código do produto",
            "REF": "Referência interna ou código alternativo do produto",
            "C5STATUS": "Status do pedido (ex.: entregue, pendente, cancelado)",
            "TPFRETE": "Tipo de frete (ex.: CIF, FOB, etc.)",
            "DT_ENTREG": "Data planejada de entrega",
            "DT_ENTREG2": "Data real de entrega (caso exista)",
            "DT_ENT_PED1": "Data de emissão do pedido (campo 1)",
            "DT_ENT_PED2": "Data de emissão complementar (campo 2)",
            "QTD_ORIG": "Quantidade original do pedido",
            "QTD_VEND": "Quantidade vendida (unidades)",
            "QTD_TOLMA": "Tolerância máxima de quantidade permitida",
            "QTD_TOLME": "Tolerância mínima de quantidade permitida",
            "QTD_PRONTO": "Quantidade pronta para expedição",
            "DT_PRONTO": "Data em que o pedido ficou pronto para entrega",
            "AREA_PED": "Área total do pedido (m²)",
            "QTD_NF": "Quantidade total faturada em notas fiscais",
            "NUM_NOTAS": "Número de notas fiscais associadas ao pedido",
            "DT_PRI_NF": "Data da primeira nota fiscal emitida",
            "DT_ULT_NF": "Data da última nota fiscal emitida",
            "OTIF_DATA": "Indicador de pontualidade (1 se entregue no prazo, 0 caso contrário)",
            "OTIF_QUANT": "Indicador de completude da entrega (1 se entregue totalmente, 0 caso contrário)",
            "OTIF_FINAL": "Indicador final OTIF (1 se pontual e completo, 0 caso contrário)",
            "TP_DATA": "Tipo de data considerada (ex.: entrega, emissão, etc.)",
            "TP_QTD": "Tipo de quantidade (planejada, real, tolerada, etc.)",
            "TQ_MENOS": "Diferença de quantidade abaixo do esperado",
            "TQ_MAIS": "Diferença de quantidade acima do esperado",
            "DT_MENOR": "Menor data entre entregas relacionadas ao pedido",
            "DT_MAIOR": "Maior data entre entregas relacionadas ao pedido",
            "NR_DIASVIA": "Número de dias de viagem ou transporte até o cliente",
            "TP_PRODUTO": "Tipo do produto (ex.: acabado, intermediário, etc.)",
            "TOP30": "Flag indicando se o cliente está no top 30",
            "VALOR_UNIT": "Valor unitário do produto (R$)",
            "KANBAN": "Indicador de controle Kanban",
            "ESHOP": "Flag de venda via e-commerce (E-shop)",
            "CIDADE_CLIENTE": "Cidade do cliente",
            "ESTADO_CLIENTE": "Estado do cliente",
            "FECHADO": "Indicador de fechamento do pedido (1 = fechado, 0 = aberto)",
            "QTD_DEV": "Quantidade devolvida pelo cliente",
            "COD_SAP_CLIENTE": "Código SAP do cliente"
        }
    },

    "DASH_ATUAL": {
        "descricao": "Base atual (DASH_ATUAL) — usada para consultas do mês corrente (ex.: outubro/2025)",
        "colunas": {
            "RecordID": "Identificador interno (float)",
            "Unit": "Unidade / filial (nvarchar)",
            "Tipo_Venda": "Tipo de venda (nvarchar)",
            "CPF_CNPJ": "CPF/CNPJ do cliente (nvarchar)",
            "ID_Cidade_Nome": "Identificador/cidade nome (nvarchar)",
            "Grupo": "Grupo (nvarchar)",
            "Cluster_New": "Cluster (nvarchar)",
            "Vendedor": "Vendedor/rep (nvarchar)",
            "SKU_Type_Descricao": "Descrição do tipo SKU (nvarchar)",
            "Hierarquia_SKU": "Hierarquia do SKU (nvarchar)",
            "Segmento": "Segmento (nvarchar)",
            "Type": "Type (nvarchar)",
            "Papel": "Papel (nvarchar)",
            "Ov_Date_Incoterms": "Data/Incoterms (nvarchar)",
            "Tipo_Doc": "Tipo do documento (nvarchar)",
            "Of_data_Nf": "Data da nota (nvarchar)",
            "Status_Ordem": "Status da ordem (ex.: CANCELADO, Cancelled, Suspended)",
            "Status_CS": "Status CS (nvarchar)",
            "Desconsiderar": "Flag Desconsiderar (nvarchar)",
            "Data": "Data (datetime)",
            "Qtd_Total": "Quantidade total (float)",
            "Qtd_Antecipada": "Quantidade antecipada (float)",
            "Qtd_Liquida": "Quantidade líquida (float)",
            "M2_Bruto": "Área bruta / m2 bruto (float) — USADO PARA CARTEIRA",
            "Kg_Bruto": "Peso bruto (float)",
            "Net_Price_Kiwi": "Preço líquido (float)",
            "Frete+outros": "Frete e outros (float)",
            "Bruto-Imp-Enc": "Bruto menos impostos/encargos (float)",
            "Encargos": "Encargos (float)",
            "Bruto - Impostos": "Bruto - Impostos (float)",
            "Impostos": "Impostos (float)",
            "Valor_Bruto": "Valor bruto (float)",
            "Custos": "Custos (float)",
            "Margem": "Margem (float)",
            "Legacy": "Legacy (nvarchar)",
            "System": "System (nvarchar)",
            "Type_Info": "Type Info (nvarchar)",
            "Date_Ref": "Date Ref (datetime)",
            "Date_Ext": "Date Ext (nvarchar)",
            "Data_Entrega_Original": "Data de entrega original (datetime)",
            "Data_Entrega": "Data de entrega (datetime) — usada para filtragem de carteira",
            "Data_Embarque_Original": "Data embarque original (datetime)",
            "Data_Embarque": "Data embarque (datetime)",
            "M2_Bruto_Antecipado": "M2 bruto antecipado (float)"
        }
    },

    "DASH_HISTORICO": {
        "descricao": "Base histórica (DASH_HISTORICO) — usar para consultas fora do mês corrente/históricas",
        "colunas": {
            # mesmas colunas de DASH_ATUAL
            "RecordID": "Identificador interno (float)",
            "Unit": "Unidade / filial (nvarchar)",
            "Tipo_Venda": "Tipo de venda (nvarchar)",
            "CPF_CNPJ": "CPF/CNPJ do cliente (nvarchar)",
            "ID_Cidade_Nome": "Identificador/cidade nome (nvarchar)",
            "Grupo": "Grupo (nvarchar)",
            "Cluster_New": "Cluster (nvarchar)",
            "Vendedor": "Vendedor/rep (nvarchar)",
            "SKU_Type_Descricao": "Descrição do tipo SKU (nvarchar)",
            "Hierarquia_SKU": "Hierarquia do SKU (nvarchar)",
            "Segmento": "Segmento (nvarchar)",
            "Type": "Type (nvarchar)",
            "Papel": "Papel (nvarchar)",
            "Ov_Date_Incoterms": "Data/Incoterms (nvarchar)",
            "Tipo_Doc": "Tipo do documento (nvarchar)",
            "Of_data_Nf": "Data da nota (nvarchar)",
            "Status_Ordem": "Status da ordem (ex.: CANCELADO, Cancelled, Suspended)",
            "Status_CS": "Status CS (nvarchar)",
            "Desconsiderar": "Flag Desconsiderar (nvarchar)",
            "Data": "Data (datetime)",
            "Qtd_Total": "Quantidade total (float)",
            "Qtd_Antecipada": "Quantidade antecipada (float)",
            "Qtd_Liquida": "Quantidade líquida (float)",
            "M2_Bruto": "Área bruta / m2 bruto (float) — USADO PARA CARTEIRA",
            "Kg_Bruto": "Peso bruto (float)",
            "Net_Price_Kiwi": "Preço líquido (float)",
            "Frete+outros": "Frete e outros (float)",
            "Bruto-Imp-Enc": "Bruto menos impostos/encargos (float)",
            "Encargos": "Encargos (float)",
            "Bruto - Impostos": "Bruto - Impostos (float)",
            "Impostos": "Impostos (float)",
            "Valor_Bruto": "Valor bruto (float)",
            "Custos": "Custos (float)",
            "Margem": "Margem (float)",
            "Legacy": "Legacy (nvarchar)",
            "System": "System (nvarchar)",
            "Type_Info": "Type Info (nvarchar)",
            "Date_Ref": "Date Ref (datetime)",
            "Date_Ext": "Date Ext (nvarchar)",
            "Data_Entrega_Original": "Data de entrega original (datetime)",
            "Data_Entrega": "Data de entrega (datetime) — usada para filtragem de carteira",
            "Data_Embarque_Original": "Data embarque original (datetime)",
            "Data_Embarque": "Data embarque (datetime)",
            "M2_Bruto_Antecipado": "M2 bruto antecipado (float)"
        }
    },

    "VW_DEVOLUCAO_LAB": {
        "descricao": "View usada para exemplos de volume (área), faturamento, top clientes",
        "colunas": {
            "CIDADE": "Cidade / planta (usuária para agrupamento)",
            "AREA": "Área relacionada à devolução / venda (m²)",
            "DATA_EMISSAO": "Data de emissão do documento (datetime)",
            # Se a view tiver coluna de cliente, assumimos NOME_CLI; caso contrário adapte o exemplo
            "NOME_CLIENTE": "Nome do cliente (se disponível)",
            "CIDADE_CLIENTE": "Cidade do cliente, origem do cliente região",
            "DESCRICAO_PRODUTO": "Descrição do Produto",
            "TIPO_PRODUTO": "Tipo de produto",
            "GRUPO_PRODUTO": "Grupo de produto",
            "VALOR_UNITARIO": "Valor unitário do produto",
            "VALOR_TOTAL": "Valor total do item e quantidade",
            "VALOR_SEM_IPI": "Valor sem IPI",
            "VALOR_NET": "Valor net ou líquido do produto",
            "PESO": "Peso total",
            "PRECO_KG": "Preço por kilo ou KG do produto",
            "PRECO_M2": "Preço por metros quadrados do produto",
            "DESCRICAO_SEGMENTO": "Descrição do segmento do cliente"
        }
    }
}


METRIC_RULES = dedent(f"""
🚨 REGRA ABSOLUTA - TABELA BLOQUEADA:
- A tabela XXXXX FOI REMOVIDA DO SISTEMA E NÃO EXISTE MAIS
- QUALQUER tentativa de usar xxxxxx resultará em ERRO
- Para consultas de volume/área: usar APENAS VW_DEVOLUCAO_LAB
- Para consultas de carteira: usar APENAS DASH_ATUAL ou DASH_HISTORICO
- Para consultas de saldo de pedido: usar BI_PEDIDOS_LAB
- Para consultas OTIF: usar APENAS BI_OTIF

🚨 REGRA ABSOLUTA - ESCOLHA DE TABELA:
- Se a pergunta mencionar "volume", "área", "m²" → usar VW_DEVOLUCAO_LAB
- Se a pergunta mencionar "carteira" → usar DASH_ATUAL (mês corrente) ou DASH_HISTORICO (histórico)
- Se a pergunta mencionar "OTIF", "pontualidade", "entrega no prazo" → usar BI_OTIF
- Para consultas de saldo de pedido: usar BI_PEDIDOS_LAB
- NUNCA inventar nomes de tabelas que não estão listadas abaixo

TABELAS DISPONÍVEIS NO SISTEMA:
1. VW_DEVOLUCAO_LAB - Para volume/área por planta/cidade
2. DASH_ATUAL - Para carteira do mês corrente (outubro/2025)
3. DASH_HISTORICO - Para carteira de períodos históricos
4. BI_OTIF - Para análises de pontualidade e completude de entregas

⚠️ REGRA CRÍTICA - VOLUME POR PLANTA/CIDADE:
- SEMPRE que a pergunta mencionar "volume", "vol", "área", "m²" referente a uma PLANTA/CIDADE específica, usar OBRIGATORIAMENTE a view VW_DEVOLUCAO_LAB
- Filtros OBRIGATÓRIOS em VW_DEVOLUCAO_LAB:
  * AND GRUPO_PRODUTO NOT IN ('PAPEL','BOBINA')
  * AND TIPO IN ('VENDA','DEVOLUCAO')
- Coluna de data: DATA_EMISSAO (não EMISSAO)
- Coluna de área: AREA (não AREA_VENDIDA)
- Sempre incluir GROUP BY CIDADE

Interpretação de métricas em VW_DEVOLUCAO_LAB:
- volume / vol / m² / área → SUM(AREA)
- Se houver período, use MONTH(DATA_EMISSAO) e YEAR(DATA_EMISSAO)
- Sempre incluir: AND GRUPO_PRODUTO NOT IN ('PAPEL','BOBINA') AND TIPO IN ('VENDA','DEVOLUCAO')

Regras específicas para bases DASH (DASH_ATUAL / DASH_HISTORICO):
- As tabelas DASH usam a coluna **Status_Ordem** para status.
- **Por padrão, ao consultar DASH_ATUAL / DASH_HISTORICO NÃO removeremos automaticamente registros cancelados.**
  Ou seja: não aplicaremos filtros que excluam Status_Ordem = 'CANCELADO' / 'CANCELLED' / 'SUSPENDED' a menos que o usuário peça explicitamente.
- Origem dos dados:
  - Para perguntas relacionadas ao mês corrente (outubro/2025): **usar DASH_ATUAL**.
  - Para perguntas sobre períodos históricos: **usar DASH_HISTORICO**.
- Definição de carteira (DASH):
  - Carteira mensal = soma da coluna **M2_Bruto** para registros com **Data_Entrega** dentro do mês alvo.
  - Recomendamos usar intervalo semi-aberto para robustez:
      TRY_CONVERT(date, Data_Entrega) >= 'YYYY-MM-01' AND TRY_CONVERT(date, Data_Entrega) < 'YYYY-(MM+1)-01'

Regras específicas para BI_OTIF:
- Use BI_OTIF para análises de desempenho de entregas
- Colunas principais: OTIF_DATA (pontualidade), OTIF_QUANT (completude), OTIF_FINAL (indicador geral)
- Filtrar por ANO e MES para períodos específicos
- CIDADE indica a origem/planta de produção

Plantas disponíveis: {", ".join(PLANTAS)}
Sempre que a pergunta citar um desses nomes, filtre por CIDADE (collate Latin1_General_CI_AI).

Apenas SELECT/CTE permitidos. Proibido DDL/DCL/EXEC.
""").strip()

EXEMPLOS_SEMENTE = [
  
    # -------------------------------------------------------------------------
    # Novos exemplos: VW_DEVOLUCAO_LAB (volume)
    # -------------------------------------------------------------------------
    # V-1) Volume total de uma planta (VW_DEVOLUCAO_LAB) — exemplo: MARANGUAPE, agosto/2025
    {"pergunta":"Volume total em Maranguape em agosto de 2025",
     "sql":dedent("""
        -- Volume total (área) por planta na view de devoluções / vendas
        SELECT 
            CIDADE,
            SUM(AREA) AS AREA_TOTAL_LIQUIDA
        FROM VW_DEVOLUCAO_LAB WITH (NOLOCK)
        WHERE 
            CIDADE COLLATE Latin1_General_CI_AI = 'MARANGUAPE'
            AND MONTH(DATA_EMISSAO) = 8
            AND YEAR(DATA_EMISSAO) = 2025
            AND GRUPO_PRODUTO NOT IN ('PAPEL','BOBINA')
            AND TIPO IN ('VENDA','DEVOLUCAO')
        GROUP BY 
            CIDADE; --END
     """)},

     # V-2) Volume por múltiplas plantas
    {"pergunta":"Volume total em Bento e Blumenau em setembro de 2025",
    "sql":dedent("""
      SELECT CIDADE, SUM(AREA) AS AREA_TOTAL_LIQUIDA
      FROM VW_DEVOLUCAO_LAB WITH (NOLOCK)
      WHERE CIDADE COLLATE Latin1_General_CI_AI IN ('BENTO', 'BLUMENAU')
        AND MONTH(DATA_EMISSAO) = 9
        AND YEAR(DATA_EMISSAO) = 2025
        AND GRUPO_PRODUTO NOT IN ('PAPEL','BOBINA')
        AND TIPO IN ('VENDA','DEVOLUCAO')
      GROUP BY CIDADE
      ORDER BY AREA_TOTAL_LIQUIDA DESC; --END
      """)},

      # V-3) Volume total (todas as plantas) em um período
      {"pergunta":"Volume total de todas as plantas em julho de 2025",
      "sql":dedent("""
      SELECT SUM(AREA) AS AREA_TOTAL_LIQUIDA
      FROM VW_DEVOLUCAO_LAB WITH (NOLOCK)
      WHERE MONTH(DATA_EMISSAO) = 7
        AND YEAR(DATA_EMISSAO) = 2025
        AND GRUPO_PRODUTO NOT IN ('PAPEL','BOBINA')
        AND TIPO IN ('VENDA','DEVOLUCAO'); --END
      """)},


    # -------------------------------------------------------------------------
    # Exemplos DASH para carteira (usar intervalo semi-aberto; por padrão NÃO removemos cancelados)
    # -------------------------------------------------------------------------

    # DASH-CAR-A) Carteira — Outubro/2025 (usar DASH_ATUAL) — intervalo semi-aberto
    {"pergunta":"Carteira outubro de 2025 (usar DASH_ATUAL) — intervalo semi-aberto",
     "sql":dedent("""
        -- Carteira OUTUBRO/2025 — usar DASH_ATUAL
        -- Regra: soma M2_Bruto para registros com Data_Entrega dentro de outubro/2025.
        -- NOTA: por padrão não removemos Status_Ordem cancelados nesta base (o usuário pode pedir).
        SELECT
          '2025-10' AS MES_REFERENCIA,
          COUNT(DISTINCT RecordID) AS QTD_REGISTROS,
          COALESCE(SUM(M2_Bruto),0) AS M2_BRUTO_CARTEIRA
        FROM dbo.DASH_ATUAL WITH (NOLOCK)
        WHERE TRY_CONVERT(date, Data_Entrega) >= '2025-10-01'
          AND TRY_CONVERT(date, Data_Entrega) <  '2025-11-01'
        ;
     """)},

    # DASH-CAR-B) Carteira histórica / outros meses (usar DASH_HISTORICO) — exemplo genérico
    {"pergunta":"Carteira (períodos fora de outubro/2025) — usar DASH_HISTORICO (intervalo semi-aberto)",
     "sql":dedent("""
        -- Carteira histórica (exemplo genérico)
        -- Defina DATA_INICIO / DATA_FIM conforme a pergunta (DATA_FIM = primeiro dia do mês seguinte)
        SELECT
          YEAR(TRY_CONVERT(date, Data_Entrega)) AS ANO,
          MONTH(TRY_CONVERT(date, Data_Entrega)) AS MES,
          COUNT(DISTINCT RecordID) AS QTD_REGISTROS,
          COALESCE(SUM(M2_Bruto),0) AS M2_BRUTO_CARTEIRA
        FROM dbo.DASH_HISTORICO WITH (NOLOCK)
        WHERE TRY_CONVERT(date, Data_Entrega) >= '2025-09-01' -- ajustar conforme pergunta
          AND TRY_CONVERT(date, Data_Entrega) <  '2025-10-01' -- ajustar conforme pergunta
        GROUP BY YEAR(TRY_CONVERT(date, Data_Entrega)), MONTH(TRY_CONVERT(date, Data_Entrega))
        ORDER BY ANO, MES;
     """)},

    # DASH-CAR-C) Carteira por unidade/planta (DASH_ATUAL) — template semi-aberto
    {"pergunta":"Carteira outubro/2025 por unidade (DASH_ATUAL) — template semi-aberto",
     "sql":dedent("""
        -- Substitua 'SUA_UNIDADE' e as datas conforme necessário
        SELECT
          Unit AS UNIDADE,
          COUNT(DISTINCT RecordID) AS QTD_REGISTROS,
          COALESCE(SUM(M2_Bruto),0) AS M2_BRUTO_CARTEIRA
        FROM dbo.DASH_ATUAL WITH (NOLOCK)
        WHERE Unit COLLATE Latin1_General_CI_AI = 'SUA_UNIDADE'
          AND TRY_CONVERT(date, Data_Entrega) >= '2025-10-01'
          AND TRY_CONVERT(date, Data_Entrega) <  '2025-11-01'
        GROUP BY Unit
        ORDER BY M2_BRUTO_CARTEIRA DESC;
     """)},

    # DASH-CAR-D) Carteira outubro/2025 em Maranguape (usar DASH_ATUAL) — exemplo pedido anteriormente
    {"pergunta":"Carteira outubro/2025 em Maranguape (DASH_ATUAL) — intervalo semi-aberto",
     "sql":dedent("""
        -- Carteira outubro/2025 em Maranguape (usar DASH_ATUAL) — filtro Data_Entrega entre 2025-10-01 e 2025-10-31 (semi-aberto)
        SELECT
          '2025-10' AS MES_REFERENCIA,
          COUNT(DISTINCT RecordID) AS QTD_REGISTROS,
          COALESCE(SUM(M2_Bruto),0) AS M2_BRUTO_CARTEIRA
        FROM dbo.DASH_ATUAL WITH (NOLOCK)
        WHERE Unit COLLATE Latin1_General_CI_AI = 'MARANGUAPE'
          AND TRY_CONVERT(date, Data_Entrega) >= '2025-10-01'
          AND TRY_CONVERT(date, Data_Entrega) <  '2025-11-01'
        ;
     """)},

    # DASH-DEBUG) Query diagnóstica para inspeção de colunas e status (útil se a carteira vier vazia) — NÃO exclui cancelados
    {"pergunta":"Debug DASH_ATUAL — inspecionar registros do cliente/exemplo (não exclui cancelados)",
     "sql":dedent("""
        SELECT TOP 200
          RecordID, Unit, CPF_CNPJ, ID_Cidade_Nome, Grupo, Vendedor,
          Status_Ordem, Data, Data_Entrega, M2_Bruto, Qtd_Liquida
        FROM dbo.DASH_ATUAL WITH (NOLOCK)
        ORDER BY TRY_CONVERT(date, Data_Entrega) DESC;
     """)},

      # S-2) Lista simples de pedidos com AREA_SALDO e PESO_SALDO (linha a linha, sem APPLY/JOINs)
    {"pergunta":"Lista simples de pedidos com AREA_SALDO e PESO_SALDO (linha a linha)",
     "sql":dedent("""
        SELECT
          PED.PEDIDO,
          PED.ITEM,
          PED.PLANTA,
          PED.CIDADE,
          PED.NOME_CLI,
          ISNULL(PED.QUANT_VENDIDA,0) - ISNULL(PED.QUANT_ENTREGUE,0) AS QUANT_SALDO_BRUTO,
          (ISNULL(PED.QUANT_VENDIDA,0) - ISNULL(PED.QUANT_ENTREGUE,0)) * ISNULL(PED.AREA_UNITARIA,0) AS AREA_SALDO,
          (ISNULL(PED.QUANT_VENDIDA,0) - ISNULL(PED.QUANT_ENTREGUE,0)) * ISNULL(PED.PESO_UNITARIO,0) AS PESO_SALDO,
          (ISNULL(PED.QUANT_VENDIDA,0) - ISNULL(PED.QUANT_ENTREGUE,0)) * ISNULL(PED.VALOR_UNITARIO_NET,0) AS VALOR_SALDO
        FROM BI_PEDIDOS_LAB PED WITH (NOLOCK)
        WHERE PED.STATUS_PEDIDO COLLATE Latin1_General_CI_AI NOT LIKE '%CANCELADO%'
          AND ISNULL(PED.QUANT_SALDO_ENTREGAR,0) >= 0
        ORDER BY PED.PLANTA, AREA_SALDO DESC; --END
     """)},

    # S-3) Agregado por PLANTA e CIDADE (soma de area/peso/valor saldo)
    {"pergunta":"Agregado por planta e cidade (soma de area/peso/valor saldo)",
     "sql":dedent("""
        WITH BASE_SALDOS AS (
          SELECT
            PED.PLANTA, PED.CIDADE,
            CASE WHEN PED.CIDADE COLLATE Latin1_General_CI_AI IN ('PIRAPETINGA','UBERABA','ESHOP')
                 THEN ISNULL(PED.QUANT_VENDIDA,0)/(1 + ISNULL(PED.PER_TOLERANCIA_MAIS,0)/100.0)
                 ELSE ISNULL(PED.QUANT_VENDIDA,0) END AS Q_BASE,
            ISNULL(PED.QUANT_ENTREGUE,0) AS Q_ENTREGUE,
            ISNULL(PED.AREA_UNITARIA,0) AS AREA_UNIT
          FROM BI_PEDIDOS_LAB PED WITH (NOLOCK)
          WHERE PED.STATUS_PEDIDO COLLATE Latin1_General_CI_AI NOT LIKE '%CANCELADO%'
        )
        SELECT
          PLANTA,
          CIDADE,
          SUM(CASE WHEN Q_BASE - Q_ENTREGUE < 0 THEN 0 ELSE (Q_BASE - Q_ENTREGUE) * AREA_UNIT END) AS AREA_SALDO_TOTAL,
          SUM(CASE WHEN Q_BASE - Q_ENTREGUE < 0 THEN 0 ELSE (Q_BASE - Q_ENTREGUE) END) AS QUANT_SALDO_TOTAL
        FROM BASE_SALDOS
        GROUP BY PLANTA, CIDADE
        ORDER BY PLANTA, AREA_SALDO_TOTAL DESC; --END
     """)},

    # S-4) Top clientes por AREA_SALDO — versão enxuta (top 50)
    {"pergunta":"Top 50 clientes por area_saldo (versão enxuta)",
     "sql":dedent("""
        WITH CLIENTE_SALDO AS (
          SELECT
            PED.COD_CLI,
            PED.NOME_CLI,
            SUM(CASE 
                  WHEN (CASE WHEN PED.CIDADE COLLATE Latin1_General_CI_AI IN ('PIRAPETINGA','UBERABA','ESHOP')
                             THEN ISNULL(PED.QUANT_VENDIDA,0)/(1 + ISNULL(PED.PER_TOLERANCIA_MAIS,0)/100.0)
                             ELSE ISNULL(PED.QUANT_VENDIDA,0) END) - ISNULL(PED.QUANT_ENTREGUE,0) < 0
                  THEN 0
                  ELSE (CASE WHEN PED.CIDADE COLLATE Latin1_General_CI_AI IN ('PIRAPETINGA','UBERABA','ESHOP')
                             THEN ISNULL(PED.QUANT_VENDIDA,0)/(1 + ISNULL(PED.PER_TOLERANCIA_MAIS,0)/100.0)
                             ELSE ISNULL(PED.QUANT_VENDIDA,0) END) - ISNULL(PED.QUANT_ENTREGUE,0)
                END * ISNULL(PED.AREA_UNITARIA,0)
            ) AS AREA_SALDO_TOTAL
          FROM BI_PEDIDOS_LAB PED WITH (NOLOCK)
          WHERE PED.STATUS_PEDIDO COLLATE Latin1_General_CI_AI NOT LIKE '%CANCELADO%'
            AND ISNULL(PED.QUANT_SALDO_ENTREGAR,0) >= 0
          GROUP BY PED.COD_CLI, PED.NOME_CLI
        )
        SELECT TOP 50 COD_CLI, NOME_CLI, AREA_SALDO_TOTAL
        FROM CLIENTE_SALDO
        ORDER BY AREA_SALDO_TOTAL DESC; --END
     """)},

    # S-5) Top máquinas por AREA_SALDO — pequeno, com JOINs mínimos
    {"pergunta":"Top maquinas por area_saldo (pequeno, com JOINs mínimos)",
     "sql":dedent("""
        WITH MAQ_SALDO AS (
          SELECT
            ISNULL(CASE WHEN PED.GRUPO_PRODUTO = 'CHAPA' THEN 'ONDULADEIRA' ELSE ISNULL(R1.NOME_MAQUINA_1,R2.NOME_MAQUINA_1) END,'') AS MAQUINA,
            CASE WHEN (CASE WHEN PED.CIDADE COLLATE Latin1_General_CI_AI IN ('PIRAPETINGA','UBERABA','ESHOP')
                            THEN ISNULL(PED.QUANT_VENDIDA,0)/(1 + ISNULL(PED.PER_TOLERANCIA_MAIS,0)/100.0)
                            ELSE ISNULL(PED.QUANT_VENDIDA,0) END) - ISNULL(PED.QUANT_ENTREGUE,0) < 0
                 THEN 0
                 ELSE (CASE WHEN PED.CIDADE COLLATE Latin1_General_CI_AI IN ('PIRAPETINGA','UBERABA','ESHOP')
                            THEN ISNULL(PED.QUANT_VENDIDA,0)/(1 + ISNULL(PED.PER_TOLERANCIA_MAIS,0)/100.0)
                            ELSE ISNULL(PED.QUANT_VENDIDA,0) END) - ISNULL(PED.QUANT_ENTREGUE,0)
            END * ISNULL(PED.AREA_UNITARIA,0) AS AREA_SALDO
          FROM BI_PEDIDOS_LAB PED WITH (NOLOCK)
          LEFT JOIN BI_PRODUTOS P ON P.CODIGO = PED.PRODUTO AND P.CIDADE = PED.CIDADE
          LEFT JOIN BI_ROTEIRO R1 ON R1.PRODUTO = P.CODIGO COLLATE Latin1_General_CI_AS AND R1.CIDADE = CASE WHEN P.CIDADE = 'FORTALEZA' THEN 'MARANGUAPE' ELSE P.CIDADE END
          LEFT JOIN BI_ROTEIRO R2 ON R2.PRODUTO = P.CODIGO COLLATE Latin1_General_CI_AS AND R2.CIDADE = CASE WHEN P.CIDADE = 'FORTALEZA' THEN 'MARANGUAPE' ELSE P.CIDADE END
          WHERE PED.STATUS_PEDIDO COLLATE Latin1_General_CI_AI NOT LIKE '%CANCELADO%'
        )
        SELECT TOP 20 MAQUINA, SUM(AREA_SALDO) AS AREA_SALDO_TOTAL
        FROM MAQ_SALDO
        GROUP BY MAQUINA
        ORDER BY AREA_SALDO_TOTAL DESC; --END
     """)},
]

EXEMPLOS_SQL = EXEMPLOS_SEMENTE
