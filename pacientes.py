# pacientes.py
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

DATA_DIR = "data"
PACIENTES_FILE = os.path.join(DATA_DIR, "pacientes.json")

class Atendimento:
    def __init__(self, timestamp: Optional[str] = None, duracao_min: Optional[float] = None,
                 espera_min: Optional[float] = None, medico_id: Optional[str] = None):
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.duracao_min = duracao_min
        self.espera_min = espera_min
        self.medico_id = medico_id

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Atendimento":
        return Atendimento(**d)

class Paciente:
    def __init__(self, id: str, nome: str):
        self.id = id
        self.nome = nome
        self.historico: List[Atendimento] = []

    def adicionar_atendimento(self, duracao_min=None, espera_min=None, medico_id=None):
        self.historico.append(Atendimento(duracao_min=duracao_min, espera_min=espera_min, medico_id=medico_id))

def carregar_pacientes(limit: int = 100) -> List[Paciente]:
    if not os.path.exists(PACIENTES_FILE):
        return []
    with open(PACIENTES_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            return []
    res = []
    for i, p in enumerate(data[:limit]):
        pid = p.get("id", f"p{i+1}")
        nome = p.get("nome", f"Pessoa {i+1}")
        pac = Paciente(str(pid), str(nome))
        # carregar histórico se existir
        hist = p.get("historico", [])
        for a in hist:
            pac.historico.append(Atendimento.from_dict(a) if isinstance(a, dict) else Atendimento())
        res.append(pac)
    return res

def guardar_pacientes(pacientes: List[Paciente]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PACIENTES_FILE, "w", encoding="utf-8") as f:
        json.dump([{"id": p.id, "nome": p.nome, "historico":[a.to_dict() for a in p.historico]} for p in pacientes], f, indent=2, ensure_ascii=False)
