import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class Performance():
    '''
    Provides all relevant methods for the technical evaluation
    according to own methods and methods cited in:
        T. Khatib, I. A. Ibrahim, and A. Mohamed, 
        ‘A review on sizing methodologies of photovoltaic array and storage battery in a standalone photovoltaic system’, 
        Energy Convers. Manag., vol. 120, pp. 430–448, Jul. 2016.
    
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

    def calculate(self):        
        '''
        Parameters
        ----------
        None
        '''         
        self.state_of_charge_evaluation()
        self.technical_objectives()
        self.days_with_cut_offs()


    def state_of_charge_evaluation(self):
        '''
        Calculate Battery State of Charge at specific daytime
        
        Parameters
        ----------
        None
        '''   
        # Maximum & Minimum battery SoC every day
        self.state_of_charge_dayarray = np.array_split(self.sim.battery_state_of_charge, 
                                                  int((len(self.sim.battery_state_of_charge))/(24*(3600/self.timestep))))
        #Find max/min values of each day array
        self.state_of_charge_day_max  = list()
        self.state_of_charge_day_min  = list()

        for i in range(0,len(self.state_of_charge_dayarray)):
            self.state_of_charge_day_max.append(max(self.state_of_charge_dayarray[i][:]))
            self.state_of_charge_day_min.append(min(self.state_of_charge_dayarray[i][:]))


    def technical_objectives(self):
        '''
        Determines different technical objective evaluation parameters 
        Calculates:
            Loss of Power supply (LPS)
            Power of load supplied
            Power of PV which is unused
            Loss of Load Probability
            Level of Autonomy
            
        Parameters
        ----------
        None
        '''
        self.loss_of_power_supply = list()
        self.power_load_supplied = list()
        self.tot_power_bought = list()
        self.tot_power_sold = list()
        self.power_pv_unused = list()
        self.level_of_autonomy_list = list()
        
        #if model optimization active and already initialized
        if self.optimization and self.opt_model.power_shortage_list:
            ## Calculation of loss of power supply and pv energy not used
            for i in range(0,len(self.sim.power_junction_power)):
                
                self.loss_of_power_supply.append(self.opt_model.power_shortage_list[i])
                self.power_pv_unused.append(self.opt_model.pv_power_unused[i])
                    
                # Determination of level of autonomy
                # Case loss of power supply - LA == 1
                if self.loss_of_power_supply[i] > 0.0001:
                    self.level_of_autonomy_list.append(1)  
                # Case no loss of power supply - LA == 0
                else:
                    self.level_of_autonomy_list.append(0)  
            
            
            # Loss of Load Probability
            self.loss_of_load_probability = sum(self.loss_of_power_supply) / sum(self.sim.load_power_demand)
    
            # PV energy not used per day
            self.energy_pv_unused_day = sum(self.power_pv_unused) \
                                    / (len(self.power_pv_unused) / (24*(3600/self.timestep)))
            
            #power bought
            if self.sim.grid_connected:
                self.tot_power_bought = sum(self.sim.load_power_demand) - sum(self.sim.pv_charger_power) - self.energy_pv_unused_day
            
            # Level of autonomy
            self.level_of_autonomy = 1 - (sum(self.level_of_autonomy_list)/np.count_nonzero(self.sim.load_power_demand)) 
        else:
            ## Calculation of loss of power supply and pv energy not used
            for i in range(0,len(self.sim.power_junction_power)):
                
                # Battery discharge case
                if self.sim.power_junction_power[i] < 0: 
                    self.loss_of_power_supply.append(abs(self.sim.power_junction_power[i] \
                                                     - self.sim.battery_management_power[i] * self.sim.battery_management_discharger_efficiency[i]))
                    self.power_pv_unused.append(0)
                    
                # Battery charge case
                elif self.sim.power_junction_power[i] > 0:
                    self.loss_of_power_supply.append(0)
                    # Check if bms efficeincy is > 0
                    if self.sim.battery_management_charger_efficiency[i] > 0:
                        self.power_pv_unused.append(abs(self.sim.power_junction_power[i] \
                                                    - self.sim.battery_management_power[i] / self.sim.battery_management_charger_efficiency[i]))
                    else:
                        self.power_pv_unused.append(abs(self.sim.power_junction_power[i]))
                
                # Idle case       
                else:
                    self.loss_of_power_supply.append(0)
                    self.power_pv_unused.append(0)
    
                # Determination of level of autonomy
                # Case loss of power supply - LA == 1
                if self.loss_of_power_supply[i] > 0.0001:
                    self.level_of_autonomy_list.append(1)  
                # Case no loss of power supply - LA == 0
                else:
                    self.level_of_autonomy_list.append(0)  
                    
            # Loss of Load Probability
            self.loss_of_load_probability = sum(self.loss_of_power_supply) / sum(self.sim.load_power_demand)
    
            # PV energy not used per day
            self.energy_pv_unused_day = sum(self.power_pv_unused) \
                                    / (len(self.power_pv_unused) / (24*(3600/self.timestep)))
    
            # Level of autonomy
            self.level_of_autonomy = 1 - (sum(self.level_of_autonomy_list)/np.count_nonzero(self.sim.load_power_demand)) 


    def days_with_cut_offs(self):
        '''
        Calculates Number of days with power cut offs
        
        Parameters
        ----------
        None
        '''
        # Day arrays of power cut offs
        self.cut_off_day = np.array(np.split(np.array(self.level_of_autonomy_list), 
                                             (len(self.level_of_autonomy_list)/(24*(3600/self.timestep)))
                                             ))

        # Number and percentage of days with cut offs
        self.cut_off_day_list = list()
        for i in range(0,len(self.cut_off_day)):
            self.cut_off_day_list.append(max(self.cut_off_day[i,:]))

        self.cut_off_day_number = sum(self.cut_off_day_list) \
                                  / ((self.sim.simulation_steps*(self.timestep/3600))/8760)
        self.cut_off_day_percentage = sum(self.cut_off_day_list) / len(self.cut_off_day_list)

        # Daily distribution of cut offs
        self.cut_off_day_distribution_daily = list()
        for i in range(0,24):
            if sum(self.cut_off_day[:,i]) == 0:
                self.cut_off_day_distribution_daily.append(0)
            else:
                self.cut_off_day_distribution_daily.append((self.cut_off_day[:,i]) / sum(self.cut_off_day[:,i]))


    def avg_daily_power_mix(self, month,year):    
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
    
    def figure_format(self):
        MEDIUM_SIZE = 10
        BIGGER_SIZE = 12
        plt.rc('font', size=MEDIUM_SIZE)          # controls default text sizes
        plt.rc('axes', titlesize=BIGGER_SIZE)     # fontsize of the axes title
        plt.rc('axes', labelsize=BIGGER_SIZE)    # fontsize of the x and y labels
        plt.rc('xtick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
        plt.rc('ytick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
        plt.rc('legend', fontsize=MEDIUM_SIZE)    # legend fontsize
        plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
        self.figsize = (5,3)


    def plot_loss_of_power_supply(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.loss_of_power_supply, '-b', label='loss _of_power_supply')
        plt.xlabel('Time [date]')
        plt.ylabel('Loss of Power Supply [Wh]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()
        plt.show()


    def plot_soc_days(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        #Carpet plot
        plt.title('Battery state of Charge')
        plt.imshow(self.state_of_charge_dayarray, aspect='auto')
        plt.colorbar()
        plt.xlabel('Time of day [h]')
        plt.ylabel('Day of simulation timeframe')
        plt.grid()
        plt.show()
        
    def plot_cut_off_days(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        #Carpet plot
        plt.title('Power Cut offs')
        plt.imshow(self.cut_off_day, aspect='auto')
        plt.colorbar()
        plt.xlabel('Time of day [h]')
        plt.ylabel('Day of simulation timeframe')
        plt.grid()
        plt.show()


    def print_technical_objective_functions(self):
        print('---------------------------------------------------------')
        print('Objective functions - Technical')
        print('---------------------------------------------------------')
        print('Loss of power Supply [Wh]=', round(sum(self.loss_of_power_supply),2))
        print('Loss of load propability [1]=',  round(self.loss_of_load_probability, 4))
        print('level of autonomy [1]=', round(self.level_of_autonomy,4))
        print('No. of days with cut off per year [d/a]=', self.cut_off_day_number)

        print('---------------------------------------------------------')
        print('Components')
        print('---------------------------------------------------------')
        print('PV Energy not used [Wh/day]', round(self.energy_pv_unused_day,2))
        print('SoC mean =', round(np.mean(self.state_of_charge_dayarray),2))

    def get_runtime(self, time):
        
        self.runtime.append(time)