#!/uisr/bin/env python3
# -*- coding: utf-8 -*-
import pdb
from pprint import pprint

import argparse
from argparse import RawTextHelpFormatter
import requests
import yaml
import re
import xlsxwriter
import sys
import logging
from Redmine_utils import Redmine_utils

# create logger
logging.basicConfig(
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', 
        level=logging.INFO,
        )
logger = logging.getLogger(__name__)


from collections import defaultdict
def nested_dict():
        return defaultdict(nested_dict)



def redmine_url(type, id):

    base_url = config['url']

    if type == 'issue':
        return f"{base_url}/issues/{id}"

    elif type == 'time_entry':
        return f"{base_url}/time_entries/{id}/edit"




def uni_shortname2longname(uni, issue_id="<not set>"):

    # define translation table
    translation = {
        'Chalmers'                          : 'Chalmers University of Technology',
        'KI'                                : 'Karolinska Institutet',
        'KTH'                               : 'KTH Royal Institute of Technology',
        'LiU'                               : 'Linköping University',
        'LU'                                : 'Lund University',
        'SU'                                : 'Stockholm University',
        'SLU'                               : 'Swedish University of Agricultural Sciences',
        'UmU'                               : 'Umeå University',
        'GU'                                : 'University of Gothenburg',
        'UU'                                : 'Uppsala University',
        'NRM'                               : 'Naturhistoriska Riksmuséet',
        'LNU'                               : 'Linnaeus University',
        'Örebro University'                 : 'Örebro University',
        'Other Swedish University'          : 'Other Swedish University',
        'Other Swedish organization'        : 'Other Swedish organization',
        'Healthcare'                        : 'Healthcare',
        'Industry'                          : 'Industry',
        'International University'          : 'International University',
        'Other international organization'  : 'Other international organization',
        'SciLifeLab'                        : None,
        'Other'                             : None,
        'N/A'                               : None,
    }

    if uni not in translation:
        # should we look at PIs email to determin this_
        logger.warning(f"Uni not in translation list, '{uni}' (issue: {redmine_url('issue', issue_id)})")

    # return translation if it exists, otherwise return None
    return translation.get(uni, None)




