# importing libraries
import math
import time

import matplotlib as mpl
import matplotlib.lines
import matplotlib.pyplot as plt
import matplotlib.text as mtxt
import numpy as np
import serial.tools.list_ports
from matplotlib.pyplot import cm
from matplotlib.sankey import Sankey
from matplotlib.transforms import Bbox
from matplotlib.widgets import Button
from serial import STOPBITS_ONE, EIGHTBITS, PARITY_NONE, SerialException


class My_click:
    def __init__(self, plt_ind, aev_meter,my_serial, onof=True, bar=False, profram_titel="AEV Meter", ):
        self.onof = onof
        self.bar = bar
        self.manager = plt_ind.get_current_fig_manager()
        self.manager.full_screen_toggle()
        self.manager.set_window_title(profram_titel)
        axes = plt_ind.axes([0.5, 0.5, 0.5, 0.5])
        self.b_toggle_screen = Button(axes, '', color="green")
        self.b_toggle_screen.on_clicked(self.button_on_click_maximise)
        axes.set(frame_on=False)
        axes2 = plt_ind.axes([0, 0.00, 0.5, 0.5])
        self.b_toggle_velo_tacho = Button(axes2, '', color="red")
        self.b_toggle_velo_tacho.on_clicked(self.button_on_click_tacho_line)
        axes2.set(frame_on=False)
        axes3 = plt_ind.axes([0.5, 0, 0.5, 0.5])
        self.b_toggle_sankey_bar = Button(axes3, '', color="blue")
        self.b_toggle_sankey_bar.on_clicked(self.button_on_click_sankey_bar)
        axes3.set(frame_on=False)
        axes4 = plt_ind.axes([0, 0.5, 0.5, 0.5])
        self.b_reset = Button(axes4, '', color="blue")
        self.b_reset.on_clicked(self.button_on_click_reset)
        axes4.set(frame_on=False)
        self.aev_meter = aev_meter
        self.my_serial=my_serial

    def button_on_click_maximise(self, event):
        self.manager.full_screen_toggle()

    def button_on_click_tacho_line(self, event):
        self.onof = not self.onof

    def button_on_click_sankey_bar(self, event):
        self.bar = not self.bar

    def button_on_click_reset(self, event):
        self.aev_meter.reset()
        self.my_serial.reset()


    def is_onof(self):
        return self.onof

    def is_bar(self):
        return self.bar


class My_bar:
    def __init__(self, axd, bar_colors, label, pos):
        self.axd = axd
        self.bar_colors = bar_colors
        self.label = label
        self.axd.set_position(pos)
        self.axd.set_ylabel('Watt')
        self.axd.yaxis.grid(True)
        self.bar = self.axd.bar(self.label, [0, -2, 1, 1, 1, 1, 2],
                                label=self.label, color=self.bar_colors)
        self.axd.set_title('Leistungen Energieanhänger', fontsize=15, color='blue', fontweight='bold')

    def update(self, y):
        _min = math.ceil(y[0][-1] / 5) * 5.2
        _max = _min

        for __y in range(len(y)):
            self.bar[__y].set_height(y[__y][-1])
            if _min > math.ceil(y[__y][-1] / 5) * 5.2:
                _min = math.ceil(y[__y][-1] / 5) * 5.2
            if _max < math.ceil(y[__y][-1] / 5) * 5.2:
                _max = math.ceil(y[__y][-1] / 5) * 5.2
        self.axd.set_ylim(_min, _max)

    def set_visible(self, param):
        self.axd.set_visible(param)


