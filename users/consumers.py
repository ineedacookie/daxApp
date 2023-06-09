import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get the user ID from the session
        user_id = self.scope['user'].id
        print("Connected")

        # Set the channel name to "user_{user_id}"
        self.group_name = 'user_' + str(user_id)

        # Add the user ID to the group named after the user ID
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        print("Disconnected")
        # Remove the user ID from the group named after the user ID
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_message(self, event):
        # Send a message to the WebSocket
        print("IT IS WORKING")
        await self.send(text_data=json.dumps(event['data']))