def uni_from_pi_email(email, issue_id="<not set>"):
    """
    Guess the project's university based on the PIs email domain.
    """

    # email suffix geographical translation
    domains = {

    'gu'                    : 'University of Gothenburg',
    'akademiska'            : 'Healthcare',
    'bergianska'            : 'Stockholm University',
    'bils'                  : 'Other Swedish University',
    'bioinfo'               : 'Other Swedish University',
    'broadinstitute'        : 'International University',
    'chalmers'              : 'Chalmers University of Technology',
    'csic'                  : 'International University',
    'du'                    : 'Other Swedish University',
    'foi'                   : 'Other Swedish University',
    'folkhalsomyndigheten'  : 'Healthcare',
#    'gmail'                 : 'Other Swedish University',
#    'hotmail'               : 'Other Swedish University',
    'hb'                    : 'Other Swedish University',
    'hhs'                   : 'Other Swedish University',
    'hig'                   : 'Other Swedish University',
    'irfu'                  : 'Uppsala University',
    'karolinska'            : 'Healthcare',
    'kau'                   : 'Other Swedish University',
    'ki'                    : 'Karolinska Institutet',
    'kth'                   : 'KTH Royal Institute of Technology',
    'lio'                   : 'Healthcare',
    'liu'                   : 'Linköping University',
    'lnu'                   : 'Other Swedish University',
    'lth'                   : 'Lund University',
    'ltu'                   : 'Other Swedish University',
    'lu'                    : 'Lund University',
    'ivl'                   : 'Other Swedish organization',
    'ju'                    : 'Other Swedish University',
    'mac'                   : 'Other Swedish University',
    'mdh'                   : 'Other Swedish University',
    'miun'                  : 'Other Swedish University',
    'nrm'                   : 'Naturhistoriska Riksmuséet',
    'oru'                   : 'Other Swedish University',
    'physto'                : 'Stockholm University',
    'regionorebrolan'       : 'Healthcare',
    'regionostergotland'    : 'Healthcare',
#    'scilifelab'            : 'Stockholm University',
    'sh'                    : 'Other Swedish University',
    'sll'                   : 'Healthcare',
    'slu'                   : 'Swedish University of Agricultural Sciences',
    'su'                    : 'Stockholm University',
    'sva'                   : 'Other Swedish organization',
    'umu'                   : 'Umeå University',
    'uu'                    : 'Uppsala University',
    'vgregion'              : 'Other Swedish organization',
    'regionhalland'         : 'Healthcare',
    'regionorebrolan'       : 'Healthcare',
    'rjl'                   : 'Other Swedish organization',
    'his'                   : 'Other Swedish University',
    'ac'                    : 'International University',
    'univ-amu'              : 'International University',
    'usp'                   : 'International University',
    'syonax'                : 'Stockholm University',
    }


    # define a list of persons who are exceptions, for addresses like scilifelab.se etc
    override = {

    'kersli@broadinstitute.org' : 'Uppsala University',
    'afshin.ahmadian@scilifelab.se' : 'KTH Royal Institute of Technology',
    'anders.andersson@scilifelab.se' : 'KTH Royal Institute of Technology',
    'ann-charlotte.sonnhammer@scilifelab.se' : 'KTH Royal Institute of Technology',
    'arne@bioinfo.se' : 'Stockholm University',
    'bastiaan.evers@scilifelab.se' : 'Karolinska Institutet',
    'bjorn.nystedt@scilifelab.se' : 'Uppsala University',
    'bo.lundgren@scilifelab.se' : 'Stockholm University',
    'ellen.sherwood@scilifelab.se' : 'Karolinska Institutet',
    'emma.lundberg@scilifelab.se' : 'KTH Royal Institute of Technology',
    'erik.sonnhammer@scilifelab.se' : 'Stockholm University',
    'erikbong@mac.com' : 'Swedish University of Agricultural Sciences',
    'fredrik.levander@bils.se' : 'Lund University',
    'grabherr@broadinstitute.org' : 'Uppsala University',
    'henrik.lantz@bils.se' : 'Uppsala University',
    'jens.carlsson.lab@gmail.com' : 'Stockholm University',
    'joakim.lundeberg@scilifelab.se' : 'KTH Royal Institute of Technology',
    'jochen.schwenk@scilifelab.se' : 'KTH Royal Institute of Technology',
    'johan.reimegard@scilifelab.se' : 'Uppsala University',
    'johanna.wallenius@hhs.se' : 'Other Swedish University',
    'klas.straat@scilifelab.se' : 'KTH Royal Institute of Technology',
    'lars.arvestad@scilifelab.se' : 'KTH Royal Institute of Technology',
    'lukas.kall@scilifelab.se' : 'Stockholm University',
    'lukasz.huminiecki@scilifelab.se' : 'Karolinska Institutet',
    'lukaszhuminieckionlypersonal@gmail.com' : 'Karolinska Institutet',
    'majid.osman@regionostergotland.se' : 'Linköping University',
    'marc.friedlander@scilifelab.se' : 'Stockholm University',
    'martin.norling@bils.se' : 'Uppsala University',
    'mathias.uhlen@scilifelab.se' : 'KTH Royal Institute of Technology',
    'mats.nilsson@scilifelab.se' : 'Stockholm University',
    'max.kaller@scilifelab.se' : 'Karolinska Institutet',
    'olof.emanuelsson@scilifelab.se' : 'KTH Royal Institute of Technology',
    'petter.brodin@scilifelab.se' : 'Karolinska Institutet',
    'sara.light@scilifelab.se' : 'Stockholm University',
    'silvano.garnerone@scilifelab.se' : 'Karolinska Institutet',
    'tanja.slotte@scilifelab.se' : 'Stockholm University',
    'thomas.svensson@scilifelab.se' : 'Karolinska Institutet',
    'bjorn.claremar@gmail.com' : 'Uppsala University',
    'olga.dethlefsen@bils.se' : 'Stockholm University',
    'tanjavanharn@hotmail.com' : 'Karolinska Institutet',
    'mikael.borg@bils.se' : 'Uppsala University',
    'aganna@broadinstitute.org' : 'Karolinska Institutet',
    'jingwang368@gmail.com' : 'Umeå University',
    'eriking@stanford.edu' : 'Uppsala University', 
    'mattias@liefvendahl.se' : 'Chalmers University of Technology', 
    'henrik.lantz@nbis.se' : 'Uppsala University', 
    'nieuwenhuis@bio.lmu.de' : 'Uppsala University', 
    'olga.dethlefsen@nbis.se' : 'Stockholm University', 
    'm.hoeppner@ikmb.uni-kiel.de' : 'Uppsala University', 
    'david.boersma@medaustron.at' : 'Uppsala University', 
    'fredrik.levander@nbis.se' : 'Lund University', 
    'martin.norling@nbis.se' : 'Uppsala University', 
    'mikael.borg@nbis.se' : 'Stockholm University', 
    'roy.francis@nbis.se' : 'Uppsala University', 
    'strassert@protist.eu' : 'Uppsala University', 
    'mait@ebc.ee' : 'International University', 
    'agata.smialowska@nbis.se' : 'Stockholm University', 
    'lriemann@bio.ku.dk' : 'International University', 
    'kisand@ut.ee' : 'Uppsala University',  
    'willian.silva@evobiolab.com' : 'Uppsala University', 
    'robin@binf.ku.dk' : 'International University', 
    'maarit.holtta-vuori@helsinki.fi' : 'International University', 
    'ricardo_eyre@yahoo.es' : 'International University', 
    'caroline.callot@inra.fr' : 'International University', 
    'albin@binf.ku.dk' : 'International University', 
    'esko.pakarinen@utu.fi' : 'International University', 
    'rlh@sejet.dk' : 'International University', 
    'thomas.smol@chru-lille.fr' : 'International University', 
    'jacques.dainat@nbis.se' : 'Uppsala University', 
    'rasmus.agren@astrazeneca.com' : 'Other Swedish organization', 
    'strassert@gmx.net' : 'Uppsala University', 
    'mareschal@ovsa.fr' : 'Karolinska Institutet', 
    'jana.biermann@outlook.com' : 'University of Gothenburg', 
    'stefan.franzen@registercentrum.se' : 'Healthcare', 
    'lotta.wik@olink.com' : 'Other Swedish organization', 
    'morgane.vacher@univ-nantes.fr' : 'International University', 
    'ricky.ansell@polisen.se' : 'Other Swedish organization', 
    'marcin.wojewodzic@kreftregisteret.no' : 'Foreign organization', 
    'mikk.espenberg@ut.ee' : 'International University', 
    'moa@genagon.com' : 'Other Swedish organization', 
    'mueller@orn.mpg.de' : 'International University', 
    'darek.kedra@gumed.edu.pl' : 'International University', 
    'ejvest@utu.fi' : 'International University', 
    'mbaldwin@orn.mpg.de' : 'International University', 
    '' : '', 
    '' : '', 
    '' : '', 
    }

    # check if email is a special one
    if email in override:
        return override[email.lower()]

    # check if the domain is known
    else:
        # make sure the email has a @ in it
        domain_split = email.split('@')
        if len(domain_split) == 1:
            return None

        # get the 2nd last element, like uu from domain.uu.se
        domain = domain_split[-1].split(".")[-2]

        # if it is known
        if domain in domains:
            return domains[domain]

        # if it is not known
        else:
            logger.warning(f"Issue organization not known, and PI email cannot resolve which organization it belongs to: {email} (issue: {redmine_url('issue', issue_id)})")
            return None





