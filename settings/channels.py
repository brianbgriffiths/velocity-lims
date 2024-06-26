from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json

class automation(AsyncWebsocketConsumer):
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