class My_sankey:

    def __init__(self, axd, bar_colors, label, pos):
        self.axd = axd
        self.bar_colors = bar_colors
        self.label = label
        self.axd.cla()
        self.axd.set_position(pos)

    def update(self, y):
        self.axd.cla()
        self.axd.axis('off')
        self.axd.set_title('Leistungen Energieanhänger', fontsize=15, color='blue', fontweight='bold')
        sankey = (Sankey
                  (ax=self.axd,
                   scale=7 / (np.amax(y[-1]) - np.amin(y[-1])),
                   offset=1.2,
                   head_angle=120,
                   shoulder=0.2,
                   gap=1,
                   radius=0.3,
                   format='%i',
                   unit=' W'))
        for i in range(len(y)):
            pl = 1
            if i == 0:
                sankey.add(facecolor="beige",
                           flows=[y[0][-1], y[1][-1], y[2][-1], y[3][-1], y[4][-1], y[5][-1], y[6][-1]],
                           labels=[None, None, None, None, None, None, None],
                           pathlengths=[pl, pl, pl, pl, pl, pl, pl],
                           orientations=[math.copysign(1, y[0][-1]),
                                         math.copysign(1, y[1][-1]),
                                         math.copysign(1, y[2][-1]),
                                         math.copysign(1, y[3][-1]),
                                         math.copysign(1, y[4][-1]),
                                         math.copysign(1, y[5][-1]),
                                         math.copysign(1, y[6][-1])],

                           connect=(1, 0),
                           rotation=90)

            sankey.add(facecolor=self.bar_colors[i],
                       flows=[-y[i][-1], y[i][-1]],
                       labels=[None, self.label[i]],
                       orientations=[0, 0],
                       prior=0,
                       connect=(i, 0),
                       trunklength=5
                       )
        sankey.finish()

    def set_visible(self, param):
        self.axd.set_visible(param)


class My_leistung:
    def __init__(self, axd, bar_colors, label, x, y, pos):
        self.axd = axd
        self.line = np.empty(len(y) + 1, matplotlib.lines.Line2D)
        for __x in range(len(y)):
            self.line[__x], = self.axd.plot(x, y[__x], label=label[__x], color=bar_colors[__x], linewidth=3)
        self.axd.grid(True)
        self.axd.legend()
        self.axd.set_ylabel('Watt')
        self.axd.set_xlabel('Minuten')
        self.axd.set_title('Leistungen', fontsize=15, color='blue', fontweight='bold')
        self.axd.set_position(pos)

    def update(self, plot_time, x, y, ):
        maxx = plot_time
        if np.amax(x) >= plot_time:
            maxx = np.amax(x)
        ymax = math.ceil(np.amax(y) / 5) * 5.2
        if ymax < 200:
            ymax = 200
        ymin = math.floor(np.amin(y) / 5) * 5
        if ymin > -200:
            ymin = -200
        for __x in range(len(self.line) - 1):
            self.line[__x].set_xdata(x)
            self.line[__x].set_ydata(y[__x])

        self.line[len(self.line) - 1].set_xdata(x)
        self.line[len(self.line) - 1].set_ydata(y[0])
        self.axd.set_xlim(np.amin(x), maxx)
        self.axd.set_ylim(ymin, ymax)

    def get_line(self):
        return self.line


class My_velo:
    def __init__(self, axd, bar_colors, label, line, pos, x, y):
        self.axd = axd
        self.bar_colors = bar_colors
        axd.set_position(pos)
        line[len(line) - 1], = self.axd.plot(x, y[0], color=bar_colors[0], linewidth=3, label=label[0])
        self.fill_between_col = self.axd.fill_between(x, 0, y[0])
        self.axd.set_ylabel('Watt')
        self.axd.set_xlabel('Minuten')
        self.axd.legend()
        self.axd.set_title('Stromvelo', fontsize=15, color='blue', fontweight='bold')
        self.axd.grid(True)

    def update(self, plot_time, velowh, x, y):
        maxx = plot_time
        if np.amax(x) >= plot_time:
            maxx = np.amax(x)
        ymin = math.floor(np.amin(y[0]) / 5) * 5
        if ymin > -30:
            ymin = -30
        ymax = math.ceil(np.amax(y[0]) / 5) * 5.2
        if ymax < 200:
            ymax = 200
        self.axd.set_xlim(np.amin(x), maxx)
        self.axd.set_ylim(ymin, ymax)
        self.fill_between_col.remove()
        self.fill_between_col = self.axd.fill_between(x, 0, y[0], facecolor=self.bar_colors[0], alpha=0.7)
        legend = self.axd.legend()
        legend.get_texts()[0].set_text(str(round(velowh / 3600, 2)) + " Wh Energie")

    def set_visible(self, param):
        self.axd.set_visible(param)