def fetch_time_entries(args, url, api_key):
    """
    Fetches the time entries within the specified date range and project ID.

    Args:
        start_date (str): Start date in format 'YYYY-MM-DD'.
        end_date (str): End date in format 'YYYY-MM-DD'.
        project_id (int): Project ID.
        url (str): Redmine URL.
        api_key (str): Redmine API key.

    Returns:
        set: Set of unique issue IDs.
    """
    params = {
        'key': api_key,
        'spent_on': f'><{args.start_date}|{args.end_date}',
#        'project_id': project_id,
        'limit': 100,
        'offset': 0
    }
    issue_ids = nested_dict()

    response = requests.get(f'{url}/time_entries.json', params=params)
    response.raise_for_status()
    data = response.json()

    total_count = data['total_count']

    # Fetch time entries in batches
    while params['offset'] < total_count:
        response = requests.get(f'{url}/time_entries.json', params=params)
        response.raise_for_status()
        data = response.json()

        time_entries = data['time_entries']

        for entry in time_entries:
            try:
                issue_ids[entry['issue']['id']][entry['activity']['name']] += entry['hours']

            except:
                try:
                    issue_ids[entry['issue']['id']][entry['activity']['name']] = entry['hours']
                except Exception as e:
                    logger.debug(f"Time entry not tied to issue: {redmine_url('time_entry', entry['id'])}")

        params['offset'] += params['limit']

        # Calculate progress percentage
        progress = min(params['offset'], total_count) / total_count * 100
        print(f'Fetching time entries: {progress:.2f}% complete               ', end='\r')

    print('Fetching time entries: 100% complete                               ')
    
    return issue_ids

def fetch_issue_details(issue_ids, url, api_key, project_filter):
    """
    Fetches the detailed information about each issue.

    Args:
        issue_ids (set): Set of unique issue IDs.
        url (str): Redmine URL.
        api_key (str): Redmine API key.

    Returns:
        list: List of issue details.
    """
    issue_details = []

    for i, issue_id in enumerate(issue_ids, 1):
        response = requests.get(f'{url}/issues/{issue_id}.json', params={'key': api_key})
        response.raise_for_status()
        data = response.json()

        # Calculate progress percentage
        progress = i / len(issue_ids) * 100
        print(f'Fetching issue details: {progress:.2f}%                ', end='\r')

#        # skip projects from the wrong trackers
#        if data['issue']['tracker'] not in ['Support']:

        # skip issues from other projects than defined below#        if data['issue'] ['project']['name'] not in ['National Bioinformatics Support', ] and not re.search('^Round ', data['issue'] ['project']['name']):
        # filter out everything not in the requested filter list
        #pdb.set_trace()
        if data['issue'] ['project']['id'] not in project_filter:
            continue
       
        data['issue']['spent_per_activity'] = dict(issue_ids[issue_id])
        issue_details.append(data['issue'])


    print('Fetching issue details: 100%                    ')

    return issue_details





def get_custom_field(issue, field_name):


    # get field value
    field_value = [ field['value'] for field in issue['custom_fields'] if field['name']==field_name ]
    if len(field_value) > 0:
        field_value = field_value[0]
    else:
        field_value = ''

    return field_value




