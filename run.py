import math
import os
import random

os.environ.setdefault("SDL_FRAMEBUFFER_ACCELERATION", "0")

import pygame

from problema import (CARREGANDO, DIREITA, ENTREGAR, ESQUERDA, MOVIMENTOS, OBSTACULO, PEDAGIO,
                      PEGAR, aplicar, gerar_mundo, resolver)

LARGURA, ALTURA = 1180, 800
AREA_GRID = 740
MARGEM = 30
PAINEL_X = MARGEM * 2 + AREA_GRID
PAINEL_W = LARGURA - PAINEL_X - MARGEM
N_MIN, N_MAX = 3, 40
VELOCIDADES = [0.5, 1, 2, 4, 8, 16]

FUNDO = (13, 15, 34)
FUNDO2 = (22, 26, 58)
PAINEL = (24, 28, 62)
PAINEL_BORDA = (60, 70, 140)
PISO_A = (40, 47, 92)
PISO_B = (45, 53, 101)
PEDAGIO_COR = (128, 132, 156)
OURO = (255, 205, 60)
OURO_ESCURO = (200, 140, 20)
CIANO = (70, 225, 255)
LARANJA = (255, 150, 50)
VERMELHO = (255, 70, 90)
VERDE = (80, 235, 140)
ROXO = (170, 110, 255)
BRANCO = (240, 242, 255)
CINZA = (150, 156, 190)
CAIXA = (230, 160, 60)
CAIXA_ESCURA = (170, 105, 30)
CONFETE = [VERDE, OURO, CIANO, VERMELHO, ROXO, BRANCO]
COR_ACAO = {PEGAR: OURO, ENTREGAR: VERDE}


def fonte(tam, negrito=True):
    caminho = pygame.font.match_font("dejavusans,arial,liberationsans", bold=negrito)
    return pygame.font.Font(caminho, tam)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_cor(a, b, t):
    return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))


def suave(t):
    return t * t * (3 - 2 * t)


def texto(sup, f, s, cor, pos, ancora="topleft", sombra=True):
    img = f.render(s, True, cor)
    r = img.get_rect(**{ancora: pos})
    if sombra:
        sup.blit(f.render(s, True, (0, 0, 0)), r.move(2, 2))
    sup.blit(img, r)


class Particula:
    def __init__(self, x, y, cor, vel, vida, tam, grav):
        ang = random.uniform(0, math.tau)
        v = random.uniform(0.3, 1.0) * vel
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(ang) * v, math.sin(ang) * v - vel * 0.4
        self.cor, self.vida, self.vida0, self.tam, self.grav = cor, vida, vida, tam, grav

    def atualizar(self, dt):
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += self.grav * dt * 60
        self.vida -= dt
        return self.vida > 0

    def desenhar(self, sup):
        t = max(1, int(self.tam * (0.4 + 0.6 * self.vida / self.vida0)))
        w = max(1, int(abs(math.cos(self.vida * 8)) * t * 2))
        pygame.draw.rect(sup, self.cor, (self.x - w / 2, self.y - t / 2, w, t))


class TextoFlutuante:
    def __init__(self, x, y, s, cor, f):
        self.x, self.y, self.s, self.cor, self.f = x, y, s, cor, f
        self.vida = 1.1

    def atualizar(self, dt):
        self.y -= 38 * dt
        self.vida -= dt
        return self.vida > 0

    def desenhar(self, sup):
        alpha = int(255 * min(1, self.vida / 0.5))
        for cor, d in (((0, 0, 0), 2), (self.cor, 0)):
            img = self.f.render(self.s, True, cor)
            img.set_alpha(alpha)
            sup.blit(img, img.get_rect(center=(self.x + d, self.y + d)))


class Botao:
    def __init__(self, rect, rotulo, cor, acao):
        self.rect, self.rotulo, self.cor, self.acao = pygame.Rect(rect), rotulo, cor, acao

    def desenhar(self, sup, f):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        base = lerp_cor(self.cor, BRANCO, 0.25) if hover else self.cor
        pygame.draw.rect(sup, lerp_cor(self.cor, (0, 0, 0), 0.55), self.rect.move(0, 4), border_radius=10)
        r = self.rect.move(0, -2 if hover else 0)
        pygame.draw.rect(sup, base, r, border_radius=10)
        pygame.draw.rect(sup, lerp_cor(base, BRANCO, 0.35), (r.x + 6, r.y + 3, r.w - 12, 4), border_radius=2)
        texto(sup, f, self.rotulo, BRANCO, r.center, "center")


