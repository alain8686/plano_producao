import pulp


class Ativacao:
    def __init__(self):
        self.elements = {}

    def create_variavel(self, machine):
        if machine in self.elements:
            return self.elements[machine]

        var = pulp.LpVariable(f"linhe_ativacao_{machine}", cat="Binary")
        self.elements[machine] = var
        return var

    def get_variavel(self, machine):
        # if machine not in self.elements:
        #     return self.create_variavel(machine)
        return self.elements[machine]

    def constains(self, machine):
        return machine in self.elements

    def fill_variavel(self, machines):
        for machine in machines:
            self.create_variavel(machine)
