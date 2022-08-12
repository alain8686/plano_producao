import pulp
import numpy as np
import pandas as pd
from app.model.variaveis.LineaRetail import LineaRetail
from app.model.variaveis.LineaEstoque import LineaEstoque
from app.model.variaveis.EstoqueRetail import EstoqueRetail
from app.model.variaveis.Ativacao import Ativacao
from app.model.variaveis.CustomerDescarte import CustomerDescarte
from app.model.variaveis.RetailSatifacao import RetailSatifacao

TEMPO_EXECUCAO = 4
G = 10**10


class PlanoExecucao:
    def __init__(self, df_demanda, df_capacidade_producao, df_capacidade_produtiva, df_custo_producao,
                 df_capacidade_armacenamento, df_custo_ativacao, df_descarte_produto, df_capacidad_descarte):
        self.df_demanda: pd.DataFrame = df_demanda
        self.df_capacidade_producao = df_capacidade_producao
        self.df_capacidade_produtiva = df_capacidade_produtiva
        self.df_custo_producao = df_custo_producao
        self.df_capacidade_armacenamento = df_capacidade_armacenamento
        self.df_custo_ativacao = df_custo_ativacao
        self.df_descarte_produto = df_descarte_produto
        self.df_capacidad_descarte = df_capacidad_descarte

        _custo_producao = self.df_custo_producao['price'] - self.df_custo_producao['cost_unit']
        self.max_ganho = _custo_producao.max()
        max_eficiencia = self.df_capacidade_producao['eficiency'].max()
        max_capacidade = self.df_capacidade_produtiva['capacity'].max()
        self.C = 4 * self.max_ganho * max_eficiencia * max_capacidade

        self.demanda_max = int(self.df_demanda['demand'].max())
        demanda_total = self.df_demanda['demand'].sum()

        max_by_product = self.df_descarte_produto['by_product'].max()
        self.quantidade_max_descarte_produto = float(max_by_product * demanda_total)

        self.df_capacidade_producao['eficiency'] = 60 * self.df_capacidade_producao['eficiency']

        self.__init_variaveis()
        self.__define_variaveis(df_demanda, df_capacidade_producao, df_capacidade_armacenamento)

        self.prob = pulp.LpProblem("PlanoExecucao", pulp.LpMaximize)

    def __init_variaveis(self):
        self.linea_retail = LineaRetail(0, self.C)
        self.linea_estoque = LineaEstoque(0, self.C)
        self.estoque_retail = EstoqueRetail(0, self.C)
        self.ativacao = Ativacao()
        self.customer_descarte = CustomerDescarte(0, self.C)
        self.retail_satisfacao = RetailSatifacao()

    def __define_variaveis(self, df_demanda, df_producao, df_capacidade_armacenamento):
        demanda_producao = pd.merge(left=df_demanda,
                                    right=df_producao, how='inner', on='sku')[['sku', 'month', 'machine', 'retail', 'demand']]
        self.linea_retail.fill_variavel(demanda_producao)

        df_produtos_estoque = demanda_producao[['sku', 'machine', 'month']]
        self.linea_estoque.fill_variavel(df_produtos_estoque)

        machines = np.unique(df_producao[['machine']], axis=0)
        self.ativacao.fill_variavel([int(machine) for machine in machines])

        customers = ['Cooperativa', 'Reciclagem', 'Descarte']
        self.customer_descarte.fill_variavel(customers)

        self.estoque_retail.fill_variavel(df_demanda)
        self.retail_satisfacao.fill_variavel(df_demanda)

        self.capacidade_armacenamento_interna = None
        self.capacidade_estoque = None
        self.preco_estoque = None
        for _, row in df_capacidade_armacenamento.iterrows():
            local = row['unit']
            capacidade = row['capacity']
            preco = row['price']

            if local == "Frabrica":
                self.capacidade_armacenamento_interna = capacidade
            else:
                self.capacidade_estoque = capacidade
                self.preco_estoque = preco

    def define_obj(self):
        obj_ganho = self.objetivo_ganho_venda()
        obj_custo_estoque = self.objetivo_custo_estoque()
        obj_custo_ativacao = self.objetivo_custo_ativacao()
        obj_penalizacao_satisfacao = self.objetivo_penalizacao_satisfacao()
        #obj_subproduto = self.objetivo_subrodutos()
        obj_subproduto = self.objetivo_subrodutos_2()

        self.prob += obj_ganho - obj_custo_estoque - obj_custo_ativacao + obj_subproduto - obj_penalizacao_satisfacao

    def objetivo_penalizacao_satisfacao(self):
        obj = None
        max_dem = int(self.df_demanda['demand'].max())

        for retail, row in self.df_demanda.iterrows():
            mes = int(row['month'])
            produto = int(row['sku'])

            if self.retail_satisfacao.constains(retail, produto, mes):
                var_satisfacao = self.retail_satisfacao.get_variavel(retail, produto, mes)
                obj = obj + (1 - var_satisfacao) * max_dem * self.max_ganho if obj is not None else \
                    (1 - var_satisfacao) * max_dem * self.max_ganho
        return obj

    def objetivo_custo_ativacao(self):
        obj = None
        for _, row in self.df_custo_ativacao.iterrows():
            machine = int(row['machine'])
            custo = row['activation_cost']

            obj = obj + self.ativacao.get_variavel(machine) * custo if obj is not None \
                else self.ativacao.get_variavel(machine) * custo
        return obj

    def objetivo_custo_estoque(self):
        productos = np.unique(self.df_capacidade_producao['sku'])
        machines = np.unique(self.df_capacidade_producao[['machine']], axis=0)
        retails = range(0, self.df_demanda.shape[0])

        acc = {}
        obj = None
        for m in range(1, TEMPO_EXECUCAO + 1):
            acc[m] = {}
            for producto in productos:
                producto = int(producto)
                acc[m][producto] = {}

                input_sum = acc[m - 1][producto]['in'] if m - 1 in acc and producto in acc[m - 1] else None
                output_sum = acc[m - 1][producto]['out'] if m - 1 in acc and producto in acc[m - 1] else None

                for machine in machines:
                    machine = int(machine)
                    if self.linea_estoque.constains(machine, producto, m):
                        conexao = self.linea_estoque.get_variavel(machine, producto, m)
                        input_sum = input_sum + conexao if input_sum is not None else conexao

                for retail in retails:
                    if self.estoque_retail.constains(retail, producto, m):
                        conexao = self.estoque_retail.get_variavel(retail, producto, m)
                        output_sum = output_sum + conexao if output_sum is not None else conexao

                acc[m][producto]['in'] = input_sum
                acc[m][producto]['out'] = output_sum

                delta = (input_sum - output_sum - self.capacidade_armacenamento_interna) * self.preco_estoque
                obj = obj + delta if obj is not None else delta
        return obj

    def objetivo_ganho_venda(self):
        machines = np.unique(self.df_capacidade_producao[['machine']], axis=0)
        retails = range(0, self.df_demanda.shape[0])

        obj = None
        for _, row in self.df_custo_producao.iterrows():
            produto = int(row['sku'])
            m = int(row['month'])
            ganho = row['price'] - row['cost_unit']
            for retail in retails:
                if self.estoque_retail.constains(retail, produto, m):
                    conexao = self.estoque_retail.get_variavel(retail, produto, m)
                    obj = obj + ganho * conexao if ganho is not None else ganho * conexao

                for machine in machines:
                    machine = int(machine)

                    if self.linea_retail.constains(machine, produto, retail, m):
                        conexao = self.linea_retail.get_variavel(machine, produto, retail, m)
                        obj = obj + ganho * conexao if ganho is not None else ganho * conexao

        return obj

    def objetivo_subrodutos_2(self):
        machines = np.unique(self.df_capacidade_producao[['machine']], axis=0)
        retails = range(0, self.df_demanda.shape[0])
        productos = np.unique(self.df_capacidade_producao['sku'])

        cooperativa, reciclagem, descarte = self.capacidade_customer()

        descarte_total = None
        for machine in machines:
            machine = int(machine)
            for produto in productos:
                produto = int(produto)

                by_machine = self.df_descarte_produto[self.df_descarte_produto['machine'] == machine]
                by_machine_producto: pd.DataFrame = by_machine[by_machine['sku'] == produto]['by_product']
                if by_machine_producto.empty:
                    continue
                kg_descarte = float(by_machine_producto.array[0])

                for m in range(1, TEMPO_EXECUCAO + 1):
                    if self.linea_estoque.constains(machine, produto, m):
                        conexao = self.linea_estoque.get_variavel(machine, produto, m)
                        descarte_total = descarte_total + conexao * kg_descarte if descarte_total is not None else conexao * kg_descarte

                    for retail in retails:
                        if self.linea_retail.constains(machine, produto, retail, m):
                            conexao = self.linea_retail.get_variavel(machine, produto, retail, m)
                            descarte_total = descarte_total + conexao * kg_descarte \
                                if descarte_total is not None else conexao * kg_descarte
        return descarte_total * cooperativa['price']

    def objetivo_subrodutos(self):
        var_cooperativa = self.customer_descarte.get_variavel('Cooperativa')
        var_reciclagem = self.customer_descarte.get_variavel('Reciclagem')
        var_descarte = self.customer_descarte.get_variavel('Descarte')

        cooperativa, reciclagem, descarte = self.capacidade_customer()

        obj = var_cooperativa * cooperativa['price'] - var_cooperativa * cooperativa['cost']
        obj += var_reciclagem * cooperativa['price'] - var_reciclagem * cooperativa['cost']
        obj += var_descarte * cooperativa['price'] - var_descarte * cooperativa['cost']

        return obj

    def capacidade_customer(self):
        cooperativa = None
        reciclagem = None
        descarte = None
        for _, row in self.df_capacidad_descarte.iterrows():
            if row['customer'] == 'Cooperativa':
                cooperativa = row
            elif row['customer'] == 'Reciclagem':
                reciclagem = row
            else:
                descarte = row
        return cooperativa, reciclagem, descarte

    def restricao_subrodutos(self):
        machines = np.unique(self.df_capacidade_producao[['machine']], axis=0)
        retails = range(0, self.df_demanda.shape[0])
        productos = np.unique(self.df_capacidade_producao['sku'])

        cooperativa, reciclagem, descarte = self.capacidade_customer()

        descarte_total = None
        for machine in machines:
            machine = int(machine)
            for produto in productos:
                produto = int(produto)

                by_machine = self.df_descarte_produto[self.df_descarte_produto['machine'] == machine]
                by_machine_producto: pd.DataFrame = by_machine[by_machine['sku'] == produto]['by_product']
                if by_machine_producto.empty:
                    continue
                kg_descarte = float(by_machine_producto.array[0])

                for m in range(1, TEMPO_EXECUCAO + 1):
                    if self.linea_estoque.constains(machine, produto, m):
                        conexao = self.linea_estoque.get_variavel(machine, produto, m)
                        descarte_total = descarte_total + conexao * kg_descarte if descarte_total is not None else conexao * kg_descarte

                    for retail in retails:
                        if self.linea_retail.constains(machine, produto, retail, m):
                            conexao = self.linea_retail.get_variavel(machine, produto, retail, m)
                            descarte_total = descarte_total + conexao * kg_descarte \
                                if descarte_total is not None else conexao * kg_descarte

        var_cooperativa = self.customer_descarte.get_variavel('Cooperativa')
        tmp1 = pulp.LpVariable("tmp_1", cat="Binary")
        self.prob += descarte_total <= var_cooperativa + self.quantidade_max_descarte_produto * tmp1
        self.prob += var_cooperativa <= descarte_total + self.quantidade_max_descarte_produto * tmp1
        self.prob += cooperativa['capacity'] <= var_cooperativa + self.quantidade_max_descarte_produto * (1 - tmp1)
        self.prob += var_cooperativa <= cooperativa['capacity'] + self.quantidade_max_descarte_produto * (1 - tmp1)

        var_reciclagem = self.customer_descarte.get_variavel('Reciclagem')
        tmp2 = pulp.LpVariable("tmp_2", cat="Binary")
        self.prob += descarte_total - var_cooperativa <= var_reciclagem + 2 * self.quantidade_max_descarte_produto * tmp2
        self.prob += var_reciclagem <= descarte_total - var_cooperativa + 2 * self.quantidade_max_descarte_produto * tmp2
        self.prob += min(reciclagem['capacity'], self.quantidade_max_descarte_produto) <= var_reciclagem + \
                     2 * self.quantidade_max_descarte_produto * (1 - tmp2)
        self.prob += var_reciclagem <= min(reciclagem['capacity'], self.quantidade_max_descarte_produto) + \
                     2 * self.quantidade_max_descarte_produto * (1 - tmp2)

        # var_descarte = self.customer_descarte.get_variavel('Descarte')
        # tmp3 = pulp.LpVariable("tmp_3", cat="Binary")
        # self.prob += descarte_total - var_cooperativa - var_reciclagem <= var_descarte + \
        #              2 * self.quantidade_max_descarte_produto * tmp3
        # self.prob += var_descarte <= descarte_total - var_cooperativa - var_reciclagem + \
        #              2 * self.quantidade_max_descarte_produto * tmp3
        # self.prob += min(descarte['capacity'], self.quantidade_max_descarte_produto) <= var_descarte + \
        #              2 * self.quantidade_max_descarte_produto * (1 - tmp3)
        # self.prob += var_descarte <= min(descarte['capacity'], self.quantidade_max_descarte_produto) + \
        #              2 * self.quantidade_max_descarte_produto * (1 - tmp3)

    def restricao_demanda_total(self):
        machines = np.unique(self.df_capacidade_producao[['machine']], axis=0)
        retails = range(0, self.df_demanda.shape[0])

        df_demanda_produto = self.df_demanda[['sku', 'demand']].groupby(['sku'], as_index=False, sort=False).sum()
        for _, row in df_demanda_produto.iterrows():
            produto = int(row['sku'])
            demanda = float(row['demand'])

            producao = None
            for m in range(1, TEMPO_EXECUCAO + 1):
                for retail in retails:
                    for machine in machines:
                        machine = int(machine)
                        if self.linea_retail.constains(machine, produto, retail, m):
                            conexao = self.linea_retail.get_variavel(machine, produto, retail, m)
                            producao = producao + conexao if producao is not None else conexao
                if self.linea_estoque.constains(machine, produto, m):
                    conexao = self.linea_estoque.get_variavel(machine, produto, m)
                    producao = producao + conexao if producao is not None else conexao

            if producao is not None:
                self.prob += producao <= demanda

    def restricao_custo_ativacao(self):
        retails = range(0, self.df_demanda.shape[0])
        productos = np.unique(self.df_capacidade_producao['sku'])

        df_eficiencia_capacidad = pd.merge(left=self.df_capacidade_producao,
                                    right=self.df_capacidade_produtiva, how='inner', on='machine')[
            ['sku', 'machine', 'eficiency', 'capacity']]
        df_eficiencia_capacidad['capacidade_max'] = df_eficiencia_capacidad['eficiency'] * \
                                                    df_eficiencia_capacidad['capacity']
        df_eficiencia_capacidad = df_eficiencia_capacidad[['machine', 'capacidade_max']]
        df_eficiencia_capacidad = df_eficiencia_capacidad.groupby(['machine'], as_index=False, sort=False).max()
        df_eficiencia_capacidad['capacidade_max'] = 400 * df_eficiencia_capacidad['capacidade_max']

        for _, row in df_eficiencia_capacidad.iterrows():
            machine = int(row['machine'])
            capacidade_max = float(row['capacidade_max'])

            sum = None
            for m in range(1, TEMPO_EXECUCAO + 1):
                for produto in productos:
                    produto = int(produto)
                    if self.linea_estoque.constains(machine, produto, m):
                        conexao = self.linea_estoque.get_variavel(machine, produto, m)
                        sum = sum + conexao if sum is not None else conexao

                    for retail in retails:
                        if self.linea_retail.constains(machine, produto, retail, m):
                            conexao = self.linea_retail.get_variavel(machine, produto, retail, m)
                            sum = sum + conexao if sum is not None else conexao
            if sum is not None:
                self.prob += self.ativacao.get_variavel(machine) <= sum
                self.prob += sum <= self.ativacao.get_variavel(machine) * capacidade_max

    def restricao_controle_estoque(self):
        productos = np.unique(self.df_capacidade_producao['sku'])
        machines = np.unique(self.df_capacidade_producao[['machine']], axis=0)
        retails = range(0, self.df_demanda.shape[0])

        acc = {}
        for m in range(1, TEMPO_EXECUCAO + 1):
            acc[m] = {}
            for producto in productos:
                producto = int(producto)
                acc[m][producto] = {}

                input_sum = acc[m - 1][producto]['in'] if m - 1 in acc and producto in acc[m - 1] else None
                for machine in machines:
                    machine = int(machine)
                    if self.linea_estoque.constains(machine, producto, m) and m  < TEMPO_EXECUCAO:
                        conexao = self.linea_estoque.get_variavel(machine, producto, m)
                        input_sum = input_sum + conexao if input_sum is not None else conexao

                output_sum = acc[m - 1][producto]['out'] if m - 1 in acc and producto in acc[m - 1] else None
                for retail in retails:
                    if self.estoque_retail.constains(retail, producto, m):
                        conexao = self.estoque_retail.get_variavel(retail, producto, m)
                        output_sum = output_sum + conexao if output_sum is not None else conexao

                acc[m][producto]['in'] = input_sum
                acc[m][producto]['out'] = output_sum

                if m < TEMPO_EXECUCAO:
                    if output_sum is not None and input_sum is not None:
                        self.prob += output_sum <= input_sum

                    input_sum_ = input_sum if input_sum is not None else 0
                    output_sum_ = output_sum if output_sum is not None else 0
                    self.prob += input_sum_ - output_sum_ <= self.capacidade_armacenamento_interna + \
                                 self.capacidade_estoque
                else:
                    self.prob += output_sum == input_sum

    def restricao_capacidade_produtiva(self):
        machines = np.unique(self.df_capacidade_producao[['machine']], axis=0)
        retails = range(0, self.df_demanda.shape[0])
        produtos = np.unique(self.df_capacidade_producao['sku'])

        for machine in machines:
            machine = int(machine)

            for m in range(1, TEMPO_EXECUCAO + 1):
                suma = None

                for produto in produtos:
                    produto = int(produto)

                    df_capacidade = self.df_capacidade_producao[self.df_capacidade_producao['machine'] == machine]
                    df_capacidade = df_capacidade[df_capacidade['sku'] == produto]

                    if df_capacidade.shape[0] == 0:
                        continue
                    eficiencia = df_capacidade['eficiency'].array[0]

                    for retail in retails:
                        if self.linea_retail.constains(machine, produto, retail, m):
                            conexao = self.linea_retail.get_variavel(machine, produto, retail, m)
                            suma = suma + conexao * (1 / eficiencia) if suma is not None else conexao * (1 / eficiencia)

                    if self.linea_estoque.constains(machine, produto, m):
                        conexao = self.linea_estoque.get_variavel(machine, produto, m)
                        suma = suma + conexao * (1 / eficiencia) if suma is not None else conexao * (1 / eficiencia)

                if suma is not None:
                    df_capacidade = self.df_capacidade_produtiva[self.df_capacidade_produtiva['machine'] == machine]
                    capacidade = df_capacidade['capacity'].array[0]
                    self.prob += suma <= capacidade

    def restricao_demanda(self):
        machines = np.unique(self.df_capacidade_producao['machine'], axis=0)

        for retail, row in self.df_demanda.iterrows():
            mes = int(row['month'])
            produto = int(row['sku'])

            demanda = float(row['demand'])
            pedido_firme = float(row['retail'])

            suma = None
            for machine in machines:
                machine = int(machine)

                if self.linea_retail.constains(machine, produto, retail, mes):
                    conexao = self.linea_retail.get_variavel(machine, produto, retail, mes)
                    suma = suma + conexao if suma is not None else conexao

            if mes > 1:
                if self.estoque_retail.constains(retail, produto, mes):
                    conexao = self.estoque_retail.get_variavel(retail, produto, mes)
                    suma = suma + conexao if suma is not None else conexao

            if suma is not None:
                self.prob += suma <= demanda

                satisfacao = self.retail_satisfacao.get_variavel(retail, produto, mes)
                self.prob += -self.demanda_max + satisfacao * self.demanda_max <= suma - pedido_firme
                self.prob += suma - pedido_firme <= satisfacao * self.demanda_max



