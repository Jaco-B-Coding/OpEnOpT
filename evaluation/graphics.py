import matplotlib.pyplot as plt
import numpy as np

class Graphics():

    def __init__(self, simulation, optimization):
        
        # Component specific parameter
        self.sim = simulation   
        self.opt = optimization
        
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
        
    def stack_plot(self, x_array, y_array, y_dict, dict_std,  y, secondary_y):
        """Relevant methods for the plotting stacked plots. Takes in x-Value array and y-array of
        of n dimension, where n is the amount of curves plotted

        Parameters
        ----------
        x_array : list of floats 
            list of x values. Must be equal for all curves
        y_array : list of floats
            list of load values
        y_param : n-dimensional dictionary
            dictionary of arrays containing curve y values
        label : list of strings
            list of label strings
        Returns
        -------        
        """
        self.x_array = x_array
        self.y_array = y_array
        self.y_dict = y_dict
        self.dict_std = dict_std
        self.y = y
        self.secondary_y = secondary_y
        self.std = True
        
        colors = [(0,0,0.9,0.3),(0,0.9,0,0.3),(0.9,0.0,0,0.3)]
        ecolors = [(0,0,0.5,1),(0,0.5,0,1), (0.5,0,0,1)]
        
        self.x_label = 'Day hour [h]'
        self.y1_label = 'Power [kWh]'
        self.y2_label = 'Battery state of charge [-]'
        
        
        fig, ax = plt.subplots()         
        ax2 = ax.twinx()
        
        ax.stackplot(self.x_array, self.y_dict.values(),
               labels=self.y_dict.keys(), colors = colors)
       
        ax.plot(self.x_array, self.y, label = 'load', color = 'red', linewidth = 1, linestyle ='--')
        
        if self.std :
            #plot standard deviation
            j=0
            ylist = None
            for i in  self.y_dict.values(): #self.dict_means:
                if j == 0:
                    ylist=np.array(i)
                else:
                    ylist += np.array(i)
                if self.std == True:  
                    ax.errorbar(self.x_array, ylist, yerr=self.dict_std[j], linestyle='None', marker='None', ecolor = ecolors[j],  elinewidth=2)
                j +=1
        
        # secondsary axis
        ax2.plot(self.x_array, self.secondary_y, label = 'SOC', linestyle = '-.', color = 'black')
        ax2.axhline(y = 0.0, color = (0,0,0,0.3), linestyle = '-.')
        ax2.axhline(y = 1.0, color = (0,0,0,0.3), linestyle = '-.')
        
        ax.set_ylim([0, max(self.y)*1.7])
        ax.set_xlim([0,23])
        plt.xticks(np.arange(0, 23, step=2))
        
        ax2.set_ylim([-1.2, 1.2])
        
        # ask matplotlib for the plotted objects and their labels
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        legend1 = ax2.legend(lines , labels , loc=2)
        ax2.add_artist(legend1)
        ax2.legend(lines2, labels2, loc=1)
        
        ax.set_xlabel(self.x_label)
        ax2.set_ylabel(self.y2_label)  
        ax.set_ylabel(self.y1_label)        
        plt.show()
        
        # ax.stackplot(self.x_array, self.y_dict.values(),
        #       labels=self.y_dict.keys())
        # ax.plot(self.x_array, self.y_array)
        # ax.legend(loc='upper left')
        # ax.set_xlabel(self.xlabel)
        # ax.set_ylabel(self.ylabel)
        
        # plt.show()
           
    def scatter_hist(self, x, y, ax, ax_histx, ax_histy, x_axis_title):
        # no labels
        # ax_histx.tick_params(axis="x", labelbottom=False)
        # ax_histy.tick_params(axis="y", labelleft=False)
    
        # the scatter plot:
        ax.scatter(x, y)
        xtitle = x_axis_title.replace("_"," ")
        # ax.title('optimization objective value over {}'.format(x_axis_title))      
        # ax.xlabel(xtitle)
        # ax.ylabel('optimization value')
    
        # now determine nice limits by hand:
        binwidth = 0.1
        xymax = np.max(np.abs(x))
        lim = (int(xymax/binwidth) + 1) * binwidth
        # limy =  np.max(np.abs(y))*(1+binwidth)
    
        # bins = np.arange(0, lim + binwidth, binwidth)
        # ax_histx.hist(x, bins=bins)
        # ax_histy.hist(y, bins=bins, orientation='horizontal')
        
        plt.show()


    def plot_load_data(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.load_power_demand, '-b', label='power load demand')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_pv_energy(self):
        self.figure_format()
        
        fig, ax1 = plt.subplots(figsize=self.figsize) 

        x = 0
        for i in range(len(self.sim.pv)):
            ax1.plot(self.sim.timeindex, self.sim.pv_power[i], color = (x, 0.2, 0.5), label='pv power')
            if self.opt:
                ax1.plot(self.sim.timeindex, self.opt.pv_max_possible_power[i], linestyle='dashed', color=(x, 0.2, 0.5), label='pv max power')
            x += 0.3
            if x > 1:
                x = 1
        #plt.plot(self.sim.timeindex, self.sim.pv_power_loss, 'r', label='pv power loss')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_controller_energy(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.pv_charger_power, '-b', label='pv_charger power')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_main_energy(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.power_junction_power, '-b', label='power junction')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_battery_energy(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.battery_management_power, '-g', label='bms power')
        plt.plot(self.sim.timeindex, self.sim.battery_power, '-b', label='battery power')
        plt.plot(self.sim.timeindex, self.sim.battery_power_loss, '-r', label='battery power loss')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.2), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_battery_eta(self):
        self.figure_format()

        fig, ax1 = plt.subplots(figsize=self.figsize)        
        ax1.plot(self.sim.timeindex, self.sim.battery_power_eta, 'ob', label='battery eta')
        ax1.set_ylabel('Efficiency [-]')
        ax1.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        ax2 = ax1.twinx()   
        ax2.plot(self.sim.timeindex, self.sim.battery_management_power_eta, 'xg', label='bms eta')
        ax2.set_xlabel('Time [date]')
        ax2.set_ylabel('Efficiency [-]')
        ax2.legend(bbox_to_anchor=(0.9, 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()
        
    def plot_battery_soc(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        # plt.plot(self.sim.timeindex, self.opt.battery_state_of_charge, '-g', label='battery SoC')
        plt.plot(self.sim.timeindex, self.sim.battery_state_of_charge, '-b', label='battery SoC')
        plt.xlabel('Time [date]')
        plt.ylabel('SoC [-]')
        plt.legend(bbox_to_anchor=(0., 1.2), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_components_temperature(self):
        self.figure_format()

        fig, ax1 = plt.subplots(figsize=self.figsize) 
        ax1.plot(self.sim.timeindex, self.sim.battery_temperature, '-b', label='temperature battery')
        ax1.set_ylabel('Temperature battery [C]')
        ax1.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        ax2 = ax1.twinx() 
        ax2.plot(self.sim.timeindex, self.sim.pv_temperature, ':g', label='temperature pv cell')
        ax2.set_xlabel('Time [date]')
        ax2.set_ylabel('Temperature pv [C]')
        ax2.legend(bbox_to_anchor=(0.9, 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_components_sod(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        
        x = 0
        for i in range(len(self.sim.pv)):
            plt.plot(self.sim.timeindex, self.sim.photovoltaic_state_of_destruction[i], color= (x, 0.2, 0.5 ), label='pv SoC')
            x += 0.3
            if x > 1:
                x = 1
                
        plt.plot(self.sim.timeindex, self.sim.battery_state_of_destruction, '-g', label='battery SoD')
        plt.plot(self.sim.timeindex, self.sim.pv_charger_state_of_destruction, '-r', label='pv_charger SoD')
        plt.plot(self.sim.timeindex, self.sim.battery_management_state_of_destruction, '-r', label='bms SoD')
        plt.xlabel('Time [date]')
        plt.ylabel('SoD [-]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=5)
        plt.grid()
        plt.show()
        
    def plot_sold_power(self):
        self.figure_format()
        
        fig, ax1 = plt.subplots(figsize=self.figsize)
        line1, = ax1.plot(self.sim.timeindex, self.sim.battery_power, '-b', label='battery power')
        line2, = ax1.plot(self.sim.timeindex, self.opt.bought_power_list, '-r', label='bought power')
        line3, = ax1.plot(self.sim.timeindex, self.opt.power_shortage_list, '-y', label='shortage power')
        line4, = ax1.plot(self.sim.timeindex, self.opt.sold_power_list, '-g', label='Sold power')
        ax2 = ax1.twinx()
        if self.sim.day_ahead_market:
            ax2.plot(self.sim.timeindex, self.opt.buyprice, '-k', label='day ahead price')
        else:
            ax2.plot(self.sim.timeindex, self.opt.buyprice, '--k', label='buy price')
            ax2.plot(self.sim.timeindex, self.opt.sellprice, '-.k', label='sell price')
        ax2.set_ylabel('day ahead price [€/kWh]')
        ax1.set_xlabel('Time [date]')
        ax1.set_ylabel('Power [W]')
        ax1.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=5)
        ax2.legend(bbox_to_anchor=(0., 1.2), loc=2, borderaxespad=0., ncol=4)
        plt.grid()
        plt.show()
                
    def plot_sens_analysis(self, obj_values, **kwargs):
        
        fig_list = list()
        gs_list = list()
        ax_list = list()
        ax_histx_list = list()
        ax_histy_list = list()
        
        fig_iterator = 0
        for key, value in kwargs.items():    
            print('plotting scatterplot number', fig_iterator )
            
            # start with a square Figure
            fig_list.append( plt.figure(figsize=(8, 8)))
            
            # Add a gridspec with two rows and two columns and a ratio of 2 to 7 between
            # the size of the marginal axes and the main axes in both directions.
            # Also adjust the subplot parameters for a square plot.
            gs_list.append(fig_list[fig_iterator].add_gridspec(2, 2,  width_ratios=(7, 2), height_ratios=(2, 7),
                                  left=0.1, right=0.9, bottom=0.1, top=0.9,
                                  wspace=0.05, hspace=0.05))
            
            ax_list.append(fig_list[fig_iterator].add_subplot(gs_list[fig_iterator][1, 0]))
            ax_histx_list.append(fig_list[fig_iterator].add_subplot(gs_list[fig_iterator][0, 0], sharex=ax_list[fig_iterator]))
            ax_histy_list.append(fig_list[fig_iterator].add_subplot(gs_list[fig_iterator][1, 1], sharey=ax_list[fig_iterator]))
            # use the scatter plot function
            self.scatter_hist(value, obj_values, ax_list[fig_iterator], ax_histx_list[fig_iterator], ax_histy_list[fig_iterator], key)
            
            fig_iterator +=1
         
       
            