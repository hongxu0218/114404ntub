import os, sys
import django
from django.test import RequestFactory

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

from petapp import chat_service
import json

def test_api_logic():
    print("Testing API logic directly...")

    # Create a fake request
    factory = RequestFactory()
    request_data = {"message": "狗狗適合的運動量？"}
    request = factory.post('/api/chat/',
                          data=json.dumps(request_data),
                          content_type='application/json')

    # Add session
    from django.contrib.sessions.backends.db import SessionStore
    session = SessionStore()
    session.create()
    request.session = session

    print(f"Request message: {request_data['message']}")

    # Test the API function directly
    try:
        response = chat_service.api_chat(request)
        response_data = json.loads(response.content)

        print(f"Response: {response_data.get('reply', 'No reply')}")
        print(f"Sources: {len(response_data.get('sources', []))}")
        print(f"Handoff: {response_data.get('handoff', {})}")

    except Exception as e:
        print(f"API Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_logic()