def generate_vr_report(args, issue_details, output_path):
    """
    Saves the issues as an Excel file and makes statistics as well.

    Args:
        issue_details (list): List of dictionaries containing issues.
        output_path (str): Path to save the Excel file.
    """

    # create workbook and the info sheet
    workbook  = xlsxwriter.Workbook(output_path)
    info_sheet  = workbook.add_worksheet("Report info")

    # create project list sheet
    pl_sheet  = workbook.add_worksheet("Project list")
    pl_sheet.activate()
    bold_text = workbook.add_format({'bold': True})

    # print metadata
    info_sheet.write("A1", "General info", bold_text)
    info_sheet.write("A2", "Start date:")
    info_sheet.write("B2", args.start_date)
    info_sheet.write("A3", "End date:")
    info_sheet.write("B3", args.end_date)
    info_sheet.write("A4", "Redmine projects:")
    info_sheet.write("B4", ", ".join(args.project_id))


    # write headers
    headers = ['Project ID', 'PI first name', 'PI last name', 'email', 'Organization', 'SCB Subject Code', 'Sex', 'Tracker', 'LTS project ID', 'Publications', 'Funding', 'Spent time this period', 'Spent time total']
    for col_num, header in enumerate(headers):
        pl_sheet.write(0, col_num, header, bold_text)


    # write data rows
    for row_num, issue in enumerate(issue_details, 1):

        # get PI first and last name
        pi_name       = get_custom_field(issue, 'Principal Investigator')
        pi_name_split = pi_name.split(' ')
        pi_last_name  = pi_name_split[-1]
        pi_first_name = " ".join(pi_name_split[:-1])

        # summarize the hours spent the requested period
        time_spent_this_period = sum([ hours for hours in issue['spent_per_activity'].values() ])

        #pdb.set_trace()

        # print values
        pl_sheet.write(row_num, 0,  issue.get('id',''))
        pl_sheet.write(row_num, 1,  pi_first_name)
        pl_sheet.write(row_num, 2,  pi_last_name)
        pl_sheet.write(row_num, 3,  get_custom_field(issue, 'PI e-mail'))
        pl_sheet.write(row_num, 4,  uni_shortname2longname(get_custom_field(issue, 'Organization')))
        pl_sheet.write(row_num, 5,  get_custom_field(issue, 'SCB Subject Code'))
        pl_sheet.write(row_num, 6,  get_custom_field(issue, 'PI Gender'))
        pl_sheet.write(row_num, 7,  issue.get('tracker',{}).get('name',''))
        pl_sheet.write(row_num, 8,  get_custom_field(issue, 'WABI ID'))
        pl_sheet.write(row_num, 9,  get_custom_field(issue, 'Publication(s)'))
        pl_sheet.write(row_num, 10, get_custom_field(issue, 'Funding'))
        pl_sheet.write(row_num, 11, time_spent_this_period)
        pl_sheet.write(row_num, 12, issue.get('spent_hours',''))







    ### do other statistics

    # PIs per uni
    if 1:
        ppo_sheet = workbook.add_worksheet("Projects per org")

        # print headers
        ppo_sheet.write(f"A1", "Organization", bold_text)
        ppo_sheet.write(f"B1", "#", bold_text)

        # print the UNIQUE function to get all org names
        ppo_sheet.write(f'Y1', "Raw unsorted data for the plot, don't touch.")
        ppo_sheet.write(f"Y2", "=UNIQUE('Project list'!$E$2:'Project list'!$E$10000)") # how to get rid of the 0 0 ?

        # print the counting function
        for row_num in range(2,200):

            # for each row, print the number of occurences in the project list of the corresponding organization name, only if there is a org name on the current row
            ppo_sheet.write(f"Z{row_num}", f"=IF( ISBLANK(Y{row_num}), \"\", COUNTIF('Project list'!$E$2:'Project list'!$E$1000, Y{row_num}))")


        # create a sorted range for the pie chart
        ppo_sheet.write('A2', f"=SORT(Y2:Z10000, 2)") # how to get rid of the spill over range filled with 0?

        # create pie chart
        ppo_chart = workbook.add_chart({'type': 'pie'})

        # add data series
        #[sheetname, first_row, first_col, last_row, last_col].
        ppo_chart.add_series({
            'name'       : '# projects',
            'categories' : ['Projects per org', 1, 0, 1000, 0],
            'values'     : ['Projects per org', 1, 1, 1000, 1],
            "data_labels": {"category": True, 'position': 'outside_end'}
        })

        # tweak the chart
        ppo_chart.set_title({'name': 'Projects per organization'})
        ppo_chart.set_legend({'position': 'none'})
        ppo_chart.set_size({'x_scale': 1.5, 'y_scale': 2})
        ppo_chart.set_style(10)

        # insert the chart
        ppo_sheet.insert_chart('E2', ppo_chart)


        ## chart style gallery, devel
        #for i in range(1,49):

        #    # create pie chart
        #    ppo_chart = workbook.add_chart({'type': 'pie'})

        #    # add data series
        #    #[sheetname, first_row, first_col, last_row, last_col].
        #    ppo_chart.add_series({
        #        'name'      : '# projects',
        #        'categories': ['Projects per org', 1, 0, 1000, 0],
        #        'values'    : ['Projects per org', 1, 1, 1000, 1],
        #    })

        #    # set chart title, duh
        #    ppo_chart.set_title({'name': 'Projects per organization'})
        #    # set chart style
        #    ppo_chart.set_style(i)

        #    # insert the chart
        #    ppo_sheet.write(f"D{2+i*15}", i)
        #    ppo_sheet.insert_chart(f"E{2+i*15}", ppo_chart)




    workbook.close()
    print(f'Statistics saved as {output_path}')





