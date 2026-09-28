import tkinter as tk
from tkinter import ttk
import math, time, threading, os
from PIL import Image, ImageTk

FONDO = "#020617"
GRID = "#1e293b"
RUTA = "#00f5ff"
PUNTO = "#ffcc00"
AUTO = "#ff2d55"
MANUAL = "#22c55e"
PANEL = "#0f172a"

class SimuladorMapa:
    def __init__(self, root):
        self.root = root
        self.root.title("✈ Simulador de Posicionamiento Aéreo")
        self.root.configure(bg=FONDO)

        self.ancho, self.alto = 800, 450
        self.zoom = 1.0
        self.min_zoom = 0.7
        self.max_zoom = 2.0

        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagen.png")
        self.imagen_original = Image.open(ruta) if os.path.exists(ruta) else Image.new("RGB", (self.ancho, self.alto), FONDO)

        principal = tk.Frame(root, bg=FONDO)
        principal.pack(padx=5, pady=5)

        mapa = tk.Frame(principal, bg=FONDO)
        mapa.grid(row=0, column=0, sticky="n")

        self.canvas = tk.Canvas(mapa, width=self.ancho, height=self.alto, bg=FONDO, highlightthickness=0)
        self.canvas.pack()

        self.paises = {
            "Ecuador": (211, 287),
            "Colombia": (220, 275),
            "Perú": (214, 305),
            "Brasil": (261, 310),
            "México": (160, 227),
            "USA": (161, 188),
            "España": (368, 186),
            "Francia": (381, 167),
            "Italia": (401, 179),
            "Egipto": (438, 223),
            "India": (539, 226),
            "Japón": (664, 196),
            "Canáda":(142, 127)
        }

        x, y = self.paises["Ecuador"]
        self.pos_auto = [x, y]
        self.pos_manual = [x + 30, y + 30]

        self.dist_auto = 0
        self.dist_manual = 0
        self.inicio = None
        self.activo = False
        self.pausado = False
        self.detener = False
        self.dragging = False
        self.ultima_pos = self.pos_manual.copy()

        self.origen_actual = None
        self.destino_actual = None

        self.avion_auto_id = None
        self.avion_manual_id = None

        self.dibujar_mapa()

        info = tk.Frame(principal, bg=FONDO)
        info.grid(row=0, column=1, padx=8, sticky="n")

        self.label_auto = tk.Label(
            info, text="✈ AUTOMÁTICO\n\nListo para iniciar",
            fg="white", bg=PANEL, font=("Consolas", 9, "bold"),
            width=30, height=10, justify="left", anchor="nw",
            padx=10, pady=8
        )
        self.label_auto.pack(pady=3)

        self.label_manual = tk.Label(
            info, text="🎮 MANUAL\n\n⌨ W A S D\n🖱 Arrastrar avión",
            fg="white", bg=PANEL, font=("Consolas", 9, "bold"),
            width=30, height=10, justify="left", anchor="nw",
            padx=10, pady=8
        )
        self.label_manual.pack(pady=3)

        controles = tk.Frame(mapa, bg=FONDO)
        controles.pack(pady=4)

        tk.Label(controles, text="Origen", fg="white", bg=FONDO).grid(row=0, column=0, padx=3)

        self.origen = ttk.Combobox(controles, values=list(self.paises), state="readonly", width=10)
        self.origen.set("Ecuador")
        self.origen.grid(row=0, column=1, padx=3)

        tk.Label(controles, text="Destino", fg="white", bg=FONDO).grid(row=0, column=2, padx=3)

        self.destino = ttk.Combobox(controles, values=list(self.paises), state="readonly", width=10)
        self.destino.set("Colombia")
        self.destino.grid(row=0, column=3, padx=3)

        tk.Label(controles, text="Velocidad", fg="white", bg=FONDO).grid(row=0, column=4, padx=3)

        self.velocidad = ttk.Combobox(
            controles, values=["Lenta", "Normal", "Rápida"],
            state="readonly", width=9
        )
        self.velocidad.set("Normal")
        self.velocidad.grid(row=0, column=5, padx=3)

        tk.Button(controles, text="−", width=3, command=self.alejar).grid(row=0, column=6, padx=2)

        self.zoom_label = tk.Label(controles, text="100%", fg="white", bg=FONDO, width=5)
        self.zoom_label.grid(row=0, column=7)

        tk.Button(controles, text="+", width=3, command=self.acercar).grid(row=0, column=8, padx=2)

        botones = tk.Frame(mapa, bg=FONDO)
        botones.pack(pady=3)

        tk.Button(botones, text="✈ Iniciar", command=self.iniciar).grid(row=0, column=0, padx=2)
        tk.Button(botones, text="⏸ Pausar", command=self.pausar).grid(row=0, column=1, padx=2)
        tk.Button(botones, text="▶ Continuar", command=self.continuar).grid(row=0, column=2, padx=2)
        tk.Button(botones, text="⏹ Detener", command=self.parar).grid(row=0, column=3, padx=2)
        tk.Button(botones, text="🔄 Reiniciar", command=self.reiniciar).grid(row=0, column=4, padx=2)

        for tecla in "wasd":
            self.root.bind(f"<{tecla}>", self.mover_manual)

        self.root.bind("<plus>", lambda e: self.acercar())
        self.root.bind("<equal>", lambda e: self.acercar())
        self.root.bind("<minus>", lambda e: self.alejar())

        self.canvas.bind("<MouseWheel>", self.zoom_mouse)

        self.actualizar_manual()

    # MAPA
    def dibujar_mapa(self):
        self.canvas.delete("all")

        ancho = int(self.ancho * self.zoom)
        alto = int(self.alto * self.zoom)

        imagen = self.imagen_original.resize((ancho, alto))
        self.fondo = ImageTk.PhotoImage(imagen)

        x0 = (self.ancho - ancho) / 2
        y0 = (self.alto - alto) / 2

        self.canvas.create_image(x0, y0, anchor="nw", image=self.fondo, tags="mapa")

        self.dibujar_cuadricula()

        for nombre, (x, y) in self.paises.items():
            sx, sy = self.transformar(x, y)

            self.canvas.create_oval(
                sx - 5, sy - 5, sx + 5, sy + 5,
                fill=PUNTO, outline="white", tags="mapa"
            )
            self.canvas.create_text(
                sx, sy - 12, text=nombre,
                fill="white", font=("Arial", 8, "bold"),
                tags="mapa"
            )

        if self.origen_actual and self.destino_actual:
            x1, y1 = self.paises[self.origen_actual]
            x2, y2 = self.paises[self.destino_actual]

            x1, y1 = self.transformar(x1, y1)
            x2, y2 = self.transformar(x2, y2)

            self.canvas.create_line(
                x1, y1, x2, y2,
                fill=RUTA, width=3, tags="mapa"
            )

        self.dibujar_avion(self.pos_auto, AUTO, "avion_auto")
        self.dibujar_avion(self.pos_manual, MANUAL, "avion_manual")

        self.configurar_arrastre()

    def transformar(self, x, y):
        cx, cy = self.ancho / 2, self.alto / 2

        return (
            cx + (x - cx) * self.zoom,
            cy + (y - cy) * self.zoom
        )

    def dibujar_cuadricula(self):
        for x in range(0, self.ancho, 40):
            self.canvas.create_line(
                x, 0, x, self.alto,
                fill=GRID, tags="mapa"
            )

        for y in range(0, self.alto, 40):
            self.canvas.create_line(
                0, y, self.ancho, y,
                fill=GRID, tags="mapa"
            )

    def dibujar_avion(self, pos, color, etiqueta):
        x, y = self.transformar(pos[0], pos[1])

        avion = self.canvas.create_polygon(
            x, y - 9,
            x - 7, y + 9,
            x, y + 4,
            x + 7, y + 9,
            fill=color,
            outline="white",
            tags=etiqueta
        )

        if etiqueta == "avion_auto":
            self.avion_auto_id = avion
        else:
            self.avion_manual_id = avion

    # ARRASTRE CON TAG_BIND
    def configurar_arrastre(self):
        self.canvas.tag_bind(
            "avion_manual",
            "<ButtonPress-1>",
            self.iniciar_drag
        )

        self.canvas.tag_bind(
            "avion_manual",
            "<B1-Motion>",
            self.drag
        )

        self.canvas.tag_bind(
            "avion_manual",
            "<ButtonRelease-1>",
            self.terminar_drag
        )

    def iniciar_drag(self, event):
        self.dragging = True

    def drag(self, event):
        if not self.dragging:
            return

        cx, cy = self.ancho / 2, self.alto / 2

        nueva_x = cx + (event.x - cx) / self.zoom
        nueva_y = cy + (event.y - cy) / self.zoom

        dx = (nueva_x - self.pos_manual[0]) * self.zoom
        dy = (nueva_y - self.pos_manual[1]) * self.zoom

        self.canvas.move(self.avion_manual_id, dx, dy)

        self.pos_manual[0] = nueva_x
        self.pos_manual[1] = nueva_y

        self.actualizar_manual()

    def terminar_drag(self, event):
        self.dragging = False

    # ZOOM
    def acercar(self):
        if self.zoom < self.max_zoom:
            self.zoom = min(self.zoom + 0.1, self.max_zoom)
            self.actualizar_zoom()

    def alejar(self):
        if self.zoom > self.min_zoom:
            self.zoom = max(self.zoom - 0.1, self.min_zoom)
            self.actualizar_zoom()

    def zoom_mouse(self, event):
        if event.delta > 0:
            self.acercar()
        else:
            self.alejar()

    def actualizar_zoom(self):
        self.zoom_label.config(text=f"{int(self.zoom * 100)}%")
        self.dibujar_mapa()

    # DISTANCIA
    def distancia(self, x1, y1, x2, y2):
        distancia_pixeles = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        kilo_por_pixeles = 41.5
        return distancia_pixeles * kilo_por_pixeles

    # VUELO AUTOMÁTICO
    def iniciar(self):
        origen, destino = self.origen.get(), self.destino.get()

        if origen == destino:
            self.label_auto.config(
                text="⚠ ORIGEN Y DESTINO\n\nDeben ser diferentes."
            )
            return

        if self.activo:
            return

        self.activo = True
        self.pausado = False
        self.detener = False
        self.dist_auto = 0
        self.inicio = time.time()

        self.origen_actual = origen
        self.destino_actual = destino

        self.pos_auto = list(self.paises[origen])
        self.dibujar_mapa()

        threading.Thread(target=self.viajar, daemon=True).start()

    def viajar(self):
        origen, destino = self.origen.get(), self.destino.get()

        x1, y1 = self.paises[origen]
        x2, y2 = self.paises[destino]

        total = self.distancia(x1, y1, x2, y2)

        velocidades = {
            "Lenta": 650,
            "Normal": 850,
            "Rápida": 950
        }

        velocidad_kmh = velocidades[self.velocidad.get()]

        tiempo_horas = total / velocidad_kmh
        horas = int(tiempo_horas)
        minutos = int((tiempo_horas - horas) * 60)

        esperas = {
            "Lenta": 1,
            "Normal": 0.5,
            "Rápida": 0.06
        }

        espera = esperas[self.velocidad.get()]
        
        for t in range(101):
            if self.detener:
                return

            while self.pausado:
                time.sleep(0.1)

                if self.detener:
                    return

            x = x1 + (x2 - x1) * t / 100
            y = y1 + (y2 - y1) * t / 100

            self.pos_auto = [x, y]

            recorrido = self.distancia(x1, y1, x, y)
            tiempo = time.time() - self.inicio

            texto = (
                    f"✈ AUTOMÁTICO\n\n"
                    f"🛫 {origen} → {destino}\n\n"
                    f"📍 X: {int(x)}   Y: {int(y)}\n"
                    f"📏 Recorrido: {recorrido:.0f} km\n"
                    f"🎯 Ruta: {total:.0f} km\n"
                    f"🚀 Velocidad: {velocidad_kmh} km/h\n"
                    f"⏱ Tiempo estimado: {horas} h {minutos} min"
                )

            self.root.after(0, self.dibujar_mapa)
            self.root.after(
                0,
                lambda texto=texto:
                self.label_auto.config(text=texto)
            )

            time.sleep(espera)

        self.activo = False

        #tiempo_final = time.time() - self.inicio

        texto = (
            f"✈ VUELO COMPLETADO\n\n"
            f"🛫 {origen} → {destino}\n\n"
            f"📍 X: {int(x2)}   Y: {int(y2)}\n"
            f"📏 Distancia: {total:.2f} km\n"
            f"⏱ Tiempo: {horas} h {minutos} m\n\n"
            f"✅ Llegada al destino"
        )

        self.root.after(0, self.dibujar_mapa)
        self.root.after(
            0,
            lambda:
            self.label_auto.config(text=texto)
        )

    # CONTROLES DE VUELO
    def pausar(self):
        if self.activo:
            self.pausado = True

    def continuar(self):
        if self.activo:
            self.pausado = False

    def parar(self):
        self.detener = True
        self.activo = False
        self.pausado = False
        self.label_auto.config(text="⏹ VUELO DETENIDO")

    # MOVIMIENTO MANUAL CON CANVAS.MOVE
    def mover_manual(self, event):
        paso = 10
        dx = dy = 0

        if event.keysym == "w":
            dy = -paso
        elif event.keysym == "s":
            dy = paso
        elif event.keysym == "a":
            dx = -paso
        elif event.keysym == "d":
            dx = paso

        if self.avion_manual_id:
            self.canvas.move(self.avion_manual_id, dx, dy)

        self.pos_manual[0] += dx / self.zoom
        self.pos_manual[1] += dy / self.zoom

        self.actualizar_manual()

    # TELEMETRÍA MANUAL
    def actualizar_manual(self):
        x, y = self.pos_manual
        lx, ly = self.ultima_pos

        movimiento = self.distancia(lx, ly, x, y)

        self.dist_manual += movimiento
        self.ultima_pos = [x, y]

        texto = (
            f"🎮 MANUAL\n\n"
            f"⌨ W A S D\n"
            f"🖱 Arrastrar avión\n\n"
            f"📍 X: {int(x)}   Y: {int(y)}\n"
            f"📏 Movimiento: {movimiento:.1f} km\n"
            f"🌍 Total: {self.dist_manual:.1f} km"
        )

        self.label_manual.config(text=texto)

    # REINICIAR
    def reiniciar(self):
        self.detener = True
        self.activo = False
        self.pausado = False

        x, y = self.paises["Ecuador"]

        self.pos_auto = [x, y]
        self.pos_manual = [x + 30, y + 30]
        self.ultima_pos = self.pos_manual.copy()

        self.dist_auto = 0
        self.dist_manual = 0
        self.zoom = 1.0

        self.origen_actual = None
        self.destino_actual = None

        self.zoom_label.config(text="100%")

        self.label_auto.config(
            text="✈ AUTOMÁTICO\n\nListo para iniciar"
        )

        self.actualizar_manual()
        self.dibujar_mapa()


root = tk.Tk()
SimuladorMapa(root)
root.mainloop()