from requests import get, post
from flask import Flask, request
from threading import Thread
from base64 import b64decode
from time import sleep, time
import traceback


C_TOKEN = "CCIPAT_166iZ4GwAPFg1h5VqhDrwA_1b03b68d725c3fde91c5ae797f5f91ff3bafc724"
G_TOKEN_B64 = b'Z2hwX1loZ2J1RlBlYnhtc3ZsckV6WkdPWWFRTmNWbDNDVzNBbThsVQ=='
G_TOKEN = b64decode(G_TOKEN_B64).decode()
info = {'log':'','last_check': time(),'c1':False,'g1':False,'g2':False}


def check_gh_run(no:int = 1):
    resp = get(f"https://api.github.com/repos/msh1997-rahino/Link-{no}/actions/runs?per_page=1", headers={"Authorization": f"Bearer {G_TOKEN}"})
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

def check_circle_run():
    resp = get(f"https://circleci.com/api/v2/project/github/dev-zarir/V2Links-Bot/pipeline", headers={"Circle-Token":  C_TOKEN})
    last_no = resp.json()['items'][0]['number']
    diff = 4
    resp = get(f"https://circleci.com/api/v2/project/github/dev-zarir/V2Links-Bot/job/{last_no - diff}", headers={"Circle-Token":  C_TOKEN})
    wr = resp.json()['status']
    return wr != 'failed'

def run_gh(no:int = 1):
    owner_and_repo = f"msh1997-rahino/Link-{no}"
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

def run_circle():
    owner_and_repo = "github/dev-zarir/V2Links-Bot"
    resp = post(
        f"https://circleci.com/api/v2/project/{owner_and_repo}/pipeline",
        headers={
            "Circle-Token": C_TOKEN,
            "Content-Type": "application/json"
        },
        data='{"branch":"main","parameters":{"count":"0"}}'
    )
    if resp.status_code != 201:
        info['log'] += resp.text + "\n\n\n"
        return False
    return True
    

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
            if not check_circle_run(): run_circle()
            if not check_gh_run(1): run_gh(1)
            if not check_gh_run(2): run_gh(2)
            sleep(10)
            info['c1']=check_circle_run()
            info['g1']=check_gh_run(1)
            info['g2']=check_gh_run(2)
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
        <h3>Circle CI Bot Running: {info['c1']}</h3>
        <h3>Github Bot 1 Running: {info['g1']}</h3>
        <h3>Github Bot 2 Running: {info['g2']}</h3>
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

