from requests import get, post
from json import loads
from flask import Flask, request
from threading import Thread
from base64 import b64decode
from time import sleep, time
import traceback


info = {'log':'','last_check': time()}
all_gh_tokens = all_ci_tokens ={}


def check_gh_run(usr):
    try:
        resp = get(f"https://api.github.com/repos/{usr}/URL-Bot/actions/runs?per_page=1", headers={"Authorization": f"Bearer {all_gh_tokens.get(usr)}"})
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
        resp = get(f"https://circleci.com/api/v2/project/github/{usr}/URL-Bot/pipeline", headers={"Circle-Token":  all_ci_tokens.get(usr)})
        last_no = resp.json()['items'][0]['number']
        for diff in range(0,16):
            try:
                resp = get(f"https://circleci.com/api/v2/project/github/{usr}/URL-Bot/job/{last_no - diff}", headers={"Circle-Token": all_ci_tokens.get(usr)})
                wr = resp.json()['status']
                return wr != 'failed'
            except KeyError:
                continue
    except:
        info['log']+=traceback.format_exc() + '\n\n\n'
        return None

def run_gh(usr):
    try:
        resp = post(
            f"https://api.github.com/repos/{usr}/URL-Bot/actions/workflows/Job.yml/dispatches",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization":  f"Bearer {all_gh_tokens.get(usr)}",
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
            f"https://circleci.com/api/v2/project/github/{usr}/URL-Bot/pipeline",
            headers={
                "Circle-Token": all_ci_tokens.get(usr),
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
    global all_ci_tokens
    global all_gh_tokens
    old_raw = ''
    while True:
        try:
            raw = get('https://pastebin.com/raw/jHWc7wVF').text
            if old_raw != raw:
                old_raw = raw
                info['log']=''
                for key, value in list(info.items()):
                    if 'l' not in key:
                        if 'c' in key or 'g' in key:
                            del info[key]
                            
            json_raw = loads(raw)
            all_ci_tokens = json_raw['CI']
            all_gh_tokens = json_raw['GH']
            i=1
            for usr in list(all_ci_tokens):
                info[f'c{i}'] = check_circle_run(usr)
                i+=1
            i=1
            for usr in list(all_gh_tokens):
                info[f'g{i}'] = check_gh_run(usr)
                i+=1
                
            sleep(10)
            
            i=1
            for usr in list(all_ci_tokens):
                if not info[f'c{i}']:
                    if not check_circle_run(usr):
                        info[f'c{i}']=run_circle(usr)
                i+=1
            i=1
            for usr in list(all_gh_tokens):
                if not info[f'g{i}']:
                    if not check_gh_run(usr):
                        info[f'g{i}']=run_gh(usr)
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
    content=''
    for key, value in info.items():
        if 'l' not in key:
            if 'c' in key:
                content+=f'<h3>Circle CI Bot {key.replace("c","")} Running: {value}</h3>'
            if 'g' in key:
                content+=f'<h3>Github Bot {key.replace("g","")} Running: {value}</h3>'
    return f"""{tag_meta}
        {content}
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
