import heapq
import itertools
import math
import numpy as np
from typing import List, Dict, Any, Optional
from utils import gera_tempo_consulta, carregar_pacientes_json

CHEGADA = "CHEGADA"
SAIDA = "SAIDA"

class SimulacaoClinica:
    """
    Simulação por eventos discretos de uma clínica médica.
    Parâmetros:
      - lambda_rate: taxa de chegada de pacientes (pacientes/hora)
      - num_doctors: número de médicos simultaneamente disponíveis
      - service_distribution: tipo de distribuição dos tempos de consulta
      - mean_service_time: tempo médio de consulta (minutos)
      - simulation_time: duração total da simulação (minutos)
      - pacientes: lista opcional de objetos Paciente (com nome)
    """

    def __init__(self,
                 lambda_rate: float = 10,
                 num_doctors: int = 3,
                 service_distribution: str = "exponential",
                 mean_service_time: float = 15,
                 simulation_time: int = 480,
                 seed: Optional[int] = None,
                 pacientes: Optional[List[Any]] = None):
        self.lambda_rate = float(lambda_rate)
        self.num_doctors = int(num_doctors)
        self.service_distribution = service_distribution
        self.mean_service_time = float(mean_service_time)
        self.simulation_time = int(simulation_time)
        self.seed = seed
        self.pacientes = pacientes or carregar_pacientes_json(limite=200)
        self.reset()

    # ------------------------------------------------------------------

    def reset(self):
        """Reinicializa variáveis da simulação."""
        self.tempos_espera: List[float] = []
        self.tempos_consulta: List[float] = []
        self.tempos_clinica: List[float] = []
        self.fila_sizes: List[int] = []
        self.ocupacao_medicos: List[float] = []
        self.eventos: List[Dict[str, Any]] = []
        self.doentes_atendidos = 0

        # Estado interno
        self._rng = np.random.default_rng(self.seed)
        self._heap = []  # fila de eventos
        self._counter = itertools.count()

        # Dicionários de tempos
        self._chegada: Dict[str, float] = {}
        self._inicio: Dict[str, float] = {}
        self._saida: Dict[str, float] = {}
        self._duracao: Dict[str, float] = {}

        # Lista de médicos
        self._medicos = [{"id": i, "livre": True, "fim": 0.0} for i in range(self.num_doctors)]

    # ------------------------------------------------------------------

    def _gera_intervalo_chegada(self) -> float:
        """Intervalo de tempo entre chegadas (minutos)."""
        if self.lambda_rate <= 0:
            return float('inf')
        taxa_min = self.lambda_rate / 60.0  # pacientes por minuto
        return float(self._rng.exponential(1.0 / taxa_min))

    def _gera_tempo_consulta(self) -> float:
        """Duração da consulta (minutos)."""
        return float(gera_tempo_consulta(self.mean_service_time, self.service_distribution))

    def _medico_livre(self) -> Optional[int]:
        """Retorna o índice de um médico livre, ou None se todos ocupados."""
        for i, m in enumerate(self._medicos):
            if m["livre"]:
                return i
        return None

    # ------------------------------------------------------------------

    def run(self):
        """Executa a simulação."""
        self.reset()

        # Gera todas as chegadas
        t = self._gera_intervalo_chegada()
        pid_counter = 1
        while t < self.simulation_time:
            pid = f"p{pid_counter}"
            pid_counter += 1
            self._chegada[pid] = t
            heapq.heappush(self._heap, (t, next(self._counter), CHEGADA, pid))
            t += self._gera_intervalo_chegada()

        # Preparar fila de espera
        fila: List[str] = []

        # Índice para associar nomes reais
        prox_idx = 0
        total_pacientes = len(self.pacientes)

        # Loop por minuto
        for minuto in range(self.simulation_time):
            limite = minuto + 1.0
            while self._heap and self._heap[0][0] <= limite:
                tempo, _, tipo, pid = heapq.heappop(self._heap)

                if tipo == CHEGADA:
                    # Tenta arranjar médico livre
                    idx = self._medico_livre()
                    if idx is not None:
                        dur = self._gera_tempo_consulta()
                        self._inicio[pid] = tempo
                        self._duracao[pid] = dur
                        self._medicos[idx]["livre"] = False
                        self._medicos[idx]["fim"] = tempo + dur
                        heapq.heappush(self._heap, (tempo + dur, next(self._counter), SAIDA, pid))

                        # Nome real do paciente
                        nome = None
                        if prox_idx < total_pacientes:
                            nome = self.pacientes[prox_idx].nome
                            prox_idx += 1

                        self.eventos.append({
                            "minuto_inicio": int(math.floor(tempo)),
                            "duracao": dur,
                            "medico": idx,
                            "paciente": nome
                        })
                    else:
                        fila.append(pid)

                elif tipo == SAIDA:
                    # Liberta o médico
                    for m in self._medicos:
                        if not m["livre"] and math.isclose(m["fim"], tempo, rel_tol=1e-4):
                            m["livre"] = True
                            break
                    self._saida[pid] = tempo
                    self.doentes_atendidos += 1

                    # Se houver alguém à espera, atende o próximo
                    if fila:
                        prox_pid = fila.pop(0)
                        dur = self._gera_tempo_consulta()
                        self._inicio[prox_pid] = tempo
                        self._duracao[prox_pid] = dur
                        m["livre"] = False
                        m["fim"] = tempo + dur
                        heapq.heappush(self._heap, (tempo + dur, next(self._counter), SAIDA, prox_pid))

                        nome = None
                        if prox_idx < total_pacientes:
                            nome = self.pacientes[prox_idx].nome
                            prox_idx += 1

                        self.eventos.append({
                            "minuto_inicio": int(math.floor(tempo)),
                            "duracao": dur,
                            "medico": m["id"],
                            "paciente": nome
                        })

            # Estado por minuto
            self.fila_sizes.append(len(fila))
            ocupados = sum(not m["livre"] for m in self._medicos)
            self.ocupacao_medicos.append(100.0 * ocupados / max(1, self.num_doctors))

        # Estatísticas finais
        for pid, tinicio in self._inicio.items():
            tchegada = self._chegada.get(pid)
            tsaida = self._saida.get(pid)
            dur = self._duracao.get(pid, 0)
            espera = max(0, tinicio - tchegada)
            total = (tsaida - tchegada) if tsaida is not None else (espera + dur)
            self.tempos_espera.append(espera)
            self.tempos_consulta.append(dur)
            self.tempos_clinica.append(total)

        return {
            "tempos_espera": self.tempos_espera,
            "tempos_consulta": self.tempos_consulta,
            "tempos_clinica": self.tempos_clinica,
            "fila_sizes": self.fila_sizes,
            "ocupacao_medicos": self.ocupacao_medicos,
            "doentes_atendidos": self.doentes_atendidos,
            "eventos": self.eventos,
        }
