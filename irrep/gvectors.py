
            # ###   ###   #####  ###
            # #  #  #  #  #      #  #
            # ###   ###   ###    ###
            # #  #  #  #  #      #
            # #   # #   # #####  #


##################################################################
## This file is distributed as part of                           #
## "IrRep" code and under terms of GNU General Public license v3 #
## see LICENSE file in the                                       #
##                                                               #
##  Written by Stepan Tsirkin, University of Zurich.             #
##  e-mail: stepan.tsirkin@physik.uzh.ch                         #
##################################################################


import numpy as np
from numpy.linalg import det, norm


class NotSymmetryError(RuntimeError):
    """
    Pass if we attemp to apply to a k-vector a symmetry that does not belong 
    to its little-group.
    """
    pass


#!!   constant  below is 2m/hbar**2 in units of 1/eV Ang^2 (value is
#!!   adjusted in final decimal places to agree with VASP value; program
#!!   checks for discrepancy of any results between this and VASP values)
twomhbar2 = 0.262465831

correction = 0
twomhbar2 *= 1 + correction


# This function is a python translation of a part of WaveTrans Code
def calc_gvectors(
    K,
    RecLattice,
    Ecut,
    nplane=np.Inf,
    Ecut1=-1,
    thresh=1e-3,
    spinor=True,
    nplanemax=10000,
):
    """ 
    Generates G-vectors taking part in the plane-wave expansion of 
    wave-functions in a particular k-point. Optionally, a cutoff `Ecut1` is 
    applied to get rid of large G-vectors.

    Parameters
    ----------
    K : array
        Direct coordinates of the k-point.
    RecLattice : array, shape=(3,3)
        Each row contains the cartesian coordinates of a basis vector forming 
        the unit-cell in reciprocal space.
    Ecut : float
        Plane-wave cutoff (in eV) used in the DFT calulation. Always read from 
        DFT files.
    nplane : int, default=np.Inf
        Number of plane-waves in the expansion of wave-functions (read from DFT 
        files). Only significant for VASP. 
    Ecut1 : float, default=Ecut
        Plane-wave cutoff (in eV) to consider in the expansion of wave-functions.
    thresh : float, default=1e-3
        Threshold for defining the g-vectors with the same energy.
    spinor : bool, default=True
        `True` if wave functions are spinors, `False` if they are scalars. It 
        will be read from DFT files. Mandatory for `vasp`.
    nplanemax : int, default=10000
        Sets the maximun number of iterations when calculating vectors.

    Returns
    -------
    igall : array
        Every column corresponds to a plane-wave of energy smaller than 
        `Ecut`. The number of rows is 6: the first 3 contain direct 
        coordinates of the plane-wave, the fourth row stores indices needed
        to short plane-waves based on energy (ascending order). Fitfth 
        (sixth) row contains the index of the first (last) plane-wave with 
        the same energy as the plane-wave of the current column.
    
"""
    if Ecut1 <= 0:
        Ecut1 = Ecut
    B = RecLattice

    igp = np.zeros(3)
    igall = []
    Eg = []
    memory = np.full(10, True)
    for N in range(nplanemax):
        flag = True
        if N % 10 == 0:
            print(N, len(igall))
        # if len(igall) >= nplane / (2 if spinor else 1):
        #     break
        if len(igall) >= nplane / 2:    # Only enters if vasp
            if spinor:
                break
            else:      # Sure that not spinors?
                if len(igall) >= nplane: # spinor=F, all plane waves found
                    break
                elif np.all(memory): # probably spinor wrong set as spinor=F
                    flag = False
                    raise RuntimeError(
                          "calc_gvectors is stuck "
                          "calculating plane waves of energy larger "
                          "than cutoff Ecut = {}. Make sure that the "
                          "VASP calculation does not include SOC and "
                          "set -spinor if it does.".format(Ecut)
                    )

        for ig3 in range(-N, N + 1):
            for ig2 in range(-(N - abs(ig3)), N - abs(ig3) + 1):
                for ig1 in set([-(N - abs(ig3) - abs(ig2)), N - abs(ig3) - abs(ig2)]):
                    igp = (ig1, ig2, ig3)
                    etot = norm((K + np.array(igp)).dot(B)) ** 2 / twomhbar2
                    if etot < Ecut:
                        igall.append(igp)
                        Eg.append(etot)
                        flag = False
        memory[:-1] = memory[1:]
        memory[-1] = flag

    ncnt = len(igall)
    #    print ("\n".join("{0:+4d}  {1:4d} {2:4d}  |  {3:6d}".format(ig[0],ig[1],ig[2],np.abs(ig).sum()) for ig in igall) )
    #    print (len(igall),len(set(igall)))
    if nplane < np.Inf: # vasp
        if spinor:
            if 2 * ncnt != nplane:
                raise RuntimeError(
                    "*** error - computed 2*ncnt={0} != input nplane={1}".format(
                        2 * ncnt, nplane
                    )
                )
        else:
            if ncnt != nplane:
                raise RuntimeError(
                    "*** error - computed ncnt={0} != input nplane={1}".format(
                        ncnt, nplane
                    )
                )
    igall = np.array(igall, dtype=int)
    ng = igall.max(axis=0) - igall.min(axis=0)
    igall1 = igall % ng[None, :]
    #    print ("ng=",ng)
    #    print ("igall1=",igall1)
    igallsrt = np.argsort((igall1[:, 2] * ng[1] + igall1[:, 1]) * ng[0] + igall1[:, 0])
    #    print (igallsrt)
    igall1 = igall[igallsrt]
    Eg = np.array(Eg)[igallsrt]
    #    print (igall1)
    igall = np.zeros((ncnt, 6), dtype=int)
    igall[:, :3] = igall1
    #    print (igall)
    igall[:, 3] = np.arange(ncnt)
    igall = igall[Eg <= Ecut1]
    Eg = Eg[Eg <= Ecut1]
    srt = np.argsort(Eg)
    Eg = Eg[srt]
    igall = igall[srt, :].T
    wall = [0] + list(np.where(Eg[1:] - Eg[:-1] > thresh)[0] + 1) + [igall.shape[1]]
    for i in range(len(wall) - 1):
        igall[4, wall[i] : wall[i + 1]] = wall[i]
        igall[5, wall[i] : wall[i + 1]] = wall[i + 1]
    #    print ("K={0}\n E={1}\nigall=\n{2}".format(K,Eg,igall.T))
    return igall


