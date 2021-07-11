# -*- coding: utf-8 -*-
#"""
#@author: Xubo
#@email: guxubo@alumni.sjtu.edu
#"""
import random
import numpy as np
import joblib

class JAYA:
    """
    JAYA algorithm
    
    :param mode: (str) problem type, either "min" for minimization problem or "max" for maximization
    :param bounds: (dict) input parameter type and lower/upper bounds in dictionary form. Example: ``bounds={'x1': ['int', 1, 4], 'x2': ['float', 0.1, 0.8], 'x3': ['float', 2.2, 6.2]}``
    :param fit: (function) the fitness function 
    :param npop: (int) number of individuals in the population
    :param ncores: (int) number of parallel processors
    :param seed: (int) random seed for sampling
    """
    
    def __init__(self, mode, bounds, fit, npop=50, ncores=1, seed=None):

        self.seed=seed
        if self.seed:
            random.seed(self.seed)
            np.random.seed(self.seed)

        assert npop > 3, '--eror: size of npop must be more than 3'
        self.npop= npop
        self.bounds=bounds
        self.ncores=ncores

        self.mode=mode
        if mode == 'max':
            self.fit=fit
        elif mode == 'min':
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

        fitness = self.fit(x)

        return fitness

    def evolute(self, ngen, x0=None, verbose=0):
        """
        This function evolutes the MFO algorithm for number of generations.
        
        :param ngen: (int) number of generations to evolute
        :param x0: (list of lists) the initial individuals of the population
        :param verbose: (bool) print statistics to screen
        
        :return: (dict) dictionary containing major MFO search results
        """
        N = self.npop # population size
        dim = len(self.bounds) # individual length

        if self.seed:
            random.seed(self.seed)
            np.random.seed(self.seed)
        
        fitness_mat = np.zeros(N)

        Best_pos = np.zeros(dim)
        Best_score = float('-inf') # find a maximum, so the larger the better
        Worst_pos = np.zeros(dim)
        Worst_score = float('inf')
        ## INITIALIZE
        #  population
        if x0:
            assert len(x0) == N, '--error: the length of x0 ({}) (initial population) must equal to number of individuals npop ({})'.format(len(x0), self.npop)
            pos = self.init_population(x0=x0)
        else:
            pos = self.init_population()     
        
        # calulate fitness 
        for i in range(N):
            fitness = self.fit_worker(pos[i, :])
            fitness_mat[i] = fitness
            if fitness > Best_score:
                Best_score = fitness
                Best_pos = pos[i, :]
            if fitness < Worst_score:
                Worst_score = fitness
                Worst_pos = pos[i, :]

        ## main loop
        best_scores = []
        for gen in range(1, ngen+1):

            new_pos = np.zeros((N,dim))

            # update pos
            for i in range(N):
                r1=np.random.random(dim)
                r2=np.random.random(dim)
                # Update pos
                new_pos[i,:] = (
                    pos[i,:] 
                    + r1*(Best_pos - abs(pos[i,:]))
                    - r2*(Worst_pos - abs(pos[i,:])) # !! minus
                )
                # check bounds            
                new_pos[i,:] = self.ensure_bounds(new_pos[i,:])

            if self.ncores > 1:
                with joblib.Parallel(n_jobs=self.ncores) as parallel:
                    fitness_new = parallel(joblib.delayed(self.fit_worker)(item) for item in new_pos)
                for i in range(N):
                    if fitness_new[i] > fitness_mat[i]:
                        pos[i,:] = new_pos[i,:]
                        fitness_mat[i] = fitness_new[i]

            else:
                for i in range(N):
                    # replace current element with new element if it has better fitness
                    fitness_temp = self.fit_worker(new_pos[i,:])
                    if fitness_temp > fitness_mat[i]: # better than the old
                        pos[i,:] = new_pos[i,:]
                        fitness_mat[i] = fitness_temp

            # update best_score and worst_score
            for i in range(N):
                # new_pos[i,:] = self.ensure_bounds(new_pos[i,:])
                if fitness_mat[i] > Best_score:
                    Best_score = fitness_mat[i]
                    Best_pos = pos[i, :]
                if fitness_mat[i] < Worst_score:
                    Worst_score = fitness_mat[i]
                    Worst_pos = pos[i, :]            

            #-----------------------------
            #Fitness saving 
            #-----------------------------
            gen_avg = sum(fitness_mat) / N                   # current generation avg. fitness
            y_best = Best_score                                # fitness of best individual
            x_best = Best_pos  # position of the best flame
            best_scores.append(y_best)
            
            #--mir  show the value wrt min/max
            if self.mode=='min':
                y_best_correct=-y_best
            else:
                y_best_correct=y_best

            if verbose:
                print('************************************************************')
                print('JAYA step {}/{}, Ncores={}'.format(gen*self.npop, ngen*self.npop, self.ncores))
                print('************************************************************')
                print('Best fitness:', np.round(y_best_correct,6))
                print('Best individual:', x_best)
                print('Average fitness:', np.round(gen_avg,6))
                print('************************************************************')


        if verbose:
            print('------------------------ JAYA Summary --------------------------')
            print('Best fitness (y) found:', y_best_correct)
            print('Best individual (x) found:', x_best)
            print('--------------------------------------------------------------')
    
        if self.mode=='min':
            best_scores=[-item for item in best_scores]
                
        return x_best, y_best_correct, best_scores