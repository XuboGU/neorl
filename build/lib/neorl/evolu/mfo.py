# -*- coding: utf-8 -*-
#"""
#@author: Xubo
#@email: guxubo@alumni.sjtu.edu
#"""
import random
import numpy as np
import math
import joblib

class MFO:
    """
    Moth-flame Optimization (MFO)
    
    :param mode: (str) problem type, either "min" for minimization problem or "max" for maximization
    :param bounds: (dict) input parameter type and lower/upper bounds in dictionary form. Example: ``bounds={'x1': ['int', 1, 4], 'x2': ['float', 0.1, 0.8], 'x3': ['float', 2.2, 6.2]}``
    :param fit: (function) the fitness function 
    :param nmoths: (int) number of moths in the population
    :param b: (float) constant for defining the shape of the logarithmic spiral
    :param ncores: (int) number of parallel processors
    :param seed: (int) random seed for sampling
    """
    
    def __init__(self, mode, bounds, fit, nmoths=50, b=1, ncores=1, seed=None):

        self.seed=seed
        if self.seed:
            random.seed(self.seed)
            np.random.seed(self.seed)

        assert nmoths > 3, '--eror: size of nmoths must be more than 3'
        self.npop= nmoths
        self.bounds=bounds
        self.ncores=ncores
        self.b=b

        self.mode=mode
        if mode == 'min':
            self.fit=fit
        elif mode == 'max':
            def fitness_wrapper(*args, **kwargs):
                return -fit(*args, **kwargs)
            self.fit = fitness_wrapper
        else:
            raise ValueError('--error: The mode entered by user is invalid, use either `min` or `max`')

    def gen_indv(self, bounds): # individual 

        indv = []
        for key in bounds:
            if bounds[key][0] == 'int':
                indv.append(random.randint(bounds[key][1], bounds[key][2]))
            elif bounds[key][0] == 'float':
                indv.append(random.uniform(bounds[key][1], bounds[key][2]))
            elif bounds[key][0] == 'grid':
                indv.append(random.sample(bounds[key][1],1)[0])
        return indv

    def init_population(self, x0=None): # population

        pop = []
        if x0: # have premary solution
            print('The first individual provided by the user:', x0[0])
            print('The last individual provided by the user:', x0[-1])
            for i in range(len(x0)):
                pop.append(x0[i])
        else: # random init
            for i in range(self.npop):
                indv=self.gen_indv(self.bounds)
                pop.append(indv)
        
        # array
        pop = np.array(pop)

        return pop

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
        
        xchecked=self.ensure_bounds(x)

        fitness = self.fit(xchecked)

        return fitness

    def evolute(self, ngen, x0=None, verbose=0):
        """
        This function evolutes the MFO algorithm for number of generations.
        
        :param ngen: (int) number of generations to evolute
        :param x0: (list of lists) the initial individuals of the population
        :param verbose: (bool) print statistics to screen
        
        :return: (dict) dictionary containing major MFO search results
        """
        
        self.history = {'local_fitness':[], 'global_fitness':[], 'r': []}
        self.best_fitness=float("inf")
        N = self.npop # population size
        dim = len(self.bounds) # individual length

        if self.seed:
            random.seed(self.seed)
            np.random.seed(self.seed)

        ## INITIALIZE
        #  moths
        if x0:
            assert len(x0) == N, '--error: the length of x0 ({}) (initial population) must equal to number of individuals npop ({})'.format(len(x0), self.npop)
            Moth_pos = self.init_population(x0=x0)
        else:
            Moth_pos = self.init_population()     
        Moth_fitness = np.full(N, float('inf'))  # set as worst result

        # sort moths
        sorted_population = np.copy(Moth_pos)
        fitness_sorted = np.zeros(N)
        # flames
        best_flames = np.copy(Moth_pos)
        best_flame_fitness = np.zeros(N)
        # moths+flames
        double_population = np.zeros((2 * N, dim))
        double_fitness = np.zeros(2 * N)     
        double_sorted_population = np.zeros((2*N, dim))
        double_fitness_sorted = np.zeros(2*N)
        # previous generation
        previous_population = np.zeros((N, dim))
        previous_fitness = np.zeros(N)
        
        ## main loop
        best_scores = []
        for gen in range(1, ngen+1):

            Flame_no = round(N - gen*((N-1) / (ngen+1)))

            if self.ncores > 1: 
                with joblib.Parallel(n_jobs=self.ncores) as parallel:
                    Moth_fitness=parallel(joblib.delayed(self.fit_worker)(indv) for indv in Moth_pos) # 2d list
                Moth_pos = np.array(Moth_pos)
                Moth_fitness = np.array(Moth_fitness)
            else:
                for i in range(N):
                    Moth_fitness[i] = self.fit_worker(Moth_pos[i,:])

            if gen == 1: # OF # equal to OM #
                # sort the moths
                fitness_sorted = np.sort(Moth_fitness) # default: (small -> large)
                #fitness_sorted = -(np.sort(-np.array(Moth_fitness)))  # descend (large -> small)
                I = np.argsort(np.array(Moth_fitness)) # index of sorted list 
                sorted_population = Moth_pos[I, :]

                # update flames
                best_flames = sorted_population
                best_flame_fitness = fitness_sorted

            else: # #OF may > #OM
                
                double_population = np.concatenate((previous_population, best_flames), axis=0)
                double_fitness = np.concatenate((previous_fitness, best_flame_fitness), axis=0)
                
                double_fitness_sorted = np.sort(double_fitness)
                I2 = np.argsort(double_fitness)
                double_sorted_population = double_population[I2, :]
                
                fitness_sorted = double_fitness_sorted[0:N]
                sorted_population = double_sorted_population[0:N, :]

                best_flames = sorted_population
                best_flame_fitness = fitness_sorted
            
            # record the best flame so far   
            Best_flame_score = fitness_sorted[0]
            Best_flame_pos = sorted_population[0, :]

            # previous
            previous_population = np.copy(Moth_pos)  # if not using np.copy(),changes of Moth_pos after this code will also change previous_population!  
            previous_fitness = np.copy(Moth_fitness) # because of the joblib..

            # r linearly dicreases from -1 to -2 to calculate t in Eq. (3.12)
            r = -1 + gen * ((-1) / ngen)

            # update moth position
            for i in range(0, N):
                for j in range(0,dim):
                    if i <= Flame_no:
                        distance_to_flame = abs(sorted_population[i,j]-Moth_pos[i,j])
                        t = (r-1)*random.random()+1
                        # eq. (3.12)
                        Moth_pos[i,j] = (
                            distance_to_flame*math.exp(self.b*t)*math.cos(t*2*math.pi)
                        + sorted_population[i,j] 
                        )

                    if i > Flame_no: 
                        distance_to_flame = abs(sorted_population[Flame_no,j]-Moth_pos[i,j])
                        t = (r-1)*random.random()+1     
                        # rebundant moths all fly to the last Flame_no
                        Moth_pos[i,j] = (
                            distance_to_flame*math.exp(self.b*t)*math.cos(t*2*math.pi)
                        + sorted_population[Flame_no,j] 
                        )
            
                
                Moth_pos[i,:]=self.ensure_bounds(Moth_pos[i,:])
    
            #-----------------------------
            #Fitness saving 
            #-----------------------------
            gen_avg = sum(best_flame_fitness) / len(best_flame_fitness)  # current generation avg. fitness
            y_local_best = Best_flame_score # fitness of best individual
            x_local_best = Best_flame_pos  # position of the best flame
            
            for i, fits in enumerate(fitness_sorted):
                #save the best of the best!!!
                if fits < self.best_fitness:
                    self.best_fitness=fits
                    self.best_position=sorted_population[i, :].copy()
                
            #--mir
            if self.mode=='max':
                self.fitness_best_correct=-self.best_fitness
                self.local_fitness=-Best_flame_score
            else:
                self.fitness_best_correct=self.best_fitness
                self.local_fitness=Best_flame_score

            self.history['local_fitness'].append(self.local_fitness)
            self.history['global_fitness'].append(self.fitness_best_correct)
            self.history['r'].append(r)

            if verbose:
                print('************************************************************')
                print('MFO step {}/{}, Ncores={}'.format(gen*self.npop, ngen*self.npop, self.ncores))
                print('************************************************************')
                print('Best fitness:', np.round(self.fitness_best_correct,6))
                print('Best individual:', self.best_position)
                print('Average fitness:', np.round(gen_avg,6))
                print('************************************************************')


        if verbose:
            print('------------------------ MFO Summary --------------------------')
            print('Best fitness (y) found:', self.fitness_best_correct)
            print('Best individual (x) found:', self.best_position)
            print('--------------------------------------------------------------')
                
        return self.best_position, self.fitness_best_correct, self.history
