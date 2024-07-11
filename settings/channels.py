from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
import psycopg
from psycopg import sql
from psycopg.rows import dict_row 
from psycopg.pq import Escaping
import pylims

def save_step(id,col,value):
    print(pylims.term(),f'Updating Step',id,col,value)
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute(
        sql.SQL("UPDATE automation_step SET {} = %s WHERE asid = %s").format(sql.Identifier(col)),
        [value, id]
    )
    conn.commit()
    cursor.close()
    conn.close()

def save_workflow(id,col,value):
    print(pylims.term(),f'Updating Workflow',id,col,value)
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    if col == "steps" and value<0: #this is remove step from workflow
        print(pylims.term(),f'removing step',value)
        cursor.execute("SELECT steps FROM automation_workflow WHERE wfid = %s",(id,))
        result = cursor.fetchone()
        steps = json.loads(result['steps'])

    cursor.execute(
        sql.SQL("UPDATE automation_workflow SET {} = %s WHERE wfid = %s").format(sql.Identifier(col)),
        [value, id]
    )
    conn.commit()
    cursor.close()
    conn.close()

class automation_configure(AsyncWebsocketConsumer):
    async def connect(self):
        # Check if the user is authenticated

        await self.accept()
        

        # Add the WebSocket connection to a channel group
        await self.channel_layer.group_add(
            "automation",  # Replace "channel_name" with the desired channel name
            self.channel_name,
        )

    async def disconnect(self, close_code):
        # Remove the WebSocket connection from the channel group
        await self.channel_layer.group_discard(
            "automation",  # Replace "channel_name" with the desired channel name
            self.channel_name,
        )

    async def receive(self, text_data):
        # Broadcast the received message to all listeners on the channel
        current_session_data = await sync_to_async ( self.scope["session"].load) ()
        print('CURRENT SESSION DATA',current_session_data)
        json_data = json.loads(text_data)
        print('json data',json_data)
        json_data['message']['data']['op_id'] = current_session_data['userid']
        sd = json_data['message']['data']

        if json_data['message']['type'] == 'save_step_type' or json_data['message']['type'] == 'save_step':
            save_step(sd['id'],sd['key'],sd['value'])
        elif json_data['message']['type'] == 'save_workflow_type' or json_data['message']['type'] == 'save_workflow':
            save_workflow(sd['id'],sd['key'],sd['value'])
        elif json_data['message']['type'] == 'add_step_to_workflow':
            print(pylims.term(),f'Add Step {sd["step"]} to Workflow {sd["wf"]}')
            conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
            cursor = conn.cursor()

            cursor.execute("SELECT steps FROM automation_workflow WHERE wfid = %s;",(sd["wf"],))
            result = cursor.fetchone()
            if result['steps']==None:
                result['steps']='[]'
            steps = json.loads(result['steps'])
            steps.append(sd["step"])
            step_save = json.dumps(steps)
            cursor.execute("UPDATE automation_workflow SET steps = %s WHERE wfid = %s;",(step_save, sd["wf"]))
            
            cursor.execute("SELECT workflows FROM automation_step WHERE asid = %s;",(sd["step"],))
            result = cursor.fetchone()
            if result['workflows']==None:
                result['workflows']='[]'
            workflows = json.loads(result['workflows'])
            workflows.append(sd["wf"])
            workflow_save = json.dumps(workflows)
            cursor.execute("UPDATE automation_step SET workflows = %s WHERE asid = %s;",(workflow_save, sd["step"]))

            conn.commit()
            cursor.close()
            conn.close()
        elif json_data['message']['type'] == 'remove_step_from_workflow':
            print(pylims.term(),f'Remove Step {sd["step"]} from Workflow {sd["wf"]} @ position {sd["pos"]}')
            conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
            cursor = conn.cursor()

            cursor.execute("SELECT steps FROM automation_workflow WHERE wfid = %s;",(sd["wf"],))
            result = cursor.fetchone()
            if result['steps']==None:
                result['steps']='[]'
            steps = json.loads(result['steps'])
            steps.pop(sd["pos"])
            step_save = json.dumps(steps)
            cursor.execute("UPDATE automation_workflow SET steps = %s WHERE wfid = %s;",(step_save, sd["wf"]))

            cursor.execute("SELECT workflows FROM automation_step WHERE asid = %s;",(sd["step"],))
            result = cursor.fetchone()
            if result['workflows']==None:
                result['workflows']='[]'  
            workflows = json.loads(result['workflows'])
            print('workflows1',workflows)
            index_pos = workflows.index(sd["wf"])
            print('index',index_pos)
            workflows.pop(index_pos)
            print('workflows2',workflows)
            workflow_save = json.dumps(workflows)
            cursor.execute("UPDATE automation_step SET workflows = %s WHERE asid = %s",(workflow_save, sd["step"]))

            conn.commit()
            cursor.close()
            conn.close()

        json_string = json.dumps(json_data)
        await self.channel_layer.group_send(
            "automation",  # Replace "channel_name" with the desired channel name
            {
                "type": "message",
                "message": json_string,
            },
        )
    
    # async def receive(self, text_data):
    #     # Broadcast the received message to all listeners on the channel
    #     print('text_data',text_data)
    #     data = json.loads(text_data)
    #     message_type = data.get('type')
    #     message_content = data.get('message')
    #     additional_data = data.get('data', {})
    #     await self.channel_layer.group_send(
    #         "automation",  # Replace "channel_name" with the desired channel name
    #         {
    #             "type": "message",
    #             "message_type": message_type,
    #             "message_content": message_content,
    #             "additional_data": additional_data,
    #         },
    #     )

    async def message(self, event):
        # Send the message to the WebSocket client
        await self.send(text_data=event["message"])



