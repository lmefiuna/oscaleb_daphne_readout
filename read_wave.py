from oei import *
import matplotlib.pyplot as plt
import numpy as np
import warnings
import time

class readwave:
    def __init__(self, ep=4, afe=0, ch=0,plot=False):
        thing = OEI(f"192.168.0.200")
        thing.write(0x2000,[1234])
        wf=[]
        for i in range (20):
            doutrec = thing.read(0x40000000+(0x100000 * afe)+(0x10000 * ch)+i*50,50)[2:]
            for word in doutrec:
                wf.append(word)
        x = np.linspace(0.0, len(wf) * 16e-9, num=len(wf))
        if plot:
            plt.figure()
            plt.plot(x,wf,linewidth=0.6,label=f'{j} \t rms={np.round(np.mean(wf),2)}')
            plt.show()
        self.wf=np.array(wf)
        self.ep=ep
        self.ch=ch
        self.afe=afe
        thing.close()

def main():
    a=[ readwave(ep=0,afe=i,ch=j) for i in [0] for j in [6]]
    plt.figure()

    for h in range (len(a)):
        x = np.linspace(0.0, len(a[h].wf)*16, num=len(a[h].wf))
        plt.plot(x,a[h].wf, linewidth=0.5, label='channel {a[h].ch+a[h].afe*8} slot {a[h].ep}')
    plt.title("Waveforms")
    plt.xlabel("ns")
    plt.ylabel("ADC counts")
    plt.show()

if __name__ == "__main__":
    main()      