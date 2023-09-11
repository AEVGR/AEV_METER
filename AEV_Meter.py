# importing libraries
import math
import time

import matplotlib as mpl
import matplotlib.lines
import matplotlib.pyplot as plt
import numpy as np
import serial.tools.list_ports
import matplotlib.text as mtxt
from matplotlib.pyplot import cm
from matplotlib.sankey import Sankey
from serial import STOPBITS_ONE, EIGHTBITS, PARITY_NONE, SerialException
from matplotlib.widgets import Button


def tachoInit(axes, tiks=220, titel="", einheit="W", colr=cm.viridis):
    def onclik(event):
        print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
              ('double' if event.dblclick else 'single', event.button,
               event.x, event.y, event.xdata, event.ydata))

    left, width = .25, .5
    bottom, height = .25, .5
    right = left + width
    top = bottom + height
    colors = colr(np.linspace(0, 1, tiks))
    #  fig, ax = plt.subplots(subplot_kw=dict(projection="polar"));
    if tiks != 0:
        mpitiks = math.pi / tiks * (math.pi) * (math.pi / 8)
        axes.bar(x=np.linspace(-math.pi / 8, math.pi + math.pi / 8 - mpitiks, tiks), width=mpitiks, height=0.5,
                 bottom=2,
                 linewidth=0.5, edgecolor="white",
                 color=colors, align="edge")
    else:
        mpitiks = math.pi / 1 * (math.pi) * (math.pi / 8)
        axes.bar(x=np.linspace(-math.pi / 8, math.pi + math.pi / 8 - mpitiks, 1), width=mpitiks, height=0.5, bottom=2,
                 linewidth=0.5, edgecolor="white",
                 color=colors, align="edge")

    axes.set_title(titel, y=0, horizontalalignment='center',
                   verticalalignment='center',
                   weight='bold',
                   color='blue',
                   fontsize=15)
    ann = axes.text(0.5 * (left + right), 0.3 * (bottom + top), einheit,
                    horizontalalignment='center',
                    verticalalignment='center',
                    fontsize=15,
                    transform=axes.transAxes),
    ann = axes.annotate(" ", xytext=(0, 0), xy=(0, 2),
                        arrowprops=dict(arrowstyle="wedge, tail_width=0.5", color="black", shrinkA=0),
                        bbox=dict(boxstyle="circle", facecolor="black", linewidth=2.0, ),
                        color="white", ha="center")

    axes.set_axis_off()


def tachoUpdate(ax, value, beschr=5, min=0, max=math.pi):
    time.sleep(0.5)
    annotations = [child for child in ax.get_children() if isinstance(child, mtxt.Annotation)]
    for an in annotations:
        an.remove()
    xi = round((math.pi + math.pi / 8) - ((value - min) / (max - min) * (math.pi + math.pi / 4)), 2)
    for i in range(beschr):
        xi2 = (math.pi + math.pi / 8) - ((math.pi + math.pi / 4) / (beschr - 1.0001)) * i
        p = ax.annotate(str(int(round((max - min) / (beschr - 1.0001) * i + min, 0))), xytext=(xi2, 2.8), xy=(xi2, 2.5),
                        arrowprops=dict(arrowstyle="->", color="white", shrinkA=0),
                        color="black", ha="center")
    ann = ax.annotate(str(int(value)), xytext=(0, 0), xy=(xi, 2),
                      arrowprops=dict(arrowstyle="wedge, tail_width=0.5", color="black", shrinkA=0),
                      bbox=dict(boxstyle="circle", facecolor="black", linewidth=2.0),
                      color="white", weight='bold', ha="center", fontsize=15)

    return ann


def get_usb_port():
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        g_ser = serial.Serial(port, 115200, timeout=0.1, stopbits=STOPBITS_ONE, bytesize=EIGHTBITS,
                              parity=PARITY_NONE)
        i = 0
        print(port)
        reset_usb_device(g_ser)
        while True:
            line = g_ser.readline()  # read a '\n' terminated line
            print(line)
            try:
                if line.decode('utf-8') == '' and i < 20:
                    break
            except:
                break
            if line.decode('utf-8').startswith('AEV_METER '):
                return port, g_ser
            if i > 100:
                g_ser.close()
                return "", None
            i = i + 1
        g_ser.close()
    return "", None


