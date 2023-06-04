import logging
import time
from mytools.common.log import Handlers
from threading import Thread

from solution import ChatGPT, Poe
from flask import Flask, render_template, request

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    handlers=[Handlers().colored_stream()],
)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("selenium").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Use Google account for poe chatbot and openai account for chatgpt chatbot
EMAIL = 'youremail@gmail.com'
PASSWORD = 'your password'
VISIBILITY = False
CHATBOT = 'poe'     # or openai


def select_bot():
    if CHATBOT == 'openai':
        return ChatGPT(EMAIL, PASSWORD, headless=not VISIBILITY)
    elif CHATBOT == 'poe':
        return Poe(EMAIL, PASSWORD, headless=not VISIBILITY)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/openai', methods=['GET', 'POST'])
def chatgpt_resolver():
    prompt = request.json['prompt']
    logger.info(f"Prompt send: {prompt}")

    answer = bot.interact(prompt)
    logger.info(f"Response: {answer}")

    return answer


@app.route('/poe', methods=['GET', 'POST'])
def poe_resolver():
    prompt, engine = request.json['prompt'], request.json.get('engine')
    logger.info(f"Prompt send: {prompt}")

    answer = bot.interact(prompt, engine=engine if engine is not None else 'sage')
    logger.info(f"Response: {answer}")

    return answer


def _destroyer(seconds):
    global bot
    bot.quit()
    logger.info(f"Driver destroyed for {seconds} seconds")
    time.sleep(seconds)
    bot = select_bot()


@app.route('/destroy', methods=['GET', 'POST'])
def destroyer():
    seconds = int(request.args.get('time', default=0))
    if seconds == 0:
        return "Time param must be greater than 0"
    Thread(target=_destroyer, args=(seconds, )).start()
    return 'Success re-initialized the driver'


if __name__ == '__main__':
    import waitress

    bot = select_bot()

    waitress.serve(app, listen='0.0.0.0:5005', threads=1)
