import pulp


class CustomerDescarte:
    def __init__(self, vMin, vMax):
        self.elements = {}
        self.vMin = vMin
        self.vMax = vMax

    def create_variavel(self, customer):
        if customer in self.elements:
            return self.elements[customer]

        var = pulp.LpVariable(f"descarte_{customer}", cat="Integer")
        self.elements[customer] = var
        return var

    def get_variavel(self, customer):
        # if customer not in self.elements:
        #     return self.create_variavel(customer)
        return self.elements[customer]

    def constains(self, customer):
        return customer in self.elements

    def fill_variavel(self, customers):
        for customer in customers:
            self.create_variavel(customer)
