import os
import json
import random
import numpy as np
from typing import List, Optional

DATA_FILE = "pessoas.json"

class Paciente:
    """Representa uma pessoa da base de dados (pode vir a ser um paciente)."""
    def __init__(self, id: str, nome: str, idade: Optional[int] = None, profissao: Optional[str] = None):
        self.id = id
        self.nome = nome
        self.idade = idade
        self.profissao = profissao

    def __repr__(self):
        return f"{self.nome} ({self.idade or '?'} anos, {self.profissao or 'sem profissão'})"

def carregar_pacientes_json(ficheiro: str = DATA_FILE, limite: Optional[int] = 200) -> List[Paciente]:
    """
    Lê o ficheiro pessoas.json e devolve uma lista de objetos Paciente.
    Filtra apenas pessoas que não são médicos (ou seja, pacientes potenciais).
    """
    if not os.path.exists(ficheiro):
        print(f"⚠️ Ficheiro {ficheiro} não encontrado. Retornando lista vazia.")
        return []

    try:
        with open(ficheiro, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ Erro ao ler {ficheiro}: {e}")
        return []

    pacientes = []
    for i, p in enumerate(data):
        nome = p.get("nome") or f"Pessoa {i+1}"
        profissao = str(p.get("profissao", "")).lower()
        # ignorar médicos
        if "médico" in profissao or "medicina" in profissao:
            continue
        pacientes.append(Paciente(
            id=str(p.get("id", i + 1)),
            nome=nome,
            idade=p.get("idade"),
            profissao=p.get("profissao"),
        ))

    # baralhar e aplicar limite
    random.shuffle(pacientes)
    if limite:
        pacientes = pacientes[:limite]

    print(f"✅ {len(pacientes)} pacientes carregados de {ficheiro}")
    return pacientes


# Geradores de tempos (mantidos)
def gera_intervalo_tempo_chegada(taxa):
    """Gera o intervalo de chegada (em minutos) com base na taxa λ."""
    if taxa <= 0:
        return float('inf')
    taxa_por_minuto = taxa / 60.0
    return float(np.random.exponential(1.0 / taxa_por_minuto))

def gera_tempo_consulta(media, distribuicao="exponential"):
    """Gera a duração de uma consulta segundo a distribuição escolhida."""
    if distribuicao in ("exponential", "exponencial"):
        return float(np.random.exponential(scale=media))
    elif distribuicao == "normal":
        return max(0.1, float(np.random.normal(loc=media, scale=0.2 * media)))
    elif distribuicao in ("uniform", "uniforme"):
        return float(np.random.uniform(low=0.5 * media, high=1.5 * media))
    else:
        raise ValueError("Distribuição inválida")
