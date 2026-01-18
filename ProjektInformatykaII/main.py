import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QSlider, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QPainter, QPen, QColor
import pyqtgraph as pg
import numpy as np

class Zbiornik:
    def __init__(self, x, y, name, temp, max_fill_ratio=1.0):
        self.x = x
        self.y = y
        self.w = 110
        self.h = 200

        self.name = name
        self.max_volume = 100.0
        self.volume = 50.0
        self.temperature = temp

        self.max_fill_ratio = max_fill_ratio  # np. 0.75 dla Z3

    def level(self):
        raw_level = self.volume / self.max_volume
        return min(raw_level, 1.0) * self.max_fill_ratio

    def add(self, amount, temp):
        if amount <= 0:
            return
        self.temperature = ((self.temperature * self.volume + temp * amount) / (self.volume + amount))
        self.volume = min(self.max_volume, self.volume + amount)

    def remove(self, amount):
        taken = min(self.volume, amount)
        self.volume -= taken
        return taken

    def draw(self, p, t_otoczenia=None):
        #ciecz
        if self.volume > 0:
            h = int(self.h * self.level())
            p.setBrush(QColor(0, 120, 255, 180))
            p.setPen(QPen())
            p.drawRect(int(self.x + 4), int(self.y + self.h - h), int(self.w - 8), int(h))

        p.setFont(p.font())
        font = p.font()
        font.setPointSize(10)
        p.setFont(font)

        #obrys
        p.setPen(QPen(QColor("white"), 3))
        p.setBrush(QBrush())
        p.drawRect(self.x, self.y, self.w, self.h)

        #opis
        p.drawText(self.x, self.y - 20, self.name)
        p.drawText(self.x, self.y + self.h + 15, f"{int(self.temperature)} °C")

        if t_otoczenia is not None:
            p.setPen(QColor(180, 180, 180))
            p.drawText(self.x - 50, self.y - 80, f"Temperatura otoczenia: {int(t_otoczenia)} °C")

class Rura:
    grubosc = 12
    grubosc_flow = 8

    def __init__(self, points, parent, direction=1):
        self.points = points
        self.flow = False
        self._parent = parent
        self.direction = direction

    def parent(self):
        return self._parent

    def draw(self, p):
        if len(self.points) < 2:
            return

        p.setPen(QPen(QColor("gray"), self.grubosc, Qt.PenStyle.SolidLine))
        for i in range(len(self.points) - 1):
            p.drawLine(*self.points[i], *self.points[i + 1])

        #animacja przeplywu
        if self.flow:
            pen = QPen(QColor(0, 200, 255), self.grubosc_flow)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setDashPattern([12, 10])
            pen.setDashOffset(self.direction * self.parent().flow_offset)

            p.setPen(pen)
            for i in range(len(self.points) - 1):
                p.drawLine(*self.points[i], *self.points[i + 1])

