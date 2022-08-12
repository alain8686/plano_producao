import pandas as pd
import numpy as np


def verifica_estoque(df_linha_estoque, df_estoque_retail):
    linha_estoque = df_linha_estoque[['produto', 'quantidade']]
    estoque_retail = df_estoque_retail[['produto', 'quantidade']]

    estoque_retail['quantidade'] = - estoque_retail['quantidade']
    union = pd.concat([estoque_retail, linha_estoque])
    estoque_produto_mes = union.groupby(['produto'], as_index=False, sort=False).sum()

    print(f"controle de estoque: {np.all(estoque_produto_mes['quantidade'] == 0)}")


def analise_producao_consumo(df_linha_retail, df_linha_estoque, df_estoque_retail):
    df_producao_produto = pd.concat([df_linha_estoque[['produto', 'quantidade']],
                                     df_linha_retail[['produto', 'quantidade']]])
    df_producao_consumo = pd.concat([df_estoque_retail[['produto', 'quantidade']],
                                     df_linha_retail[['produto', 'quantidade']]])

    df_producao_produto = df_producao_produto.groupby(['produto'], as_index=False, sort=False).sum()
    df_producao_consumo = df_producao_consumo.groupby(['produto'], as_index=False, sort=False).sum()
    df_producao_consumo['quantidade'] = - df_producao_consumo['quantidade']

    consumo_producao = pd.concat([df_producao_produto, df_producao_consumo])
    consumo_producao = consumo_producao.groupby(['produto'], as_index=False, sort=False).sum()

    print(f"verficacao consumo producao: {np.all(consumo_producao['quantidade'] == 0)}")


def analise_controle_demanda(df_demanda: pd.DataFrame, df_linha_retail, df_estoque_retail):
    df_consumo_produto = pd.concat([df_estoque_retail[['mes', 'retail', 'produto', 'quantidade']],
                                    df_linha_retail[['mes', 'retail', 'produto', 'quantidade']]])
    df_consumo_produto = df_consumo_produto.groupby(['mes', 'retail', 'produto'], as_index=False, sort=False).sum()
    df_consumo_produto['mes'] = pd.to_numeric(df_consumo_produto['mes'])
    df_consumo_produto['retail'] = pd.to_numeric(df_consumo_produto['retail'])
    df_consumo_produto['produto'] = pd.to_numeric(df_consumo_produto['produto'])

    df_demanda_ = df_demanda[['sku', 'month', 'demand']]
    df_demanda_['sku'] = pd.to_numeric(df_demanda_['sku'])
    df_demanda_['month'] = pd.to_numeric(df_demanda_['month'])
    #df_demanda_['demand'] = pd.to_numeric(df_demanda_['demand'])

    df_demanda_['retail'] = range(0, df_demanda_.shape[0])
    df_demanda_ = df_demanda_.rename({'sku': 'produto', 'month': 'mes'}, axis='columns')

    demanda_producao = pd.merge(left=df_demanda_,
                                right=df_consumo_produto, how='inner', on=['mes', 'retail', 'produto'])
    demanda_producido = demanda_producao['demand'] - demanda_producao['quantidade']

    print(f"demanda e producao: {np.all(demanda_producido >= 0)}")


def analise(prob, df_demanda):
    catalog_estoque_retail = {
        'produto': [],
        'mes': [],
        'retail': [],
        'quantidade': []
    }

    catalog_linha_estoque = {
        'linha': [],
        'produto': [],
        'mes': [],
        'quantidade': []
    }

    catalog_linha_retail = {
        'linha': [],
        'produto': [],
        'mes': [],
        'retail': [],
        'quantidade': []
    }

    sub_var = [var for var in prob.variables()]  # if var.name.find('mes1') != -1
    for v in sub_var:
        if v.name.find("estoqueRetail") != -1:
            produto, retail, mes = v.name.split('_')[1:]

            if v.varValue > 0:
                catalog_estoque_retail['produto'].append(produto)
                catalog_estoque_retail['mes'].append(mes)
                catalog_estoque_retail['retail'].append(retail)
                catalog_estoque_retail['quantidade'].append(v.varValue)
        elif v.name.find("lineaRetail") != -1:
            linha, retail, produto, mes = v.name.split('_')[1:]

            if v.varValue > 0:
                catalog_linha_retail['linha'].append(linha)
                catalog_linha_retail['produto'].append(produto)
                catalog_linha_retail['mes'].append(mes)
                catalog_linha_retail['retail'].append(retail)
                catalog_linha_retail['quantidade'].append(v.varValue)
        elif v.name.find("lineaEstoque") != -1:
            linha, produto, mes = v.name.split('_')[1:]

            if v.varValue > 0:
                catalog_linha_estoque['linha'].append(linha)
                catalog_linha_estoque['produto'].append(produto)
                catalog_linha_estoque['mes'].append(mes)
                catalog_linha_estoque['quantidade'].append(v.varValue)

    df_estoque_retail = pd.DataFrame(catalog_estoque_retail)
    df_linha_retail = pd.DataFrame(catalog_linha_retail)
    df_linha_estoque = pd.DataFrame(catalog_linha_estoque)

    df_linha_estoque.to_csv('linha_estoque.csv')
    df_estoque_retail.to_csv('estoque_retail.csv')
    df_linha_retail.to_csv('linha_retail.csv')

    verifica_estoque(df_linha_estoque, df_estoque_retail)
    analise_producao_consumo(df_linha_retail, df_linha_estoque, df_estoque_retail)
    analise_controle_demanda(df_demanda, df_linha_retail, df_estoque_retail)


