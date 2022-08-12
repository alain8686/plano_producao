import pulp


class LineaEstoque:
    def __init__(self, vMin, vMax):
        self.elements = {}
        self.vMin = vMin
        self.vMax = vMax

    def create_variavel(self, linea_producao, produto, mes):
        if (linea_producao, produto, mes) in self.elements:
            return self.elements[(linea_producao, produto, mes)]

        var = pulp.LpVariable(f"lineaEstoque_{linea_producao}_{produto}_{mes}", cat="Integer", lowBound=self.vMin,
                              upBound=self.vMax)
        self.elements[(linea_producao, produto, mes)] = var
        return var

    def get_variavel(self, linea_producao, produto, mes):
        # if (linea_producao, produto, mes) not in self.elements:
        #     return self.create_variavel(linea_producao, produto, mes)
        return self.elements[(linea_producao, produto, mes)]

    def constains(self, linea_producao, produto, mes):
        return (linea_producao, produto, mes) in self.elements

    def fill_variavel(self, df_produtos_estoque):
        for _, row in df_produtos_estoque.iterrows():
            self.create_variavel(int(row['machine']), int(row['sku']), int(row['month']))