def generate_sll_report(issue_details, project_id, start_date, end_date, output_path):
    """
    Summarize the issues as an Excel file and makes statistics as well.

    Args:
        issue_details (list): List of dictionaries containing issues.
        output_path (str): Path to save the Excel file.
    """

    # define dict of consortium members
    consortium_members = {
            'Chalmers University of Technology':1,
            'Karolinska Institutet':1,
            'KTH Royal Institute of Technology':1,
            'Linköping University':1,
            'Lund University':1,
            'Stockholm University':1,
            'Swedish University of Agricultural Sciences':1,
            'Umeå University':1,
            'University of Gothenburg':1,
            'Uppsala University':1,
            'Naturhistoriska Riksmuséet':1,
        }
    # init counter
    n_active  = 0
    n_consult = 0
    n_pis     = set()

    # create workbook and the info sheet
    workbook  = xlsxwriter.Workbook(output_path)
    info_sheet  = workbook.add_worksheet("Report info")

    # create project list sheet
    pl_sheet  = workbook.add_worksheet("PI list")
    pl_sheet.activate()
    bold_text = workbook.add_format({'bold': True})

    # create raw data sheet
    rd_sheet  = workbook.add_worksheet("Raw data")
    rd_sheet.write("A1","Project ID", bold_text)
    rd_sheet.write("B1","LTS project ID", bold_text)
    rd_sheet.write("C1","PI first name", bold_text)
    rd_sheet.write("D1","PI last name", bold_text)
    rd_sheet.write("E1","PI email", bold_text)
    rd_sheet.write("F1","Organization", bold_text)
    rd_sheet.write("G1","SBC subject code", bold_text)
    rd_sheet.write("H1","Sex", bold_text)
    rd_sheet.write("I1","Type", bold_text)
    rd_sheet.write("J1","Consortium", bold_text)
    rd_sheet.write("K1","Spent hours this period", bold_text)
    rd_sheet.write("L1","Redmine project", bold_text)
    rd_sheet.write("M1","PI identifier", bold_text)


    # create a email to name translation table
    name2email = {}
    email2name = {}
    for issue in issue_details:

        # readability
        pi_email = get_custom_field(issue, 'PI e-mail')

        # get PI name
        pi_name  = get_custom_field(issue, 'Principal Investigator')

        # make a lookup table for email to name and back
        if pi_email and pi_name:
            name2email[pi_name.lower()]  = pi_email.lower()
            email2name[pi_email.lower()] = pi_name.lower()


    # summarize data per PI
    pis = dict()
    for i, issue in enumerate(issue_details, 2):



        # count stuff
        if issue['tracker']['name'] in ['Support', 'Task', 'Partner Project'] :
            n_active  += 1
            pi_email = get_custom_field(issue, 'PI e-mail')
            if pi_email:
                n_pis.add(pi_email.lower())
            else:
                # we still want to count something
                n_pis.add(get_custom_field(issue, 'Principal Investigator'))


        elif issue['tracker']['name'] == 'Consultation':
            n_consult += 1

        # readability
        pi_email = get_custom_field(issue, 'PI e-mail')

        # get PI first and last name
        pi_name       = get_custom_field(issue, 'Principal Investigator')

        # catch None PIs
        if not pi_name:
            pi_name = ''
        
        pi_name_split = pi_name.split(' ')
        pi_last_name  = pi_name_split[-1]
        pi_first_name = " ".join(pi_name_split[:-1])

        # if the email is empty
        if not pi_email:
    
            # has the pi name been seen before and already connected to an email?
            if pi_name.lower() in name2email:
                pi_email = name2email[pi_name.lower()]
            
            else:

                # if there is a PI name
                if pi_name:
                    pi_email = pi_name.lower()
                else:
                    # use the issue name instead
                    pi_email = issue['subject']

        # summarize the hours spent the requested period
        time_spent_this_period = sum([ hours for hours in issue['spent_per_activity'].values() ])

        # get PI affiliation
        pi_affiliation = uni_shortname2longname(get_custom_field(issue, 'Organization'), issue['id'])

        # if a valid affiliation was not found, try getting it through the PIs email instead
        if not pi_affiliation:

            # check that there is an email and try to get affiliation from that
            if pi_email:
                pi_affiliation = uni_from_pi_email(pi_email, issue['id'])

            # if it was still not found
            if not pi_affiliation:
                pi_affiliation = ''

        # if affiliation is other, specify it
        pi_affiliation_details = ''
        if pi_affiliation in ['Other Swedish University', 'International University', 'Healthcare', 'Industry', 'Other Swedish organization', 'Other international organization', '']:
            # get organization name
            pi_affiliation_details = get_custom_field(issue, 'Organization') 
            if pi_affiliation_details == '' or pi_affiliation_details == 'Other':

                # set details to PI email url if organization is not known
                pi_affiliation_details = pi_email.split('@').pop() # pop, in case the email doesnt contain a @

        # summarize time spent for pis that have been seen before
        try:
            pis[pi_email.lower()]['time_spent'] += time_spent_this_period

        # if the pi has not been seen before
        except:
            pis[pi_email.lower()] = {'pi_first_name'         : pi_first_name,
                                     'pi_last_name'          : pi_last_name,
                                     'pi_email'              : pi_email.lower(),
                                     'pi_affiliation'        : pi_affiliation,
                                     'pi_affiliation_details': pi_affiliation_details,
                                     'time_spent'            : time_spent_this_period
                                    }

        # convert the tracker name to a type that matches the rest of the reporting
        issue['report_type'] = issue['tracker']['name']
        if issue['project']['name'] == 'Bioimage Informatics':
            issue['report_type'] = 'BIIF'
        elif re.match(r'Round \d{4}-\d+', issue['project']['name']):
            issue['report_type'] = 'LTS'
        if issue['tracker']['name'] == 'Partner Project':
            issue['report_type'] = 'PP'


        # print raw data
        rd_sheet.write(f"A{i}", issue['id'])
        rd_sheet.write(f"B{i}", get_custom_field(issue, 'WABI ID'))
        rd_sheet.write(f"C{i}", pi_first_name)
        rd_sheet.write(f"D{i}", pi_last_name)
        rd_sheet.write(f"E{i}", pi_email)
        rd_sheet.write(f"F{i}", pi_affiliation)
        rd_sheet.write(f"G{i}", get_custom_field(issue, 'SCB Subject Code'))
        rd_sheet.write(f"H{i}", get_custom_field(issue, 'PI Gender'))
        rd_sheet.write(f"I{i}", issue['report_type'])
        rd_sheet.write(f"J{i}", consortium_members.get(pi_affiliation, 0))
        rd_sheet.write(f"K{i}", sum([ hours for hours in issue['spent_per_activity'].values() ]))
        rd_sheet.write(f"L{i}", issue['project']['name'])
        rd_sheet.write(f"M{i}", pi_email.lower())



        




    # print metadata
    info_sheet.write("A1", "General info", bold_text)
    info_sheet.write("A2", "Start date:")
    info_sheet.write("B2", start_date)
    info_sheet.write("A3", "End date:")
    info_sheet.write("B3", end_date)
    info_sheet.write("A4", "Redmine projects:")
    info_sheet.write("B4", ", ".join(project_id))
    info_sheet.write("A6", "Active support projects:")
    info_sheet.write("B6", n_active)
    info_sheet.write("A7", "Booked consultations:")
    info_sheet.write("B7", n_consult)
    info_sheet.write("A8", "Unique PIs (ex. consultations):")
    info_sheet.write("B8", len(n_pis))


    # write headers
    headers = ['PI first name', 'PI last name', 'PI e-mail', 'Affiliation', 'Non-specific affiliation', 'Time spent this period']
    for col_num, header in enumerate(headers):
        pl_sheet.write(0, col_num, header, bold_text)


    # write data rows
    for row_num, pi in enumerate(pis.values(), 1):

        # print values
        pl_sheet.write(row_num, 0,  pi['pi_first_name'])
        pl_sheet.write(row_num, 1,  pi['pi_last_name'])
        pl_sheet.write(row_num, 2,  pi['pi_email'])
        pl_sheet.write(row_num, 3,  pi['pi_affiliation'])
        pl_sheet.write(row_num, 4,  pi['pi_affiliation_details'])
        pl_sheet.write(row_num, 5,  pi['time_spent'])







    ### do other statistics

    # PIs per uni
    if 0:
        ppo_sheet = workbook.add_worksheet("Projects per org")

        # print headers
        ppo_sheet.write(f"A1", "Organization", bold_text)
        ppo_sheet.write(f"B1", "#", bold_text)

        # print the UNIQUE function to get all org names
        ppo_sheet.write(f'Y1', "Raw unsorted data for the plot, don't touch.")
        ppo_sheet.write(f"Y2", "=UNIQUE('Project list'!$E$2:'Project list'!$E$10000)") # how to get rid of the 0 0 ?

        # print the counting function
        for row_num in range(2,200):

            # for each row, print the number of occurences in the project list of the corresponding organization name, only if there is a org name on the current row
            ppo_sheet.write(f"Z{row_num}", f"=IF( ISBLANK(Y{row_num}), \"\", COUNTIF('Project list'!$E$2:'Project list'!$E$1000, Y{row_num}))")


        # create a sorted range for the pie chart
        ppo_sheet.write('A2', f"=SORT(Y2:Z10000, 2)") # how to get rid of the spill over range filled with 0?

        # create pie chart
        ppo_chart = workbook.add_chart({'type': 'pie'})

        # add data series
        #[sheetname, first_row, first_col, last_row, last_col].
        ppo_chart.add_series({
            'name'       : '# projects',
            'categories' : ['Projects per org', 1, 0, 1000, 0],
            'values'     : ['Projects per org', 1, 1, 1000, 1],
            "data_labels": {"category": True, 'position': 'outside_end'}
        })

        # tweak the chart
        ppo_chart.set_title({'name': 'Projects per organization'})
        ppo_chart.set_legend({'position': 'none'})
        ppo_chart.set_size({'x_scale': 1.5, 'y_scale': 2})
        ppo_chart.set_style(10)

        # insert the chart
        ppo_sheet.insert_chart('E2', ppo_chart)


        ## chart style gallery, devel
        #for i in range(1,49):

        #    # create pie chart
        #    ppo_chart = workbook.add_chart({'type': 'pie'})

        #    # add data series
        #    #[sheetname, first_row, first_col, last_row, last_col].
        #    ppo_chart.add_series({
        #        'name'      : '# projects',
        #        'categories': ['Projects per org', 1, 0, 1000, 0],
        #        'values'    : ['Projects per org', 1, 1, 1000, 1],
        #    })

        #    # set chart title, duh
        #    ppo_chart.set_title({'name': 'Projects per organization'})
        #    # set chart style
        #    ppo_chart.set_style(i)

        #    # insert the chart
        #    ppo_sheet.write(f"D{2+i*15}", i)
        #    ppo_sheet.insert_chart(f"E{2+i*15}", ppo_chart)




    workbook.close()
    print(f'Statistics saved as {output_path}')






