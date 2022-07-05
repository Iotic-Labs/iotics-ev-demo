import random
import datetime as dt

class EvChargeOccupancyPredictor:
    # we _arbitrarily_ assume a betavariate 
    # distrib based on the hour of the day
    # different shape for 1h and 2h prediction
    def __init__(self):
        self.params_1h = []
        self.params_2h = []

        for i in range(0, 7):
            self.params_1h.append([5, 5])
        for i in range(7, 11):
            self.params_1h.append([2, 8])
        for i in range(11, 15):
            self.params_1h.append([8, 2])
        for i in range(15, 18):
            self.params_1h.append([2, 2])
        for i in range(18, 24):
            self.params_1h.append([5, 5])

        for i in range(0, 24):
            self.params_2h.append([.5, .5])

    @property
    def busy_forecast_h1_prob(self):
        p = self.params_1h[dt.datetime.now().hour]
        return random.betavariate(p[0], p[1])
    
    @property
    def busy_forecast_h2_prob(self):
        p = self.params_2h[dt.datetime.now().hour]
        return random.betavariate(p[0], p[1])
    
