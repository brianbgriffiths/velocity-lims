import os, json
from settings import settings
import psycopg
from psycopg import sql
from psycopg.rows import dict_row 
from psycopg.pq import Escaping

dbname = 'pylims'
dbuser = 'dbroot'
dbpass = 'pylims2023'
dbhost = '127.0.0.1'
dbport = '5432'

def term():
    colored_text=f"[\033[38;5;32mp\033[38;5;220my\033[38;5;32ml\033[38;5;220mi\033[38;5;32mm\033[38;5;220ms\033[0m]"
    return f'{colored_text}'


class user:
    def __init__(self, username, user_id):
        self.username = username
        self.user_id = user_id
        self.logged_in = False

    def login(self):
        #declared in login module
        pass
        
def build_module_dict():
    main_directory = settings.BASE_DIR / 'modules'
    directory_dict = {}
    # print('trawling',main_directory)
    for root, dirs, files in os.walk(main_directory):
        for folder in dirs:
            folder_path = os.path.join(root, folder)
            manifest_path = os.path.join(folder_path, 'manifest.json')
            
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as manifest_file:
                    subdirectory = os.path.relpath(root, main_directory)
                    if subdirectory not in directory_dict:
                        directory_dict[subdirectory] = {}
                    try:
                        manifest_data = json.load(manifest_file)
                        directory_dict[subdirectory][folder] = manifest_data
                    except json.JSONDecodeError as e:
                        print(f"{term()} \033[38;5;196mError loading JSON\033[0m from \033[38;5;202m{manifest_path}\033[0m: {e}")
                        directory_dict[subdirectory][folder]={'type':'error'}
    return json.dumps(directory_dict)
def get_setup_options():
    file_path = settings.BASE_DIR / 'json/module_setup.json'
    with open(file_path, 'r') as json_file:
        datadict = json.load(json_file)
    return json.dumps(datadict)

def loggedin(request):
    if request.session==None:
        return False
    if not 'userid' in request.session:
        return False
    if not request.session['userid']>0:
        return False
    
    return True
def authmatch(loggedin,auth):
    if auth=='loggedout' and loggedin==True:
        return False
    if auth=='loggedin' and loggedin==False:
        return False
    return True

def adminauthmatch(user_permissions,permissions_accepted):
    if len(user_permissions)==0:
        return False
    print(term(),info('accepted permissions'),permissions_accepted)
    print(term(),info('user permissions'),user_permissions)
    if user_permissions=={}:
        return False
    if permissions_accepted==[]:
        print(warning('there seems to be missing permissions for this admin file'))
        return False
    for accept in permissions_accepted:
        if accept in user_permissions:
            print(term(),info('user has permission'),accept)
            return True
    print(term(),error('did not find sufficient permissions'))

def loaduser_admin(userid):
    conn = psycopg.connect(dbname=dbname, user=dbuser, password=dbpass, host=dbhost, port=dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    admin={}
    query = sql.SQL("""
        SELECT admin.permission, user_admin.value
        FROM user_admin
        JOIN admin ON admin.aid = user_admin.permission
        WHERE user_admin.USER = {}
    """).format(sql.Literal(userid))
    
    cursor.execute(query)
    result = cursor.fetchall()
    for permission in result:
        admin[permission['permission']]=permission['value'] 
    return admin

def error(msg):
    return f"\033[38;5;196m{msg}\033[0m"

def info(msg):
    return f"\033[38;5;40m{msg}\033[0m"

def warning(msg):
    return f"\033[38;5;220m{msg}\033[0m"

def build_module_links(request):
    # print('BUILDING MODULE LINKS')
    modules = json.loads(build_module_dict())
    file_path = settings.BASE_DIR / 'json/module_setup.json'
    links=[]
    if 'admin' in request.session:
        if 'modules_setup' in request.session['admin']:
            newlink=['setup','Setup','../../setup']
            links.append(newlink)
    with open(file_path, 'r') as json_file:
        setup = json.load(json_file)
    for m in setup['setup']:
        if setup['setup'][m]=='disabled':
            continue
        # print(m)
        # print(modules[m])
        # print(modules[m][setup['setup'][m]])
        if modules[m][setup['setup'][m]]['type']=='error':
            print(term(),f'Not building {m} links for {setup["setup"][m]} due to error')
            continue
        for template in modules[m][setup['setup'][m]]['templates']:
            print(term(),'template',template)
            
            link=modules[m][setup['setup'][m]]['templates'][template]
            print(term(),'link',link)
            match=authmatch(loggedin(request),link['authentication'])
            print('display=',link['display_link'],'match=',match)
            if link['display_link']==True and match==True:
                print('attaching link')
                if template==modules[m][setup['setup'][m]]['default_template']:
                    newlink=[m,link['name'],'']
                else:
                    newlink=[m,link['name'],template.split('.')[0]]
                links.append(newlink)
    
    print(links)
    return links        
