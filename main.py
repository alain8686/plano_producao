import os
import pulp
import pandas as pd
from data import ROOT_DIR
from app.model.PlanoExecucao import PlanoExecucao
from app.analise import analise


if __name__ == '__main__':
    demanda = pd.read_csv(os.path.join(ROOT_DIR, "demand.csv"), sep=";", decimal=",")
    capacidade_producao = pd.read_csv(os.path.join(ROOT_DIR, "production_arcs.csv"), sep=";", decimal=",")
    capacidade_produtiva = pd.read_csv(os.path.join(ROOT_DIR, "production_capacity.csv"), sep=";", decimal=",")
    custo_producao = pd.read_csv(os.path.join(ROOT_DIR, "cost_revenues.csv"), sep=";", decimal=",")
    capacidade_armacenamento = pd.read_csv(os.path.join(ROOT_DIR, "storage_capacity.csv"), sep=";", decimal=",")
    custo_ativacao = pd.read_csv(os.path.join(ROOT_DIR, "activation_cost.csv"), sep=";", decimal=",")
    descarte_produto = pd.read_csv(os.path.join(ROOT_DIR, "by_products.csv"), sep=";", decimal=",")
    capacidad_descarte = pd.read_csv(os.path.join(ROOT_DIR, "by_products_capacity.csv"), sep=";", decimal=",")

    plano = PlanoExecucao(demanda, capacidade_producao, capacidade_produtiva, custo_producao, capacidade_armacenamento,
                          custo_ativacao, descarte_produto, capacidad_descarte)

    plano.restricao_demanda()
    plano.restricao_capacidade_produtiva()
    plano.restricao_controle_estoque()
    plano.restricao_demanda_total()
    plano.restricao_custo_ativacao()
    #plano.restricao_subrodutos()

    plano.define_obj()

    plano.prob.solve(pulp.PULP_CBC_CMD(timeLimit=10*60))

    analise(plano.prob, demanda)

    plano.prob.writeMPS('modelo.mps')
    plano.prob.writeLP('modelo.lp')