def reset_usb_device(g_ser):
    high = False
    low = True
    g_ser.dtr = low  # Non reset state
    g_ser.rts = high  # IO0=HIGH
    g_ser.dtr = g_ser.dtr  # usbser.sys workaround
    try:
        if not g_ser.isOpen():
            g_ser.open()
    except serial.serialutil.SerialException as e:
        print("Error Serial Open", e)
    g_ser.dtr = high  # Set dtr to reset state (affected by rts)
    g_ser.rts = low  # Set rts/dtr to the reset state
    g_ser.dtr = g_ser.dtr  # usbser.sys workaround
    # Add a delay to meet the requirements of minimal EN low time (2ms for ESP32-C3)
    time.sleep(0.02)
    g_ser.rts = high  # IO0=HIGH
    g_ser.dtr = g_ser.dtr  # usbser.sys workaround


def get_url_string(g_ser, g_port):
    _mystr = "1.999,1.999,1.999,1.999,1.999,1.999,1.999"
    try:
        if g_port == '':
            g_port, g_ser = get_usb_port()
            print(g_port)
            if g_port == '':
                return _mystr, g_ser, g_port
        while True:
            line = g_ser.readline()
            g_ser.flush()
            print(line.decode('utf-8'))
            if line.decode('utf-8').startswith('AEV_METER '):
                _mystr = line.decode('utf-8')
                _mystr = _mystr.removeprefix("AEV_METER ")
                _mystr = _mystr.removesuffix("\r\n")
                _mystr = _mystr.replace("0.0", "0.1")
                return _mystr, g_ser, g_port

    except SerialException:
        # do something
        try:
            _mystr = "1.999,1.999,1.999,1.999,1.999,1.999,1.999"
            g_ser.close()
            g_port = ''
            g_ser = None
        except:
            pass

        return _mystr, g_ser, g_port


def print_error(fig, p):
    if float(p[0]) == 1.999 and float(p[1]) == 1.999 and float(p[2]) == 1.999:
        fig.suptitle('PC mit AEV_METER mittels USB Kabel verbinden', fontsize=14,
                     fontweight='bold')
        return False
    else:
        fig.suptitle('', fontsize=14, fontweight='bold')
        return True


