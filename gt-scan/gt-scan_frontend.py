#!/usr/bin/python
import sys
import os
import zipfile
import re
import time
from threading import Thread
import threading
#Root path
base_path = os.path.dirname(os.path.abspath(__file__))
#Insert local directories into path (required to load modules in 'libs' directory)
sys.path.insert(0, base_path)
sys.path.insert(0, os.path.join(base_path, 'libs'))

import configparser
import web
from web import form
import model
import api

import sqlite3 as db

#Initialize web server stuff
urls = (
    '/', 'index',
    '/submit/', 'Submit',
    '/api/', api.app_api,
    '/downloads/', 'Downloads',
    '/docs/copyright/', 'Copyright',
    '/docs/faq/', 'FAQ',
    '/docs/install/', 'Install',
    '/docs/manual/', 'Manual',
    '/docs/release/', 'Release',
    '/reset/', 'Reset',
    '/citing/', 'Citing',
    '/example/', 'Example',
    '/(appgt-scan[0-9|-]+)/', 'Results',
    '/(appgt-scan[0-9|-]+)/status/', 'Status',
    '/(appgt-scan[0-9|-]+)/(input|log|error)/', 'JobMessage',
    '/((?:appgt-scan[0-9|-]+)|(?:example))/save/', 'Save',
)
web.config.debug = False
app = web.application(urls, locals())
session = web.session.Session(app, web.session.DiskStore(os.path.join(base_path, 'sessions')), initializer = {'current': ''})
render = web.template.render(os.path.join(base_path, 'templates'), base='layout')

web_base = '/'

#Read the config.ini file to 'config'
config = configparser.ConfigParser()
config.optionxform=str
config.read_file(open(os.path.join(base_path, 'config.ini')))

#Set up some variables for the APIs etc.
genomePath = config.get('important','ref_genome_dir')
webRoot = config.get('important','web_root')
port = config.getint('important','port')
opal_client = model.OpalAdapter()
stylez = {1:['hide','hide','show','hide'],2:['hide','hide','show','hide'],4:['show','show','show','hide'],8:['show','hide','show','show']}

#Sets email settings from config.ini
web.config.smtp_username = config.get('mail','username')
web.config.smtp_password = config.get('mail','password')
web.config.smtp_server = config.get('mail','server')
web.config.smtp_port = int(config.get('mail','port'))
web.config.smtp_starttls = config.get('mail','tls')
emailAddress = config.get('mail','address')
baseUrl = config.get('mail','base_url')

#Parses genome list from config.ini into proper format for the webform
genomes = []
curKey=''
curGroup=['']
for key,name in config.items('ref_genomes'):
    if name == 'group':
        genomes.append((curKey,curGroup))
        curKey = key
        curGroup = []
    else:
        curGroup.append((key,name.split('|')[0]))
genomes.append((curKey,curGroup))

#Requirements for user-specified inputs to meet in web form.
vfaPaste1 = form.regexp(r"^(>.*\r\n)?[actgACTG 0-9\r\n]*$", '<span class=r>Must be a DNA sequence, with or without a FASTA header.</span>')
vfaPaste2 = form.Validator('<span class=r>Input sequence must be between 17 and 4000 characters, inclusive.</span>', lambda x:17<= (len(''.join(re.split("\n|\r\n", x)[1:])) if x[0]==">" else len(''.join(re.split("\n|\r\n", x))))<=4000)




vrule1 = form.regexp(r"^[ATCGatcgXxNnRr]*$", '<span class=r>Rule should only contain the following characters: <span class=positions>AaTtCcGgXxRN</span>.</span>')
vrule2 = form.Validator('<span class=r>Rule should be between 17 and 50 characters.</span>', lambda x: 17<=len(x)<=50)
vrule3 = form.Validator('<span class=r>Rule should contain no more than three Ns.</span>', lambda x: x.lower().count('n')<=3)
vfilter1 = form.regexp(r"^[AaTtCcGgWwSsMmKkRrYyBbDdHhVvNn]*$", '<span class=r>Off-target filter should only contain IUPAC nucleic acid characters.</span>')
vgenome = form.Validator('<span class=r>Make a selection.</span>', lambda x: x!='')
vemail = form.regexp(r"($^)|(.*@.*\..{2,10})", '<span class=r>Leave field blank or enter a valid email address.</span>')

