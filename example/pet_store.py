import os

from typing import Optional

from pyintegration import Container
from pyintegration import lastBuilt

from constants import TEST_PETSTORE_IMAGE

IMAGE_BASE_NAME = 'openapi-petstore'
IMAGE_NAME = os.environ.get(TEST_PETSTORE_IMAGE, lastBuilt(IMAGE_BASE_NAME))

REST_PORT = 8080


class PetStore(Container):
    def __init__(
        self,
        name: str,
        image_name: str = IMAGE_NAME,
        rest_port: Optional[int] = REST_PORT,
        **kwargs,
    ):
        ports = kwargs.pop('portmap', {})
        ports.update({
            REST_PORT: rest_port,
        })
        super().__init__(name=name, image_name=image_name, portmap=ports, **kwargs)

    def getAddress(self) -> str:
        return self.hostAddrForPort(REST_PORT)

    def info(self) -> str:
        return self.getAddress()
