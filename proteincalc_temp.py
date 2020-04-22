# -*- coding: utf-8 -*-


import matplotlib.pyplot as plt
import numpy as np


from brainpy import isotopic_variants

## Define Stuff
Peptide = "MRLAVGA 270        280        290      S        510        520        530        540        550EGCAPGSKKD SSLCKLCMGS GLNLCEPNNK EGYYGYTGAF RCLVEKGDVA        560        570        580        590        600FVKHQTVPQN TGGKNPDPWA KNLNEKDYEL LCLDGTRKPV EEYANCHLAR        610        620        630        640        650APNHAVVTRK DKEACVHKIL RQQQHLFGSN VTDCSGNFCL FRSETKDLLF        660        670        680        690 RDDTVCLAKL HDRNTYEKYL GEEYVKAVGN LRKCSTSSLL EACTFRRP"

Hex = 6
HexNAc = 4
Fuc = 0
Sia = 2
Charge = 1

Deamidation = 1  # number

Disulfidebridges = 0  # enter number; 0 corresponds to denatured protein

Instrument = 'low resolution'  # low resolution,  TOF or super high resolution

## Stopp input

Peptide = Peptide.upper()

countA = Peptide.count('A')
countR = Peptide.count('R')
countN = Peptide.count('N')
countD = Peptide.count('D')
countC = Peptide.count('C')
countQ = Peptide.count('Q')
countE = Peptide.count('E')
countG = Peptide.count('G')
countH = Peptide.count('H')
countI = Peptide.count('I')
countL = Peptide.count('L')
countK = Peptide.count('K')
countM = Peptide.count('M')
countF = Peptide.count('F')
countP = Peptide.count('P')
countS = Peptide.count('S')
countT = Peptide.count('T')
countW = Peptide.count('W')
countY = Peptide.count('Y')
countV = Peptide.count('V')

A = [[3, 5, 1, 1, 0]]
R = [[6, 12, 4, 1, 0]]
N = [[4, 6, 2, 2, 0]]
D = [[4, 5, 1, 3, 0]]
C = [[3, 5, 1, 1, 1]]  # without Caramidomethyl
Q = [[5, 8, 2, 2, 0]]
E = [[5, 7, 1, 3, 0]]
G = [[2, 3, 1, 1, 0]]
H = [[6, 7, 3, 1, 0]]
I = [[6, 11, 1, 1, 0]]
L = [[6, 11, 1, 1, 0]]
K = [[6, 12, 2, 1, 0]]
M = [[5, 9, 1, 1, 1]]
F = [[9, 9, 1, 1, 0]]
P = [[5, 7, 1, 1, 0]]
S = [[3, 5, 1, 2, 0]]
T = [[4, 7, 1, 2, 0]]
W = [[11, 10, 2, 1, 0]]
Y = [[9, 9, 1, 2, 0]]
V = [[5, 9, 1, 1, 0]]
H2O = [[0, 2, 0, 1, 0]]
He = [[6, 10, 0, 5, 0]]
Na = [[8, 13, 1, 5, 0]]
Fu = [[6, 10, 0, 4, 0]]
Si = [[11, 17, 1, 8, 0]]
Deamido = [[0, 1, 1, -1, 0]]
Bridge = [[0, 2, 0, 0, 0]]

if (countC < (Disulfidebridges * 2)):
    print('Number of disulfide bridges does not match number of cystein residues in amino acid sequence')

SP = countA * np.array(A) + countR * np.array(R) + countN * np.array(N) + countD * np.array(D) + countC * np.array(
    C) + countQ * np.array(Q) + countE * np.array(E) + countG * np.array(G) + countH * np.array(H) + countI * np.array(
    I) + countL * np.array(L) + countK * np.array(K) + countM * np.array(M) + countF * np.array(F) + countP * np.array(
    P) + countS * np.array(S) + countT * np.array(T) + countW * np.array(W) + countY * np.array(Y) + countV * np.array(
    V) + H2O

if (Disulfidebridges > 0):
    SP = SP - (Disulfidebridges * Bridge)

if (Deamidation == 0):
    Z = SP + Hex * np.array(He) + HexNAc * np.array(Na) + Fuc * np.array(Fu) + Sia * np.array(Si)
else:
    Z = SP + Hex * np.array(He) + HexNAc * np.array(Na) + Fuc * np.array(Fu) + Sia * np.array(
        Si) + Deamidation * Deamido

z = Z.tolist()
z = z[0]
print('composition =', 'C', z[0], 'H', z[1], 'N', z[2], 'O', z[3], 'S', z[4])



AC = Z[0][0]
AH = Z[0][1]
AN = Z[0][2]
AO = Z[0][3]
AS = Z[0][4]

if (Instrument == 'low resolution'):
    sigma = 0.05
    npeaks = 200

if (Instrument == 'medium'):
    sigma = 0.003
    npeaks = 200

if (Instrument == 'super high resolution'):
    sigma = 0.001
    npeaks = 200

peptide = {'H': AH, 'C': AC, 'O': AO, 'N': AN, 'S': AS}
theoretical_isotopic_cluster = isotopic_variants(peptide, npeaks, charge=Charge)
for peak in theoretical_isotopic_cluster:
    """print(peak.mz, peak.intensity)"""

# produce a theoretical profile using a gaussian peak shape


grid = np.arange(theoretical_isotopic_cluster[0].mz - 1,
                 theoretical_isotopic_cluster[-1].mz + 1, sigma)
intensity = np.zeros_like(grid)

for i, mz in enumerate(grid):
    for peak in theoretical_isotopic_cluster:
        intensity[i] += peak.intensity * np.exp(-(mz - peak.mz) ** 2 / (2 * sigma)
                                                ) / (np.sqrt(2 * np.pi) * sigma)

#intensity = (intensity / intensity.max()) * 100

# draw the profile

plt.plot(grid, intensity)
plt.xlabel("m/z")
plt.ylabel("Relative intensity")
plt.show()

mono = theoretical_isotopic_cluster[0]
mostabundant = grid[np.where(intensity == max(intensity))]
print('monoisotopic mass =', mono.mz)
print('most abundant mass =', mostabundant[0])
# print  (grid[0])