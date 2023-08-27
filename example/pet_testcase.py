from typing import Dict
from typing import List

from pyintegration import IntegrationTestCase

from pet_store import PetStore


class PetStoreTestCase(IntegrationTestCase):
    """
    This class extends the IntegrationTestCase with some PetStore specific functions.
    """

    def startPetStore(self, name: str, env: Dict[str, str] = {}) -> PetStore:
        container = PetStore(name=name, rest_port=0, environment=env)
        container.start()
        self.addContainer(container)
        return container

    def getPetStores(self) -> List[PetStore]:
        return self.getContainerClass(PetStore)

    def basicSetup(self, env: Dict[str, str] = {}) -> None:
        for name in ["petstore-a", "petstore-b"]:
            try:
                self.startPetStore(name=name, env=env)
            except Exception as ex:
                self.tearDown()
                raise ex
        self.waitForReady(self.getPetStores())
