import os
import struct
import time
from logger import logger
from multiprocessing import Process
import mysql.connector
from oei import OEI
from daphne_channel import DaphneChannel
import registers as reg
from typing import Tuple

DAPHNE_IP="192.168.0.200"

STORE_WAVEFORMS=True
UPLOAD_TO_DB=True
UPLOAD_PERIOD_SECONDS=60
UPLOAD_BUFFER_PATH="/home/lmenode1/TFG_OSCAR_CALEB/oscaleb_readout/upload_buffer.csv"
UPLOAD_BUFFER_HEADER="timestamp,top,mid,bot\n"
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

def store_data_to_buffer(
        timestamp,
        trigger_rate_top,
        trigger_rate_mid,
        trigger_rate_bot):
    # logger.debug("Storing data to buffer")
    with open(UPLOAD_BUFFER_PATH, "a") as f:
        f.write(f"{timestamp},{trigger_rate_top},{trigger_rate_mid},{trigger_rate_bot}\n")

SQL_COMMAND = f"""\
INSERT INTO {DB_NAME}.{DB_TABLE}
(`timestamp`, TOP, MID, BOT)
VALUES(%s, %s, %s, %s);
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
            logger.info(f"upload_to_sql: flushed upload buffer.")
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
        upload_buffer_now):
    store_data_to_buffer(timestamp,
                         trigger_rate_top,
                         trigger_rate_mid,
                         trigger_rate_bot)
    if upload_buffer_now:
        upload_buffer_to_sql()

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

    last_upload_time = None

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

        if UPLOAD_TO_DB:
            cuentas_top = 0
            cuentas_mid = 0
            cuentas_bot = 0

            if CH_TOP_ENABLE:
                cuentas_top = channel_top.cuentas
            if CH_MID_ENABLE:
                cuentas_mid = channel_mid.cuentas
            if CH_BOT_ENABLE:
                cuentas_bot = channel_bot.cuentas

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
        print(f"Canal\tThreshold\tCuentas\tCeros")
        for ch in channels:
            print(f"{ch.identifier}\t{ch.threshold_adc_units}\t\t{ch.cuentas}\t{ch.contador_ceros}")
        print()    
        print(f"Current Timestamp: {inicio_int}")
        print(f"Delta time:\t{time.time()-inicio}")


if __name__ == "__main__":
    main()
