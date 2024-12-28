from daphne_channel import DaphneChannel
from oei import OEI
import registers as reg
import matplotlib.pyplot as plt
import time

DAPHNE_IP="192.168.0.200"


oei = OEI(DAPHNE_IP)

CH_TOP_BASELINE=8150
CH_MID_BASELINE=8150
CH_BOT_BASELINE=8150

CH_TOP_THRESHOLD_ADC_UNITS=8000
CH_MID_THRESHOLD_ADC_UNITS=7223-000
CH_BOT_THRESHOLD_ADC_UNITS=7396-000

channel_top = DaphneChannel(
    "TOP",
    0,
    reg.FIFO_TOP_ADDR,
    reg.FIFO_TOP_TS_ADDR,
    reg.FIFO_TOP_WR_ADDR,
    reg.TOP_THRESHOLD_ADDR,
    CH_TOP_THRESHOLD_ADC_UNITS)

channel_mid = DaphneChannel(
    "MID",
    1,
    reg.FIFO_MID_ADDR,
    reg.FIFO_MID_TS_ADDR,
    reg.FIFO_MID_WR_ADDR,
    reg.MID_THRESHOLD_ADDR,
    CH_MID_THRESHOLD_ADC_UNITS)

channel_bot = DaphneChannel(
    "BOT",
    2,
    reg.FIFO_BOT_ADDR,
    reg.FIFO_BOT_TS_ADDR,
    reg.FIFO_BOT_WR_ADDR,
    reg.BOT_THRESHOLD_ADDR,
    CH_BOT_THRESHOLD_ADC_UNITS)


channel = channel_top

channel.empty_fifos(oei)
channel.empty_fifos(oei)

oei.write(reg.SOFT_TRIGGER_MODE_ADDR, [1234])

for i in range(10):
    oei.write(reg.TRIGGER_SOFTWARE, [1234])
    doutrec = channel.read_waveform(oei)
    doutts = channel.read_timestamp(oei)
    for sample in doutrec:
        channel.waveform_data.append(sample&0x3FFF)

    channel.timestamp_data.append(doutts)
    time.sleep(0.1)


plt.plot(channel.waveform_data)
plt.vlines([x for x in range(0, len(channel.waveform_data), DaphneChannel.WAVEFORM_LENGTH)], 0, 2**14, lw=0.5)
plt.show()