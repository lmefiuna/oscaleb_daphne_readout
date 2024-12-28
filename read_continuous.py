import os
import struct
import time
import copy
import datetime
from logger import logger
from multiprocessing import Process, Manager
from multiprocessing.managers import ValueProxy
import mysql.connector
from oei import OEI
from daphne_channel import DaphneChannel
import registers as reg
from typing import Tuple, List
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from ctypes import c_bool

DAPHNE_IP="192.168.0.200"


PLOT_HISTOGRAMS = True
STORE_WAVEFORMS=False
STORE_HEADER_COMMENT=input("Comment: ")
STORE_WAVEFORMS_DIR="/home/lmenode1/TFG_OSCAR_CALEB/oscaleb_readout/25x25"
UPLOAD_TO_DB=False
UPLOAD_PERIOD_SECONDS=10
UPLOAD_BUFFER_PATH="/home/lmenode1/TFG_OSCAR_CALEB/oscaleb_readout/upload_buffer.csv"
UPLOAD_BUFFER_HEADER="timestamp,top,mid,bot,top_amp,mid_amp,bot_amp\n"
LOG_TO_FILE=True
LOG_FILE_PATH=".log"


CH_TOP_ENABLE=True
CH_MID_ENABLE=False
CH_BOT_ENABLE=False

# con offset:
CH_TOP_THRESHOLD_ADC_UNITS=5980

CH_MID_THRESHOLD_ADC_UNITS=7223-000
CH_BOT_THRESHOLD_ADC_UNITS=7396-000
# sin offset:
# CH_TOP_THRESHOLD_ADC_UNITS=7391
# CH_MID_THRESHOLD_ADC_UNITS=7207
# CH_BOT_THRESHOLD_ADC_UNITS=7414

CH_TOP_BASELINE=8150
CH_MID_BASELINE=8150
CH_BOT_BASELINE=8150

DB_USER="root"
DB_PASSWORD=""
DB_HOST="127.0.0.1"
DB_NAME=""
DB_TABLE=""

def write_to_file(channel: DaphneChannel, pc_timestamp: float, comment: str=None):
    wf = channel.waveform_data
    ts = channel.timestamp_data
    filename = f"{int(pc_timestamp)}_{channel.IDENTIFIER}"

    cuentas = len(wf)//DaphneChannel.WAVEFORM_LENGTH
    segmentos = [wf[i:i+DaphneChannel.WAVEFORM_LENGTH] for i in range(0, cuentas*DaphneChannel.WAVEFORM_LENGTH, DaphneChannel.WAVEFORM_LENGTH)]

    pc_datetime = datetime.datetime.fromtimestamp(pc_timestamp)

    with open(f"{STORE_WAVEFORMS_DIR}/{filename}.dat", "wb") as f:
        f.write((f"Source,{channel.IDENTIFIER}\n").encode())
        f.write((f"StartAcquisitionDatetime,{pc_datetime}\n").encode())
        f.write((f"TriggerLevelADU,{channel.threshold_adc_units}\n").encode())
        f.write((f"BaselineLevelADU,{channel.baseline_adc_units}\n").encode())
        f.write((f"Cuentas,{channel.cuentas}\n").encode())
        if comment:
            f.write((f"Comment,{comment}\n").encode())
        f.write((f"WaveformsData,\n").encode())
        for i in range(len(segmentos)):
            f.write(struct.pack(">I", ts[i]))
            for sample in segmentos[i]:
                f.write(struct.pack(">H", sample&0x3FFF))


