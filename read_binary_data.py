import struct
import matplotlib.pyplot as plt


filepath = "./waveforms/1713905826.dat"
wf = []
segmentos = []
counter = 0
ts = []

with open(filepath, "rb") as f:
    while True:
        data = f.read(4 + 2*128)
        if data == b"":
            break

        ts.append(struct.unpack(">I", data[0:4]))

        segmento = []
        for i in range(4, 4 + 2*128, 2):
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
