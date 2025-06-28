import json

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        print(f"📥 Received payload: {body}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Received IP data successfully',
                'input': body
            }),
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
