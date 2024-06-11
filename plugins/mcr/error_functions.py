import numpy as np


def err_fcn_R2_lof(C, ST, D_actual, D_calculated):

    residual = D_actual - D_calculated
    experimental_squared_sum = np.sum(D_actual**2)

    upper_term =  experimental_squared_sum - np.sum(residual**2)
    lower_term =  experimental_squared_sum

    Rsquared = 100* np.sqrt(upper_term/lower_term)

    upper_term = np.sum(residual**2)

    lof = 100* np.sqrt(upper_term/lower_term)

    print("lof: {:.2f}%".format(lof))
    print("R2:  {:.2f}%".format(Rsquared))
    print("Score:",np.sqrt((100 - Rsquared)**2 + lof**2))

    return np.sqrt((100 - Rsquared)**2 + lof**2)

def err_fcn_R2(C, ST, D_actual, D_calculated):

    residual = D_actual - D_calculated
    experimental_squared_sum = np.sum(D_actual**2)

    upper_term =  experimental_squared_sum - np.sum(residual**2)
    lower_term =  experimental_squared_sum

    Rsquared = 100* np.sqrt(upper_term/lower_term)
    return 100 - Rsquared

def err_fcn_lof(C, ST, D_actual, D_calculated):
    """
    MATLAB
    function[sigma] = lofr(de, c, s)
    % function[sigma] = lof(de, c, s)

    [nr, nc] = size(de);
    [nr, ns] = size(c);
    dr = c * s;
    res = de - dr;   --> residual
    sst1 = sum(sum(res. * res));
    sst2 = sum(sum(de. * de));   -> experimental_squared_sum
    sigma = (sqrt(sst1 / sst2)) * 100;
    r2 = (sst2 - sst1) / sst2;
    disp([])
    """
    residual = D_actual - D_calculated
    experimental_squared_sum = np.sum(D_actual**2)

    #============================================================
    #  R2 pour affichage uniquement
    #============================================================
    upper_term = experimental_squared_sum - np.sum(residual ** 2)
    lower_term = experimental_squared_sum

    Rsquared = 100 * np.sqrt(upper_term / lower_term)
    print("R2: {:.2f}%".format(Rsquared))
    #============================================================
    #  lack of fit pour affichage uniquement
    #============================================================
    upper_term = np.sum(residual**2)
    lower_term = experimental_squared_sum

    lof = 100* np.sqrt(upper_term/lower_term)
    print("lof: {:.2f}%".format(lof))
    return lof