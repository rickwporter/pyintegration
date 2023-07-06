import os
import docker
import tarfile
import tempfile

from abc import ABC
from abc import abstractmethod
from datetime import datetime
from datetime import timedelta
from time import sleep
from typing import Dict
from typing import List
from typing import Optional

from .constants import DEFAULT_CONTAINER_POLL_MAX
from .constants import DEFAULT_CONTAINER_POLL_MIN
from .constants import DEFAULT_CONTAINER_POLL_START
from .constants import DEFAULT_CONTAINER_READY_TIMEOUT
from .result import Result
from .utils import bytesToString
from .utils import envPrintOutput
from .utils import envPrintCommands
from .utils import getLocalIp

ANY_HOST = '0.0.0.0'


class Container(ABC):
    def __init__(
        self,
        name: str,
        image_name: str,
        print_commands: Optional[int] = None,
        print_output: Optional[int] = None,
        userid: int = os.getuid(),
        auto_removal: bool = True,
        portmap: Dict[int, int] = {},
        volumes: Dict[str, Dict] = {},
        environment: Dict[str, str] = {},
    ):
        self.name: str = name
        self.image_name: str = image_name
        self.print_commands: int = envPrintCommands(print_commands)
        self.print_output: int = envPrintOutput(print_output)
        self.userid: Optional[int] = userid
        self.auto_removal: bool = auto_removal
        self.portmap: Dict[int, int] = portmap
        self.volumes: Dict[str, Dict] = volumes
        self.environment: Dict[str, str] = environment

        # initialize things that are not args
        self.container: Optional[docker.models.containers.Container] = None
        self.last_log_size: int = 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, container={self.containerName()})"

    @abstractmethod
    def info(self) -> str:
        """
        Abstract method to give info about the container
        """
        return ""

    def start(self) -> None:
        if self.container:
            print(f"Already running {self}")
            return

        if not imageExists(self.image_name):
            raise FileNotFoundError(f"{self.__class__.__name__} image {self.image_name} does not exist")

        dockerClient = docker.from_env()
        self.container = dockerClient.containers.run(
            name=self.name,
            image=self.image_name,
            remove=True,  # remove teh container when done running
            detach=True,  # run in background
            **self.startArgs()
        )

        # NOTE: refresh() to get the ports (when using ephemeral ports)
        self.refresh()

        if self.print_commands:
            info = self.info()
            extra = ' - ' + info if info else ''
            print(f"Started '{self.name}' ({self.image_name}{extra})")

        return

    def startArgs(self) -> Dict:
        args = {
            'auto_remove': self.auto_removal,
        }
        if self.userid is not None:
            args['user'] = str(self.userid)
        if self.volumes:
            args['volumes'] = self.volumes
        if self.portmap:
            args['ports'] = {str(k): str(v) for k, v in self.portmap.items() if v is not None}
        if self.environment:
            args['environment'] = self.environment

        return args

    def containerName(self) -> Optional[str]:
        if not self.container:
            return None
        return self.container.short_id

    def _findByName(self, name: str) -> Optional[docker.models.containers.Container]:
        dockerClient = docker.from_env()
        containers = dockerClient.containers.list()
        for c in containers:
            if c.name == name:
                return c
        return None

    def refresh(self) -> None:
        if not self.container:
            return
        self.container = self._findByName(self.name)

    def resolve(self) -> None:
        self.refresh()

    def status(self) -> Optional[str]:
        if not self.container:
            return None
        return self.container.status

    def stop(self) -> None:
        if not self.container:
            return None
        self.container.stop()
        if self.print_commands:
            print(f"Stopped '{self.name}'")
        self.container = None  # set back to None, so we don't try to stop again
        return

    def kill(self) -> None:
        if not self.container:
            return
        self.container.kill()
        if self.print_commands:
            print(f"Killed '{self.name}'")
        self.container = None  # set back to None, so we don't try to stop again
        return

    def terminate(self) -> None:
        if not self.container:
            return
        try:
            self.container.kill()
            self.container = None
            if self.print_commands:
                print(f"Terminated '{self.name}'")
        except Exception as ex:
            print(f"Failed to kill '{self.name}': {ex}")
        return

    def logs(self) -> str:
        """
        Gets the container logs in string form (converted from bytes)
        """
        if not self.container:
            return ""
        return bytesToString(self.container.logs())

    def logSnapshotSet(self) -> Result:
        """
        Caches the current log size, for later comparison
        """
        cmd = f"docker logs {self.name} | wc --chars"
        if self.print_commands:
            print(cmd)

        start = datetime.now()
        self.last_log_size = len(self.logs())
        delta = datetime.now() - start

        output = f"logSize: {self.last_log_size}"
        if self.print_output:
            print(output)

        return Result(
            return_value=0,
            command=cmd,
            timediff=delta,
            stdout=[output, ""],
            stderr=[]
        )

    def logSnapshotDiff(self) -> Result:
        """
        Get the logs since the last snapshot
        """
        cmd = f"docker logs {self.name} | tail -c +{self.last_log_size}"
        if self.print_commands:
            print(cmd)

        start = datetime.now()
        logs = self.logs()[self.last_log_size:]
        delta = datetime.now() - start

        if self.print_output:
            print(logs)

        return Result(
            return_value=0,
            command=cmd,
            timediff=delta,
            stdout=logs.split('\n'),
            stderr=[]
        )

    def isReady(self) -> bool:
        """
        Reports whether the container is "running"
        """
        if not self.container:
            return False
        self.refresh()  # make sure we get the latest
        return self.container.status == "running"

    def runningImage(self) -> Optional[str]:
        """
        Prints the image name of the running container (if running)
        """
        if not self.container:
            return None
        tags = self.container.image.tags
        if tags:
            return tags[0]
        return None

    def shellCmd(self, cmd: str) -> Result:
        """
        Runs the specifed cmd in the container and returns the `Result`.
        """
        if not self.container:
            raise RuntimeError(f"Container '{self.name}' is not started: cannot run '{cmd}'")

        command = f"{self.name} exec: {cmd}"
        if self.print_commands:
            print(command)

        start = datetime.now()
        exec_result = self.container.exec_run(cmd)
        delta = datetime.now() - start
        output = bytesToString(exec_result.output)

        if self.print_output:
            print(output)

        return Result(
            return_value=exec_result.exit_code,
            command=command,
            timediff=delta,
            stdout=output.split('\n'),
            stderr=[],
        )

    def hostAddrForPort(self, internalPort: int) -> Optional[str]:
        """
        Returns the localhost address:port for the specified internal port for a running container.
        """
        if not self.container:
            return None

        ports = self.container.ports
        if not ports:
            return None

        iport = str(internalPort)
        for key, values in ports.items():
            if iport not in key:
                continue

            for v in values:
                ipaddr = v.get('HostIp', ANY_HOST)
                if ipaddr == ANY_HOST:
                    ipaddr = getLocalIp()
                return f"{ipaddr}:{v.get('HostPort')}"

    def setMount(self, hostPath: str, containerPath: Optional[str] = None, mode: str = 'rw'):
        if self.container:
            raise RuntimeError(f"Cannot set {self.name} mounts after running")

        if not containerPath:
            self.volumes.pop(hostPath, None)
        else:
            self.volumes.upate({hostPath: {'bind': containerPath, 'mode': mode}})
        return

    def copyDir(self, hostDir: str, containerDir: str) -> None:
        if not self.container:
            raise RuntimeError(f"Cannot copy to '{self.name}' until it is running")

        tarname = tempfile.mktemp(prefix=self.name + '-', suffix='.tar')
        tf = tarfile.open(tarname, mode='w')
        tf.add(hostDir, arcname='')  # empty 'arcname' drops the path from the name
        tf.close()

        df = open(tarname, 'rb')
        self.container.put_archive(containerDir, df)
        df.close()
        os.unlink(tarname)
        return


