import pandas as pd
import statsmodels.api as sm
import numpy as np
import random as rd
import sys

# Static parameters of the simulation

CONTEXTUAL_BANDIT = True # set to False to disable smartness.
VISITORS = 2000          # number of visitors to simulate.
CHUNKS = 50              # number of samples to collect before printing intermediate results.
WARMUP = 100             # number of samples to collect before training.
J = 100                  # number of bootstrap samples to use.
MAX_SAMPLE = 2000        # max number of samples per bootstrap.
SIMULATIONS = 100        # number of simulations to run sequentially.

print "simulation, visitors, current conversion rate, overall conversion rate, total conversions, pulls per arm";

for sim in xrange(0, SIMULATIONS):
    # counters for simulation
    conversions     = 0
    sub_conversions = 0
    
    # with these settings, non-contextual best should be ~0.4 vs contextual ~0.5  
    arms = [
        {
            "base_rate": 0.3,
            "modifiers": { 
                "var-A_1": 2, 
                "var-B_1": 1./2,
            },
            "models": []
        },
        {
            "base_rate": 0.4,
            "modifiers": { },
            "models": []
        },
    ]

    # init models and pulls
    for a in xrange(0, len(arms)):
        arms[a]["pulls"] = 0
        for j in xrange(0,J):
            arms[a]["models"].append({"model": None, "df": pd.DataFrame(), "update": True})
    
    for r in xrange(1,VISITORS+1):
        # generate a visitor
        l = rd.choice(["A","B"])
        v = {
            "var-A": int(l == "A"),
            "var-B": int(l == "B"),
        }
        
        # predict conversion each arm.
        scores = []
        for a in xrange(0,len(arms)):
            j = rd.randint(0,J-1)
            if (len(arms[a]["models"][j]["df"]) < WARMUP):
                scores.append(np.random.ranf())
            else:
                if CONTEXTUAL_BANDIT:
                    if (arms[a]["models"][j]["update"] == True):
                        df = arms[a]["models"][j]["df"]
                        arms[a]["models"][j]["model"] = sm.Logit(df["c"], df[df.columns[1:]]).fit(disp=0)
                        arms[a]["models"][j]["update"] = False
                    scores.append(arms[a]["models"][j]["model"].predict(pd.DataFrame([v]))[0])
                else:
                    scores.append((sum(arms[a]["models"][j]["df"]["c"])*1.)/len(arms[a]["models"][j]["df"]))
        
        # pick best arm
        arm = np.argmax(scores) # argmax(index @scores)
        
        # calculate conversion odds
        odds = arms[arm]["base_rate"]
        for m in arms[arm]["modifiers"].keys():
            if int(v[m.split("_")[0]]) == int(m.split("_")[1]):
                odds *= arms[arm]["modifiers"][m]
        
        # pull arm and check for conversion
        arms[arm]["pulls"] += 1
        v["c"] = np.random.ranf() < odds
        conversions += v["c"]
    
        # update bootstrap samples for all pools
        for j in xrange(0,J):
            if (rd.randint(0,1) == 1): # probabilistically sample 50%
                if arms[arm]["models"][j]["df"] is None:
                    arms[arm]["models"][j]["df"] = pd.DataFrame([v])
                else: 
                    if (len(arms[arm]["models"][j]["df"]) == MAX_SAMPLE): # limit sample size
                        i = rd.randint(0,MAX_SAMPLE-1) # replace random old sample
                        arms[arm]["models"][j]["df"][i:i+1] = pd.DataFrame([v])
                    else:
                        arms[arm]["models"][j]["df"] = arms[arm]["models"][j]["df"].append(pd.DataFrame([v]))
                # set update models if needed
                if CONTEXTUAL_BANDIT:
                    if (len(arms[arm]["models"][j]["df"]) >= WARMUP):
                        arms[arm]["models"][j]["update"] = True
    
        if r % CHUNKS == 0:
            p = str(arms[0]["pulls"])
            for a in xrange(1, len(arms)):
                p += ", " + str(arms[a]["pulls"])
            print str(sim) + ", " + str(r) + ", " + str((conversions-sub_conversions)*1./CHUNKS) + ", " + str(conversions*1./r) + ", " + str(conversions) + ", " + p
            sys.stdout.flush()
            sub_conversions = conversions