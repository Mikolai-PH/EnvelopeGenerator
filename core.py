"""
core.py
=======

SEKCJA ORYGINALNA — MATEMATYKA I LOGIKA NIEZMIENIONE.

Ten plik zawiera oryginalny skrypt `odwrocony_obwiednioskop.py` w całości.
Wprowadzone zostały WYŁĄCZNIE następujące zmiany, z których żadna nie dotyka
matematyki ani kolejności operacji:

  (1) Kod od linii `cdf=np.cumsum(x)*(t[1]-t[0])` do końca został objęty
      funkcją `run(x, new_filter_multiplier)` — czyli wcięty o 4 spacje.
      Żadna linia nie została usunięta, dodana ani przestawiona.

  (2) HOOK 1 — blok wyboru obwiedni (`x = rect(...)` itd.) jest zakomentowany;
      tablica `x` przychodzi jako argument funkcji `run`.

  (3) HOOK 2 — dwie linie:
          Factor1 = 44
          new_filter_multiplier = np.exp(-np.abs(freq)**Factor1)
      są zakomentowane; tablica `new_filter_multiplier` przychodzi jako
      argument funkcji `run`. Domyślnie aplikacja podaje dokładnie tę samą
      tablicę, którą wyliczyłby oryginał.

  (4) `plt.show()` zastąpione przez `return fig` (backend nieinteraktywny Agg).

  (5) `matplotlib.use("Agg")` na samej górze — wymóg serwera bez ekranu.

Nic poza powyższym nie zostało zmienione. `print()` z oryginału pozostają
nietknięte (aplikacja przechwytuje stdout i pokazuje je w interfejsie).
"""

import matplotlib
matplotlib.use("Agg")

# ==================== POCZĄTEK KODU ORYGINALNEGO ====================

################################Importy
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import cm
from matplotlib.ticker import MaxNLocator
import os
from matplotlib.ticker import FixedLocator, FixedFormatter
import numpy as np
import pandas
import glob
from scipy.signal import find_peaks
from scipy.interpolate import interp1d


########################################

################################Definicje Obwiedni początkowej

N=16348*4*2*2 +1
t=np.linspace(-4,4,N,endpoint=True)

def Gauss(x,mu,sigma):
    Norm=1/(np.sqrt(2*np.pi*sigma**2))
    return Norm*np.exp(-0.5*(x-mu)**2 / sigma**2)*2*np.pi

def pseudo_beta(x,dt,alpha):
    vals=(1-x**2)**alpha
    Norm=2*np.pi/(np.sum(vals)*dt)
    return vals*Norm


def rect(x,dt):
    vals = np.where(np.abs(x)<=0.5,1,0)
    Norm=2*np.pi/(np.sum(vals)*dt)
    return vals*Norm


def tri(x,dt, width=2.0):
    """Generuje puls trójkątny o zadanej szerokości (width) wyśrodkowany w x=0."""
    Norm=2*np.pi/(np.sum(vals)*dt)
    vals = np.where(
        np.abs(x) < width / 2, 1.0 - np.abs(x) / (width / 2), 0.0
    )
    return vals*Norm


def semicirc(x,dt, width=2.0):
    """Generuje puls półokrągły o zadanej szerokości (width) wyśrodkowany w t=x."""

    r = width / 2
    # Równanie górnej połowy okręgu przesunięte w pionie zależy od promienia
    # Tutaj normalizujemy wysokość pulsu do 1.0 w punkcie t=0


    vals = np.where(np.abs(x) < r, np.sqrt(1.0 - (x / r) ** 2), 0.0)
    Norm=2*np.pi/(np.sum(vals)*dt)
    return vals*Norm




def catpulse(t,dt):
    # Wykorzystujemy absolutną wartość czasu dla zachowania idealnej symetrii
    abs_t = np.abs(t)

    # 1. Puls kolisty: szczyt 0.8 przy t=0, opada do 0.75 przy t=0.25
    circle = -1.725 + np.sqrt(2.525**2 - 4 * abs_t**2)

    # 2. Trójkąt wznoszący: od 0.75 (t=0.25) do 1.0 (t=0.5) - ostre zbocze
    triangle_up = abs_t + 0.5

    # 3. Trójkąt opadający: od 1.0 (t=0.5) do 0.75 (t=0.75)
    triangle_down = -abs_t + 1.5

    # 4. Parabola: od 0.75 (t=0.75) do 0 (t=1.0)
    parabola = 12 * (abs_t - 1.0) ** 2

    # Definicja przedziałów dla zmiennej czasowej
    conditions = [
        abs_t <= 0.25,  # Środkowy łuk kolisty
        abs_t <= 0.50,  # Wznoszenie trójkąta do 1.0
        abs_t <= 0.75,  # Opadanie trójkąta do 0.75
        abs_t <= 1.00,  # Paraboliczne wygaszanie do 0
    ]

    choices = [circle, triangle_up, triangle_down, parabola]

    # Dla abs_t > 1.0 funkcja zwraca dokładnie 0.0
    vals = np.select(conditions, choices, default=0.0)
    Norm=2*np.pi/(np.sum(vals)*dt)

    return vals*Norm

