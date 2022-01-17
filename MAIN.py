import pandas as pd
from collections import OrderedDict
from datetime import datetime
 
from simulation import Simulation
from evaluation.sensitivity import Sensitivity_analysis
from evaluation.economics import Economics
from evaluation.performance import Performance
from evaluation.dispatch_eval import Dispatch_Eval
from evaluation.graphics import Graphics
from data_manager import *

from optimization.PyomoMain import Optimization_model

def Main():
    #%% Define simulation settings 
    # Simulation timestep in seconds
    timestep = 60*60
    # Simulation number of timestep
    simulation_steps = 24*31*1
    #declare if run needs to be saved
    save_data = False
    
    #%% Create Simulation instance
    sim = Simulation(simulation_steps=simulation_steps,
                     timestep=timestep)
    plot_simulation_results = True
    
    #Call Main Simulation methods
    sim.simulate()  
    
    #%%Define pyomo optimization settings
    #declare whether model needs to be optimized with Pyomo-model addon
    optimization = True
    opt_model = None
    #toggle multiobjective optimsation objectives
    opt_pv = True  
    opt_bat = True
    #maximal number of iterations per optimisation run
    max_opt_iterations = 30
    
    #create optimization instance
    if optimization:
        opt_model = Optimization_model(
            simulation_steps = simulation_steps, 
            time_step = timestep,
            simulation = sim, 
            opt_pv_size = opt_pv,
            opt_batt_size = opt_bat)
    
    #%% initialize technical performance instance
    tech = Performance(simulation=sim,
                        opt_model = opt_model,
                        timestep=timestep,
                        optimization = optimization)
    
    #%% inititalize dispatch evaluation instance
    dispatch = Dispatch_Eval(simulation=sim,
                        opt_model = opt_model,
                        timestep=timestep,
                        optimization = optimization)
    
    #%%Define sensitivity analysis settings
    sensitivity_analysis = False
    max_sens_samples = 20
    
    #create sensitivity analysis instance
    if sensitivity_analysis:
        sens = Sensitivity_analysis(simulation = sim,
                                    optimization = opt_model,
                                    randomize_method = 1)
        #declare input variables that need be changed
        sens_pv_investment_costs = list()
        for i in range(len(sim.pv)):
            sens_pv_investment_costs.append(sim.pv[i].investment_costs_specific)
        sens_battery_investment_costs = sim.battery.investment_costs_specific
        sens_load = sim.load_power_demand
        
    else:
        max_sens_samples = 1
    
    #%%
    #%% Main optimization method 
    sens_iterations = 0
    #loop for sensitivity analysis
    while sens_iterations < max_sens_samples:
        #get model start time to calculate program run-time
        model_start = datetime.now()
        model_start_time = model_start.strftime("%H:%M:%S")
        
        if sensitivity_analysis:
            print('---------------------------------------------------------')
            print('sensitivity simulation number', sens_iterations)
        #iterate over optimization procedure if needed
        iteration_needed = True
        econ_recalc_needed = True
        iteration = 0
        
        sens_iterations +=1
        
        #loop for optimization run
        while iteration_needed:
            iteration_needed = False
        
            # Initialize economic analysis instancees with simulation values for each sensitivity iteration
            if econ_recalc_needed: 
                #reset flag
                econ_recalc_needed = False
                eco_pv = list()
                for i in range(len(sim.pv)):
                    eco_pv_array = Economics(sim.pv[i], 
                                            sim.photovoltaic_replacement[i], 
                                            sim.pv_tot_energy[i],
                                            timestep,
                                            simulation_steps)
                    eco_pv.append(eco_pv_array)
                    
                eco_pv_charger = Economics(sim.pv_charger, 
                                            sim.pv_charger_replacement, 
                                            sim.pv_arrays_tot_energy,
                                            timestep,
                                            simulation_steps)
                eco_bms = Economics(sim.battery_management, 
                                            sim.battery_management_replacement,
                                            sim.battery_management_tot_energy,
                                            timestep,
                                            simulation_steps)
                eco_bat = Economics(sim.battery, 
                                            sim.battery_replacement,
                                            sim.battery_tot_energy,
                                            timestep,
                                            simulation_steps)
                #run economics module to obtain LCOEs to pass to pyomo optimization model
                for i in range(len(sim.pv)):
                    eco_pv[i].calculate()
                
                eco_pv_charger.calculate()
               
                eco_bms.calculate()
                
                eco_bat.calculate()
                
            #calculate technical preformance
            tech.calculate()
            
            #exit iteration loop if no optimization of model selected
            if not optimization:
                print('---------------------------------------------------------')
                print('no optimization selected')
                print('---------------------------------------------------------')
                break
            
            else:
                #run optimization
                #update optimisation model economical data                
                opt_model.update_model_data(eco_pv = eco_pv, 
                                            eco_bat = eco_bat,
                                            eco_charger = eco_pv_charger,
                                            eco_bms = eco_bms)
                #initialize optimisation and run it
                opt_model.init_model()
                opt_model.optimize_model()                
                
                #rerun simulaiton model with optimization data and obtain new component efficiencies and SODs    
                sim.update_simulation_data(opt_model.pv_flow, 
                                           opt_model.battery_flow, 
                                           opt_model.power_junct_flow,
                                           opt_model.pv_peak_mod_list,
                                           opt_model.batt_peak_mod,
                                           opt_model.bought_power_list)
                
                if opt_pv:
                    opt_model.update = False
                
                #calculate technical preformance
                tech.calculate()
                
                #get average daily power composition for the dispatch analysis
                dispatch.get_daily_power_mix(1,1)    
            
                #check whether deviation in costs between iterations is lower than threshold. If not rerun optimization
                if opt_model.check_iteration_deviation():
                    iteration_needed = True
                    
                #go into next iteration if needed
                if iteration_needed:
                    iteration += 1
                    
                    if iteration >= max_opt_iterations:
                        print('---------------------------------------------------------')
                        print('Caution: maximal iteration thrreshold passed. Exiting loop')
                        break
                    print('---------------------------------------------------------')
                    print("iteration", iteration, ": Rerunning model simulation and optimization")
        
        #get model optimization end time
        model_end = datetime.now()
        model_end_time = model_end.strftime("%H:%M:%S")       
        total_elapsed_time = (model_end.hour - model_start.hour) * 60 + model_end.minute - model_start.minute + (model_end.second-model_start.second)/60
        
        print('-----------Optimization duration-----------')
        print("Model optimization End Time =", model_end_time)
        print('total elapsed time [min]', total_elapsed_time)
        
        tech.get_runtime(total_elapsed_time)
        
        #%% 
        #%% Simulation results
        #plot results for first and unaltered simulation (and optimization) run
        if sens_iterations == 1:
            
            #%% Simulation evaluation and plots
            #create graphics model
            graph = Graphics(sim, opt_model)        
            # Graphics
            if plot_simulation_results:
                graph = Graphics(sim, opt_model)
                graph.plot_load_data()
                graph.plot_pv_energy()
                graph.plot_battery_soc()
                graph.plot_components_sod()
                if opt_model:
                    graph.plot_sold_power()
                    #plot dispatch schedule
                    graph.stack_plot(dispatch.day_hours,
                                     dispatch.load_power,
                                     dispatch.power_mix,
                                     dispatch.mstd,
                                     dispatch.load_power,
                                     dispatch.mean_SOC)
                    
                ## print technical performance
                tech.plot_cut_off_days()
                tech.plot_soc_days()
                # Print main technical objective results
                tech.print_technical_objective_functions()
                if optimization:
                    for i in range(len(sim.pv)):
                        print("LCOE_PV",i,":",opt_model.pv_LCOE[i])
                    print("LCOE_bat:",opt_model.bat_LCOE)
                else:
                    for i in range(len(eco_pv)):
                        print("LCOE_PV",i,":",round(eco_pv[i].levelized_costs,3))
                    print("LCOE_bat:",round(eco_bat.levelized_costs,3))
                
                if optimization:
                    #Sum of each component LCoE
                    #from energy system
                    LCoE = ((sum(sim.pv_charger_power)-sum(tech.power_pv_unused))/sum(sim.load_power_demand))*\
                            opt_model.pv_LCOE[i] 
                            
                    #from grid
                    LCoE += (tech.tot_power_bought)/sum(sim.load_power_demand)*sim.market.avg_buy_cost
                else:
                    LCoE = (sum(eco_pv[i].annuity_total_levelized_costs for i in range(len(eco_pv)))\
                            + eco_pv_charger.annuity_total_levelized_costs \
                            + eco_bms.annuity_total_levelized_costs \
                            + eco_bat.annuity_total_levelized_costs) \
                            / (((sum(sim.pv_tot_energy)-sum(tech.power_pv_unused))) *1000*(timestep/3600)/1000 / (simulation_steps*(timestep/3600)/8760))
                
                print('---------------------------------------------------------')
                print('Objective functions - Technical')
                print('---------------------------------------------------------')
                if optimization:
                   print('total load [MWh] =', sum(sim.load_power_demand)/10**6)
                   print('total RES Power used [MWh] =', (sum(sim.load_power_demand) - tech.tot_power_bought -sum(opt_model.power_shortage_list))/10**6)
                   print('total shortage power [MWh]=', sum(opt_model.power_shortage_list)/10**6)
                   print('total bought [MWh]=', tech.tot_power_bought/10**6)
                print('LCoE [$/kWh] =', round(LCoE,4))
                print('---------------------------------------------------------')    
     
        #%%sensitivity evaluation   
        if sensitivity_analysis:
            #save simulation data for current sensitivity iteration
            sens.save_sim_data(sim, opt_model)
            
            if sens_iterations < max_sens_samples:
                # Create new Simulation instance
                sim = Simulation(simulation_steps=simulation_steps,
                                 timestep=timestep)
                #Call Main Simulation methods
                sim.simulate()  
                
                #declare what input parameters shall be randomized and get a randomized sample
                for i in range(len(sim.pv)):
                    sim.pv[i].investment_costs_specific = sens.generate_random_sample(sample_input=sens_pv_investment_costs[i],
                                                                       max_deviation=0.2)
                sim.load_power_demand = sens.generate_random_sample(sample_input=sens_load,
                                                                       max_deviation=0.2)
                sim.battery.investment_costs_specific = sens.generate_random_sample(sample_input=sens_battery_investment_costs,
                                                                       max_deviation=0.5)
                
                #create new opt_model with changed input data
                opt_model = Optimization_model(
                    simulation_steps = simulation_steps, 
                    time_step = timestep,
                    simulation = sim, 
                    opt_pv_size = opt_pv,
                    opt_batt_size = opt_bat)
            
            #print results of sensitivity anylysis if laast iteration
            if sens_iterations == max_sens_samples:
                print('-----plotting results-----')
                graph.plot_sens_analysis(obj_values =  sens.opt_obj,
                                         battery_inv_costs = sens.battery_investment_costs,
                                            pv_inv_costs = sens.pv_investment_costs,
                                            total_load = sens.total_load)
    if save_data:
        if sensitivity_analysis:
            save_model_data(sim = sim, opt = opt_model, tech = tech, sens = sens)
        elif optimization: 
            save_model_data(sim = sim, opt = opt_model, tech = tech)    
        else:
            save_model_data(sim = sim, tech = tech)         
    
#run code with try exception handling for debugging
try:
    main = Main()
    print('exited normally')
except (RuntimeError) as error:
    print('Runtime Error ')
    
           
