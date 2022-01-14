import numpy as np

class Economics():
    '''
    Provides all relevant methods for the Levelized Costs of Energy calculation
    according to method cited in:
        T. Khatib, I. A. Ibrahim, and A. Mohamed, 
        ‘A review on sizing methodologies of photovoltaic array and storage battery in a standalone photovoltaic system’, 
        Energy Convers. Manag., vol. 120, pp. 430–448, Jul. 2016.
    
    Methods
    -------
    calculate
    
    capital_recovery_factor
    constant_escalation_levelisation_factor
    annuity_investment_costs
    annuity_operation_maintenance_costs
    annuity_replacement_costs
    annuity_residual_value
    annuity_total_levelized_costs
    '''
    
    def __init__(self, component, component_replacement, component_energy, timestep, sim_duration):
        '''
        Parameters
        ----------
        component : class. simulated component class
        component_replacement : list. List with timeindex of component replacement
            timeindex is dependent on set timestep
        timestep: int. Simulation timestep in seconds
        ''' 
        # Timestep of simulation [s]
        self.timestep = timestep
        self.sim_duration = sim_duration
        ## Component specific parameter
        self.component = component     
        self.component_replacement = np.trim_zeros(component_replacement) 
        self.component_energy = component_energy
        self.operation_maintenance_costs_specific = 0.0 * self.component.investment_costs_specific 
        
        ## Main economic parameter
        # [a] Timeframe of annuity calculation
        self.timeframe = 30
        # [-] Anual percentage rate/effektiver Jahreszins
        self.apr= 0.0588
        # [-] Nominal price escalation rate
        self.ry = 0.03
        # [-] Nominal price advance of OMC costs /nominale Preissteigerung
        self.romy = 0.


    def calculate(self):
        '''
        Parameter
        ---------
        None
        '''
        # calculate economic parameter
        self.calc_capital_recovery_factor()
        self.calc_constant_escalation_levelisation_factor()                        
                     
        # Calculation of all LCoE components
        self.calc_annuity_investment_costs()
        self.calc_annuity_operation_maintenance_costs()
        self.calc_annuity_replacement_costs()
        self.calc_annuity_residual_value()
        
        self.calc_annuity_total_levelized_costs()
        self.calc_levelized_costs()


    def calc_capital_recovery_factor(self):
        '''
        Capital recovery factor
        
        Parameter
        ---------
        None
        '''
        self.capital_recovery_factor = (self.apr* (1 + self.apr)**self.timeframe) \
                                       / (((1 + self.apr)**self.timeframe)-1)

    
    def calc_constant_escalation_levelisation_factor(self):
        '''
        Constant Escalation Levelisation Factor - CELF (Nivelierungsfaktor)
        
        Parameter
        ---------
        None
        '''
        k = (1 + self.ry) / (1 + self.apr)
        self.constant_escalation_levelisation_factor = (k*(1-k**self.timeframe)) \
                                                       / (1-k) * self.capital_recovery_factor

    
    def calc_annuity_investment_costs(self):
        '''
        Annuity calculation of Investment Costs
        
        Parameter
        ---------
        None
        '''
        self.annuity_investment_factor = self.capital_recovery_factor * self.component.investment_costs_specific
        self.annuity_investment_costs =  self.annuity_investment_factor *  self.component.size_nominal

    
    def calc_annuity_operation_maintenance_costs(self):
        '''
        Annuity calculation of Operation and Maintenance Costs
        
        Parameter
        ---------
        None
        '''
        self.annuity_operation_maintenanance_factor = self.capital_recovery_factor * self.operation_maintenance_costs_specific
        self.annuity_operation_maintenance_costs = self.annuity_operation_maintenanance_factor *  self.component.size_nominal
        
    def calc_annuity_replacement_costs(self):
        '''
        Annuity calculation of Replacement Costs
        
        Parameter
        ---------
        None
        '''  
        # Define emtpty array for calculatiom of each replacement
        rc = np.zeros(len(self.component_replacement))
        # Cost calc for every replacement
        for k in range(0,len(self.component_replacement)):
            # Cost of each replacement with escalation rate r
            cc = (self.component.investment_costs_specific \
                  * (1+self.ry)**(self.component_replacement[k] / (365*24*(3600/self.timestep))))
            # Present value of replacement cost
            rc[k] = cc / (1+self.apr)**(self.component_replacement[k]/(24*365*(3600/self.timestep)))
        # Annuity of present value
        self.annuity_replacement_factor = self.capital_recovery_factor * sum(rc)
        self.annuity_replacement_costs = self.annuity_replacement_factor  * self.component.size_nominal 

    
    def calc_annuity_residual_value(self):
        '''
        Annuity calculation of Residual value
        
        Parameter
        ---------
        None
        '''  
        self.annuity_residual_value_factor = ((1 - self.component.state_of_destruction) \
                                      * self.component.investment_costs_specific) \
                                      / ((1+self.apr)**self.timeframe) * self.capital_recovery_factor
        self.annuity_residual_value = self.annuity_residual_value_factor  * self.component.size_nominal

    
    def calc_annuity_total_levelized_costs(self):
        '''
        Annuity calculation of Total levelized costs
        
        Parameter
        ---------
        None
        '''  
        self.annuity_total_levelized_costs = self.annuity_investment_costs + self.annuity_operation_maintenance_costs \
                                        + self.annuity_replacement_costs - self.annuity_residual_value

    
    def calc_levelized_costs(self):
        '''
        Calculate technology LCOE [€/kWh] based on the power provided and provide technology cost factor 
        to be used in Pyomo model for LCOE calculation'
        '''
        self.total_LCOE_factor = (self.annuity_investment_factor + self.annuity_operation_maintenanance_factor\
                + self.annuity_replacement_factor - self.annuity_residual_value_factor)
        
        self.levelized_costs = self.annuity_total_levelized_costs*self.component.size_nominal/self.component_energy