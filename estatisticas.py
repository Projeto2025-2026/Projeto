# estatisticas.py
from typing import List, Tuple
import math

def tempo_medio(tempos: List[float]) -> float:
    if not tempos:
        return 0.0
    return sum(tempos)/len(tempos)

def variancia(tempos: List[float]) -> float:
    if not tempos:
        return 0.0
    m = tempo_medio(tempos)
    return sum((x - m)**2 for x in tempos) / len(tempos)

def tamanho_fila(filas: List[int]) -> Tuple[float,int]:
    if not filas:
        return 0.0, 0
    return sum(filas)/len(filas), max(filas)

def calcular_estatisticas(sim) -> dict:
    return {
        "tempo_medio_espera": tempo_medio(sim.tempos_espera),
        "variancia_tempo_espera": variancia(sim.tempos_espera),
        "tempo_medio_consulta": tempo_medio(sim.tempos_consulta),
        "variancia_tempo_consulta": variancia(sim.tempos_consulta),
        "tempo_medio_na_clinica": tempo_medio(sim.tempos_clinica),
        "fila_media": tamanho_fila(sim.fila_sizes)[0],
        "fila_max": tamanho_fila(sim.fila_sizes)[1],
        "ocupacao_media_medicos": tempo_medio(sim.ocupacao_medicos),
        "doentes_atendidos": sim.doentes_atendidos
    }
