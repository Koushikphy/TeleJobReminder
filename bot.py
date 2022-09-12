import re
import os
import sys
import json
import telebot
from textwrap import dedent
from flask import Flask, request
from psycopg2 import connect
import pytz





TOKEN = os.getenv("TEL_API")
ADMIN = os.getenv('TEL_ADMIN')
dbURL = os.getenv('DATABASE_URL')
ADMIN_NAME = "Koushik Naskar"
server = Flask(__name__)

bot= telebot.TeleBot(TOKEN, parse_mode='HTML')


def formatDateTime(dTimeUTC):
    # heroku postgres uses UTC datetime format
    utcTimeZone = pytz.timezone('UTC')
    kolkataTimeZone = pytz.timezone('Asia/Kolkata')
    #^ Fixed to India date time zone, will give bad value if accessed outside of India
    dateTimeKZ = utcTimeZone.localize(dTimeUTC).astimezone(kolkataTimeZone)

    return dateTimeKZ.strftime("%e %b %Y, %l:%M %p")

# Database to keep track of all jobs for all users-----

class DataBase:
    def __init__(self):
        self.dbFile = dbURL
        self.con = connect(dbURL)
        with self.con:
            with self.con.cursor() as cur:
                # create database tables and insert admin details
                cur.execute( "CREATE TABLE IF NOT EXISTS JOBINFO("
                "jobID SERIAL PRIMARY KEY,"
                "userId INTEGER NOT NULL,"
                "host TEXT NOT NULL,"
                "status TEXT NOT NULL,"
                "directory TEXT,"
                "added TIMESTAMP default CURRENT_TIMESTAMP,"
                "closed TIMESTAMP,"
                "job TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS USERIDS ("
                " userid INTEGER NOT NULL UNIQUE,"
                " name TEXT NOT NULL,"
                " auth BOOLEAN DEFAULT FALSE);"
                "INSERT into USERIDS (userid,name,auth) values (%s,%s,%s) "
                "ON CONFLICT (userid) DO NOTHING",(ADMIN,ADMIN_NAME,True)
                )


    def listRunningJobs(self, userID):
        with self.con:
            with self.con.cursor() as cur:
                cur.execute("Select host,job from JOBINFO where status='R' and userId=%s",(userID,))
                # ^ only use single quote inside the postgres sql command
                data = cur.fetchall()
                count = len(data)
        txt = "The follwing jobs are running:"+self.formatter(data,['Host','Job']) if count else \
                "No running jobs found"
        return txt,count


    def listAllJobs(self, userID):
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('Select host,status,job from JOBINFO where userId=%s',(userID,))
                data = cur.fetchall()
                count = len(data)
        txt = "List of Jobs:"+self.formatter(data,['Host','S','Job']) if count else\
                "Job List empty"
        return txt,count


    def formatter(self,data,header):
        data = [[f'{l}. {d[0]}',*d[1:]] for l,d in enumerate(data, start=1)]
        data = [[i[:10]+'...' if len(i)>13 else i for i in j ] for j in data]
        lens = [max([len(i)+1 for i in a]) for a in list(zip(*data))]
        txt = [[i.ljust(lens[k]) for k,i in enumerate(j)] for j in data]
        head = '  '.join([ h.center(l) for h,l in zip(header,lens) ])
        return "\n\n <pre>"+head+'\n'+'-'*30+'\n'+'\n'.join(['  '.join(i) for i in txt])+'</pre>'


    def addJob(self, userId, host, job, directory):
        # Adds new job to the database and returns the job ID
        with self.con:
            with self.con.cursor() as cur:
                cur.execute(
                'Insert into JOBINFO (userId, host, status, job, directory) values (%s,%s,%s,%s,%s) RETURNING jobId',
                (userId,host,'R',job, directory)
                )# ^ only work with postgres
                jobID, = cur.fetchone()
                return jobID


    def closeJob(self, jobID, status):
        # set job status as complete or finished
        with self.con:
            with self.con.cursor() as cur:
                cur.execute("SELECT count(*) from JOBINFO where jobID=%s",(jobID,))
                if cur.fetchone()[0]==0: # incoming close job request for a missing job
                    return False
                cur.execute("UPDATE JOBINFO SET status=%s, closed=CURRENT_TIMESTAMP where jobID=%s",(status,jobID))
                return True


    def removeJob(self, userId, index):
        # remove job details from database
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('Select jobID from JOBINFO where userId=%s',(userId,))
                jobIds = cur.fetchall() # check if those jobs are in database
                jobIdsToRemove= [jobIds[i-1] for i in index]
                cur.executemany("Delete from JOBINFO where jobID=%s ",jobIdsToRemove)
                print(f'Job(s) removed for user {userId} jobIDs : {" ".join([str(i) for (i,) in jobIdsToRemove])}')


    def clearJobs(self,userID):
        with self.con:
            with self.con.cursor() as cur:
                cur.execute("Delete from JOBINFO where userId=%s and status in ('C','F') RETURNING *",(userID,))
                deletedRows = cur.fetchall()
                return len(deletedRows)


    def getJobDetail(self,userId, index): #WIP
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('Select jobID from JOBINFO where userId=%s',(userId,))
                thisJob = cur.fetchall()[index-1][0]
                cur.execute("SELECT job,host,directory,status,added,closed from JOBINFO where jobID=%s",(thisJob,))
                info = cur.fetchone()
                # print(info)
                return dedent(f'''
                    Job Details for Job No: {index}
                    ------------------------------------------------
                    <b>Job</b>: {info[0]} 
                    <b>Host</b>: {info[1]}
                    <b>Directory</b>: {info[2]}
                    <b>Status</b>: {info[3]}
                    <b>Added</b>: {formatDateTime(info[4])}
                    <b>Closed</b>: {formatDateTime(info[5]) if info[5] else '---'}
                ''')



    def listOtherJobs(self):
        # admin only service
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('Select name,userid from USERIDS')
                tt = cur.fetchall()

        jobsArr = [f"Jobs for {n}\n"+ self.listAllJobs(u)[0] for n,u in tt]
        return jobsArr



    def listUser(self):
        # list all users, admin only
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('Select name,userid,auth from USERIDS')
                tt = cur.fetchall()
                txt= "\n".join([f'{i}. {n} ({ii}), {a}' for i,(n,ii,a) in enumerate(tt, start=1)])
        return txt


    def checkIfRegisteredID(self, userID):
        # check if registered from the post to server
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('SELECT name from USERIDS where userId=%s and auth',(userID,))
                name = cur.fetchone()
                if name: 
                    return name[0]
                else:
                    bot.send_message(ADMIN, f'Incoming request from unregistered user {userID}')
                    bot.send_message(userID,'You are not authorised to use this option.')




    def checkIfRegisteredUser(self, user, start=False):
        # check if registered from the telegram messages
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('SELECT name from USERIDS where userId=%s and auth',(user.id,))
                name = cur.fetchone()
                if name:
                    return name[0]
                else: # if not registered just note the user, do not authenticate
                    cur.execute('INSERT into USERIDS (name,userid) values (%s,%s) '
                    ' ON CONFLICT (userid) DO NOTHING',(fullName(user,idd=False),user.id))
                    print(f"Incoming request for unregistered user: {fullName(user)}")
                    bot.send_message(ADMIN, f'Incoming request from unregistered user {fullName(user)}')
                    if not start: bot.send_message(user.id,'You are not authorised to use this option.')
                    return False


    def registerUser(self, userID):
        # register a user, ADMIN only function
        userID = int(userID)
        with self.con:
            with self.con.cursor() as cur:
                cur.execute("SELECT name,auth from USERIDS where userId=%s",(userID,))
                #^ this should return a record
                name,auth = cur.fetchone()
                if auth:
                    bot.send_message(ADMIN, f'User ID {name} ({userID}) is already authenticated.')
                    print(f'User ID {name} ({userID}) is already authenticated.')
                else:
                    cur.execute("UPDATE USERIDS SET auth=%s where userid=%s",(True,userID))
                    bot.send_message(ADMIN, f"User {name} ({userID}) is now authenticated.")
                    bot.send_message(userID, 'You are succesfully added to the bot to submit jobs.')
                self.con.commit()