def check_required_args(args):
    """
    Makes sure that we have enough info to generate a report.
    """

    # check if at least one of --sll and --vr is set
    if not (args.sll or args.vr):
        sys.exit("ERROR: At least one of --sll or --vr must be specified.")

    # check if either --long-term, --sm-term or project-[id, name] is set.
    if not (args.long_term or args.sm_term or args.project_id or args.project_name or args.biif):
        sys.exit("ERROR: No project(s) selected, either --long-term, --sm-term, --biif, --project-id or --project-name must be set.")

    # check that some timeframe is set
    if not (args.year or (args.start_date and args.end_date)):
        sys.exit("ERROR: No timeframe set, either --year or --start-date and --end-date must be set.")


def resolve_args(args):
    """
    Resolves the shortcut arguments (e.g. --dm, --long-term) to the actual arguments.
    """

    # resolve --sm-term
    if args.sm_term:

        sm_term_project_name = 'National Bioinformatics Support'
        logging.info(f'--sm-term specified, adding "{sm_term_project_name}" to --project-id list.')

        try:
            args.project_id += [sm_term_project_name]
        except:
            args.project_id  = [sm_term_project_name]



    # resolve --biif
    if args.biif:

        biif_project_name = 'Bioimage Informatics'
        logging.info(f'--biif specified, adding "{biif_project_name}" to --project-id list.')

        try:
            args.project_id += [biif_project_name]
        except:
            args.project_id  = [biif_project_name]



    # resolve --long-term
    if args.long_term:

        long_term_project_name = "Long-term Support"
        logging.info(f'--long-term specified, adding "{long_term_project_name}" to --project-id list, and setting --recursive.')

        try:
            args.project_id += [long_term_project_name]
        except:
            args.project_id  = [long_term_project_name]
        args.recursive = True



    # resolve --dm
    if args.dm:

        dm_activity_filter_text = "[DM]"
        logging.info(f'--dm specified, adding "{dm_activity_filter_text}" to --activity-filter list.')

        try:
            args.activity_filter += [dm_activity_filter_text]
        except:
            args.activity_filter  = [dm_activity_filter_text]



    # resolve --year
    if args.year:

        logging.info(f"--year specified, setting --start-date to {args.year-1}-12-01 and --end-date to {args.year}-11-30")
        args.start_date = f"{args.year-1}-12-01"
        args.end_date   = f"{args.year  }-11-30"




    return args




