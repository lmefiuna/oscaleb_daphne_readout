from oei import *
from multiprocessing import Process
import matplotlib.pyplot as plt
import numpy as np
import struct
import time

thing = OEI("192.168.0.200")
FIFO_WR_ADDR = 0x000000A

FIFO_TOP_ADDR = 0x80000000
FIFO_TOP_TS_ADDR = 0x80000010

FIFO_MID_ADDR = 0x90000000
FIFO_MID_TS_ADDR = 0x90000010

FIFO_BOT_ADDR = 0xA0000000
FIFO_BOT_TS_ADDR = 0xA0000010


def write_to_file(ts, wf, timestamp_inicio_int, plot=False):
    cuentas = len(wf)//128
    segmentos = [wf[i:i+128] for i in range(0, cuentas*128, 128)]

    with open(f"./waveforms/{timestamp_inicio_int}.dat", "wb") as f:
        for i in range(len(segmentos)):
            f.write(struct.pack(">I", ts[i]))
            for sample in segmentos[i]:
                f.write(struct.pack(">H", sample))

    if plot:
        figure = plt.figure()
        plt.subplot(211)
        wf_plot = []
        for segmento in segmentos:
            if segmento[-1] != 0:
                plt.plot(segmento, lw=0.25)
                wf_plot = (*wf_plot, *segmento)
            else:
                plt.plot(segmento[:-1], lw=0.25)
                wf_plot = (*wf_plot, *segmento[:-1])

        plt.subplot(212)
        # print(wf)
        plt.plot(np.array(wf_plot), lw=0.25)
        plt.savefig(f"./plots/{timestamp_inicio_int}.png", dpi=600)
        plt.close(figure)


def main():
    CANAL = FIFO_TOP_ADDR
    CANAL_TS = FIFO_TOP_TS_ADDR
    thing = OEI(f"192.168.0.200")
    thing.write(0x00006000, [7780])  # 8250 203A  SET threshold
    print("SELF-TRIGGER THRESHOLD %d" % thing.read(0x00006000, 1)[2])  # NACHO
    thing.write(0x00006010, [1234])

    print("emtpying fifo")
    for i in range(256):
        doutrec = thing.readf(CANAL, 128)[2:]
        doutts = thing.readf(CANAL_TS, 1)[2:]

    plot = False
    store = False

    while True:
        inicio = time.time()
        cuentas = 0
        # if plot:
        #     figure = plt.figure()
        wf = []
        ts = []
        ahora = time.time()
        contador_ceros = 0
        while ahora - inicio < 1.0:
            ahora = time.time()
            try:
                doutrec = thing.readf(CANAL, 128)[2:]
                doutts = thing.readf(CANAL_TS, 1)[2:]
                todo_ceros = True
                for i in range(10):
                    if doutrec[i] != 0:
                        todo_ceros = False
                        break
                if not todo_ceros:
                    wf = (*wf, *doutrec)
                    ts = (*ts, *doutts)
                else:
                    # print("sleeping")
                    contador_ceros += 1
                    time.sleep(0.05)

            except TimeoutError:
                print("se colgo")
                continue

        inicio_int = int(inicio)

        cuentas = len(wf)//128

        if store:
            if len(wf) > 0:
                write_process = Process(target=write_to_file, args=(
                    ts, wf, inicio_int, plot))
                write_process.start()
        print(f"{time.time()-inicio}\tTrigger Rate: {cuentas}\tCeros: {contador_ceros}")


if __name__ == "__main__":
    main()
