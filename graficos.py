# graficos.py
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import List

def embed_plot_on_frame(frame, fig):
    canvas = FigureCanvasTkAgg(fig, frame)
    widget = canvas.get_tk_widget()
    widget.pack(expand=True, fill="both")
    canvas.draw()
    return canvas

def grafico_tempo_espera_frame(frame, tempos_espera):
    fig, ax = plt.subplots(figsize=(6,4))
    ax.hist(tempos_espera, bins=20)
    ax.set_title("Distribuição dos tempos de espera")
    ax.set_xlabel("Minutos")
    ax.set_ylabel("Nº de pacientes")
    fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_tempo_total_frame(frame, tempos_total):
    fig, ax = plt.subplots(figsize=(6,4))
    ax.hist(tempos_total, bins=20)
    ax.set_title("Tempo total na clínica")
    ax.set_xlabel("Minutos")
    ax.set_ylabel("Nº de pacientes")
    fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_ocupacao_frame(frame, ocupacao):
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(ocupacao)
    ax.set_title("Ocupação dos médicos (%) ao longo do tempo")
    ax.set_xlabel("Minutos")
    ax.set_ylabel("% Ocupação")
    fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_fila_frame(frame, filas):
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(filas)
    ax.set_title("Tamanho da fila ao longo do tempo")
    ax.set_xlabel("Minutos")
    ax.set_ylabel("Tamanho da fila")
    fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_fila_vs_taxa_frame(frame, taxas, medias_fila):
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(taxas, medias_fila, marker='o')
    ax.set_title("Fila média vs Taxa de chegada")
    ax.set_xlabel("Taxa (pacientes/h)")
    ax.set_ylabel("Tamanho médio da fila")
    fig.tight_layout()
    return embed_plot_on_frame(frame, fig)
