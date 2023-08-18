from requests import get, post
from flask import Flask, request
from threading import Thread
from base64 import b64decode
from time import sleep, time
import traceback


all_tokens = {
    'dev-zarir' : 'CCIPAT_166iZ4GwAPFg1h5VqhDrwA_1b03b68d725c3fde91c5ae797f5f91ff3bafc724',
    'makhatun204' : 'CCIPAT_CDqH8Y8sCHan79JyX2Htsn_8cdb7ae29215ed1b98a8d68b99b0fad941db21bd',
    'szharir0' : 'CCIPAT_9yW7eCqKY2kJ6voJ1481PT_43b8e501e3237f32aade959507b6e67069bee241'
}

info = {'log':'','last_check': time(),'c1':False,'c2':False,'c3':False}


def check_gh_run(no:int = 1):
    try:
        resp = get(f"https://api.github.com/repos/{G_USER}/Link-{no}/actions/runs?per_page=1", headers={"Authorization": f"Bearer {G_TOKEN}"})
        try:
            wr = resp.json()['workflow_runs'][0]
        except:
            raise Exception('Error at check_gh_run - wr:\n'+resp.text)
        if wr['status'] != 'completed':
            return True
        else:
            if wr['conclusion'] == 'cancelled':
                return True
            return False
    except:
        info['log']+=traceback.format_exc() + '\n\n\n'
        return None

def check_circle_run(usr):
    try:
        resp = get(f"https://circleci.com/api/v2/project/github/{usr}/Links-Bot/pipeline", headers={"Circle-Token":  all_tokens.get(usr)})
        last_no = resp.json()['items'][0]['number']
        for diff in range(0,16):
            try:
                resp = get(f"https://circleci.com/api/v2/project/github/{usr}/Links-Bot/job/{last_no - diff}", headers={"Circle-Token": all_tokens.get(usr)})
                wr = resp.json()['status']
                return wr != 'failed'
            except KeyError:
                continue
    except:
        info['log']+=traceback.format_exc() + '\n\n\n'
        return None

def run_gh(no:int = 1):
    try:
        owner_and_repo = f"{G_USER}/Link-{no}"
        resp = post(
            f"https://api.github.com/repos/{owner_and_repo}/actions/workflows/Job.yml/dispatches",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization":  f"Bearer {G_TOKEN}",
                "Content-Type": "application/json"
            },
            data='{"ref":"main","inputs":{"count":"0"}}'
        )
        if resp.status_code != 204:
            info['log'] += 'Error at run_gh status_code:\n' + resp.text + "\n\n\n"
            return False
        return True
    except:
        info['log']+=traceback.format_exc() + '\n\n\n'
        return None

def run_circle(usr):
    try:
        resp = post(
            f"https://circleci.com/api/v2/project/github/{usr}/Links-Bot/pipeline",
            headers={
                "Circle-Token": all_tokens.get(usr),
                "Content-Type": "application/json"
            },
            data='{"branch":"main","parameters":{"count":"0"}}'
        )
        if resp.status_code != 201:
            info['log'] += resp.text + "\n\n\n"
            return False
        return True
    except:
        info['log']+=traceback.format_exc() + '\n\n\n'
        return None
    

def seconds_to_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining_seconds = int(seconds % 60)

    if hours == 0:
        return f"{minutes}m {remaining_seconds}s"
    else:
        return f"{hours}h {minutes}m {remaining_seconds}s"


def thread_func():
    while True:
        try:
            i=1
            for usr in list(all_tokens):
                info[f'c{i}'] = check_circle_run(usr)
                i+=1
            sleep(10)
            i=1
            for usr in list(all_tokens):
                if not info[f'c{i}']:
                    if not check_circle_run(usr):
                        info[f'c{i}']=run_circle(usr)
                i+=1
            info['last_check']=time()
        except:
            info['log']+=traceback.format_exc() + '\n\n\n'
        sleep(110)


t=Thread(target=thread_func)
t.daemon = True
t.start()


app = Flask(__name__)
app.config['SECRET_KEY'] = 'thisIsMySecretKeyOK'
tag_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'

@app.route('/', methods=['GET', 'POST'])
def home():
    return f"""{tag_meta}
        <h3>Circle CI Bot 1 Running: {info['c1']}</h3>
        <h3>Circle CI Bot 2 Running: {info['c2']}</h3>
        <h3>Circle CI Bot 3 Running: {info['c3']}</h3>
        <p><span style="color:red;">Note:</span> If the CI Bot is manually cancelled/stopped, then it will be count as running. Only failed CI/Bot will set as running = False.</p>
        <br>
        <h3>Last Checked: {seconds_to_time(time() - info['last_check'])} ago</h3>
        <br>
        <a href="/log">View Log</a>
        <br>
    """

@app.route('/log')
def log_view():
    if info['log'] == '':
        return tag_meta + '<h3>Log is Empty</h3>'
    return tag_meta + info['log'].replace('\n', '<br>')


if __name__ == '__main__':
    app.run('0.0.0.0', 80, True)
