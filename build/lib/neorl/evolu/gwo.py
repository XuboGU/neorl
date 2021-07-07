# -*- coding: utf-8 -*-
#"""
#Created on Thu Dec  3 14:42:29 2020
#
#@author: Majdi
#"""


import random
import numpy as np
import math
#from solution import solution
import time
import joblib

class GWO(object):
    """
    Grey Wolf Optimizer
    
    :param mode: (str) problem type, either "min" for minimization problem or "max" for maximization
    :param bounds: (dict) input parameter type and lower/upper bounds in dictionary form. Example: ``bounds={'x1': ['int', 1, 4], 'x2': ['float', 0.1, 0.8], 'x3': ['float', 2.2, 6.2]}``
    :param fit: (function) the fitness function 
    :param nwolves: (int): number of the grey wolves in the group
    :param ncores: (int) number of parallel processors (must be ``<= nwolves``)
    :param seed: (int) random seed for sampling
    """
    def __init__(self, mode, bounds, fit, nwolves=5, ncores=1, seed=None):
        
        if seed:
            random.seed(seed)
            np.random.seed(seed)
        
        assert ncores <= nwolves, '--error: ncores ({}) must be less than or equal than nwolves ({})'.format(ncores, nwolves)
        
        #--mir
        self.mode=mode
        if mode == 'min':
            self.fit=fit
        elif mode == 'max':
            def fitness_wrapper(*args, **kwargs):
                return -fit(*args, **kwargs) 
            self.fit=fitness_wrapper
        else:
            raise ValueError('--error: The mode entered by user is invalid, use either `min` or `max`')
            
        self.bounds=bounds
        self.ncores = ncores
        self.nwolves=nwolves
        self.dim = len(bounds)
        
        self.lb=[self.bounds[item][1] for item in self.bounds]
        self.ub=[self.bounds[item][2] for item in self.bounds]

    def init_sample(self, bounds):
    
        indv=[]
        for key in bounds:
            if bounds[key][0] == 'int':
                indv.append(random.randint(bounds[key][1], bounds[key][2]))
            elif bounds[key][0] == 'float':
                indv.append(random.uniform(bounds[key][1], bounds[key][2]))
            elif bounds[key][0] == 'grid':
                indv.append(random.sample(bounds[key][1],1)[0])
            else:
                raise Exception ('unknown data type is given, either int, float, or grid are allowed for parameter bounds')   
        return indv
    
    def ensure_bounds(self, vec): # bounds check

        vec_new = []

        for i, (key, val) in enumerate(self.bounds.items()):
            # less than minimum 
            if vec[i] < self.bounds[key][1]:
                vec_new.append(self.bounds[key][1])
            # more than maximum
            if vec[i] > self.bounds[key][2]:
                vec_new.append(self.bounds[key][2])
            # fine
            if self.bounds[key][1] <= vec[i] <= self.bounds[key][2]:
                vec_new.append(vec[i])
        
        return vec_new
    
    def fit_worker(self, x):
        #This worker is for parallel calculations of the GWO
        
        # Clip the wolf with position outside the lower/upper bounds and return same position
        x=self.ensure_bounds(x)
        
        # Calculate objective function for each search agent
        fitness = self.fit(x)
        
        return fitness

    def evolute(self, ngen, x0=None, verbose=True):
        """
        This function evolutes the GWO algorithm for number of generations.
        
        :param ngen: (int) number of generations to evolute
        :param x0: (list of lists) initial position of the wolves (must be of same size as ``nwolves``)
        :param verbose: (bool) print statistics to screen
        
        :return: (dict) dictionary containing major GWO search results
        """
        self.history = {'alpha_wolf':[], 'beta_wolf':[], 'delta_wolf': [], 'fitness':[]}
        self.fitness_best=float("inf") 
        self.verbose=verbose
        self.Positions = np.zeros((self.nwolves, self.dim))
        if x0:
            assert len(x0) == self.nwolves, '--error: the length of x0 ({}) MUST equal the number of wolves in the group ({})'.format(len(x0), self.nwolves)
            for i in range(self.nwolves):
                self.Positions[i,:] = x0[i]
        else:
            #self.Positions=self.init_sample(self.bounds)  #TODO, update GWO laterfor mixed-integer optimisation
            # Initialize the positions of search agents
            
            for i in range(self.dim):
                self.Positions[:, i] = (np.random.uniform(0, 1, self.nwolves) * (self.ub[i] - self.lb[i]) + self.lb[i])       
 
        # initialize alpha, beta, and delta_pos
        Alpha_pos = np.zeros(self.dim)
        Alpha_score = float("inf")  #GWO is built to minimize
    
        Beta_pos = np.zeros(self.dim)
        Beta_score = float("inf")  #GWO is built to minimize
    
        Delta_pos = np.zeros(self.dim)
        Delta_score = float("inf") #GWO is built to minimize
           
        with joblib.Parallel(n_jobs=self.ncores) as parallel:
            
            for l in range(0, ngen):
                
                #---------------------
                # Fitness calcs
                #---------------------
                core_lst=[]
                for case in range (0, self.Positions.shape[0]):
                    core_lst.append(self.Positions[case, :])
            
                if self.ncores > 1:

                    with joblib.Parallel(n_jobs=self.ncores) as parallel:
                        fitness=parallel(joblib.delayed(self.fit_worker)(item) for item in core_lst)
                        
                else:
                    fitness=[]
                    for item in core_lst:
                        fitness.append(self.fit_worker(item))  
                        
                #----------------------
                #  Update wolf scores
                #----------------------
                #Loop through the fitness list and update the score of alpha, beta, gamma, and omega!
                for i, fits in enumerate(fitness):
                    # Update Alpha, Beta, and Delta
                    if fits < Alpha_score:
                        Delta_score = Beta_score  # Update delte
                        Delta_pos = Beta_pos.copy()
                        Beta_score = Alpha_score  # Update beta
                        Beta_pos = Alpha_pos.copy()
                        Alpha_score = fits
                        # Update alpha
                        Alpha_pos = self.Positions[i, :].copy()
        
                    if fits > Alpha_score and fits < Beta_score:
                        Delta_score = Beta_score  # Update delte
                        Delta_pos = Beta_pos.copy()
                        Beta_score = fits  # Update beta
                        Beta_pos = self.Positions[i, :].copy()
        
                    if fits > Alpha_score and fits > Beta_score and fits < Delta_score:
                        Delta_score = fits  # Update delta
                        Delta_pos = self.Positions[i, :].copy()
                    
                    #save the best of the best!!!
                    if fits < self.fitness_best:
                        self.fitness_best=fits
                        self.x_best=self.Positions[i, :].copy()
                    
                    
                self.history['alpha_wolf'].append(Alpha_score)
                self.history['beta_wolf'].append(Beta_score)
                self.history['delta_wolf'].append(Delta_score)
                
                a = 2 - l * ((2) / ngen)
                # a decreases linearly from 2 to 0
                
                #--------------------------------
                # Position update loop
                #--------------------------------
                # Update the position of search wolves
                for i in range(0, self.nwolves):
                    for j in range(0, self.dim):
        
                        r1 = random.random()  # r1 is a random number in [0,1]
                        r2 = random.random()  # r2 is a random number in [0,1]
        
                        A1 = 2 * a * r1 - a
                        # Equation (3.3)
                        C1 = 2 * r2
                        # Equation (3.4)
        
                        D_alpha = abs(C1 * Alpha_pos[j] - self.Positions[i, j])
                        # Equation (3.5)-part 1
                        X1 = Alpha_pos[j] - A1 * D_alpha
                        # Equation (3.6)-part 1
        
                        r1 = random.random()
                        r2 = random.random()
        
                        A2 = 2 * a * r1 - a
                        # Equation (3.3)
                        C2 = 2 * r2
                        # Equation (3.4)
        
                        D_beta = abs(C2 * Beta_pos[j] - self.Positions[i, j])
                        # Equation (3.5)-part 2
                        X2 = Beta_pos[j] - A2 * D_beta
                        # Equation (3.6)-part 2
        
                        r1 = random.random()
                        r2 = random.random()
        
                        A3 = 2 * a * r1 - a
                        # Equation (3.3)
                        C3 = 2 * r2
                        # Equation (3.4)
        
                        D_delta = abs(C3 * Delta_pos[j] - self.Positions[i, j])
                        # Equation (3.5)-part 3
                        X3 = Delta_pos[j] - A3 * D_delta
                        # Equation (3.5)-part 3
        
                        self.Positions[i, j] = (X1 + X2 + X3) / 3  # Equation (3.7)
                    
                    self.Positions[i,:]=self.ensure_bounds(self.Positions[i,:])
                 
                #--mir
                if self.mode=='max':
                    self.fitness_best_correct=-self.fitness_best
                else:
                    self.fitness_best_correct=self.fitness_best
                
                # Print statistics
                if self.verbose and i % self.nwolves:
                    print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
                    print('GWO step {}/{}, nwolves={}, Ncores={}'.format((l+1)*self.nwolves, ngen*self.nwolves, self.nwolves, self.ncores))
                    print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
                    print('Best Group Fitness:', np.round(self.fitness_best_correct,6))
                    print('Best Group Position:', np.round(self.x_best,6))
                    print('Alpha wolf Fitness:', np.round(Alpha_score,6) if self.mode is 'min' else -np.round(Alpha_score,6))
                    print('Beta wolf Fitness:', np.round(Beta_score,6) if self.mode is 'min' else -np.round(Beta_score,6))
                    print('Delta wolf Fitness:', np.round(Delta_score,6) if self.mode is 'min' else -np.round(Delta_score,6))
                    print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
    
        
                self.history['fitness'].append(self.fitness_best)

        if self.verbose:
            print('------------------------ GWO Summary --------------------------')
            print('Best fitness (y) found:', self.fitness_best_correct)
            print('Best individual (x) found:', self.x_best)
            print('--------------------------------------------------------------')  
        
        #--mir
        if self.mode=='max':
            self.history['alpha_wolf']=[-item for item in self.history['alpha_wolf']]
            self.history['beta_wolf']=[-item for item in self.history['beta_wolf']]
            self.history['delta_wolf']=[-item for item in self.history['delta_wolf']]
            self.history['fitness']=[-item for item in self.history['fitness']]
            
        return self.x_best, self.fitness_best_correct, self.history