def main():
    global onof
    onof = True
    g_port: str = ''
    g_ser: serial.Serial = None
    mpl.rcParams['toolbar'] = 'None'
    label = ['Stromvelo', 'PV Dach', 'PV Geländer', 'Netz', 'Batterie', 'Wärme Pumpe', 'Alg. Verb.']

    bar_colors = ['tab:blue', 'tab:orange', 'Yellow', 'tab:green', 'tab:purple', 'tab:red', 'tab:olive']

    plot_time = 15
    xi = 0.0

    _mystr = "1.999,1.999,1.999,1.999,1.999,1.999,1.999"
    mystr, g_ser, g_port = get_url_string(g_ser, g_port)

    p = mystr.split(",")
    x: [float]
    x = [xi]
    y = [[0.01]] * len(p)

    for __x in range(len(p)):
        y[__x] = [float(p[__x])]
    plt.ion()
    inner = [
        ["Velo"],
        ["Velo1"],
    ]

    fig, axd = plt.subplot_mosaic([['Leistung', 'Sankey', ],
                                   [inner, 'Sankey', ]],
                                  figsize=(5.5, 3.5), layout="constrained",
                                  per_subplot_kw={'Velo1': {"projection": "polar"}})

    plt.get_current_fig_manager().set_window_title('Energieanhänger Monitor')

    print_error(fig, p)
    line = np.empty(len(y) + 1, matplotlib.lines.Line2D)
    for __x in range(len(y)):
        line[__x], = axd['Leistung'].plot(x, y[__x], label=label[__x], color=bar_colors[__x], linewidth=3)
    axd['Leistung'].grid(True)
    axd['Leistung'].legend()
    axd['Leistung'].set_ylabel('Watt')
    axd['Leistung'].set_xlabel('Minuten')
    axd['Leistung'].set_title('Leistungen', fontsize=15, color='blue', fontweight='bold')

    posvelo = axd['Velo'].get_position()
    posvelo.y0 = 0.05
    posvelo.x0 = 0.037
    posvelo.y1 = 0.42
    posvelo.x1 = 0.51
    axd['Velo'].set_position(posvelo)
    axd['Velo1'].set_position(posvelo)
    line[len(line) - 1], = axd['Velo'].plot(x, y[0], color=bar_colors[0], linewidth=3, label=label[0])
    fill_between_col = axd['Velo'].fill_between(x, 0, y[0])
    axd['Velo'].set_ylabel('Watt')
    axd['Velo'].set_xlabel('Minuten')
    axd['Velo'].legend()
    axd['Velo'].set_title('Stromvelo', fontsize=15, color='blue', fontweight='bold')
    axd['Velo'].grid(True)

    axd['Sankey'].cla()

    tachoInit(axd['Velo1'], 44, "Stromvelo", "W", colr=cm.winter_r)

    fig.canvas.draw()
    fig.canvas.flush_events()

    def button_on_click(event):
        manager_ = plt.get_current_fig_manager()
        manager_.full_screen_toggle()

    def button_on_click2(event):
        global onof
        onof = not (onof)

    # button
    axes = plt.axes([0.5, 0.5, 0.5, 0.5])
    bnext = Button(axes, '', color="white")
    bnext.on_clicked(button_on_click)
    axes.set(frame_on=False)
    axes2 = plt.axes([0, 0.00, 0.5, 0.5])
    bnext2 = Button(axes2, '', color="red")
    bnext2.on_clicked(button_on_click2)
    axes2.set(frame_on=False)
    plt.show()

    manager = plt.get_current_fig_manager()
    manager.full_screen_toggle()
    velowh = 0
    while True:
        try:
            mystr, g_ser, g_port = get_url_string(g_ser, g_port)
            dt = 1 / 60
            p = mystr.split(",")
            #    print(p)
            if print_error(fig, p):
                xi = xi + dt
                x = np.append(x, xi)
                for __x in range(len(p)):
                    y[__x] = np.append(y[__x], float(p[__x]))

                for __x in range(len(line) - 1):
                    line[__x].set_xdata(x)
                    line[__x].set_ydata(y[__x])

                line[len(line) - 1].set_xdata(x)
                line[len(line) - 1].set_ydata(y[0])

                maxx = plot_time
                if np.amax(x) >= plot_time:
                    maxx = np.amax(x)
                ymax = math.ceil(np.amax(y) / 5) * 5.2
                if ymax < 200:
                    ymax = 200
                ymin = math.floor(np.amin(y) / 5) * 5
                if ymin > -200:
                    ymin = -200

                axd['Leistung'].set_xlim(np.amin(x), maxx)
                axd['Leistung'].set_ylim(ymin, ymax)
                ymax = math.ceil(np.amax(y[0]) / 5) * 5.2
                if ymax < 200:
                    ymax = 200
                axd['Velo'].set_xlim(np.amin(x), maxx)
                axd['Velo'].set_ylim(-30, ymax)
                fill_between_col.remove()
                fill_between_col = axd['Velo'].fill_between(x, 0, y[0], facecolor=bar_colors[0], alpha=0.7)
                l = axd['Velo'].legend()
                l.get_texts()[0].set_text( str(round(velowh / 3600, 2)) + " Wh Energie")

                min_right = 0.0
                max_right = 0.0
                for __x in range(len(p)):
                    if float(p[__x]) > max_right:
                        max_right = float(p[__x])
                    if float(p[__x]) < min_right:
                        min_right = float(p[__x])

                axd['Sankey'].cla()
                axd['Sankey'].axis('off')
                axd['Sankey'].set_title('Leistungen Energieanhänger', fontsize=15, color='blue', fontweight='bold')

                px = [eval(i) for i in p]
                velowh = velowh + px[0]

                sankey = (Sankey
                          (ax=axd['Sankey'],
                           scale=7 / (np.amax(px) - np.amin(px)),
                           offset=1.2,
                           head_angle=120,
                           shoulder=0.2,
                           gap=1,
                           radius=0.3,
                           format='%i',
                           unit=' W'))

                for i in range(len(px)):
                    pl = 1
                    if i == 0:
                        sankey.add(facecolor="beige",
                                   flows=[px[0], px[1], px[2], px[3], px[4], px[5], px[6]],
                                   labels=[None, None, None, None, None, None, None],
                                   pathlengths=[pl, pl, pl, pl, pl, pl, pl],
                                   orientations=[math.copysign(1, px[0]), math.copysign(1, px[1]),
                                                 math.copysign(1, px[2]),
                                                 math.copysign(1, px[3]), math.copysign(1, px[4]),
                                                 math.copysign(1, px[5]),
                                                 math.copysign(1, px[6])],

                                   connect=(1, 0),
                                   rotation=90)

                    sankey.add(facecolor=bar_colors[i],
                               flows=[-px[i], px[i]],
                               labels=[None, label[i]],
                               orientations=[0, 0],
                               prior=0,
                               connect=(i, 0),
                               trunklength=5
                               )

                sankey.finish()
                tachoUpdate(axd['Velo1'], px[0], 8, -30, ymax)

            if xi > plot_time:
                for __x in range(len(y)):
                    y[__x] = np.delete(y[__x], [0])
                velowh = velowh - x[0]
                x = np.delete(x, [0])

            if onof:
                axd['Velo1'].set_visible(False)
                axd['Velo'].set_visible(True)
            else:
                axd['Velo1'].set_visible(True)

                axd['Velo'].set_visible(False)

            fig.canvas.draw()
            fig.canvas.flush_events()
        except:
            print("Error")


main()
