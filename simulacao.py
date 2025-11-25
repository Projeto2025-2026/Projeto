import os
import json
import random
import numpy as np
import heapq
import itertools
import math
from typing import List, Dict, Any, Optional, Tuple

# --- CONSTANTES GLOBAIS ---
FALLBACK_ESP = "clinica_geral"
CHEGADA = "CHEGADA"
SAIDA = "SAIDA"

DOENCA_TO_ESP = {
    "asma": "pneumologia", "bronquite": "pneumologia", "covid": "pneumologia",
    "diabetes": "endocrinologia", "obesidade": "endocrinologia", "angina": "cardiologia",
    "arritmia": "cardiologia", "hipertensão": "cardiologia", "fractura": "ortopedia",
    "queda": "ortopedia", "luxacao": "ortopedia", "febre": "clinica_geral",
    "virose": "clinica_geral", "gripe": "clinica_geral", "otite": "otorrino",
    "rinite": "otorrino", "sinusite": "otorrino", "geriatria_cronica": "geriatria",
}


# --- UTILS E CÁLCULOS ---

class Paciente:
    def __init__(self, id: str, nome: str, idade: Optional[int] = None,
                 profissao: Optional[str] = None, prioridade: str = "normal", **kwargs):
        self.id = id
        self.nome = nome
        self.idade = idade
        self.profissao = profissao
        self.prioridade = "normal" 
        self.sexo = kwargs.get('sexo')
        self.morada = kwargs.get('morada', {}) 
        self.descrição = kwargs.get('descrição')
        self.atributos = kwargs.get('atributos')
        self.religiao = kwargs.get('religiao')
        self.desportos = kwargs.get('desportos')
        
    def __repr__(self):
        return f"{self.nome} ({self.prioridade})"