def transformed_g(kpt, ig, RecLattice, A):
    """
    Determines how the transformation matrix `A` reorders the reciprocal
    lattice vectors taking part in the plane-wave expansion of wave-functions.

    Parameters
    ----------
    kpt : array, shape=(3,)
        Direct coordinates of the k-point.
    ig : array
        Every column corresponds to a plane-wave of energy smaller than 
        `Ecut`. The number of rows is 6: the first 3 contain direct 
        coordinates of the plane-wave, the fourth row stores indices needed
        to short plane-waves based on energy (ascending order). Fitfth 
        (sixth) row contains the index of the first (last) groups of 
        plane-waves of identical energy.
    RecLattice : array, shape=(3,3)
        Each row contains the cartesian coordinates of a basis vector forming 
        the unit-cell in reciprocal space.
    A : array, shape=(3,3)
        Matrix describing the tranformation of basis vectors of the unit cell 
        under the symmetry operation.
    
    Returns
    -------
    rotind : array
        `rotind[i]`=`j` if `A`*`ig[:,i]`==`ig[:,j]`.
"""
    #    Btrr=RecLattice.dot(A).dot(np.linalg.inv(RecLattice))
    #    Btr=np.array(np.round(Btrr),dtype=int) # The transformed rec. lattice expressed in the basis of the original rec. lattice
    #    if np.sum(np.abs(Btr-Btrr))>1e-6:
    #        raise NotSymmetryError("The lattice is not invariant under transformation \n {0}".format(A))
    B = np.linalg.inv(A).T
    kpt_ = B.dot(kpt)
    dkpt = np.array(np.round(kpt_ - kpt), dtype=int)
    #    print ("Transformation\n",A)
    #    print ("kpt ={0} -> {1}".format(kpt,kpt_))
    if not np.isclose(dkpt, kpt_ - kpt).all():
        raise NotSymmetryError(
            "The k-point {0} is transformed to non-equivalent point {1}  under transformation\n {2}".format(
                kpt, kpt_, A
            )
        )

    igTr = B.dot(ig[:3, :]) + dkpt[:, None]  # the transformed
    igTr = np.array(np.round(igTr), dtype=int)
    #    print ("the original g-vectors :\n",ig)
    #    print ("the transformed g-vectors :\n",igTr)
    ng = ig.shape[1]
    rotind = -np.ones(ng, dtype=int)
    for i in range(ng):
        for j in range(ig[4, i], ig[5, i]):
            if (igTr[:, i] == ig[:3, j]).all():
                rotind[i] = j
                break
        if rotind[i] == -1:
            raise RuntimeError(
                "no pair found for the transformed g-vector igTr[{i}]={igtr}  ig[{i}]={ig} in the original g-vectors set (kpoint{kp}). Other g-vectors with same energy:\n{other} ".format(
                    i=i,
                    ig=ig[:3, i],
                    igtr=igTr[:, i],
                    kp=kpt,
                    other=ig[:3, ig[4, i] : ig[5, i]],
                )
            )
    return rotind


