import pulp


class RetailSatifacao:
    def __init__(self):
        self.elements = {}

    def create_variavel(self, retail, produto, mes):
        if (retail, produto, mes) in self.elements:
            return self.elements[(retail, produto, mes)]

        var = pulp.LpVariable(f"satifacao_produto{produto}_retail{retail}_mes{mes}", cat="Binary", upBound=1,
                              lowBound=1)
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
            self.create_variavel(i, row['sku'], row['month'])
