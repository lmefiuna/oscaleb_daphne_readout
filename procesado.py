from matplotlib.colors import Normalize
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as signal
from scipy.stats import gaussian_kde


def suavizar_waveforms(ondas: np.ndarray):
    print('suavizando waveforms')
    ondas_suavizadas = []
    for onda in ondas:
        onda_suavizada = signal.savgol_filter(onda, 7, 1)
        ondas_suavizadas.append(onda_suavizada)
    return np.array(ondas_suavizadas, dtype=np.int16)

def transformar_waveforms(ondas: np.ndarray):
    print('transformando waveforms')
    return ondas*0.80+4100

def plotear_waveforms(ondas: np.ndarray, titulo: str, **kwargs):
    """ activar antes la figura o subplot en el cual se quiere plotear"""
    print('ploteando waveforms')
    fs = 62.5e6  # Frecuencia de muestreo en Hz
    ts = 1 / fs  # Periodo de muestreo en segundos
    num_samples = 64  # Número total de muestras
    pretrigger_samples = num_samples // 2  # Número de muestras antes del trigger (50%)

    # Generar el vector de tiempo
    time_vector = np.linspace(-pretrigger_samples * ts, (num_samples - pretrigger_samples - 1) * ts, num_samples)

    plt.ylabel('ADU', fontsize=15)
    plt.title(titulo ,fontsize=15)
    plt.xlabel('tiempo [us]',fontsize=15)
    for onda in ondas:
        plt.plot(time_vector,onda, **kwargs)

def plotear_waveforms_step(ondas: np.ndarray, **kwargs):
    """ activar antes la figura o subplot en el cual se quiere plotear"""
    print('ploteando waveforms step')
    for onda in ondas:
        plt.step(range(len(onda)), onda, **kwargs)

def generar_histograma_por_cantidad_bins(ondas: np.ndarray, cantidad_bines: int):
    bin = np.linspace(2500, 11250, cantidad_bines)
    amplitudes = []
    for segmento in ondas:
        amplitudes.append(max(segmento))
    counts, bins = np.histogram(amplitudes, bin, density=False)
    return counts, bins

def generar_histograma(ondas: np.ndarray):
    print('generando histograma')
    bin = list(range(0, 2**14, 1))
    amplitudes = []
    for segmento in ondas:
        amplitudes.append(max(segmento))
    counts, bins = np.histogram(amplitudes, bin, density=False)
    return counts, bins

def filtrar_por_baseline(ondas: np.ndarray):
    print('filtrando por baseline')
    filtradas = []
    for onda in ondas:
        if any(onda[:14] > 6000):
            continue
        filtradas.append(onda)
    return np.array(filtradas)

def filtrar_por_pico_maximo(ondas: np.ndarray):
    print('filtrando por pico maximo')
    filtradas = []
    for onda in ondas:
        if any(onda[30:40] > 12000):
            continue
        filtradas.append(onda)
    return np.array(filtradas)

def filtrar_senoidales(ondas: np.ndarray):
    print('filtrando senoidales')
    filtradas = []
    for onda in ondas:
        if any(onda[34:38] < 5930):
            continue
        filtradas.append(onda)
    return np.array(filtradas)

def corregir_segmento_final(ondas: np.ndarray):
    print('corrigiendo segmento final')
    for onda in ondas:
        if onda[63] > onda[62]:
            onda[63] = onda[61]
        else:
            onda[63] = 2*onda[62] - onda[61]
    return ondas

def plotear_con_colores(ondas: np.ndarray):
    print('ploteando con colores')
    norm = Normalize(vmin=0, vmax=1)
    cmap = plt.get_cmap('spring')

    for i in range(ondas.shape[0]):
        density = (i + 1) / ondas.shape[0]
        plt.plot(ondas[i], color=cmap(norm(density)), alpha=0.5, lw=0.03)