def plot_data(channels_last, update_plot: ValueProxy):
        x_plot = np.array(range(DaphneChannel.WAVEFORM_LENGTH))
        # global channels_last
        with open("plot.log", "at") as f:
            # f.write(f"{x_plot}\n")
            try:
                plt.ion()
                figure, (ax1, ax2) = plt.subplots(1, 2)
                figure.tight_layout()
                # ax.plot(x_plot, np.zeros(DaphneChannel.WAVEFORM_LENGTH))
                figure.canvas.draw()
                figure.canvas.flush_events()
                # f.write("plt.ion!\n")
                # lines: List[Line2D] = []
                # for i in len(channels_last):
                #     lines.append(ax.plot(x_plot, np.zeros(DaphneChannel.WAVEFORM_LENGTH))[0])
                # f.write(f"len(lines) {len(lines)}\n")

                #ax1.set_xlim(6000,2**14)
                ax1.set_xlim(CH_TOP_THRESHOLD_ADC_UNITS-100,2**14)
                ax1.set_ylim(0, 0.1)
                # ax1.set_yscale("log")

                ax2.set_xlim(0, DaphneChannel.WAVEFORM_LENGTH)
                ax2.set_ylim(4000, 15000)
                xlim1 = ax1.get_xlim()
                ylim1 = ax1.get_ylim()
                
                xlim2 = ax2.get_xlim()
                ylim2 = ax2.get_ylim()

                # para señales positivas debe ir desde threshold hasta 2**14,
                # para señales negativas desde 0 hasta threshold
                bin= list(range(CH_TOP_THRESHOLD_ADC_UNITS,2**14,1))
                #bin= list(range(CH_TOP_THRESHOLD_ADC_UNITS,2**14,(16383-CH_TOP_THRESHOLD_ADC_UNITS)//4096))
                # f.write(f"{bin}\n")

                frecuencias = np.array(2**14, dtype=np.int32)
                aux         = np.zeros(len(bin)-1)
                counts, bins = np.histogram(aux,bin)
                frecuencias_acumuladas=aux

                def on_press(event):
                    if event.key == "g":
                        try:
                            times = int(time.time())
                            f.write("Saving histogram..."+"\n")
                            np.save(f"histogramas/{times}_bin", bin)
                            np.save(f"histogramas/{times}_histograma", frecuencias_acumuladas)
                        except Exception as e:
                            f.write(str(e) + "\n")

                figure.canvas.mpl_connect('key_press_event', on_press)
                # f.write(f"{aux}\n")

                # ax.autoscale(enable=False, tight=False)
                # ax.autoscale_view(scaley=False, tight=False)
                # inicio = time.time()
                while True:
                    # f.write(f"{update_plot.value}\n")
                    # update_plot.acquire()
                    # ahora = time.time()
                    # if ahora - inicio < 1:
                    #     continue

                    _update_plot = update_plot.value
                    if not _update_plot:
                        continue

                    # figure.suptitle()
                    # inicio = ahora
                    # f.write(f"{_update_plot}\n")
                    # update_plot.release()
                    # if _update_plot:
                    # f.write("plotting!\n")
                    len(channels_last[0].waveform_data) and ax1.cla()
                    ax1.set_xlim(*xlim1)
                    ax1.set_ylim(*ylim1)
                    # ax1.set_yscale("log")

                    ax2.cla()
                    ax2.set_xlim(*xlim2)
                    ax2.set_ylim(*ylim2)
                    # plt.cla()

                    for ii in range(len(channels_last)):
                        cuentas = len(channels_last[ii].waveform_data)//DaphneChannel.WAVEFORM_LENGTH
                        if cuentas == 0:
                            continue
                        wf = channels_last[ii].waveform_data
                        segmentos = [wf[i:i+DaphneChannel.WAVEFORM_LENGTH] for i in range(0, cuentas*DaphneChannel.WAVEFORM_LENGTH, DaphneChannel.WAVEFORM_LENGTH)]
                        amplitudes, undershoots=[],[]

                        max_waves = 10 if cuentas >= 10 else cuentas
                        i = 0
                        filtrados = 0
                        for segmento in segmentos[:]:
                            if len(segmento) == 0:
                                continue
                            a1 = np.array(segmento[:22])
                            # if a < 2**13 or a > 8200:
                                # continue
                            # baseline = int(np.mean(segmento[0:20]))
                            # if any(a > 8250) or any(a < 8150):
                            if  any(np.array(segmento[:24]) > 5960):
                                filtrados += 1
                                continue
                            if any(np.array(segmento) < 5900):
                                filtrados += 1
                                continue
                            undershoot = max(segmento)
                            undershoots.append(undershoot)
                            # if i < 50:
                            ax2.plot(x_plot, segmento, lw=0.05, color='b', alpha=0.8)
                            # i += 1
                            #undershoots.append(baseline- undershoot)

                        #     minimo = min(segmento[20:-20]) 
                        #     if  (8100<baseline<8220):
                        #         amplitud = abs (minimo - baseline)
                        #         undershoot = abs(maximo - baseline)
                        #         amplitudes.append(amplitud)
                        print(f"{filtrados}/{cuentas}")
                        counts, bins = np.histogram(undershoots, bin, density=False)
                        frecuencias_acumuladas = frecuencias_acumuladas + counts
                        # f.write(str(frecuencias_acumuladas)+"\n")
                        # for i in range(len(frecuencias_acumuladas)):
                        #     if frecuencias_acumuladas[i] > 0.1:
                        #         frecuencias_acumuladas[i] = 0.1

                        ax1.plot(bins[:-1], frecuencias_acumuladas, lw=0.5)
                        ax1.set_ylim(0, max(frecuencias_acumuladas))
                            # f.write(str(segmento))
                    #  for i in range(0, cuentas*DaphneChannel.WAVEFORM_LENGTH, DaphneChannel.WAVEFORM_LENGTH)]
                    #     lines[i].set_xdata(x_plot)
                    #     # f.write(str(ch.waveform_data))
                    #     lines[i].set_ydata(channels_last[i].waveform_data)
                    
                    ax2.text(0.95, 0.01, datetime.datetime.fromtimestamp(time.time()),
                    verticalalignment='bottom', horizontalalignment='right',
                    transform=ax2.transAxes,
                    #fontsize=15
                    )

                    figure.canvas.draw()
                    figure.canvas.flush_events()
                    ylim1 = ax1.get_ylim()
                    xlim1 = ax1.get_xlim()
                    ylim2 = ax2.get_ylim()
                    xlim2 = ax2.get_xlim()
                    f.flush()
                    # time.sleep(0.05)
            except Exception as e:
                print(str(e))
                f.write(str(e)+"\n")

