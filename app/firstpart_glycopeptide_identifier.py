# -*- coding: utf-8 -*-

import numpy as np

from pyteomics import mgf
url='C:/Users/Melissa/Desktop/glycopeptide/test.mgf'

# import mgf file
def mgfread(url):
    reader = []
    with mgf.read(url) as temp_read:
        for thing in temp_read:
            reader.append(thing)
    return reader

def backup (spectrum):
    oldspeactra = spectrum
    return oldspeactra

glycospectra = mgfread(url)
org_spectra=backup(glycospectra)

# classifly as glycopeptide spactra based on 366 OR 657 oxonium ions (later implement also HexNac difference)
new = [''] * len(glycospectra)
for i in range (0,len(glycospectra)):
       #print(np.any([(reader[i][('m/z array')] > 366.07) & (reader[i][('m/z array')] < 366.22) , (reader[i][('m/z array')] > 657.16) & (reader[i][('m/z array')] < 657.29)]))
       new[i] = np.any([(glycospectra[i][('m/z array')] > 366.125) & (glycospectra[i][('m/z array')] < 366.16) , (glycospectra[i][('m/z array')] > 657.16) & (glycospectra[i][('m/z array')] < 657.29)])

##print(new.count(True), 'number of glycopeptide specta')
##print(new.count(False), 'number of peptide specta')

for i in range (0, len(new)):
    if new[i] == False:
        glycospectra[i]= 0

glycospectra[:] = (value for value in glycospectra if value != 0)


# the next part needs to be a function: Find papide mass based on Pep+HexNac as most intense
def findpep_HexNAc_mass (x):

    diff = np.zeros((len(glycospectra[x][('m/z array')]),len(glycospectra[x][('m/z array')])))
                
               
    for j in range (0, len(glycospectra[x][('m/z array')])):
                for k in range (0, len(glycospectra[x][('m/z array')])):
                        diff[j][k] = glycospectra[x][('m/z array')][j] - glycospectra[x][('m/z array')][k]
                        
    rows_HexNAc, cols_HexNAc = np.where(np.logical_and(diff > 203.02, diff < 203.12))
    '''rows_HexNAcHex, cols_HexNAcHex = np.where(np.logical_and(diff > 364, diff < 366.5)) # find peptide mass based on HexNac AND HexNAcHex'''
    if len(cols_HexNAc) == 0:
        print('no peptide mass found, no HexNAc difference')
        Pep_HexNAC_mass = 0
         
    else:    
        '''matches = np.intersect1d(cols_HexNAc, cols_HexNAcHex)'''
        matches = cols_HexNAc    
            # delte matches below mass range 700 m/z
        for i in range (0, len(matches)):
            if  glycospectra[x][('m/z array')][matches[i]] < 700:
                matches[i] = 0
                    
        matches = matches[matches != 0]
            
        if len(matches) == 0:
            print('no peptide mass found, peptide mass to low')
            Pep_HexNAC_mass = 0
        else:  
            for i in range (0, len(matches)):
                if  glycospectra[x][('m/z array')][matches[i]] < 700:
                    matches[i] = 0
                    
            matches = matches[matches != 0]  
            intensities = np.zeros((len(matches)))
            for j in range (0, len(matches)):
                    intensities[j] =  glycospectra[x][('intensity array')][matches[j]]
                                
            maxint = np.maximum.reduce(intensities)
            '''print(maxint)'''
        
            pep_HexNAc_index = np.where(glycospectra[x][('intensity array')] == maxint)
            
            if len(pep_HexNAc_index[0] ) > 1:
                print('ambigous peptide mass')
                Pep_HexNAC_mass = 0
            else:    
                Pep_HexNAC_mass =  glycospectra[x][('m/z array')][pep_HexNAc_index]
                print(Pep_HexNAC_mass)    
    return Pep_HexNAC_mass
    

results = []
for i in range (0, len(glycospectra)):
    results.append(findpep_HexNAc_mass(i))
    
for i in range (0, len(results)):
    if results[i] == 0:
        glycospectra[i]= 0
        

glycospectra[:] = (value for value in glycospectra if value != 0)
results[:] = (value for value in results if value != 0)      

Peptidemass = np.zeros(len(results))
for i in range (0, len(results)):
    Peptidemass[i] = results[i] - 203.0866


# keep precursor mass and charge
precursorcharge = []
precursormass = []
glycopepitdemass = []
for i in range (0, len(glycospectra)):
    precursormass.append(glycospectra[i][('params')][('pepmass')][0])
    precursorcharge.append(glycospectra[i][('params')][('charge')][0])
    glycopepitdemass.append(precursormass[i]*precursorcharge[i]-precursorcharge[i]*1.007276466621 + 1.007276466621)

glycanmass = glycopepitdemass - Peptidemass
    
# this needs to be a function
# als erstes 291, 366 und 657 löschen
def filteredspectrum (x):    
    for i in range(0, len(glycospectra[x][('m/z array')])):
        if  (glycospectra[x][('m/z array')][i] > 292  and glycospectra[x][('m/z array')][i] < 292.5):
             glycospectra[x][('m/z array')][i] = 0
             glycospectra[x][('intensity array')][i] = 0

        if  (glycospectra[x][('m/z array')][i] > 366.1  and glycospectra[x][('m/z array')][i] < 367.3):
             glycospectra[x][('m/z array')][i] = 0
             glycospectra[x][('intensity array')][i] = 0

        if  (glycospectra[x][('m/z array')][i] > 657  and glycospectra[x][('m/z array')][i] < 658.5):
             glycospectra[x][('m/z array')][i] = 0
             glycospectra[x][('intensity array')][i] = 0
    
    # delete everything bigger than peptide mass         

        if  glycospectra[x][('m/z array')][i] > Peptidemass[x]+1:
             glycospectra[x][('m/z array')][i] = 0
             glycospectra[x][('intensity array')][i] = 0
    
    return glycospectra[x]


results_2 = []
for i in range (0, len(glycospectra)):
    results_2.append(filteredspectrum(i))
 
# output mgf with new peptide mass and charge
for i in range(0, len(results_2)):   
     del glycospectra[i][('params')][('com')]
     del glycospectra[i][('params')][('username')]
     
for i in range(0, len(results_2)):   
    results_2[i][('params')].update({'pepmass': (Peptidemass[i], 1)})
    results_2[i][('params')].update({'charge': 1})


mgf.write(results_2, 'C:/Users/Melissa/Desktop/glycopeptide/test.mgf')
