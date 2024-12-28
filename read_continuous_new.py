import os
import struct
import datetime
import time
from typing import Tuple
from oei import OEI
from daphne_channel import DaphneChannel
import registers as reg

CH_TOP_THRESHOLD_ADC_UNITS = 4000
CH_TOP_BASELINE = 8150

PLOT_HISTOGRAMS = True
STORE_WAVEFORMS = False

STORE_WAVEFORMS_DIR = "./waveforms"


def write_to_file(channel: DaphneChannel, pc_timestamp: float, comment: str = None):
    wf = channel.waveform_data
    ts = channel.timestamp_data
    filename = f"{int(pc_timestamp)}_{channel.IDENTIFIER}"

    cuentas = len(wf)//DaphneChannel.WAVEFORM_LENGTH
    segmentos = [wf[i:i+DaphneChannel.WAVEFORM_LENGTH]
                 for i in range(0, cuentas*DaphneChannel.WAVEFORM_LENGTH, DaphneChannel.WAVEFORM_LENGTH)]

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
                f.write(struct.pack(">H", sample & 0x3FFF))


def main():
    channel_top = DaphneChannel(
        "TOP",
        reg.FIFO_TOP_ADDR,
        reg.FIFO_TOP_TS_ADDR,
        reg.FIFO_TOP_WR_ADDR,
        reg.TOP_THRESHOLD_ADDR,
        CH_TOP_THRESHOLD_ADC_UNITS,
        CH_TOP_BASELINE)

    channels = []
    channels.append(channel_top)
    channels: Tuple[DaphneChannel] = tuple(channels)

    thing = OEI("192.168.0.200")

    thing.write(reg.SOFT_TRIGGER_MODE_ADDR, [1234])
    for channel in channels:
        channel.write_threshold_value(thing)
        channel.empty_fifos(thing)

    thing.write(reg.SELF_TRIGGER_MODE_ADDR, [1234])

    while True:
        inicio = time.time()
        print(inicio)

        for channel in channels:
            channel.contador_ceros = 0
            channel.contador_no_validos = 0
            channel.cuentas = 0
            channel.waveform_data = []
            channel.timestamp_data = []
            channel.suma_amplitudes = 0

        ahora = time.time()

        while ahora - inicio < 1.0:
            ahora = time.time()
            try:

                readable_flags = thing.readf(reg.READABLE_FLAG_ADDR, 1)[2]
                flags = (readable_flags & 0b1), \
                        ((readable_flags >> 1) & 0b1), \
                        ((readable_flags >> 2) & 0b1)

                channel_top.write_flag_firmware = flags[0]

                for ch in channels:
                    ch.fifo_last_write_address = thing.readf(
                        ch.FIFO_WRITE_ADDRESS, 1)[2]
                    if ch.write_flag_firmware:
                        doutrec = thing.readf(ch.DATA_ADDRESS,
                                              DaphneChannel.WAVEFORM_LENGTH)[2:]
                        # ch.waveform_data.append(*doutrec)
                        if 0 in doutrec:
                            ch.contador_ceros += 1
                        else:
                            for sample in doutrec:
                                ch.waveform_data.append(sample & 0x3FFF)

                            doutts = thing.readf(ch.TIMESTAMP_ADDRESS, 1)[2]
                            ch.timestamp_data.append(doutts)
                            ch.cuentas += 1
            except TimeoutError as e:
                print(e)
                continue

        os.system("clear")

        print("======= Mango/DAPHNE Acquisition System =======")
        print()

        print(f"Storing Waveforms:\t{STORE_WAVEFORMS}")
        print()
        print(f"Canal\tThresh\tRate\tNoVal\tCeros\tSumAmp\tAvgAmp")
        for ch in channels:
            print(f"{ch.IDENTIFIER}\t{ch.threshold_adc_units}\t{ch.cuentas}\t{ch.contador_no_validos}\t{ch.contador_ceros}\t{ch.suma_amplitudes}\t{ch.suma_amplitudes//ch.cuentas if ch.cuentas != 0 else 0}")
        print()
        print(f"Current Timestamp: {int(inicio)}")
        print(f"Delta time:\t{time.time()-inicio}")


if __name__ == '__main__':
    main()
