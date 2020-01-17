# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from ..signal import signal_smooth
from ..signal import signal_filter


def eda_decompose(eda_signal, sampling_rate=1000, method="highpass"):
    """Decompose Electrodermal Activity (EDA) into Phasic and Tonic components.

    Decompose the Electrodermal Activity (EDA) into two components, namely Phasic and Tonic, using different methods including cvxEDA (Greco, 2016) or Biopac's Acqknowledge algorithms.

    Parameters
    ----------
    eda_signal : list, array or Series
        The raw EDA signal.
    sampling_rate : int
        The sampling frequency of raw EDA signal (in Hz, i.e., samples/second).
    method : str
        The processing pipeline to apply. Can be one of "cvxEDA"
        (default) or "biosppy".

    Returns
    -------
    DataFrame
        DataFrame containing the 'Tonic' and the 'Phasic' components as columns.

    See Also
    --------
    eda_simulate, eda_clean, eda_findpeaks


    Examples
    ---------
    >>> import neurokit2 as nk
    >>>
    >>> # Decompose using different algorithms
    >>> eda_signal = nk.eda_simulate(duration=30, n_scr=5, drift=0.1)
    >>> cvxEDA = nk.eda_decompose(nk.standardize(eda_signal), method='cvxeda')
    >>> smoothMedian = nk.eda_decompose(nk.standardize(eda_signal), method='smoothmedian')
    >>> highpass = nk.eda_decompose(nk.standardize(eda_signal), method='highpass')
    >>>
    >>> data = pd.concat([cvxEDA.add_suffix('_cvxEDA'),
                          smoothMedian.add_suffix('_SmoothMedian'),
                          highpass.add_suffix('_Highpass')], axis=1)
    >>> data["EDA_Raw"] = eda_signal
    >>> data.plot()
    >>>
    >>> eda_signal = pd.read_csv("https://raw.githubusercontent.com/neuropsychology/NeuroKit/master/data/example_bio_100hz.csv")["EDA"]
    >>> data = nk.eda_decompose(nk.standardize(eda_signal), sampling_rate=200)
    >>> data["EDA_Raw"] = eda_signal
    >>> out = nk1.bio
    >>> data.plot()

    References
    -----------
    - cvxEDA: https://github.com/lciti/cvxEDA
    - Greco, A., Valenza, G., & Scilingo, E. P. (2016). Evaluation of CDA and CvxEDA Models. In Advances in Electrodermal Activity Processing with Applications for Mental Health (pp. 35-43). Springer International Publishing.
    - Greco, A., Valenza, G., Lanata, A., Scilingo, E. P., & Citi, L. (2016). cvxEDA: A convex optimization approach to electrodermal activity processing. IEEE Transactions on Biomedical Engineering, 63(4), 797-804.
    """
    method = method.lower()  # remove capitalised letters
    if method == "cvxeda":
        data = _eda_decompose_cvxeda(eda_signal, sampling_rate)
    elif method in ["median", "smoothmedian"]:
        data = _eda_decompose_mediansmooth(eda_signal, sampling_rate)
    elif method in ["highpass", "biopac", "acqknowledge"]:
        data = _eda_decompose_highpass(eda_signal, sampling_rate)
    else:
        raise ValueError("NeuroKit error: eda_clean(): 'method' should be "
                         "one of 'biosppy'.")

    return data




# =============================================================================
# Acqknowledge
# =============================================================================
def _eda_decompose_mediansmooth(eda_signal, sampling_rate=1000, smoothing_factor=4):
    """
    One of the two methods available in biopac's acqknowledge (https://www.biopac.com/knowledge-base/phasic-eda-issue/)
    """
    size = smoothing_factor * sampling_rate
    tonic = signal_smooth(eda_signal, kernel='median', size=size)
    phasic = eda_signal - tonic

    out = pd.DataFrame({"EDA_Tonic": np.array(tonic),
                        "EDA_Phasic": np.array(phasic)})

    return out





def _eda_decompose_highpass(eda_signal, sampling_rate=1000):
    """
    One of the two methods available in biopac's acqknowledge (https://www.biopac.com/knowledge-base/phasic-eda-issue/)
    """
    phasic = signal_filter(eda_signal, sampling_rate=sampling_rate, lowcut=0.05, method="butter")
    tonic = signal_filter(eda_signal, sampling_rate=sampling_rate, highcut=0.05, method="butter")

    out = pd.DataFrame({"EDA_Tonic": np.array(tonic),
                        "EDA_Phasic": np.array(phasic)})

    return out