def desenhar_parede(sup, r):
    s = r.w
    topo = max(2, s // 7)
    pygame.draw.rect(sup, (10, 10, 18), r)
    pygame.draw.rect(sup, (52, 52, 70), (r.x, r.y, s, topo))
    if s >= 14:
        h = max(4, s // 4)
        for i, y in enumerate(range(r.y + topo, r.bottom, h)):
            pygame.draw.line(sup, (28, 28, 42), (r.x, y), (r.right - 1, y))
            for x in range(r.x + (s // 2) * (i % 2), r.right, s // 2 + 1):
                pygame.draw.line(sup, (28, 28, 42), (x, y), (x, min(y + h, r.bottom - 1)))
    pygame.draw.rect(sup, (0, 0, 0), r, 1)


def desenhar_pedagio(sup, r, t, f_moeda=None):
    s = r.w
    pygame.draw.rect(sup, PEDAGIO_COR, r)
    sup.set_clip(r)
    for k in range(-s, s * 2, max(6, s // 3)):
        pygame.draw.line(sup, (98, 102, 126), (r.x + k, r.y), (r.x + k - s, r.bottom), max(1, s // 12))
    sup.set_clip(None)
    raio = max(3, s // 5)
    cx, cy = r.right - raio - 3, r.y + raio + 3
    larg = max(1, int(abs(math.cos(t * 3 + r.x * 0.1)) * raio))
    pygame.draw.ellipse(sup, OURO_ESCURO, (cx - larg, cy - raio + 1, larg * 2, raio * 2))
    pygame.draw.ellipse(sup, OURO, (cx - larg, cy - raio, larg * 2, raio * 2))
    if f_moeda and larg > raio * 0.6:
        texto(sup, f_moeda, "$", OURO_ESCURO, (cx, cy), "center", sombra=False)


def desenhar_destino(sup, r, t):
    cx, cy = r.center
    s = r.w
    pulso = 0.5 + 0.5 * math.sin(t * 4)
    halo = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
    pygame.draw.circle(halo, (*VERMELHO, int(40 + 50 * pulso)), (s, s), int(s * (0.36 + 0.12 * pulso)))
    sup.blit(halo, (cx - s, cy - s))
    k, w = s * 0.28, max(3, s // 7)
    for d in (1, -1):
        a, b = (cx - k, cy - d * k), (cx + k, cy + d * k)
        pygame.draw.line(sup, (90, 0, 20), (a[0] + 2, a[1] + 2), (b[0] + 2, b[1] + 2), w + 1)
        pygame.draw.line(sup, VERMELHO, a, b, w)


def desenhar_caixa(sup, cx, cy, s):
    s = int(s)
    borda = max(2, s // 14)
    r = pygame.Rect(0, 0, s * 0.62, s * 0.52)
    r.center = (cx, cy)
    pygame.draw.ellipse(sup, (20, 20, 40), (r.x + 2, r.bottom - 3, r.w - 4, max(3, s // 9)))
    pygame.draw.rect(sup, CAIXA_ESCURA, r.move(0, 2), border_radius=borda)
    pygame.draw.rect(sup, CAIXA, r, border_radius=borda)
    pygame.draw.rect(sup, lerp_cor(CAIXA, BRANCO, 0.2), (r.x, r.y, r.w, r.h * 0.3), border_radius=borda)
    fw = max(2, int(s * 0.1))
    pygame.draw.rect(sup, (250, 220, 150), (r.centerx - fw // 2, r.y, fw, r.h))
    pygame.draw.rect(sup, CAIXA_ESCURA, r, max(1, s // 30), border_radius=borda)


def desenhar_agente(sup, cx, cy, s, t, carregando=False, direcao=1, andando=False):
    s = int(s)
    quica = abs(math.sin(t * 14)) * s * 0.08 if andando else math.sin(t * 3) * s * 0.025
    cy -= quica
    pygame.draw.ellipse(sup, (10, 12, 30), (cx - s * 0.28, cy + s * 0.3 + quica, s * 0.56, s * 0.13))
    corpo = pygame.Rect(0, 0, s * 0.46, s * 0.36)
    corpo.center = (cx, cy + s * 0.14)
    pygame.draw.rect(sup, (30, 90, 200), corpo.move(0, 2), border_radius=max(2, s // 8))
    pygame.draw.rect(sup, (50, 130, 255), corpo, border_radius=max(2, s // 8))
    perna = s * 0.03 * math.sin(t * 14) if andando else 0
    for lado in (-1, 1):
        pygame.draw.rect(sup, (25, 30, 70), (cx + lado * s * 0.1 - s * 0.05, corpo.bottom - 2 - lado * perna,
                                             s * 0.1, s * 0.1))
    raio = s * 0.19
    hy = cy - s * 0.12
    pygame.draw.circle(sup, (255, 210, 170), (cx, hy), raio)
    pygame.draw.ellipse(sup, VERMELHO, (cx - raio, hy - raio * 1.05, raio * 2, raio * 1.2))
    pygame.draw.ellipse(sup, (200, 40, 60), (cx + direcao * raio * 0.7 - raio * 0.4,
                                             hy - raio * 0.25, raio * 1.3, raio * 0.4))
    for lado in (-1, 1):
        olho = (cx + direcao * raio * 0.25 + lado * raio * 0.38, hy + raio * 0.2)
        pygame.draw.circle(sup, (20, 20, 40), olho, max(1, s // 30))
    if carregando:
        desenhar_caixa(sup, cx, cy - s * 0.48, s * 0.75)


def desenhar_icone_acao(sup, acao, cx, cy, s, cor):
    if acao in MOVIMENTOS:
        dl, dc = MOVIMENTOS[acao]
        seta = [(1, 0), (-0.2, 1), (-0.2, 0.4), (-1, 0.4), (-1, -0.4), (-0.2, -0.4), (-0.2, -1)]
        pygame.draw.polygon(sup, cor, [(cx + s * (a * dc - b * dl), cy + s * (a * dl + b * dc)) for a, b in seta])
    elif acao == PEGAR:
        pygame.draw.rect(sup, cor, (cx - s, cy - s * 0.7, s * 2, s * 1.5), border_radius=2)
        pygame.draw.line(sup, PAINEL, (cx, cy - s * 0.7), (cx, cy + s * 0.8), 2)
    else:
        pygame.draw.lines(sup, cor, False, [(cx - s, cy), (cx - s * 0.2, cy + s * 0.8), (cx + s, cy - s * 0.8)], 3)


class Jogo:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Entregador BFS")
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        self.relogio = pygame.time.Clock()
        self.f_titulo, self.f_grande, self.f_media = fonte(64), fonte(40), fonte(22)
        self.f, self.f_peq, self.f_mini = fonte(17), fonte(13, negrito=False), fonte(11)
        self.t = 0.0
        self.cena = "menu"
        self.n = 10
        self.vel = 1
        self.particulas = []
        self.textos = []
        self.tremor = 0.0
        self.mostrar_calor = False
        self.mostrar_caminho = True
        self.arrastando = None
        self.mao = False
        self.mouse = (0, 0)
        self.fundo = pygame.Surface((LARGURA, ALTURA))
        for y in range(ALTURA):
            pygame.draw.line(self.fundo, lerp_cor(FUNDO, FUNDO2, y / ALTURA), (0, y), (LARGURA, y))

        cx = LARGURA // 2
        self.botoes_menu = [
            Botao((cx - 190, 380, 70, 70), "-", (190, 60, 90), lambda: self.mudar_n(-1)),
            Botao((cx + 120, 380, 70, 70), "+", (40, 160, 90), lambda: self.mudar_n(1)),
            Botao((cx - 150, 600, 300, 70), "JOGAR", (230, 120, 30), self.novo_mundo),
        ]
        bw = PAINEL_W // 2 - 5
        self.botao_play = Botao((PAINEL_X, 622, bw, 40), "PLAY", (40, 160, 90), self.alternar_play)
        self.botoes_jogo = [
            self.botao_play,
            Botao((PAINEL_X + bw + 10, 622, bw, 40), "PASSO", (60, 90, 190), self.um_passo),
            Botao((PAINEL_X, 674, bw, 40), "NOVO MUNDO", (150, 70, 200), self.novo_mundo),
            Botao((PAINEL_X + bw + 10, 674, bw, 40), "MENU", (90, 95, 130), self.ir_menu),
        ]
        self.teclas_menu = {
            pygame.K_LEFT: lambda: self.mudar_n(-1), pygame.K_DOWN: lambda: self.mudar_n(-1),
            pygame.K_RIGHT: lambda: self.mudar_n(1), pygame.K_UP: lambda: self.mudar_n(1),
            pygame.K_RETURN: self.novo_mundo, pygame.K_SPACE: self.novo_mundo,
        }
        self.teclas_jogo = {
            pygame.K_SPACE: self.alternar_play, pygame.K_RIGHT: self.um_passo,
            pygame.K_r: self.novo_mundo, pygame.K_m: self.ir_menu, pygame.K_ESCAPE: self.ir_menu,
            pygame.K_h: lambda: setattr(self, "mostrar_calor", not self.mostrar_calor),
            pygame.K_c: lambda: setattr(self, "mostrar_caminho", not self.mostrar_caminho),
            pygame.K_UP: lambda: self.mudar_vel(1), pygame.K_EQUALS: lambda: self.mudar_vel(1),
            pygame.K_PLUS: lambda: self.mudar_vel(1), pygame.K_KP_PLUS: lambda: self.mudar_vel(1),
            pygame.K_DOWN: lambda: self.mudar_vel(-1), pygame.K_MINUS: lambda: self.mudar_vel(-1),
            pygame.K_KP_MINUS: lambda: self.mudar_vel(-1),
        }

    def explodir(self, x, y, cores, qtd, vel, vida, tam, grav=0.15):
        for _ in range(qtd):
            self.particulas.append(Particula(x, y, random.choice(cores), vel, vida * random.uniform(0.6, 1.2),
                                             tam, grav))

    def flutuar(self, x, y, s, cor, f):
        self.textos.append(TextoFlutuante(x, y, s, cor, f))

    def ret(self, l, c):
        return pygame.Rect(self.ox + c * self.cel, self.oy + l * self.cel, self.cel, self.cel)

    def centro(self, l, c):
        return self.ret(l, c).center

    def novo_mundo(self):
        self.particulas.clear()
        self.textos.clear()
        self.mundo = m = gerar_mundo(self.n)
        self.cel = min(110, AREA_GRID // self.n)
        tam = self.cel * self.n
        self.ox = MARGEM + (AREA_GRID - tam) // 2
        self.oy = (ALTURA - tam) // 2
        self.f_moeda = fonte(self.cel // 5) if self.cel >= 22 else None
        self.f_float = fonte(max(14, min(28, self.cel // 2)))
        self.cena = "jogo"
        self.arrastando = None
        self.resolver_mundo()
        self.explodir(*self.centro(*m.agente), [CIANO, BRANCO, ROXO], 25, 4, 0.8, 4, 0)

    def resolver_mundo(self):
        m = self.mundo
        self.res = resolver(m)
        self.plano = self.res.plano or []
        self.estados = [(*m.agente, m.pacote)]
        for acao in self.plano:
            self.estados.append(aplicar(m, self.estados[-1], acao))
        self.reiniciar()
        if not self.res.tem_solucao:
            self.tremor = 0.2

    def celula_em(self, pos):
        l, c = (pos[1] - self.oy) // self.cel, (pos[0] - self.ox) // self.cel
        return (l, c) if self.mundo.dentro(l, c) else None

    def item_em(self, cel):
        l, c, pac = self.estados[self.passo]
        if cel == (l, c):
            return "agente"
        if cel == pac:
            return "pacote"
        if cel == self.mundo.destino:
            return "destino"
        return None

    def pode_soltar(self, cel):
        if cel is None or self.mundo.grid[cel[0]][cel[1]] == OBSTACULO:
            return False
        outros = [getattr(self.mundo, k) for k in ("agente", "pacote", "destino") if k != self.arrastando]
        return cel not in outros

    def pegar_item(self, pos):
        cel = self.celula_em(pos)
        item = cel and self.item_em(cel)
        if not item:
            return False
        self.reiniciar()
        self.arrastando = item
        return True

    def soltar_item(self, pos):
        cel = self.celula_em(pos)
        if self.pode_soltar(cel) and cel != getattr(self.mundo, self.arrastando):
            setattr(self.mundo, self.arrastando, cel)
            self.resolver_mundo()
            self.explodir(*self.centro(*cel), [CIANO, BRANCO, OURO], 20, 4, 0.6, 4, 0)
        self.arrastando = None

    def reiniciar(self):
        self.passo = 0
        self.progresso = None
        self.custo = 0
        self.tocando = False
        self.direcao = 1
        self.fase = "jogando" if self.res.tem_solucao else "sem_solucao"

    def ir_menu(self):
        self.cena = "menu"

    def mudar_n(self, d):
        self.n = max(N_MIN, min(N_MAX, self.n + d))
        self.explodir(LARGURA // 2, 415, [OURO, CIANO] if d > 0 else [VERMELHO, ROXO], 12, 4, 0.5, 4, 0)

    def mudar_vel(self, d):
        self.vel = max(0, min(len(VELOCIDADES) - 1, self.vel + d))

    def alternar_play(self):
        if self.fase == "concluido":
            self.reiniciar()
            self.tocando = True
        elif self.fase == "jogando":
            self.tocando = not self.tocando

    def um_passo(self):
        self.tocando = False
        self.iniciar_passo()

    def iniciar_passo(self):
        if self.fase != "jogando" or self.progresso is not None:
            return
        acao = self.plano[self.passo]
        l, c, _ = self.estados[self.passo]
        custo = self.mundo.custo_acao(l, c)
        self.custo += custo
        self.progresso = 0.0
        self.direcao = {ESQUERDA: -1, DIREITA: 1}.get(acao, self.direcao)
        x, y = self.centro(l, c)
        self.flutuar(x, y - self.cel * 0.5, f"+{custo}", OURO if custo > 1 else BRANCO, self.f_float)
        if custo > 1:
            self.explodir(x, y, [OURO, OURO_ESCURO], 10, 3, 0.6, 4)
            self.tremor = 0.12
        if acao == PEGAR:
            self.flutuar(x, y - self.cel, "PEGOU!", OURO, self.f_media)
            self.explodir(x, y, [OURO, CAIXA, BRANCO], 35, 5, 0.9, 5)

    def terminar_passo(self):
        acao = self.plano[self.passo]
        self.progresso = None
        self.passo += 1
        if acao == ENTREGAR:
            x, y = self.centro(*self.mundo.destino)
            self.flutuar(x, y - self.cel, "ENTREGUE!", VERDE, self.f_media)
            self.explodir(x, y, CONFETE, 120, 9, 2.2, 7)
            for _ in range(6):
                self.explodir(random.randint(self.ox, self.ox + self.cel * self.n), self.oy, CONFETE, 25, 4, 2.5, 6)
            self.tremor = 0.35
        if self.passo == len(self.plano):
            self.fase = "concluido"
            self.tocando = False

    def atualizar(self, dt):
        self.t += dt
        self.tremor = max(0, self.tremor - dt)
        self.particulas = [p for p in self.particulas if p.atualizar(dt)]
        self.textos = [x for x in self.textos if x.atualizar(dt)]
        mao = self.cena == "jogo" and bool(self.arrastando or self.item_em(self.celula_em(self.mouse)))
        if mao != self.mao:
            self.mao = mao
            try:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if mao else pygame.SYSTEM_CURSOR_ARROW)
            except pygame.error:
                pass
        if self.cena != "jogo":
            return
        if self.progresso is not None:
            self.progresso += dt * VELOCIDADES[self.vel] * 4
            if self.progresso >= 1:
                self.terminar_passo()
        if self.tocando:
            self.iniciar_passo()

    def eventos(self):
        no_menu = self.cena == "menu"
        teclas = self.teclas_menu if no_menu else self.teclas_jogo
        botoes = self.botoes_menu if no_menu else self.botoes_jogo
        for ev in pygame.event.get():
            if hasattr(ev, "pos"):
                self.mouse = ev.pos
            if ev.type == pygame.QUIT or (no_menu and ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                return False
            if ev.type == pygame.KEYDOWN and ev.key in teclas:
                teclas[ev.key]()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if not no_menu and self.pegar_item(ev.pos):
                    continue
                for b in botoes:
                    if b.rect.collidepoint(ev.pos):
                        b.acao()
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.arrastando:
                self.soltar_item(ev.pos)
            elif ev.type == pygame.MOUSEWHEEL and no_menu:
                self.mudar_n(ev.y)
        return True

    def desenhar(self):
        self.tela.blit(self.fundo, (0, 0))
        if self.cena == "menu":
            self.desenhar_menu()
        else:
            k = self.tremor * 18
            camada = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            self.desenhar_grid(camada)
            self.tela.blit(camada, (random.uniform(-k, k), random.uniform(-k, k)))
            self.desenhar_painel()
            if self.arrastando:
                self.desenhar_arrasto()
            elif self.fase == "sem_solucao":
                self.desenhar_banner("SEM SOLUÇÃO", self.res.motivo, VERMELHO)
            elif self.fase == "concluido":
                self.desenhar_banner("ENTREGA CONCLUÍDA!",
                                     f"Custo ótimo {self.custo}  •  {len(self.plano)} ações", VERDE)
        for efeito in self.particulas + self.textos:
            efeito.desenhar(self.tela)
        pygame.display.flip()

    def desenhar_menu(self):
        t, cx, s = self.t, LARGURA // 2, 46
        for i in range(-1, LARGURA // s + 2):
            for j in range(-1, ALTURA // s + 2):
                v = math.sin(i * 0.7 + j * 1.3 + t) * 0.3 + 0.3
                pygame.draw.rect(self.tela, lerp_cor(FUNDO, (34, 40, 86), v),
                                 (i * s + (t * 20) % s, j * s + (t * 12) % s, s - 3, s - 3), 1, border_radius=4)
        balanco = math.sin(t * 2) * 6
        texto(self.tela, self.f_titulo, "ENTREGADOR", OURO, (cx, 130 + balanco), "center")
        texto(self.tela, self.f_titulo, "BFS", CIANO, (cx, 200 - balanco), "center")
        texto(self.tela, self.f_media, "plano ótimo com busca em largura (aigyminsper)", CINZA,
              (cx, 260), "center", sombra=False)
        desenhar_agente(self.tela, cx - 300, 165, 110, t, andando=True)
        desenhar_caixa(self.tela, cx + 300, 165 + math.sin(t * 3) * 6, 110)

        texto(self.tela, self.f_media, "DIMENSÃO DO GRID", BRANCO, (cx, 345), "center")
        caixa = pygame.Rect(cx - 105, 375, 210, 80)
        pygame.draw.rect(self.tela, PAINEL, caixa, border_radius=14)
        pygame.draw.rect(self.tela, PAINEL_BORDA, caixa, 3, border_radius=14)
        texto(self.tela, self.f_grande, f"{self.n} × {self.n}", BRANCO, caixa.center, "center")
        ps = 90 / self.n
        for i in range(self.n):
            for j in range(self.n):
                pygame.draw.rect(self.tela, PISO_A if (i + j) % 2 else PISO_B,
                                 (cx - 45 + j * ps, 465 + i * ps, math.ceil(ps), math.ceil(ps)))
        texto(self.tela, self.f_mini, f"{self.n * self.n} células", CINZA, (cx, 569), "center", sombra=False)
        for b in self.botoes_menu:
            b.desenhar(self.tela, self.f_grande if b.rotulo in "+-" else self.f_media)

        legenda = [
            ("Agente", lambda r: desenhar_agente(self.tela, r.centerx, r.centery + 3, r.w, t)),
            ("Pacote", lambda r: desenhar_caixa(self.tela, *r.center, r.w)),
            ("Destino", lambda r: desenhar_destino(self.tela, r, t)),
            ("Obstáculo", lambda r: desenhar_parede(self.tela, r)),
            ("Pedágio (+2)", lambda r: desenhar_pedagio(self.tela, r, t)),
        ]
        for k, (nome, icone) in enumerate(legenda):
            r = pygame.Rect(cx - 425 + k * 170, 704, 32, 32)
            pygame.draw.rect(self.tela, PISO_A, r)
            icone(r)
            texto(self.tela, self.f, nome, BRANCO, (r.right + 8, r.centery), "midleft")
        texto(self.tela, self.f_peq, "←/→ muda a dimensão  •  ENTER para começar  •  ESC sai", CINZA,
              (cx, ALTURA - 22), "center", sombra=False)

    def desenhar_grid(self, sup):
        m, cel, t, res = self.mundo, self.cel, self.t, self.res
        moldura = pygame.Rect(self.ox - 8, self.oy - 8, cel * m.n + 16, cel * m.n + 16)
        pygame.draw.rect(sup, (8, 10, 24), moldura.move(0, 6), border_radius=12)
        pygame.draw.rect(sup, PAINEL_BORDA, moldura, border_radius=12)
        pygame.draw.rect(sup, (16, 18, 40), moldura.inflate(-6, -6), border_radius=10)

        max_calor = max(res.expandidos_por_celula.values(), default=1)
        for l in range(m.n):
            for c in range(m.n):
                r = self.ret(l, c)
                if m.grid[l][c] == OBSTACULO:
                    desenhar_parede(sup, r)
                    continue
                if m.grid[l][c] == PEDAGIO:
                    desenhar_pedagio(sup, r, t, self.f_moeda)
                else:
                    pygame.draw.rect(sup, PISO_A if (l + c) % 2 else PISO_B, r)
                if self.fase == "sem_solucao":
                    alcancavel = (l, c) in res.regiao_agente
                    pygame.draw.rect(sup, (60, 200, 255, 40) if alcancavel else (120, 20, 40, 110), r)
                if self.mostrar_calor and (l, c) in res.expandidos_por_celula:
                    q = res.expandidos_por_celula[(l, c)] / max_calor
                    pygame.draw.rect(sup, (*lerp_cor(ROXO, LARANJA, q), int(40 + 100 * q)), r)
                pygame.draw.rect(sup, (30, 35, 72), r, 1)

        trilha = [self.centro(l, c) for l, c, _ in self.estados[:self.passo + 1]]
        if len(trilha) > 1:
            pygame.draw.lines(sup, (255, 255, 255, 60), False, trilha, max(2, cel // 6))
        if self.mostrar_caminho and self.fase == "jogando" and not self.arrastando:
            self.desenhar_caminho(sup)
        if self.arrastando != "destino":
            desenhar_destino(sup, self.ret(*m.destino), t)

        atual = self.estados[self.passo]
        ax, ay = self.centro(atual[0], atual[1])
        visual, andando = atual, False
        if self.progresso is not None:
            prox = self.estados[self.passo + 1]
            e = suave(min(1, self.progresso))
            bx, by = self.centro(prox[0], prox[1])
            ax, ay = lerp(ax, bx, e), lerp(ay, by, e)
            andando = self.plano[self.passo] in MOVIMENTOS
            if self.progresso > 0.5:
                visual = prox
        pac = visual[2]
        if pac != CARREGANDO and self.arrastando != "pacote":
            x, y = self.centro(*pac)
            bob = 0 if pac == m.destino else math.sin(t * 3) * cel * 0.04
            desenhar_caixa(sup, x, y + bob, cel)
        if self.arrastando != "agente":
            desenhar_agente(sup, ax, ay, cel, t, pac == CARREGANDO, self.direcao, andando)

    def desenhar_arrasto(self):
        mx, my = self.mouse
        cel = self.celula_em(self.mouse)
        if cel:
            r = self.ret(*cel)
            cor = VERDE if self.pode_soltar(cel) else VERMELHO
            marca = pygame.Surface(r.size, pygame.SRCALPHA)
            marca.fill((*cor, 70))
            self.tela.blit(marca, r)
            pygame.draw.rect(self.tela, cor, r, 3)
        s = int(self.cel * 1.15)
        if self.arrastando == "agente":
            desenhar_agente(self.tela, mx, my, s, self.t, andando=True)
        elif self.arrastando == "pacote":
            desenhar_caixa(self.tela, mx, my, s)
        else:
            desenhar_destino(self.tela, pygame.Rect(mx - s // 2, my - s // 2, s, s), self.t)

    def desenhar_caminho(self, sup):
        raio = max(2, min(6, self.cel // 9))
        for a, b in zip(self.estados[self.passo:], self.estados[self.passo + 1:]):
            if a[:2] == b[:2]:
                continue
            cor = LARANJA if a[2] == CARREGANDO else CIANO
            (x0, y0), (x1, y1) = self.centro(a[0], a[1]), self.centro(b[0], b[1])
            for k in range(3):
                f = (k / 3 + self.t * 1.2) % 1
                pygame.draw.circle(sup, (*cor, 200), (lerp(x0, x1, f), lerp(y0, y1, f)), raio)

    def card(self, y, h, titulo=None):
        r = pygame.Rect(PAINEL_X, y, PAINEL_W, h)
        pygame.draw.rect(self.tela, (8, 10, 24), r.move(0, 4), border_radius=12)
        pygame.draw.rect(self.tela, PAINEL, r, border_radius=12)
        pygame.draw.rect(self.tela, PAINEL_BORDA, r, 2, border_radius=12)
        if titulo:
            texto(self.tela, self.f_mini, titulo, CINZA, (r.x + 14, r.y + 10), sombra=False)
        return r

    def desenhar_painel(self):
        m, res, tela, x = self.mundo, self.res, self.tela, PAINEL_X
        texto(tela, self.f_grande, "ENTREGADOR", OURO, (x, 22))
        texto(tela, self.f_media, "BFS", CIANO, (x + PAINEL_W, 36), "topright")

        if self.fase == "sem_solucao":
            status, cor = "SEM SOLUÇÃO", VERMELHO
        elif self.fase == "concluido":
            status, cor = "ENTREGUE!", VERDE
        elif self.estados[self.passo][2] == CARREGANDO:
            status, cor = "LEVANDO O PACOTE", LARANJA
        else:
            status, cor = "INDO BUSCAR O PACOTE", CIANO
        r = self.card(80, 46)
        pulso = 0.5 + 0.5 * math.sin(self.t * 5)
        pygame.draw.circle(tela, lerp_cor(cor, BRANCO, pulso * 0.4), (r.x + 22, r.centery), 7)
        texto(tela, self.f_media, status, cor, (r.x + 40, r.centery), "midleft")

        r = self.card(138, 112, "CUSTO ACUMULADO")
        if res.tem_solucao:
            pygame.draw.circle(tela, OURO_ESCURO, (r.x + 32, r.y + 65), 22)
            pygame.draw.circle(tela, OURO, (r.x + 32, r.y + 62), 22)
            pygame.draw.circle(tela, OURO_ESCURO, (r.x + 32, r.y + 62), 15, 2)
            texto(tela, self.f_grande, str(self.custo), OURO, (r.x + 62, r.y + 62), "midleft")
            texto(tela, self.f_media, f"/ {res.custo}", CINZA, (r.right - 16, r.y + 62), "midright")
            barra = pygame.Rect(r.x + 14, r.bottom - 22, r.w - 28, 10)
            pygame.draw.rect(tela, (12, 14, 32), barra, border_radius=5)
            prog = self.passo / len(self.plano)
            if prog > 0:
                barra.w = max(10, barra.w * prog)
                pygame.draw.rect(tela, lerp_cor(CIANO, VERDE, prog), barra, border_radius=5)
        else:
            texto(tela, self.f_grande, "∞", VERMELHO, (r.centerx, r.y + 62), "center")

        r = self.card(262, 112, "ESTATÍSTICAS")
        stats = [
            ("Grid", f"{m.n} × {m.n}"),
            ("Obstáculos / Pedágios", f"{m.n_obstaculos} / {m.n_pedagios}"),
            ("Passo", f"{self.passo} / {len(self.plano)}"),
            ("Nós expandidos (BFS)", f"{res.expandidos}  ({res.tempo_ms:.1f} ms)"),
        ]
        for i, (nome, valor) in enumerate(stats):
            y = r.y + 32 + i * 19
            texto(tela, self.f_peq, nome, CINZA, (r.x + 14, y), sombra=False)
            texto(tela, self.f_peq, valor, BRANCO, (r.right - 14, y), "topright", sombra=False)

        r = self.card(386, 222, "AÇÕES")
        if res.tem_solucao:
            atual = self.passo if self.progresso is not None else self.passo - 1
            ini = max(0, min(self.passo - 3, len(self.plano) - 9))
            for i, acao in enumerate(self.plano[ini:ini + 9], ini):
                y = r.y + 30 + (i - ini) * 21
                if i == atual:
                    pygame.draw.rect(tela, (50, 60, 120), (r.x + 8, y - 2, r.w - 16, 20), border_radius=6)
                cor = COR_ACAO.get(acao, CIANO)
                if i > atual:
                    cor = lerp_cor(cor, PAINEL, 0.6)
                l, c, _ = self.estados[i]
                pedagio = m.grid[l][c] == PEDAGIO
                texto(tela, self.f_peq, f"{i + 1:>3}", CINZA, (r.x + 14, y), sombra=False)
                desenhar_icone_acao(tela, acao, r.x + 58, y + 8, 7, cor)
                texto(tela, self.f, acao, cor, (r.x + 76, y - 1), sombra=False)
                texto(tela, self.f_peq, f"+{m.custo_acao(l, c)}" + (" $" if pedagio else ""),
                      OURO if pedagio else CINZA, (r.right - 14, y), "topright", sombra=False)
        else:
            linhas = [res.motivo, "", "Azul: região alcançável pelo agente.", "Vermelho: fora de alcance.",
                      "", "Aperte R para gerar outro mundo."]
            for i, linha in enumerate(linhas):
                texto(tela, self.f_peq, linha, VERMELHO if i == 0 else CINZA, (r.x + 14, r.y + 34 + i * 20),
                      sombra=False)

        self.botao_play.rotulo = "REPLAY" if self.fase == "concluido" else "PAUSE" if self.tocando else "PLAY"
        for b in self.botoes_jogo:
            b.desenhar(tela, self.f)

        for dx, cor, nome in ((0, CIANO, "até o pacote"), (114, LARANJA, "até o destino"),
                              (230, PEDAGIO_COR, "pedágio +2")):
            pygame.draw.circle(tela, cor, (x + dx + 6, ALTURA - 66), 4)
            texto(tela, self.f_mini, nome, CINZA, (x + dx + 14, ALTURA - 66), "midleft", sombra=False)
        ligado = {True: "on", False: "off"}
        texto(tela, self.f_peq, "ESPAÇO play   → passo   R novo   M menu", CINZA,
              (x + PAINEL_W // 2, ALTURA - 47), "center", sombra=False)
        texto(tela, self.f_peq, f"vel {VELOCIDADES[self.vel]:g}x (+/-)   H calor {ligado[self.mostrar_calor]}   "
              f"C caminho {ligado[self.mostrar_caminho]}", CINZA, (x + PAINEL_W // 2, ALTURA - 31), "center",
              sombra=False)
        texto(tela, self.f_peq, "arraste o agente, o pacote ou o X para movê-los", CINZA,
              (x + PAINEL_W // 2, ALTURA - 15), "center", sombra=False)

    def desenhar_banner(self, titulo, sub, cor):
        tam = self.cel * self.mundo.n
        w = min(tam - 20, 560)
        r = pygame.Rect(0, 0, w, 130)
        r.center = (self.ox + tam // 2, self.oy + tam // 2)
        fundo = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (10, 12, 30, 225), fundo.get_rect(), border_radius=18)
        self.tela.blit(fundo, r)
        pygame.draw.rect(self.tela, cor, r, 4, border_radius=18)
        texto(self.tela, self.f_grande if w > 420 else self.f_media, titulo, cor, (r.centerx, r.centery - 22),
              "center")
        texto(self.tela, self.f, sub, BRANCO, (r.centerx, r.centery + 22), "center")
        dica = "R novo mundo  •  arraste as peças" + ("  •  ESPAÇO replay" if self.fase == "concluido" else "")
        texto(self.tela, self.f_mini, dica, CINZA, (r.centerx, r.centery + 48), "center", sombra=False)

    def rodar(self):
        while self.eventos():
            self.atualizar(min(self.relogio.tick(60) / 1000, 0.05))
            self.desenhar()
        pygame.quit()


if __name__ == "__main__":
    Jogo().rodar()