class My_tacho:
    def __init__(self, axd, pos):
        self.axd = axd
        self.axd.set_position(pos)
        self.tacho_init(axd, 44, "Stromvelo", "W", colr=cm.winter_r)

    @staticmethod
    def tacho_init(axes, tiks=220, titel="", einheit="W", colr=cm.viridis):
        left, width = .25, .5
        bottom, height = .25, .5
        right = left + width
        top = bottom + height
        colors = colr(np.linspace(0, 1, tiks))
        #  fig, ax = plt.subplots(subplot_kw=dict(projection="polar"));
        if tiks != 0:
            mpitiks = math.pi / tiks * math.pi * (math.pi / 8)
            axes.bar(x=np.linspace(-math.pi / 8, math.pi + math.pi / 8 - mpitiks, tiks), width=mpitiks, height=0.5,
                     bottom=2,
                     linewidth=0.5, edgecolor="white",
                     color=colors, align="edge")
        else:
            mpitiks = math.pi / 1 * math.pi * (math.pi / 8)
            axes.bar(x=np.linspace(-math.pi / 8, math.pi + math.pi / 8 - mpitiks, 1), width=mpitiks, height=0.5,
                     bottom=2,
                     linewidth=0.5, edgecolor="white",
                     color=colors, align="edge")

        axes.set_title(titel, y=0, horizontalalignment='center',
                       verticalalignment='center',
                       weight='bold',
                       color='blue',
                       fontsize=15)
        axes.text(0.5 * (left + right), 0.3 * (bottom + top), einheit,
                  horizontalalignment='center',
                  verticalalignment='center',
                  fontsize=15,
                  transform=axes.transAxes),
        axes.annotate(" ", xytext=(0, 0), xy=(0, 2),
                      arrowprops=dict(arrowstyle="wedge, tail_width=0.5", color="black", shrinkA=0),
                      bbox=dict(boxstyle="circle", facecolor="black", linewidth=2.0, ),
                      color="white", ha="center")

        axes.set_axis_off()

    @staticmethod
    def update(ax, value, y, beschr=5):
        _min = math.ceil(np.amin(y[0]) / 5) * 5.2
        _max = math.ceil(np.amax(y[0]) / 5) * 5.2
        if _max < 200:
            _max = 200
        if _min > -30:
                _min = -30
        time.sleep(0.5)
        annotations = [child for child in ax.get_children() if isinstance(child, mtxt.Annotation)]
        for an in annotations:
            an.remove()
        xi = round((math.pi + math.pi / 8) - ((value - _min) / (_max - _min) * (math.pi + math.pi / 4)), 2)
        for i in range(beschr):
            xi2 = (math.pi + math.pi / 8) - ((math.pi + math.pi / 4) / (beschr - 1.0001)) * i
            ax.annotate(str(int(round((_max - _min) / (beschr - 1.0001) * i + _min, 0))), xytext=(xi2, 2.8),
                        xy=(xi2, 2.5),
                        arrowprops=dict(arrowstyle="->", color="white", shrinkA=0),
                        color="black", ha="center")
        ann = ax.annotate(str(int(value)), xytext=(0, 0), xy=(xi, 2),
                          arrowprops=dict(arrowstyle="wedge, tail_width=0.5", color="black", shrinkA=0),
                          bbox=dict(boxstyle="circle", facecolor="black", linewidth=2.0),
                          color="white", weight='bold', ha="center", fontsize=15)

        return ann

    def set_visible(self, param):
        self.axd.set_visible(param)


