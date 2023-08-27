import json
import requests

from time import sleep

from pet_testcase import PetStoreTestCase
from constants import DEFAULT_HDRS


class TestBasic(PetStoreTestCase):
    def setUp(self):
        super().setUp()
        self.basicSetup()

    def test_basic_user(self):
        containers = self.getPetStores()
        psA = containers[0].getAddress()
        psB = containers[1].getAddress()

        user_info = {
            "firstName": "Rick",
            "lastName": "Porter",
            "password": "abc123",
            "userStatus": 99,
            "phone": "8675309",
            "id": 0,
            "email": "rickwporter@gmail.com",
            "username": "rickp",
        }

        # NOTE: this is hacky... should have a better way to wait for ready
        sleep(15)

        for addr in (psA, psB):
            base_url = f"http://{addr}"
            url = base_url + "/v3/user"
            resp = requests.post(url, data=json.dumps(user_info), headers=DEFAULT_HDRS)
            self.assertEqual(200, resp.status_code)

            url = base_url + f"/v3/user/{user_info.get('username')}"
            resp = requests.get(url, headers=DEFAULT_HDRS)
            self.assertEqual(200, resp.status_code)
            self.assertEqual(user_info, resp.json())
