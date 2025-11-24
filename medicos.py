# medicos.py
from datetime import datetime, timedelta
from typing import List

class Medico:
    def __init__(self, id: str, nome: str):
        self.id = id
        self.nome = nome
        self.agenda: List[dict] = []
        self.num_atendidos = 0
        self.tempo_ocupado = 0.0

    def livre(self, inicio: datetime, duracao: int) -> bool:
        fim = inicio + timedelta(minutes=duracao)
        return all(fim <= c["inicio"] or inicio >= c["fim"] for c in self.agenda)

    def agendar(self, paciente_id: str, inicio: datetime, duracao: int) -> bool:
        if self.livre(inicio, duracao):
            self.agenda.append({"paciente_id": paciente_id, "inicio": inicio, "fim": inicio + timedelta(minutes=duracao)})
            self.num_atendidos += 1
            self.tempo_ocupado += duracao
            return True
        return False
