# -*- coding: utf-8 -*-

import numpy as np

class Dispatch_Eval():
    '''
    Provides methods for the power dispatch evaluation and gaters necessary data for the plots
    Methods
    -------
    calculate
    
    state_of_charge_evaluation
    technical_objectives
    days_with_cut_offs
    '''
    
    def __init__(self, simulation, opt_model, timestep, optimization):
        '''
        Parameters
        ----------
        simulation : class. Main simulation class
        timestep: int. Simulation timestep in seconds
        '''        
        self.sim = simulation
        self.opt_model = opt_model
        self.timestep = timestep
        self.optimization = optimization
        self.runtime = list()
        

    def get_daily_power_mix(self, month,year):    
        '''
        Calculates the average daily power flows and saves them in a dictionary 
        
        Parameters
        ----------
        power_mix : dict
            dictionary containing the average daily power flows
        None
        '''
        order_of_magnitude = 10**3
        step = int((self.sim.timestep/3600))
        self.month = month
        self.year = year
        month_day = [0,31,59,90,120,151,181,212,243,273,304,334,365]
        month_hour_start = (self.year-1)*(365*24) #+ month_day[self.month-1]*24 
        month_hour_end =(self.year)*365*24 -1 #+ month_day[self.month]*24 -1
        
        # self.day_hours = list(range(0,24, step))
        self.day_hours = np.arange(0,24,1)
        self.load_power = list()
        battery_power =list()
        pv_power = list()
        grid_bought_power = list()
        grid_sold_power = list()
        power_label = list()
        self.mean_SOC = list()
        
        self.discharged_power = self.sim.battery_power.copy()
        j=0
        for i in self.discharged_power:
            if i > 0 :
                self.discharged_power[j]=0
            j+=1
                
        
        power_values = list()
        self.mstd =[[],[],[]]
        self.power_mix = dict()
        if self.opt_model:
            for i in self.day_hours:
                #load power
                self.load_power.append(np.mean(self.sim.load_power_demand[i+month_hour_start:month_hour_end:24].copy())/order_of_magnitude)
                
                #battery discharge power                
                if self.sim.battery is not None:
                    battery_power.append(np.mean(self.discharged_power[i+month_hour_start:month_hour_end:24].copy())*(-1)/order_of_magnitude)
                    self.mstd[0].append(np.std(self.discharged_power[i+month_hour_start:month_hour_end:24].copy())/order_of_magnitude)

                if self.sim.pv is not None:
                    pv_power.append(np.mean(self.sim.pv_charger_power[i+month_hour_start:month_hour_end:24].copy())/order_of_magnitude)
                    self.mstd[1].append(np.std(self.sim.pv_charger_power[i+month_hour_start:month_hour_end:24].copy())/order_of_magnitude)

                if self.sim.grid_connected:
                    grid_bought_power.append(np.mean(self.opt_model.bought_power_list[i+month_hour_start:month_hour_end:24].copy())/order_of_magnitude)
                    self.mstd[2].append(np.std(self.opt_model.bought_power_list[i+month_hour_start:month_hour_end:24].copy())/order_of_magnitude)
                    grid_sold_power.append(np.mean(self.opt_model.sold_power_list[i+month_hour_start:month_hour_end:24].copy())/order_of_magnitude)
                
                self.mean_SOC.append(np.mean(self.sim.battery_state_of_charge[i+month_hour_start:month_hour_end:24].copy())) 

            if self.sim.battery is not None:
                power_label.append('battery power')
                power_values.append(battery_power)
            if self.sim.pv is not None:
                power_label.append('PV')
                power_values.append(pv_power)
            if self.sim.grid_connected:
                power_label.append('grid bought power')
                power_values.append(grid_bought_power)
                # power_label.extend(['grid bought power', 'grid sold power'])
                # power_values.extend([grid_bought_power, grid_sold_power])
        else:
            return
            
        j=0
        for i in power_label:
            self.power_mix[i] = power_values[j]
            j+=1