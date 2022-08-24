#%%
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
from pandas import DataFrame
import seaborn as sns
from scipy.stats import ttest_ind

DRUGS = ["heparin", "warfarin", "dibigatran", "rivaroxaban", "apixaban", "edoxaban", "betrixaban",
         "pradaxa", "xarelto", "eliquis", "savaysa", "bevyxxa"] # Brand names just in case
#%%
df_pres: DataFrame = pd.read_excel(R"data\patients_anticoag_prescriptions.xlsx")
df_inputcv: DataFrame = pd.read_excel(R"data\patients_anticoag_inputeventscv.xlsx")
df_inputmv: DataFrame = pd.read_excel(R"data\patients_anticoag_inputeventsmv.xlsx")
cont_df = [df_pres, df_inputcv, df_inputmv]
#%%
drug_std_counter = Counter()
drug_counter = Counter()
df_anticoag = DataFrame()
for df in cont_df:
    col_drug = "LABEL" if "LABEL" in df.columns else "DRUG" # "LABEL" if inputevents, "DRUG" for prescriptions table
    for ind, row in df.iterrows():
        if isinstance(row[col_drug], str):
            is_anticoag = False # Anticoagulation flag for each entry
            drug_name = row[col_drug].lower()
            for drug in DRUGS:
                if drug in drug_name:
                    drug_std_counter[drug] += 1
                    drug_counter[drug_name] += 1
                    is_anticoag = True
            if is_anticoag:
                df_anticoag = pd.concat([df_anticoag, df.iloc[[ind]]],
                                        ignore_index=True)
                    
print(drug_std_counter)
print(drug_counter)
print(df_anticoag.head)
df_anticoag.to_excel(R"data\anticoag_events.xlsx")
#%% Load
df_anticoag = pd.read_excel(R"data\anticoag_events.xlsx")
# %%

df_admis: DataFrame = pd.read_excel(R"data\patients_anticoag.xlsx")
df_admis.drop_duplicates(inplace=True, subset=["HADM_ID"])

df_admis_unique = df_admis.drop_duplicates(subset=["SUBJECT_ID"])
df_admis_unique.to_excel(R"data\patients_anticoag_unique.xlsx")
#%%

df_merged = pd.merge(df_anticoag, df_admis, on="HADM_ID", how="left")
df_merged.to_excel(R"data/anticoag_events_admit.xlsx") # Annotate with admission data

#%% Load
df_merged = pd.read_excel(R"data/anticoag_events_admit.xlsx") 
#%%
dt_format = "%Y-%m-%d %H:%M:%S" # Year variable must be capitalized
a = []
pt_anticoag_tracker: dict[int, list] = dict()
for ind, row in df_merged.iterrows():
    # Assign start time differentially based on which parameters are available
    subj_id = row["SUBJECT_ID_x"]
    
    if isinstance(row["STARTDATE"], str):
        anticoag_label = "STARTDATE"
    elif isinstance(row["CHARTTIME"], str):
        anticoag_label = "CHARTTIME"
    elif isinstance(row["STARTTIME"], str):
        anticoag_label = "STARTTIME"
        
    anticoag_time = datetime.strptime(row[anticoag_label], dt_format)
    
    admit_time = datetime.strptime(row["ADMITTIME"], dt_format)
    
    anticoag_delay = anticoag_time - admit_time
    anticoag_delay_days = anticoag_delay/timedelta(days=1) # Divide datetime item to get float
    
    
    if isinstance(row["DEATHTIME"], str):
        status = "Expired"
    else:
        status = "Alive"

    if subj_id not in pt_anticoag_tracker:
        pt_anticoag_tracker[subj_id] = [] # Instantiate empty list
    
    pt_anticoag_tracker[subj_id].append((status, anticoag_delay_days))
    a.append((status, anticoag_delay_days))

#%%
pt_earliest_event: dict[int, tuple[str, float]] = {sub_id: (events[0][0], min([i[1] for i in events])) # Take first event to define alive/expired
       for sub_id, events in pt_anticoag_tracker.items()}

sns.violinplot(x=[status for sub_id, (status, delay) in pt_earliest_event.items()],
               y=[delay for sub_id, (status, delay) in pt_earliest_event.items()])

#%%
c = [delay for sub_id, (status, delay) in pt_earliest_event.items() if status == "Expired"]
d = [delay for sub_id, (status, delay) in pt_earliest_event.items() if status == "Alive"]
ttest_ind(d, c)

# 
#%% Look at patients that didn't receive anticoagulation and compare in chi squared 

pt_tracker = dict()
for ind, row in df_admis_unique.iterrows():
    subj_id = row["SUBJECT_ID"]
    if isinstance(row["DEATHTIME"], str):
        status = "Expired"
    else:
        status = "Alive"


    pt_tracker[subj_id] = status

#%%
pt_no_anticoag = {key: val for key, val in pt_tracker.items() 
                  if key not in pt_anticoag_tracker}
pt_no_anticoag_alive = [k for k, v in pt_no_anticoag.items() if v == "Alive"]
print(F"{len(pt_no_anticoag_alive)} - {len(pt_no_anticoag) - len(pt_no_anticoag_alive)}")
print(len(pt_no_anticoag_alive)/len(pt_no_anticoag))

pt_anticoag_alive = [k for k, v in pt_anticoag_tracker.items() if v[0][0] == "Alive"]
print(F"{len(pt_anticoag_alive)} - {len(pt_anticoag_tracker) - len(pt_anticoag_alive)}")
print(len(pt_anticoag_alive)/len(pt_anticoag_tracker))