def get_redmine_project_structure(config):
    """
    Build a dict with the strucutre of the Redmine projects, and a name-id translation table.
    """

    params = {
        'key': config['api_key'],
        'limit': 100,
        'offset': 0
    }

    # get the project list
    redmine_projects = []
    
    response = requests.get(f"{config['url']}/projects.json", params=params)
    response.raise_for_status()
    data = response.json()

    redmine_projects.extend(data['projects'])

    total_count = data['total_count']
    while params['offset'] < total_count:
        response = requests.get(f"{config['url']}/projects.json", params=params)
        response.raise_for_status()
        data = response.json()


        redmine_projects.extend(data['projects'])

        params['offset'] += params['limit']

        # Calculate progress percentage
        progress = min(params['offset'], total_count) / total_count * 100
        print(f'Fetching Redmine project: {progress:.2f}% complete                ', end='\r')

    print('Fetching Redmine projects: 100% complete                             ')

    # Initialize an empty dictionary to store the hierarchy
    projects_dict = {}

    # restructure projects at a dict
    redmine_projects = { proj['id']:proj for proj in redmine_projects }

    redmine_projects['utils']                    = {}
    redmine_projects['utils']['name2id']         = {}
    redmine_projects['utils']['id2name']         = {}
    redmine_projects['utils']['name2identifier'] = {}
    redmine_projects['utils']['identifier2name'] = {}
    redmine_projects['utils']['id2identifier']   = {}
    redmine_projects['utils']['identifier2id']   = {}


    # Function to recursively build the dictionary
    def build_project_hierarchy(project, child_ids):
        
        # add name conversions to translation tables
        redmine_projects['utils']['name2id'][project['name']]               = project['id']
        redmine_projects['utils']['id2name'][project['id']]                 = project['name']
        redmine_projects['utils']['name2identifier'][project['name']]       = project['identifier']
        redmine_projects['utils']['identifier2name'][project['identifier']] = project['name']
        redmine_projects['utils']['id2identifier'][project['id']]           = project['identifier']
        redmine_projects['utils']['identifier2id'][project['identifier']]   = project['id']

        # if there are any children to be added
        if len(child_ids) > 0:
            try:
                redmine_projects[project['id']]['children'].update(child_ids)
            except:
                redmine_projects[project['id']]['children'] = set()
                redmine_projects[project['id']]['children'].update(child_ids)

        # if we have reached the top
        if 'parent' not in project:
            return

        # add this project and its children to the list of children
        child_ids.add(project['id'])
        child_ids.update(redmine_projects[project['id']].get('children', set()))

        # pass on the child list to the parent
        build_project_hierarchy(redmine_projects[project['parent']['id']], child_ids=child_ids)


    # process each project
    for key,project in redmine_projects.items():

        # skip utility key
        if key == 'utils':
            continue

        build_project_hierarchy(project, child_ids=set())




    return redmine_projects


