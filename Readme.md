<p align="center">
  <h2 align="center">Job Reminder Bot</h2>
  <h3 align="center">A Telegram bot that keeps track of your computer jobs.</h3>
</p>

<p align="center">
  <a href="https://t.me/JobReminderBot" alt="Version"><img src="https://img.shields.io/badge/Telegram-JobReminderBot-blue.svg?style=flat&logo=telegram" /></a>  <a href="https://t.me/Koushikphy" alt="Version"><img src="https://img.shields.io/badge/Telegram-Koushik_Naskar-blue.svg?style=flat&logo=telegram" /></a>  <a href="https://telejobreminder.herokuapp.com/" alt="Version"><img src="https://img.shields.io/badge/Heroku-Deployed-brightgreen.svg?style=flat&logo=heroku" /></a>  
</p>

---


Telegram bots are an extermely useful way to send automated notification/message directly to phone. Its completely free, easy to set up and you can send any kind of messagages including document, pictures, videos etc. as long as its connected to the internet. Here, I have made a bot to keep track of my long running computer jobs, so that it can send me notification when the job finishes/fails.


### Getting Started:
1. Open the Telegram bot at https://t.me/JobReminderBot and press `start` to get started. Wait for the admin to authorise you.
2. Download the `telebot` script (only written for bash), make it executable and keep it in your `PATH`.
3. Submit your job with the shell script as
    ```
    telebot -u USER_ID -n JOB_Name -j JOB_Command
    ```


### Setting middlehost:
If you are working in an isolated shell that can not communicate with the bot server (i.e. internet) you can run the `middlehost.py` to set as middle worker between the client and bot server communication. In that case, chage the bot server address in the `telebot` script with the middle host server details.

### Useful Links:
[Telegram Bots: An introduction for developers.](https://core.telegram.org/bots)