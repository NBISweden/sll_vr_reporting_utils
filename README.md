# SciLifeLab & VR reporting utils

These are scripts used to gather data that is used in the SciLifeLab and VR annual reports.

## Requirements

Before running, install required python modules, in a virtual environment if you prefer:

```bash
# create venv
python3 -m venv venv

# activate the venv
source venv/bin/activate

# update pip
pip install -U pip

# install requirements
pip install -r requirements.txt
```


## generate_report.py

A __slightly__ over-engineered script to create SciLifeLab and VR reports.

Used to fetch all time entries logged between two dates given as arguments. These time entries are used to determin which projects have been active during the selected time period. Data about these active projects are then summarized and printed to a `.xslx` file.

```bash
# examples

# standard SciLifeLab report for short-medium term projects 2023
python3 generate_report.py -c config.yaml --sll --sm-term   --year 2023 -o sll_2023.xlsx

# standard SciLifeLab report for long term projects 2023
python3 generate_report.py -c config.yaml --sll --long-term --year 2023 -o sll_2023.xlsx

# standard VR report for short-medium term projects 2023
python3 generate_report.py -c config.yaml --vr --sm-term   --year 2023 -o sll_2023.xlsx

# standard VR report for long term projects 2023
python3 generate_report.py -c config.yaml --vr --long-term --year 2023 -o sll_2023.xlsx
```