class SCADA(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Układ podgrzewania i chłodzenia")
        self.setFixedSize(1300, 800)
        self.setStyleSheet("background-color:#222;")
        self.fan_angle = 0
        self.coal_timer = 0
        self.grzalka_on = False
        self.T_otoczenia = 19
        self.heat_request = False
        self.cool_request = False
        self.grzanie_trwa = False
        self.temp_zadana_z3 = 50  #domyslnie taka jest ustawiona
        self.histereza = 3  #+-3 stopnie
        self.system_start = False
        self.process_running = False
        self.temp_min_z2 = 65
        self.temp_max_z2 = 70
        self.min_volume_z2 = 40
        self.grzanie_z2 = True
        self.temp_stop_grzania_z3 = 66
        self.flow_offset = 0.0

        #Zbiorniki
        self.z1 = Zbiornik(80, 340, "Zbiornik 1", 20)
        self.z2 = Zbiornik(340, 440, "Bufor", 40)
        self.z3 = Zbiornik(720, 240, "Zbiornik 3", 30, max_fill_ratio=0.75)
        self.z4 = Zbiornik(340, 120, "Chlodnia", 15)
        self.z5 = Zbiornik(220, 700, "Z5 – Węgiel", 300)
        self.z5.volume = 100.0

        #Rury
        #Z1-Z2
        self.r1 = Rura([(190, 440), (260, 440), (260, 540), (340, 540)], self, direction=-1)

        #Z2-Z3
        self.r2 = Rura([(450, 540), (520, 540), (520, 350), (720, 350)], self, direction=-1)

        #Z4-Z3
        self.r3 = Rura([(450, 180), (450, 260), (720, 260)], self, direction=-1) #direction -1 czyli woda plynie z lewa do prawa

        #Z3-kanalizacja
        self.r_out = Rura([(775, 440), (775, 760)], self, direction=-1)

        #zrodlo-Z4
        self.r_main_top = Rura([(40, 20), (40, 120)], self, direction=-1)

        #Z4-Z1
        self.r_main_bottom = Rura([(40, 120), (40, 440)], self, direction=-1)

        #rozgaleznik-Z1
        self.r_main_to_z1 = Rura([(40, 440), (80, 440)], self, direction=-1)

        #rozgaleznik-Z4
        self.r_main_to_z4 = Rura([(40, 120), (340, 120)], self, direction=-1)

        #timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.process)
        self.timer.start(100)

        #dane na wykresie
        self.time_data = np.arange(0, 200) #os X
        self.temp_data = np.zeros(200)  #os Y

        #przycisk "uzupelnij wegiel"
        self.btn_wegiel = QPushButton("Uzupełnij węgiel", self)
        self.btn_wegiel.setGeometry(1020, 215, 250, 35)
        self.btn_wegiel.clicked.connect(self.uzupelnij_wegiel)

        (self.btn_wegiel.setStyleSheet
         (
            """
            QPushButton 
            {
                background-color: #bbbbbb;
                color: black;
                border: 2px solid #888888;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover 
            {
                background-color: #d0d0d0;
            }
            QPushButton:pressed 
            {
                background-color: #aaaaaa;
            }
            """
         )
        )

        self.btn_start = QPushButton("START", self)
        self.btn_start.setGeometry(1080, 740, 140, 45)
        self.btn_start.clicked.connect(self.start_system)

        (self.btn_start.setStyleSheet
         (
            """
            QPushButton 
            {
                background-color: #55aa55;
                color: black;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover 
            {
                background-color: #66cc66;
            }
            """
         )
        )

        self.btn_stop = QPushButton("STOP", self)
        self.btn_stop.setGeometry(920, 740, 140, 45)
        self.btn_stop.clicked.connect(self.stop_system)

        (self.btn_stop.setStyleSheet
         (
            """
            QPushButton 
            {
                background-color: #cc5555;
                color: black;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover 
            {
                background-color: #dd6666;
            }
            """
          )
         )

        #suwak temperatury
        self.slider_temp = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_temp.setGeometry(1020, 95, 250, 30)
        self.slider_temp.setMinimum(30)
        self.slider_temp.setMaximum(70)
        self.slider_temp.setValue(self.temp_zadana_z3)
        self.slider_temp.valueChanged.connect(self.zmien_temperature_zadana)

        self.label_temp = QLabel(self)
        self.label_temp.setGeometry(1020, 70, 250, 20)
        self.label_temp.setStyleSheet("color: white;")
        self.label_temp.setText(f"Temperatura w Zbiorniku 3: {self.temp_zadana_z3} °C")

        #suwak ilosci wegla na poczatku procesu
        self.slider_wegiel = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_wegiel.setGeometry(1020, 170, 250, 30)
        self.slider_wegiel.setMinimum(0)
        self.slider_wegiel.setMaximum(100)
        self.slider_wegiel.setValue(100)
        self.slider_wegiel.valueChanged.connect(self.zmien_wegiel)

        self.label_wegiel = QLabel(self)
        self.label_wegiel.setGeometry(1020, 145, 250, 20)
        self.label_wegiel.setStyleSheet("color: white;")
        self.label_wegiel.setText("Stan węgla: 100 %")

        #wykres Z3
        self.plot_widget = pg.PlotWidget(self)
        self.plot_widget.setGeometry(1000, 300, 280, 250)

        self.plot_widget.setBackground((30, 30, 30))
        self.plot_widget.setTitle("Temperatura w Zbiorniku 3", color='w', size='9pt')
        self.plot_widget.setLabel('left', 'Temperatura [°C]', color='white')
        self.plot_widget.setLabel('bottom', 'Czas', color='white')

        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        #blokada os Y
        self.plot_widget.setYRange(0, 80)

        self.temp_curve = self.plot_widget.plot(self.time_data, self.temp_data, pen=pg.mkPen(color=(255, 100, 100), width=2))

    def start_system(self):
        self.system_start = True
        self.process_running = True
        self.slider_wegiel.setEnabled(False)
        self.btn_start.setEnabled(False)

    def stop_system(self):
        self.process_running = False
        self.btn_start.setEnabled(True)

    def process(self):
        self.r_main_top.flow = False
        self.r_main_bottom.flow = False
        self.r_main_to_z1.flow = False
        self.r_main_to_z4.flow = False

        if not self.system_start:
            self.update()
            return

        if not self.process_running:
            #stygniecie Z3 przez temperature otoczenia
            if self.z3.temperature > self.T_otoczenia:
                self.z3.temperature -= 0.007

            #wykres aktualizuje sie wraz ze spadkiem temperatury stygniecia
            self.temp_data = np.roll(self.temp_data, -1)
            self.temp_data[-1] = self.z3.temperature
            self.temp_curve.setData(self.time_data, self.temp_data)

            self.update()
            return

        self.grzalka_on = False

        #regulator Z3
        tzad = self.temp_zadana_z3
        hi = self.histereza

        #grzanie
        if not self.grzanie_trwa and self.z3.temperature <= (tzad - hi):
            self.grzanie_trwa = True

        if self.grzanie_trwa and self.z3.temperature >= (tzad + hi):
            self.grzanie_trwa = False

        self.heat_request = self.grzanie_trwa

        #chlodzenie
        if self.z3.temperature >= (tzad + hi):
            self.cool_request = True

        if self.cool_request and self.z3.temperature <= tzad:
            self.cool_request = False

        #doplyw zimnej wody do Z4
        if self.cool_request and self.z4.level() < 0.3:
            self.z4.add(2, 15)

            self.r_main_top.flow = True
            self.r_main_to_z4.flow = True
        else:
            self.r_main_to_z4.flow = False

        #dmuchawa
        if self.cool_request:
            self.fan_angle = (self.fan_angle + 80) % 360  #szybkie obroty
        else:
            self.fan_angle = (self.fan_angle + 10) % 360  #wolne obroty

        #rurociag - z1
        if self.z1.level() < 0.6:
            self.z1.add(2, 20)

            self.r_main_top.flow = True
            self.r_main_bottom.flow = True
            self.r_main_to_z1.flow = True
        else:
            self.r_main_to_z1.flow = False

        #utrzymanie objetosci bufora
        z1_to_z2_flow = False
        if self.z2.volume < self.min_volume_z2:
            v = self.z1.remove(1)
            self.z2.volume = min(self.z2.max_volume, self.z2.volume + v)
            z1_to_z2_flow = v > 0
            self.r1.flow = z1_to_z2_flow
        else:
            self.r1.flow = False

        self.coal_timer += 1


        #spalanie gdy trzeba nagrzac lun podtrzymac temperature
        if self.z2.temperature < self.temp_max_z2 or z1_to_z2_flow:
            if self.z5.volume > 0:
                self.z5.remove(0.08)  #ciagle spalanie
                self.grzalka_on = False
            else:
                self.grzalka_on = True

        #grzanie Z3
        if self.heat_request and self.z2.volume > 10:
            v2 = self.z2.remove(2.0)  #staly przeplyw
            self.z3.add(v2, self.z2.temperature)
            self.r2.flow = True
        else:
            self.r2.flow = False

        #dojscie do 70 stopni Z2
        if self.z2.temperature < self.temp_max_z2:
            self.z2.temperature += 0.35

        if self.z2.temperature > self.temp_max_z2:
            self.z2.temperature = self.temp_max_z2

        #przegrzanie-chlodzenie
        if self.cool_request:
            v3 = self.z4.remove(0.6)
            self.z3.add(v3, self.z4.temperature)
            self.r3.flow = True
        else:
            self.r3.flow = False

        #przepelnienie-kanalizacja
        if self.z3.volume >= self.z3.max_volume:
            self.z3.remove(3)
            self.r_out.flow = True
        else:
            self.r_out.flow = False

        if self.z4.temperature < 15:
            self.z4.temperature = 15

        #oddawanie ciepla to otoczenia
        if self.z3.temperature > self.T_otoczenia:
            self.z3.temperature -= 0.007

        if self.z2.temperature > 70:
            self.z2.temperature = 70

        if self.z2.volume < 1:
            self.z2.volume = 1

        #aktualizacja wykresu
        self.temp_data = np.roll(self.temp_data, -1)
        self.temp_data[-1] = self.z3.temperature
        self.temp_curve.setData(self.time_data, self.temp_data)

        self.flow_offset += 1.5
        if self.flow_offset > 100:
            self.flow_offset = 0

        self.update()

    def draw_wegiel(self, p):
        #obrys pojemnika
        x = self.z2.x
        y = self.z2.y + self.z2.h + 30
        w = self.z2.w
        h = 25

        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(QBrush())
        p.drawRect(x, y, w, h)

        #poziom wegla
        level = self.z5.volume / self.z5.max_volume
        fill_w = int(w * level)

        p.setBrush(QColor(40, 40, 40))
        p.drawRect(x + 2, y + 2, fill_w - 4, h - 4)

        p.drawText(x + 30, y + h + 20, "Węgiel")

    def draw_fan(self, p): #dmuchawa
        cx = self.z4.x - 50
        cy = self.z4.y + 50
        r = 26

        #obudowa
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(QColor(70, 70, 70))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        #wirnik
        p.save()
        p.translate(cx, cy)
        p.rotate(self.fan_angle)

        p.setPen(QPen(QColor(0, 220, 255), 3))
        for angle in (0, 120, 240):
            p.save()
            p.rotate(angle)
            p.drawLine(0, 0, r - 6, 0)
            p.restore()

        p.restore()

        #powietrze
        if self.cool_request:
            #mocny podmuch
            p.setPen(QPen(QColor(150, 220, 255), 3))
            for i in range(3):
                p.drawLine(cx + r + 4, cy - 10 + i * 10, cx + r + 35, cy - 10 + i * 10)
        else:
            #lekki podmuch
            p.setPen(QPen(QColor(120, 180, 220), 2))
            for i in range(2):
                p.drawLine(cx + r + 4, cy - 5 + i * 10, cx + r + 20, cy - 5 + i * 10)

        p.setPen(QColor("white"))
        p.drawText(cx - 50, cy + r + 25, "Dmuchawa")

    def draw_grzalka(self, p):
        x = self.z2.x + self.z2.w + 15
        y = self.z2.y + 230

        color = QColor(255, 80, 0) if self.grzalka_on else QColor(100, 100, 100)

        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(color)
        p.drawRect(x, y, 40, 25)

        p.drawText(x - 10, y + 45, "Grzałka")

    @staticmethod
    def draw_kanalizacja(p):
        #pozycja konca rury r_out
        x = 720
        y = 760
        w = 120
        h = 40

        #obrys
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(QColor(160, 160, 160))
        p.drawRect(x, y, w, h)

        #napis
        p.setPen(QColor("black"))
        p.drawText(x + 8, y + 25, "KANALIZACJA")

    @staticmethod
    def draw_rurociag(p):
        #pozycja rurociagu
        x = 10
        y = 0
        w = 120
        h = 35

        #obrys
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(QColor(160, 160, 160))
        p.drawRect(x, y, w, h)

        #napis
        p.setPen(QColor("black"))
        p.drawText(x + 15, y + 23, "RUROCIĄG")

    @staticmethod
    def draw_podzial(p):
        #inst zew
        p.setPen(QPen(QColor("white"), 2, Qt.PenStyle.DashLine))
        p.setBrush(QBrush())
        p.drawRect(20, 60, 520, 700)  #zawiera Z1, Z2, Z4
        p.drawText(200, 790, "INSTALACJA WEWNĘTRZNA")

        #inst wew
        p.drawRect(640, 200, 260, 340)  #zawiera Z3
        p.drawText(695, 580, "INSTALACJA     ZEWNĘTRZNA")

    @staticmethod
    def draw_panel(p):
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(QColor(30, 30, 30))
        p.drawRect(1000, 20, 280, 260)
        p.drawText(1080, 40, "PANEL STEROWANIA")

    def uzupelnij_wegiel(self):
        self.z5.volume = self.z5.max_volume

    def zmien_temperature_zadana(self, value):
        self.temp_zadana_z3 = value
        self.label_temp.setText(f"Temperatura Zbiornik 3: {value} °C")

    def zmien_wegiel(self, value):
        self.z5.volume = self.z5.max_volume * (value / 100)
        self.label_wegiel.setText(f"Stan węgla: {value} %")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        self.draw_panel(p)
        self.draw_podzial(p)

        for r in [self.r_main_top, self.r_main_bottom, self.r_main_to_z1, self.r_main_to_z4, self.r1, self.r2, self.r3, self.r_out]:
            r.draw(p)

        self.z1.draw(p)
        self.z2.draw(p)
        self.z3.draw(p, self.T_otoczenia) #przekazana temperatura otoczenia
        self.z4.draw(p)

        self.draw_wegiel(p)
        self.draw_fan(p)
        self.draw_grzalka(p)
        self.draw_kanalizacja(p)
        self.draw_rurociag(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SCADA()
    win.show()
    sys.exit(app.exec_())
