<p align="center">
  <h2 align="center">Job Reminder Bot</h2>
  <h3 align="center">A Telegram bot that keeps track of your computer jobs.</h3>
</p>

<p align="center">
  <a href="https://t.me/JobReminderBot" alt="Version"><img src="https://img.shields.io/badge/Telegram-JobReminderBot-blue.svg?style=flat&logo=telegram" /></a>  <a href="https://t.me/Koushikphy" alt="Version"><img src="https://img.shields.io/badge/Telegram-Koushik_Naskar-blue.svg?style=flat&logo=telegram" /></a>  
</p>




https://user-images.githubusercontent.com/43264301/202856466-bc857542-e334-4ea2-910e-a1a8d62a0656.mp4



---


Telegram bots are an extremely handy tool to send automated notifications/messages directly to the phone. It's completely free, easy to set up, and you can send any kind of message, including documents, pictures, videos etc. Here, I have made a bot to keep track of my long-running computer jobs so that it can send me a notification when the job finishes/fails.


### 🚀 Getting Started:
- Open the Telegram bot at https://t.me/JobReminderBot and press `start` to get started. Wait for the admin to authorize you.
- Download the [telebot](https://github.com/Koushikphy/TeleJobReminder/blob/main/telebot) script (only written for bash atm), make it executable and keep it in your `PATH`.
- Submit your job with the shell script as
    ```
    telebot -u USER_ID -n JOB_Name -j JOB_Command
    ```


### ⚒ Setting Optional Middlehost:
If you are working in an isolated shell that can not communicate with the bot server (i.e., internet) directly, you can run the [middlehost.py](https://github.com/Koushikphy/TeleJobReminder/blob/main/middlehost.py). It creates an HTTP route that transfers the network communications to and from the client-side to the bot server running on the cloud. In that case, you need to change the bot server address in the [telebot](https://github.com/Koushikphy/TeleJobReminder/blob/main/telebot) script with the middle host server details.

### 👍Useful Links:
- [Telegram Bots: An introduction for developers.](https://core.telegram.org/bots)
- [Getting Started with Heroku.](https://devcenter.heroku.com/)
