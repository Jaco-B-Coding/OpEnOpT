# -*- coding: utf-8 -*-
"""
Created on Wed May 19 15:49:50 2021

@author: JB
"""
import pyomo.environ as pyo
import pyomo.gdp as gdp
import numpy as np
from datetime import datetime
import os

class Optimization_model():
    """Relevant methods to optimize model.

    Parameters
    ----------

    Note
    ----
    - 
    - 
    
    """
    
    def __init__(self, simulation_steps, time_step, simulation, opt_pv_size, opt_batt_size):
        
        #simulation solver
        self.opt = None
        
        #simulation parameters
        self.simulation_steps = simulation_steps
        self.time_step = time_step        
        self.sim = simulation
        self.opt_pv_size = opt_pv_size
        self.opt_batt_size = opt_batt_size
        
        self.deviation_threshold = 0.01
        self.deviation_counter = 0
        self.low_dev_in_row = 1     #to mark how many deviations in a row need to be lower than threshhold to have an answer
        
        
        self.round_error = 0.0
        
        #variable to take track of iterations over optimization model
        self.iteration = 0
        
        #objective function result
        self.total_costs_new = 0
        self.total_costs_old = 0
        
        #power flows lists
        self.battery_flow = list()
        self.battery_charge_list = list()
        self.battery_discharge_list = list()
        self.pv_flow = list()
        self.pv_power_unused = list()
        self.power_junct_flow =list()
        self.bought_power_list = list()
        self.sold_power_list = list()
        self.power_shortage_list = list()
        
        
        #save first pv power flows
        self.pv_max_power_start = list()
        self.max_pv_peak_power = list()
        for i in range(len(self.sim.pv)):
            self.pv_max_power_start.append(self.sim.pv_power[i])
            self.max_pv_peak_power.append(self.sim.max_pv_peak_power[i])
        
        #update flag
        self.update = False
        
        #solver specifications
        self.solver_type = 'mumps'
                
        #fit efficiencies through polynomial fit
        self.poly_fit_eff = False
        self.exact_ch_eff = True
   
    def update_model_data(self, eco_pv, eco_bat, eco_charger, eco_bms):
        """Method to update modelling parameters.

        Parameters
        ----------
    
        Note
        ----
        - 
        - 
        
        """    
        #demand 
        self.demand = self.sim.load_power_demand
        
        #buy and sell parameters
        self.buyprice = list()
        self.sellprice = list()
        
        if self.sim.grid_connected:
            self.max_sell = 0 #max(self.sim.load_power_demand) 
            self.max_buy = max(self.sim.load_power_demand)
        else:
            self.max_sell = 0
            self.max_buy = 0
        
        #electricity costs
        if self.sim.day_ahead_market:
            self.buyprice = self.sim.market.day_ahead_prices.values 
            self.sellprice = self.buyprice
        else:
            buyprice = self.sim.market.buyprice 
            sellprice = self.sim.market.sellprice 
            self.buyprice = [buyprice]*self.simulation_steps
            self.sellprice = [sellprice]*self.simulation_steps   
        #power shortage costs
        self.LCOE_shortage = 0.01
        self.max_shortage_power = 500000
        
        #power components
        self.pvCharger_total_LCOE_factor = eco_charger.total_LCOE_factor
        self.bms_total_LCOE_factor = eco_bms.total_LCOE_factor
        
        #pv
        if self.sim.pv is not None:            
            self.num_pv_sources = len(self.sim.pv)
            
            self.LCOE_pv = list()
            self.pv_total_LCOE_factor = list()
            
            #udate current power only first time<<
            #udate current power only first time<<
            if self.update == False:
                self.pv_max_power = list()
                self.pv_used_power_old = list()
            else:
                self.pv_used_power_old = self.pv_used_power.copy
            self.pv_used_power = list()  
            self.pv_array_kWp = list()
            self.min_pv_used_kWp = list()
            
            for i in range(self.num_pv_sources):
                self.LCOE_pv.append(eco_pv[i].levelized_costs)
                self.pv_total_LCOE_factor.append(eco_pv[i].total_LCOE_factor)
                
                #update only once at start or when pv peak power changes
                if self.update == False:     
                    self.pv_max_power.append(self.sim.pv_power[i]) 
                    self.pv_used_power_old.append(self.sim.used_pv_power)
                self.pv_used_power.append(self.sim.used_pv_power)
                self.pv_array_kWp.append(self.sim.pv_peak_power[i])
                self.min_pv_used_kWp.append(self.sim.pv[i].min_used_kWp)
            #pv charger
            if self.iteration == 0:
                self.pv_charger_efficiency = [1]* self.simulation_steps 
            else:
                self.pv_charger_efficiency = self.sim.pv_charger_efficiency
                
        #wind turbine               
        if self.sim.wind is not None:
            self.LCOE_wind = self.sim.wind.LCOE_wind
            self.num_wind_sources = 1                         #-->later make based on # of wind arrays in simulation
            self.wind_current_power = self.sim.wind_power            
            self.wind_array_nominal_kWp = self.sim.wind.size_nominal
            self.wind_array_kWp = self.sim.wind_peak_power
            self.min_wind_used_kWp = self.sim.wind.min_used_kWp
            
            #wind charger
            if self.iteration == 0:
                self.wind_charger_efficiency = [1]* self.simulation_steps 
            else:
                self.wind_charger_efficiency = self.sim.charger_efficiency
            
            #wind charger
            self.wind_charger_efficiency= self.sim.charger_efficiency
            
            
        #battery   
        if self.sim.battery is not None:
            self.LCOE_battery_charge = self.sim.battery.LCOE_battery
            self.bat_total_LCOE_factor = eco_bat.total_LCOE_factor
            
            self.LCOE_battery_discharge = 0 #self.LCOE_battery_charge  #--> assuming no cost in discharging energy from battery
            self.num_battery_arrays = 1
            self.battery_array_nominal_capacity = self.sim.battery_capacity
            self.max_battery_capacity = self.sim.max_battery_capacity
            self.battery_capacity_current_wh = self.sim.battery_capacity_current_wh
            self.min_battery_used_capacity = self.sim.battery.min_used_capacity
            
            self.battery_charged_power = self.sim.battery_charge_power
            
            #battery management and battery efficiencies
            #set maximal efficiency on first iteration
            if self.iteration == 0:
                self.battery_charger_efficiency =[1]* self.simulation_steps
                self.battery_discharger_efficiency = [1]* self.simulation_steps
                self.battery_charging_efficiency = [1]* self.simulation_steps
                self.battery_discharging_efficiency = [1]* self.simulation_steps
            else:
                self.battery_charger_efficiency =self.sim.battery_management_charger_efficiency
                self.battery_discharger_efficiency =self.sim.battery_management_discharger_efficiency
                self.battery_charging_efficiency = self.sim.battery_charging_efficiency
                self.battery_discharging_efficiency = self.sim.battery_discharging_efficiency
        
            self.SOC_start = self.sim.battery.state_of_charge_init
            self.SOC_min = self.sim.battery.end_of_discharge_b
            self.SOC_max = self.sim.battery.end_of_charge_b
            self.battery_min_charge_power = 0   
            self.battery_max_charge_power = 600    
            self.battery_min_discharge_power = 0  
            self.battery_max_discharge_power = 600
            
            self.battery_self_discharge = 3.8072e-09 *self.time_step
        
        #set update flag 
        self.update = True
        
        # print(self.buyprice) 
        # print(self.LCOE_pv[0])  
        # print('LCOE battery: ',self.LCOE_battery_charge)
    

    def check_iteration_deviation(self):
        '''
        method to analyze results deviation between iterations of the optimization model
        
        Parameters
        ----------
        None
        
        '''
            
        deviation_threshold_passed = True
        
        #go into next optimization model iteration
        self.iteration +=1       
        
        #check whether deviation is within acceptable bounds between iterations
        if self.deviation_threshold == 0:
            print('deviation threshold needs to be greater than 0')
            print('optimization aborted. Results may be off')
            deviation_threshold_passed = False
            return deviation_threshold_passed
        
        #no recalculation/ iteration occured yet
        if not self.total_costs_old:
            self.total_costs_old = self.total_costs_new            
            #set flag to recalculate OpEnCells model based on optimization values
            return True
        else:
            #calculate deviation
            
            print('old costs',round(self.total_costs_old,4), 'new costs', round(self.total_costs_new,4))
            deviation = abs(self.total_costs_old - self.total_costs_new)
            print('deviation between optimization iteration:',round(deviation,5))
            
            #if threshhold passed set flag to true and update total_costs_old
            threshhold = self.deviation_threshold * (self.total_costs_old + self.total_costs_new)/2
            if deviation >= threshhold:
                print('deviation between iterations greater than allowed')
                self.total_costs_old = self.total_costs_new
                #reset deviation counter
                self.deviation_counter = 0
                deviation = True
            #if iteration is smaller then start counter on how many times in a row
            else:
                print('deviation within allowed limits. Rerunning for ',self.low_dev_in_row - 1 - self.deviation_counter,\
                          'times, to check for result stability')
                self.deviation_counter +=1
                if self.deviation_counter >= self.low_dev_in_row and self.iteration > 4:
                    deviation = False
            
            return deviation
        
    def init_model(self):
        '''
        Central model optimization method which optimizes the model according to data received from first and subsequent simulation runs. 
        
        Parameters
        ----------
        None        
        '''
       
        #%%declaration of model components
        self.model = pyo.ConcreteModel()
        
        #objective variables
        self.model.econ_opt = pyo.Var(initialize = 1)
        # self.model.size_opt = pyo.Var(initialize = 1, bounds = (0,100))
        
        #Set of one to circumvent package conflicts between Pyomo and numpy
        self.model.S = pyo.Set(initialize = [1,])
        
        #timesteps 
        self.model.sim_step = pyo.Param( initialize = self.simulation_steps)
        self.model.simulation_steps = pyo.RangeSet(1,self.simulation_steps)
        self.model.time_step = pyo.Param(initialize = self.time_step)
        
        #rounding error to be used for disjuncts
        self.model.round_error = pyo.Param(initialize = self.round_error)
        
        #demand curve data
        def demand_init_rule(m,t):
            return self.demand[t-1] / self.sim.order_of_magnitude
        self.model.demand = pyo.Param(self.model.simulation_steps, initialize = demand_init_rule)
        
        
        #%%Grid Parameters
        def buyprice_rule(m, t):
            return self.buyprice[t-1] * self.sim.order_of_magnitude
        self.model.grid_buyprice = pyo.Param(self.model.simulation_steps, initialize = buyprice_rule)
        
        def sellprice_rule(m,t):
            return self.sellprice[t-1] * self.sim.order_of_magnitude
        self.model.grid_sellprice = pyo.Param(self.model.simulation_steps, initialize = sellprice_rule)
        
        def buy_rule(m,t):
            if not self.bought_power_list:
                return 0
            else:
                #init with old iteration values
                return self.bought_power_list[t-1] / self.sim.order_of_magnitude
        self.model.grid_current_bought_power = pyo.Var(self.model.simulation_steps, initialize = buy_rule, bounds = (0, self.max_buy))
        
        def sell_rule(m,t):
            if not self.sold_power_list:
                return 0
            else:
                #init with old iteration values
                return self.sold_power_list[t-1] / self.sim.order_of_magnitude
        self.model.grid_current_sold_power = pyo.Var(self.model.simulation_steps, initialize = sell_rule, bounds= (0, self.max_sell))
        
        #%%shortage parameters
        def shortage_cost_rule(m, shortage_cost):
            expr = np.array(self.buyprice)
            expr = np.concatenate((expr, self.sellprice))
            expr = np.concatenate((expr,np.array(self.LCOE_pv),[self.LCOE_battery_discharge, self.LCOE_battery_charge]))
            
            #set a shortage cost price higher than other energy costs if none specified
            if not shortage_cost:
                shortage_cost = (max(expr) + 1) * self.sim.order_of_magnitude
                return shortage_cost
            #set the specified cost as self.model shortage cost
            else:
                return shortage_cost * self.sim.order_of_magnitude
            
        self.model.shortage_costs = pyo.Param(initialize = shortage_cost_rule(self.model,self.LCOE_shortage))
        
        def shortage_power_rule(m,t):
            if not self.power_shortage_list:
                return 0
            else:
                #init with old iteration values
                return self.power_shortage_list[t-1] / self.sim.order_of_magnitude
        self.model.shortage_power = pyo.Var(self.model.simulation_steps, initialize = shortage_power_rule, bounds = (0, self.max_shortage_power))
        
        #%%power components data
        self.model.pvCharger_total_LCOE_factor = pyo.Param(initialize = self.pvCharger_total_LCOE_factor *self.sim.order_of_magnitude)
        self.model.bms_total_LCOE_factor = pyo.Param(initialize = self.bms_total_LCOE_factor *self.sim.order_of_magnitude)
        
        #%%PV
        self.model.num_pv_sources = pyo.Param(initialize = self.num_pv_sources)
        self.model.pv_sources_set = pyo.RangeSet(1,self.model.num_pv_sources)        
        self.model.pv_charger_eff_coeff_set = pyo.RangeSet(1,len(self.sim.pv_charger.eff_coeff_array))
        self.model.pv_eff_fit_deg = pyo.Param(initialize = len(self.sim.pv_charger.eff_coeff_array))

        
        #block used for construction of pv self.model components
        def pv_comp_rule (model_block, model_set):
            model_block.pv_sources_set = pyo.RangeSet(model_set)   #-->in case of use within other file
            
            model_block.pv_total_LCOE_factor = pyo.Param(initialize = self.pv_total_LCOE_factor[model_set-1] *self.sim.order_of_magnitude)
            if self.iteration <=1:
                model_block.pv_cost = pyo.Var( initialize = self.LCOE_pv[model_set-1] * self.sim.order_of_magnitude, within = pyo.NonNegativeReals)
            else:
                model_block.pv_cost = pyo.Var( initialize = self.LCOE_pv_old[model_set-1] * self.sim.order_of_magnitude, within = pyo.NonNegativeReals)

            model_block.pv_array_kWp = pyo.Param( initialize = self.pv_array_kWp[model_set-1] / self.sim.order_of_magnitude)
            model_block.max_pv_kWp = pyo.Param( initialize = self.max_pv_peak_power[model_set-1] / self.sim.order_of_magnitude)
            
            def pv_max_power_rule(_model_block, t):
                return self.pv_max_power[model_set-1][t-1]/ self.sim.order_of_magnitude                       #for different power data for different sources: return pv_max_power[i][t-1] for i in _self.model_block.pv_sources_set
            model_block.pv_max_power = pyo.Param(self.model.simulation_steps, initialize = pv_max_power_rule)
            
            def pv_used_power_rule(m):
                return self.pv_used_power_old[model_set-1]/self.sim.order_of_magnitude
            model_block.pv_used_power = pyo.Param(initialize = pv_used_power_rule)
            
            def pv_power_rule(m,t):
                if not self.pv_flow:
                    return 0
                else:
                    #init with old iteration values
                    return self.pv_flow[model_set-1][t-1]
            model_block.pv_module_power = pyo.Var(self.model.simulation_steps, initialize = pv_power_rule, bounds = (0,1))
            
            if self.opt_pv_size == True and self.iteration >=1 :
                model_block.pv_peak_mod = pyo.Var(self.model.S,initialize = 1, bounds = (0.01,10))
            else:
                model_block.pv_peak_mod = pyo.Param(self.model.S, initialize = 1)
            
            def pv_eff_coeff_rule(_model_block, coeff_set):
                return self.sim.pv_charger.eff_coeff_array[coeff_set-1]
            
            def pv_charger_efficiency_rule(_model_block, t):
                return self.pv_charger_efficiency[t-1]
            if self.poly_fit_eff:
                model_block.pv_charger_efficiency = pyo.Var(self.model.simulation_steps, initialize = pv_charger_efficiency_rule,bounds = (0,1))    
                model_block.ch_eff_param = pyo.Param(self.model.pv_charger_eff_coeff_set, initialize = pv_eff_coeff_rule)
            else:
                model_block.pv_charger_efficiency = pyo.Param(self.model.simulation_steps, initialize = pv_charger_efficiency_rule)    
            
        self.model.pv_comp_block = pyo.Block(self.model.pv_sources_set, rule = pv_comp_rule)
        
        #%%Batteries
        self.model.num_battery_arrays = pyo.Param(initialize = self.num_battery_arrays)
        self.model.battery_arrays_set = pyo.RangeSet(1,self.model.num_battery_arrays)
        self.model.battery_charger_eff_coeff_set = pyo.RangeSet(1,len(self.sim.battery_management.eff_coeff_array))
        self.model.batt_eff_fit_deg = pyo.Param(initialize = len(self.sim.battery_management.eff_coeff_array))

        
        #block used for construction of battery model components
        def battery_comp_rule (model_block, model_set):
            model_block.battery_sources_set = pyo.RangeSet(model_set)   #-->in case of use within other file
            
            model_block.bat_total_LCOE_factor = pyo.Param(initialize = self.bat_total_LCOE_factor *self.sim.order_of_magnitude )
            model_block.battery_charge_cost = pyo.Var(initialize = self.LCOE_battery_charge*self.sim.order_of_magnitude, within = pyo.NonNegativeReals)
            model_block.battery_discharge_cost = pyo.Param(initialize = self.LCOE_battery_discharge*self.sim.order_of_magnitude)
            
            model_block.bat_array_kWp = pyo.Param( initialize = self.battery_array_nominal_capacity/self.sim.order_of_magnitude)
            model_block.max_battery_capacity = pyo.Param( initialize = self.max_battery_capacity/self.sim.order_of_magnitude)
            
            if self.opt_batt_size == True and self.iteration >=1:
                model_block.battery_peak_mod = pyo.Var(self.model.S, initialize = 1, bounds = (0.01,5))
            else:
                model_block.battery_peak_mod = pyo.Param(self.model.S, initialize = 1)
            
            def battery_discharge_rule(m,t):
                if not self.battery_discharge_list:
                    return 0
                else:
                    #init with old iteration values
                    return self.battery_discharge_list[t-1] / self.sim.order_of_magnitude
            model_block.battery_current_discharge_power = pyo.Var(self.model.simulation_steps, initialize = battery_discharge_rule, bounds = (self.battery_min_discharge_power,self.battery_max_discharge_power))
            
            def battery_charge_rule(m,t):
                if not self.battery_charge_list:
                    return 0
                else:
                    #init with old iteration values
                    return self.battery_charge_list[t-1] / self.sim.order_of_magnitude
            model_block.battery_current_charge_power = pyo.Var(self.model.simulation_steps, initialize = battery_charge_rule, bounds = (self.battery_min_charge_power,self.battery_max_charge_power))
            
            def battery_charged_power_rule(m,t):
                return self.battery_charged_power[t-1] / self.sim.order_of_magnitude
            model_block.battery_charged_power = pyo.Param(self.model.simulation_steps, initialize = battery_charged_power_rule)
                
            
            def battery_array_capacity_rule(_model_block, t):
                return self.battery_capacity_current_wh[t-1] / self.sim.order_of_magnitude
            model_block.battery_capacity_current_wh = pyo.Param(self.model.simulation_steps, initialize = battery_array_capacity_rule)
            
            model_block.SOC_min = pyo.Param(initialize = self.SOC_min)
            model_block.SOC_max = pyo.Param(initialize = self.SOC_max)
            model_block.SOC_start = pyo.Param(initialize = self.SOC_start)
            model_block.battery_SOC = pyo.Var(self.model.simulation_steps, initialize = model_block.SOC_max, bounds = (self.SOC_min, self.SOC_max))
            model_block.battery_self_discharge = pyo.Param(initialize = self.battery_self_discharge)
            
            #battery and battery management efficiencies
            def bat_eff_coeff_rule(_model_block, coeff_set):
                return self.sim.battery_management.eff_coeff_array[coeff_set-1]
            
            def battery_charger_efficiency_rule(_model_block, t):
                return self.battery_charger_efficiency[t-1]
            if self.poly_fit_eff:
                model_block.battery_charger_efficiency = pyo.Var(self.model.simulation_steps, initialize = battery_charger_efficiency_rule, bounds = (0,1))   
                model_block.ch_eff_param = pyo.Param(self.model.battery_charger_eff_coeff_set, initialize = bat_eff_coeff_rule)

            else:
                model_block.battery_charger_efficiency = pyo.Param(self.model.simulation_steps, initialize = battery_charger_efficiency_rule)   
            
            def battery_discharger_efficiency_rule(_model_block, t):
                return self.battery_discharger_efficiency[t-1]
            if self.poly_fit_eff:
                model_block.battery_discharger_efficiency = pyo.Var(self.model.simulation_steps, initialize = battery_discharger_efficiency_rule, bounds = (0,1))    
                model_block.power_self_consumption = pyo.Param(initialize = self.sim.battery_management.power_self_consumption)
                model_block.voltage_loss = pyo.Param(initialize = self.sim.battery_management.voltage_loss)
                model_block.resistance_loss = pyo.Param(initialize = self.sim.battery_management.resistance_loss)
            else:
                model_block.battery_discharger_efficiency = pyo.Param(self.model.simulation_steps, initialize = battery_discharger_efficiency_rule)    
            
            def battery_charging_efficiency_rule(_model_block, t):
                return self.battery_charging_efficiency[t-1]
            if self.exact_ch_eff:
                model_block.charge_power_efficiency_a = pyo.Param(initialize = self.sim.battery.charge_power_efficiency_a)
                model_block.charge_power_efficiency_b = pyo.Param(initialize = self.sim.battery.charge_power_efficiency_b)
                model_block.battery_charging_efficiency = pyo.Var(self.model.simulation_steps, initialize = battery_charging_efficiency_rule, bounds = (0,1))
            else:
                model_block.battery_charging_efficiency = pyo.Param(self.model.simulation_steps, initialize = battery_charging_efficiency_rule)
            
            def battery_discharging_efficiency_rule(_model_block, t):
                return self.battery_discharging_efficiency[t-1]
            if self.exact_ch_eff:
                model_block.discharge_power_efficiency_a = pyo.Param(initialize = self.sim.battery.discharge_power_efficiency_a)
                model_block.discharge_power_efficiency_b = pyo.Param(initialize = self.sim.battery.discharge_power_efficiency_b)
                model_block.battery_discharging_efficiency = pyo.Var(self.model.simulation_steps, initialize = battery_discharging_efficiency_rule, bounds =(0,1))
            else:
                model_block.battery_discharging_efficiency = pyo.Param(self.model.simulation_steps, initialize = battery_discharging_efficiency_rule)
            
            model_block.battery_min_charge_power = pyo.Param(initialize = self.battery_min_charge_power)
            model_block.battery_min_discharge_power = pyo.Param(initialize = self.battery_min_discharge_power)
            
        self.model.battery_comp_block = pyo.Block(self.model.battery_arrays_set, rule = battery_comp_rule)
        
        #%%Objective definitions
        #economical objective
        # def econ_obj_rule(m):
        #     expr = 0
            
        #     #summation of costs through different sources
        #     for b in m.pv_sources_set:
        #         #pv
        #         expr += sum(m.pv_comp_block[b].pv_cost*m.pv_comp_block[b].pv_max_power[t]\
        #                     *m.pv_comp_block[b].pv_module_power[t]*m.pv_comp_block[b].pv_peak_mod[1]\
        #                     for t in m.simulation_steps)   
        #       #battery
        #     for b in m.battery_comp_block:
        #         expr += sum(m.battery_comp_block[b].battery_charge_cost*m.battery_comp_block[b].battery_current_charge_power[t]\
        #                     for t in m.simulation_steps)
        #     #shortage
        #     expr += sum(m.shortage_costs*m.shortage_power[t]\
        #                 for t in m.simulation_steps)
        #     #grid        
        #     expr += sum(m.grid_buyprice[t]*m.grid_current_bought_power[t]\
        #                 - m.grid_sellprice[t]*m.grid_current_sold_power[t]\
        #                 for t in m.simulation_steps)
            
        #     return m.econ_opt == expr  
        
        def econ_obj_rule(m):
            expr = 0
            
            #summation of costs through different sources
            for b in m.pv_sources_set:
                #pv
                expr += sum(m.pv_comp_block[b].pv_cost*m.pv_comp_block[b].pv_max_power[t]\
                            *m.pv_comp_block[b].pv_module_power[t]*m.pv_comp_block[b].pv_peak_mod[1]\
                            for t in m.simulation_steps)   
            #   #battery
            # for b in m.battery_comp_block:
            #     expr += sum(m.battery_comp_block[b].battery_charge_cost*m.battery_comp_block[b].battery_current_charge_power[t]\
            #                 for t in m.simulation_steps)
            #shortage
            expr += sum(m.shortage_costs*m.shortage_power[t]\
                        for t in m.simulation_steps)
            #grid        
            expr += sum(m.grid_buyprice[t]*m.grid_current_bought_power[t]\
                        - m.grid_sellprice[t]*m.grid_current_sold_power[t]\
                        for t in m.simulation_steps)
            
            return m.econ_opt == expr  
        
        self.model.econ_obj_constr = pyo.Constraint(rule=econ_obj_rule)
        
        self.model.econ_obj = pyo.Objective(expr=self.model.econ_opt, sense = pyo.minimize)
        
        
        #%%
        #%%defining Constraints
        #constraint for meeting demand at all timesteps t
        def meet_demand_rule(m,t):
            expr = 0
            
            #summation of power from different sources
            #pv
            for b in m.pv_comp_block:
                expr += m.pv_comp_block[b].pv_max_power[t]*m.pv_comp_block[b].pv_module_power[t]*m.pv_comp_block[b].pv_charger_efficiency[t]\
                    *m.pv_comp_block[b].pv_peak_mod[1]
            
            #battery  
            for b in m.battery_comp_block:
                expr += m.battery_comp_block[b].battery_current_discharge_power[t]\
                    *m.battery_comp_block[b].battery_discharging_efficiency[t]*m.battery_comp_block[b].battery_discharger_efficiency[t]\
                    - m.battery_comp_block[b].battery_current_charge_power[t]
            
            #shortage
            expr += m.shortage_power[t]
            
            #grid
            expr += m.grid_current_bought_power[t]-m.grid_current_sold_power[t]
            
            return expr == m.demand[t]
                
        self.model.meet_demand_constr = pyo.Constraint(self.model.simulation_steps, rule = meet_demand_rule)
        
        #%%LCOE constraints
        #pv
        def pv_LCOE_rule(m, b):
            expr = 0
            expr =  ((m.pvCharger_total_LCOE_factor + m.pv_comp_block[b].pv_total_LCOE_factor) * m.pv_comp_block[b].pv_array_kWp\
                *m.pv_comp_block[b].pv_peak_mod[1] + m.battery_comp_block[b].battery_peak_mod[1]*m.battery_comp_block[b].bat_array_kWp \
                *(m.battery_comp_block[b].bat_total_LCOE_factor + m.bms_total_LCOE_factor)) \
                /(1 + m.pv_comp_block[b].pv_used_power*(m.time_step/3600)/ (m.sim_step/8760))
            
            
            return m.pv_comp_block[b].pv_cost == expr
        self.model.pv_LCOE_constr = pyo.Constraint(self.model.pv_sources_set, rule = pv_LCOE_rule)
        
        # #battery
        # def battery_charge_LCOE_rule(m, b):
        #     expr = 0
        #     # expr = m.battery_comp_block[b].bat_total_LCOE_factor * m.battery_comp_block[b].bat_array_kWp\
        #     #     / (1+sum(m.battery_comp_block[b].battery_charged_power[t]
        #     #           for t in m.simulation_steps)*(m.time_step/3600)/ (m.sim_step/8760))
        #     # expr = m.battery_comp_block[b].battery_peak_mod[1]* m.battery_comp_block[b].bat_total_LCOE_factor * m.battery_comp_block[b].bat_array_kWp\
        #     #     / (1+sum(m.battery_comp_block[b].battery_charged_power[t]
        #     #           for t in m.simulation_steps)*(m.time_step/3600)/ (m.sim_step/8760))
        #     if self.opt_batt_size == True:
        #         expr = m.battery_comp_block[b].battery_peak_mod[1]* m.battery_comp_block[b].bat_total_LCOE_factor * m.battery_comp_block[b].bat_array_kWp\
        #             / (1+sum(m.battery_comp_block[b].battery_current_discharge_power[t]\
        #              *m.battery_comp_block[b].battery_discharging_efficiency[t]*m.battery_comp_block[b].battery_discharger_efficiency[t]
        #                  for t in m.simulation_steps)*(m.time_step/3600)/ (m.sim_step/8760))
        #     else:
        #         expr = m.battery_comp_block[b].bat_total_LCOE_factor * m.battery_comp_block[b].bat_array_kWp\
        #         / (1+sum(m.battery_comp_block[b].battery_current_discharge_power[t]\
        #              *m.battery_comp_block[b].battery_discharging_efficiency[t]*m.battery_comp_block[b].battery_discharger_efficiency[t]
        #               for t in m.simulation_steps)*(m.time_step/3600)/ (m.sim_step/8760))
                
        #     return m.battery_comp_block[b].battery_charge_cost == expr
        # self.model.battery_LCOE_constr = pyo.Constraint(self.model.battery_arrays_set, rule = battery_charge_LCOE_rule)
        
        #%%max peak power and capacity constraints
        def max_pv_peak_rule(m,b):
            expr = m.pv_comp_block[b].pv_array_kWp * m.pv_comp_block[b].pv_peak_mod[1]
            return expr <= m.pv_comp_block[b].max_pv_kWp
        self.model.max_pv_kWp_constr = pyo.Constraint(self.model.pv_sources_set, rule = max_pv_peak_rule)
        
        def max_battery_capa_rule(m,b):
            expr = m.battery_comp_block[b].bat_array_kWp * m.battery_comp_block[b].battery_peak_mod[1]
            return expr <= m.battery_comp_block[b].max_battery_capacity
        self.model.max_battery_capa_constr = pyo.Constraint(self.model.battery_arrays_set, rule = max_battery_capa_rule)
        
        #%%efficiency constraints
        if self.poly_fit_eff:
            def pv_charger_eff_rule(m,b,t):
                expr = sum(m.pv_comp_block[b].ch_eff_param[i]*m.pv_comp_block[b].pv_module_power[t]**(m.pv_eff_fit_deg-i) \
                            for i in m.pv_charger_eff_coeff_set)
                return m.pv_comp_block[b].pv_charger_efficiency[t] == 0.9
            self.model.pv_charger_eff_const = pyo.Constraint(self.model.pv_sources_set, self.model.simulation_steps, rule = pv_charger_eff_rule)

            #run time intensive constraint
            def battery_charger_eff_rule(m,b,t):
                expr = sum((m.battery_comp_block[b].battery_current_discharge_power[t]/(m.battery_comp_block[b].battery_peak_mod[1] \
                            * m.battery_comp_block[b].battery_capacity_current_wh[t]))\
                            **(m.batt_eff_fit_deg-i)* m.battery_comp_block[b].ch_eff_param[i]\
                            for i in m.battery_charger_eff_coeff_set)
                return m.battery_comp_block[b].battery_charger_efficiency[t] == 0.8
            self.model.battery_charger_eff_const = pyo.Constraint(self.model.battery_arrays_set, self.model.simulation_steps, rule = battery_charger_eff_rule)
        
            #run time intensive constraint
            def battery_discharger_eff_rule(m,b,t):
                power_output = (m.battery_comp_block[b].battery_current_discharge_power[t]/(m.battery_comp_block[b].battery_peak_mod[1] \
                            * m.battery_comp_block[b].battery_capacity_current_wh[t]))
                expr = power_output / (power_output + m.battery_comp_block[b].power_self_consumption + (power_output * m.battery_comp_block[b].voltage_loss) \
                    + (power_output**2 * m.battery_comp_block[b].resistance_loss))
                return m.battery_comp_block[b].battery_discharger_efficiency[t]== 0.8
            self.model.battery_discharger_eff_const = pyo.Constraint(self.model.battery_arrays_set, self.model.simulation_steps, rule = battery_discharger_eff_rule)

        if self.exact_ch_eff:
            def battery_charging_eff_rule(m,b,t):
                expr = m.battery_comp_block[b].charge_power_efficiency_a * (m.battery_comp_block[b].battery_current_charge_power[t]*m.battery_comp_block[b].battery_charger_efficiency[t]/(m.battery_comp_block[b].battery_peak_mod[1] \
                           * m.battery_comp_block[b].battery_capacity_current_wh[t]))\
                    + m.battery_comp_block[b].charge_power_efficiency_b
                return m.battery_comp_block[b].battery_charging_efficiency[t] == expr
            self.model.battery_charging_eff_const = pyo.Constraint(self.model.battery_arrays_set, self.model.simulation_steps, rule = battery_charging_eff_rule)

            def battery_discharging_eff_rule(m,b,t):
                expr = m.battery_comp_block[b].discharge_power_efficiency_a*(m.battery_comp_block[b].battery_current_discharge_power[t]/(m.battery_comp_block[b].battery_peak_mod[1] \
                    * m.battery_comp_block[b].battery_capacity_current_wh[t]))\
                    + m.battery_comp_block[b].discharge_power_efficiency_b

                return m.battery_comp_block[b].battery_discharging_efficiency[t] == expr
            self.model.battery_discharging_eff_const = pyo.Constraint(self.model.battery_arrays_set, self.model.simulation_steps, rule = battery_discharging_eff_rule)

        #%%Constraint for battery state of charge
        def SOC_rule (m,b,t):
            expr = 0
            if t == 1:
                expr = m.battery_comp_block[b].SOC_start
            elif t > 1 :
                #negative battery current flow as flow into battery when battery current flo is negative
                batt_total_capa = m.battery_comp_block[b].battery_peak_mod[1] * m.battery_comp_block[b].battery_capacity_current_wh[t-1]
                expr = m.battery_comp_block[b].battery_SOC[t-1]\
                    + (m.battery_comp_block[b].battery_current_charge_power[t-1]\
                    *m.battery_comp_block[b].battery_charging_efficiency[t-1]*m.battery_comp_block[b].battery_charger_efficiency[t-1]\
                    - m.battery_comp_block[b].battery_current_discharge_power[t-1])\
                    /batt_total_capa\
                    - m.battery_comp_block[b].battery_self_discharge
            else:
                print ("SOC_Rule: t not in right bounds")
            
            return m.battery_comp_block[b].battery_SOC[t] == expr
        
        self.model.SOC_constr = pyo.Constraint(self.model.battery_arrays_set, self.model.simulation_steps, rule = SOC_rule)
        
        #Constraint for maximal discharge power at last time step
        def last_discharge_rule(m, b):
            expr = 0
            expr += (m.battery_comp_block[b].battery_SOC[self.simulation_steps] - self.SOC_min)*m.battery_comp_block[b].battery_capacity_current_wh[self.simulation_steps]\
                *m.battery_comp_block[b].battery_peak_mod[1]
            return m.battery_comp_block[b].battery_current_discharge_power[self.simulation_steps] <= expr
        self.model.last_discharge_constr = pyo.Constraint(self.model.battery_arrays_set, rule = last_discharge_rule)
        
        
        # %%disjunctive constraint for battery charge and discharge
        #two conditions for each time step
        # def _d_batt_charge(disjunct, b, t, flag ):
        #     m = disjunct.model()
        #     if flag:
        #           #discharging
        #         disjunct.ch = pyo.Constraint(expr = m.battery_comp_block[b].battery_current_discharge_power[t] >= m.battery_comp_block[b].battery_min_discharge_power )
        #         disjunct.dch = pyo.Constraint(expr = m.battery_comp_block[b].battery_current_charge_power[t] <= m.battery_comp_block[b].battery_min_charge_power)
        #     else:
        #         #charging 
        #         disjunct.ch = pyo.Constraint(expr = m.battery_comp_block[b].battery_current_discharge_power[t] <= m.battery_comp_block[b].battery_min_discharge_power)
        #         disjunct.dch = pyo.Constraint(expr = m.battery_comp_block[b].battery_current_charge_power[t] >= m.battery_comp_block[b].battery_min_charge_power )
        
        # self.model.d_batt_charge = gdp.Disjunct(self.model.battery_arrays_set, self.model.simulation_steps, [0,1], rule=_d_batt_charge)
        
        # #define the disjunction for grid buy and sell 
        # def _c_batt_charge(m, b, t):
        #     return [m.d_batt_charge[b, t, 0],m.d_batt_charge[b, t, 1]]
        # self.model.c_batt_charge = gdp.Disjunction(self.model.battery_arrays_set, self.model.simulation_steps, rule=_c_batt_charge)
        
        #%% disjunctive constraint for battery charge and discharge
        # #two conditions for each time step
        # def _d_batt_charge(disjunct, b, t, flag ):
        #     m = disjunct.model()
        #     if flag:
        #           #discharging
        #         disjunct.ch = pyo.Constraint(expr = m.battery_comp_block[b].battery_current_discharge_power[t] >= m.battery_comp_block[b].battery_min_discharge_power )
        #         disjunct.dch = pyo.Constraint(expr = m.battery_comp_block[b].battery_current_charge_power[t] <= m.battery_comp_block[b].battery_min_charge_power)
        #     else:
        #         #charging 
        #         disjunct.ch = pyo.Constraint(expr = m.battery_comp_block[b].battery_current_discharge_power[t] <= m.battery_comp_block[b].battery_min_discharge_power)
        #         disjunct.dch = pyo.Constraint(expr = m.battery_comp_block[b].battery_current_charge_power[t] >= m.battery_comp_block[b].battery_min_charge_power )
        
        # self.model.d_batt_charge = gdp.Disjunct(self.model.battery_arrays_set, self.model.simulation_steps, [0,1], rule=_d_batt_charge)
        
        # #define the disjunction for grid buy and sell 
        # def _c_batt_charge(m, b, t):
        #     return [m.d_batt_charge[b, t, 0],m.d_batt_charge[b, t, 1]]
        # self.model.c_batt_charge = gdp.Disjunction(self.model.battery_arrays_set, self.model.simulation_steps, rule=_c_batt_charge)
        
        # #%%disjunctive constraint for buy and sell amount
        # #two conditions for each time step
        # def _d(disjunct, t, flag ):
        #     m = disjunct.model()
        #     if flag:
        #         #buying power ==> sell == 0
        #         disjunct.buy = pyo.Constraint(expr = m.grid_current_bought_power[t] >= 0)
        #         disjunct.sell = pyo.Constraint( expr = m.grid_current_sold_power[t] <= 0)
        #     else:
        #         #selling power ==> buy == 0
        #         disjunct.buy = pyo.Constraint(expr = m.grid_current_bought_power[t] <= 0)
        #         disjunct.sell = pyo.Constraint( expr = m.grid_current_sold_power[t] >= 0)
        # self.model.d = gdp.Disjunct(self.model.simulation_steps, [0,1], rule=_d)
        
        # #define the disjunction for grid buy and sell 
        # def _c(m, t):
        #     return [m.d[t, 0],m.d[t, 1]]
        # self.model.c = gdp.Disjunction(self.model.simulation_steps, rule=_c)
        
      
    def optimize_model(self):
      
        #%% solve model and get results 
         #get start time
        start = datetime.now()
        start_time = start.strftime("%H:%M:%S")
                
        print('----Optimization procedure start----')
        print("Start Time =", start_time)
        
        # pyo.TransformationFactory('core.logical_to_linear').apply_to(self.model)
        # pyo.TransformationFactory('gdp.bigm').apply_to(self.model)
        # pyo.TransformationFactory('gdp.hull').apply_to(self.model)
        # pyo.TransformationFactory('gdp.cuttingplane').apply_to(self.model)
        
        # if self.opt == None:
        #     ##solve with linear solver glpk
        #     self.opt = pyo.SolverFactory('couenne')
        # results = self.opt.solve(self.model, tee = True)  
        
        #Solve through NEOS server
        # provide an email address
        # os.environ['NEOS_EMAIL'] ='j.biagioli@campus.tu-berlin.de'
        # solver_manager = pyo.SolverManagerFactory('neos')
        # results = solver_manager.solve(self.model, opt='couenne', tee = True)
        
         # solve with non-linear solver ipopt 
        opt = pyo.SolverFactory('ipopt',solver_io='python')
        opt.options['max_iter']= 100 #number of iterations you wish
        opt.options['linear_solver'] = self.solver_type
        try:
            results = opt.solve(self.model, tee=False)   #set tee to True if solver output needs to be printed
        except (ValueError) as error:
            print('--------------------------------------------------------------------------------------------')
            print('Error solving optimization model: Cannot load a SolverResults object with bad status: error')
            print('--------------------------------------------------------------------------------------------')
        
        # self.model.pprint()        
        
        # pyo.SolverFactory('mpec_minlp').solve(self.model, tee = True)
        # pyo.SolverFactory('gdpopt').solve(self.model, mip_solver = 'glpk', tee = True, time_limit = 6000)
        # pyo.SolverFactory('mindtpy').solve(self.model, mip_solver='gurobi', nlp_solver='ipopt', tee = True, time_limit = 6000)   
        
        #print optimization end time
        end = datetime.now()
        end_time = end.strftime("%H:%M:%S")        
        print("End Time =", end_time)
        
        #get total costs
        self.total_costs_new = pyo.value(self.model.econ_obj)
        # self.total_costs_new = pyo.value(self.model.size_opt)
        # self.total_costs_new = pyo.value(self.model.O_augmecon)
        # print(pyo.value(self.model.pv_comp_block[1].pv_peak_mod[1]))
                
        b=1
        
        print('pvLCOE:',round(pyo.value(self.model.pv_comp_block[b].pv_cost)*1000/self.sim.order_of_magnitude,4))
        print('battery LCOE', round(pyo.value(self.model.battery_comp_block[b].battery_charge_cost)*1000/self.sim.order_of_magnitude,4))
        print('buy cost:', pyo.value(self.model.grid_buyprice[1])*1000/self.sim.order_of_magnitude)
        print('shortage LCOE:',round(pyo.value(self.model.shortage_costs)*1000/self.sim.order_of_magnitude,4))
        
        self.pv_peak_mod_list = list()
        for i in range(len(self.sim.pv)):
            self.pv_peak_mod_list.append(pyo.value(self.model.pv_comp_block[i+1].pv_peak_mod[1]))
        print('pv_peak_mod:', self.pv_peak_mod_list)
        self.batt_peak_mod = pyo.value(self.model.battery_comp_block[b].battery_peak_mod[1]) 
        print('battery_peak_mod:',round(self.batt_peak_mod,2))
        
        
        self.pv_max_possible_power = list()
        for i in range(len(self.sim.pv)):
            mult_workaround = pyo.value(self.model.pv_comp_block[i+1].pv_peak_mod[1])
            self.pv_max_possible_power.append(self.pv_max_power_start[i])
            for j in range(len(self.pv_max_possible_power[i])):
                self.pv_max_possible_power[i][j]*mult_workaround
        
        self.get_opt_values()
        
        #check whether energy generation is 
        energy_creation = 0
        for t in self.model.simulation_steps:
            for j in range(len(self.sim.pv)):  
                j +=1
                energy_creation += pyo.value(self.model.pv_comp_block[j].pv_max_power[t]*self.model.pv_comp_block[j].pv_module_power[t]*self.model.pv_comp_block[j].pv_charger_efficiency[t]\
                                             *self.model.pv_comp_block[j].pv_peak_mod[1])
            
            energy_creation += pyo.value(self.model.battery_comp_block[b].battery_current_discharge_power[t]*self.model.battery_comp_block[b].battery_discharging_efficiency[t] *self.model.battery_comp_block[b].battery_discharger_efficiency[t]\
                -self.model.battery_comp_block[b].battery_current_charge_power[t]\
                +self.model.grid_current_bought_power[t]- self.model.grid_current_sold_power[t]\
                -self.model.demand[t])    
                
        if energy_creation >= (0.001*(sum(pyo.value(self.model.demand[t]) for t in self.model.simulation_steps))):
            print('energy creation:',energy_creation)
        
        # for i in self.model.simulation_steps:
        #     txt = 'bought: {b:.2f} sold: {s:.2f}'
        #     print(txt.format(b = pyo.value(self.model.grid_current_bought_power[i]), s = pyo.value(self.model.grid_current_sold_power[i])))
            
        # for t in self.model.simulation_steps:
        #     expr = 0
        #     expr += self.model.pv_comp_block[b].pv_max_power[t]*self.model.pv_comp_block[b].pv_module_power[t]* self.model.pv_comp_block[b].pv_charger_efficiency[t]*self.model.pv_comp_block[b].pv_peak_mod[1]
        #     expr += self.model.battery_comp_block[b].battery_current_discharge_power[t] *self.model.battery_comp_block[b].battery_discharging_efficiency[t] *self.model.battery_comp_block[b].battery_discharger_efficiency[t] - self.model.battery_comp_block[b].battery_current_charge_power[t]
        #     expr += self.model.grid_current_bought_power[t]- self.model.grid_current_sold_power[t]
            
        #     print('supply:',pyo.value(expr),' demand: ',pyo.value(self.model.demand[t]))
            
        # for t in self.model.simulation_steps:
        #     if pyo.value(self.model.shortage_power[t]) > 0:
        #         expr = self.model.shortage_power[t]/self.model.demand[t]
        #         print('power shortage at time', t, ':', pyo.value(expr))
        # for b in range(len(self.sim.pv)):  
        #     b +=1
        #     for t in self.model.simulation_steps:
        #         expr = 0
        #         expr += self.model.pv_comp_block[b].pv_max_power[t]* self.model.pv_comp_block[b].pv_module_power[t]* self.model.pv_comp_block[b].pv_charger_efficiency[t]*self.model.pv_comp_block[b].pv_peak_mod[1]
        #         print('pv power at time:',t,':', pyo.value(expr))
        
        # for b in range(len(self.sim.pv)):  
        #     b +=1
        #     for t in self.model.simulation_steps:
        #         expr = 0
        #         expr += self.model.pv_comp_block[b].pv_max_power[t]* self.model.pv_comp_block[b].pv_module_power[t]* self.model.pv_comp_block[b].pv_charger_efficiency[t]*self.model.pv_comp_block[b].pv_peak_mod[1]
        #         print('pv array', b,' power at time:',t,':', pyo.value(expr))
            
        # for t in self.model.simulation_steps:
        #     time = int(t)
        #     txt = 'batery temp at time: {t:.0f}: +{temp:.15f}'
        #     temperature = pyo.value(self.model.battery_comp_block[b].battery_temp[t])
        #     print(txt.format(t = time, temp = temperature))
        
        # print('battery flow into battery and from battery into grid')
        # for t in self.model.simulation_steps:
        #     time = int(t)
        #     txt = 'battery power flow at time: {t:.0f}: +{c:.4f}  -{d:.4f}'
        #     charge = pyo.value(self.model.battery_comp_block[b].battery_current_charge_power[t]\
        #                         *self.model.battery_comp_block[b].battery_charger_efficiency[t] *self.model.battery_comp_block[b].battery_charging_efficiency[t])
        #     discharge = pyo.value(self.model.battery_comp_block[b].battery_current_discharge_power[t])#\
        #                           # *self.model.battery_comp_block[b].battery_discharging_efficiency[t] *self.model.battery_comp_block[b].battery_discharger_efficiency[t])
        #     print(txt.format(t = time, c = charge,d = discharge))
            
        #     SOC = pyo.value(self.model.battery_comp_block[b].battery_SOC[t])
        #     txt = 'SOC at time: {t:.0f}: {S:.3f}'
        #     print(txt.format(t = time, S = SOC))
        
        # print('attention:\n'\
        #       '-minimal_efficiency set to 0 in power_component and battery module. Might cause ipopt to fail')
        print('total costs:',round(self.total_costs_new,4)) 
        
    
    def get_opt_values(self):
        b = 1
        #get LCOEs
        self.pv_LCOE = list()
        self.LCOE_pv_old = list()
        # self.bat_LCOE = list()
        
        for i in range(len(self.sim.pv)):
            self.pv_LCOE.append(round(pyo.value(self.model.pv_comp_block[b].pv_cost)*1000 /self.sim.order_of_magnitude,4))
            self.LCOE_pv_old.append(round(pyo.value(self.model.pv_comp_block[b].pv_cost)*1000 /self.sim.order_of_magnitude,4))
        self.bat_LCOE = round(pyo.value(self.model.battery_comp_block[b].battery_charge_cost)*1000/self.sim.order_of_magnitude,4)
        #get power flows
        self.battery_state_of_charge = list()
        self.battery_flow = list()
        self.battery_charge_list = list()
        self.battery_discharge_list = list()
        self.pv_flow = list()
        for i in range(len(self.sim.pv)):
            self.pv_flow.append([])
        self.pv_power_unused = list()
        self.power_junct_flow =list()
        self.bought_power_list = list()
        self.sold_power_list = list()
        self.power_shortage_list = list()
        
        for t in self.model.simulation_steps:
            #pv
            for i in range(len(self.sim.pv)):
                peak_mod_workaround = [pyo.value(self.model.pv_comp_block[i+1].pv_peak_mod[1])]
                expr=peak_mod_workaround[0]*pyo.value(self.model.pv_comp_block[i+1].pv_max_power[t]*self.model.pv_comp_block[i+1].pv_module_power[t])*self.sim.order_of_magnitude
                self.pv_flow[i].append(expr)
                
            #unused pv power     --> add self.model.pv_comp_block[i+1].pv_peak_mod[1]*
            expr = sum(pyo.value((self.model.pv_comp_block[j+1].pv_peak_mod[1]*self.model.pv_comp_block[j+1].pv_max_power[t] \
                             -self.model.pv_comp_block[j+1].pv_max_power[t]*self.model.pv_comp_block[j+1].pv_module_power[t]\
                             *self.model.pv_comp_block[j+1].pv_peak_mod[1]))*self.sim.order_of_magnitude for j in range(len(self.sim.pv)))
                    
            self.pv_power_unused.append(expr)
            
            #battery
            self.battery_state_of_charge.append(pyo.value(self.model.battery_comp_block[b].battery_SOC[t]))
            
            expr = pyo.value(self.model.battery_comp_block[b].battery_current_charge_power[t] - self.model.battery_comp_block[b].battery_current_discharge_power[t]\
                             *self.model.battery_comp_block[b].battery_discharger_efficiency[t] *self.model.battery_comp_block[b].battery_discharging_efficiency[t])\
                             *self.sim.order_of_magnitude
            self.battery_flow.append(expr)
            
            self.battery_charge_list.append(pyo.value(self.model.battery_comp_block[b].battery_current_charge_power[t])*self.sim.order_of_magnitude)
            self.battery_discharge_list.append(pyo.value(self.model.battery_comp_block[b].battery_current_discharge_power[t])*self.sim.order_of_magnitude)
            #power junction
            expr = sum(pyo.value(self.model.pv_comp_block[j+1].pv_max_power[t]*self.model.pv_comp_block[j+1].pv_module_power[t]\
                                 *self.model.pv_comp_block[j+1].pv_charger_efficiency[t])*self.sim.order_of_magnitude\
                                   for j in range(len(self.sim.pv)))\
                             + pyo.value(self.model.grid_current_bought_power[t]- self.model.grid_current_sold_power[t]\
                             -self.model.demand[t])*self.sim.order_of_magnitude
            self.power_junct_flow.append(expr)
            
            #bought and sold amounts
            expr = pyo.value(self.model.grid_current_bought_power[t]) * self.sim.order_of_magnitude
            self.bought_power_list.append(expr)
            expr = pyo.value(self.model.grid_current_sold_power[t]) * self.sim.order_of_magnitude
            self.sold_power_list.append(expr)
            
            #power shortage
            expr = pyo.value(self.model.shortage_power[t]) * self.sim.order_of_magnitude
            self.power_shortage_list.append(expr)
            