def store_data_to_buffer(
        timestamp,
        trigger_rate_top,
        trigger_rate_mid,
        trigger_rate_bot,
        sum_amplitude_top,
        sum_amplitude_mid,
        sum_amplitude_bot):
    #logger.debug(f"Storing data to buffer: {UPLOAD_BUFFER_PATH}")
    try:
        average_amplitude_top = 0 if trigger_rate_top == 0 else sum_amplitude_top//trigger_rate_top
        average_amplitude_mid = 0 if trigger_rate_mid == 0 else sum_amplitude_mid//trigger_rate_mid
        average_amplitude_bot = 0 if trigger_rate_bot == 0 else sum_amplitude_bot//trigger_rate_top
        with open(UPLOAD_BUFFER_PATH, "a") as f:
            f.write(f"{timestamp},{trigger_rate_top},{trigger_rate_mid},{trigger_rate_bot},{average_amplitude_top},{average_amplitude_mid},{average_amplitude_bot}\n")
    except Exception as e:
        logger.error(f"store_data_to_buffer({UPLOAD_BUFFER_PATH}): {e}")

SQL_COMMAND = f"""\
INSERT INTO {DB_NAME}.{DB_TABLE}
(`timestamp`, TOP, MID, BOT, TOP_AMPLITUDE_SUM, MID_AMPLITUDE_SUM, BOT_AMPLITUDE_SUM)
VALUES(%s, %s, %s, %s, %s, %s, %s);
"""