#Creates the input form. Set default values and limitations here.
form1 = form.Form(
    form.Textarea(
        'faPaste', vfaPaste1, vfaPaste2, rows=10, cols=60, description='Enter or upload the <b>candidate genomic region</b>', class_='input_form'),
    form.GroupedDropdown(
        'refGenome', genomes, vgenome, tabindex=1, description='Select the <b>reference genome</b>', class_='input_form', **{'data-placeholder':'Click to see available genomes'}),
    form.Textbox(
        'rule', vrule1, vrule2, vrule3, maxlength=50, description='Enter the <b>target rule</b>', class_='input_form', autocomplete='off'),
    form.Textbox(
        'filter', vfilter1, maxlength=50, description='Enter the <b>off-target filter</b>', class_='input_form', autocomplete='off'),
    form.Dropdown(
        'mismatches', ['0','1','2','3'], description='Select the <b>high-specificity mismatch</b> limit', class_='input_form'),
    form.Textbox(
        'jobName', value='', description='Enter a <b>job description</b>', class_='input_form'),
    form.Textbox(
        'email', vemail, description='Enter your <b>email address</b>', class_='input_form'),
    form.Button(
        'Scan', class_='big nice_button'),
        validators = [
            form.Validator('<span class=r>Off-target filter must be same length as rule.</span>', lambda x: len(x.rule) == len(x.filter))]
)

class EmailThread(threading.Thread):
    def __init__(self, emailAddress, userEmailAddress, subject, content, headers):
        self.subject = subject
        self.content = content
        self.emailAddress = emailAddress
        self.userEmailAddress = userEmailAddress
        self.headers = headers
        threading.Thread.__init__(self)

    def run (self):
        #try:
        web.sendmail(self.emailAddress, self.userEmailAddress, self.subject, self.content, headers = { 'Content-Type':'text/html;charset=utf-8' })
        #except:
        #    print 'Email settings are wrong...\n'
            
            
            
def checkMenu():
    menuCookies = web.cookies(doc_menu='collapsed', recent_menu='collapsed')
    results_children = {'collapsed':['right_arrow',"display:none;"],"expanded":["down_arrow","display:block;"]}
    doc_children = {'collapsed':['right_arrow',"display:none;"],"expanded":["down_arrow","display:block;"]}
    return [results_children[menuCookies.recent_menu],doc_children[menuCookies.doc_menu]]


class index:
    def GET(self):
        return render.index(session.current,checkMenu())
    
class Submit:
    def GET(self):
        f1 = form1()
        menuStatus = checkMenu()
        return render.submit(session.current,f1,checkMenu())

    def POST(self):
        f1 = form1()
        if not f1.validates():
            return render.submit(session.current,f1,checkMenu())
        else:
            #Create FASTA file from input sequence
            faPath = os.path.join(base_path, 'tmp', 'input.fa')
            with open(faPath,'w') as fas:
                fas.write(f1.d.faPaste)

            #Time since epoch
            jobTime = int(time.time()*1000)
            #appends job description to time
            newName = f1.d.jobName.replace('.','&#46;').replace('"','&quot;').replace("'","&#39;").replace(' ','&nbsp;')
            #Specifies arguments for Opal job
            argList = '-g {0} -r {1} -o {2} -m {3} -n "{4}"'.format( f1.d.refGenome, f1.d.rule, f1.d.filter, f1.d.mismatches, newName )
            #Submits job via SOAP to Opal
            try:
                newJob = opal_client.launchJob( argList, [faPath] )
                #newJob = client.launchJobNB( argList, [faPath] )
            except:
                return 'Unexpected error:', sys.exc_info()

            #Attempt to email the user
            if len(f1.d.email) > 0:
                emailSubject = 'GT-Scan notification'
                emailContent = 'Your submission of GT-Scan job <a href="http://{1}{2}/{0}/status/">{0}</a> is succesful!<br> \
                             Click the above link or copy and paste the following URL into your browser to view your job status and results upon completion:<br> \
                             http://{1}{2}/{0}/status/<br> \
                             If you have any questions or comments, please feel free to reply to this email.'.format(newJob.getJobId(), baseUrl, webRoot)
                EmailThread(emailAddress, f1.d.email, emailSubject, emailContent, headers = { 'Content-Type':'text/html;charset=utf-8' }).start()

                
            #Add link to recent jobs, for current session
            #(This would be better as a cookie, so it doesn't reset on browser restart. But anyway..)
            session.current += '<li id={0} class=child><a href="{1}{2}{0}/status/"><span class="time">{3}</span>{4}</a>\n'.format(
                newJob.getJobId(), webRoot, web_base, jobTime, newName )
            #Redirects user to status page
            raise web.seeother('/{0}/status/'.format(newJob.getJobId()))

