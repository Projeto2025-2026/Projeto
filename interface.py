import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import threading
import traceback
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
from collections import Counter
from simulacao import SimulacaoClinica, carregar_pacientes_json, calcular_estatisticas, Paciente


# --- 1. FUNÇÕES DE PLOTAGEM (Melhoradas e Essenciais) ---

def embed_plot_on_frame(frame, fig):
    canvas = FigureCanvasTkAgg(fig, frame)
    widget = canvas.get_tk_widget()
    widget.pack(expand=True, fill="both")
    canvas.draw()
    return canvas

def grafico_distritos_bar(frame, distritos_pacientes):
    fig, ax = plt.subplots(figsize=(6, 4))
    
    if distritos_pacientes and len(distritos_pacientes) > 0:
        contagens = Counter(distritos_pacientes)
        distritos = list(contagens.keys())
        valores = list(contagens.values())
        
        distritos_ordenados, valores_ordenados = zip(*sorted(zip(distritos, valores), key=lambda x: x[1], reverse=True))

        top_n = 10
        ax.bar(list(distritos_ordenados[:top_n]), list(valores_ordenados[:top_n]), color='skyblue', edgecolor='black')
        
        ax.set_title(f"Distribuição de Pacientes por Distrito (Top {top_n})")
        
    else:
        ax.text(0.5, 0.5, "Nenhum dado de distrito registado na simulação.", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        ax.set_title("Distribuição de Pacientes por Distrito")
        
    ax.set_xlabel("Distrito"); ax.set_ylabel("Nº de Pacientes"); plt.xticks(rotation=45, ha='right'); fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_tempo_espera_frame(frame, tempos_espera):
    fig, ax = plt.subplots(figsize=(6,4))
    if len(tempos_espera) > 0 and np.sum(tempos_espera) > 0.01:
        ax.hist(tempos_espera, bins=20, edgecolor='black')
        ax.set_xlim(left=0)
    else:
        ax.text(0.5, 0.5, "Aumente λ ou Duração da simulação para gerar tempos de espera.", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
    ax.set_title("Distribuição dos Tempos de Espera"); ax.set_xlabel("Minutos"); ax.set_ylabel("Nº de Pacientes"); fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_tempo_total_frame(frame, tempos_total):
    fig, ax = plt.subplots(figsize=(6,4))
    if len(tempos_total) > 0 and np.sum(tempos_total) > 0.01:
        ax.hist(tempos_total, bins=20, edgecolor='black'); ax.set_xlim(left=0)
    else:
        ax.text(0.5, 0.5, "Corra a simulação para gerar dados de tempo total.", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
    ax.set_title("Tempo Total na Clínica"); ax.set_xlabel("Minutos"); ax.set_ylabel("Nº de Pacientes"); fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_ocupacao_frame(frame, ocupacao):
    # Gráfico ESSENCIAL: Evolução da taxa de ocupação dos médicos ao longo do tempo da simulação
    fig, ax = plt.subplots(figsize=(6,4))
    if len(ocupacao) > 0: ax.plot(ocupacao)
    ax.set_title("Evolução da Taxa de Ocupação dos Médicos (%)"); ax.set_xlabel("Minutos"); ax.set_ylabel("% Ocupação"); ax.set_ylim(0, 100); fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_fila_frame(frame, filas):
    # Gráfico ESSENCIAL: Evolução do tamanho da fila de espera ao longo do tempo da simulação
    fig, ax = plt.subplots(figsize=(6,4))
    if len(filas) > 0: ax.plot(filas)
    ax.set_title("Evolução do Tamanho da Fila de Espera"); ax.set_xlabel("Minutos"); ax.set_ylabel("Tamanho da Fila"); ax.set_ylim(bottom=0); fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_fila_vs_taxa_frame(frame, taxas, medias_fila):
    # Gráfico ESSENCIAL: Gráfico mostrando a relação do tamanho médio da fila de espera com a taxa de chegada de doentes
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(taxas, medias_fila, marker='o', color='blue'); ax.set_title("Comparação: Fila Média vs. Taxa de Chegada (λ)"); ax.set_xlabel("Taxa de Chegada (pacientes/h)"); ax.set_ylabel("Tamanho Médio da Fila"); ax.grid(True, linestyle='--', alpha=0.7); fig.tight_layout()
    return embed_plot_on_frame(frame, fig)

def grafico_ocupacao_medicos_bar(frame, med_stats):
    # Gráfico de Ocupação Média por Médico (Métrica por Médico)
    OCUPADO_COR = "#00A86B" 
    ids = [f"Médico {i+1}\n({s['especialidade'].title()})" for i, s in med_stats.items()]
    ocupacoes = [s['ocupacao_percent'] for s in med_stats.values()]
    
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(ids, ocupacoes, color=[OCUPADO_COR if o > 0 else '#adb5bd' for o in ocupacoes])
    ax.set_title("Ocupação Média por Médico"); ax.set_ylabel("Percentagem de Ocupação (%)"); ax.set_ylim(0, 100); fig.tight_layout()
    return embed_plot_on_frame(frame, fig)


# --- CLASSE APP (INTERFACE) ---

class App(tk.Tk):
    def __init__(self, initial_params):
        super().__init__()
        self.title("Simulação Clínica - Versão Final")
        self.geometry("1100x720")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
        # --- FIX: Métodos ligados a self para evitar AttributeError ---
        self.iniciar_simulacao = self._iniciar_simulacao
        self.parar_animacao = self._parar_animacao
        self.abrir_graficos_abas = self._abrir_graficos_abas
        self.carregar_dataset_dialog = self._carregar_dataset_dialog
        self.comparar_taxas = self._comparar_taxas

        self.initial_params = initial_params
        self.dataset_file = initial_params.get("dataset_file", "pessoas.json")
        
        # FIX DEFINITIVO: Inicializa pacientes como lista vazia. O carregamento é adiado.
        self.pacientes = [] 
        
        self.sim = None
        self.anim_after = None
        self.minuto_atual = 0
        self.comparacao_taxas_data = None 
        
        # Lista de especialidades fixas (sem tempo de serviço associado)
        self.all_specialties = ["clinica_geral", "pneumologia", "endocrinologia", "cardiologia", "ortopedia", "otorrino", "geriatria"]
        self.doctor_specialties = {str(i): "clinica_geral" for i in range(self.initial_params.get("num_doctors", 3))} 

        self._build_ui()
        self._apply_initial_config(initial_params)
        
        # O label inicial reflete que não há dados carregados
        self.lbl_dataset = tk.Label(self.left_frame, text=f"Dataset: NENHUM CARREGADO (0 pessoas)", font=("Segoe UI", 8))
        self.lbl_dataset.pack(pady=(5, 5))


    def _apply_initial_config(self, config):
        self.ent_lambda.delete(0, tk.END); self.ent_lambda.insert(0, str(config["lambda_rate"]))
        self.ent_medicos.delete(0, tk.END); self.ent_medicos.insert(0, str(config["num_doctors"]))
        self.cmb_dist.set(config["service_distribution"])
        self.ent_tempo.delete(0, tk.END); self.ent_tempo.insert(0, str(config["mean_service_time"]))
        self.ent_duracao.delete(0, tk.END); self.ent_duracao.insert(0, str(config["simulation_time"]))
        self.cmb_arrival_pattern.set(config["arrival_pattern"])
        
        num_docs = int(self.ent_medicos.get())
        self.doctor_specialties = {str(i): self.doctor_specialties.get(str(i), "clinica_geral") for i in range(num_docs)}

    def _build_ui(self):
        self.left_frame = tk.Frame(self, width=320, padx=10, pady=10)
        self.left_frame.pack(side="left", fill="y")
        right = tk.Frame(self, padx=10, pady=10)
        right.pack(side="right", expand=True, fill="both")

        tk.Label(self.left_frame, text="Simulação Clínica Médica", font=("Segoe UI", 14, "bold")).pack(pady=(0,10))

        frm_params = tk.Frame(self.left_frame)
        frm_params.pack(fill="x", pady=5)

        tk.Label(frm_params, text="Taxa λ (pacientes/h):").grid(row=0, column=0, sticky="w")
        self.ent_lambda = tk.Entry(frm_params, width=8); 
        self.ent_lambda.grid(row=0, column=1, sticky="w")
        
        tk.Label(frm_params, text="Padrão Chegada:").grid(row=5, column=0, sticky="w")
        self.cmb_arrival_pattern = ttk.Combobox(frm_params, values=["homogeneous","nonhomogeneous"], width=10, state="readonly")
        self.cmb_arrival_pattern.grid(row=5, column=1, sticky="w")
        
        tk.Label(frm_params, text="Nº médicos:").grid(row=1, column=0, sticky="w")
        self.ent_medicos = tk.Entry(frm_params, width=8); 
        self.ent_medicos.grid(row=1, column=1, sticky="w")
        self.ent_medicos.bind("<FocusOut>", self._update_specialty_structure)


        tk.Label(frm_params, text="Distribuição:").grid(row=2, column=0, sticky="w")
        self.cmb_dist = ttk.Combobox(frm_params, values=["exponential","normal","uniform"], width=10, state="readonly")
        self.cmb_dist.grid(row=2, column=1, sticky="w")

        tk.Label(frm_params, text="Tempo médio (min):").grid(row=3, column=0, sticky="w")
        self.ent_tempo = tk.Entry(frm_params, width=8); 
        self.ent_tempo.grid(row=3, column=1, sticky="w")

        tk.Label(frm_params, text="Duração (min):").grid(row=4, column=0, sticky="w")
        self.ent_duracao = tk.Entry(frm_params, width=8); 
        self.ent_duracao.grid(row=4, column=1, sticky="w")

        tk.Button(self.left_frame, text="Iniciar Simulação", bg="#ffb703", command=self.iniciar_simulacao).pack(fill="x", pady=(12,6))
        tk.Button(self.left_frame, text="Parar Animação", bg="#e63946", fg="white", command=self.parar_animacao).pack(fill="x", pady=3)
        tk.Button(self.left_frame, text="Abrir Painel de Gráficos", bg="#219ebc", fg="white", command=self.abrir_graficos_abas).pack(fill="x", pady=3)
        tk.Button(self.left_frame, text="Configurar Especialidades", bg="#8ecae6", command=self._open_specialty_config).pack(fill="x", pady=3)
        tk.Button(self.left_frame, text="Carregar Dataset JSON", bg="#f4f4f4", command=self.carregar_dataset_dialog).pack(fill="x", pady=3)
        tk.Button(self.left_frame, text="Pesquisar Pacientes", bg="#f4f4f4", command=self._open_patient_search).pack(fill="x", pady=3)

        tk.Label(self.left_frame, text="Estatísticas Finais:", font=("Segoe UI", 12, "bold")).pack(pady=(10,0))
        tk.Label(self.left_frame, text="(Resultados de Congestionamento)", font=("Segoe UI", 8)).pack()
        self.txt_stats = tk.Text(self.left_frame, height=12, width=38, bg="#fff0e6", font=("Courier", 10))
        self.txt_stats.pack(pady=(2,10))

        tk.Label(self.left_frame, text="Paciente Atual:", font=("Segoe UI", 10, "bold")).pack()
        self.lbl_paciente = tk.Label(self.left_frame, text="— nenhum —", justify="left", wraplength=280)
        self.lbl_paciente.pack(pady=(2,10))

        top_right = tk.Frame(right)
        top_right.pack(side="top", fill="both", expand=True)

        canvas_frame = tk.Frame(top_right)
        canvas_frame.pack(side="top", fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg="#f7f7f7", height=420)
        self.canvas.pack(expand=True, fill="both")

    def _update_specialty_structure(self, event=None):
        try:
            num_docs = int(self.ent_medicos.get())
            self.doctor_specialties = {str(i): self.doctor_specialties.get(str(i), "clinica_geral") for i in range(num_docs)}
        except ValueError:
            pass 

    def _open_specialty_config(self):
        self._update_specialty_structure() 
        
        config_win = tk.Toplevel(self)
        config_win.title("Configurar Especialidades")
        
        row_num = 0
        all_specialties = self.all_specialties
        
        self.specialty_comboboxes = {} 
        
        try:
            num_medicos = int(self.ent_medicos.get())
        except ValueError:
            messagebox.showwarning("Aviso", "Número de médicos inválido.")
            return

        for i in range(num_medicos):
            doc_id = str(i)
            
            tk.Label(config_win, text=f"Médico {i+1}").grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
            
            cmb = ttk.Combobox(config_win, values=all_specialties, state="readonly")
            cmb.set(self.doctor_specialties.get(doc_id, "clinica_geral"))
            cmb.grid(row=row_num, column=1, padx=5, pady=5)
            self.specialty_comboboxes[doc_id] = cmb
            
            row_num += 1
            
        def save_specialties():
            new_specialties = {}
            for doc_id, cmb in self.specialty_comboboxes.items():
                new_specialties[doc_id] = cmb.get()
            
            self.doctor_specialties = new_specialties
            messagebox.showinfo("Sucesso", "Especialidades guardadas com sucesso!")
            config_win.destroy()

        tk.Button(config_win, text="Guardar e Fechar", command=save_specialties).grid(row=row_num, column=0, columnspan=2, pady=10)

    def _open_patient_search(self):
        search_win = tk.Toplevel(self)
        search_win.title("Pesquisa de Pacientes")
        search_win.geometry("750x550")

        frm_input = ttk.Frame(search_win)
        frm_input.pack(fill="x", padx=10, pady=10)
        
        self.search_vars = {
            'nome': tk.StringVar(), 'idade': tk.StringVar(), 'sexo': tk.StringVar(), 'id_cc': tk.StringVar()
        }
        
        # Labels e Entradas de Pesquisa Filtrada (sem "(parcial)")
        ttk.Label(frm_input, text="Nome:").grid(row=0, column=0, sticky="w"); ttk.Entry(frm_input, textvariable=self.search_vars['nome']).grid(row=0, column=1, sticky="we", padx=5)
        ttk.Label(frm_input, text="Idade:").grid(row=1, column=0, sticky="w"); ttk.Entry(frm_input, textvariable=self.search_vars['idade']).grid(row=1, column=1, sticky="we", padx=5)
        
        ttk.Label(frm_input, text="CC/BI:").grid(row=0, column=2, sticky="w"); ttk.Entry(frm_input, textvariable=self.search_vars['id_cc']).grid(row=0, column=3, sticky="we", padx=5)
        ttk.Label(frm_input, text="Sexo:").grid(row=1, column=2, sticky="w"); ttk.Combobox(frm_input, values=['', 'masculino', 'feminino', 'outro'], textvariable=self.search_vars['sexo'], state="readonly").grid(row=1, column=3, sticky="we", padx=5)
        
        tk.Button(frm_input, text="Pesquisar", command=lambda: self._perform_search(listbox_results)).grid(row=2, column=0, columnspan=4, pady=10)

        listbox_results = tk.Listbox(search_win, width=100, height=20, font=("Courier", 10))
        listbox_results.pack(padx=10, pady=10)
        listbox_results.bind("<<ListboxSelect>>", lambda event: self._show_patient_details(listbox_results))
        listbox_results.insert(tk.END, "ID | NOME | IDADE | SEXO | DISTRITO | PRIO | NOTAS CLÍNICAS (Clique para Detalhes)")
        listbox_results.insert(tk.END, "----------------------------------------------------------------------------------------------------")
        
    def _show_patient_details(self, listbox_results):
        try:
            selection = listbox_results.curselection()
            if not selection or listbox_results.get(selection[0]).startswith("ID |"): return
            
            selected_line = listbox_results.get(selection[0])
            patient_id_raw = selected_line.split('|')[0].strip()
            
            patient = next((p for p in self.pacientes if str(p.id) == patient_id_raw), None)
            
            if not patient: return

            details_win = tk.Toplevel(self)
            details_win.title(f"Detalhes Clínicos do Paciente: {patient.nome}")
            details_win.geometry("500x450")
            
            # Reutiliza o motor de prioridade da simulação
            p_for_sim = {k: getattr(patient, k) for k in ['idade', 'descrição', 'religiao', 'atributos']}
            _, prioridade_str, motivo_str = SimulacaoClinica._detectar_doenca_e_prioridade(SimulacaoClinica(pacientes=[]), p_for_sim)
            
            
            # --- Preparação do Texto Detalhado ---
            
            details_text = f"--- DADOS PESSOAIS ---\n"
            details_text += f"{'Nome:':<15} {patient.nome}\n"
            details_text += f"{'CC/BI (ID):':<15} {patient.id}\n" # Inclui CC/BI (ID)
            details_text += f"{'Idade:':<15} {patient.idade}\n"
            details_text += f"{'Sexo:':<15} {patient.sexo}\n"
            details_text += f"{'Profissão:':<15} {patient.profissao}\n"
            details_text += f"{'Religião:':<15} {patient.religiao or 'N/A'}\n"
            details_text += f"{'Distrito:':<15} {patient.morada.get('distrito', 'N/A')}\n\n"
            
            details_text += f"--- AVALIAÇÃO CLÍNICA (SIMULAÇÃO) ---\n"
            details_text += f"{'PRIORIDADE FILA:':<20} NORMAL\n" # Prioridade é sempre NORMAL
            details_text += f"{'NOTAS CLÍNICAS:':<20} {motivo_str}\n" # Notas Clínicas
            
            atributos = patient.atributos or {}
            fumador_status = "Sim" if atributos.get('fumador') else "Não"
            details_text += f"{'Fumador (Atributo):':<20} {fumador_status}\n"
            details_text += f"{'Desportos:':<20} {', '.join(patient.desportos) if patient.desportos else 'N/A'}\n\n"
            
            details_text += f"--- QUADRO CLÍNICO/HISTÓRICO (DO DATASET) ---\n"
            details_text += f"{patient.descrição or 'Nenhuma descrição no dataset.'}\n"
            
            text_widget = tk.Text(details_win, wrap="word", padx=10, pady=10, font=("Courier", 10))
            text_widget.insert(tk.END, details_text)
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(fill="both", expand=True)

        except Exception as e:
            messagebox.showerror("Erro de Detalhe", f"Erro ao exibir detalhes: {e}")


    def _perform_search(self, listbox_results):
        listbox_results.delete(0, tk.END)
        listbox_results.insert(tk.END, "ID | NOME | IDADE | SEXO | DISTRITO | PRIO | NOTAS CLÍNICAS (Clique para Detalhes)")
        listbox_results.insert(tk.END, "----------------------------------------------------------------------------------------------------")
        
        query_nome = self.search_vars['nome'].get().lower()
        query_idade = self.search_vars['idade'].get().lower()
        query_sexo = self.search_vars['sexo'].get().lower()
        query_id_cc = self.search_vars['id_cc'].get().lower()
        
        found_count = 0
        for p in self.pacientes:
            p_data = p.__dict__
            
            is_match = True
            
            # Filtro 1: Nome (Contém a string)
            if query_nome and query_nome not in str(p_data.get('nome', '')).lower(): 
                is_match = False
            
            # Filtro 2: Idade (Contém a string)
            if is_match and query_idade and query_idade not in str(p_data.get('idade', '')): 
                is_match = False

            # Filtro 3: Sexo (EXATO)
            if is_match and query_sexo and str(p_data.get('sexo', '')).lower() != query_sexo: 
                is_match = False
                
            # Filtro 4: CC/BI (Contém a string)
            if is_match and query_id_cc and query_id_cc not in str(p.id).lower():
                is_match = False
            
            # Se todos os filtros passarem
            if is_match:
                # Determina a prioridade e motivo (para exibir as notas clínicas)
                p_for_sim = {k: getattr(p, k) for k in ['idade', 'descrição', 'religiao', 'atributos']}
                _, prioridade_str, motivo_str = SimulacaoClinica._detectar_doenca_e_prioridade(SimulacaoClinica(pacientes=[]), p_for_sim)

                morada = p_data.get('morada', {}); distrito = morada.get('distrito', '?')
                
                # A prioridade é sempre "NORMAL" na exibição
                line = f"{p.id:<3} | {p.nome:<20} | {p.idade:<5} | {p.sexo:<5} | {distrito:<15} | {'NORM':<4} | {motivo_str[:35]:<35}"
                listbox_results.insert(tk.END, line)
                found_count += 1
        
        if found_count == 0:
            listbox_results.insert(tk.END, "Nenhum paciente encontrado com os filtros especificados.")
            
    def _carregar_dataset_dialog(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.getcwd()
        )
        if filepath:
            try:
                new_pacientes = carregar_pacientes_json(ficheiro=filepath, limite=None)
                if new_pacientes:
                    self.pacientes = new_pacientes
                    self.dataset_file = filepath
                    self.lbl_dataset.config(text=f"Dataset: {os.path.basename(self.dataset_file)} ({len(self.pacientes)} pessoas)")
                    messagebox.showinfo("Sucesso", f"{len(self.pacientes)} pacientes carregados de {os.path.basename(filepath)}.")
                else:
                    # Avisa se o ficheiro estiver vazio/inválido
                    messagebox.showwarning("Aviso", f"O ficheiro {os.path.basename(filepath)} está vazio ou com formato inválido.")
            except Exception as e:
                messagebox.showerror("Erro de Leitura", f"Não foi possível ler o ficheiro: {e}")

    def _iniciar_simulacao(self):
        lambda_rate = None; num_doctors = None; dist = None; tempo = None; duracao = None; arrival_pattern = None; valid_params = True
        
        try:
            lambda_rate = float(self.ent_lambda.get()); num_doctors = int(self.ent_medicos.get()); dist = self.cmb_dist.get(); tempo = float(self.ent_tempo.get())
            duracao = int(self.ent_duracao.get()); arrival_pattern = self.cmb_arrival_pattern.get(); self._update_specialty_structure()
        except ValueError:
            messagebox.showwarning("Aviso","Insira valores válidos!"); valid_params = False

        if valid_params:
            # BLOQUEIO: É obrigatório carregar um dataset
            if not self.pacientes or len(self.pacientes) == 0:
                messagebox.showwarning("Aviso", "Não é possível iniciar. É **obrigatório** carregar um Dataset JSON válido (ficheiro de pacientes) antes de simular.")
                return

            self.sim = SimulacaoClinica(lambda_rate=lambda_rate, num_doctors=num_doctors,
                                        service_distribution=dist, mean_service_time=tempo,
                                        simulation_time=duracao, pacientes=self.pacientes,
                                        arrival_pattern=arrival_pattern,
                                        doctor_specialties=self.doctor_specialties)
                                        
            thread = threading.Thread(target=self._run_sim_thread, daemon=True)
            thread.start()
            self.minuto_atual = 0; self.canvas.delete("all"); self.lbl_paciente.config(text="Executando simulação... aguarda")
            self.after(200, self.animar)

    def _run_sim_thread(self):
        try:
            self.sim.run()
            # Se a simulação abortou em simulacao.py (sem pacientes), não calcula stats
            if not self.sim.pacientes: 
                self.after(50, lambda: self._mostrar_stats_texto("Simulação abortada: Dataset de pacientes vazio."))
                return

            stats = calcular_estatisticas(self.sim)
            
            # NOVO FORMATO DE ESTATÍSTICAS
            texto = "📊 ESTATÍSTICAS GERAIS\n"
            texto += "--------------------------------------\n"
            texto += f"Pacientes Atendidos: {stats['doentes_atendidos']}\n"
            texto += f"Ocupação Média Médicos: {stats['ocupacao_media_medicos']:.2f}%\n\n"
            
            texto += "⏱️ TEMPOS (Minutos)\n"
            texto += f"T. Médio Espera: {stats['tempo_medio_espera']:.2f} | Var: {stats['variancia_tempo_espera']:.2f}\n"
            texto += f"T. Médio Consulta: {stats['tempo_medio_consulta']:.2f} | Var: {stats['variancia_tempo_consulta']:.2f}\n"
            texto += f"T. Médio Total Clínica: {stats['tempo_medio_na_clinica']:.2f}\n\n"
            
            texto += "🔢 FILA (Pacientes)\n"
            texto += f"Fila Média: {stats['fila_media']:.2f} | Fila Máxima: {stats['fila_max']}\n\n"
            
            med_stats_str = "🧑‍⚕️ MÉTRICAS POR MÉDICO\n"
            med_stats_str += "--------------------------------------\n"
            for mid, m_stats in stats.get("stats_por_medico", {}).items():
                med_stats_str += f"Médico {mid+1} ({m_stats['especialidade'].title()}):\n"
                med_stats_str += f"  - Atendidos: {m_stats['num_atendidos']:<5} | Ocupação: {m_stats['ocupacao_percent']:.1f}%\n"
                med_stats_str += f"  - T. Consulta Médio: {m_stats['media_consulta']:.2f} min\n"
                
            texto += med_stats_str
            
            self.after(50, lambda: self._mostrar_stats_texto(texto))
        except Exception as e:
            print("Erro durante a execução da simulação (thread):", e)
            traceback.print_exc()

    def _mostrar_stats_texto(self, texto):
        self.txt_stats.delete("1.0","end")
        self.txt_stats.insert("1.0", texto)

    def animar(self):
        try:
            if not self.sim: self.after(200, self.animar); return
            # Se a simulação abortou, pára a animação
            if hasattr(self.sim, "pacientes") and not self.sim.pacientes: 
                self.lbl_paciente.config(text="Simulação abortada: Sem pacientes de dataset."); self.parar_animacao(); return
                
            if not hasattr(self.sim, "fila_sizes") or not hasattr(self.sim, "ocupacao_medicos"): self.after(200, self.animar); return
            if self.minuto_atual >= len(self.sim.fila_sizes): self.lbl_paciente.config(text="Simulação terminada."); self.parar_animacao(); return

            self.canvas.delete("all")
            fila_size = self.sim.fila_sizes[self.minuto_atual] if self.minuto_atual < len(self.sim.fila_sizes) else 0
            ocupacao = self.sim.ocupacao_medicos[self.minuto_atual] if self.minuto_atual < len(self.sim.ocupacao_medicos) else 0.0

            start_x = 30; start_y = 40
            self.canvas.create_text(start_x, start_y-20, anchor="w", text=f"Fila de espera ({fila_size} pacientes)", font=("Arial", 12, "bold"))
            for i in range(fila_size):
                x = start_x + (i % 10) * 28; y = start_y + (i//10) * 40
                self.canvas.create_rectangle(x, y, x+20, y+30, fill="#e63946", outline="black")

            num_doctors = getattr(self.sim, "num_doctors", 3)
            box_w = 220; box_h = 40; left_med_x = 450; top_med_y = 60
            ocup_num = int(round((ocupacao/100.0) * num_doctors)) if num_doctors > 0 else 0
            nomes_por_medico = {i: None for i in range(num_doctors)}; eventos = getattr(self.sim, "eventos", []) or []
            
            for ev in eventos:
                inicio = 0; dur = 0.0; fim = 0; is_valid_event = True
                try: inicio = int(ev.get("minuto_inicio", 0)); dur = float(ev.get("duracao", 0.0)); fim = inicio + int(np.ceil(dur))
                except Exception: is_valid_event = False 
                if is_valid_event and inicio <= self.minuto_atual < fim:
                    medico_raw = ev.get("medico", None); 
                    
                    # Apenas mostra o nome
                    nome_completo = ev.get("paciente") or "Paciente desconhecido"
                    nome_puro = nome_completo.split(' (')[0]
                    
                    is_valid_medico = True
                    try: m_idx = int(medico_raw); 
                    except Exception: is_valid_medico = False 
                    if is_valid_medico: nomes_por_medico[m_idx] = nome_puro

            OCUPADO_COR = "#00A86B" 
            pacientes_em_consulta = []
            for i in range(num_doctors):
                y = top_med_y + i*(box_h+20)
                
                nome_atual = nomes_por_medico.get(i)
                color = OCUPADO_COR if nome_atual is not None else "#adb5bd" 
                
                self.canvas.create_rectangle(left_med_x, y, left_med_x+box_w, y+box_h, fill=color, outline="black")
                self.canvas.create_text(left_med_x+box_w+10, y+box_h/2, anchor="w", text=f"Médico {i+1} ({self.doctor_specialties.get(str(i), 'geral').title()})", font=("Arial", 11))
                
                if nome_atual: 
                    self.canvas.create_text(left_med_x+6, y+box_h/2, anchor="w", text=nome_atual, font=("Arial", 10, "bold"), fill="white")
                    medico_str = f"Médico {i + 1}"
                    pacientes_em_consulta.append(f"{medico_str}: {nome_atual}")

            atendidos = getattr(self.sim, "doentes_atendidos", 0)
            tempos_espera = getattr(self.sim, "tempos_espera", []) or []
            tempo_esp = np.mean(tempos_espera) if tempos_espera else 0
            tempo_cons = np.mean(getattr(self.sim, "tempos_consulta", [])) or 0
            
            txt = f"Minuto: {self.minuto_atual} | Atendidos: {atendidos} | Tempo médio espera: {tempo_esp:.2f} min | Tempo médio consulta: {tempo_cons:.2f} min"
            self.canvas.create_text(30, 380, anchor="w", text=txt, font=("Arial", 10))

            # Atualiza o label de Paciente Atual apenas com o nome
            if pacientes_em_consulta: texto = "\n".join(pacientes_em_consulta)
            else: texto = "— nenhum paciente em consulta neste minuto —"

            self.lbl_paciente.config(text=texto)
            self.minuto_atual += 1
            self.anim_after = self.after(120, self.animar) 

        except Exception as e:
            print("Erro na função animar():", e)
            traceback.print_exc()
            self.after(500, self.animar)
    
    def _parar_animacao(self):
        if self.anim_after: self.after_cancel(self.anim_after)
        self.anim_after = None

    def _abrir_graficos_abas(self):
        should_proceed = True
        if not self.sim: messagebox.showwarning("Aviso", "Execute a simulação antes de abrir gráficos."); should_proceed = False
        
        # Verifica se a simulação correu sem abortar
        if hasattr(self.sim, "pacientes") and not self.sim.pacientes:
            messagebox.showwarning("Aviso", "A simulação não gerou dados. Por favor, inicie a simulação com um dataset carregado.")
            should_proceed = False

        if should_proceed:
            win = tk.Toplevel(self)
            win.title("Painel de Gráficos")
            win.geometry("1000x600") 
            notebook = ttk.Notebook(win)
            notebook.pack(expand=True, fill="both")

            tab1 = tk.Frame(notebook); notebook.add(tab1, text="Fila"); grafico_fila_frame(tab1, self.sim.fila_sizes)
            tab2 = tk.Frame(notebook); notebook.add(tab2, text="Ocupação (Tempo)"); grafico_ocupacao_frame(tab2, self.sim.ocupacao_medicos)
            
            tab_distritos = tk.Frame(notebook); notebook.add(tab_distritos, text="Distribuição")
            grafico_distritos_bar(tab_distritos, self.sim.distritos_pacientes)
            
            tab_metricas = tk.Frame(notebook); notebook.add(tab_metricas, text="Métricas Chave")
            
            frame_utilizacao = tk.Frame(tab_metricas); frame_utilizacao.pack(side="left", fill="both", expand=True)
            if hasattr(self.sim, "stats_por_medico"):
                grafico_ocupacao_medicos_bar(frame_utilizacao, self.sim.stats_por_medico)
            else:
                tk.Label(frame_utilizacao, text="Simulação não gerou métricas por médico.").pack()
            
            frame_rho = tk.Frame(tab_metricas); frame_rho.pack(side="right", fill="both", expand=True)

            tab3 = tk.Frame(notebook); notebook.add(tab3, text="T. Espera"); grafico_tempo_espera_frame(tab3, self.sim.tempos_espera)
            tab4 = tk.Frame(notebook); notebook.add(tab4, text="T. Clínica"); grafico_tempo_total_frame(tab4, self.sim.tempos_clinica)

            tab5 = tk.Frame(notebook); notebook.add(tab5, text="Comparações (λ)")
            
            if self.comparacao_taxas_data:
                taxas, medias = self.comparacao_taxas_data
                grafico_fila_vs_taxa_frame(tab5, taxas, medias)
            else:
                tk.Label(tab5, text="O gráfico de comparação precisa de ser calculado (taxas 10 a 30).").pack(pady=10)
                tk.Button(tab5, text="Calcular Comparação Lambda (10..30)", bg="#8ecae6", 
                          command=lambda: self._trigger_comparacao(win, tab5)).pack(pady=10)

    def _trigger_comparacao(self, graph_window, current_tab):
        graph_window.destroy() 
        self.comparar_taxas()
        self.abrir_graficos_abas() 
        
    def _comparar_taxas(self):
        # BLOQUEIO: É obrigatório carregar um dataset
        if not self.pacientes or len(self.pacientes) == 0:
            messagebox.showwarning("Aviso", "Não é possível comparar taxas. É **obrigatório** carregar um Dataset JSON válido (ficheiro de pacientes).")
            return
            
        taxas = list(range(10, 31, 5)); medias = []
        
        progresso = tk.Toplevel(self); progresso.title("A executar comparações...")
        lb = tk.Label(progresso, text="A correr simulações para cada taxa, aguarda..."); lb.pack(padx=20, pady=15)
        self.update()

        num_doctors = int(self.ent_medicos.get()); dist = self.cmb_dist.get(); tempo = float(self.ent_tempo.get()); duracao = int(self.ent_duracao.get())
        
        for taxa in taxas:
            sim_temp = SimulacaoClinica(lambda_rate=taxa, num_doctors=num_doctors,
                                        service_distribution=dist, mean_service_time=tempo,
                                        simulation_time=duracao, pacientes=self.pacientes,
                                        arrival_pattern="homogeneous",
                                        doctor_specialties=self.doctor_specialties) 
            sim_temp.run()
            # Se a simulação correu, calcula a média da fila
            if sim_temp.fila_sizes:
                medias.append( sum(sim_temp.fila_sizes)/len(sim_temp.fila_sizes) )
            else:
                medias.append(0) 
            
        self.comparacao_taxas_data = (taxas, medias)

        progresso.destroy()
        messagebox.showinfo("Sucesso", "A comparação de taxas foi concluída e está pronta para ser exibida na aba 'Comparações (λ)'.")

    def _on_close(self):
        if self.anim_after: self.after_cancel(self.anim_after)
        self.destroy()
