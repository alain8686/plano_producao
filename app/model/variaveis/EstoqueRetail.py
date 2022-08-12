import pulp


class EstoqueRetail:
    def __init__(self, vMin, vMax):
        self.elements = {}
        self.vMin = vMin
        self.vMax = vMax

    def create_variavel(self, retail, produto, mes):
        if (retail, produto, mes) in self.elements:
            return self.elements[(retail, produto, mes)]

        var = pulp.LpVariable(f"estoqueRetail_{produto}_{retail}_{mes}", cat="Integer", lowBound=self.vMin,
                              upBound=self.vMax)
        self.elements[(retail, produto, mes)] = var
        return var

    def get_variavel(self, retail, produto, mes):
        # if (retail, produto, mes) not in self.elements:
        #     return self.create_variavel(retail, produto, mes)
        return self.elements[(retail, produto, mes)]

    def constains(self, retail, produto, mes):
        return (retail, produto, mes) in self.elements

    def fill_variavel(self, df_demanda):
        for i, row in df_demanda.iterrows():
            if row['month'] > 1:
                self.create_variavel(i, row['sku'], row['month'])
