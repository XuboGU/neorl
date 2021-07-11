import gym
from gym.spaces import Discrete, Box
from neorl import DQN
from neorl import DQNPolicy
from neorl import RLLogger

#--------------------------------------------------------
# Fitness class based on OpenAI Gym
#--------------------------------------------------------
#Define a Gym-class containing your function to optimise
#see the template below for the Sphere function
#We will build automatic templates for RL in the near future to simplify fitness definition
class IntegerSphere(gym.Env):
    #An integer/discrete form of the sphere function
    def __init__(self):
        lb=-100
        ub=100
        self.nx=5
        self.action_space = Discrete(201)
        self.real_actions=list(range(lb,ub+1))
        self.observation_space = Box(low=min(self.real_actions), high=max(self.real_actions), shape=(self.nx,), dtype=int)
        self.episode_length=50
        self.reset()
        self.done=False
        self.counter = 0

    def step(self, action):
        individual=[self.real_actions[action]]*self.nx
        reward=self.fit(individual=individual)
        self.counter += 1
        if self.counter == self.episode_length:
            self.done=True
            self.counter = 0

        return individual, reward, self.done, {'x':individual}

    def fit(self, individual):
            """Sphere test objective function.
                    F(x) = sum_{i=1}^d xi^2
                    d=1,2,3,...
                    Range: [-100,100]
                    Minima: 0
            """
            #-1 is used to convert minimization to maximization
            return -sum(x**2 for x in individual)

    def reset(self):
        self.done=False
        ac=self.action_space.sample()
        individual=[self.real_actions[ac]]*self.nx
        return individual

    def render(self, mode='human'):
        pass

#--------------------------------------------------------
# RL Optimisation
#--------------------------------------------------------
def test_dqn():
    #create an object from the class
    env=IntegerSphere()
    #create a callback function to log data
    cb=RLLogger(check_freq=1)
    #create an a2c object based on the env object
    dqn = DQN(DQNPolicy, env=env)
    #optimise the enviroment class
    dqn.learn(total_timesteps=2000, callback=cb)
    #print the best results
    print('--------------- DQN results ---------------')
    print('The best value of x found:', cb.xbest)
    print('The best value of y found:', cb.rbest)
    
    return

test_dqn()