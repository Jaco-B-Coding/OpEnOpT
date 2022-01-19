# OpEnOpT
Open-source Energy-grid Optimisation Tool

The Open Energy-grid Optimisation Tool (OpEnOpT) is a program to aid in the planning and analysis of energy power systems. It aims to increase an energy system's economic feasibility by optimizing the system's dispatch schedule and, if needed, the power component sizes using a Non-Linear Problem (NLP) approach. 
It currently has the means to model a photovoltaics (PV) integrated Battery Energy Storage System (BESS) as well as a power grid, which can be used to purchase and sell electricity. It further includes models for a PV-charger component and the battery management system.

The oiptimization objective is comprised of a cost minimisation approach, where the systems total costs over the simulated time frame, based on a calculation of the PV-BESS levelized costs of electricity, have to be kept to a minimum.  

As for the optimization environment, the software package Pyomo was used. It is a Python-based open-source software package that supports a diverse set of optimization capabilities for formulating, solving, and analyzing optimization models.

## Installation
To install OpEnOpT download the code directly. Additional packages that need to be installed are Pyomo and others relating to the chosen optimization solver.

To install Pyomo, refer to the Pyomo installation guide: https://pyomo.readthedocs.io/en/stable/installation.html

For best results and lower optimization run-times the installation of additional solvers is advised. Since OpEnOpT is based on a NLP, all NLP-solvers that are compatible with Pyomo can be used. For a list of possible solvers the following command can be used in the terminal: 
> pyomo help -s
or refer to the Pyomo manual: https://pyomo.readthedocs.io/en/stable/solving_pyomo_models.html?highlight=solvers
However, program testing was conducted using the following solvers:
- *Ipopt (Interior Point Optimizer)*: An open source software package for large-scale nonlinear optimization. 
- *MPEC_NLP*: a meta-solver included within the installation of Pyomo. 


#### Ipopt
Ipopt is to be installed separately according to:
https://coin-or.github.io/Ipopt/INSTALL.html

It comes with the free MUMPS solver which can be used directly in OpEnOpT to solve models. However, it is advisable to install further more efficient sub-solvers such as MA27, MA57 or MA86 as these provide faster results and are generally more stable.
The installation of the sub-solvers needs to happen separately and is more straightforward whithin a Linux-environment. These need to be downloaded from HSL (Harwell Subroutines Library):
https://www.hsl.rl.ac.uk/catalogue/
Older packages, such as the MA27 sub-solver are freely available. The more powerfull MA57 solver as well as the MA86 require an academic license which is obtainable through an application form.

Further additional packages, such as LAPACk and BLAS may also be necessary. Additional information can be found in the Ipopt installation documentation.