class My_serial:
    def __init__(self):
        self.port = ""
        self.g_ser = None
        self.myString = "1.999,1.999,1.999,1.999,1.999,1.999,1.999"
        self.xi = 0
        self.dt = 1 / 60

    def get_usb_port(self):
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            self.g_ser = serial.Serial(port, 115200, timeout=0.3, stopbits=STOPBITS_ONE, bytesize=EIGHTBITS,
                                       parity=PARITY_NONE)
            i = 0
            print(port)
            self.reset_usb_device()
            while True:
                line = self.g_ser.readline()  # read a '\n' terminated line
                print(line)
                try:
                    if line.decode('utf-8') == '' and i < 20:
                        break
                except UnicodeDecodeError:
                    print('UnicodeDecodeError ')
                if line.decode('utf-8').startswith('AEV_METER '):
                    self.port = port
                    return
                if i > 100:
                    self.g_ser.close()
                    self.port = ""
                    self.g_ser = None
                    return
                i = i + 1
            self.g_ser.close()
        self.port = ""
        self.g_ser = None
        return

    def reset_usb_device(self):
        high = False
        low = True
        self.g_ser.dtr = low  # Non reset state
        self.g_ser.rts = high  # IO0=HIGH
        self.g_ser.dtr = self.g_ser.dtr  # usbser.sys workaround
        try:
            if not self.g_ser.isOpen():
                self.g_ser.open()
        except serial.serialutil.SerialException as e:
            print("Error Serial Open", e)
        self.g_ser.dtr = high  # Set dtr to reset state (affected by rts)
        self.g_ser.rts = low  # Set rts/dtr to the reset state
        self.g_ser.dtr = self.g_ser.dtr  # usbser.sys workaround
        # Add a delay to meet the requirements of minimal EN low time (2ms for ESP32-C3)
        time.sleep(0.02)
        self.g_ser.rts = high  # IO0=HIGH
        self.g_ser.dtr = self.g_ser.dtr  # usbser.sys workaround

    def get_url_string(self):
        self.myString = "1.999,1.999,1.999,1.999,1.999,1.999,1.999"
        try:
            if self.port == '':
                self.get_usb_port()
                print(self.port)
                if self.port == '':
                    return
            while True:
                line = self.g_ser.readline()
                print(line.decode('utf-8'))
                if line.decode('utf-8').startswith('AEV_METER '):
                    self.myString = line.decode('utf-8')
                    self.myString = self.myString.removeprefix("AEV_METER ")
                    self.myString = self.myString.removesuffix("\r\n")
                    self.myString = self.myString.replace("0.0", "0.1")
                    self.g_ser.flushInput()
                    return

        except SerialException:
            # do something
            self.myString = "1.999,1.999,1.999,1.999,1.999,1.999,1.999"
            if not (self.g_ser is None):
                self.g_ser.close()
            self.port = ''
            self.g_ser = None
            return

    def get_x_y(self):
        self.get_url_string()
        p = self.myString.split(",")

        self.xi = self.xi + self.dt

        yi = [0.01] * len(p)

        for __x in range(len(p)):
            yi[__x] = float(p[__x])
        return self.xi, yi

    def print_error(self, fig):
        if self.myString == "1.999,1.999,1.999,1.999,1.999,1.999,1.999":
            fig.suptitle('PC mit AEV_METER mittels USB Kabel verbinden', fontsize=14,
                         fontweight='bold')
            return False
        else:
            fig.suptitle('', fontsize=14, fontweight='bold')
            return True

    def reset(self):
        self.xi=0


