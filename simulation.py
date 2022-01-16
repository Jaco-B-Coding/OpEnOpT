import sys # Define the absolute path for loading other modules
sys.path.insert(0,'../..')

import pvlib
from datetime import datetime

from simulatable import Simulatable
from environment import Environment
from components.load import Load
from components.market import Market
from components.photovoltaic import Photovoltaic
from components.power_component import Power_Component
from components.power_junction import Power_Junction
from components.battery import Battery

class Simulation(Simulatable):
    '''
    Central Simulation class, where energy system is constructed
    Extractable system power flows are defined here
    
    Attributes
    ----------
    Simulatable : class. In order to simulate system
    
    Methods
    -------
    simulate
    '''    
    
    def __init__(self,
                 simulation_steps,
                 timestep):
        '''
        Parameters can be defined externally or inside class
        ----------
        pv_peak_power : int. Installed phovoltaic peak power in Watt peak [Wp]
        battery capacity : int. Installed nominal battery capacity in Watthours [Wh]
        pv_orientation : tuble of floats. PV oriantation with:
            1. tuble entry pv azimuth in degrees from north [°] (0°=north, 90°=east, 180°=south, 270°=west).
            2. tuble entry pv inclination in degrees from horizontal [°]
        system_location : tuble of floats. System location coordinates:
            1. tuble entry system longitude in degrees [°]
            2. tuble entry system latitude in degrees [°]
        simulation_steps : int. Number of simulation steps
        timestep: int. Simulation timestep in seconds
        '''
        
        #%% Define simulation settings

        # System specifications
        self.order_of_magnitude = 1000000
        # [Wp] Installed PV power
        self.pv_peak_power = [500000]
        self.pv_peak_power_start = self.pv_peak_power.copy()
        self.max_pv_peak_power = [5000000]
        self.pv_tot_peak = 0 
        for peak_power in self.pv_peak_power:
            self.pv_tot_peak += peak_power
        # [Wp] Installend Wind power
        self.wind_peak_power = 0
        # [Wh] Installed battery capacity
        self.battery_capacity = 900000
        self.battery_capacity_start = self.battery_capacity 
        self.max_battery_capacity = 3000000
        #  PV orientation : tuble of floats. PV oriantation with:
        # 1. pv azimuth in degrees [°] (0°=north, 90°=east, 180°=south, 270°=west). & 2. pv inclination in degrees [°]
        self.pv_orientation = (0,0)
        
        # System location
        # Latitude: Positive north of equator, negative south of equator.
        # Longitude: Positive east of prime meridian, negative west of prime meridian.
        self.system_location = pvlib.location.Location(latitude= 41.965,
                                                       longitude=12.795,
                                                       tz='Europe/Rome',
                                                       altitude=200)

        #for the optimisation model
        #Enable/disable grid connection
        self.grid_connected = False
        self.day_ahead_market = False
        if self.grid_connected or self.day_ahead_market:
            #specify maximal buy and sell amounts
            self.max_buy = 10000000
            self.max_sell = 0
        self.market = Market(day_ahead = self.day_ahead_market)
        
        #shortage power
        self.LCoE_shortrage = 0.01
        self.max_shortage_power = 50000000

        ## Define simulation time parameters     
        # Number of simulation timesteps
        self.simulation_steps = simulation_steps
        # [s] Simulation timestep 
        self.timestep = timestep
        
                
        #%% Initialize classes      
        
        # Environment class                                                         --> to make fct of how many arrays choosen
        self.env = Environment(timestep=self.timestep,
                               system_orientation=self.pv_orientation,
                               system_location=self.system_location)
        
        # load class
        self.load = Load()
        

        # Component classes
        self.pv = list()
        for pv_peak_power in self.pv_peak_power:
            pv_array = Photovoltaic(timestep=self.timestep,
                               peak_power=pv_peak_power,
                               controller_type='mppt',
                               env=self.env,
                               file_path='data/components/photovoltaic_resonix_120Wp.json')
            self.pv.append(pv_array) 
        
        self.pv_power_junction = Power_Junction(input_link_1=self.pv, 
                                             input_link_2=None, 
                                             load= None)
                
        self.pv_charger = Power_Component(timestep=self.timestep,
                                       power_nominal=self.pv_tot_peak, 
                                       input_link=self.pv_power_junction, 
                                       file_path='data/components/power_component_mppt.json')  
        
        self.wind = None
        
        self.power_junction = Power_Junction(input_link_1=self.pv_charger, 
                                             input_link_2=None, 
                                             load=self.load)
        
        self.battery_management = Power_Component(timestep=self.timestep,
                                                  power_nominal=self.pv_tot_peak, 
                                                  input_link=self.power_junction, 
                                                  file_path='data/components/power_component_bms.json')

        self.battery = Battery(timestep=self.timestep,
                               capacity_nominal_wh=self.battery_capacity, 
                               input_link=self.battery_management, 
                               env=self.env,
                               file_path='data/components/battery_lfp.json')
        
       
        ## Initialize Simulatable class and define needs_update initially to True
        self.needs_update = True
        
        Simulatable.__init__(self, self.env,self.load,self.pv, self.pv_power_junction, self.pv_charger,
                             self.power_junction, self.battery_management, self.battery)
        
        # load hourly data
        #Load timeseries irradiation data
        self.env.meteo_irradiation.read_csv(file_name='data/env/irradiation-89c990c4-62ac-11ec-a6f1-bc97e153e1e6.csv',
                                           start=0, 
                                           end=self.simulation_steps)
        #Load weather data
        self.env.meteo_weather.read_csv(file_name='data/env/SoDa_MERRA2_lat41.965_lon12.795_2000-01-01_2020-01-01_790723248.csv', 
                                       start=0, 
                                       end=self.simulation_steps)
        #Load load demand data
        self.load.load_demand.read_csv(file_name='data/load/Load_Data.csv', 
                                      start=0, 
                                      end=8760)
        
        #load day_ahead market data or cost fixed buy and sell costs
        if self.day_ahead_market:
            self.market.load_market_data.read_csv(file_name='data/market/day_ahead_DE.csv',
                                              start=0,
                                              end=self.simulation_steps)
        else:
            self.market.load_market_data.read_csv(file_name='data/market/consumer_price_list.csv',
                                              start=0,
                                              end=2)
        self.market.calculate()

   
    
    #%% run simulation for every timestep
    def simulate(self):
        '''
        Central simulation method, which :
            initializes all list containers to store simulation results
            iterates over all simulation timesteps and calls Simulatable.start/update/end()
        
        Parameters
        ----------
        None        
        '''
        ## Initialization of list containers to store simulation results                               
        # Timeindex
        self.timeindex = list()
        # Load demand 
        self.load_power_demand = list()   
        # PV 
        self.pv_power = list()
        self.used_pv_power = 0
        self.pv_temperature = list()
        self.pv_peak_power_current = list()
        for i in range(len(self.pv)):
            self.pv_power.append([])
            self.pv_temperature.append([])
            self.pv_peak_power_current.append([])
            
        # pv_charger
        self.pv_charger_power = list()
        self.pv_charger_efficiency = list()
        # Power junction
        self.power_junction_power = list()
        # BMS
        self.battery_management_power = list()
        self.battery_management_charger_efficiency = list()
        self.battery_management_discharger_efficiency = list()
        # Battery
        self.battery_power = list()
        self.battery_charge_power = list()
        self.battery_charging_efficiency = list()
        self.battery_discharging_efficiency = list()
        self.battery_power_loss = list()
        self.battery_temperature = list()
        self.battery_state_of_charge = list()
        self.battery_state_of_health = list()
        self.battery_capacity_current_wh = list()
        self.battery_capacity_loss_wh = list()
        self.battery_voltage = list()
        # Component state of destruction            
        self.photovoltaic_state_of_destruction = list()
        for i in range(len(self.pv)):
            self.photovoltaic_state_of_destruction.append([])
        self.battery_state_of_destruction = list()
        self.pv_charger_state_of_destruction = list()
        self.battery_management_state_of_destruction = list()
        # Component replacement
        self.photovoltaic_replacement = list()
        for i in range(len(self.pv)):
            self.photovoltaic_replacement.append([])
        self.battery_replacement = list()
        self.pv_charger_replacement = list()
        self.battery_management_replacement = list()

       
        # As long as needs_update = True simulation takes place
        if self.needs_update:
            print("----OpEnCells simulation start----")
            print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' Start')
            
            ## pvlib: irradiation and weather data
            self.env.load_data()
            ## Timeindex from irradiation data file
            time_index = self.env.time_index   
            ## pvlib: pv power
            for i in range(len(self.pv)):
                self.pv[i].load_data()
            
            ## Call start method (inheret from Simulatable) to start simulation
            self.start()
                             
            ## Iteration over all simulation steps
            for t in range(0, self.simulation_steps):
                ## Call update method to call calculation method and go one simulation step further
                self.update()
                
                # Time index
                self.timeindex.append(time_index[t])
                # Load demand
                self.load_power_demand.append(self.load.power) 
                # PV
                for i in range(len(self.pv)):
                    self.pv_power[i].append(self.pv[i].power)
                    self.pv_temperature[i].append(self.pv[i].temperature)
                    self.pv_peak_power_current[i].append(self.pv[i].peak_power_current)
                # pv_charger
                self.pv_charger_power.append(self.pv_charger.power)
                self.pv_charger_efficiency.append(self.pv_charger.charger_efficiency)
                # Power junction
                self.power_junction_power.append(self.power_junction.power)
                # BMS
                self.battery_management_power.append(self.battery_management.power)
                self.battery_management_charger_efficiency.append(self.battery_management.charger_efficiency)
                self.battery_management_discharger_efficiency.append(self.battery_management.discharger_efficiency)                
                # Battery
                self.battery_power.append(self.battery.power_battery)
                if self.battery.power_battery > 0:
                    self.battery_charge_power.append(self.battery.power_battery)
                else:
                    self.battery_charge_power.append(0)
                self.battery_charging_efficiency.append(self.battery.charging_efficiency)
                self.battery_discharging_efficiency.append(self.battery.discharging_efficiency)
                self.battery_power_loss.append(self.battery.power_loss)
                self.battery_temperature.append(self.battery.temperature)
                self.battery_state_of_charge.append(self.battery.state_of_charge)
                self.battery_state_of_health.append(self.battery.state_of_health)
                self.battery_capacity_current_wh.append(self.battery.capacity_current_wh)
                self.battery_capacity_loss_wh.append(self.battery.capacity_loss_wh)
                self.battery_voltage.append(self.battery.voltage)
                # Component state of destruction
                
                for i in range(len(self.pv)):
                    self.photovoltaic_state_of_destruction[i].append(self.pv[i].state_of_destruction)
                self.battery_state_of_destruction.append(self.battery.state_of_destruction)
                self.pv_charger_state_of_destruction.append(self.pv_charger.state_of_destruction)
                self.battery_management_state_of_destruction.append(self.battery_management.state_of_destruction)
                # Component replacement
                for i in range(len(self.pv)):
                    self.photovoltaic_replacement[i].append(self.pv[i].replacement)
                self.battery_replacement.append(self.battery.replacement)
                self.pv_charger_replacement.append(self.pv_charger.replacement)
                self.battery_management_replacement.append(self.battery_management.replacement)
                
            #total pv energy, after inefficiencies going into load coverage
            for i in range(len(self.pv_power)):
                self.used_pv_power += sum(self.pv_power[i])        
            
            #calculate average total generated energy of tech over a year
            #pv
            self.pv_tot_energy = list()
            
            for i in range(len(self.pv)):
                self.pv_tot_energy.append(sum(self.pv_power[i])*(self.timestep/3600)/1000/(self.simulation_steps*(self.timestep/3600)/8760))
            
            #charger
            self.pv_arrays_tot_energy = sum(self.pv_tot_energy[i] for i in range(len(self.pv_tot_energy)))
            
            #BM
            tot_batt_management_energy = 0
            for power_flow in self.power_junction_power:
                #only positive power flows into battery, i.e. charge case, count into battery energy 
                if power_flow > 0:
                    tot_batt_management_energy += power_flow
            self.battery_management_tot_energy = tot_batt_management_energy*(self.timestep/3600)/1000/(self.simulation_steps*(self.timestep/3600)/8760)
            
            #battery
            tot_batt_energy = 0
            for power_flow in self.battery_power:
                #only positive power flows into battery, i.e. charge case, count into battery energy 
                if power_flow > 0:
                    tot_batt_energy += power_flow
            self.battery_tot_energy = tot_batt_energy*(self.timestep/3600)/1000/ (self.simulation_steps*(self.timestep/3600)/8760)

            ## Simulation over: set needs_update to false and call end method
            self.needs_update = False
            print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' End')
            self.end()
    
    
    #%% Recalculate current battery capacity based on wear model and model optimization data
    def update_simulation_data (self, pv_flow, battery_flow, power_junct_flow, pv_peak_mod, batt_peak_mod, bought_power_list):
        '''
        Method to recalculate simulation model efficiencies as well as battery current capacity with optimization mdodel solution data at different time :
            recalculates pv charger and battery management efficiencies
            recalculates battery charge and discharge efficiencies
            recalculates battery capacity at different time steps
        
        Parameters
        ----------
        None        
        '''
        # restart modules that need it
        self.pv_tot_peak = 0
        for i in range(len(self.pv)):
            self.pv_peak_power[i] = self.pv_peak_power[i] * pv_peak_mod[i]
            self.pv_tot_peak += self.pv_peak_power[i]
        
        
            
        self.pv_charger = Power_Component(timestep=self.timestep,
                                       power_nominal=self.pv_tot_peak, 
                                       input_link=self.pv_power_junction, 
                                       file_path='data/components/power_component_mppt.json')
        print('sim:new pv peak capa', round(self.pv_tot_peak,2) )
        
        battery_investment_costs_specific = self.battery.investment_costs_specific
        self.battery_capacity = batt_peak_mod * self.battery_capacity
        print('sim:new battery peak capa', round(self.battery_capacity,2) )
        self.battery = Battery(timestep=self.timestep,
                               capacity_nominal_wh=self.battery_capacity, 
                               input_link=self.battery_management, 
                               env=self.env,
                               file_path='data/components/battery_lfp.json')
        self.battery.investment_costs_specific = battery_investment_costs_specific
        #get power flows passed from optimization model
        self.battery_flow = battery_flow
        self.power_junct_flow = power_junct_flow
        self.bought_power_list = bought_power_list
        
        # Reset necessary lists
        # PV 
        self.pv_power = list()
        self.max_possible_power = list()
        for i in range(len(self.pv)):
            self.pv_power.append([])
        pv_power = list()
        # pv_charger
        self.pv_charger_power = list()
        self.pv_charger_efficiency = list()
        # Power junction
        self.power_junction_power = list()
        # BMS
        self.battery_management_power = list()
        self.battery_management_charger_efficiency = list()
        self.battery_management_discharger_efficiency = list()
        #battery
        self.battery_power = list()
        self.battery_charge_power = list()
        self.battery_charging_efficiency = list()
        self.battery_discharging_efficiency = list()
        self.battery_power_loss = list()
        self.battery_temperature = list()
        self.battery_state_of_charge = list()
        self.battery_state_of_health = list()
        self.battery_capacity_current_wh = list()
        self.battery_capacity_loss_wh = list()
        self.battery_voltage = list()
        
        t = 0
        for i in self.battery_flow:
            #get power values at timestep t
            pv_power = sum(pv_flow[j][t] for j in range(len(self.pv)))
            power_junct_power = self.power_junct_flow[t]
            battery_power = self.battery_flow[t]   
            
            #recalculate battery model with new input values
            self.pv_charger.recalculate(pv_power)
            self.battery_management.recalculate(battery_power)
            self.battery.calculate()   #use standardr calculation method, as data comes from updated battery_management module
            
            # update lists to new values
            # PV
            for j in range(len(self.pv)):
                self.pv_power[j].append(pv_flow[j][t])
            # pv_charger
            self.pv_charger_power.append(self.pv_charger.power)
            self.pv_charger_efficiency.append(self.pv_charger.charger_efficiency)
            # Power jundtion
            self.power_junction_power.append(power_junct_power)
            # BMS
            self.battery_management_power.append(self.battery_management.power)
            self.battery_management_charger_efficiency.append(self.battery_management.charger_efficiency)
            self.battery_management_discharger_efficiency.append(self.battery_management.discharger_efficiency)           
            #battery
            self.battery_power.append(self.battery.power_battery)
            if self.battery.power_battery > 0:
                self.battery_charge_power.append(self.battery.power_battery)
            else:
                self.battery_charge_power.append(0)
            self.battery_charging_efficiency.append(self.battery.charging_efficiency)
            self.battery_discharging_efficiency.append(self.battery.discharging_efficiency)
            self.battery_power_loss.append(self.battery.power_loss)
            self.battery_temperature.append(self.battery.temperature)
            self.battery_state_of_charge.append(self.battery.state_of_charge)
            self.battery_state_of_health.append(self.battery.state_of_health)
            self.battery_capacity_current_wh.append(self.battery.capacity_current_wh)
            self.battery_capacity_loss_wh.append(self.battery.capacity_loss_wh)
            self.battery_voltage.append(self.battery.voltage)
        
            #go into next time step
            t += 1
            
            self.pv_charger.time += 1
            self.battery_management.time += 1
            self.battery.time += 1
        
        #calculate average total generated energy of tech over a year
        #pv
        self.pv_tot_energy = list()
        
        for i in range(len(self.pv)):
            self.pv_tot_energy.append(sum(self.pv_power[i])*(self.timestep/3600)/ 1000/ (self.simulation_steps*(self.timestep/3600)/8760))
        
        #charger
        self.pv_arrays_tot_energy = sum(self.pv_tot_energy[i] for i in range(len(self.pv_tot_energy)))
        
        #total pv energy, after inefficiencies going into load coverage
        self.used_pv_power = sum(self.load_power_demand) - sum(self.bought_power_list)
        
        #BM
        tot_batt_management_energy = 0
        for power_flow in self.power_junction_power:
            #only positive power flows into battery, i.e. charge case, count into battery energy 
            if power_flow > 0:
                tot_batt_management_energy += power_flow
        self.battery_management_tot_energy = tot_batt_management_energy*(self.timestep/3600)/ 1000/ (self.simulation_steps*(self.timestep/3600)/8760)
        
        #battery
        tot_batt_energy = 0
        for power_flow in self.battery_power:
            #only negative power flows from battery into grid, i.e. discharge case, count into battery energy 
            if power_flow < 0:
                tot_batt_energy += power_flow
        self.battery_tot_energy = tot_batt_energy*(self.timestep/3600)/ 1000/ (self.simulation_steps*(self.timestep/3600)/8760)
        
        self.pv_charger.time = 0
        self.battery_management.time = 0
        self.battery.time = 0
        
        #get overall change in component size
        self.pv_peak_change = list()
        for i in range(len(self.pv)):
            self.pv_peak_change.append( self.pv_peak_power[i] /self.pv_peak_power_start[i])
        self.bat_capa_change = self.battery_capacity/self.battery_capacity_start