def carregar_pacientes_json(ficheiro: str, limite: Optional[int] = None) -> List[Paciente]:
    """Carrega todos os pacientes de um ficheiro JSON, procurando por 'id' ou 'cc'."""
    if not os.path.exists(ficheiro):
        print(f"⚠️ Ficheiro {ficheiro} não encontrado. Retornando lista vazia.")
        return []

    data = None
    try:
        with open(ficheiro, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ Erro ao ler {ficheiro}: {e}")
        return []
    
    if data is None:
        return []

    pacientes = []
    for i, p in enumerate(data):
        profissao = str(p.get("profissao", "")).lower()
        is_doctor = "médico" in profissao or "medicina" in profissao
        
        # Tenta obter ID de 'id' ou 'cc'
        patient_id = p.get("id") or p.get("cc") or (i + 1)
        
        if not is_doctor:
            pacientes.append(Paciente(
                id=str(patient_id),
                nome=p.get("nome", f"Pessoa {i+1}"),
                idade=p.get("idade"),
                profissao=p.get("profissao"),
                prioridade="normal", 
                sexo=p.get('sexo'),
                morada=p.get('morada'),
                descrição=p.get('descrição'),
                atributos=p.get('atributos', {}),
                religiao=p.get('religiao'),
                desportos=p.get('desportos')
                ))

    # Importante: A ordem na lista define a ordem de chegada (e o limite de pacientes para simulação)
    random.shuffle(pacientes)
    if limite is not None:
        pacientes = pacientes[:limite]

    print(f"✅ {len(pacientes)} pacientes carregados de {ficheiro}")
    return pacientes

def gera_intervalo_tempo_chegada(taxa, rng: Optional[np.random.Generator] = None):
    if taxa <= 0: return float('inf')
    taxa_por_minuto = taxa / 60.0
    if rng is None: return float(np.random.exponential(1.0 / taxa_por_minuto))
    return float(rng.exponential(1.0 / taxa_por_minuto))

def gera_tempo_consulta(media, distribuicao="exponential", rng: Optional[np.random.Generator] = None):
    val = 0.0
    if distribuicao in ("exponential", "exponencial"):
        if rng is None: val = float(np.random.exponential(scale=media))
        else: val = float(np.random.exponential(scale=media))
    elif distribuicao == "normal":
        if rng is None: val = float(np.random.normal(loc=media, scale=0.2 * media))
        else: val = float(np.random.normal(loc=media, scale=0.2 * media))
        val = max(0.1, val)
    elif distribuicao in ("uniform", "uniforme"):
        if rng is None: val = float(np.random.uniform(low=0.5 * media, high=1.5 * media))
        else: val = float(np.random.uniform(low=0.5 * media, high=1.5 * media))
    else: raise ValueError("Distribuição inválida")
    return val

def calcular_estatisticas(sim) -> dict:
    
    ii = 0
    while ii < len(sim._medicos):
        m = sim._medicos[ii]
        tempos = m.get("tempos_consulta", []) or []
        num_att = m.get("num_atendidos", 0)
        total_ocup = m.get("total_tempo_ocupado", 0.0)
        media_cons = float(np.mean(tempos)) if len(tempos) > 0 else 0.0
        p90 = float(np.percentile(tempos, 90)) if len(tempos) > 0 else 0.0
        
        ocup_percent = 100.0 * total_ocup / max(1.0, float(sim.simulation_time))
        tempo_ocioso = max(0.0, float(sim.simulation_time) - total_ocup)
        
        sim.stats_por_medico[ii] = {
            "id": m.get("id"), "especialidade": m.get("especialidade"),
            "num_atendidos": num_att, "tempo_ocioso": tempo_ocioso,
            "ocupacao_percent": ocup_percent, "media_consulta": media_cons, "p90_consulta": p90,
        }
        ii += 1

    tempos_esp_arr = np.array(sim.tempos_espera) if len(sim.tempos_espera) > 0 else np.array([0.0])
    tempos_cons_arr = np.array(sim.tempos_consulta) if len(sim.tempos_consulta) > 0 else np.array([0.0])
    fila_arr = np.array(sim.fila_sizes) if len(sim.fila_sizes) > 0 else np.array([0])
    ocup_arr = np.array(sim.ocupacao_medicos) if len(sim.ocupacao_medicos) > 0 else np.array([0.0])
    
    sim.stats_geral = {
        "tempo_medio_espera": float(np.mean(tempos_esp_arr)),
        "tempo_p95_espera": float(np.percentile(tempos_esp_arr, 95)),
        "tempo_medio_consulta": float(np.mean(tempos_cons_arr)),
        "fila_media": float(np.mean(fila_arr)),
        "fila_max": int(np.max(fila_arr)) if fila_arr.size > 0 else 0,
        "ocupacao_media_medicos": float(np.mean(ocup_arr)),
        "doentes_atendidos": int(sim.doentes_atendidos)
    }

    return {
        "tempo_medio_espera": sim.stats_geral["tempo_medio_espera"],
        "variancia_tempo_espera": (float(np.var(tempos_esp_arr)) if len(tempos_esp_arr)>1 else 0.0),
        "tempo_medio_consulta": sim.stats_geral["tempo_medio_consulta"],
        "variancia_tempo_consulta": (float(np.var(tempos_cons_arr)) if len(tempos_cons_arr)>1 else 0.0),
        "tempo_medio_na_clinica": float(np.mean(sim.tempos_clinica)) if sim.tempos_clinica else 0.0,
        "fila_media": sim.stats_geral["fila_media"],
        "fila_max": sim.stats_geral["fila_max"],
        "ocupacao_media_medicos": sim.stats_geral["ocupacao_media_medicos"],
        "doentes_atendidos": sim.stats_geral["doentes_atendidos"],
        "stats_por_medico": sim.stats_por_medico 
    }

# --- MOTOR DE SIMULAÇÃO (SimulacaoClinica) ---

class SimulacaoClinica:
    def __init__(self, **kwargs):
        self.lambda_rate = float(kwargs.get('lambda_rate', 10))
        self.num_doctors = int(kwargs.get('num_doctors', 3))
        self.service_distribution = kwargs.get('service_distribution', "exponential")
        self.mean_service_time = float(kwargs.get('mean_service_time', 15))
        self.simulation_time = int(kwargs.get('simulation_time', 480))
        self.seed = kwargs.get('seed')
        self.arrival_pattern = kwargs.get('arrival_pattern', "homogeneous")
        self.arrival_profile = kwargs.get('arrival_profile')
        self.pacientes: List[Paciente] = kwargs.get('pacientes', [])
        self.doctor_specialties = kwargs.get('doctor_specialties', {})
        self.reset()

    def reset(self):
        self.tempos_espera: List[float] = []
        self.tempos_consulta: List[float] = []
        self.tempos_clinica: List[float] = []

        self.fila_sizes: List[int] = []
        self.ocupacao_medicos: List[float] = []
        self.eventos: List[Dict[str, Any]] = []
        self.distritos_pacientes: List[str] = []

        self.doentes_atendidos = 0
        self.stats_por_medico: Dict[int, Dict[str, Any]] = {}
        self.stats_geral: Dict[str, Any] = {}

        self._rng = np.random.default_rng(self.seed)
        self._heap: List[Tuple[float, int, str, str]] = []
        self._counter = itertools.count()

        self._chegada: Dict[str, float] = {}
        self._inicio: Dict[str, float] = {}
        self._saida: Dict[str, float] = {}
        self._duracao: Dict[str, float] = {}
        # O ID do paciente (pid) mapeia para o índice na lista self.pacientes
        self._pid_to_pidx: Dict[str, int] = {} 

        self._medicos: List[Dict[str, Any]] = []
        i = 0
        while i < self.num_doctors:
            esp = self.doctor_specialties.get(str(i), FALLBACK_ESP)
            self._medicos.append({
                "id": i,
                "livre": True,
                "fim": 0.0,
                "especialidade": esp, 
                "last_event_time": 0.0,
                "total_tempo_ocupado": 0.0,
                "num_atendidos": 0,
                "tempos_consulta": []
            })
            i += 1

        # FIX: Fila simplificada, sem distinção de prioridade
        self._filas: Dict[str, List[str]] = {} 
        self._pid_counter = 1
        
    def _gera_intervalo_chegada_homogeneo(self) -> float:
        if not self.pacientes: return float('inf') 
        return gera_intervalo_tempo_chegada(self.lambda_rate, rng=self._rng)

    def _gera_chegadas_nonhomogeneous(self):
        if not self.pacientes: return 
        
        profile = self.arrival_profile
        if profile is None:
            profile = [
                (0, 120, 5.0), (120, 300, 15.0),
                (300, 420, 25.0), (420, self.simulation_time, 10.0)
            ]

        pid_ctr = self._pid_counter
        pidx = 0
        for bloco in profile:
            start_min, end_min, lam = bloco
            
            is_valid_block = end_min > start_min and lam > 0
            
            if is_valid_block:
                t = float(start_min)
                taxa_min = lam / 60.0
                
                while t < end_min and pidx < len(self.pacientes):
                    intervalo = float(self._rng.exponential(1.0 / taxa_min))
                    t = t + intervalo
                    
                    if t < end_min and pidx < len(self.pacientes):
                        pid = f"p{pid_ctr}"
                        pid_ctr += 1
                        self._chegada[pid] = t
                        heapq.heappush(self._heap, (t, next(self._counter), CHEGADA, pid))
                        self._pid_to_pidx[pid] = pidx
                        pidx += 1
                        
        self._pid_counter = pid_ctr

    def _gera_chegadas_homogeneo(self):
        if not self.pacientes: return 
        
        t = float(self._gera_intervalo_chegada_homogeneo())
        pid_ctr = self._pid_counter
        pidx = 0
        while t < self.simulation_time and pidx < len(self.pacientes):
            pid = f"p{pid_ctr}"
            pid_ctr += 1
            self._chegada[pid] = t
            heapq.heappush(self._heap, (t, next(self._counter), CHEGADA, pid))
            self._pid_to_pidx[pid] = pidx
            pidx += 1
            t = t + float(self._gera_intervalo_chegada_homogeneo())
        self._pid_counter = pid_ctr
    
    def _gera_tempo_consulta_local(self, especialidade: Optional[str], paciente_idx: Optional[int]) -> float:
        # FIX: O tempo de serviço agora depende APENAS do input do utilizador (mean_service_time)
        mean = self.mean_service_time
        return gera_tempo_consulta(mean, self.service_distribution, rng=self._rng)

    def _detectar_doenca_e_prioridade(self, p: Dict[str, Any]) -> Tuple[str, str, str]:
        doenca = None; prioridade = "normal"; prioridade_motivo = []; nota_clinica = []

        if isinstance(p, dict):
            doenca = p.get("doenca", p.get("descrição")); 
            if isinstance(doenca, str): doenca = doenca.lower()
            
            # 1. Notas Clínicas/Alertas (sem implicar urgência na fila)
            if str(p.get('religiao', '')).lower() == 'testemunhas de jeová': nota_clinica.append("Restrição de Transfusão de Sangue")
            if str(p.get('atributos', {}).get('fumador')).lower() == 'true': nota_clinica.append("Alerta: Fumador")

            # Prioridade de fila é sempre 'normal'
            prioridade = "normal"

            if doenca is None or not doenca:
                doenca = "virose"

        else: doenca = "virose"

        if doenca is None or not doenca: doenca = "virose"
        
        # O motivo clínico agora é uma lista concisa de notas
        motivo_str = f"{', '.join(prioridade_motivo + nota_clinica)}" if prioridade_motivo or nota_clinica else "Sem Nota Clínica"
            
        return doenca.lower(), prioridade, motivo_str

    def _doenca_para_especialidade(self, doenca: str) -> str:
        if doenca in DOENCA_TO_ESP: return DOENCA_TO_ESP[doenca]
        if "cardio" in doenca or "angina" in doenca or "hipertens" in doenca or "arritm" in doenca: return "cardiologia"
        if "pneumo" in doenca or "asma" in doenca or "bronq" in doenca: return "pneumologia"
        if "diabet" in doenca or "endocrinologia" in doenca: return "endocrinologia"
        if "fract" in doenca or "queda" in doenca or "ortop" in doenca: return "ortopedia"
        if "otit" in doenca or "rinite" in doenca or "otorr" in doenca: return "otorrino"
        if "geriatria" in doenca: return "geriatria"
        return FALLBACK_ESP

    def run(self):
        self.reset()
        
        # FIX: Verifica se há pacientes carregados (Obrigatoriedade do Dataset)
        if not self.pacientes:
            print("❌ Simulação abortada: Sem pacientes carregados. Verifique o dataset.")
            return

        if self.arrival_pattern == "nonhomogeneous": self._gera_chegadas_nonhomogeneous()
        else: self._gera_chegadas_homogeneo()

        # FIX: Inicialização da fila simplificada
        self._filas[FALLBACK_ESP] = [] 

        while self._heap:
            tempo, _, tipo, pid = heapq.heappop(self._heap)
            
            if tipo == CHEGADA:
                pidx = self._pid_to_pidx.get(pid, None)
                
                if pidx is not None and pidx < len(self.pacientes): 
                    pdata = self.pacientes[pidx]
                    p_info = pdata.__dict__ if not isinstance(pdata, dict) else pdata
                    doenca, prioridade, motivo_str = self._detectar_doenca_e_prioridade(p_info)

                    especialidade_req = self._doenca_para_especialidade(doenca)

                    if pdata.morada and pdata.morada.get('distrito'): self.distritos_pacientes.append(pdata.morada['distrito'])
                    else: self.distritos_pacientes.append("Desconhecido")
                        
                    # FIX: Inicialização da fila simplificada
                    if especialidade_req not in self._filas: self._filas[especialidade_req] = []

                    medico_idx = None
                    j = 0
                    found_compatible_doctor = False
                    
                    # Procura 1: Compatível e Livre
                    while j < len(self._medicos):
                        m = self._medicos[j]
                        is_compatible = (m["especialidade"] == especialidade_req) or (m["especialidade"] == FALLBACK_ESP)
                        
                        if m["livre"] and is_compatible and not found_compatible_doctor: 
                            medico_idx = j
                            found_compatible_doctor = True 
                        
                        j += 1
                    
                    # Procura 2: Generalista Livre (Fallback), se ainda não encontrou
                    k = 0
                    if not found_compatible_doctor:
                        found_fallback_doctor = False
                        while k < len(self._medicos):
                            m2 = self._medicos[k]
                            if m2["livre"] and m2["especialidade"] == FALLBACK_ESP and not found_fallback_doctor: 
                                medico_idx = k
                                found_fallback_doctor = True
                            k += 1

                    if medico_idx is not None:
                        # Paciente ATENDIDO IMEDIATAMENTE
                        dur = self._gera_tempo_consulta_local(especialidade_req, pidx)
                        
                        if dur <= 0.001: dur = self.mean_service_time 
                            
                        self._inicio[pid] = tempo; self._duracao[pid] = dur; self._medicos[medico_idx]["livre"] = False; self._medicos[medico_idx]["fim"] = tempo + dur
                        self._medicos[medico_idx]["num_atendidos"] += 1; self._medicos[medico_idx]["tempos_consulta"].append(dur)
                        heapq.heappush(self._heap, (tempo + dur, next(self._counter), SAIDA, pid))
                        
                        nome = pdata.nome
                        ev = {"minuto_inicio": int(math.floor(tempo)), "duracao": dur, "medico": medico_idx, "paciente": f"{nome} ({motivo_str})", "especialidade": especialidade_req, "prioridade": prioridade, "motivo": motivo_str}
                        self.eventos.append(ev)
                        
                        self._medicos[medico_idx]["last_event_time"] = tempo
                    else:
                        # Paciente VAI PARA A FILA (FIFO)
                        self._filas[especialidade_req].append(pid)
                        
                        nome = pdata.nome
                        self.eventos.append({"minuto_inicio": int(math.floor(tempo)), "duracao": 0.0, "medico": None, "paciente": f"{nome} ({motivo_str})", "especialidade": especialidade_req, "prioridade": prioridade, "motivo": motivo_str})
            

            elif tipo == SAIDA:
                found_idx = None
                kk = 0
                doctor_found = False
                while kk < len(self._medicos) and not doctor_found:
                    m = self._medicos[kk]
                    if (not m["livre"]) and (abs(m["fim"] - tempo) <= 1e-4): 
                        found_idx = kk
                        doctor_found = True
                    kk += 1

                self._saida[pid] = tempo; self.doentes_atendidos += 1

                if found_idx is not None:
                    dur_local = self._duracao.get(pid, 0.0); self._medicos[found_idx]["total_tempo_ocupado"] += dur_local; self._medicos[found_idx]["livre"] = True
                    self._medicos[found_idx]["last_event_time"] = tempo

                    esp_med = self._medicos[found_idx].get("especialidade", FALLBACK_ESP); prox_pid = None; keys = sorted(list(self._filas.keys())) 
                    
                    found_next_patient = False
                    
                    # 1. Tenta encontrar na fila da especialidade do médico (FIFO)
                    if esp_med in self._filas and len(self._filas[esp_med]) > 0: 
                        prox_pid = self._filas[esp_med].pop(0) # FIFO
                        found_next_patient = True
                        
                    # 2. Tenta encontrar na fila de outras especialidades (FIFO)
                    i2 = 0
                    while i2 < len(keys) and not found_next_patient:
                        kf = keys[i2]
                        if kf != esp_med and len(self._filas.get(kf, [])) > 0: 
                            prox_pid = self._filas[kf].pop(0) # FIFO
                            found_next_patient = True
                        i2 += 1
                    
                    # 3. Tenta encontrar na fila do FALLBACK (FIFO)
                    if not found_next_patient and FALLBACK_ESP in self._filas and len(self._filas[FALLBACK_ESP]) > 0:
                        prox_pid = self._filas[FALLBACK_ESP].pop(0)
                        found_next_patient = True


                    if prox_pid is not None:
                        # Próximo paciente INICIA ATENDIMENTO
                        pidx2 = self._pid_to_pidx.get(prox_pid, None)
                        pdata2 = self.pacientes[pidx2] if pidx2 is not None and pidx2 < len(self.pacientes) else None
                        p_info2 = pdata2.__dict__ if pdata2 is not None and not isinstance(pdata2, dict) else (pdata2 if pdata2 is not None else {})
                        doenca2, prioridade2, motivo_str2 = self._detectar_doenca_e_prioridade(p_info2)
                        
                        esp_final = self._doenca_para_especialidade(doenca2); dur2 = self._gera_tempo_consulta_local(esp_final, pidx2)
                        if dur2 <= 0.001: dur2 = self.mean_service_time 

                        self._inicio[prox_pid] = tempo; self._duracao[prox_pid] = dur2; self._medicos[found_idx]["livre"] = False; self._medicos[found_idx]["fim"] = tempo + dur2
                        self._medicos[found_idx]["num_atendidos"] += 1; self._medicos[found_idx]["tempos_consulta"].append(dur2)
                        heapq.heappush(self._heap, (tempo + dur2, next(self._counter), SAIDA, prox_pid))
                        
                        nome2 = pdata2.nome if pdata2 else "Paciente desconhecido (ERRO)"
                        self.eventos.append({"minuto_inicio": int(math.floor(tempo)), "duracao": dur2, "medico": found_idx, "paciente": f"{nome2} ({motivo_str2})", "especialidade": esp_final, "prioridade": prioridade2, "motivo": motivo_str2})
                    else:
                        pass
            
        # O cálculo das filas e ocupação continua aqui
        minuto = 0
        while minuto < self.simulation_time:
            chegada_count = 0; inicio_count = 0
            keys_cheg = list(self._chegada.keys()); ik = 0
            while ik < len(keys_cheg):
                pk = keys_cheg[ik]; tcheg = self._chegada.get(pk, float('inf')); tin = self._inicio.get(pk)
                if tcheg <= minuto:
                    chegada_count += 1
                    if tin is not None and tin <= minuto: inicio_count += 1
                ik += 1
            fila_atual = chegada_count - inicio_count
            if fila_atual < 0: fila_atual = 0
            self.fila_sizes.append(fila_atual)
            
            ocup = 0; mm = 0
            while mm < len(self._medicos):
                med = self._medicos[mm]
                if med.get("fim", 0.0) > minuto and not med.get("livre", True): ocup += 1
                mm += 1
                
            porc = 100.0 * ocup / max(1, self.num_doctors)
            if porc < 0.0: porc = 0.0
            if porc > 100.0: porc = 100.0
            self.ocupacao_medicos.append(porc); minuto += 1

        pid_keys = list(self._inicio.keys()); ppi = 0
        while ppi < len(pid_keys):
            pid = pid_keys[ppi]; tinicio = self._inicio.get(pid); tchegada = self._chegada.get(pid)
            tsaida = self._saida.get(pid); dur = self._duracao.get(pid, 0.0) 
            espera = 0.0
            if tinicio is not None and tchegada is not None: espera = max(0.0, tinicio - tchegada) 
            total = 0.0
            if tsaida is not None and tchegada is not None: total = max(0.0, tsaida - tchegada)
            else: total = espera + dur
            self.tempos_espera.append(espera); self.tempos_consulta.append(dur); self.tempos_clinica.append(total)
            ppi += 1

        calcular_estatisticas(self) 
        
        return {
            "tempos_espera": self.tempos_espera, "tempos_consulta": self.tempos_consulta,
            "fila_sizes": self.fila_sizes, "ocupacao_medicos": self.ocupacao_medicos,
            "stats_por_medico": self.stats_por_medico, "stats_geral": self.stats_geral,
            "distritos_pacientes": self.distritos_pacientes
        }
