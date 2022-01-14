import pandas
import data_loader

class Market():
    """Relevant methods to define the simulation day_ahead market profile or the fixed electricity buy and sell costs.

    Parameters
    ----------
    None : `None`

    Note
    ----
    - Class data_loader is integrated and its method LoadMarketData() to integrate csv day_ahead prices.
    - This method is called externally within the central method simulate() of the class simulation.
    
    """


    def __init__(self, day_ahead = False):

        self.day_ahead = day_ahead
        
        self.load_market_data = data_loader.LoadMarketData()
        
        self.market_data = None
        
        self.avg_buy_cost = None  #for LCOE calc in main


    def calculate(self):
        """Extracts market prices and summarizes them within an array in case of the day_ahead market prices or saves the 
        fixed selling and buying costs

        Parameters
        ----------
        None : `None`

        Returns
        -------
    
        """
        if not isinstance(self.market_data, pandas.core.series.Series):
            self.market_data = self.load_market_data.get_day_ahead_profile()
        
        if self.day_ahead:
            self.day_ahead_prices = self.market_data/1000
        else:
            #buy and sell prices in Wh
            self.buyprice = self.market_data.values[0]/1000
            self.sellprice = self.market_data.values[1]/1000
            
            self.avg_buy_cost = self.buyprice*1000
        
            