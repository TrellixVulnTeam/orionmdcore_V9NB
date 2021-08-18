# (C) 2020 OpenEye Scientific Software Inc. All rights reserved.
#
# TERMS FOR USE OF SAMPLE CODE The software below ("Sample Code") is
# provided to current licensees or subscribers of OpenEye products or
# SaaS offerings (each a "Customer").
# Customer is hereby permitted to use, copy, and modify the Sample Code,
# subject to these terms. OpenEye claims no rights to Customer's
# modifications. Modification of Sample Code is at Customer's sole and
# exclusive risk. Sample Code may require Customer to have a then
# current license or subscription to the applicable OpenEye offering.
# THE SAMPLE CODE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED.  OPENEYE DISCLAIMS ALL WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. In no event shall OpenEye be
# liable for any damages or liability in connection with the Sample Code
# or its use.


import os

import orionmdcore

PACKAGE_DIR = os.path.dirname(os.path.dirname(orionmdcore.__file__))
COFACTOR_DIR = os.path.join(
    PACKAGE_DIR, "orionmdcore/forcefield/ff_library", "cofactors"
)
EXT_FORCEFIELD_DIR = os.path.join(
    PACKAGE_DIR, "orionmdcore/forcefield/ff_library", "ext_forcefield"
)

proteinff = {
    "Amber99SBildn": "amber99sbildn.xml",
    "Amber99SB": "amber99sb.xml",
    "Amber14SB": "amber14/protein.ff14SB.xml",
    "AmberFB15": "amberfb15.xml",
}

ligandff = {
    "Gaff_1.81": "GAFF",
    "Gaff_2.11": "GAFF2",
    "Smirnoff99Frosst": "smirnoff99Frosst_reference_0_2_spec.offxml",
    "OpenFF_1.1.1": "openff_unconstrained-1.1.1.offxml",
    "OpenFF_1.2.1": "openff_unconstrained-1.2.1.offxml",
    "OpenFF_1.3.1": "openff_unconstrained-1.3.1.offxml",
    "OpenFF_2.0.0": "openff_unconstrained-2.0.0.offxml"
}

otherff = ligandff

solventff = {"Tip3p": "tip3p.xml"}

counter_ionsff = {"Counter_ions": "amber14/tip3p.xml"}

metals_ff = {"Metals": "amber14/tip3p.xml"}

excipients_ff = {"Excipients": "amber14/tip3p.xml"}

# cofactors_ff = {'Cofactors': [f for f in glob.glob(COFACTOR_DIR+"/*.xml")]}
cofactors_ff = {"Cofactors": os.path.join(COFACTOR_DIR, "cofactors.xml")}

lipids_ff = {"Lipids": "amber14/lipid17.xml"}

nucleics_ff = {"Nucleics": "amber14-all.xml"}


class Default:
    class _Record:

        def __init__(self, name, offxml):
            self.name = name
            self.offxml = offxml

    proteinff = _Record("Amber14SB", "amber14/protein.ff14SB.xml")
    ligandff = _Record("OpenFF_2.0.0",  "openff_unconstrained-2.0.0.offxml")
    otherff = _Record("OpenFF_2.0.0",  "openff_unconstrained-2.0.0.offxml")
    solventff = _Record("Tip3p", "tip3p.xml")
    counter_ionsff = _Record("Counter_ions", "amber14/tip3p.xml")
    metals_ff = _Record("Metals", "amber14/tip3p.xml")
    excipients_ff = _Record("Excipients", "amber14/tip3p.xml")
    cofactors_ff = _Record("Cofactors", os.path.join(COFACTOR_DIR, "cofactors.xml"))
    lipids_ff = _Record("Lipids", "amber14/lipid17.xml")
    nucleics_ff = _Record("Nucleics", "amber14-all.xml")


protein_standard_residue_names = [
    "ALA",
    "ARG",
    "ASN",
    "ASP",
    "CYS",
    "GLN",
    "GLU",
    "GLY",
    "HIS",
    "ILE",
    "LEU",
    "LYS",
    "MET",
    "PHE",
    "PRO",
    "SER",
    "THR",
    "TRP",
    "TYR",
    "VAL",
    "ASX",
    "GLX",
    "CYX",
    "CYH",
    "HID",
    "HIE",
    "HIP",
    "ACE",
    "NME",
]