def upload_buffer_to_sql():
    try:
        with open(UPLOAD_BUFFER_PATH, "r") as f:
            header = f.readline()

            if header != UPLOAD_BUFFER_HEADER:
                f.seek(0)

            records_to_insert = []

            for line in f.readlines():
                record = tuple([int(x) for x in line.strip("\n").split(",")])
                records_to_insert.append(record)
    except FileNotFoundError:
        logger.error(f"upload_to_sql: buffer file {UPLOAD_BUFFER_PATH} not found")
    except Exception as e:
        logger.error(f"upload_to_sql: {e}")

    try:
        connection = mysql.connector.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            database=DB_NAME)

        cursor = connection.cursor()

        cursor.executemany(SQL_COMMAND, records_to_insert)
        connection.commit()
        logger.info(f"upload_to_sql: successfully uploaded {cursor.rowcount} records to table.")
        with open(UPLOAD_BUFFER_PATH, "w") as f:
            logger.info(f"upload_to_sql: flushed upload buffer: {UPLOAD_BUFFER_PATH}.")
            f.write(UPLOAD_BUFFER_HEADER)
    except mysql.connector.Error as error:
        logger.error(f"upload_to_sql: failed to insert record into MySQL table: {error}")
    except Exception as e:
        logger.error(f"upload_to_sql: {e}")
    finally:
        cursor.close()
        connection.close()

def store_data(timestamp,
        trigger_rate_top,
        trigger_rate_mid,
        trigger_rate_bot,
        sum_amplitude_top,
        sum_amplitude_mid,
        sum_amplitude_bot,
        upload_buffer_now):
    store_data_to_buffer(timestamp,
                         trigger_rate_top,
                         trigger_rate_mid,
                         trigger_rate_bot,
                         sum_amplitude_top,
                         sum_amplitude_mid,
                         sum_amplitude_bot)
    if upload_buffer_now:
        upload_buffer_to_sql()