def create_project_filter_list(args, redmine_projects):
    """
    Creates a list of project ids we want to filter on. Based on --project-id and --recursive.
    """

    # init
    project_id_filter_list = set()

    # convert all text names to project id#
    for name in args.project_id:

        match_found = False

        # for all redmine projects
        for project in redmine_projects.values():

            # check if the name matches the id, name or identifier
            if str(name) == str(project['id']) or name == project['identifier'] or name == project['name']:

                # add the project id to the filter lsit
                project_id_filter_list.add(project['id'])

                # if recursive is set, add all children if any as well
                if args.recursive:
                    project_id_filter_list.update(project.get('children', []))

                # jump to next name
                match_found = True
                break

        # it didn't match any project
        if not match_found:

            if args.force:
                logging.warn(f'Project identifier found no match among all Redmine projects: "{name}"')
            else:
                #pdb.set_trace()
                logging.error(f'Project identifier found no match among all Redmine projects: "{name}"')
                sys.exit(-1)

    return project_id_filter_list


def main():


    # define arguments
    parser = argparse.ArgumentParser(
            description="Generate reports based on information from Redmine.",
            epilog="""Example runs:

# standard SciLifeLab report for short-medium term projects 2023
python3 generate_report.py -c config.yaml --sll --sm-term   --year 2023 -o sll_2023.xlsx

# standard SciLifeLab report for long term projects 2023
python3 generate_report.py -c config.yaml --sll --long-term --year 2023 -o sll_2023.xlsx

# standard VR report for short-medium term projects 2023
python3 generate_report.py -c config.yaml --vr  --sm-term   --year 2023 -o sll_2023.xlsx

# standard VR report for long term projects 2023
python3 generate_report.py -c config.yaml --vr  --long-term --year 2023 -o sll_2023.xlsx
""", formatter_class=RawTextHelpFormatter)

    required_files_group = parser.add_argument_group('Required files')
    required_files_group.add_argument('-c', '--config',     help='Config file path', required=True,)
    required_files_group.add_argument('-o', '--output',     help='Output file path', required=True,)

    shortcuts_group = parser.add_argument_group('Shortcut options')
    shortcuts_group.add_argument('--dm',                    help='Use to only consider time logged in an activity with "[DM]" in its name.', action='store_true')
    shortcuts_group.add_argument('--long-term',             help='Use to only include project in and under the "Long-term Support" project.', action='store_true')
    shortcuts_group.add_argument('--sm-term',               help='Use to only include project in and under the "National Bioinformatics Support" project.', action='store_true')
    shortcuts_group.add_argument('--biif',                  help='Use to only include project in and under the "Bioimage Informatics" project.', action='store_true')
    shortcuts_group.add_argument('--sll',                   help='Use to include the SciLifeLab report specific statistics in the output file.',      action='store_true')
    shortcuts_group.add_argument('--vr',                    help='Use to include the Vetenskapsrådet report specific statistics in the output file.', action='store_true')
    shortcuts_group.add_argument('-y', '--year',            help='Shortcut to select start and end date as $(YEAR-1)-dec to $YEAR-dec'         , type=int)

    filters_group = parser.add_argument_group('Filter options')
    filters_group.add_argument('--project-id',              help='Redmine Project name/id#/identifier to filer out (comma separated if multiple)', type=str, required=False,)
    filters_group.add_argument('--activity-filter',         help='Words used to filter out activity types (comma separated if multiple).', type=str, required=False,)
    filters_group.add_argument('-s', '--start-date',        help='Start date in YYYY-MM-DD format', type=str, required=False,)
    filters_group.add_argument('-e', '--end-date',          help='End date in YYYY-MM-DD format',   type=str, required=False,)
    filters_group.add_argument('-f', '--force',             help='Use to continue generating the report even if there are warnings.', action='store_true')
    filters_group.add_argument('-r', '--recursive',         help='Use together with --project-id or --project-name to recursivly include all subprojects to the project specified.', action='store_true')

    global args
    args = parser.parse_args()


    # check required args
    check_required_args(args)

    # read the config file
    global config
    with open(args.config) as f:
        config = yaml.safe_load(f)

    # resolve the arguments
    args = resolve_args(args)

    # construct the project hierarchy
    redmine = Redmine_utils(config)
    redmine_projects = get_redmine_project_structure(config)


    # generate list of projects to filiter out
    project_id_filter_list = create_project_filter_list(args, redmine_projects)

    #pdb.set_trace()

    issue_ids       = fetch_time_entries(args, config['url'], config['api_key'])
    issue_details   = fetch_issue_details(issue_ids, config['url'], config['api_key'], project_id_filter_list)
    #statistics      = generate_statistics(issue_details)

    # if sll
    if args.sll:
        generate_sll_report(issue_details, args.project_id, args.start_date, args.end_date,  args.output)

if __name__ == '__main__':
    main()
