# -*- coding: utf-8 -*-
import pandas as pd

from ..ecg import ecg_process
from ..eda import eda_process
from ..emg import emg_process
from ..eog import eog_process
from ..hrv import hrv_rsa
from ..misc import as_vector
from ..ppg import ppg_process
from ..rsp import rsp_process


def bio_process(
    ecg=None, rsp=None, eda=None, emg=None, ppg=None, eog=None, keep=None, sampling_rate=1000
):
    """**Automated processing of bio signals**

    Wrapper for other bio processing functions of
    electrocardiography signals (ECG), respiration signals (RSP),
    electrodermal activity (EDA) and electromyography signals (EMG).

    Parameters
    ----------
    data : DataFrame
        The DataFrame containing all the respective signals (e.g., ecg, rsp, Photosensor etc.). If
        provided, there is no need to fill in the other arguments denoting the channel inputs.
        Defaults to ``None``.
    ecg : Union[list, np.array, pd.Series]
        The raw ECG channel.
    rsp : Union[list, np.array, pd.Series]
        The raw RSP channel (as measured, for instance, by a respiration belt).
    eda : Union[list, np.array, pd.Series]
        The raw EDA channel.
    emg : Union[list, np.array, pd.Series]
        The raw EMG channel.
    ppg : Union[list, np.array, pd.Series]
        The raw PPG channel.
    eog : Union[list, np.array, pd.Series]
        The raw EOG channel, extracted from :func:`.mne_channel_extract().`
    keep : DataFrame
        Dataframe or channels to add by concatenation
        to the processed dataframe (for instance, the Photosensor channel).
    sampling_rate : int
        The sampling frequency of the signals (in Hz, i.e., samples/second).
        Defaults to ``1000``.

    Returns
    ----------
    bio_df : DataFrame
        DataFrames of the following processed bio features:

        * *"ECG"*: the raw signal, the cleaned signal, the heart rate, and the R peaks indexes.
          Also generated by :func:`.ecg_process()`.
        * *"RSP"*: the raw signal, the cleaned signal, the rate, and the amplitude. Also generated
          by :func:`.rsp_process()`.
        * *"EDA"*: the raw signal, the cleaned signal, the tonic component, the phasic component,
          indexes of the SCR onsets, peaks, amplitudes, and half-recovery times. Also generated by
          :func:`.eda_process()`.
        * *"EMG"*: the raw signal, the cleaned signal, and amplitudes. Also generated by :func:`.
          emg_process()`.
        * *"PPG"*: the raw signal, the cleaned signal, rate and peaks. Also generated by :func:`.
          ppg_process()`.
        * *"RSA"*: Respiratory Sinus Arrhythmia features generated by :func:`.ecg_rsa()`, if both
          ECG and RSP are provided.
        * *"EOG"*: the raw signal, the cleaned signal, the indexes of EOG blinks, and the blink
          rate.
    bio_info : dict
        A dictionary containing the samples of peaks, troughs, amplitudes, onsets, offsets, periods
        of activation, recovery times of the respective processed signals,
        as well as the signals' sampling rate.


    See Also
    ----------
    .ecg_process, .rsp_process, .eda_process, .emg_process, .ppg_process, .eog_process

    Example
    ----------
    **Example 1**: Using synthetic data
    .. ipython:: python

      import neurokit2 as nk

      # With Simulated Data
      ecg = nk.ecg_simulate(duration=40, sampling_rate=250)
      rsp = nk.rsp_simulate(duration=40, sampling_rate=250)
      eda = nk.eda_simulate(duration=40, sampling_rate=250, scr_number=3)
      emg = nk.emg_simulate(duration=40, sampling_rate=250, burst_number=5)

      bio_df, bio_info = nk.bio_process(ecg=ecg, rsp=rsp, eda=eda, emg=emg, eog=None,
      sampling_rate=250)
      bio_df.head()

    .. ipython:: python

      # Visualize a subset of signals
      @savefig p_bio_process1.png scale=100%
      fig = bio_df.iloc[:, 0:16].plot(subplots=True)
      @suppress
      plt.close()

    **Example 2**: Using a real dataset
    .. ipython:: python

      # Download EOG signal separately
      eog = nk.data('eog_100hz')
      # Download data but crop with same length as eog signal
      data = nk.data('bio_eventrelated_100hz')[:len(eog)]

      bio_df2, bio_info2 = nk.bio_process(ecg=data['ECG'], rsp=data['RSP'], eda=data['EDA'],
      emg=None, eog=eog, keep=data['Photosensor'], sampling_rate=100)
      bio_df2.head()

      # Visualize all signals
      @savefig p_bio_process2.png scale=100%
      fig = bio_df2.iloc[:, 0:16].plot(subplots=True)
      @suppress
      plt.close()

    """
    bio_info = {}
    bio_df = pd.DataFrame({})

    # Error check if first argument is a Dataframe.
    if ecg is not None:
        if isinstance(ecg, pd.DataFrame):
            data = ecg.copy()
            if "RSP" in data.keys():
                rsp = data["RSP"]
            else:
                rsp = None
            if "EDA" in data.keys():
                eda = data["EDA"]
            else:
                eda = None
            if "EMG" in data.keys():
                emg = data["EMG"]
            else:
                emg = None
            if "ECG" in data.keys():
                ecg = data["ECG"]
            elif "EKG" in data.keys():
                ecg = data["EKG"]
            else:
                ecg = None
            if "PPG" in data.keys():
                ppg = data["PPG"]
            else:
                ppg = None
            if "EOG" in data.keys():
                eog = data["EOG"]
            else:
                eog = None
            cols = ["ECG", "EKG", "RSP", "EDA", "EMG", "PPG", "EOG"]
            keep_keys = [key for key in data.keys() if key not in cols]
            if len(keep_keys) != 0:
                keep = data[keep_keys]
            else:
                keep = None

    # ECG
    if ecg is not None:
        ecg = as_vector(ecg)
        ecg_signals, ecg_info = ecg_process(ecg, sampling_rate=sampling_rate)
        bio_info.update(ecg_info)
        bio_df = pd.concat([bio_df, ecg_signals], axis=1)

    # RSP
    if rsp is not None:
        rsp = as_vector(rsp)
        rsp_signals, rsp_info = rsp_process(rsp, sampling_rate=sampling_rate)
        bio_info.update(rsp_info)
        bio_df = pd.concat([bio_df, rsp_signals], axis=1)

    # EDA
    if eda is not None:
        eda = as_vector(eda)
        eda_signals, eda_info = eda_process(eda, sampling_rate=sampling_rate)
        bio_info.update(eda_info)
        bio_df = pd.concat([bio_df, eda_signals], axis=1)

    # EMG
    if emg is not None:
        emg = as_vector(emg)
        emg_signals, emg_info = emg_process(emg, sampling_rate=sampling_rate)
        bio_info.update(emg_info)
        bio_df = pd.concat([bio_df, emg_signals], axis=1)

    # PPG
    if ppg is not None:
        ppg = as_vector(ppg)
        ppg_signals, ppg_info = ppg_process(ppg, sampling_rate=sampling_rate)
        bio_info.update(ppg_info)
        bio_df = pd.concat([bio_df, ppg_signals], axis=1)

    # EOG
    if eog is not None:
        eog = as_vector(eog)
        eog_signals, eog_info = eog_process(eog, sampling_rate=sampling_rate)
        bio_info.update(eog_info)
        bio_df = pd.concat([bio_df, eog_signals], axis=1)

    # Additional channels to keep
    if keep is not None:
        keep = keep.reset_index(drop=True)
        bio_df = pd.concat([bio_df, keep], axis=1)

    # RSA
    if ecg is not None and rsp is not None:
        rsa = hrv_rsa(
            ecg_signals, rsp_signals, rpeaks=None, sampling_rate=sampling_rate, continuous=True
        )
        bio_df = pd.concat([bio_df, rsa], axis=1)

    # Add sampling rate in dict info
    bio_info["sampling_rate"] = sampling_rate

    return bio_df, bio_info
