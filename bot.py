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
        return txt,

    def formatter(self,data,header):
        data = [[f'{l}. {d[0]}',*d[1:]] for l,d in enumerate(data, start=1)]
        data = [[i[:10]+'...' if len(i)>13 else i for i in j ] for j in data]
        lens = [max([len(i)+1 for i in a]) for a in list(zip(*data))]
        txt = [[i.ljust(lens[k]) for k,i in enumerate(j)] for j in data]
        head = '  '.join([ h.center(l) for h,l in zip(header,lens) ])
        return "\n\n <pre>"+head+'\n'+'-'*30+'\n'+'\n'.join(['  '.join(i) for i in txt])+'</pre>'


    def listDetailedJobs(self, userID):
        # will run the same function both for detail and removing
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('Select jobID,host,status,job from JOBINFO where userId=%s ORDER by jobID',(userID,))
                data = cur.fetchall()
                count = len(data)
        if count ==0:
            txt = "No jobs found"
        else:
            txt = "List of Jobs:\n"+"-"*50+'\n\n'+"\n\n".join(
                f"{i}. <b>{job}</b> (<i>{host}</i>) [<b>{status}</b>] \n    /d_{jobID}        /r_{jobID}" 
            for i,(jobID,host,status,job) in enumerate(data,start=1))
            txt += "\n\n <i>* Use the <b>'d_*'</b> link to get details of a job and the <b>'r_*'</b> to remove the job.</i>" 
        return txt



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


    def removeJob(self, userId, jobID):
        # remove job details from database

        with self.con:
            with self.con.cursor() as cur:

                cur.execute("Delete from JOBINFO where jobID=%s and userID=%s RETURNING job",(jobID, userId))

                jobName = cur.fetchone()[0]
                return f"Job <b>{jobName}</b> removed from list."



    def getJobDetail(self,userId, jobID): #WIP
        with self.con:
            with self.con.cursor() as cur:
                # although we can get all the info from just the jobid, but also include the userid
                cur.execute("SELECT job,host,directory,status,added,closed "
                    "from JOBINFO where jobID=%s and userID=%s",(jobID,userId))
                info = cur.fetchone()
                # print(info)
                return dedent(f'''
                    Job Details:
                    ------------------------------------------------
                    <b>Job</b>: {info[0]} 
                    <b>Host</b>: {info[1]}
                    <b>Directory</b>: {info[2]}
                    <b>Status</b>: {info[3]}
                    <b>Added</b>: {formatDateTime(info[4])}
                    <b>Closed</b>: {formatDateTime(info[5]) if info[5] else '---'}
                ''')


    def status(self):
        # list all users, admin only
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('Select name,userid,auth from USERIDS')
                tt = cur.fetchall()
                txt= "\n".join([f'{i}. {n} ({ii}), {a}' for i,(n,ii,a) in enumerate(tt, start=1)])
                cur.execute("Select userId, count(*) from JOBINFO group by userId")
                tt = cur.fetchall()
                txt += "\n\n"
                txt += "\n".join(f"{i}. {u} - {n}" for i,(u,n) in enumerate(tt,start=1))
        return txt



    def checkIfRegistered(self, userID, name=None):
        # check if registered from the post to server
        with self.con:
            with self.con.cursor() as cur:
                cur.execute('SELECT name from USERIDS where userId=%s and auth',(userID,))
                name = cur.fetchone()
                if name: 
                    return name[0]
                else:
                    cur.execute('INSERT into USERIDS (name,userid) values (%s,%s) '
                    ' ON CONFLICT (userid) DO NOTHING',(name,userID))
                    print(f"Incoming request for unregistered user: {name}({userID})")
                    bot.send_message(ADMIN, f'Incoming request from unregistered user {userID}({userID})')
                    bot.send_message(userID,'You are not authorised to use this option.')



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



db = DataBase()


# Core Telegram bot message handlers-----------------------------------

def send_welcome(userID,name):

    bot.send_message(userID, f"Hi there <b>{name}</b>. "
        "Welcome to this automated bot. This bot keeps track of your computer jobs "
        "and sends you notification when your job is finished. "
        f"Your id is <b>{userID}</b>. Use this when submitting jobs.")
    bot.send_message(userID,"Download and run the "
        "<a href='https://raw.githubusercontent.com/Koushikphy/TeleJobReminder/master/telebot'>telebot</a> "
        "script to get started.")
    bot.send_message(userID," Contact <a href='https://t.me/Koushikphy'>Koushik Naskar (Admin)</a> or "
        "check out this <a href='https://github.com/Koushikphy/TeleJobReminder'>Github Repo</a> or for further queries.")



@bot.message_handler(func=lambda x: True)
def allCommnad(message):
    user :int = message.from_user.id
    text :str = message.text.lower()
    name :str= f"{user.first_name} {user.last_name if user.last_name else ''}"


    if text=='/start' or text=='/help':
        send_welcome(user,name)

    if not db.checkIfRegistered(user,name):
        bot.send_message(user,'You are not authorised to use this bot. Please wait for the admin to authenticate you.')
        return
    

    elif text=="/list":
        bot.send_message(user,db.listRunningJobs(user))

    elif text=="/list_detail":
        bot.send_message(user,db.listDetailedJobs(user))


    elif text.startswith('/d'):
        jobID = text.strip('/d_')
        bot.reply_to(message, db.getJobDetail(user, jobID))

    elif text.startswith('/r_'):
        jobID = text.strip('/r_')
        bot.reply_to(message,db.removeJob(user,jobID))
    

    elif text=="/status" and user ==int(ADMIN):
        bot.send_message(user,db.status())
        
    elif text.startswith("register") and user ==int(ADMIN):
        newUser = int(text.strip("register"))
        db.registerUser(newUser)
        

    else:
        print("Unknown command")





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
    userName = db.checkIfRegistered(userId)
    if userName:
        if(status=='S'):  # newly submitted job
            jobID = db.addJob(userId, host, job, directory)
            print(f'New job added for user {userName} ({userId}) at {host} : {job}')
            bot.send_message(userId, f'A new job <b><i>{job}</i></b> '
                'is submitted on <b>{host}</b> from directory <i>{directory}</i>.')
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