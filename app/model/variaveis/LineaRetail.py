import pandas as pd
import pulp


class LineaRetail:
    def __init__(self, vMin, vMax):
        self.elements = {}
        self.vMin = vMin
        self.vMax = vMax

    def create_variavel(self, linea_producao, produto, retail, mes, demand=10**10, pedido_firme=0):
        var = pulp.LpVariable(f"lineaRetail_{linea_producao}_{retail}_{produto}_{mes}", cat="Integer",
                              lowBound=max(self.vMin, 0), upBound=min(self.vMax, demand))
        self.elements[(linea_producao, produto, retail, mes)] = var
        return var

    def get_variavel(self, linea_producao, produto, retail, mes):
        # if (linea_producao, produto, retail, mes) not in self.elements:
        #     return self.create_variavel(linea_producao, produto, retail, mes)
        return self.elements[(linea_producao, produto, retail, mes)]

    def constains(self, linea_producao, produto, retail, mes):
        return (linea_producao, produto, retail, mes) in self.elements

    def fill_variavel(self, df_demenda_producao: pd.DataFrame):
        for i, row in df_demenda_producao.iterrows():
            self.create_variavel(int(row['machine']), int(row['sku']), i, int(row['month']), int(row['demand']), int(row['retail']))