#Resets recent job list and sends user back to the page that they were originally on.
class Reset:
    def GET(self):
        session.kill()
        raise web.seeother(web.ctx['env']['HTTP_REFERER'])

#Page that shows job status while job is in progress. Automatically redirects user to results if the job is complete.
class Status:
    def GET(self, job_id):
        try:
            status_code = opal_client.getStatusCode(job_id)
            status = model.statii[status_code]
            status_html = '<div class="heading" style="background-color:{0}">{1}</div>'.format(status[1],status[0])
        except:
            return 'Invalid job Id'
        return render.status(session.current, job_id, status_html, stylez[status_code], checkMenu())

class JobMessage:
    def GET(self, job_id, message_type):
        web.header('Content-Type', 'text/plain')
        message_array = {'input': 'input.fa', 'log': 'stdout.txt', 'error': 'stderr.txt'}
        in_file = os.path.join(base_path, 'static', 'results', job_id, message_array[message_type])
        with open(in_file) as f:
            return f.read()

class Install:
    def GET(self):
        return render.install(session.current,checkMenu())

class Manual:
    def GET(self):
        return render.manual(session.current,checkMenu())

class Release:
    def GET(self):
        return render.release(session.current,checkMenu())
    
class FAQ:
    def GET(self):
        return render.faq(session.current,checkMenu())

class Downloads:
    def GET(self):
        return render.downloads(session.current,checkMenu())

class Citing:
    def GET(self):
        return render.citing(session.current,checkMenu())
 
class Copyright:
    def GET(self):
        return render.copyright(session.current,checkMenu())

