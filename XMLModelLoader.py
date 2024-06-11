# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 11:20:59 2012

@author: mbouhier
"""

#import matplotlib.pyplot as pl
import numpy as np
import xml.etree.ElementTree as et
from numpy import log,exp


class ParamConteneur(object):
    def __init__(self, **kwargs):
        for k, v in list(kwargs.items()):
            setattr(self, k, v)
        
        
        
class XMLModelLoader(object):
    """
    Retrieve model informations from XMLModelFit files
    usage:
        model = loadModel(filename)
        model.name
        model.x_min
        model.x_max
        model.total_equation_std = coeff1*f11(x) + coeff2*f12(x) + ... + coeffn*f1n(x)
        model.match_names[coeffX] = nom original du coeffX dans le xml
        
        Avec N models chargés:
        models = loadModels(filename)
        models.total_equation_std = coeff1*(model1) + coeff2*(model2) + ... + coeffN*(modelN)
           
    """
    def __init__(self):
       pass

    def loadModels(self,modelFitXMLfilenames):
        """
          Charge les XMLs contenant les models pour le curve fit
          retourne:
              - la liste des models chargés
              - l'equation complete 
              - les noms des coefficients dans l'equation totale
              - les bornes des coefficients sous forme [(min,max),...,(min,max)]
              - le nombre de modèles
              - un dictionnaire de corespondance entre noms des coeffs dans
                l'equation totale, leurs models et noms de variables associés dans
                les models initiaux
                match_names[coeff_name_in_equ_total]["model_name"]    = model_x 
                match_names[coeff_name_in_equ_total]["original_name"] = var_name_in_model_x
        """
        models         = []
        total_equation = ""
        model_nb       = len(modelFitXMLfilenames)
        match_names    = dict()
        
        coeffs_names  = ["coeff[%d]" % i for i in range(model_nb)]
        coeffs_bounds = [(0,1) for i in range(model_nb) ]
        
        start_idx = model_nb
        
        for idx,filename in enumerate(modelFitXMLfilenames):
            model = self.loadModel(filename, start_idx)
            models.append(model)
        
            start_idx = start_idx + len(model.all_coeffs_names)

            #concatenate name list ans coeffs_bounds
            coeffs_names   = coeffs_names  + model.all_coeffs_names 
            coeffs_bounds  = coeffs_bounds + model.all_coeffs_bounds 
            total_equation = total_equation + ("+" if idx!=0 else "") + " coeff[%d]*(" % (idx,) + model.equation_std + ")"
            
            match_names["coeff[%d]"%(idx,)] = model.name
            #ajout des identifiants des coefficients "internes" des equations 
            match_names.update(model.match_names)
            
        return models,total_equation,coeffs_names,coeffs_bounds,match_names
        
        
    def _get_coeff_nb(self,filename):
        pass
    
    def getModelName(self,filename):
        tree = et.parse(filename)
        root = tree.getroot()
        model_name = root.find("name").text.strip()
        return model_name
        
    def loadModel(self,filename,start_idx_for_coeffs=0):
        tree = et.parse(filename)
        root = tree.getroot()
        
        model_name     = root.find("name").text.strip()
        math_model     = root.find("math_model")
        component_list = math_model.find("components").findall("component")
        
        #=============== infos sur le model de reference ===================#
        #TODO: possibilité de mettre plusieurs models avec differente conditions
        #d'acquisition
        exp_model = root.find("exp_models")
        model     = exp_model.find("model") #models = exp_model.findall("model")
        ref_path  = model.find("path").text.strip()
        #===================================================================#
        
        
        x_lim = []
        x_lim = math_model.find('xlim').text.split('-')
        x_lim = list(map(float,x_lim)) #on converti en float

        total_equation   = ""
        
        all_coeffs_names  = []
        all_coeffs_bounds = []
        # Dictionnaire de correpondance 
        # match_vars_names["coeff[x]"] = "model_name - component_name - parameter_name"
        match_names  = dict() 
        
        components_container = []
        index                = start_idx_for_coeffs - 1
        
        #==================================================================#
        #       On boucle sur toutes les balises <component> du xml        #
        #==================================================================#
        for cp_idx,component in enumerate(component_list):
            
            c_name       = component.find("name").text
            c_parameters = component.find("parameters").text.split(',')
            c_equation   = component.find("equation").text
            c_equation   = self._translate_for_python_syntax(c_equation)
            #equation with standardized coeff names (initialisation)
            eq_std_c_names = c_equation 
            
            #==================================================================#
            #  On boucle sur tout les coefficients declarés dans la balise     #
            #                   <parameters> du xml                            #
            #==================================================================#
            coeff_params = []     #contient les noms tel qu'ils sont dans le xml
            for param_idx,coeff in enumerate(c_parameters):
                # sous la forme "name = vmin-vmax" 
                v = coeff.split('=')
                
                if len(v) == 2: #si la balise n'est pas vide et avec 'a' = 'b'
                    index = index + 1
                    coeff_name = v[0].strip() #a gauche du "="
                    coeff_min  = v[1].split('-')[0]
                    coeff_max  = v[1].split('-')[1]
                    coeff_name_std = 'coeff[%d]' % (index) #nom 'standardisé'
                    
                    coeff_param = ParamConteneur( name = coeff_name, 
                                                  std_name = coeff_name_std,
                                                  min = float(coeff_min),
                                                  max = float(coeff_max) 
                                                 )
                      
                    coeff_params.append(coeff_param)
                    
                    all_coeffs_names.append(coeff_name_std)
                    all_coeffs_bounds.append((float(coeff_min),float(coeff_max)))
                    
                    #on remplace param_name par coeffN dans l'equation du component
                    eq_std_c_names = eq_std_c_names.replace(coeff_name,coeff_name_std)
                    
                    #on ajoute l'entrée dans le dictionnaire des noms
                    match_name = "%s - %s - %s" % ( model_name, c_name, coeff_name)
                    match_names[coeff_name_std] = match_name
                    
            #==================================================================#
            #==================================================================#
            
            compo_infos  = ParamConteneur( name         = c_name,
                                           equation     = c_equation,
                                           equation_std = eq_std_c_names,
                                           parameters   = coeff_params 
                                          )
            components_container.append(compo_infos)
            
            total_equation = total_equation + ("+" if cp_idx!=0 else "") + eq_std_c_names

                       
        current_model = ParamConteneur(name       = model_name,
                                       x_min      = x_lim[0],
                                       x_max      = x_lim[1],
                                       components = components_container,
                                       all_coeffs_names  = all_coeffs_names,
                                       all_coeffs_bounds = all_coeffs_bounds,
                                       equation_std      = total_equation,
                                       match_names       = match_names,
                                       ref_path          = ref_path
                                       )
        return current_model
            
    def _translate_for_python_syntax(self,equation):
            #On remet l'equation en forme, version python (vs matlab)
            equation = equation.strip() #enleve les espaces blanc
            equation = equation.replace('.*','*')
            equation = equation.replace('./','/')
            equation = equation.replace('.^','**')
            equation = equation.replace('inf','<')
            equation = equation.replace('sup','>')
            return equation
        
def testloadModel():
    
    folder = "\\\\crabe\\communs\\LIDyL\\PCR\\Mickael Bouhier\\PCA\\xml\\"
    filename = folder + "wustite.xml"
    
    loader = XMLModelLoader()   
    
    model = loader.loadModel(filename)        
    
    title = "Model named '%s' defined in %.2f - %.2f:" % (model.name, model.x_min, model.x_max)
    print(title)
    print("="*len(title))
    
    for component in model.components:
        print("Component '%s':" % (component.name))

        if len(component.parameters) != 0:
            for param in component.parameters:
               print("    param '%s' : from %.2f to %.2f" % (param.name,param.min,param.max)) 
        else:
            print("    params   : No param")
            
        print("    equation originale:" , component.equation)
        print("    equation standard :" , component.equation_std)
        
        
def testloadModels():
    
    
    folder = "\\\\crabe\\communs\\LIDyL\\PCR\\Mickael Bouhier\\PCA\\xml\\"

    filename  = folder + "wustite.xml"
    filename2 = folder + "magnetite.xml"
    filename3 = folder + "maghemite.xml"
    
    loader = XMLModelLoader()   
    
    models,total_equation,coeffs_names,coeffs_bounds,match_names = loader.loadModels([filename,filename2,filename3])        
    
    for idx,model in enumerate(models):
        title = "Model %d named '%s' defined in %.2f - %.2f:" % (idx,model.name, model.x_min, model.x_max)
        print(title)
        print("="*len(title))
        
        for component in model.components:
            print("Component '%s':" % (component.name))
    
            if len(component.parameters) != 0:
                for param in component.parameters:
                   print("    param '%s' : from %.2f to %.2f" % (param.name,param.min,param.max)) 
            else:
                print("    params   : No param")
                
            print("    equation originale:" , component.equation)
            print("    equation standard :" , component.equation_std)
        
      
    print(len(title)*"=")
    print("Total equation:")
    print(total_equation)
        
if __name__=="__main__":    
    #testloadModel()
    testloadModel()                       
                 
    