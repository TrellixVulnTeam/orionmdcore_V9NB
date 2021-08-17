# Copyright (C) 2020 OpenEye Scientific Software, Inc.
#
# THIS CODE IS PROPRIETARY TO OPENEYE SCIENTIFIC SOFTWARE INC AND IS SUBJECT
# TO THE FULL PROTECTION OF COPYRIGHT AND TRADESECRET LAW.  IT MAY BE USED
# ONLY PURSUANT TO A VALID AND CURRENT LICENSE FROM OPENEYE AND SUBJECT TO
# THE TERMS AND CONDITIONS THEREIN.  ALL OTHER USE IS STRICTLY PROHIBITED.
# PLEASE CONTACT OPENEYE AT LEGAL@EYESOPEN.COM IF YOU HAVE ANY QUESTIONS
# ABOUT THIS WARNING.

try:
    from openeye import oechem

    from openeye import oespruce
except ImportError:
    from orionmdcore import __installation__error__
    raise ImportError(__installation__error__)


from orionmdcore.forcefield import ff_library

from orionmdcore.forcefield.utils import ParamMolStructure

import parmed

from io import StringIO

from lxml import etree

from simtk.openmm.app.forcefield import NonbondedGenerator


def nsr_template_generator(
    protein, omm_topology, omm_forcefield, openff=ff_library.Default.ligandff
):
    """
    This function is able to parametrize a protein containing
    mostly unknown and known Non Standard Residues. Currently NSR
    containing Proline or beta NSR are not supported.

    Parameters:
    -----------
    protein: OEMol molecule
        The protein with the NSR to parametrize
    omm_topology: simtk.openmm.app.topology.Topology
        The openmm protein topology in sync with the oe protein molecule

    omm_forcefield: simtk.openmm.app.forcefield.ForceField
        The OpenMM ForceField used to parametrize the protein

    openff: string
        The Open Force Field file used to parametrize the Non Standard Residues


    Return:
    -------
    ffmxl_template_list: list of strings
        Python list of strings containing the openmm template
        for each non standard residue detected. Each list element
        (NSR template) can be loaded into the OpenMM ForceField object
    """

    unmatched_res_list = omm_forcefield.getUnmatchedResidues(omm_topology)

    non_standard_reside_names = set()

    for res in unmatched_res_list:
        if res.name not in ff_library.protein_standard_residue_names:
            non_standard_reside_names.add(res.name)

    # This dictionary is used to store the chain ID and residue number of the all NSR
    map_nsr = dict()

    for nsr_name in non_standard_reside_names:
        for oe_res in oechem.OEGetResidues(protein):
            if oe_res.GetName() == nsr_name:
                map_nsr[nsr_name] = [
                    oe_res.GetChainID(),
                    str(oe_res.GetResidueNumber()),
                ]
                break

    ffmxl_template_list = []
    for nsr_name in non_standard_reside_names:

        # Extract the NSR from the protein
        nsr_match = oechem.OEAtomMatchResidueID()

        nsr_match.SetName(nsr_name)
        nsr_match.SetChainID(map_nsr[nsr_name][0])
        nsr_match.SetResidueNumber(map_nsr[nsr_name][1])

        pred_nsr = oechem.OEAtomMatchResidue(nsr_match)
        oe_nsr = oechem.OEMol()
        oechem.OESubsetMol(oe_nsr, protein, pred_nsr, True)

        # C or N terminus Non Standard Residue check
        isCTerminus = False
        isNTerminus = False

        # N backbone atom
        pred = oechem.OEAndAtom(oechem.OEIsBackboneAtom(), oechem.OEIsNitrogen())

        for at in oe_nsr.GetAtoms(pred):

            nbors = [nbr for nbr in at.GetAtoms(oechem.OEIsHydrogen())]
            if len(nbors) == 3:
                isNTerminus = True

        # C backbone atom
        pred = oechem.OEAndAtom(oechem.OEIsCarbon(), oechem.OEIsBackboneAtom())
        pred_not_ca = oechem.OEAndAtom(pred, oechem.OENotAtom(oechem.OEIsCAlpha()))

        for at in oe_nsr.GetAtoms(pred_not_ca):
            nbors = [nbr for nbr in at.GetAtoms(oechem.OEIsOxygen())]
            if len(nbors) == 2:
                isCTerminus = True

        if isCTerminus:
            termini = "C Terminus"
        elif isNTerminus:
            termini = "N Terminus"
        else:
            termini = "Not Termini"

        print("Non-Standard Residue Detected: {} - {}".format(nsr_name, termini))

        oe_nsr_caps = oechem.OEMol(oe_nsr)

        nsr_formal_charge = 0
        for at in oe_nsr_caps.GetAtoms():
            nsr_formal_charge += at.GetFormalCharge()

        # Load the correct FF Library Template
        if nsr_formal_charge == 0 and isCTerminus:
            reference_residue_name = "CALA"
        elif nsr_formal_charge == 0 and isNTerminus:
            reference_residue_name = "NALA"
        elif nsr_formal_charge == 0 and not (isCTerminus or isNTerminus):
            reference_residue_name = "ALA"
        elif nsr_formal_charge < 0 and isCTerminus:
            reference_residue_name = "CASP"
        elif nsr_formal_charge < 0 and isNTerminus:
            reference_residue_name = "NASP"
        elif nsr_formal_charge < 0 and not (isCTerminus or isNTerminus):
            reference_residue_name = "ASP"
        elif nsr_formal_charge > 0 and isCTerminus:
            reference_residue_name = "CLYS"
        elif nsr_formal_charge > 0 and isNTerminus:
            reference_residue_name = "NLYS"
        else:
            reference_residue_name = "LYS"

        # print("Loaded Template: {}".format(reference_residue_name))

        for at in oe_nsr_caps.GetAtoms():
            res = oechem.OEAtomGetResidue(at)
            if isCTerminus or isNTerminus:
                res.SetName(reference_residue_name[1:])
            else:
                res.SetName(reference_residue_name)
            oechem.OEAtomSetResidue(at, res)

        if isCTerminus:
            oespruce.OECapNTermini(oe_nsr_caps)
        elif isNTerminus:
            oespruce.OECapCTermini(oe_nsr_caps)
        else:
            oespruce.OECapTermini(oe_nsr_caps)

        # Add Hydrogens after capping
        oechem.OEPlaceHydrogens(oe_nsr_caps)
        # Reset Atom Order because we added Hydrogens
        oechem.OEPDBOrderAtoms(oe_nsr_caps, False)

        if isCTerminus:
            if oe_nsr_caps.NumAtoms() != oe_nsr.NumAtoms() + 6:
                raise ValueError(
                    "Error Capping the Non Standard Residue C Terminus  {}. Atoms expected {} vs {}".format(
                        nsr_name, oe_nsr.NumAtoms() + 6, oe_nsr_caps.NumAtoms()
                    )
                )

        elif isNTerminus:
            if oe_nsr_caps.NumAtoms() != oe_nsr.NumAtoms() + 6:
                raise ValueError(
                    "Error Capping the Non Standard Residue N Terminus  {}. Atoms expected {} vs {}".format(
                        nsr_name, oe_nsr.NumAtoms() + 6, oe_nsr_caps.NumAtoms()
                    )
                )

        else:
            if oe_nsr_caps.NumAtoms() != oe_nsr.NumAtoms() + 12:
                raise ValueError(
                    "Error Capping the Non Standard Residue {}. Atoms expected {} vs {}".format(
                        nsr_name, oe_nsr.NumAtoms() + 12, oe_nsr_caps.NumAtoms()
                    )
                )

        # Generate Unique atom names for the new capped non-standard residue
        for index, oe_at in enumerate(oe_nsr_caps.GetAtoms()):
            oe_at.SetName(oe_at.GetName() + "_" + str(index))

        # # TODO
        # with oechem.oemolostream("oe_nsr_caps.oeb") as ofs:
        #     oechem.OEWriteConstMolecule(ofs, oe_nsr_caps)

        nsr_backbone_atoms = []
        nsr_side_chain_atoms = []
        C_ACE_or_N_NME_atoms = []
        CBeta_side_chain = []

        if isCTerminus or isNTerminus:
            nsr_caps_pred_backbone = oechem.OEIsBackboneAtom(True, True)
        else:
            nsr_caps_pred_backbone = oechem.OEIsBackboneAtom()

        nsr_caps_match_ACE = oechem.OEAtomMatchResidueID()
        nsr_caps_match_ACE.SetName("ACE")
        nsr_caps_pred_ACE = oechem.OEAtomMatchResidue(nsr_caps_match_ACE)

        nsr_caps_match_NME = oechem.OEAtomMatchResidueID()
        nsr_caps_match_NME.SetName("NME")
        nsr_caps_pred_NME = oechem.OEAtomMatchResidue(nsr_caps_match_NME)

        pred = oechem.OEAndAtom(
            nsr_caps_pred_backbone,
            oechem.OENotAtom(oechem.OEOrAtom(nsr_caps_pred_ACE, nsr_caps_pred_NME)),
        )

        for atom in oe_nsr_caps.GetAtoms(pred):

            nsr_backbone_atoms.append(atom)

            if atom.GetAtomicNum() == oechem.OEElemNo_N:

                for nbor in atom.GetAtoms(oechem.OEIsHydrogen()):
                    nsr_backbone_atoms.append(nbor)

                # C in ACE
                for nbor in atom.GetAtoms(
                    oechem.OENotAtom(
                        oechem.OEOrAtom(oechem.OEIsHydrogen(), oechem.IsCAlpha())
                    )
                ):
                    C_ACE_or_N_NME_atoms.append(nbor)

                for nbor in atom.GetAtoms(oechem.OEIsCAlpha()):
                    for can in nbor.GetAtoms(oechem.OEIsHydrogen()):
                        nsr_backbone_atoms.append(can)

        nsr_caps_match_reference_residue = oechem.OEAtomMatchResidueID()
        if isCTerminus or isNTerminus:
            nsr_caps_match_reference_residue.SetName(reference_residue_name[1:])
        else:
            nsr_caps_match_reference_residue.SetName(reference_residue_name)

        nsr_caps_pred_reference_residue = oechem.OEAtomMatchResidue(
            nsr_caps_match_reference_residue
        )

        # NSR SIDE CHAIN
        for atom in oe_nsr_caps.GetAtoms(nsr_caps_pred_reference_residue):
            if atom not in nsr_backbone_atoms:
                nsr_side_chain_atoms.append(atom)

        # N in NME
        for atom in oe_nsr_caps.GetAtoms(
            oechem.OEAndAtom(nsr_caps_pred_NME, oechem.OEIsNitrogen())
        ):
            C_ACE_or_N_NME_atoms.append(atom)

        # TODO
        # for at in nsr_backbone_atoms:
        #     print(at.GetName())
        # with oechem.oemolostream("nsr_caps.oeb") as ofs:
        #     oechem.OEWriteConstMolecule(ofs, oe_nsr_caps)

        # Generate NSR Parametrization
        pmd = ParamMolStructure(
            oe_nsr_caps, openff, prefix_name=nsr_name, recharge=True
        )

        nsr_pmd = pmd.parameterize()

        # Parmed and OpenEye Residue atoms sync
        pmd_atoms = []
        oe_atoms = []

        for res in nsr_pmd.residues:
            if res.name == reference_residue_name:
                res.name = nsr_name
            for at in res.atoms:
                pmd_atoms.append(at)

        # for res in nsr_pmd.residues:
        #     print(res.name)
        #     for at in res.atoms:
        #         print("{} {}".format(at.name, at.charge))

        for oe_res in oechem.OEGetResidues(oe_nsr_caps):
            # print(oe_res.GetName(), oe_res.GetResidueNumber(), oe_res.GetChainID())
            for oe_at in oechem.OEGetResidueAtoms(
                oe_nsr_caps,
                oe_res,
                oechem.OEAssumption_ResPerceived + oechem.OEAssumption_PDBOrder,
            ):
                oe_atoms.append(oe_at)
                # print("\t", oe_at.GetName())

        if len(oe_atoms) != len(pmd_atoms):
            raise ValueError(
                "Parmed and OpenEye topology number of atoms mismatch: {} vs {}".format(
                    len(pmd_atoms), len(oe_atoms)
                )
            )

        # Protein Reference Template atom types
        protein_ff_template = omm_forcefield._templates[reference_residue_name]
        protein_ff_backbone_atype = dict()
        protein_ff_backbone_parameters = dict()

        for at in protein_ff_template.atoms:
            protein_ff_backbone_atype[at.name] = at.type
            protein_ff_backbone_parameters[at.name] = at.parameters
            # print(at.name, at.type, at.parameters)

        # Charges can be present in the Non Bonded Section and not in the loaded Residue Template
        charge_from_non_bonded = False
        for d in protein_ff_backbone_parameters.values():
            if "charge" not in d:
                charge_from_non_bonded = True
                break

        if charge_from_non_bonded:
            non_bonded_gen = None
            for gen in omm_forcefield._forces:
                if isinstance(gen, NonbondedGenerator):
                    non_bonded_gen = gen
                    break
            if non_bonded_gen:
                for at_name, at_type in protein_ff_backbone_atype.items():
                    protein_ff_backbone_parameters[
                        at_name
                    ] = non_bonded_gen.params.paramsForType[at_type]
            else:
                raise ValueError(
                    "Cannot Find the Non Bonded Generator for the selected Force Field"
                )

        # Atom Types Assignment
        new_atom_type_dic = dict()
        C_ACE_N_NME_type_dic = dict()
        count = 0

        nsr_partial_charge = 0.0
        for oe_at, pmd_at in zip(oe_atoms, pmd_atoms):

            if oe_at.GetAtomicNum() != pmd_at.atomic_number:
                raise ValueError(
                    "OE and Parmed atomic number mismatch: {} vs {}".format(
                        oe_at.GetAtomicNum(), pmd_at.atomic_number
                    )
                )

            if oe_at in nsr_side_chain_atoms:

                if pmd_at.type not in new_atom_type_dic:
                    type = nsr_name + "_" + oe_at.GetName() + "_" + str(count)
                    atom_type = parmed.parameters.AtomType(
                        type, count, pmd_at.mass, pmd_at.atomic_number
                    )
                    atom_type.set_lj_params(
                        pmd_at.epsilon, pmd_at.rmin, pmd_at.epsilon_14, pmd_at.rmin_14
                    )
                    new_atom_type_dic[pmd_at.type] = atom_type
                    count += 1

                pmd_at.atom_type = new_atom_type_dic[pmd_at.type]
                pmd_at.type = new_atom_type_dic[pmd_at.type].name
                oe_at.SetType(pmd_at.type)
                oe_at.SetPartialCharge(pmd_at.charge)
                nsr_partial_charge += oe_at.GetPartialCharge()

                # Identity CB
                if [nbr for nbr in oe_at.GetAtoms(oechem.OEIsCAlpha())]:
                    CBeta_side_chain.append(oe_at)

            elif oe_at in nsr_backbone_atoms:
                if oe_at.GetAtomicNum() == oechem.OEElemNo_N:
                    type = protein_ff_backbone_atype["N"]
                    params = protein_ff_backbone_parameters["N"]
                elif oe_at.GetAtomicNum() == oechem.OEElemNo_C:
                    if [nbr for nbr in oe_at.GetAtoms(oechem.OEIsOxygen())]:
                        type = protein_ff_backbone_atype["C"]
                        params = protein_ff_backbone_parameters["C"]
                    else:
                        type = protein_ff_backbone_atype["CA"]
                        params = protein_ff_backbone_parameters["CA"]

                elif oe_at.GetAtomicNum() == oechem.OEElemNo_O:
                    type = protein_ff_backbone_atype["O"]
                    params = protein_ff_backbone_parameters["O"]
                else:  # Hydrogen
                    if [nbr for nbr in oe_at.GetAtoms(oechem.OEIsNitrogen())]:
                        if isNTerminus:
                            type = protein_ff_backbone_atype["H1"]
                            params = protein_ff_backbone_parameters["H1"]
                        else:
                            type = protein_ff_backbone_atype["H"]
                            params = protein_ff_backbone_parameters["H"]
                    else:
                        type = protein_ff_backbone_atype["HA"]
                        params = protein_ff_backbone_parameters["HA"]

                type += "_Backbone"
                atom_type = parmed.parameters.AtomType(
                    type, count, pmd_at.mass, pmd_at.atomic_number
                )
                atom_type.set_lj_params(
                    pmd_at.epsilon, pmd_at.rmin, pmd_at.epsilon_14, pmd_at.rmin_14
                )

                if type == protein_ff_backbone_atype["C"] + "_Backbone":
                    C_ACE_N_NME_type_dic["C"] = atom_type
                if type == protein_ff_backbone_atype["N"] + "_Backbone":
                    C_ACE_N_NME_type_dic["N"] = atom_type

                pmd_at.atom_type = atom_type
                pmd_at.type = type
                oe_at.SetType(pmd_at.type)
                oe_at.SetPartialCharge(params["charge"])
                nsr_partial_charge += oe_at.GetPartialCharge()

        # Fix Atom types C in ACE and N in NME and Set new Charge for CB side Chain
        for oe_at, pmd_at in zip(oe_atoms, pmd_atoms):

            if oe_at in C_ACE_or_N_NME_atoms:
                if oe_at.GetAtomicNum() == oechem.OEElemNo_N:
                    type = protein_ff_backbone_atype["N"]
                    params = protein_ff_backbone_parameters["N"]
                    atom_type = C_ACE_N_NME_type_dic["N"]
                else:
                    type = protein_ff_backbone_atype["C"]
                    params = protein_ff_backbone_parameters["C"]
                    atom_type = C_ACE_N_NME_type_dic["C"]

                pmd_at.atom_type = atom_type
                pmd_at.type = type
                oe_at.SetType(pmd_at.type)
                oe_at.SetPartialCharge(params["charge"])

            # Fix CB charge
            if oe_at in CBeta_side_chain:

                # Excess charge in proton units
                excess_charge = nsr_formal_charge - nsr_partial_charge

                if abs(excess_charge) > 0.2:
                    raise ValueError(
                        "{} non-standard residue CB excess charge correction too large {}".format(
                            nsr_name, excess_charge
                        )
                    )

                new_cb_charge = oe_at.GetPartialCharge() + excess_charge
                oe_at.SetPartialCharge(new_cb_charge)
                pmd_at.charge = new_cb_charge

        residue_atoms = nsr_backbone_atoms + nsr_side_chain_atoms

        # TODO
        # for at in residue_atoms:
        #     print(">>>>>>>>>>", at.GetName())
        #

        # Check partial charge:
        partial_charge_check = 0.0
        for oe_at in residue_atoms:
            partial_charge_check += oe_at.GetPartialCharge()

        if abs(nsr_formal_charge - partial_charge_check) > 0.01:
            raise ValueError(
                "{} non-standard residue partial charge and formal charge mismatch: {} vs {}".format(
                    nsr_name, nsr_formal_charge, partial_charge_check
                )
            )

        # Generate the Parmed NSR Capped parameters to be used with OpenMM
        params = parmed.openmm.parameters.OpenMMParameterSet.from_structure(nsr_pmd)

        # Convert the Parameters in a XML format
        ffxml = StringIO()
        params.write(ffxml)
        ffxml_contents = ffxml.getvalue()

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(ffxml_contents, parser=parser)

        # New Sections
        residues_xml = etree.SubElement(root, "Residues")
        residue_xml = etree.SubElement(residues_xml, "Residue", name=nsr_name)

        # XML Atom Section
        for oe_at, pmd_at in zip(oe_atoms, pmd_atoms):
            if oe_at in residue_atoms:
                atom_xml = etree.SubElement(
                    residue_xml,
                    "Atom",
                    name=oe_at.GetName(),
                    type=oe_at.GetType(),
                    charge=str(oe_at.GetPartialCharge()),
                )

        # XML Bond Section
        for bond in oe_nsr_caps.GetBonds():
            if (bond.GetBgn() in residue_atoms) and (bond.GetEnd() in residue_atoms):
                bond_xml = etree.SubElement(
                    residue_xml,
                    "Bond",
                    atomName1=bond.GetBgn().GetName(),
                    atomName2=bond.GetEnd().GetName(),
                )
            elif (bond.GetBgn() in residue_atoms) and (
                bond.GetEnd() not in residue_atoms
            ):
                bond_xml = etree.SubElement(
                    residue_xml, "ExternalBond", atomName=bond.GetBgn().GetName()
                )

            elif (bond.GetBgn() not in residue_atoms) and (
                bond.GetEnd() in residue_atoms
            ):
                bond_xml = etree.SubElement(
                    residue_xml, "ExternalBond", atomName=bond.GetEnd().GetName()
                )

        # XML Cleaning

        new_atom_type_names = [oe_at.GetType() for oe_at in nsr_side_chain_atoms]

        # Removing unwanted Capping Atom Types
        for element in root.xpath("/ForceField/AtomTypes/Type"):
            xml_type = element.get("name")
            if xml_type not in new_atom_type_names:
                element.getparent().remove(element)

        # Removing Bond forces not involving new atom types
        for element in root.xpath("/ForceField/HarmonicBondForce/Bond"):
            type1 = element.get("type1")
            type2 = element.get("type2")

            if (type1 in new_atom_type_names) or (type2 in new_atom_type_names):
                element.set("type1", type1.replace("_Backbone", ""))
                element.set("type2", type2.replace("_Backbone", ""))
                continue
            else:
                element.getparent().remove(element)

        # Removing Angle forces not involving new atom types
        for element in root.xpath("/ForceField/HarmonicAngleForce/Angle"):

            type1 = element.get("type1")
            type2 = element.get("type2")
            type3 = element.get("type3")

            if (
                (type1 in new_atom_type_names)
                or (type2 in new_atom_type_names)
                or (type3 in new_atom_type_names)
            ):
                element.set("type1", type1.replace("_Backbone", ""))
                element.set("type2", type2.replace("_Backbone", ""))
                element.set("type3", type3.replace("_Backbone", ""))
                continue
            else:
                element.getparent().remove(element)

        # Removing Proper Dihedral forces not involving new atom types
        for element in root.xpath("/ForceField/PeriodicTorsionForce/Proper"):
            type1 = element.get("type1")
            type2 = element.get("type2")
            type3 = element.get("type3")
            type4 = element.get("type4")

            if (
                (type1 in new_atom_type_names)
                or (type2 in new_atom_type_names)
                or (type3 in new_atom_type_names)
                or (type4 in new_atom_type_names)
            ):
                element.set("type1", type1.replace("_Backbone", ""))
                element.set("type2", type2.replace("_Backbone", ""))
                element.set("type3", type3.replace("_Backbone", ""))
                element.set("type4", type4.replace("_Backbone", ""))
                continue
            else:
                element.getparent().remove(element)

        # Removing Improper Dihedral forces not involving new atom types
        for element in root.xpath("/ForceField/PeriodicTorsionForce/Improper"):
            type1 = element.get("type1")
            type2 = element.get("type2")
            type3 = element.get("type3")
            type4 = element.get("type4")

            if (
                type1 in new_atom_type_names
                or type2 in new_atom_type_names
                or type3 in new_atom_type_names
                or type4 in new_atom_type_names
            ):
                element.set("type1", type1.replace("_Backbone", ""))
                element.set("type2", type2.replace("_Backbone", ""))
                element.set("type3", type3.replace("_Backbone", ""))
                element.set("type4", type4.replace("_Backbone", ""))
                continue
            else:
                element.getparent().remove(element)

        # Removing Non-Bonded forces not involving new atom types
        for element in root.xpath("/ForceField/NonbondedForce/Atom"):
            xml_type = element.get("type")
            if xml_type not in new_atom_type_names:
                element.getparent().remove(element)

        # Changing 14-Scaling Parameters
        for element in root.xpath("/ForceField/NonbondedForce"):
            element.set("coulomb14scale", "0.8333333333333334")
            element.set("lj14scale", "0.5")

        # Cleaning the Residue Section
        for element in root.xpath("/ForceField/Residues/Residue/Atom"):
            xml_name = element.get("name")
            xml_type = element.get("type")
            element.set("name", xml_name.replace("_Backbone", ""))
            element.set("type", xml_type.replace("_Backbone", ""))

        for element in root.xpath("/ForceField/Residues/Residue/Bond"):
            atomName1 = element.get("atomName1")
            atomName2 = element.get("atomName2")
            element.set("atomName1", atomName1.replace("_Backbone", ""))
            element.set("atomName2", atomName2.replace("_Backbone", ""))

        for element in root.xpath("/ForceField/Residues/Residue/ExternalBond"):
            atomName = element.get("atomName")
            element.set("atomName", atomName.replace("_Backbone", ""))

        ffxml_contents = etree.tostring(
            root, pretty_print=True, encoding="utf-8"
        ).decode()

        # with open(nsr_name+".xml", 'w') as f:
        #     f.write(ffxml_contents)

        ffmxl_template_list.append(ffxml_contents)

    return ffmxl_template_list
