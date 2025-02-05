#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  4 11:51:22 2020

@author: majdi
"""

import numpy as np
import pandas as pd
import os
import random
import math
from itertools import repeat
import itertools
import sys, copy, shutil
import subprocess
from multiprocessing.dummy import Pool

import random
import numpy 
from deap import algorithms
from deap import base 
from deap import creator 
from deap import tools 
import matplotlib.pyplot as plt

try: 
    from collections.abc import Sequence
except ImportError:
    from collections import Sequence

class GATUNE:
    
    """
    A class to parse neorl input template and construct cases for genetic algorathim (GA) hyperparameter optimisation

    inputs: 
    The template input file
    Class object from PARSER.py, featuring user input for TUNE
    neorl logo
    """
    
    def __init__(self, inputfile, tuneblock, logo):
        self.logo=logo
        self.inputfile=inputfile
        self.tuneblock=tuneblock
        self.n_last_episodes=int(self.tuneblock["n_last_episodes"])
        self.ncores=int(self.tuneblock["ncores"])
        self.ncases=int(self.tuneblock["ncases"])
  
        #---------------------------------------
        # define genetic algorithm parameters
        #---------------------------------------
        self.popsize=10
        self.ngens=int(self.ncases / self.popsize)
        self.MU=2
        self.SIGMA=1
        self.INDPB=0.1
        self.CXPB=0.5
        self.MUTPB=0.2
        self.check_freq=1
        self.ETA=0.6
        self.gridindex=0
        self.paramvals=dict()
        self.paraminds=dict()
        
        #-------------------------------
        # construct results directory
        #-------------------------------
        if os.path.exists('./tunecases/'):
            shutil.rmtree('./tunecases/')
            os.makedirs('./tunecases/', exist_ok=True)
        else:
            os.makedirs('./tunecases/', exist_ok=True)
        self.csvlogger='tune.csv'
        self.tunesummary='tunesummary.txt'
        
        #---------------------------------
        # parse the input template
        #---------------------------------
        with open (self.inputfile, 'r') as input_file_text:
            self.template=input_file_text.readlines()
            
        first=0; last=0
        for i in range (len(self.template)):
            if ('READ TUNE' in self.template[i]):
                first=i
            if ('END TUNE' in self.template[i]):
                last=i
        if first == 0 and last==0:
            raise ('TUNE card cannot be found')
        
        del self.template[first : last+1]  
        self.template="".join(self.template)  
                     
    def tune_count(self):
        
        """
        1- This function uses self.tuneblock, parse it, infer all parameters to be tuned and thier distribution
        2- This function creates GA engine and instantiates the initial population for evolution algorithm
        """
        
        self.param_dict={}
        for item in self.tuneblock:
            if '{' in item and '}' in item and item[0] != '#':
                #-----------------------------------------------------
                # check the existence of the name in the template
                #-----------------------------------------------------
                if item not in self.template:
                    raise ValueError('parameter {} in TUNE block cannot be found in any other block, e.g. DQN, GA, PPO, etc.'.format(item)) 

                item_lst=self.tuneblock[item].split(",")
                item_lst=[item.strip() for item in item_lst] # get rid of white spaces in the splitted values
                #-------------------------------------------------------
                # check if a uniform distribution of floats is identified
                #-------------------------------------------------------
                try:
                    if "float" in item_lst:
                        item_lst[0]=float(item_lst[0])
                        item_lst[1]=float(item_lst[1])
                        print ('-- debug: parameter {} has uniform distribution of type --float-- between {} and {}'.format(item,item_lst[0],item_lst[1]))
                    elif "u" in item_lst: 
                        item_lst[0]=float(item_lst[0])
                        item_lst[1]=float(item_lst[1])
                        print ('-- debug: parameter {} has uniform distribution of type --float-- between {} and {}'.format(item,item_lst[0],item_lst[1]))
                except:
                    raise Exception ('--error: TUNE cannot construct the user-given uniform distribution of --floats-- for {} according to (low, high, u) syntax'.format(item))
               
                #---------------------------------------------------
                # check if a random integer distribution is identified
                #---------------------------------------------------
                try:
                    if "int" in item_lst:
                        item_lst[0]=int(item_lst[0])
                        item_lst[1]=int(item_lst[1])
                        print ('-- debug: parameter {} has uniform distribution of type --int-- between {} and {}'.format(item,item_lst[0],item_lst[1]))
                    elif "randint" in item_lst:
                        item_lst[0]=int(item_lst[0])
                        item_lst[1]=int(item_lst[1])
                        print ('-- debug: parameter {} has uniform distribution of type --int-- between {} and {}'.format(item,item_lst[0],item_lst[1]))
                except:
                    raise Exception ('--error: TUNE cannot construct the user-given uniform distribution of --int-- for {} according to (low, high, u) syntax'.format(item))
              
               #-----------------------------------------------------
               # check if a grid is identified
               #-----------------------------------------------------
                try:
                    if "grid" in item_lst:
                        element_lst=[]
                        for element in item_lst:
                            # check if it is an integer
                            not_int=0
                            try:
                                element_lst.append(int(element.strip()))
                            except Exception:
                                not_int=1
                            
                            # else check if the elment is float
                            if not_int:
                                try:
                                    element_lst.append(float(element.strip()))
                                # else consider it a string
                                except Exception:
                                    element_lst.append(str(element.strip()))
                                    
                        item_lst=element_lst
                        print ('-- debug: parameter {} has grid type with values {}'.format(item,item_lst))
                except:
                    raise Exception ('--error: TUNE cannot construct the user-given grid for {} according to the comma-seperated syntax'.format(item))

                self.param_dict[item]=item_lst # Save the final parsed list for parameter {XXX}                    
                
        
        #--------------------------------
        # Create the GA engine in DEAP 
        #--------------------------------
        #random.seed(64)
        
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)
        self.toolbox=base.Toolbox()
        if self.ncores > 1: 
            print("ENTERED PARALLEL OPTIMIZATION")
            self.pool = Pool()
        else:
            print("ENTERED SINGLE CORE OPTIMIZATION")
                
        functions = [] # List of functions to generate parameter values from appropriate distributions
        LOW=[] # Lower bounds for parameters to be tuned
        UP=[] # Upper bounds for parameters to be tuned
        for k in list(self.param_dict.keys()):
            def fun(key=k):
                if 'int' in self.param_dict[key]:
                    return random.randint(self.param_dict[key][0], self.param_dict[key][1])
                if 'float' in self.param_dict[key]:
                    return random.uniform(self.param_dict[key][0], self.param_dict[key][1])
                if 'u' in self.param_dict[key]:
                    return random.uniform(self.param_dict[key][0], self.param_dict[key][1])
                if 'randint' in self.param_dict[key]:
                    return random.randint(self.param_dict[key][0], self.param_dict[key][1])
                if 'grid' in self.param_dict[key]:
                    self.real_grid=list(self.param_dict[key])
                    self.real_grid.remove('grid') # get rid of the 'grid' to avoid sampling it 
                    self.paramvals[key] = self.real_grid
                    return random.sample(self.real_grid, 1)[0]
            functions.append(fun)
            LOW.append(self.param_dict[k][0])
            UP.append(self.param_dict[k][1])
            
        
        #--------------------------------------------------------------
        # register functions for operators and initializers in toolbox
        #--------------------------------------------------------------
        self.toolbox.register("individual", tools.initCycle, creator.Individual, functions,n=1)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        if self.ncores > 1:
            self.toolbox.register("map", self.pool.map)
        self.toolbox.register("evaluate", self.evalX)
        self.toolbox.register("evaluate", self.evalX)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", self.mutGATUNE, eta=self.ETA, low=LOW, up=UP, indpb=self.INDPB)
        self.toolbox.register("select", tools.selTournament, tournsize=3)
        
        
        self.pop = self.toolbox.population(n=self.popsize) # Generate the initial population
        
    def gen_cases(self, x=0):
        
        """
        1- This function prepares the directories and files for all cases
        2- It replaces the {XXX} with the sampled value
        """
        
        if x == 0: # Parse all inputs from self.tuneblock and generate the initial population for the first generation
            self.tune_count()
            
        self.param_names=list(self.param_dict.keys())
        for i in range (x, x + len(self.pop)):
                        
            os.makedirs('./tunecases/case{}'.format(i+1), exist_ok=True)
            self.new_template=copy.deepcopy(self.template)
            Z = i-x
            for j in range (len(self.param_names)):
                if x==0:
                    if self.param_names[j] in self.paramvals.keys():
                        self.paraminds[j]=self.param_names[j]
                self.new_template=self.new_template.replace(str(self.param_names[j]), str(self.pop[Z][j]))
            
            filename='./tunecases/case{}/case{}.inp'.format(i+1, i+1)
            with open (filename, 'w') as fout:
                fout.writelines(self.new_template)
             
            # copy external files into the new directory, if extfiles card exists
            if 'extfiles' in self.tuneblock.keys():
                if self.tuneblock['extfiles']:
                    print('--debug: external files are identified, copying them into each case directory')
                    for item in self.tuneblock['extfiles']:
                        os.system('cp -r {} ./tunecases/case{}/'.format(item, i+1))
                
        #-----------------------        
        # Infer neorl.py path
        #-----------------------
        # Find neorl path
        #self.here=os.path.dirname(os.path.abspath(__file__))
        #self.neorl_path=self.here.replace('src/tune','neorl.py') #try to infer neorl.py internally to call neorl inside or neorl
        #self.python_path=self.here.replace('neorl/src/tune','anaconda3/bin/python3') #try to infer python3 path to call neorl inside or neorl
        self.neorl_path=sys.argv[0]
        self.python_path=sys.executable
        print('--debug: NEORLPATH=', self.neorl_path)
        print('--debug: PYTHONPATH=', self.python_path)
    
    def evalX(self, individual):
        
        """
        This function evaluates an individual's fitness, calls self.case_object(individual) for evaluation
        Inputs: 
            - An individual
        Outputs: 
            - Individual fitness 
        """
        
        return self.case_object(individual)
        
    def case_object(self,ind): 
        
        """
        This function sets up a case object for an individual during evolution
        Inputs: 
            - An individual
        Outputs: 
            - Mean reward for the individual  
        """
        
        try:
            generation = ind[0]
            x = ind[1]
            
            casenum = generation
            print('--------------------------------------------------')
            print('Running TUNE Case {}/{}: {}'.format(x, len(self.pop), self.pop[x-1]))
            subprocess.call([self.python_path, self.neorl_path, '-i', 'case{}.inp'.format(casenum)], cwd='./tunecases/case{}/'.format(casenum))  # this exceutes neorl for this case.inp
            print('--------------------------------------------------')
            
            #--------------------------------------------------------------------------------------------------------------
            # Try to infer the _out.csv file in the directory since only one method is allowed
            csvfile=[f for f in os.listdir('./tunecases/case{}/case{}_log/'.format(casenum, casenum)) if f.endswith('_out.csv')]
            if len(csvfile) > 1:
                raise Exception ('multiple *_out.csv files can be found in the logger of TUNE, only one is allowed')
            #--------------------------------------------------------------------------------------------------------------
            
            reward_lst=pd.read_csv('./tunecases/case{}/case{}_log/{}'.format(casenum,casenum, csvfile[0]), usecols=['reward']).values
            mean_reward=np.mean(reward_lst[-self.n_last_episodes:])
            max_reward=np.max(reward_lst)
            
            with open (self.csvlogger, 'a') as fout:
                fout.write(str(casenum) +',')
                [fout.write(str(item) + ',') for item in self.pop[x-1]]
                fout.write(str(mean_reward) + ',' + str(max_reward) + '\n')
                
            return (mean_reward,)
        
        except:
            print('--error: case{}.inp failed during execution'.format(casenum))
            
            return 'case{}.inp:failed'.format(casenum)
        
    
    def run_cases(self):

        """
        This function performs evolution on initial population over self.ngens generations and collects their stats 
        """
        
        with open (self.csvlogger, 'w') as fout:
            fout.write('caseid, ')
            [fout.write(item + ',') for item in self.param_names]
            fout.write('mean_reward,max_reward\n')
        
        #random.seed(64)
        
        #---------------------------------        
        # Perform evolution on population
        #---------------------------------
        genid = 0 #global counter to track case numbers
        for gen in range(1, self.ngens+1):
            fit_list=[]
            
            self.offspring = algorithms.varAnd(self.pop, self.toolbox, cxpb=self.CXPB, mutpb=self.MUTPB)
    
            caseids = [(genid+i, i) for i in range(1,len(self.offspring)+1)]
            fits = self.toolbox.map(self.toolbox.evaluate, caseids)
            
            for fit, ind in zip(fits, self.offspring):
                ind.fitness.values = fit
                fit_list.append(fit)
            
            self.pop = self.toolbox.select(self.offspring, len(self.pop))

            genid = genid + len(self.offspring)
            if gen < self.ngens:
                self.gen_cases(genid)
            
            
        csvdata=pd.read_csv('tune.csv')
        asc_data=csvdata.sort_values(by=['caseid'],ascending=True)
        des_data=csvdata.sort_values(by=['mean_reward'],ascending=False)
        des_data2=csvdata.sort_values(by=['max_reward'],ascending=False)
        asc_data.to_csv('tune.csv', index=False)
        
        mean = np.mean(des_data.iloc[:,4:5])
        totalmean=mean.tolist()[0]
        
        try:
            failed_cases=len([print ('failed') for item in self.pop if isinstance(item, str)])
        except:
            failed_cases='NA'
        
        print ('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
        print('Mean Rewards for all cases=', totalmean)
        print ('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
        print ('All TUNE CASES ARE COMPLETED')
        print ('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
        print('--debug: Check tunesummary.txt file for best hyperparameters found')
        print('--debug: Check tune.csv file for complete csv logger of all cases results')
        print('--debug: Check tunecases directory for case-by-case detailed results')
        
        with open ('tunesummary.txt', 'w') as fout:
            
            fout.write(self.logo)
            fout.write('*****************************************************\n')
            fout.write('Summary for the TUNE case \n')
            fout.write('*****************************************************\n')
            fout.write('Number of cases evaluated: {} \n'.format(self.ncases))
            fout.write('Number of failed cases: {} \n'.format(failed_cases))
            fout.write('Parameter names: {} \n'.format(self.param_names))
            fout.write('Parameter values: {} \n '.format(self.param_dict))
            fout.write ('--------------------------------------------------------------------------------------\n')
            if des_data.shape[0] < 20:
                top=des_data.shape[0]
                fout.write ('Top {} hyperparameter configurations ranked according to MEAN reward \n'.format(top))
                fout.write(des_data.iloc[:top].to_string(index=False))
            else:
                top=20
                fout.write ('Top {} hyperparameter configurations ranked according to MEAN reward \n'.format(top))
                fout.write(des_data.iloc[:top].to_string(index=False))
            fout.write ('\n')
            fout.write ('--------------------------------------------------------------------------------------\n')
            if des_data2.shape[0] < 20:
                top=des_data2.shape[0]
                fout.write ('Top {} hyperparameter configurations ranked according to MAX reward \n'.format(top))
                fout.write(des_data2.iloc[:top].to_string(index=False))
            else:
                top=20
                fout.write ('Top {} hyperparameter configurations ranked according to MAX reward \n'.format(top))
                fout.write(des_data2.iloc[:top].to_string(index=False))
        
        if self.ncores > 1:
            self.pool.close()


    def mutGATUNE(self,individual, eta, low, up, indpb):
        
        """
        Polynomial mutation function as implemented in original NSGA-II algorithm in
        C by Deb. modified to handle mutation of different distributions (float, int, grid)
        Inputs: 
            - individual: :term:`Sequence <sequence>` individual to be mutated.
            - eta: Crowding degree of the mutation. A high eta will produce
                    a mutant resembling its parent, while a small eta will
                    produce a solution much more different.
            - low: A value or a :term:`python:sequence` of values that
                    is the lower bound of the search space.
            - up: A value or a :term:`python:sequence` of values that
                   is the upper bound of the search space.
        Outputs:
            - returns: A tuple of one individual.
        """
        
        size = len(individual)
        if not isinstance(low, Sequence):
            low = repeat(low, size)
        elif len(low) < size:
            raise IndexError("low must be at least the size of individual: %d < %d" % (len(low), size))
        if not isinstance(up, Sequence):
            up = repeat(up, size)
        elif len(up) < size:
            raise IndexError("up must be at least the size of individual: %d < %d" % (len(up), size))
        for i, xl, xu in zip(range(size), low, up):

            if i in self.paraminds.keys(): # Grid distribution received 
                if random.random() <= indpb:
                    paramname=self.paraminds[i]
                    individual[i]=random.sample(self.paramvals[paramname],1)[0]

            if type(individual[i]) == int: # Random integer distribution received 
                if random.random() <= indpb:
                    individual[i] == random.randint(xl, xu)

            if type(individual[i]) == float: # Uniform float distribution received
                if random.random() <= indpb:
                    x = individual[i]
                    x = float(x)
                    delta_1 = (x - xl) / (xu - xl)
                    delta_2 = (xu - x) / (xu - xl)
                    rand = random.random()
                    mut_pow = 1.0 / (eta + 1.)
                    if rand < 0.5:
                        xy = 1.0 - delta_1
                        val = 2.0 * rand + (1.0 - 2.0 * rand) * xy ** (eta + 1)
                        delta_q = val ** mut_pow - 1.0
                    else:
                        xy = 1.0 - delta_2
                        val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * xy ** (eta + 1)
                        delta_q = 1.0 - val ** mut_pow
                    x = x + delta_q * (xu - xl)
                    x = x.real
                    x = min(max(x, xl), xu)
                    individual[i] = x
        
        return individual,