class AEV_Meter:
    label = ['Stromvelo', 'PV Dach', 'PV Geländer', 'Netz', 'Batterie', 'Wärme Pumpe', 'Alg. Verb.']
    bar_colors = ['tab:blue', 'tab:orange', 'Yellow', 'tab:green', 'tab:purple', 'tab:red', 'tab:olive']
    inner = [["Velo"], ["Tacho"]]
    mosaic = [['Leistung', 'Bar', ],
              [inner, 'Sankey', ]]
    pos_velo_tacho = Bbox([[0.037, 0.05], [0.50, 0.42]])
    pos_sankey_bar = Bbox([[0.54, 0.05], [0.96, 0.96]])
    pos_leistung = Bbox([[0.037, 0.5], [0.50, 0.96]])
    plot_time = 15
    velowh = 0
    x: [float]
    x = [0]
    y = [[0.0]] * 7

    def save_x_y(self, xi, yi):
        self.x = np.append(self.x, xi)
        for __x in range(len(yi)):
            self.y[__x] = np.append(self.y[__x], yi[__x])

    def update_wh(self):
        self.velowh = self.velowh + self.y[0][-1]

    def remove_x_y(self):
        for __x in range(len(self.y)):
            self.y[__x] = np.delete(self.y[__x], [0])
        self.velowh = self.velowh - self.y[0][0]
        self.x = np.delete(self.x, [0])

    def reset(self):
        self.x = [0]
        self.y = [[0.0]] * 7
        self.velowh = 0

    @staticmethod
    def draw_flush_events(fig):
        fig.canvas.draw()
        fig.canvas.flush_events()


def main():
    mpl.rcParams['toolbar'] = 'None'
    aev_meter = AEV_Meter()
    my_serial = My_serial()

    plt.ion()
    fig, axd = plt.subplot_mosaic(aev_meter.mosaic,
                                  figsize=(5.5, 3.5), layout="constrained",
                                  per_subplot_kw={'Tacho': {"projection": "polar"}})

    xi, yi = my_serial.get_x_y()
    aev_meter.save_x_y(xi, yi)
    my_leistung = My_leistung(axd['Leistung'], aev_meter.bar_colors, aev_meter.label, aev_meter.x, aev_meter.y,
                              aev_meter.pos_leistung)
    my_velo = My_velo(axd['Velo'], aev_meter.bar_colors, aev_meter.label, my_leistung.get_line(),
                      aev_meter.pos_velo_tacho, aev_meter.x, aev_meter.y)
    my_sankey = My_sankey(axd['Sankey'], aev_meter.bar_colors, aev_meter.label, aev_meter.pos_sankey_bar)
    my_bar = My_bar(axd['Bar'], aev_meter.bar_colors, aev_meter.label, aev_meter.pos_sankey_bar)
    my_tacho = My_tacho(axd['Tacho'], aev_meter.pos_velo_tacho)

    aev_meter.draw_flush_events(fig)

    my_click = My_click(plt, aev_meter,my_serial)

    plt.show()

    while True:
        # try:
        xi, yi = my_serial.get_x_y()

        if my_serial.print_error(fig):
            aev_meter.save_x_y(xi, yi)
            my_leistung.update(aev_meter.plot_time, aev_meter.x, aev_meter.y)
            my_velo.update(aev_meter.plot_time, aev_meter.velowh, aev_meter.x, aev_meter.y)
            aev_meter.update_wh()
            my_bar.update(aev_meter.y)
            my_sankey.update(aev_meter.y)
            my_tacho.update(axd['Tacho'], aev_meter.y[0][-1], aev_meter.y, 8)

        if xi > aev_meter.plot_time:
            aev_meter.remove_x_y()

        if my_click.is_onof():
            my_tacho.set_visible(False)
            my_velo.set_visible(True)
        else:
            my_tacho.set_visible(True)
            my_velo.set_visible(False)

        if my_click.is_bar():
            my_sankey.set_visible(False)
            my_bar.set_visible(True)
        else:
            my_sankey.set_visible(True)
            my_bar.set_visible(False)

        aev_meter.draw_flush_events(fig)
        if not plt.get_fignums():
            break

    # except:
    #     print("Error")


main()