########################################

# ---------------------------------------------------------------- HOOK 1: x
#x = semicirc(t,t[1]-t[0])

#x = tri(t,t[1]-t[0])

#x=rect(t,t[1]-t[0])#Gauss(t,0, 0.2)

#x=pseudo_beta(t,t[1]-t[0], 15)


#x = catpulse(t,t[1]-t[0])
# -------------------------------------------------- (x podawane do run(...))


def run(x, new_filter_multiplier):
    ################################Obliczanie dystrybuanty -> sinunsa dystrybuanty -> transformaty Fouriera sinusa dystrybuanty

    cdf=np.cumsum(x)*(t[1]-t[0])

    cdf = 0.5*(cdf + (2*np.pi - cdf[::-1]))

    sin_mapped=np.sin(cdf)

    #sin_mapped=sin_mapped-np.sum(sin_mapped)
    #print(np.sum(sin_mapped))

    f_shifted = np.fft.ifftshift(sin_mapped)
    F = np.fft.fft(f_shifted)
    F = np.fft.fftshift(F)

    freq = np.fft.fftshift(np.fft.fftfreq(N, d=t[1]-t[0]))

    ############################################################################################################################



    ################################Rysowanie wykresów


    fig,ax=plt.subplots(2,5,figsize=(14,6))
    ax[0,0].plot(t,x)
    ax[0,1].plot(t,cdf)
    ax[0,1].axhline(2*np.pi,linestyle='--')
    ax[0,2].plot(t, sin_mapped)

    ax[0,3].plot(freq, F.imag,label='Imag',c='blue')
    ax[0,3].plot(freq, F.real,label='Real',c='red')


    ax[0,3].legend()

    ax[0,3].set_xscale('symlog', linthresh=1e1)
    ax[0,3].set_yscale('symlog', linthresh=1e-8)

    ####

    indices = np.where(freq > 0)[0]


    ax[0,4].plot(freq[indices], np.abs(F[indices])**2, label='Filter Function')


    print('Rectangular filter: ')
    print(np.max(np.abs(F[indices])**2))

    exponents=np.round(np.log10(np.array([np.min(freq[indices]),np.max(freq[indices])])))


    ax[0,4].set_xscale('log')
    ax[0,4].set_yscale('log')
    ax[0,4].set_xticks(10**np.arange(exponents[0],exponents[-1]+1))
    ax[0,4].grid()
    #ax[3].set_xscale('symlog', linthresh=1e-2)

    ####################################

    # ------------------------------------------- HOOK 2: new_filter_multiplier
    #Factor1 = 44
    #new_filter_multiplier =np.exp(-np.abs(freq)**Factor1)#Gauss(freq,0,1.1)/np.max(Gauss(freq,0,1.1)) #
    # --------------------------- (new_filter_multiplier podawane do run(...))

    scaled_F=1j* F.imag *new_filter_multiplier

    ###Chop off floating point error:
    #################################

    F_unshifted = np.fft.ifftshift(scaled_F)
    f_rec = np.fft.ifft(F_unshifted)
    f_rec = np.fft.fftshift(f_rec)
    f_rec = np.real_if_close(f_rec)


    #Normalization ARCSIN
    f_rec = f_rec /np.max(np.abs(f_rec))

    ##
    new_f_shifted = np.fft.ifftshift(f_rec)
    new_F = np.fft.fft(new_f_shifted)
    new_F = np.fft.fftshift(new_F )

    ax[1,3].plot(freq, new_F.imag,label='Imag',c='blue')
    ax[1,3].plot(freq, 0*F.real,label='Real',c='red')
    ax[1,3].legend()

    ax[1,3].set_xscale('symlog', linthresh=1e1)
    ax[1,3].set_yscale('symlog', linthresh=1e-8)

    ax[1,4].plot(freq[indices], np.abs(new_F[indices])**2, label='Filter Function')

    print('Custom filter: ')
    print(np.max(np.abs(new_F[indices])**2))
    exponents=np.round(np.log10(np.array([np.min(freq[indices]),np.max(freq[indices])])))
    ax[1,4].set_xscale('log')
    ax[1,4].set_yscale('log')
    ax[1,4].set_xticks(10**np.arange(exponents[0],exponents[-1]+1))
    ax[1,4].grid()
    ####

    ax[1,2].plot(t,f_rec)

    pre_sin_rec=np.arcsin(f_rec)
    ##
    imax = np.argmax(pre_sin_rec)
    imin = np.argmin(pre_sin_rec)
    ##
    shift=1
    pre_sin_rec_corrected=np.concatenate((pre_sin_rec[0:imax+shift], -pre_sin_rec[imax+shift:imin]+np.pi, pre_sin_rec[imin:]+2*np.pi))


    pre_sin_rec_corrected = 0.5*(pre_sin_rec_corrected + (2*np.pi - pre_sin_rec_corrected[::-1]))

    from scipy.signal import savgol_filter
    #########################################################Savgol filter 1
    pre_sin_rec_corrected = savgol_filter(
        pre_sin_rec_corrected,
        window_length=31,   # must be odd
        polyorder=3,
        mode='interp'
    )


    ########
    ax[1,1].plot(t,pre_sin_rec_corrected)
    ax[1,1].axhline(2*np.pi, linestyle='--')

    ax[0,1].legend()
    ax[1,1].legend()
    #######

    x_rec = np.diff(pre_sin_rec_corrected, prepend=0)/(t[1]-t[0])


    # Smooth the reconstructed phase

    ## Smooth the reconstructed phase ###############################Slavgol 2
    x_rec = savgol_filter(
        x_rec,
        window_length=31,   # must be odd
        polyorder=3,
        mode='interp'
    )

    x_rec[0]=0
    x_rec[-1]=0
    ax[1,0].plot(t,x_rec)


    #####DEBUG:
    x=x_rec
    cdf=np.cumsum(x)*(t[1]-t[0])

    cdf = 0.5*(cdf + (2*np.pi - cdf[::-1]))

    sin_mapped=np.sin(cdf)

    #sin_mapped=sin_mapped-np.sum(sin_mapped)
    #print(np.sum(sin_mapped))

    f_shifted = np.fft.ifftshift(sin_mapped)
    F = np.fft.fft(f_shifted)
    F = np.fft.fftshift(F)

    freq = np.fft.fftshift(np.fft.fftfreq(N, d=t[1]-t[0]))



    ax[1,0].plot(t,x)
    ax[1,1].plot(t,cdf)
    ax[1,1].axhline(2*np.pi,linestyle='--')
    ax[1,2].plot(t, sin_mapped)

    ax[1,3].plot(freq, F.imag,label='Imag',c='cyan')
    ax[1,3].plot(freq, F.real,label='Real',c='pink')


    ax[1,3].legend()

    ax[1,3].set_xscale('symlog', linthresh=1e1)
    ax[1,3].set_yscale('symlog', linthresh=1e-8)

    ####

    indices = np.where(freq > 0)[0]


    ax[1,4].plot(freq[indices], np.abs(F[indices])**2, label='Filter Function')

    exponents=np.round(np.log10(np.array([np.min(freq[indices]),np.max(freq[indices])])))


    ax[1,4].set_xscale('log')
    ax[1,4].set_yscale('log')
    ax[1,4].set_xticks(10**np.arange(exponents[0],exponents[-1]+1))
    ax[1,4].grid()


    #########################################################Podpisy osi
    ax[0,0].set_xlabel("Time")
    ax[0,0].set_ylabel("Envelope amplitude")
    ax[0,1].set_xlabel("Time")
    ax[0,1].set_ylabel("CFD of Envelope")
    ax[0,2].set_xlabel("Time")
    ax[0,2].set_ylabel("Sin of CFD")
    ax[0,3].set_xlabel("Frequency")
    ax[0,3].set_ylabel("Envelope amplitude")
    ax[0,4].set_xlabel("Frequency")
    ax[0,4].set_ylabel("Envelope amplitude")
    ax[1,3].set_xlabel("Frequency")
    ax[1,3].set_ylabel("Envelope amplitude")
    ax[1,0].set_xlabel("Time")
    ax[1,0].set_ylabel("Envelope amplitude")
    ax[1,1].set_xlabel("Time")
    ax[1,1].set_ylabel("Envelope amplitude")
    ax[1,2].set_xlabel("Time")
    ax[1,2].set_ylabel("Envelope amplitude")






    ax[0,0].set_title("Envelope")
    ax[0,1].set_title("CFD of Envelope")
    ax[0,2].set_title("Sin of CFD")
    ax[0,3].set_title("FTT of Sin")
    ax[0,4].set_title("Absolute value of FTT sqared")


    plt.tight_layout()
    return fig

# ===================== KONIEC KODU ORYGINALNEGO =====================