def fullName(user, idd=True):
    # get full name with id from the user object
    firstName = user.first_name
    lastName = user.last_name if user.last_name else ''
    txt = f"{firstName} {lastName}"
    if idd : txt+= f" ({user.id})"
    return txt


db = DataBase()


# Core Telegram bot message handlers-----------------------------------

@bot.message_handler(commands='start')
def send_welcome(message):
    # Send a welcome message and request registration to admin
    user = message.from_user
    # print(message)
    print(f"User start: {fullName(user)}")
    bot.send_message(user.id, f"Hi there <b>{fullName(user,False)}</b>. "
        "Welcome to this automated bot. This bot keeps track of your computer jobs "
        "and sends you notification when your job is finished. "
        f"Your id is <b>{user.id}</b>. Use this when submitting jobs.")
    bot.send_message(user.id,"Download and run the "
        "<a href='https://raw.githubusercontent.com/Koushikphy/TeleJobReminder/master/telebot'>telebot</a> "
        "script to get started.")
    helpMessage(user)
    if not db.checkIfRegisteredUser(user,start=True):
        bot.send_message(user.id,"Note: Currently you are not authorised to submit job with the bot. "
        "Please wait for the admin to accept your request.")


@bot.message_handler(commands='listjobs')
def send_listRunningJobs(message):
    # List Running jobs for the current user
    user = message.from_user
    print(f'List of running jobs requested for {fullName(user)}')
    if db.checkIfRegisteredUser(user):
        jobs,_ = db.listRunningJobs(user.id)
        bot.send_message(user.id,jobs)


