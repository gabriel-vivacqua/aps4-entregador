import random
import time
from collections import deque
from dataclasses import dataclass, field

from aigyminsper.search.graph import State
from aigyminsper.search.search_algorithms import BuscaLargura

LIVRE, OBSTACULO, PEDAGIO = 0, 1, 2
CARREGANDO = "carregando"

CIMA, BAIXO, ESQUERDA, DIREITA = "CIMA", "BAIXO", "ESQUERDA", "DIREITA"
PEGAR, ENTREGAR = "PEGAR", "ENTREGAR"
PAGAR_PEDAGIO = "PAGAR PEDÁGIO"
MOVIMENTOS = {CIMA: (-1, 0), BAIXO: (1, 0), ESQUERDA: (0, -1), DIREITA: (0, 1)}

CUSTO_BASE = 1
ADICIONAL_PEDAGIO = 2


@dataclass
class Mundo:
    n: int
    grid: list
    agente: tuple
    pacote: tuple
    destino: tuple

    def dentro(self, l, c):
        return 0 <= l < self.n and 0 <= c < self.n

    def passavel(self, l, c):
        return self.dentro(l, c) and self.grid[l][c] != OBSTACULO

    def custo_acao(self, l, c):
        return CUSTO_BASE + (ADICIONAL_PEDAGIO if self.grid[l][c] == PEDAGIO else 0)

    @property
    def n_obstaculos(self):
        return sum(v == OBSTACULO for linha in self.grid for v in linha)

    @property
    def n_pedagios(self):
        return sum(v == PEDAGIO for linha in self.grid for v in linha)


def gerar_mundo(n, rng=None):
    if n < 2:
        raise ValueError("A dimensão mínima é 2")
    rng = rng or random
    celulas = [(l, c) for l in range(n) for c in range(n)]
    agente, pacote, destino = rng.sample(celulas, 3)
    especiais = {agente, pacote, destino}
    resto = [p for p in celulas if p not in especiais]
    rng.shuffle(resto)

    n_obst = int(len(resto) * rng.uniform(0.10, 0.32))
    n_ped = int(len(resto) * rng.uniform(0.05, 0.15))

    grid = [[LIVRE] * n for _ in range(n)]
    for (l, c) in resto[:n_obst]:
        grid[l][c] = OBSTACULO
    candidatos = resto[n_obst:] + list(especiais)
    rng.shuffle(candidatos)
    for (l, c) in candidatos[:n_ped]:
        grid[l][c] = PEDAGIO
    return Mundo(n, grid, agente, pacote, destino)


class EntregaState(State):
    def __init__(self, mundo, agente, pacote, pedagio_pago=0, operator="", expandidos=None):
        super().__init__(operator)
        self.mundo = mundo
        self.agente = agente
        self.pacote = pacote
        self.pedagio_pago = pedagio_pago
        self.expandidos = {} if expandidos is None else expandidos

    def _novo(self, operator, agente=None, pacote=None, pedagio_pago=0):
        return EntregaState(self.mundo, agente or self.agente, pacote or self.pacote, pedagio_pago,
                            operator, self.expandidos)

    def successors(self):
        self.expandidos[self.agente] = self.expandidos.get(self.agente, 0) + 1
        l, c = self.agente
        if self.mundo.grid[l][c] == PEDAGIO and self.pedagio_pago < ADICIONAL_PEDAGIO:
            return [self._novo(PAGAR_PEDAGIO, pedagio_pago=self.pedagio_pago + 1)]

        sucessores = []
        for acao, (dl, dc) in MOVIMENTOS.items():
            if self.mundo.passavel(l + dl, c + dc):
                sucessores.append(self._novo(acao, agente=(l + dl, c + dc)))
        if self.pacote == self.agente:
            sucessores.append(self._novo(PEGAR, pacote=CARREGANDO))
        if self.pacote == CARREGANDO and self.agente == self.mundo.destino:
            sucessores.append(self._novo(ENTREGAR, pacote=self.agente))
        return sucessores

    def is_goal(self):
        return self.pacote == self.mundo.destino

    def description(self):
        return f"Entrega de pacote em grid {self.mundo.n}x{self.mundo.n} com obstáculos e pedágios"

    def cost(self):
        return 1

    def env(self):
        return str((self.agente, self.pacote, self.pedagio_pago))


def alcancaveis(mundo, origem):
    vistos = {origem}
    fila = deque([origem])
    while fila:
        l, c = fila.popleft()
        for dl, dc in MOVIMENTOS.values():
            p = (l + dl, c + dc)
            if p not in vistos and mundo.passavel(*p):
                vistos.add(p)
                fila.append(p)
    return vistos


@dataclass
class Resultado:
    plano: list = None
    custo: int = 0
    expandidos: int = 0
    tempo_ms: float = 0.0
    motivo: str = ""
    expandidos_por_celula: dict = field(default_factory=dict)
    regiao_agente: set = field(default_factory=set)

    @property
    def tem_solucao(self):
        return self.plano is not None


def resolver(mundo):
    t0 = time.perf_counter()
    inicial = EntregaState(mundo, mundo.agente, mundo.pacote)
    no = BuscaLargura().search(inicial, pruning="general")

    res = Resultado(expandidos_por_celula=inicial.expandidos)
    res.expandidos = sum(inicial.expandidos.values())
    res.tempo_ms = (time.perf_counter() - t0) * 1000

    if no is None:
        res.regiao_agente = alcancaveis(mundo, mundo.agente)
        if mundo.pacote not in res.regiao_agente:
            res.motivo = "O agente não consegue alcançar o pacote."
        else:
            res.motivo = "O pacote não consegue chegar ao destino."
        return res

    res.custo = no.g
    plano = []
    while no.father_node is not None:
        if no.state.operator != PAGAR_PEDAGIO:
            plano.append(no.state.operator)
        no = no.father_node
    res.plano = plano[::-1]
    return res


def aplicar(mundo, estado, acao):
    l, c, pac = estado
    if acao in MOVIMENTOS:
        dl, dc = MOVIMENTOS[acao]
        if mundo.passavel(l + dl, c + dc):
            l, c = l + dl, c + dc
    elif acao == PEGAR and pac == (l, c):
        pac = CARREGANDO
    elif acao == ENTREGAR and pac == CARREGANDO:
        pac = (l, c)
    return (l, c, pac)


def custo_plano(mundo, plano):
    estado = (*mundo.agente, mundo.pacote)
    total = 0
    for acao in plano:
        total += mundo.custo_acao(estado[0], estado[1])
        estado = aplicar(mundo, estado, acao)
    return total


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    m = gerar_mundo(n)
    simbolos = {LIVRE: ".", OBSTACULO: "#", PEDAGIO: "$"}
    for l in range(n):
        linha = ""
        for c in range(n):
            p = (l, c)
            linha += "A" if p == m.agente else "P" if p == m.pacote else "X" if p == m.destino else simbolos[m.grid[l][c]]
        print(linha)
    r = resolver(m)
    if r.tem_solucao:
        print(f"Custo ótimo: {r.custo} | {len(r.plano)} ações | {r.expandidos} nós | {r.tempo_ms:.1f} ms")
        print(" -> ".join(r.plano))
    else:
        print("SEM SOLUÇÃO:", r.motivo)