# =============================================================================
# cvxEDA
# =============================================================================
def _eda_decompose_cvxeda(eda_signal, sampling_rate=1000, tau0=2., tau1=0.7, delta_knot=10., alpha=8e-4, gamma=1e-2, solver=None, reltol=1e-9):
    """
    A convex optimization approach to electrodermal activity processing (CVXEDA).

    This function implements the cvxEDA algorithm described in "cvxEDA: a
    Convex Optimization Approach to Electrodermal Activity Processing" (Greco et al., 2015).

    Parameters
    ----------
       eda : list or array
           raw EDA signal array.
       sampling_rate : int
           Sampling rate (samples/second).
       tau0 : float
           Slow time constant of the Bateman function.
       tau1 : float
           Fast time constant of the Bateman function.
       delta_knot : float
           Time between knots of the tonic spline function.
       alpha : float
           Penalization for the sparse SMNA driver.
       gamma : float
           Penalization for the tonic spline coefficients.
       solver : bool
           Sparse QP solver to be used, see cvxopt.solvers.qp
       reltol : float
           Solver options, see http://cvxopt.org/userguide/coneprog.html#algorithm-parameters
    """
    # Try loading cvx
    try:
        import cvxopt
    except ImportError:
        raise ImportError("NeuroKit error: eda_decompose(): the 'cvxopt' "
                          "module is required for this method to run. ",
                          "Please install it first (`pip install cvxopt`).")

    # Internal functions
    def _cvx(m, n):
        return cvxopt.spmatrix([], [], [], (m, n))

    frequency = 1/sampling_rate

    n = len(eda_signal)
    eda = cvxopt.matrix(eda_signal)

    # bateman ARMA model
    a1 = 1./min(tau1, tau0)  # a1 > a0
    a0 = 1./max(tau1, tau0)
    ar = np.array([(a1*frequency + 2.) * (a0*frequency + 2.),
                   2.*a1*a0*frequency**2 - 8.,
                   (a1*frequency - 2.) * (a0*frequency - 2.)]) / ((a1 - a0) * frequency**2)
    ma = np.array([1., 2., 1.])

    # matrices for ARMA model
    i = np.arange(2, n)
    A = cvxopt.spmatrix(np.tile(ar, (n-2, 1)), np.c_[i, i, i], np.c_[i, i-1, i-2], (n, n))
    M = cvxopt.spmatrix(np.tile(ma, (n-2, 1)), np.c_[i, i, i], np.c_[i, i-1, i-2], (n, n))

    # spline
    delta_knot_s = int(round(delta_knot / frequency))
    spl = np.r_[np.arange(1., delta_knot_s), np.arange(delta_knot_s, 0., -1.)]  # order 1
    spl = np.convolve(spl, spl, 'full')
    spl /= max(spl)
    # matrix of spline regressors
    i = np.c_[np.arange(-(len(spl)//2), (len(spl)+1)//2)] + np.r_[np.arange(0, n, delta_knot_s)]
    nB = i.shape[1]
    j = np.tile(np.arange(nB), (len(spl), 1))
    p = np.tile(spl, (nB, 1)).T
    valid = (i >= 0) & (i < n)
    B = cvxopt.spmatrix(p[valid], i[valid], j[valid])

    # trend
    C = cvxopt.matrix(np.c_[np.ones(n), np.arange(1., n+1.)/n])
    nC = C.size[1]

    # Solve the problem:
    # .5*(M*q + B*l + C*d - eda)^2 + alpha*sum(A, 1)*p + .5*gamma*l'*l
    # s.t. A*q >= 0

    old_options = cvxopt.solvers.options.copy()
    cvxopt.solvers.options.clear()
    cvxopt.solvers.options.update({'reltol': reltol,
                                   'show_progress': False})
    if solver == 'conelp':
        # Use conelp
        G = cvxopt.sparse([[-A, _cvx(2, n), M, _cvx(nB+2, n)],
                           [_cvx(n+2, nC), C, _cvx(nB+2, nC)],
                           [_cvx(n, 1), -1, 1, _cvx(n+nB+2, 1)],
                           [_cvx(2*n+2, 1), -1, 1, _cvx(nB, 1)],
                           [_cvx(n+2, nB), B, _cvx(2, nB), cvxopt.spmatrix(1.0, range(nB), range(nB))]])
        h = cvxopt.matrix([_cvx(n, 1), .5, .5, eda, .5, .5, _cvx(nB, 1)])
        c = cvxopt.matrix([(cvxopt.matrix(alpha, (1, n)) * A).T, _cvx(nC, 1), 1, gamma, _cvx(nB, 1)])
        res = cvxopt.solvers.conelp(c, G, h, dims={'l': n, 'q': [n+2, nB+2], 's': []})
        obj = res['primal objective']
    else:
        # Use qp
        Mt, Ct, Bt = M.T, C.T, B.T
        H = cvxopt.sparse([[Mt*M, Ct*M, Bt*M], [Mt*C, Ct*C, Bt*C],
                           [Mt*B, Ct*B, Bt*B+gamma*cvxopt.spmatrix(1.0, range(nB), range(nB))]])
        f = cvxopt.matrix([(cvxopt.matrix(alpha, (1, n)) * A).T - Mt*eda, -(Ct*eda), -(Bt*eda)])
        res = cvxopt.solvers.qp(H, f, cvxopt.spmatrix(-A.V, A.I, A.J, (n, len(f))), cvxopt.matrix(0., (n, 1)), solver=solver)
        obj = res['primal objective'] + .5 * (eda.T * eda)
    cvxopt.solvers.options.clear()
    cvxopt.solvers.options.update(old_options)

    tonic_splines = res['x'][-nB:]
    drift = res['x'][n:n+nC]
    tonic = B * tonic_splines + C * drift
    q = res['x'][:n]
    smna_driver = A * q
    phasic = M * q
    residuals = eda - phasic - tonic

    out = pd.DataFrame({"EDA_Tonic": np.array(tonic)[:, 0],
                        "EDA_Phasic": np.array(phasic)[:, 0]})

    return out
