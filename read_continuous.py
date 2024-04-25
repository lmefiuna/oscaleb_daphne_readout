import os
import sys
import struct
import time
from logger import logger
from multiprocessing import Process
import matplotlib.pyplot as plt
import numpy as np
import mysql.connector
from oei import OEI
from daphne_channel import DaphneChannel
import registers as reg
from typing import Tuple

DAPHNE_IP="192.168.0.200"

STORE_WAVEFORMS=False
LOAD_DATA_TO_DB=False
UPLOAD_BUFFER_PATH="/home/lmenode1/TFG_OSCAR_CALEB/oscaleb_readout/upload_buffer.csv"
LOG_TO_FILE=True
LOG_FILE_PATH="/home/lmenode1/TFG_OSCAR_CALEB/oscaleb_readout/.log"

CH_TOP_ENABLE=True
CH_MID_ENABLE=True
CH_BOT_ENABLE=True

CH_TOP_THRESHOLD_ADC_UNITS=8120
CH_MID_THRESHOLD_ADC_UNITS=7819
CH_BOT_THRESHOLD_ADC_UNITS=7899

DB_USER="root"
DB_PASSWORD=""
DB_HOST="127.0.0.1"
DB_NAME=""
DB_TABLE=""

def write_to_file(ts, wf, filename):
    cuentas = len(wf)//128
    segmentos = [wf[i:i+128] for i in range(0, cuentas*128, 128)]

    with open(f"./waveforms/{filename}.dat", "wb") as f:
        for i in range(len(segmentos)):
            f.write(struct.pack(">I", ts[i]))
            for sample in segmentos[i]:
                f.write(struct.pack(">H", sample))

SQL_COMMAND = """\
INSERT INTO ()
(`timestamp`, TOP, MID, BOT)
VALUES(%s, %s, %s, %s);
"""

def insert_to_sql(timestamp, trigger_rate_top, trigger_rate_mid, trigger_rate_bot):
    connection = mysql.connector.connect(
        user="root",
        password="",
        host="127.0.0.1",
        database="")
    
    cursor = connection.cursor()
    cursor.execute(SQL_COMMAND, (timestamp, trigger_rate_top, trigger_rate_mid, trigger_rate_bot))
    connection.commit()
    cursor.close()
    connection.close()
    # if connection and connection.is_connected():
    #     with connection.cursor() as cursor:
            # result = 


def main():
    channel_top = DaphneChannel(
        "TOP",
        reg.FIFO_TOP_ADDR,
        reg.FIFO_TOP_TS_ADDR,
        reg.TOP_THRESHOLD_ADDR,
        CH_TOP_THRESHOLD_ADC_UNITS)
    
    channel_mid = DaphneChannel(
        "MID",
        reg.FIFO_MID_ADDR,
        reg.FIFO_MID_TS_ADDR,
        reg.MID_THRESHOLD_ADDR,
        CH_MID_THRESHOLD_ADC_UNITS)

    channel_bot = DaphneChannel(
        "BOT",
        reg.FIFO_BOT_ADDR,
        reg.FIFO_BOT_TS_ADDR,
        reg.BOT_THRESHOLD_ADDR,
        CH_BOT_THRESHOLD_ADC_UNITS)
    
    channels = []
    if CH_TOP_ENABLE:
        channels.append(channel_top)
    if CH_MID_ENABLE:
        channels.append(channel_mid)
    if CH_BOT_ENABLE:
        channels.append(channel_bot)

    channels: Tuple[DaphneChannel] = tuple(channels)
    
    thing = OEI(DAPHNE_IP)

    for channel in channels:
        channel.write_threshold_value(thing)
        channel.empty_fifos(thing)

    # TODO: leer thresholds cuando este listo en el fpga
    # print("SELF-TRIGGER THRESHOLD %d" % thing.read(0x00006000, 1)[2])

    logger.debug("Setting self trigger mode")
    thing.write(reg.SELF_TRIGGER_MODE_ADDR, [1234])

    while True:
        inicio = time.time()
        
        for channel in channels:
            channel.contador_ceros = 0
            channel.cuentas = 0
            channel.waveform_data = tuple()
            channel.timestamp_data = tuple()
        
        ahora = time.time()
        
        while ahora - inicio < 1.0:
            ahora = time.time()
            try:
                for channel in channels:
                    timestamp, waveform = channel.read_waveform(thing)
                    todo_ceros = True
                    for i in range(10):
                        if waveform[i] != 0:
                            todo_ceros = False
                            break
                    if not todo_ceros:
                        channel.waveform_data = (*channel.waveform_data, *waveform)
                        channel.timestamp_data = (*channel.timestamp_data, *timestamp)
                    else:
                        #TODO: ver si es necesario hacer un sleep
                        channel.contador_ceros += 1

            except TimeoutError as te:
                logger.warning(f"Timeout error: {te}")
                continue

        inicio_int = int(inicio)

        for ch in channels:
            ch.cuentas = len(ch.waveform_data)//128

        if STORE_WAVEFORMS:
            for ch in channels:
                if len(ch.waveform_data) > 0:
                    write_process = Process(target=write_to_file, args=(
                        ch.timestamp_data, ch.waveform_data, f"{inicio_int}_{ch.identifier}"))
                    write_process.start()

        # if load_to_sql:
        #     if len(wf) > 0:
        #         load_to_sql_process = Process(target=insert_to_sql, args=(inicio_int, cuentas, 0, 0))
        #         load_to_sql_process.start()
        os.system("clear")
        # with open("upload_buffer.csv", "at") as f:
        #     f.write(f"{inicio_int},{cuentas}\n")
        print("======= Mango/DAPHNE Acquisition System =======")
        print()
        print(f"Uploading to DB:\t{LOAD_DATA_TO_DB}")
        print(f"Storing Waveforms:\t{STORE_WAVEFORMS}")
        print()
        print(f"Canal\tCuentas\tCeros")
        for ch in channels:
            print(f"{ch.identifier}:\t{ch.cuentas}\t{ch.contador_ceros}")
        print()    
        print(f"Current Timestamp: {inicio_int}")
        print(f"Delta time:\t{time.time()-inicio}")


if __name__ == "__main__":
    main()
