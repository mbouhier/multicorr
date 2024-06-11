# -*- coding: utf-8 -*-
"""
Created on Mon May 18 14:58:49 2015

@author: mbouhier
"""
import numpy as np

import time
from lmfit import minimize,Parameters,report_errors
from scipy.optimize import minimize_scalar
from numpy import log,exp
import multiprocessing

import logging
#==============================================================================#
#                                Process                                       #
#==============================================================================#

class FitInstance(object):
    
    def __init__(self):
        pass
    
    def fitData(self, x, y, params, equation, refs=[], verbose=True, method = 'leastsq'):
        if verbose: 
            print("fitting data")
#        max_jobs = multiprocessing.cpu_count()
#        logging.debug("CPUs cores count is %d" % (max_jobs,))
#        
        
        t0 = time.clock()
        #lmfit = minimize(self.residualslmfit, params, args=(y, x, equation),method=method)
        lmfit = minimize(self.residualslmfit, params, args=(y, x, equation, refs), method = method)
        #lmfit = minimize_scalar(self.residualslmfit, params, args=(y, x, equation, refs),method='brent')
        logging.debug("Ellapsed for lmfit: %.2fs" % ((time.clock() - t0)))
        
        if verbose:
            logging.info("Ellapsed for lmfit: %.2fs" % ((time.clock() - t0)))
            print(report_errors(params))
        #ci = lmfit.conf_interval()
        return lmfit.values
    
    def residualslmfit(self, parameters, y, x, equation, refs=[]):
        coeff = list()

        for key,value in parameters.valuesdict().items():
            #print "key,value:",key,value
            coeff.append(value)
        #print "coeff:", coeff
        err = y - eval(equation)
        return err
    
    
    
    
    
    
def launchMultiprocess(ds, spectrums_to_fit, equation, coeffs_names, coeff_init, coeffs_bounds, refsFitSpectrums, fit_method, stop_event, finished_event, parameters_values, use_normalized_data):
        num_process = 10
        for i in range(num_process):        
            t = multiprocessing.Process(target = fitProcessUnit, args = (ds, spectrums_to_fit, equation, coeffs_names, coeff_init, coeffs_bounds, refsFitSpectrums, fit_method, stop_event, finished_event, parameters_values, use_normalized_data))
            t.start()
            
            
def fitData(x, y, params, equation, refs=[], verbose=True, method = 'leastsq'):
        if verbose: 
            print("fitting data")
            
        t0 = time.clock()
        #lmfit = minimize(self.residualslmfit, params, args=(y, x, equation),method=method)
        lmfit = minimize(residualslmfit, params, args=(y, x, equation, refs),method=method)
        if verbose:
            print("Ellapsed for lmfit: %.2fs" % ((time.clock() - t0)))
            print(report_errors(params))
        #ci = lmfit.conf_interval()
        return lmfit
        
        
def fitProcessUnit(ds, spectrums_to_fit, equation, coeffs_names, coeff_init, coeffs_bounds, refsFitSpectrums, fit_method, stop_event, finished_event, parameters_values, use_normalized_data):  
       
       for spectrum_index in spectrums_to_fit:

           print("Fitting spectrum #",spectrum_index)

           if use_normalized_data: X = ds["X_normalized"][spectrum_index]
           else:                   X = ds["X"][spectrum_index]
           
           W = ds["W"]
            
           #==============================================================
           # On remet à zero les valeurs precedement trouvéees pour les parametres
           #==============================================================
           params = Parameters()
           
           for idx, c_name in enumerate(coeffs_names):
               
               coeff_idx = int(c_name.split("coeff[")[1].split("]")[0])
               
               params.add(name  = c_name.replace("[","").replace("]",""),
                          value = coeff_init[coeff_idx],
                          min   = coeffs_bounds[idx][0],
                          max   = coeffs_bounds[idx][1],
                          )
            #=====================================================================#
           # Et on envoie à la methode de fit                                    #
           #=====================================================================#
           #pour gerer parallelement plusieurs fit voir:
           #https://docs.python.org/2/library/queue.html
           #http://stackoverflow.com/questions/17554046/how-to-let-a-python-thread-finish-gracefully
           #utilisation de Queue, get(), task_done()
           lmfit      = fitData(W, X, params, equation, refs = refsFitSpectrums, method = 'leastsq', verbose = False)
           fit_values = lmfit.values
           
           #==============================================================
           # affichage pour debug
           #==============================================================
    #               if len(spectrums_to_fit) <= 5:
    #                   coeff      = [0 for fv in fit_values]
    #                   
    #                   print "============ data fit=================="
    #                   for key, value in fit_values.iteritems():
    #                       idx = int(key.split("coeff")[1])
    #                       print "coeff[%d]:%.6f (%s)" % (idx,value,match_names["coeff[%d]"%(idx)])
    #                       coeff[idx] = value
    #                    print "======================================="
    #                    
    #                    pl.figure()
    #                    x = W
    #                    refs = refsFitSpectrums
    #                    pl.plot(x,eval(equation),'r--')
    #                    pl.plo_launchXMLModelsFit_Threadt(x,X)
    #                    pl.show()
           #==================================================================
           #==================================================================
           #=====================================================================#
           # On garde en memoire les resultats
           #=====================================================================#

           #TODO: pas tres optimisé...
           for key, value in fit_values.items():
                   idx = int(key.split("coeff")[1])
                   parameters_values[spectrum_index][idx] = value

           
           #======== Et on affiche le  fit effectué, pendant qu'on y est ============
           #self.emit(SIGNAL('updateDisplayedSpectrumInRepresentationTab'),spectrum_index)
           #time.sleep(0.001) #pour pas bloquer le thread?
    
def residualslmfit(parameters, y, x, equation, refs=[]):
        coeff = list()

        for key,value in parameters.valuesdict().items():
            #print "key,value:",key,value
            coeff.append(value)
        #print "coeff:", coeff
        err = y - eval(equation)
        return err   
    