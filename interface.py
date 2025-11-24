# interface.py
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from simulacao import SimulacaoClinica
from utils import carregar_pacientes_json
from estatisticas import calcular_estatisticas
import graficos as gplot
import threading
import traceback

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulação Clínica - Versão Melhorada")
        self.geometry("1100x720")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    

        # dados
        self.pacientes = carregar_pacientes_json(limite=500)
        self.sim = None
        self.anim_after = None
        self.minuto_atual = 0

        self._build_ui()

    def _build_ui(self):
        # frames principais
        left = tk.Frame(self, width=320, padx=10, pady=10)
        left.pack(side="left", fill="y")
        right = tk.Frame(self, padx=10, pady=10)
        right.pack(side="right", expand=True, fill="both")

        # CONTROLOS (left)
        tk.Label(left, text="Simulação Clínica Médica", font=("Segoe UI", 14, "bold")).pack(pady=(0,10))

        frm_params = tk.Frame(left)
        frm_params.pack(fill="x", pady=5)

        tk.Label(frm_params, text="Taxa λ (pacientes/h):").grid(row=0, column=0, sticky="w")
        self.ent_lambda = tk.Entry(frm_params, width=8); self.ent_lambda.insert(0,"10")
        self.ent_lambda.grid(row=0, column=1, sticky="w")

        tk.Label(frm_params, text="Nº médicos:").grid(row=1, column=0, sticky="w")
        self.ent_medicos = tk.Entry(frm_params, width=8); self.ent_medicos.insert(0,"3")
        self.ent_medicos.grid(row=1, column=1, sticky="w")

        tk.Label(frm_params, text="Distribuição:").grid(row=2, column=0, sticky="w")
        self.cmb_dist = ttk.Combobox(frm_params, values=["exponential","normal","uniform"], width=10, state="readonly")
        self.cmb_dist.set("exponential"); self.cmb_dist.grid(row=2, column=1, sticky="w")

        tk.Label(frm_params, text="Tempo médio (min):").grid(row=3, column=0, sticky="w")
        self.ent_tempo = tk.Entry(frm_params, width=8); self.ent_tempo.insert(0,"15")
        self.ent_tempo.grid(row=3, column=1, sticky="w")

        tk.Label(frm_params, text="Duração (min):").grid(row=4, column=0, sticky="w")
        self.ent_duracao = tk.Entry(frm_params, width=8); self.ent_duracao.insert(0,"120")
        self.ent_duracao.grid(row=4, column=1, sticky="w")

        # Botões
        tk.Button(left, text="Iniciar Simulação", bg="#ffb703", command=self.iniciar_simulacao).pack(fill="x", pady=(12,6))
        tk.Button(left, text="Parar Animação", bg="#e63946", fg="white", command=self.parar_animacao).pack(fill="x", pady=3)
        tk.Button(left, text="Comparar taxas (10..30)", bg="#8ecae6", command=self.comparar_taxas).pack(fill="x", pady=3)
        tk.Button(left, text="Mostrar janelas de gráficos", bg="#219ebc", fg="white", command=self.abrir_graficos_abas).pack(fill="x", pady=3)

        # Estatísticas finais
        tk.Label(left, text="Estatísticas finais:", font=("Segoe UI", 10, "bold")).pack(pady=(10,0))
        self.txt_stats = tk.Text(left, height=10, width=38)
        self.txt_stats.pack(pady=(2,10))

        # INFORMAÇÃO DO PACIENTE ATUAL (left)
        tk.Label(left, text="Paciente atual:", font=("Segoe UI", 10, "bold")).pack()
        self.lbl_paciente = tk.Label(left, text="— nenhum —", justify="left", wraplength=280)
        self.lbl_paciente.pack(pady=(2,10))

        # AREA VISUAL (right)
        top_right = tk.Frame(right)
        top_right.pack(side="top", fill="both", expand=True)

        # Canvas animação
        canvas_frame = tk.Frame(top_right)
        canvas_frame.pack(side="top", fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg="#f7f7f7", height=420)
        self.canvas.pack(expand=True, fill="both")

        # Notebook para gráficos (cada gráfico numa aba)
        bottom_right = tk.Frame(right)
        bottom_right.pack(side="bottom", fill="x")
        self.btn_open_tab_window = tk.Button(bottom_right, text="Abrir painel de gráficos", command=self.abrir_graficos_abas)
        self.btn_open_tab_window.pack(pady=6)

    def iniciar_simulacao(self):
        try:
            lambda_rate = float(self.ent_lambda.get())
            num_doctors = int(self.ent_medicos.get())
            dist = self.cmb_dist.get()
            tempo = float(self.ent_tempo.get())
            duracao = int(self.ent_duracao.get())
        except ValueError:
            messagebox.showwarning("Aviso","Insira valores válidos!")
            return

        # criar objecto de simulação
        self.sim = SimulacaoClinica(lambda_rate=lambda_rate, num_doctors=num_doctors,
                                    service_distribution=dist, mean_service_time=tempo,
                                    simulation_time=duracao, pacientes=self.pacientes)
        # correr a simulação num thread para não bloquear UI (gera os arrays)
        thread = threading.Thread(target=self._run_sim_thread, daemon=True)
        thread.start()
        # reset animação
        self.minuto_atual = 0
        self.canvas.delete("all")
        self.lbl_paciente.config(text="Executando simulação... aguarda")
        # inicia animação mesmo que a simulação ainda corra
        # a animação chamará self.animar repetidamente
        self.after(200, self.animar)

    def _run_sim_thread(self):
        try:
            resultados = self.sim.run()
            # quando terminar, actualizamos estatísticas
            stats = calcular_estatisticas(self.sim)
            texto = "\n".join([f"{k.replace('_',' ').title()}: {v:.2f}" if isinstance(v,(float,int)) and not isinstance(v,bool) else f"{k.replace('_',' ').title()}: {v}" for k,v in stats.items()])
            # atualiza UI no thread principal
            self.after(50, lambda: self._mostrar_stats_texto(texto))
        except Exception as e:
            print("Erro durante a execução da simulação (thread):", e)
            traceback.print_exc()

    def _mostrar_stats_texto(self, texto):
        self.txt_stats.delete("1.0","end")
        self.txt_stats.insert("1.0", texto)
        
    def animar(self):
        """
        Atualiza a visualização a cada 'tick' (minuto simulado).
        Mostra a fila, médicos, nomes dos pacientes em cada médico e actualiza a label de pacientes em consulta.
        """
        try:
            # valida existênça de simulação
            if not self.sim:
                self.after(200, self.animar)
                return

            # verifica que temos arrays para o tempo pedido
            if not hasattr(self.sim, "fila_sizes") or not hasattr(self.sim, "ocupacao_medicos"):
                # se a simulação ainda não inicializou as estruturas, tenta novamente
                self.after(200, self.animar)
                return

            # fim da simulação?
            if self.minuto_atual >= len(self.sim.fila_sizes):
                self.lbl_paciente.config(text="Simulação terminada.")
                return

            # limpa canvas
            self.canvas.delete("all")

            # dados deste minuto (com verificações)
            fila_size = self.sim.fila_sizes[self.minuto_atual] if self.minuto_atual < len(self.sim.fila_sizes) else 0
            ocupacao = self.sim.ocupacao_medicos[self.minuto_atual] if self.minuto_atual < len(self.sim.ocupacao_medicos) else 0.0

            # Desenhar fila (esquerda)
            start_x = 30
            start_y = 40
            self.canvas.create_text(start_x, start_y-20, anchor="w", text=f"Fila de espera ({fila_size} pacientes)", font=("Arial", 12, "bold"))
            for i in range(fila_size):
                x = start_x + (i % 10) * 28
                y = start_y + (i//10) * 40
                self.canvas.create_rectangle(x, y, x+20, y+30, fill="#e63946", outline="black")

            # Desenhar médicos (direita) e nomes dos pacientes dentro das caixas
            num_doctors = getattr(self.sim, "num_doctors", 3)
            box_w = 220
            box_h = 40
            left_med_x = 450
            top_med_y = 60

            # Determina quantos ocupados (inteiro)
            ocup_num = int(round((ocupacao/100.0) * num_doctors)) if num_doctors > 0 else 0
            # Para assinalar nomes, vamos construir um dicionário medico_idx -> nome (se soubermos)
            nomes_por_medico = {i: None for i in range(num_doctors)}
            # percorre eventos para encontrar quem está em consulta no minuto atual
            eventos = getattr(self.sim, "eventos", []) or []
            for ev in eventos:
                try:
                    inicio = int(ev.get("minuto_inicio", 0))
                    dur = float(ev.get("duracao", 0.0))
                    fim = inicio + int(np.ceil(dur))
                except Exception:
                    continue
                if inicio <= self.minuto_atual < fim:
                    medico_raw = ev.get("medico", None)
                    nome = ev.get("paciente") or "Paciente desconhecido"
                    try:
                        m_idx = int(medico_raw)
                        if 0 <= m_idx < num_doctors:
                            nomes_por_medico[m_idx] = nome
                    except Exception:
                        # ignora se não for int
                        pass

            # desenha cada médico com o nome se existir
            for i in range(num_doctors):
                y = top_med_y + i*(box_h+20)
                color = "#2a9d8f" if i < ocup_num else "#adb5bd"
                self.canvas.create_rectangle(left_med_x, y, left_med_x+box_w, y+box_h, fill=color, outline="black")
                # escreve o nome do médico à direita do rect
                self.canvas.create_text(left_med_x+box_w+10, y+box_h/2, anchor="w", text=f"Médico {i+1}", font=("Arial", 11))
                # escreve o nome do paciente dentro da caixa (se existir)
                nome_atual = nomes_por_medico.get(i)
                if nome_atual:
                    # texto dentro, alinhado à esquerda com padding
                    self.canvas.create_text(left_med_x+6, y+box_h/2, anchor="w", text=nome_atual, font=("Arial", 10, "bold"), fill="white")

            # Estatísticas instantâneas (texto rodapé)
            atendidos = getattr(self.sim, "doentes_atendidos", 0)
            tempos_espera = getattr(self.sim, "tempos_espera", []) or []
            tempos_consulta = getattr(self.sim, "tempos_consulta", []) or []
            tempo_esp = np.mean(tempos_espera[:max(1,self.minuto_atual)]) if tempos_espera else 0
            tempo_cons = np.mean(tempos_consulta[:max(1,self.minuto_atual)]) if tempos_consulta else 0
            txt = f"Minuto: {self.minuto_atual} | Atendidos: {atendidos} | Tempo médio espera: {tempo_esp:.2f} min | Tempo médio consulta: {tempo_cons:.2f} min"
            self.canvas.create_text(30, 380, anchor="w", text=txt, font=("Arial", 10))

            # Mostrar pacientes atualmente em consulta (texto à esquerda)
            pacientes_em_consulta = []
            for ev in eventos:
                try:
                    inicio = int(ev.get("minuto_inicio", 0))
                    dur = float(ev.get("duracao", 0.0))
                    fim = inicio + int(np.ceil(dur))
                except Exception:
                    continue
                if inicio <= self.minuto_atual < fim:
                    nome = ev.get("paciente") or "Paciente desconhecido"
                    medico_raw = ev.get("medico", None)
                    try:
                        medico_idx = int(medico_raw)
                        medico_str = f"Médico {medico_idx + 1}"
                    except Exception:
                        medico_str = "Médico ?"
                    pacientes_em_consulta.append(f"{medico_str}: {nome}")

            if pacientes_em_consulta:
                texto = "\n".join(pacientes_em_consulta)
            else:
                texto = "— nenhum paciente em consulta neste minuto —"

            self.lbl_paciente.config(text=texto)

            # próximo minuto
            self.minuto_atual += 1
            self.anim_after = self.after(120, self.animar)  # 120ms por minuto (ajusta aqui a velocidade)

        except Exception as e:
            # mostra traceback no terminal para debug e evita crash da UI
            print("Erro na função animar():", e)
            traceback.print_exc()
            # tenta continuar a animação noutro tick
            self.after(500, self.animar)
    
    def parar_animacao(self):
        if self.anim_after:
            self.after_cancel(self.anim_after)
            self.anim_after = None

    def abrir_graficos_abas(self):
        if not self.sim:
            messagebox.showwarning("Aviso", "Execute a simulação antes de abrir gráficos.")
            return

        win = tk.Toplevel(self)
        win.title("Painel de Gráficos")
        win.geometry("900x600")
        notebook = ttk.Notebook(win)
        notebook.pack(expand=True, fill="both")

        # Aba 1 - Fila ao longo do tempo
        tab1 = tk.Frame(notebook)
        notebook.add(tab1, text="Fila")
        gplot.grafico_fila_frame(tab1, self.sim.fila_sizes)

        # Aba 2 - Ocupação
        tab2 = tk.Frame(notebook)
        notebook.add(tab2, text="Ocupação")
        gplot.grafico_ocupacao_frame(tab2, self.sim.ocupacao_medicos)

        # Aba 3 - Tempos de espera
        tab3 = tk.Frame(notebook)
        notebook.add(tab3, text="Tempos de Espera")
        gplot.grafico_tempo_espera_frame(tab3, self.sim.tempos_espera)

        # Aba 4 - Tempo total na clínica
        tab4 = tk.Frame(notebook)
        notebook.add(tab4, text="Tempo na Clínica")
        gplot.grafico_tempo_total_frame(tab4, self.sim.tempos_clinica)

        # Aba 5 - Comparações (vazia - pode ser usada para múltiplas linhas)
        tab5 = tk.Frame(notebook)
        notebook.add(tab5, text="Comparações")

    def comparar_taxas(self):
        taxas = list(range(10, 31, 5))
        medias = []
        progresso = tk.Toplevel(self)
        progresso.title("A executar comparações...")
        lb = tk.Label(progresso, text="A correr simulações para cada taxa, aguarda...")
        lb.pack(padx=20, pady=15)
        self.update()

        for taxa in taxas:
            sim_temp = SimulacaoClinica(lambda_rate=taxa, num_doctors=int(self.ent_medicos.get()),
                                       service_distribution=self.cmb_dist.get(),
                                       mean_service_time=float(self.ent_tempo.get()),
                                       simulation_time=int(self.ent_duracao.get()),
                                       pacientes=self.pacientes)
            sim_temp.run()
            medias.append( sum(sim_temp.fila_sizes)/len(sim_temp.fila_sizes) if sim_temp.fila_sizes else 0 )

        progresso.destroy()
        # abrir gráfico
        win = tk.Toplevel(self)
        win.title("Comparação: Fila média vs Taxa")
        frame = tk.Frame(win)
        frame.pack(expand=True, fill="both")
        gplot.grafico_fila_vs_taxa_frame(frame, taxas, medias)

    def _on_close(self):
        # cancela animação se existir
        if self.anim_after:
            self.after_cancel(self.anim_after)
        self.destroy()
