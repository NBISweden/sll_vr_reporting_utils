from collections import defaultdict
from pprint import pprint
import argparse
import csv
import pdb
import requests
import sys
import yaml
from Redmine_utils import Redmine_utils
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

def parse_arguments():
    """
    Parse command line arguments.
    Returns:
        The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description='Fetch spent time data from Redmine.')
    parser.add_argument('-c', '--config',             help='Path to the YAML config file.', required=True)
    parser.add_argument('-e', '--end_date',           help='End date of the interval (YYYY-MM-DD).')
    parser.add_argument('-g', '--group_name',         help='Name of the group to fetch data for.')
    parser.add_argument('-o', '--output',             help='Path to the output file.', required=True)
    parser.add_argument('-s', '--start_date',         help='Start date of the interval (YYYY-MM-DD).')
    parser.add_argument('-t', '--exclude-timelogbot', help='Use to exclude all time entries created by timelogbot.', action='store_true')
    parser.add_argument('-y', '--year', type=int,     help='Shortcut to set -s (YYYY-1)-12-01 and -e YYYY-11-30.')

    return parser.parse_args()

def load_config(path):
    """
    Load Redmine URL and API key from a YAML config file.
    Args:
        path: The path to the YAML config file.
    Returns:
        The Redmine URL and API key.
    """
    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    return config['url'], config['api_key']

def get_group_id(redmine_url, api_key, group_name):
    """
    Get the ID of a group by its name.
    Args:
        redmine_url: The Redmine URL.
        api_key: The API key.
        group_name: The name of the group.
    Returns:
        The ID of the group.
    """

    # if a group name was not specified
    if not group_name:
        return None

    response = requests.get(f"{redmine_url}/groups.json", params={"key": api_key})
    response.raise_for_status()
    groups = response.json()["groups"]
    for group in groups:
        if group["name"] == group_name:
            return group["id"]
    raise ValueError(f"No group found with name {group_name}")



def classify_project(lexicon_name, proj_id):
    """
    Return the classification of a project according the requested lexicon.
    """

    
    # define the classification lexicon
    lexicon = {'bengts_report': {
                        'default': 'SMS',
                        'Long-term Support': 'Long-term',
                    },
        }

    # exit if the lexicon name is invalid
    if lexicon_name not in lexicon:
        sys.exit(f"ERROR: Lexicon not defined: {lexicon_name}")

    # check if the proj_id is a name if it is not found
    if proj_id not in projects:

        possible_proj_id = [ proj['id'] for proj in projects if proj['name'] == proj_id ]
        if len(possible_proj_id) == 1:
            proj_id = possible_proj_id
        else:
            # how will deleted projects work here?
            sys.exit(f"ERROR: proj_id \"{proj_id}\" neither a proj_id or proj_name.")


    # return the classification if found, otherwise return the default classification for the lexicon
    return lexicon[lexicon_name].get(projects[proj_id]['name'], lexicon[lexicon_name]['default'])



def get_time_entries(redmine_url, api_key, group_id, date_interval, redmine, projects, exclude_timelogbot=False):
    """
    Fetch spent time data from Redmine for a specific group.
    Args:
        redmine_url: The Redmine URL.
        api_key: The API key.
        group_id: The ID of the group.
        date_interval: The date interval.
    Returns:
        A dictionary with the spent time data.
    """
    spent_time_data     = defaultdict(lambda: defaultdict(float))
    percent_matrix_data = {}





    ### get user info

    # Set up headers with the API key
    headers = {'X-Redmine-API-Key': api_key}

    # Initialize variables for pagination
    offset      = 0
    limit       = 100
    total_users = float('inf')  # Set an initial value greater than zero
    users_all   = {}

    while offset < total_users:
        # Construct the API endpoint URL for listing users with pagination
        users_endpoint = f'{redmine_url}/users.json?offset={offset}&limit={limit}'

        # Make the GET request to the Redmine API
        response = requests.get(users_endpoint, headers=headers)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response to get user data
            users_data = response.json()

            # Update total_users based on the total count from the first page
            if offset == 0:
                total_users = users_data['total_count']

            # Extract and print user information
            for user in users_data['users']:
                users_all[user['id']] = {'firstname': user['firstname'], 'lastname':user['lastname'], 'mail':user['mail'], 'time':{}}

            # Update the offset for the next page
            offset += limit

        else:
            # Print an error message if the request was not successful
            print(f"Error: Unable to fetch users. Status Code: {response.status_code}")
            break


    # if a group is to be filtered out
    if group_id:
        # Fetch group members
        response = requests.get(f"{redmine_url}/groups/{group_id}.json", params={"key": api_key, "include": "users"})
        response.raise_for_status()
        group = response.json()["group"]
        user_ids = [user["id"] for user in group["users"]]

        # filter out group members
        users = { user_id:user_info for user_id,user_info in users_all.items() if user_id in user_ids}
    
    else:
        users = users_all



    # Fetch all time entries in the date interval
    params = {"key": api_key, "spent_on": f"><{date_interval['>=']}|{date_interval['<=']}", "limit": 100}
    offset = 0
    time_without_issue = 0
    while True:
        params["offset"] = offset
        response = requests.get(f"{redmine_url}/time_entries.json", params=params)
        response.raise_for_status()
        entries = response.json()["time_entries"]
        if not entries:
            break
        for entry in entries:

            # skip timelog importer if requested
            if exclude_timelogbot and entry['user']['name'] == "Timelog Importer":
                continue

            # get info
            user_id = entry["user"]["id"]
            toplevel_proj = redmine.get_toplevel_project(entry['project']['id'])

            # classify the project to make it end up in the right sheet
            support_type = classify_project('bengts_report', toplevel_proj)

            # if the user is in the list of users we are interested in
            if user_id in users:
                
                try:
                    # save time data
                    spent_time_data[support_type][user_id]["firstname"] = users[user_id]['firstname']
                    spent_time_data[support_type][user_id]["lastname"] = users[user_id]['lastname']
                    spent_time_data[support_type][user_id]["email"] = users[user_id]['mail']
                    spent_time_data[support_type][user_id]["total spent time"] += entry["hours"]

                # if it is the first time the support type is seed
                except TypeError:
                    spent_time_data[support_type] = defaultdict(lambda: defaultdict(float))
                    spent_time_data[support_type][user_id]["firstname"] = users[user_id]['firstname']
                    spent_time_data[support_type][user_id]["lastname"] = users[user_id]['lastname']
                    spent_time_data[support_type][user_id]["email"] = users[user_id]['mail']
                    spent_time_data[support_type][user_id]["total spent time"] += entry["hours"]


                # if it is the first time the support type or user is seen
                try:
                    spent_time_data[support_type][user_id]['spent_time'][entry["activity"]["name"]][toplevel_proj] += entry["hours"]
                    spent_time_data[support_type][user_id]['spent_time'][entry["activity"]["name"]]["total"] += entry["hours"]
                except TypeError:
                    # if it is the first time the users is seen
                    spent_time_data[support_type][user_id]['issues'] = set()
                    spent_time_data[support_type][user_id]['spent_time'] = defaultdict(lambda: defaultdict(float))
                    spent_time_data[support_type][user_id]['spent_time'][entry["activity"]["name"]][toplevel_proj] += entry["hours"]
                    spent_time_data[support_type][user_id]['spent_time'][entry["activity"]["name"]]["total"] += entry["hours"]

                try:
                    spent_time_data[support_type][user_id]['issues'].add(entry['issue']['id'])
                except:
                    print(f"WARNING: Time entry without issue id by user '{entry['user']['name']}' in project '{entry['project']['name']}': https://projects.nbis.se/time_entries/{entry['id']}/edit")
                    time_without_issue += entry['hours']
                    #pdb.set_trace()



                #pdb.set_trace()
                # make sure user is defined in the percent matrix
                if user_id not in percent_matrix_data:
                    # predefine percent matrix data keys
                    percent_matrix_data[user_id] = {'Support SMS': 0,
                                                    'Support LTS': 0,
                                                    'Centrala funkt': 0,
                                                    'Support sysbio': 0,
                                                    'Data mgmt': 0,
                                                    'Human data': 0,
                                                    'sysdev': 0,
                                                    'Pipelines & Tools': 0,
                                                    'SCoRe': 0,
                                                    'Training & Nat netw': 0,
                                                    'ELIXIR': 0,
                                                    'BIIF': 0,
                                                    'AIDA DH': 0,
                                                    'Övrigt': 0,
                                                    'total': 0,
                                                    'user': users[user_id],
                                                    }

                # classify time for the percentage matrix
                if (projects[toplevel_proj]['name'] == "National Bioinformatics Support" and entry['activity']['name'] in ["Support", "Consultation"]) or ():
                    percent_matrix_data[user_id]['Support SMS'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                elif projects[toplevel_proj]['name'] == "Long-term Support" and entry['activity']['name'] in ["Support", "Consultation"]:
                    percent_matrix_data[user_id]['Support LTS'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                elif entry.get('issue', {}).get('id') == 3774:
                    percent_matrix_data[user_id]['ELIXIR'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                elif entry['activity']['name'] in ["Professional Development", "Absence (Vacation/VAB/Other)", "Internal NBIS", "Administration", "Internal consultation"]:
                    pass

                elif projects[toplevel_proj]['name'] not in ["National Bioinformatics Support", "Long-term Support"] and entry['activity']['name'] in ["Consultation"]:
                    percent_matrix_data[user_id]['Support SMS'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                    percent_matrix_data[user_id]['total'] += entry['hours']
                elif entry.get('issue', {}).get('id') in [3499, 7000] and entry['activity']['name'] in ["Consultation"]:
                    percent_matrix_data[user_id]['Support SMS'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                elif entry['activity']['name'] == "NBIS Management":
                    percent_matrix_data[user_id]['Centrala funkt'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                elif entry['activity']['name'] in ["Support (DM)", "Consultation (DM)"]:
                    percent_matrix_data[user_id]['Data mgmt'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                elif entry['activity']['name'] in ["Development"]:
                    percent_matrix_data[user_id]['Pipelines & Tools'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                elif entry['activity']['name'] in ["Training", "Outreach"]:
                    percent_matrix_data[user_id]['Training & Nat netw'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                elif projects[toplevel_proj]['name'] not in ["National Bioinformatics Support", "Long-term Support"] and entry['activity']['name'] in ["Support"]:
                    percent_matrix_data[user_id]['Övrigt'] += entry['hours']
                    percent_matrix_data[user_id]['total'] += entry['hours']

                else:
                    print(f"WARNING: Time entry by user '{entry['user']['name']}' in project '{entry['project']['name']}' not classified: https://projects.nbis.se/time_entries/{entry['id']}/edit")

        offset += len(entries)
        print(f"Fetched {offset} time entries")

    if time_without_issue > 0:
        print(f"WARNING: {time_without_issue} hours of time entries without issue id")

    return spent_time_data, percent_matrix_data




def generate_report(spent_time_data, percent_matrix_data, args):
    """
    Summarize the issues as an Excel file and makes statistics as well.

    Args:
        output_path (str): Path to save the Excel file.
    """

    output_path = args.output

    # create workbook
    workbook  = xlsxwriter.Workbook(output_path)

    # define formatting
    col_green         = "92d050" # Accent6
    col_yellow        = "ffd966" # Accent4 60%
    col_red           = "f8cbad" # Accent2 40%
    col_blue          = "bdd7ee" # Accent5 40%
    bold_text         = workbook.add_format({'bold': True})
    percent           = workbook.add_format({'num_format': '0%'})
    percent_bg_green  = workbook.add_format({'num_format': '0%', 'bg_color': col_green}) 
    percent_bg_yellow = workbook.add_format({'num_format': '0%', 'bg_color': col_yellow})
    percent_bg_red    = workbook.add_format({'num_format': '0%', 'bg_color': col_red})
    percent_bg_blue   = workbook.add_format({'num_format': '0%', 'bg_color': col_blue})
    bg_green          = workbook.add_format({'bg_color': col_green}) 
    bg_yellow         = workbook.add_format({'bg_color': col_yellow}) 
    bg_red            = workbook.add_format({'bg_color': col_red}) 
    bg_blue           = workbook.add_format({'bg_color': col_blue}) 

    # create info sheet
    info_sheet  = workbook.add_worksheet("Report info")

    # make a sheet per support type
    sheets = {}
    first_sheet = True
    for support_type in spent_time_data:

        # create expert list sheet, freeze the first column, and make this the active sheet when opening the file
        sheets[support_type] = workbook.add_worksheet(support_type)
        sheets[support_type].freeze_panes(1, 1)
        # set the first support type sheet as the active sheet
        if first_sheet:
            sheets[support_type].activate()
            first_sheet = False
    
    
        # write headers
        headers = [ 'Expert',
                    'Internal consultation',
                    'Administration',
                    'Professional development',
                    'Support',
                    'Teaching',
                    'Development',
                    'Consultation',
                    'Outreach',
                    'Core facility support',
                    'Implementation',
                    'Design',
                    'Internal NBIS',
                    'Consultation (DM)',
                    'Support (DM)',
                    'NBIS management',
                    'Absence',
                    'Total',
                    'Total without absence',
                    'Internal consultation (%)',
                    'Administration (%)',
                    'Professional development (%)',
                    'Support (%)',
                    'Teaching (%)',
                    'Development (%)',
                    'Consultation (%)',
                    'Outreach (%)',
                    'Design (%)',
                    'Internal NBIS (%)',
                    'Absence (%)',
                    'Output',
                    '',
                    '',
                    '"Support"',
                    '"Training"',
                    'Pipelines and tools',
                    'ELIXIR',
                    'Övrigt',
                    'Centrala funktioner',
                    'Summa',
                    'Support (%)',
                    'Training(%)',
                    'Pipelines (%)',
                    'ELIXIR (%)',
                    'Övrigt(%)',
                    'Centrala funktioner (%)',
                    '',
                    'Most common Redmine project',
                    'Issues',
                  ]
        for col_num, header in enumerate(headers):
            sheets[support_type].write(0, col_num, header, bold_text)
    
        # adjust column widths to fit the headers
        for i, header in enumerate(headers):
            sheets[support_type].set_column(i, i, max(len(header), 8)+1 )
        # adjust the name column to fit the longest name
        max_name_length = max([ len(f"{user['firstname']} {user['lastname']}") for user in spent_time_data[support_type].values() ])
        sheets[support_type].set_column(0, 0, max_name_length+1 )
    
        # get the activity names
        activity_names = headers[1:17]
    
        # create mapping between activity names in the report and activity names in Redmine
        activity_map = {'Teaching':'Training',
                        'Professional development':'Professional Development',
                        'Absence':'Absence (Vacation/VAB/Other)',
                        'Core facility support':'Core Facility Report',
                        'NBIS management':'NBIS Management',
                        '':'',
                       }
    
        # make the activity map two-way
        activity_map.update( { key:val for val,key in activity_map.items() } )
    
        # write expert stats
        for row_num, (user_id, user) in enumerate(sorted(spent_time_data[support_type].items(), key=lambda item: item[1]['firstname']), 1):
    
            # init counter
            col_num = 0
    
            # easy one first, name
            sheets[support_type].write(row_num, col_num, f"{user['firstname']} {user['lastname']}")
            col_num += 1
            
            # next up, summarize per activity name
            for activity_name in activity_names:
    
                # get the user's time the the current activity
                user_spent_time = user.get('spent_time', {})
                user_activity = user_spent_time.get(activity_map.get(activity_name, activity_name), {})
    
                # write out the activity's total amount of hours
                sheets[support_type].write(row_num, col_num, user_activity.get("total", ''))
                col_num += 1
    
            
            # write formula for sum of all activity time
            sheets[support_type].write(row_num, col_num, f"=SUM(B{row_num+1}:Q{row_num+1})")
            col_num += 1
    
    
            # write formula for sum of all activity time except absence
            sheets[support_type].write(row_num, col_num, f"=SUM(B{row_num+1}:P{row_num+1})")
            col_num += 1
    
    
            # calculate percentage per activity name
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, B{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, C{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, D{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, E{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, F{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, G{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, H{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, I{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, L{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, M{row_num+1}/S{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(S{row_num+1}=0, 0, Q{row_num+1}/R{row_num+1})", percent)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(@S:S=0, 0, (@B:B+@E:E+@F:F+@G:G+@H:H+@I:I+@N:N+@O:O+@P:P)/@S:S)", percent_bg_green)
            col_num += 1
    
    
            # add 2 empty columns
            sheets[support_type].write(row_num, col_num, '')
            col_num += 1
            sheets[support_type].write(row_num, col_num, '')
            col_num += 1
    
    
            # add the Bengt report
    
            # readability
            n_experts = len(spent_time_data[support_type])
    
            # summarize values
            sheets[support_type].write(row_num, col_num, f"=@E:E + @H:H", bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=@F:F + @I:I", bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=@G:G", bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, "", bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, "", bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, "", bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=@AH:AH + @AI:AI + @AJ:AJ + @AK:AK + @AL:AL + @AM:AM", bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(@AN:AN=0, 0, @AH:AH / @AN:AN)", percent_bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(@AN:AN=0, 0, @AI:AI / @AN:AN)", percent_bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(@AN:AN=0, 0, @AJ:AJ / @AN:AN)", percent_bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(@AN:AN=0, 0, @AK:AK / @AN:AN)", percent_bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(@AN:AN=0, 0, @AL:AL / @AN:AN)", percent_bg_yellow)
            col_num += 1
            sheets[support_type].write(row_num, col_num, f"=IF(@AN:AN=0, 0, @AM:AM / @AN:AN)", percent_bg_yellow)
            col_num += 1
    
    
            # add space
            sheets[support_type].write(row_num, col_num, '')
            col_num += 1
    
    
            # calculate the most common redmine toplevel project
            proj_hour_counts = defaultdict(lambda: defaultdict(float))
            for activity,times in user['spent_time'].items():
                for proj_id,time in times.items():
                    # skip the total counter
                    if proj_id == 'total':
                        continue
                    proj_hour_counts[proj_id] =+ time
    
            # get name of most common redmine toplevel project
            most_common_redmine_project_id   = max(proj_hour_counts, key=proj_hour_counts.get)
            most_common_redmine_project_name = redmine.projects[most_common_redmine_project_id]['name']
    
            # print it
            sheets[support_type].write(row_num, col_num, most_common_redmine_project_name)
            col_num += 1
    
    
            # print out all issues the exper has logged time on
            sheets[support_type].write(row_num, col_num, ",".join(map(str, user['issues'])))
            col_num += 1
    
        ### ok, user specific data is done, now general stats
    
        # reset
        col_num  = 0
        row_num += 1 
    
        # column averages
        sheets[support_type].write(row_num, col_num, 'Average')
        col_num = 19
        for i in range(12):
            col_name = xl_col_to_name(col_num+i) 
            sheets[support_type].write(row_num, col_num+i, f"=AVERAGE({col_name}2:{col_name}{row_num})", percent_bg_red)
        sheets[support_type].set_row(row_num, None, bg_red)
    
    
        # reset
        col_num  = 0
        row_num += 1 
    
        # column averages
        sheets[support_type].set_row(row_num, None, bg_red)
        sheets[support_type].write(row_num, col_num, 'Total')
        col_num += 1
        for activity_name in activity_names:
            # write out the activity's average hours spent
            col_name = xl_col_to_name(col_num) 
            sheets[support_type].write(row_num, col_num, f"=SUM({col_name}2:{col_name}{row_num-1})")
            col_num += 1
    
        # the total columns as well
        sheets[support_type].write(row_num, col_num, f"=SUM(R2:R{row_num-1})")
        col_num += 1
        sheets[support_type].write(row_num, col_num, f"=SUM(S2:S{row_num-1})")
        col_num += 1
    
    


    ### Create the Bengt matrix ###

    # create the sheet, freeze the first column and row
    summary_sheet  = workbook.add_worksheet("Bengt's matrix")
    summary_sheet.freeze_panes(1, 1)

    # write headers
    headers_raw = ['Centrala funkt',
                   'Support SMS',
                   'Support LTS',
                   'Support sysbio',
                   'Data mgmt',
                   'Human data',
                   'sysdev',
                   'Pipelines & Tools',
                   'SCoRe',
                   'Training & Nat netw',
                   'ELIXIR',
                   'BIIF',
                   'AIDA DH',
                   'Övrigt',
                   ]

    headers = ['Expert'] + headers_raw + ['Summa'] + [f"{header} (%)" for header in headers_raw] + ['Summa (%)']

    #pdb.set_trace()
    for col_num, header in enumerate(headers):
        summary_sheet.write(0, col_num, header, bold_text)

    # adjust column widths to fit the headers
    for i, header in enumerate(headers):
        summary_sheet.set_column(i, i, max(len(header), 8)+1 )

    # adjust the name column to fit the longest name
    max_name_length = max([ len(f"{user_entry['user']['firstname']} {user_entry['user']['lastname']}") for user_entry in percent_matrix_data.values() ])
    summary_sheet.set_column(0, 0, max_name_length+1 )

    # write expert stats
    for row_num, (user_id, user_entry) in enumerate(sorted(percent_matrix_data.items(), key=lambda item: f"{item[1]['user']['firstname']} {item[1]['user']['lastname']}"), 1):

        # init counter
        col_num = 0

        # easy one first, name
        #pdb.set_trace()
        summary_sheet.write(row_num, col_num, f"{user_entry['user']['firstname']} {user_entry['user']['lastname']}")
        col_num += 1

        # write hours
        for i, header in enumerate(headers_raw):
            summary_sheet.write(row_num, col_num+i, percent_matrix_data[user_id][header])
        col_num += len(headers_raw)

        # write total hours
        summary_sheet.write(row_num, col_num, f"=SUM(B{row_num+1}:O{row_num+1})")
        col_num += 1

        # write percentages
        for i, header in enumerate(headers_raw):
            summary_sheet.write(row_num, col_num+i, f"=IF({xl_col_to_name(col_num+i-len(headers_raw)-1)}{row_num+1}=0, 0, {xl_col_to_name(col_num+i-len(headers_raw)-1)}{row_num+1}/P{row_num+1})", percent)
        col_num += len(headers_raw)

        # write total percentage
        summary_sheet.write(row_num, col_num, f"=SUM(Q{row_num+1}:AD{row_num+1})", percent)
    #######################################

    workbook.close()
    print(f'Statistics saved as {output_path}')
    return





if __name__ == "__main__":
    args = parse_arguments()

    # check if year is specified
    if args.year:
        args.start_date = f"{args.year-1}-12-01"
        args.end_date   = f"{args.year  }-11-30"

    # login to redmine
    redmine_url, api_key = load_config(args.config)
    redmine = Redmine_utils({'api_key':api_key, 'url':redmine_url})

    # get all projects
    projects = redmine.get_project_structure()
    
    # get group id from group name
    group_id = get_group_id(redmine_url, api_key, args.group_name)

    # get time entries withing the date range requested
    date_interval = {"<=": args.end_date, ">=": args.start_date}
    spent_time_data, percent_matrix_data = get_time_entries(redmine_url, api_key, group_id, date_interval, redmine, projects, args.exclude_timelogbot)

    # write the report
    generate_report(spent_time_data, percent_matrix_data, args)
