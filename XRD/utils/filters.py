"""
Advanced Filtration Module
==========================
Signal processing and filtering techniques for XRD data cleaning and enhancement.

This module provides various signal processing methods to improve data quality
before analysis and visualization.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import pandas as pd
import numpy as np
from XRD.core import gsas_processing as gp
import matplotlib.pyplot as plt
from scipy.signal import butter, iirnotch, filtfilt, freqz

def plot_butter_bandstop(lowcut, highcut, fs, order=4):
    # Design the Butterworth bandstop filter
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='bandstop')

    # Compute the frequency response
    w, h = freqz(b, a, worN=8000)

    # Plot the frequency response
    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    plt.plot(0.5 * fs * w / np.pi, np.abs(h), 'b')
    plt.title('Butterworth Bandstop Filter Frequency Response')
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Gain')
    plt.grid()

    plt.subplot(2, 1, 2)
    plt.plot(0.5 * fs * w / np.pi, np.angle(h), 'b')
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Phase [radians]')
    plt.grid()

    plt.tight_layout()
    plt.show()


def butter_bandstop(lowcut, highcut, fs, order=4):
    """
    Design a Butterworth bandstop filter.

    Parameters:
    - lowcut: Lower frequency bound of the stop band.
    - highcut: Upper frequency bound of the stop band.
    - fs: Sampling frequency of the data.
    - order: Order of the filter.

    Returns:
    - b, a: Numerator and denominator polynomials of the IIR filter.
    """
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='bandstop')
    return b, a

def apply_bandstop_filter(df, frame_rate, value_column, lowcut, highcut, order=4):
    """
    Apply a Butterworth bandstop filter to a specified column in a DataFrame.

    Parameters:
    - df: The DataFrame containing the data.
    - value_column: The name of the column to filter.
    - time_column: The name of the column containing time data.
    - lowcut: Lower frequency bound of the stop band.
    - highcut: Upper frequency bound of the stop band.
    - order: Order of the filter.

    Returns:
    - df_filtered: DataFrame with the filtered value column.
    """
    # Calculate sampling frequency from the time column
    #time_diffs = np.diff(df[time_column])
    fs = frame_rate  # Sampling frequency in Hz

    # Design the filter
    b, a = butter_bandstop(lowcut, highcut, fs, order)

    # Apply the filter
    df[value_column] = filtfilt(b, a, df[value_column])
    return df

def apply_notch_filter(df, value_column, fs, freq, quality_factor=30):
    # Design the notch filter
    b, a = iirnotch(freq, quality_factor, fs)
    # Apply the filter
    df[value_column] = filtfilt(b, a, df[value_column])
    return df

def apply_moving_median(df, value_column, window_size=21):
    """ Apply a moving average to a specified column in a DataFrame.
    
    Parameters:
    - df: The DataFrame containing the data.
    - value_column: The name of the column to smooth.
    - window_size: The size of the moving window.
    
    Returns:
    - df_smoothed: DataFrame with the smoothed value column.
    """
    df[value_column] = df[value_column].rolling(window_size).median()
    #df[value_column] = np.sign(df[value_column]) * (df[value_column] ** 2)
    df[value_column].fillna(method='bfill', inplace=True)  # Backfill NaNs
    df[value_column].fillna(method='ffill', inplace=True)  # Forward fill remaining NaNs
    return df

def do_filtration(data: pd.DataFrame, index: int, value: str):
    fs = 50
    lowcut = 6
    #lowcut = 6
    highcut = 12
    #highcut = 5
    freq = 5.5 / (fs/2)
    quality_factor = 50
    order = 4
    window_size = 11

    working = data.azimuth_orientation[index]
    #filtered_dfs = [apply_notch_filter(df, value, fs, freq, quality_factor) for df in working.dataframes]
    
    #plot_butter_bandstop(lowcut, highcut, fs, order)
    #filtered_dfs = [apply_bandstop_filter(df, fs, value, lowcut, highcut, order) for df in working.dataframes]
    
    smoothed_dfs = [apply_moving_median(df, value, window_size) for df in working.dataframes]
    working.dataframes = smoothed_dfs
    data.azimuth_orientation[index] = working
    data.frame_orientation = gp.azimuth_to_peak(data.azimuth_orientation)
    return data
