import numpy as np

import matplotlib.pyplot as plt

am = np.load("./histogramas/1722735136_histograma_cobalto.npy")

ejex = np.load("./histogramas/1722733721_bin.npy")

plt.plot(ejex[0:-1],am)
plt.show()