class Save:
    def GET(self, job_id):
        job_path = os.path.join(base_path, 'static', 'results', job_id)
        zip_file = os.path.join(job_path, 'results.zip') 
        if job_id == 'example':
            return 'Not available for example job.'
        if not os.path.exists(job_path):
            return 'Job results not found. ID may be incorrect.'
        # Returns the file if it already exists (i.e. > 1st download)
        if os.path.exists(zip_file):
            web.header('Content-Type', 'application/zip')
            web.header('Content-Transfer-Encoding', 'base64');
            web.header('Content-Disposition', 'attachment; filename="gt-scan_results.zip"')
            with open(zip_file, 'rb') as zf:
                return zf.read()

        # Create regex rules to scan for .css, .js references and '$:' placeholders 
        cssMatch = re.compile(r"[^\'| |\"]*\.css")
        jsMatch = re.compile(r"[^\'| |\"]*\.js")
        placeholder = re.compile('(\$:)[^\W]*')

        # Database magic
        dbconnection = os.path.join(job_path, 'crispr.db')
        con = db.connect(dbconnection)
        con.text_factory = str
        cur=con.cursor()

        #Gets the target side bar info from the DB
        cur.execute('SELECT * FROM info')
        targetInfo = cur.fetchall()
        
        #New array to store IDs for each row as the following function progresses
        #NOTE: in the template.html file, the tables.js line MUST be before otables.js
        rowIDs = []

        with open(os.path.join(base_path, 'templates', 'template.html'), 'r') as infile, open(os.path.join(job_path, 'downloadable.html'), 'w') as nf:
            # Reads the template.html file and inserts CSS, JS and other info to make one self-contained file.
            for line in infile:
                # If the line is a CSS reference, read that CSS file into the document.
                if cssMatch.search(line):
                    path = cssMatch.search(line).group(0)
                    nf.write('<style>\n')
                    with open(os.path.join(base_path, 'static', 'css', path.split('/')[-1]), 'r') as stylesheet:
                        for i in stylesheet:
                            nf.write(i)
                    nf.write('</style>\n')
                # If the line is a JS reference:
                elif jsMatch.search(line):
                    path = jsMatch.search(line).group(0)
                    nf.write('<script>\n')
                    # This reads JS files into the new HTML file.
                    if 'tables.js' not in path:
                        with open(os.path.join(base_path, 'static', 'js', (path.split('/')[-1])), 'r') as javascript:
                            for i in javascript:
                                nf.write(i)
                    # If the line references tables.js: read the tables from the DB to the HTML file
                    elif path.split('/')[-1] == 'tables.js':
                        nf.write('var candidateTargetData = [\n')
                        cur.execute('SELECT * FROM targets')
                        rows = cur.fetchall()
                        for row in rows:
                            rowIDs.append('{0},{1}'.format(row[0],row[1]))
                            nf.write('[{0},"{1}","{2}",{3},{4},{5},{6}],\n'.format(*row))
                        nf.write(']')

                    elif path.split('/')[-1] == 'otables.js':
                        nf.write('var offTargetData = {\n')
                        for ids in rowIDs:
                            targID = int(ids.split(',')[0])
                            targStrand = ids.split(',')[1]
                            if targStrand == '-':
                                targID = '-{0}'.format(targID)
                            else:
                                addVal = 0
                            cur.execute('SELECT * FROM "{0}"'.format(targID))
                            rows = cur.fetchall()
                            nf.write('"{0}":['.format(targID))
                            for row in rows:
                                nf.write('  ["'+'", "'.join(map(str,row))+'"],\n')
                            nf.write('],')
                        nf.write('}')
                    nf.write('</script>\n')

                elif placeholder.search(line) is not None:
                    if placeholder.search(line).group(0).split(':')[1] == 'jobName':
                        nf.write(line.replace(placeholder.search(line).group(0), targetInfo[0][0]))
                    elif placeholder.search(line).group(0).split(':')[1] == 'ruleLen':
                        nf.write(line.replace(placeholder.search(line).group(0),str(len(targetInfo[0][2])-6)))
                    elif placeholder.search(line).group(0).split(':')[1] == 'rule':
                        nf.write(line.replace(placeholder.search(line).group(0), targetInfo[0][1]))
                    elif placeholder.search(line).group(0).split(':')[1] == 'filter':
                        nf.write(line.replace(placeholder.search(line).group(0), targetInfo[0][2]))
                    elif placeholder.search(line).group(0).split(':')[1] == 'mismatches':
                        nf.write(line.replace(placeholder.search(line).group(0), str(targetInfo[0][3])))
                    elif placeholder.search(line).group(0).split(':')[1] == 'genome':
                        nf.write(line.replace(placeholder.search(line).group(0),str(targetInfo[0][4])))
                    elif placeholder.search(line).group(0).split(':')[1] == 'regionID':
                        nf.write(line.replace(placeholder.search(line).group(0),str(targetInfo[0][5])))
                    elif placeholder.search(line).group(0).split(':')[1] == 'region':
                        nf.write(line.replace(placeholder.search(line).group(0),targetInfo[0][6]))
                    elif placeholder.search(line).group(0).split(':')[1] == 'length':
                        nf.write(line.replace(placeholder.search(line).group(0),targetInfo[0][7]))
                    elif placeholder.search(line).group(0).split(':')[1] == 'time':
                        nf.write(line.replace(placeholder.search(line).group(0),targetInfo[0][8]))
                else:
                    nf.write(line)
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(os.path.join(job_path, 'downloadable.html'), 'results.html')
            os.remove(os.path.join(job_path, 'downloadable.html'))
        with open(zip_file, 'rb') as zf:
            web.header('Content-Type', 'application/zip')
            web.header('Content-Transfer-Encoding', 'base64');
            web.header('Content-Disposition', 'attachment; filename="gt-scan_results.zip"')
            return zf.read()

class Example:
    def GET(self):
        db_path = os.path.join(base_path, 'static', 'downloads', 'example.db')
        row = model.get_summary_raw(db_path)
        return render.results(session.current, checkMenu(), row, 'example')

class Results:
    def GET(self, job_id):
        db_path = os.path.join(base_path, 'static', 'results', job_id, 'crispr.db')
        try:
            row = model.get_summary_raw(db_path)
        except:
            raise web.seeother( 'status/'.format( job_id ) )
        return render.results(session.current, checkMenu(), row, job_id)

if __name__ == '__main__':
    web.httpserver.runsimple(app.wsgifunc(), ('0.0.0.0', port))
#This is when run by Apache
application = app.wsgifunc()