def plotear_con_colores_v2(ondas: np.ndarray, titulo: str):
    print('ploteando con colores v2')
    counts, bins = generar_histograma(ondas)
    norm = Normalize(vmin=0, vmax=0.5)
    cmap = plt.get_cmap('hot')

    fs = 62.5e6  # Frecuencia de muestreo en Hz
    ts = 1 / fs  # Periodo de muestreo en segundos
    num_samples = 64  # Número total de muestras
    pretrigger_samples = num_samples // 2  # Número de muestras antes del trigger (50%)

    # Generar el vector de tiempo
    time_vector = np.linspace(-pretrigger_samples * ts, (num_samples - pretrigger_samples - 1) * ts, num_samples)

    plt.ylabel('ADU', fontsize=15)
    plt.title(titulo ,fontsize=15)
    plt.xlabel('tiempo [us]',fontsize=15)

    for i in range(ondas.shape[0]):
        maximo = max(ondas[i])
        densidad = 0
        for j in range(len(bins)):
            if maximo == bins[j]:
                densidad = counts[j]
                # print(maximo, densidad)
                break
        # plt.plot(ondas[i], color=cmap(norm(densidad)), alpha=0.5, lw=0.03)
        plt.plot(time_vector, ondas[i], color=cmap(norm(densidad/max(counts))), alpha=0.5, lw=0.03)
        # plt.plot(ondas[i], color=cmap(norm(densidad/max(counts))), alpha=0.5, lw=0.03)
        # plt.plot(ondas[i], color=cmap(norm(densidad)), alpha=0.5, lw=0.03)


cobalto_wf = np.load('./cobalto.npy')
cesio_wf = np.load('./cesio.npy')
americio_wf = np.load('./americio.npy')
bario_wf = np.load('./bario.npy')
cobalto_new_wf = np.load('./cobalto_new.npy')

cobalto_suavizados = np.load('./cobalto_suavizado.npy')
americio_suavizados = np.load('./americio_suavizado.npy')
cesio_suavizados = np.load('./cesio_suavizado.npy')
bario_suavizados = np.load('./bario_suavizado.npy')
estroncio_wf = np.load('./sr-303_10000_waves.npy')

# americio_suavizados = suavizar_waveforms(
#         filtrar_por_baseline(
#             transformar_waveforms(
#                 corregir_segmento_final(
#                     cobalto_wf[:]))))

# np.save('cobalto_suavizado', americio_suavizados)
# exit()
plt.tight_layout()
print(estroncio_wf.shape)
# plt.figure()
# plt.subplot(211)
# americio_filtrados = filtrar_por_baseline(cobalto_wf)
# americio_suavizados = suavizar_waveforms(americio_filtrados)
# americio_filtrados = np.array([onda for onda in cobalto_wf[:1000] if max(onda) <= 3000])
# onda_suavizada = suavizar_waveforms(cobalto_wf[:1])
# plotear_con_colores(cobalto_suavizados[:10000])
plotear_waveforms(corregir_segmento_final(estroncio_wf[:100]), 'Cs-137', color='b', alpha=0.5, lw=0.03)
# plt.subplot(212)
# plotear_waveforms(corregir_segmento_final(cobalto_wf[:100]), color='b', lw=0.60, alpha=0.5)
# plotear_waveforms(estroncio_wf, color='b', lw=0.05, alpha=0.12)
# plotear_waveforms(americio_suavizados, color='r', lw=0.05)
# plotear_waveforms(suavizar_waveforms(cobalto_wf[:100]), color='r', lw=0.05)

# plt.figure()
# plt.subplot(211)
# counts, bins = generar_histograma(cobalto_wf)
# plt.plot(bins[:-1], counts, color='b', alpha=0.8)

# plt.subplot(212)
# counts, bins = generar_histograma_por_cantidad_bins(americio_suavizados, 4000)
# plt.plot(bins[:-1], counts, color='r', alpha=0.8)


plt.show()