import pylims
import psycopg
from psycopg.rows import dict_row
import json


class Sample:
    def __init__(self, script, **sample):
        # put all these initial values so they don't trigger the changed data
        super().__setattr__('changed_data', {})
        super().__setattr__('name', sample['name'])
        super().__setattr__('id', sample['id'])
        super().__setattr__('steps', sample['steps'])
        super().__setattr__('script', script)
        super().__setattr__('routes', Routes(self.script))
        # data = {}
        # for d in script.derivative_data_config:
        #     print(d,script.derivative_data_config[d])
        print(self.steps)
    
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if hasattr(self, 'changed_data'): 
            self.changed_data[name] = value

    def route_to(self, destination):
        print('Routing to ',destination)
        assay = 'current'
        step = 0
        if destination=='next_step':
            step_index = self.steps.index(self.script.step_config['step_type'])
            step = self.steps[step_index+1]
        elif destination=='repeat_step':
            step = -3
        self.changed_data['routing']=json.dumps([{'assay':assay, 'step':step}])
    

def ensure_last_line(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)  # Run the main logic
        self._always_run_last()  # Run the last line logic
        print('running last line')
        return result
    return wrapper

class VelocityList(list):
    def __init__(self, script, listtype):
        super().__init__()
        self.type = listtype
        self.config = script.derivative_data_config
        self.conn = script.conn
        self.cursor = script.cursor
        self.updates = script.updates
        self.run_status = 2
    
    def commit(self):
        print('commit',self.type)
        update_data=[]
        for list_item in self:
            if list_item.changed_data:
                for changed_item in list_item.changed_data:
                    print(list_item.id, self.config[changed_item]['ddcid'], list_item.changed_data[changed_item])
                    update_data.append([list_item.id,self.config[changed_item]['ddcid'], list_item.changed_data[changed_item]])

        self.cursor.executemany("""
            INSERT INTO velocity.derivative_data (derivative, data_config, value)
            VALUES (%s, %s, %s)
            ON CONFLICT (derivative, data_config)
            DO UPDATE SET value = EXCLUDED.value
            """, update_data)
        self.updates['outputs']=update_data
        self.conn.commit()
    
class Route:
    def __init__(self, script):
        pass

class Routes:
    def __init__(self, script):
        self.script = script
        pass

    def add(self):
        print('adding a route')

class Step:
    def __init__(self, script):
        self.conn = script.conn
        self.script = script
        self.cursor = self.script.cursor
        self.config = self.script.step_config
        self.id = self.script.step_config['stepid']

    def clear_routes(self):
        self.cursor.execute("UPDATE velocity.step_io sio SET routing='[]' WHERE sio.step=%s",(self.id,))
        self.conn.commit()
        
        


class VelocityScript:
    def __init__(self, **config):
        print('Initializing Velocity Custom Script')

        self.return_message = "Script has finished running."
        self.updates={}
        self.run_status = 2

        self.conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
        self.cursor = self.conn.cursor()

        self.cursor.execute("""SELECT vs.*, vps.*, vsc.*, vp.*, vpc.* FROM velocity.steps vs JOIN velocity.page_config vpc ON vpc.pcid = vs.on_page JOIN velocity.protocol_steps vps ON vps.sid=vs.step_type JOIN velocity.step_config vsc ON vsc.scid=vps.step_type JOIN velocity.protocols vp ON vp.pid=vps.protocol WHERE vs.stepid=%s;""",(config['step'],))
        self.step_config=self.cursor.fetchone()
        self.step = Step(self)

        self.cursor.execute("SELECT * FROM velocity.derivative_data_config;")
        temp_rows = self.cursor.fetchall()
        self.derivative_data_config = {row['key']: row for row in temp_rows}

        self.cursor.execute("SELECT sio.*, vwf.workflow_steps as output_steps, vdi.did as input_id, vdi.container as inputcontainer, vdo.did as output_id, vdo.container as outputcontainer, vdo.placement_string as output_well, vs.* FROM velocity.step_io sio JOIN velocity.derivatives vdi ON vdi.did=sio.input_derivative JOIN velocity.derivatives vdo ON vdo.did=sio.output_derivative JOIN velocity.samples vs ON vs.smid=vdi.sample JOIN velocity.workflows vwf ON vwf.wfid=vdo.derivative_wf WHERE sio.step=%s",(self.step.id,))
        self.io = self.cursor.fetchall()

        self.cursor.execute('SELECT scid, step_name FROM velocity.step_config')
        temp_step_names = self.cursor.fetchall()
        self.step_names={}
        for tsd in temp_step_names:
            self.step_names[tsd['scid']]=tsd['step_name']

        self.cursor.execute('SELECT assayid, assay_name FROM velocity.assay')
        temp_assay_names = self.cursor.fetchall()
        self.assay_names={}
        for tan in temp_assay_names:
            self.assay_names[tan['assayid']]=tan['assay_name']

        self.outputs=VelocityList(self, 'derivatives')
        for sample in self.io:
            self.outputs.append(Sample(self, id=sample['output_id'], name=sample['sample_name'], steps=sample['output_steps']))

    def __del__(self):
        self.cursor.close()
        self.conn.close()

    def complete(self):
        print('run status',self.run_status)
        print('return message',self.return_message)
        print('updates',self.updates)
        return(self.run_status, self.return_message, self.updates)
        
        
        