@bot.message_handler(commands='listalljobs')
def send_listAllJobs(message):
    # List all jobs for the current user
    user = message.from_user
    print(f'List of all jobs requested for {fullName(user)}')
    if db.checkIfRegisteredUser(user):
        jobs,_= db.listAllJobs(user.id)
        bot.send_message(user.id,jobs)



@bot.message_handler(commands='detail')
def send_detail(message):
    # Remove jobs for the users from database
    user = message.from_user
    print(f'Requested to get job details for {fullName(user)}')
    if db.checkIfRegisteredUser(user):
        txt, count = db.listAllJobs(user.id)
        sent = bot.send_message(user.id, ('Provide serial number of jobs to get details.\n' if count else '')+txt)
        if count : bot.register_next_step_handler(sent, detailwithIDs)


def detailwithIDs(message):
    userId = message.from_user.id
    # try:
    jobId = int(message.text)
    txt = db.getJobDetail(userId, jobId)
    bot.send_message(userId, txt)
    # except:
    # bot.send_message(userId,"Failed to get the job detail.")



@bot.message_handler(commands='remove')
def send_remove(message):
    # Remove jobs for the users from database
    user = message.from_user
    print(f'Requested to remove jobs for {fullName(user)}')
    if db.checkIfRegisteredUser(user):
        txt, count = db.listAllJobs(user.id)
        sent = bot.send_message(user.id, ('Provide serial number of jobs to remove.\n' if count else '')+txt)
        if count : bot.register_next_step_handler(sent, removewithIDs)


def removewithIDs(message):
    # Remove jobs handlers
    toRemoveIds = [int(i) for i in re.split('[, ]+',message.text)]
    db.removeJob(message.from_user.id,toRemoveIds)
    bot.send_message(message.from_user.id, f'These jobs are removed {",".join([str(i) for i in toRemoveIds])}')


@bot.message_handler(commands='clear')
def send_clear(message):
    # Remove jobs for the users from database
    user = message.from_user
    print(f'Requested to clear jobs for {fullName(user)}')
    if db.checkIfRegisteredUser(user):
        count = db.clearJobs(user.id)
        bot.send_message(user.id,f"Number of jobs removed: {count}")





