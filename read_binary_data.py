import struct
import matplotlib.pyplot as plt
from daphne_channel import DaphneChannel


filepath = "./facen/cobalto/1723926082_TOP.dat"
HAS_HEADER = True
wf = []
segmentos = []
counter = 0
ts = []

WAVEFORM_LENGTH = DaphneChannel.WAVEFORM_LENGTH#128

with open(filepath, "rb") as f:
    if HAS_HEADER:
        header = b""
        while True:
            character = f.read(1)
            header += character
            if character == b"," and b"WaveformsData" in header:
                character = f.read(1) #newline
                break
        print(header.decode()[:-1])

    print(f.tell())
    while True:
        data = f.read(4 + 2*WAVEFORM_LENGTH)
        if data == b"":
            break

        ts.append(struct.unpack(">I", data[0:4]))

        segmento = []
        for i in range(4, 4 + 2*WAVEFORM_LENGTH, 2):
            sample = struct.unpack(">H", data[i:i+2])[0]
            segmento.append(sample)
            wf.append(sample)
        if wf[-1] == 0:
            wf[-1] = wf[-2]
            segmento[-1] = segmento[-2]
        segmentos.append(segmento)

print(f"Max: {max(segmentos[0])}\tMin: {min(segmentos[0])}")
plt.subplot(311)
for i in range(len(segmentos)):
    plt.plot(segmentos[i], lw=0.25)
plt.subplot(312)
plt.plot(ts, lw=0.25)

plt.subplot(313)
plt.plot(wf, lw=0.25)
plt.show()
