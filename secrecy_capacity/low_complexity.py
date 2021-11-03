""" Calculate the secrecy capacity using a low-complexity algorithm.

This module allows calculating the secrecy capacity of a wiretap channel using
the low-complexity algorithm presented in
T. Van Nguyen, Q.-D. Vu, M.  Juntti, and L.-N. Tran, "A Low-Complexity
Algorithm for Achieving Secrecy Capacity in MIMO Wiretap Channels," in ICC 2020
- 2020 IEEE International Conference on Communications (ICC), 2020, pp. 1–6.

Copyright (C) 2020 Karl-Ludwig Besser

License:
This program is licensed under the GPLv3 license. If you in any way use this
code for research that results in publications, please cite our original
article listed above.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.
See the GNU General Public License for more details.

Author: Karl-Ludwig Besser, Technische Universitaet Braunschweig
"""

import os
from time import time
import logging

import numpy as np
from scipy.linalg import sqrtm

LOGGER = logging.getLogger("low_complexity_algorithm")


def cov_secrecy_capacity_low_complexity(mat_bob, mat_eve, power=1, tol_eps=1e-6):
    time0 = time()
    # Get all parameters
    mat_bob = np.matrix(mat_bob)
    mat_eve = np.matrix(mat_eve)
    n_rx, n_tx = np.shape(mat_bob)
    n_eve = np.shape(mat_eve)[0]
    LOGGER.debug("Matrices have shape: %d x %d", n_rx, n_tx)
    # Initialization
    h_bar = np.vstack((mat_bob, mat_eve))
    t = 0
    cov = np.zeros((n_tx, n_tx))  # S_{0}
    mat_omega = np.eye(n_rx + n_eve)  # Omega_{0}
    _obj_out_old = -2
    _obj_out_new = 2
    time1 = time()
    LOGGER.debug("Preparing everything took: %.3f sec", time1-time0)
    #while t < 10:
    while abs(_obj_out_new - _obj_out_old) > 1e-6:
        t_start = time()
        _obj_out_old = _obj_out_new
        inv_cap_eve = np.linalg.inv(np.eye(n_eve) + mat_eve@cov@mat_eve.H)
        mat_q = mat_eve.H @ inv_cap_eve @ mat_eve  # Q_{t}
        n = 0
        mat_k = np.copy(mat_omega)  # K_{0}

        _obj_inner_old = -2
        _obj_inner_new = 2
        while abs(_obj_inner_new - _obj_inner_old) > 1e-4:
            _obj_inner_old = _obj_inner_new
            mat_w = _algorithm1(h_bar, mat_k, mat_q, power=power)  # W_{n}
            mat_t = np.linalg.inv(mat_k + h_bar@mat_w@h_bar.H)  # T_{n}
            mat_t_bar = mat_t[-n_eve:, :n_rx]  # \bar{T}_{n}
            _rho, mat_u = np.linalg.eigh(mat_t_bar @ mat_t_bar.H)  # (16)
            _delta = 2*np.diag(1./(1+np.sqrt(1+4*_rho)))  # (16)
            mat_k_bar = -mat_u @ _delta @ mat_u.H @ mat_t_bar  # \bar{K}_{n+1}
            mat_k = np.block([[np.eye(n_rx), mat_k_bar.H], [mat_k_bar, np.eye(n_eve)]])
            n = n+1
            _obj_inner_new = objective_inner(mat_t, mat_k)
            #print(_obj_inner_new-_obj_inner_old)
            #print("n = {}".format(n))

        cov = np.copy(mat_w)  # S_{t+1}
        mat_omega = np.copy(mat_k)  # Omega_{t+1}
        _obj_out_new = _func_ft(h_bar, mat_omega, cov, mat_eve)
        t_end = time()
        LOGGER.info("Iteration t=%d took: %.3f sec", t, t_end-t_start)
        LOGGER.debug("Objective Difference: %f", abs(_obj_out_new-_obj_out_old))
        t = t+1
    return cov

def _algorithm1(h_bar, mat_k, mat_q, power=1, tol_eps=1e-12):
    inv_k = np.linalg.inv(mat_k)
    n_tx = np.shape(h_bar)[1]
    #mu_min = 0
    #mu_max = n_tx/power
    mu_1 = 0
    mu_u = n_tx/power
    while mu_u - mu_1 > tol_eps:
        mu = (mu_1 + mu_u)/2
        mat_m = mu*np.eye(n_tx) + mat_q
        #inv_sqrt_m = np.linalg.inv(sqrtm(mat_m))
        _sqrt_m = sqrtm(mat_m)
        inv_sqrt_m = np.linalg.inv(_sqrt_m)
        eig_val, eig_vec = np.linalg.eigh(inv_sqrt_m @ h_bar.H @ inv_k @ h_bar @ inv_sqrt_m)
        mat_phi = np.diag(np.maximum(1-1./eig_val, 0))
        mat_w = inv_sqrt_m @ eig_vec @ mat_phi @ eig_vec.H @ inv_sqrt_m
        if np.trace(mat_w) > power:
            mu_1 = mu
        else:
            mu_u = mu
    return mat_w

def _func_ft(h_bar, mat_omega, cov, mat_eve):
    n_eve = len(mat_eve)
    _part1 = np.log(np.linalg.det(mat_omega + h_bar @ cov @ h_bar.H))
    _part2 = np.log(np.linalg.det(mat_omega))
    #_part3 = np.trace(
    _part4 = np.log(np.linalg.det(np.eye(n_eve) + mat_eve @ cov @ mat_eve.H))
    return _part1 - _part2 - _part4

def objective_inner(mat_t, mat_k):
    return np.trace(mat_t @ mat_k) - np.log(np.linalg.det(mat_k))