def lastBuilt(base_image: str) -> str:
    """
    Looks for the latest build of the `base_image` in the local repository
    """
    found_time = None
    found_image = None

    dockerClient = docker.from_env()
    images = dockerClient.images.list()
    for img in images:
        tags = img.attrs.get('RepoTags', [])
        matches = [_ for _ in tags if base_image in _]
        if not matches:
            continue

        build_time = img.attrs.get('Created')
        if not found_time or build_time > found_time:
            found_time = build_time
            found_image = matches[0]

    return found_image


def imageExists(image_name: str) -> bool:
    """
    Looks for match of the full image name in the local repository.
    """
    dockerClient = docker.from_env()
    images = dockerClient.images.list()
    for img in images:
        tags = img.attrs.get('RepoTags', [])
        if any([_ for _ in tags if image_name == _]):
            return True

    return False


def waitForReady(
    containers: List[Container],
    max_wait_seconds: float = DEFAULT_CONTAINER_READY_TIMEOUT,
    max_poll_seconds: float = DEFAULT_CONTAINER_POLL_MAX,
    start_poll_seconds: float = DEFAULT_CONTAINER_POLL_START,
    message: Optional[str] = None,
    verbose: int = 0,
) -> Optional[List[Container]]:
    """
    Waits for all the containers to be ready, or reaches the max_wait_seconds.
    """
    reason = message if message else f"{len(containers)} containers to be ready"

    if verbose > 0:
        print(f"Waiting for up to {max_wait_seconds} seconds for {reason}")

    poll_seconds = max(start_poll_seconds, DEFAULT_CONTAINER_POLL_MIN)
    starttime = currtime = datetime.now()
    endtime = starttime + timedelta(seconds=max_wait_seconds)
    unready = [_ for _ in containers]
    while endtime >= currtime:
        unready = [_ for _ in unready if not _.isReady()]
        checktime = datetime.now() - currtime
        if checktime.total_seconds() > 1.0 and verbose > 0:
            print(f"Checking took {checktime.total_seconds()} seconds")

        if not unready:
            break

        poll_seconds = min(poll_seconds, max_poll_seconds)
        if verbose > 1:
            print(f"Waiting {poll_seconds} seconds before checking on {len(unready)} containers")

        sleep(poll_seconds)
        poll_seconds *= 2
        currtime = datetime.now()

    deltatime = datetime.now() - starttime
    if unready:
        names = [_.name for _ in unready]
        if verbose > 0:
            print(f"Waited {deltatime.total_seconds()} for {reason} -- still had unready: {', '.join(names)}")
        return unready

    if verbose > 0 and deltatime.total_seconds() > max_wait_seconds / 2:
        print(f"Took {deltatime.total_seconds()} of {max_wait_seconds} for {reason} -- consider increasing timeout")
    return None