def main():
    input(f"Is comment <<{STORE_HEADER_COMMENT}>> correct?")

    channel_top = DaphneChannel(
        "TOP",
        reg.FIFO_TOP_ADDR,
        reg.FIFO_TOP_TS_ADDR,
        reg.FIFO_TOP_WR_ADDR,
        reg.TOP_THRESHOLD_ADDR,
        CH_TOP_THRESHOLD_ADC_UNITS,
        CH_TOP_BASELINE)
    
    channel_mid = DaphneChannel(
        "MID",
        reg.FIFO_MID_ADDR,
        reg.FIFO_MID_TS_ADDR,
        reg.FIFO_MID_WR_ADDR,
        reg.MID_THRESHOLD_ADDR,
        CH_MID_THRESHOLD_ADC_UNITS,
        CH_MID_BASELINE)

    channel_bot = DaphneChannel(
        "BOT",
        reg.FIFO_BOT_ADDR,
        reg.FIFO_BOT_TS_ADDR,
        reg.FIFO_BOT_WR_ADDR,
        reg.BOT_THRESHOLD_ADDR,
        CH_BOT_THRESHOLD_ADC_UNITS,
        CH_BOT_BASELINE)
    
    channels = []
    if CH_TOP_ENABLE:
        channels.append(channel_top)
    if CH_MID_ENABLE:
        channels.append(channel_mid)
    if CH_BOT_ENABLE:
        channels.append(channel_bot)

    channels: Tuple[DaphneChannel] = tuple(channels)

    if PLOT_HISTOGRAMS:
        manager = Manager()
        channels_last = manager.list()
        update_plot = manager.Value("i", 0)
        # update_plot = Value("i", 0)
        # update_plot.acquire()
        # update_plot.value = 0
        # update_plot.release()

        for ch in channels:
            channels_last.append(copy.deepcopy(ch))
        # update_plot.append(0)
        plot_process = Process(target=plot_data, args=(channels_last, update_plot))
        plot_process.start()

    
    thing = OEI(DAPHNE_IP)


    logger.debug("Setting software trigger mode")
    thing.write(reg.SOFT_TRIGGER_MODE_ADDR, [1234])
    for channel in channels:
        channel.write_threshold_value(thing)
        channel.empty_fifos(thing)

    # TODO: leer thresholds cuando este listo en el fpga
    # print("SELF-TRIGGER THRESHOLD %d" % thing.read(0x00006000, 1)[2])


    last_upload_time = None

    logger.debug("Setting self trigger mode")
    thing.write(reg.SELF_TRIGGER_MODE_ADDR, [1234])
    while True:
        inicio = time.time()
        # update_plot.acquire()
        update_plot.set(0)
        # update_plot.release()
        # logger.debug("update plot = False")

        
        for channel in channels:
            channel.contador_ceros = 0
            channel.contador_no_validos = 0
            channel.cuentas = 0
            channel.waveform_data = []
            channel.timestamp_data = []
            channel.suma_amplitudes = 0

        ahora = time.time()

        # wr_ban_top=True
        # wr_ban_mid=True
        # wr_ban_bot=True

        # wf_top = []
        # wf_mid = []
        # wf_bot = []

        # ts_top = []
        # ts_mid = []
        # ts_bot = []


        while ahora - inicio < 1.0:
            ahora = time.time()
            try:
                readable_flags = thing.readf(reg.READABLE_FLAG_ADDR,1)[2]
                flags = (readable_flags & 0b1) , ((readable_flags >> 1) & 0b1) , ((readable_flags >> 2) & 0b1)

                channel_top.write_flag_firmware = flags[0]
                channel_mid.write_flag_firmware = flags[1]
                channel_bot.write_flag_firmware = flags[2]

                # logger.debug(f"{flags}")

                for ch in channels:
                    ch.fifo_last_write_address = thing.readf(ch.FIFO_WRITE_ADDRESS, 1)[2]
                    # logger.debug(f"{ch.IDENTIFIER} {ch.write_flag_software} {ch.write_flag_firmware} - {ch.fifo_last_write_address}")

                    # if ch.write_flag_software and ch.write_flag_firmware:
                    if ch.write_flag_firmware:
                        doutrec = thing.readf(ch.DATA_ADDRESS,
                                              DaphneChannel.WAVEFORM_LENGTH)[2:]
                        # ch.waveform_data.append(*doutrec)
                        if 0 in doutrec:
                            ch.contador_ceros += 1
                        else:
                            for sample in doutrec:
                                ch.waveform_data.append(sample&0x3FFF)
                        
                            doutts = thing.readf(ch.TIMESTAMP_ADDRESS, 1)[2]
                            ch.timestamp_data.append(doutts)
                            ch.cuentas += 1
                    # else:
                    #     ch.write_flag_software = False
                    #     if (2*DaphneChannel.WAVEFORM_LENGTH < \
                    #         abs(ch.fifo_last_write_address - ch.fifo_previous_last_write_address))\
                    #             and ch.fifo_previous_last_write_address != 50000:
                    #     # if (16*DaphneChannel.WAVEFORM_LENGTH < \
                    #     #     abs(ch.fifo_last_write_address - ch.fifo_previous_last_write_address)):
                    #         ch.write_flag_software = True
                    #         logger.debug("dentro del if")
                    #     ch.fifo_previous_last_write_address = ch.fifo_last_write_address
                # wr_address_top = thing.readf(reg.FIFO_TOP_WR_ADDR,1)[2]
                # wr_address_mid = thing.readf(reg.FIFO_MID_WR_ADDR,1)[2]
                # wr_address_bot = thing.readf(reg.FIFO_BOT_WR_ADDR,1)[2]

                # if wr_ban_top and top_flag:
                #     doutrec = thing.readf(reg.FIFO_TOP_ADDR,DaphneChannel.WAVEFORM_LENGTH)[2:]
                #     for word in doutrec:
                #         wf_top.append(word)

                #     doutts = thing.readf(reg.FIFO_TOP_TS_ADDR,1)[2]
                #     ts_top.append(doutts)                  



            except TimeoutError as te:
                logger.warning(f"Timeout error: {te}")
                continue

        inicio_int = int(inicio)

        for ch in channels:
            ch.cuentas = len(ch.waveform_data)//DaphneChannel.WAVEFORM_LENGTH
            segmentos = [ch.waveform_data[i:i+DaphneChannel.WAVEFORM_LENGTH] 
                         for i in range(0, ch.cuentas*DaphneChannel.WAVEFORM_LENGTH, DaphneChannel.WAVEFORM_LENGTH)]
            suma_amplitudes = 0
            for segmento in segmentos:
                amplitud = abs((min(segmento[5:-5]))-ch.baseline_adc_units)
                suma_amplitudes += amplitud
            ch.suma_amplitudes = suma_amplitudes

        if PLOT_HISTOGRAMS:
            # channels_last.clear()
            for i in range(len(channels)):
                channels_last[i] = copy.deepcopy(channels[i])
            # logger.debug("update plot = True")
            # update_plot.acquire()
            update_plot.set(1)
            # update_plot.release()


        if STORE_WAVEFORMS:
            for ch in channels:
                if len(ch.waveform_data) > 0:
                # if 0 in ch.waveform_data:
                    # logger.debug("guardando waveforms")
                    write_process = Process(target=write_to_file,
                                            args=(copy.deepcopy(ch),
                                                  inicio,
                                                  STORE_HEADER_COMMENT))
                    write_process.start()

        if UPLOAD_TO_DB:
            cuentas_top = 0
            cuentas_mid = 0
            cuentas_bot = 0
            suma_amplitudes_top = 0
            suma_amplitudes_mid = 0
            suma_amplitudes_bot = 0

            if CH_TOP_ENABLE:
                cuentas_top = channel_top.cuentas
                suma_amplitudes_top = channel_top.suma_amplitudes
            if CH_MID_ENABLE:
                cuentas_mid = channel_mid.cuentas
                suma_amplitudes_mid = channel_mid.suma_amplitudes
            if CH_BOT_ENABLE:
                cuentas_bot = channel_bot.cuentas
                suma_amplitudes_bot = channel_bot.suma_amplitudes

            upload_buffer_now = False

            if (last_upload_time is None) or \
                (time.time() - last_upload_time > UPLOAD_PERIOD_SECONDS):
                # logger.debug("last upload time is none or greater than last period")
                upload_buffer_now = True

            store_data_process = Process(target=store_data,
                    args=(inicio_int,
                        cuentas_top,
                        cuentas_mid,
                        cuentas_bot,
                        suma_amplitudes_top,
                        suma_amplitudes_mid,
                        suma_amplitudes_bot,
                        # 0,
                        # 0,
                        # 0,
                        upload_buffer_now))
            store_data_process.start()
            store_data_process.join()

            if upload_buffer_now:
                upload_buffer_now = False
                last_upload_time = time.time()
        os.system("clear")

        print("======= Mango/DAPHNE Acquisition System =======")
        print()
        print(f"Uploading to DB:\t{UPLOAD_TO_DB}")
        if UPLOAD_TO_DB:
            print(f"Uploading period:\t{UPLOAD_PERIOD_SECONDS} seg")

        print(f"Storing Waveforms:\t{STORE_WAVEFORMS}")
        print()
        print(f"Canal\tThresh\tRate\tNoVal\tCeros\tSumAmp\tAvgAmp")
        for ch in channels:
            print(f"{ch.IDENTIFIER}\t{ch.threshold_adc_units}\t{ch.cuentas}\t{ch.contador_no_validos}\t{ch.contador_ceros}\t{ch.suma_amplitudes}\t{ch.suma_amplitudes//ch.cuentas if ch.cuentas != 0 else 0}")
        print()    
        print(f"Current Timestamp: {inicio_int}")
        print(f"Delta time:\t{time.time()-inicio}")

        if UPLOAD_TO_DB and upload_buffer_now:
            print("Uploading to DB!")

        # for ch in channels:
        #     print(ch.timestamp_data)


if __name__ == "__main__":
    main()
