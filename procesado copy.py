import numpy as np
import scipy.signal as signal
from numpy.polynomial import polynomial
import pandas as pd

import matplotlib.pyplot as plt
import datashader as ds
import datashader.transfer_functions as tf

import time


def suavizar_waveforms(ondas: np.ndarray):
    ondas_suavizadas = []
    for onda in ondas:
        onda_suavizada = signal.savgol_filter(onda, 7, 1)
        ondas_suavizadas.append(onda_suavizada)
    return np.array(ondas_suavizadas, dtype=np.int16)


cobalto_wf = np.load('./cobalto.npy')
cesio_wf = np.load('./cesio.npy')
americio_wf = np.load('./americio.npy')
bario_wf = np.load('./bario.npy')
cobalto_new_wf = np.load('./cobalto_new.npy')

americio_suavizados = suavizar_waveforms(cobalto_wf[:1000])
df = pd.DataFrame(americio_suavizados)
# Following will append a nan-row and reshape the dataframe into two columns, with each sample stacked on top of each other
#   THIS IS CRUCIAL TO OPTIMIZE SPEED: https://github.com/bokeh/datashader/issues/286

# Append row with nan-values
df = df.concat(pd.DataFrame(
    [np.array([np.nan] * len(df.columns))], columns=df.columns, index=[np.nan]))

# Reshape
x, y = df.shape
arr = df.as_matrix().reshape((x * y, 1), order='F')
df_reshaped = pd.DataFrame(arr, columns=list(
    'y'), index=np.tile(df.index.values, y))
df_reshaped = df_reshaped.reset_index()
df_reshaped.columns.values[0] = 'x'

# Plotting parameters
x_range = (min(df.index.values), max(df.index.values))
y_range = (df.min().min(), df.max().max())
w = 1000
h = 750
dpi = 150
cvs = ds.Canvas(x_range=x_range, y_range=y_range, plot_height=h, plot_width=w)

# Aggregate data
t0 = time.time()
aggs = cvs.line(df_reshaped, 'x', 'y', ds.count())
print("Time to aggregate line data: {}".format(time.time()-t0))

# One colored plot
t1 = time.time()
stacked_img = tf.Image(tf.shade(aggs, cmap=["darkblue", "darkblue"]))
print("Time to create stacked image: {}".format(time.time() - t1))

# Save
f0 = plt.figure(figsize=(w / dpi, h / dpi), dpi=dpi)
ax0 = f0.add_subplot(111)
ax0.imshow(stacked_img.to_pil())
ax0.grid(False)
f0.savefig("stacked.png", bbox_inches="tight", dpi=dpi)