def symm_eigenvalues(
    K, RecLattice, WF, igall, A=np.eye(3), S=np.eye(2), T=np.zeros(3), spinor=True
):
    """
    Calculate the traces of a symmetry operation for the wave-functions in a 
    particular k-point.

    Parameters
    ----------
    K : array, shape=(3,)
        Direct coordinates of the k-point.
    RecLattice : array, shape=(3,3)
        Each row contains the cartesian coordinates of a basis vector forming 
        the unit-cell in reciprocal space.
    WF : array
        `WF[i,j]` contains the coefficient corresponding to :math:`j^{th}`
        plane-wave in the expansion of the wave-function in :math:`i^{th}`
        band. It contains only plane-waves of energy smaller than `Ecut`.
    igall : array
        Returned by `__sortIG`.
        Every column corresponds to a plane-wave of energy smaller than 
        `Ecut`. The number of rows is 6: the first 3 contain direct 
        coordinates of the plane-wave, the fourth row stores indices needed
        to short plane-waves based on energy (ascending order). Fitfth 
        (sixth) row contains the index of the first (last) plane-wave with 
        the same energy as the plane-wave of the current column.
    A : array, shape=(3,3)
        Matrix describing the tranformation of basis vectors of the unit cell 
        under the symmetry operation.
    S : array, shape=(2,2)
        Matrix describing how spinors transform under the symmetry.
    T : array, shape=(3,)
        Translational part of the symmetry operation, in terms of the basis 
        vectors of the unit cell.
    spinor : bool, default=True
        `True` if wave-functions are spinors, `False` if they are scalars.

    Returns
    -------
    array
        Each element is the trace of the symmetry operation in a wave-function.
    """
    npw1 = igall.shape[1]
    multZ = np.exp(
        -1.0j * (2 * np.pi * np.linalg.inv(A).dot(T).dot(igall[:3, :] + K[:, None]))
    )
    igrot = transformed_g(K, igall, RecLattice, A)
    if spinor:
        part1 = WF[:, igrot].conj() * WF[:, :npw1] * S[0, 0]
        part2 = (
            WF[:, igrot + npw1].conj() * WF[:, npw1:] * S[1, 1]
            + WF[:, igrot].conj() * WF[:, npw1:] * S[0, 1]
            + WF[:, igrot + npw1].conj() * WF[:, :npw1] * S[1, 0]
        )
        return np.dot(part1 + part2, multZ)
    else:
        return np.dot(WF[:, igrot].conj() * WF[:, :], multZ)


def symm_matrix(
    K, RecLattice, WF, igall, A=np.eye(3), S=np.eye(2), T=np.zeros(3), spinor=True
):
    """
    Computes the matrix S_mn = <Psi_m|{A|T}|Psi_n>

    Parameters
    ----------
    K : array, shape=(3,)
        Direct coordinates of the k-point.
    RecLattice : array, shape=(3,3)
        Each row contains the cartesian coordinates of a basis vector forming 
        the unit-cell in reciprocal space.
    WF : array
        `WF[i,j]` contains the coefficient corresponding to :math:`j^{th}`
        plane-wave in the expansion of the wave-function in :math:`i^{th}`
        band. It contains only plane-waves if energy smaller than `Ecut`.
    igall : array
        Returned by `__sortIG`.
        Every column corresponds to a plane-wave of energy smaller than 
        `Ecut`. The number of rows is 6: the first 3 contain direct 
        coordinates of the plane-wave, the fourth row stores indices needed
        to short plane-waves based on energy (ascending order). Fitfth 
        (sixth) row contains the index of the first (last) plane-wave with 
        the same energy as the plane-wave of the current column.
    A : array, shape=(3,3)
        Matrix describing the tranformation of basis vectors of the unit cell 
        under the symmetry operation.
    S : array, shape=(2,2)
        Matrix describing how spinors transform under the symmetry.
    T : array, shape=(3,)
        Translational part of the symmetry operation, in terms of the basis 
        vectors of the unit cell.
    spinor : bool, default=True
        `True` if wave functions are spinors, `False` if they are scalars.

    Returns
    -------
    array
        Matrix of the symmetry operation in the basis of eigenstates of the 
        Bloch Hamiltonian :math:`H(k)`.
    """
    npw1 = igall.shape[1]
    multZ = np.exp(-1.0j * (2 * np.pi * A.dot(T).dot(igall[:3, :] + K[:, None])))
    igrot = transformed_g(K, igall, RecLattice, A)
    if spinor:
        WF1 = np.stack([WF[:, igrot], WF[:, igrot + npw1]], axis=2).conj()
        WF2 = np.stack([WF[:, :npw1], WF[:, npw1:]], axis=2)
        #        print (WF1.shape,WF2.shape,multZ.shape,S.shape)
        return np.einsum("mgs,ngt,g,st->mn", WF1, WF2, multZ, S)
    else:
        return np.einsum("mg,ng,g->mn", WF[:, igrot].conj(), WF, multZ)