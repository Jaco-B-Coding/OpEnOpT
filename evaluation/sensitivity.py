import random
import pandas as pd

class Sensitivity_analysis():
    """Relevant methods for a sensitivity analysis of the optiization model.

    Parameters
    ----------
    ranomization_method: int. selection of randomization method
                            1:random distribution within a set range
                            2:gaussian distribution

    Note
    ----
    """


    def __init__(self, simulation, optimization, randomize_method):
        
        self.sim = simulation
        self.opt = optimization
        self.randomization_method = randomize_method
        
        self.iteration = 0
        
        self.load_path = 'data/Sens/sens_data.csv'
        self.sens_data = pd.read_csv(self.load_path)  
        
        self.opt_obj = list()
        self.pv_peak = list()
        self.batt_capa = list()
        self.load = list()
        self.total_load = list()
        
        self.pv_current_power = list()
        self.pv_used_power = list()
        self.pv_investment_costs = list()
        self.pv_tot_used_energy = list()
        
        self.battery_investment_costs = list()
        self.battery_SOC = list()
        self.battery_power = list()
        

    def generate_random_sample(self, sample_input, max_deviation, standard_deviation = None):
        """takes in the input variable to be varied according to the randomization method selected

        Parameters
        ----------
        None : `None`

        Returns
        random sample of sample_input
        -------
        """
    
        if self.randomization_method == 1:
            return self.calc_random_distribution(sample_input, max_deviation)
        elif self.randomization_method == 2:
            return self.calc_gaussian_distribution(sample_input, standard_deviation)
        elif self.randomization_method == 3:
            return self.load_data
        
    
    def load_data(self, var_name):
        
        expr = self.sens_data[var_name].to_numpy()[self.iteration]
        print(expr)
        
        self.iteration += 1
        
        return expr
        
    def calc_random_distribution(self, sample_input, max_deviation):
        """gives back random value form a random distribution of input variable

        Parameters
        ----------
        None : `None`

        Returns
        random sample of sample_input
        -------
        """
        if type(sample_input) in (float, int):
            lower_bound = sample_input* (1-max_deviation)
            upper_bound = sample_input* (1+max_deviation)            
            random_sample = random.uniform(lower_bound, upper_bound)   
            
        elif isinstance(sample_input, list):
            random_sample = list()
            for i in range(len(sample_input)): 
                lower_bound = sample_input[i]* (1-max_deviation)
                upper_bound = sample_input[i]* (1+max_deviation)
                expr = random.uniform(lower_bound, upper_bound)   
                random_sample.append(expr)
                
        else:
            print('sens class: wrong type of sample input passed')
        return random_sample
        
    def calc_gaussian_distribution(self, sample_input, standard_deviation):
        """gives back random value form a gaussian distribution of input variable

        Parameters
        ----------
        None : `None`

        Returns
        random sample of sample_input
        -------
        """  
        if type(sample_input) in (float, int):
            random_sample = random.gauss(sample_input, standard_deviation)
            
        elif isinstance(sample_input, list):
            random_sample = list()
            for i in range(len(sample_input)): 
                expr = random.gauss(sample_input[i], standard_deviation)   
                random_sample.append(expr)
                
        else:
            print('sens class: wrong type of sample input passed')
        
        return random_sample

    def save_sim_data(self,simulation, optimization):
        """saves simulation data after each iteration of simulation model and optimization with varied input variables

        Parameters
        ----------
        None : `None`

        Returns
        -------
        """
        self.sim = simulation
        self.opt = optimization
        
        self.opt_obj.append(self.opt.total_costs_new)        
        self.pv_peak.append(self.sim.pv_tot_peak)
        self.batt_capa.append(self.sim.battery_capacity)
        
        # self.load.append(self.sim.load_power_demand)
        self.total_load.append(sum(self.sim.load_power_demand))
        
        # self.pv_current_power.append(self.sim.pv_peak_power_current)
        # self.pv_used_power.append(self.sim.pv_power) 
        
        pv_tot_power = 0
        for i in range(len(self.sim.pv)):
            self.pv_investment_costs.append(self.sim.pv[i].investment_costs_specific)
            
            #pv total power        
            pv_tot_power+= sum(self.sim.pv_power[i][j] for j in range(len(self.sim.pv_power[i])))
        
        self.pv_tot_used_energy.append(pv_tot_power)
        
        self.battery_investment_costs.append(self.sim.battery.investment_costs_specific)
        # self.battery_SOC.append(self.sim.battery_state_of_charge)
        # self.battery_power.append(self.sim.battery_power)                                  
                                  