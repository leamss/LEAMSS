"""Test live WhatsApp message send to newly verified recipient 917083057910."""
import asyncio
import httpx

async def test_live_send():
    token = "EAAW0FmF4ZAp8BSbjgD650906fN5QuNXuc2Atjg9CZAt5oakWSZBdpBTQmMzTPy3pZBmvQJs5oBZB9Tb2Hp2ZBgSO98FrWDokUme9CfHQhJMOCdt3hIEkaiGoHvThqwzDAkjpJeBZBZCtz3AnHgbMtVU102ziMfBnCgPc7iRwD9Bl04F8ahqIZCTIsFSEwlXH2pGyw2gZDZD"
    phone_id = "552459977946600"
    url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    # 1. Test template message first (guaranteed delivery)
    payload_template = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "917083057910",
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {"code": "en_US"},
        },
    }
    print("--- 1. Testing Template Message ---")
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp_tpl = await client.post(url, json=payload_template, headers=headers)
        print("Template Send Status Code:", resp_tpl.status_code)
        print("Template Send Response:", resp_tpl.text)

    # 2. Test text message
    payload_text = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "917083057910",
        "type": "text",
        "text": {"preview_url": True, "body": "Hello Manali! Testing LEAMSS Live WhatsApp Chat."},
    }
    print("\n--- 2. Testing Text Message ---")
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp_txt = await client.post(url, json=payload_text, headers=headers)
        print("Text Send Status Code:", resp_txt.status_code)
        print("Text Send Response:", resp_txt.text)

if __name__ == "__main__":
    asyncio.run(test_live_send())
