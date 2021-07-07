# -*- coding: utf-8 -*-
#"""
#Created on Thu Dec  3 14:42:29 2020
#
#@author: Majdi
#"""


import random
import numpy as np
import math
import time
import joblib

class WOA(object):
    """
    Whale Optimization Algorithm
    
    :param mode: (str) problem type, either ``min`` for minimization problem or ``max`` for maximization
    :param bounds: (dict) input parameter type and lower/upper bounds in dictionary form. Example: ``bounds={'x1': ['int', 1, 4], 'x2': ['float', 0.1, 0.8], 'x3': ['float', 2.2, 6.2]}``
    :param fit: (function) the fitness function 
    :param nwhales: (int): number of whales in the population
    :param a0: (float): initial value for coefficient ``a``, which is annealed from ``a0`` to 0 (see **Notes** below for more info).
    :param b: (float): constant for defining the shape of the logarithmic spiral
    :param ncores: (int) number of parallel processors (must be ``<= nwhales``)
    :param seed: (int) random seed for sampling
    """
    def __init__(self, mode, bounds, fit, nwhales=5, a0=2, b=1, ncores=1, seed=None):
        
        if seed:
            random.seed(seed)
            np.random.seed(seed)
        
        assert ncores <= nwhales, '--error: ncores ({}) must be less than or equal than nwhales ({})'.format(ncores, nwhales)
        
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
        self.nwhales=nwhales
        assert a0 > 0, '--error: a0 must be positive'
        self.a0=a0
        self.b=b
        self.dim = len(bounds)
        
        self.lb=np.array([self.bounds[item][1] for item in self.bounds])
        self.ub=np.array([self.bounds[item][2] for item in self.bounds])

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

    def eval_whales(self):
    
        #---------------------
        # Fitness calcs
        #---------------------
        core_lst=[]
        for case in range (0, self.Positions.shape[0]):
            core_lst.append(self.Positions[case, :])
    
        if self.ncores > 1:

            with joblib.Parallel(n_jobs=self.ncores) as parallel:
                fitness_lst=parallel(joblib.delayed(self.fit_worker)(item) for item in core_lst)
                
        else:
            fitness_lst=[]
            for item in core_lst:
                fitness_lst.append(self.fit_worker(item))
        
        return fitness_lst

    def select(self, pos, fit):
        
        best_fit=np.min(fit)
        min_idx=np.argmin(fit)
        best_pos=pos[min_idx,:]
        
        return best_pos, best_fit 
        
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
        #This worker is for parallel calculations
        
        # Clip the whale with position outside the lower/upper bounds and return same position
        x=self.ensure_bounds(x)
        
        # Calculate objective function for each search agent
        fitness = self.fit(x)
        
        return fitness

    def UpdateWhales(self):

       # Update the Position of the whales agents
        for i in range(0, self.nwhales):
            r1 = random.random() 
            r2 = random.random() 
            self.A = 2 * self.a * r1 - self.a  
            C = 2 * r2
            l = (self.fac - 1) * random.random() + 1
            p = random.random()

            for j in range(0, self.dim):

                if p < 0.5:
                    if abs(self.A) >= 1:
                        r_index = math.floor(self.nwhales * random.random())
                        X_rand = self.Positions[r_index, :]
                        self.Positions[i, j] = X_rand[j] - self.A * abs(C * X_rand[j] - self.Positions[i, j])

                    elif abs(self.A) < 1:
                        self.Positions[i, j] = self.best_position[j] - self.A * abs(C * self.best_position[j] - self.Positions[i, j])

                elif p >= 0.5:
                    distance2Leader = abs(self.best_position[j] - self.Positions[i, j])
                    self.Positions[i, j] = (distance2Leader * math.exp(self.b * l) 
                                            * math.cos(l * 2 * math.pi) + self.best_position[j])
            
            self.Positions[i,:]=self.ensure_bounds(self.Positions[i,:])

    def evolute(self, ngen, x0=None, verbose=True):
        """
        This function evolutes the WOA algorithm for number of generations.
        
        :param ngen: (int) number of generations to evolute
        :param x0: (list of lists) initial position of the whales (must be of same size as ``nwhales``)
        :param verbose: (bool) print statistics to screen
        
        :return: (dict) dictionary containing major WOA search results
        """
        self.history = {'local_fitness':[], 'global_fitness':[], 'a': [], 'A': []}
        self.best_fitness=float("inf") 
        self.verbose=verbose
        self.Positions = np.zeros((self.nwhales, self.dim))
        if x0:
            assert len(x0) == self.nwhales, '--error: the length of x0 ({}) MUST equal the number of whales in the group ({})'.format(len(x0), self.nwhales)
            for i in range(self.nwhales):
                self.Positions[i,:] = x0[i]
        else:
            #self.Positions=self.init_sample(self.bounds)  #TODO, update later for mixed-integer optimisation
            # Initialize the positions of whales
            
            for i in range(self.dim):
                self.Positions[:, i] = (np.random.uniform(0, 1, self.nwhales) * (self.ub[i] - self.lb[i]) + self.lb[i])
        
        fitness0=self.eval_whales()
        
        self.best_position, self.best_fitness = self.select(self.Positions, fitness0)
                       
        for k in range(0, ngen):
            
            # a is annealed from 2 to 0
            self.a = self.a0 - k * ((self.a0) / (ngen))
            # fac is annealed from -1 to -2 to estimate l
            self.fac = -1 + k * ((-1) / ngen)
            #-----------------------------
            # Update Whale Positions
            #-----------------------------
            self.UpdateWhales()
                    
            #----------------------
            #  Evaluate New Whales
            #----------------------
            fitness=self.eval_whales()
            
            for i, fits in enumerate(fitness):
                #save the best of the best!!!
                if fits < self.best_fitness:
                    self.best_fitness=fits
                    self.best_position=self.Positions[i, :].copy()
                
            #--mir
            if self.mode=='max':
                self.fitness_best_correct=-self.best_fitness
                self.local_fitness=-np.min(fitness)
            else:
                self.fitness_best_correct=self.best_fitness
                self.local_fitness=np.min(fitness)

            self.history['local_fitness'].append(self.local_fitness)
            self.history['global_fitness'].append(self.fitness_best_correct)
            self.history['a'].append(self.a)
            self.history['A'].append(self.A)
            
            # Print statistics
            if self.verbose and i % self.nwhales:
                print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
                print('WOA step {}/{}, nwhales={}, Ncores={}'.format((k+1)*self.nwhales, ngen*self.nwhales, self.nwhales, self.ncores))
                print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
                print('Best Whale Fitness:', np.round(self.fitness_best_correct,6))
                print('Best Whale Position:', np.round(self.best_position,6))
                print('a:', np.round(self.a,3))
                print('A:', np.round(self.A,3))
                print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')

        if self.verbose:
            print('------------------------ WOA Summary --------------------------')
            print('Best fitness (y) found:', self.fitness_best_correct)
            print('Best individual (x) found:', self.best_position)
            print('--------------------------------------------------------------')  
            
        return self.best_position, self.fitness_best_correct, self.history