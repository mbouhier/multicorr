# -*- coding: utf-8 -*-
"""
Created on Wed Aug 03 13:30:07 2016

@author: mbouhier
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from functools import partial
from multiprocessing import Pool


def baseline_als(y, lam, p, niter = 10):
    L = len(y)
    D = sparse.csc_matrix(np.diff(np.eye(L), 2))
    w = np.ones(L)
    for i in range(niter):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + lam * D.dot(D.transpose())
        z = spsolve(Z, w*y)
        w = p * (y > z) + (1 - p) * (y < z)
    return z
#
# def baseline_als(y, lam, p, niter = 10):
#     L = len(y)
#     D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
#     w = np.ones(L)
#     for i in range(niter):
#         W = sparse.spdiags(w, 0, L, L)
#         Z = W + lam * D.dot(D.transpose())
#         z = spsolve(Z, w*y)
#         w = p * (y > z) + (1 - p) * (y < z)
#     return z

# def baseline_als(y, lam, p, niter =10):
#
#     s  = len(y)
#     # assemble difference matrix
#     D0 = sparse.eye( s )
#     d1 = [np.ones( s-1 ) * -2]
#     D1 = sparse.diags( d1, [-1] )
#     d2 = [ np.ones( s-2 ) * 1]
#     D2 = sparse.diags( d2, [-2] )
#
#     D  = D0 + D2 + D1
#     w  = np.ones( s )
#     for i in range( niter ):
#         W = sparse.diags( [w], [0] )
#         Z =  W + lam*D.dot( D.transpose() )
#         z = spsolve( Z, w*y )
#         w = p * (y > z) + (1-p) * (y < z)
#
#     return z

def paralelized_baseline_als(spectrums, lam, p, niter = 10):
    print("inside paralelized_baseline_als...")
    
    spectrums_asls = [None for s in spectrums]
    
    pool = Pool()
    results = pool.map_async(partial(baseline_als, lam = lam, p = p), spectrums)
    spectrums_asls = results.get()
    print("done")
    
    return spectrums_asls


if __name__ == "__main__":
    print("ASLS.py running")
    pass