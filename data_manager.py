# -*- coding: utf-8 -*-
"""
Created on Fri Sep 10 11:14:09 2021

@author: Giampiero
"""

import os
import pandas as pd
from collections import OrderedDict
 
def save_model_data(sim = None, opt= None, tech = None, sens = None):
    
    #open new directory where new model outup is saved
    modID = 'data/SaveFiles/' + str(sim.simulation_steps)+'PV' + str(round(sim.pv_peak_power[0]))+ 'bat' + str(round(sim.battery_capacity)) 
    
    if opt:
        modID += opt.solver_type+'Opt'
        if opt.opt_pv_size:
            modID += '_PV'
        if opt.opt_batt_size:
            modID += '_bat'
    if sens:
        modID += '_sens' + str(sens.sens_iterations+1)
    
    if not os.path.exists(modID):
        os.makedirs(modID)
        print("Created Directory : ", modID)
    else:
        print("Directory already existed : ", modID)
    
    # Summarize and save environmental data
    results_env = pd.DataFrame(
                  data=OrderedDict({'sun_elevation':sim.env.sun_position_pvlib['elevation'],
                                    'sun_azimuth':sim.env.sun_position_pvlib['azimuth'],
                                    'sun_angle_of_incident':sim.env.sun_aoi_pvlib,                               
                                    'sun_ghi':sim.env.sun_ghi,
                                    'sun_dhi':sim.env.sun_dhi,
                                    'sun_bni':sim.env.sun_bni,
                                    'temperature_ambient':sim.env.temperature_ambient,
                                    'windspeed':sim.env.windspeed}), index=sim.timeindex)
    path =modID+ '/env_data.csv'
    results_env.to_csv( path ,index=False)
    
    if opt:
        # Summarize and save power flows                                                                                   --> make it so it accepts power multidimensional lists for e.g. pv_power flow
        results_power = pd.DataFrame(
                        data=OrderedDict({'sun_power_poa_global':sim.env.sun_irradiance_pvlib['poa_global'],
                                          'sun_power_poa_direct':sim.env.sun_irradiance_pvlib['poa_direct'],
                                          'sun_power_poa_diffuse':sim.env.sun_irradiance_pvlib['poa_diffuse'],
                                          'pv_power':sim.pv_power, 
                                          'pv_charger_power':sim.pv_charger_power,
                                          'pv_charger_efficiency':opt.pv_charger_efficiency,                        #
                                          'load_power':sim.load_power_demand,
                                          'power_junction_power':opt.power_junct_flow,                          ##
                                          'battery_management_power':sim.battery_management_power,                  #
                                          'BMS_charger_efficiency':opt.battery_charger_efficiency,       
                                          'BMS_discharger_efficiency':opt.battery_discharger_efficiency,  
                                          'battery_power':sim.battery_power,                                         #
                                          'battery_charging_efficiency':opt.battery_charging_efficiency,            
                                          'battery_discharging_efficiency':opt.battery_discharging_efficiency,      
                                          'battery_soc':sim.battery_state_of_charge,                                #
                                          'pv_LCOE':opt.pv_LCOE,
                                          'bat_LCOE':opt.bat_LCOE,
                                          'pv_peak_mod':sim.pv_peak_change,
                                          'bat_peak_mod':sim.bat_capa_change,
                                          'bought_power':opt.bought_power_list,
                                          'sold_power':opt.sold_power_list}), index=sim.timeindex)      
    else:
        # Summarize and save power flows                                                                                   --> make it so it accepts power multidimensional lists for e.g. pv_power flow
        results_power = pd.DataFrame(
                        data=OrderedDict({'sun_power_poa_global':sim.env.sun_irradiance_pvlib['poa_global'],
                                          'sun_power_poa_direct':sim.env.sun_irradiance_pvlib['poa_direct'],
                                          'sun_power_poa_diffuse':sim.env.sun_irradiance_pvlib['poa_diffuse'],
                                          'pv_power':sim.pv_power, 
                                          'pv_charger_power':sim.pv_charger_power,
                                          'pv_charger_efficiency':sim.pv_charger_efficiency,
                                          'load_power':sim.load_power_demand,
                                          'power_junction_power':sim.power_junction_power, 
                                          'battery_management_power':sim.battery_management_power, 
                                          'BMS_charger_efficiency':sim.battery_management_charger_efficiency,
                                          'BMS_discharger_efficiency':sim.battery_management_discharger_efficiency,
                                          'battery_power':sim.battery_power,
                                          'battery_charging_efficiency':sim.battery_charging_efficiency,
                                          'battery_discharging_efficiency':sim.battery_discharging_efficiency,
                                          'battery_soc':sim.battery_state_of_charge}), index=sim.timeindex)     
        
    
    path =  modID+ '/power_data.csv' 
    results_power.to_csv(path,index=False)
    
    #Summarize and save sensitivity Analysis data
    if sens:
        # Summarize sensitivity data
        sens_index = range(sens.sens_iterations)
        results_sens = pd.DataFrame(
                        data=OrderedDict({'battery_inv_costs':sens.battery_investment_costs,
                                          'pv_inv_costs':sens.pv_investment_costs,
                                          'total_load':sens.total_load,
                                          'opt_objective':sens.opt_obj,
                                          'bat_capa':sens.pv_peak,
                                          'pv_peak':sens.batt_capa,                                      
                                          'runtime':tech.runtime,}), index=sens_index)
        path =  modID+ '/sens_data.csv' 
        results_sens.to_csv(path ,index=False)
    
    # #Summarize and save relevant data for comparison analysis
    # results_comp = pd.DataFrame(
    #                     data=OrderedDict({'runtime':tech.runtime
    #                                   }), index=sim.timeindex)
    # path =  modID+ '/comparison_data.csv' 
    # results_comp.to_csv(path ,index=False)
        
    
def load_model_data(path = 'data/SaveFiles/power_data.csv'):

    power_data = pd.read_csv(path)  
    pvPower = power_data['pv_power'].to_numpy()[1]
    
    print('pv_Power', pvPower)