@bot.message_handler(commands='help')
def send_help(message):
    # Send User Id of the user
    user = message.from_user
    print(f'Help request for {fullName(user)}')
    helpMessage(user)


def helpMessage(user):
    bot.send_message(user.id," Contact <a href='https://t.me/Koushikphy'>Koushik Naskar (Admin)</a> or "
        "check out this <a href='https://github.com/Koushikphy/TeleJobReminder'>Github Repo</a> or for further queries.")


@bot.message_handler(commands='myinfo')
def send_userinfo(message):
    # Send User Id of the user
    user = message.from_user
    print(f'Information requested for {fullName(user)}')
    bot.send_message(user.id, f"Hi there {fullName(user,False)}. "
        f"Your id is <b>{user.id}</b>. Use this when submitting jobs")



@bot.message_handler(func=lambda message: message.from_user.id==int(ADMIN))
def adminOnly(message):
    # Only admin allowed functions
    if message.text.lower().startswith('register'):
        newUserID = message.text.split()[1]
        # name,userID = re.findall(r"Register (.*) (\d+)",message.text, re.IGNORECASE)[0]
        print(f'New user registration requested for {newUserID}')
        db.registerUser(newUserID)
    elif message.text.lower().startswith('listuser'):
        bot.send_message(ADMIN,db.listUser())
    
    elif message.text.lower().startswith('listall'):
        for txt in  db.listOtherJobs():
            bot.send_message(ADMIN,txt)

        


@server.route('/api/',methods=["POST"])
def clienReqManager():
    json_string = request.get_data().decode('utf-8')
    data = json.loads(json_string)
    print(json_string)
    userId = int(data.get("id"))
    status = data.get("status")
    job    = data.get("job")
    directory    = data.get("directory")
    host   = data.get("host")
    # job status used: C: Complete; F: Failed; R: Running
    userName = db.checkIfRegisteredID(userId)
    if userName:
        if(status=='S'):  # newly submitted job
            jobID = db.addJob(userId, host, job, directory)
            print(f'New job added for user {userName} ({userId}) at {host} : {job}')
            bot.send_message(userId, f'A new job <b><i>{job}</i></b> is submitted on <b>{host}</b> from directory <i>{directory}</i>.')
            return str(jobID), 200

        elif status in ["C","F"]: # check if already closed
            jobID = data.get("jobID")  # if not starting, request must contain a job ID
            if db.closeJob(jobID, status):  # jobID is primary key so no other info is required
                txt = 'is now complete.' if status=='C' else 'has failed.'
                print(f'Job closed for user {userName} ({userId}) at {host} : {job}, job={job}, jobID={jobID}')
                bot.send_message(userId, f'Your job <i>{job}</i> on <b>{host}</b> {txt}')
            else:
                print(f'Close job requested for a unknown job [{userName}({userId}) at {host} : {job} {jobID}]')
            return str(jobID),200
        else:
            print(f"Warning: Incoming unknows status: {status}. User ID={userId}, Host={host} Job={job}")
    else:
        print(f"Incoming request for unregistered user: {userId}")
    return "!",503


@server.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200



@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://telejobreminder.herokuapp.com/' + TOKEN)
    return '''<div style="text-align: center;">
    <h1>Jobs Reminder</h1>
    <h3>A Telegram bot that notifies you about your computer jobs.</h3>
    <h2>Open <br><a href="https://t.me/JobReminderBot"> https://t.me/JobReminderBot</a> <br> to access the bot.</h2>
    </div>''', 200


if __name__ == "__main__":
    bot.send_message(ADMIN,"Bot Started")
    from waitress import serve
    serve(server, host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))


/home/koushik/H3+/ORTHO_PARA_NEW/j_1_Trial/EKIN_0.1/JTOT_0/VCUT_3/15K

pg_dump --host=ec2-52-201-106-191.compute-1.amazonaws.com --port=5432 --username=jlvrituwqsnjjo --password --dbname=jobinfo > output.sql