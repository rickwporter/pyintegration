# These are related to the Container time values in the waitForReady() function
DEFAULT_CONTAINER_POLL_START = 0.5
DEFAULT_CONTAINER_POLL_MAX = 2.0
DEFAULT_CONTAINER_POLL_MIN = 0.25
DEFAULT_CONTAINER_READY_TIMEOUT = 30.0

# This is used as a 'curl' timeout -- it is short to avoid stalling tests while waiting for a response
DEFAULT_REQUEST_TIMEOUT = 0.5

# These are environment variable names used by the test framework
PYINT_CAPTURE = "PYINT_TEST_CAPTURE"
PYINT_JOB_ID = "PYINT_TEST_JOB_ID"
PYINT_KNOWN_ISSUES = "PYINT_TEST_KNOWN_ISSUES"
PYINT_PRINT_COMMANDS = "PYINT_TEST_LOG_COMMANDS"
PYINT_PRINT_OUTPUT = "PYINT_TEST_LOG_OUTPUT"

# These are for request processing -- some standard headers for REST requests
HDR_ACCEPT = "accept"
HDR_CONTENT = "Content-Type"

ACCEPT_ANY = "*/*"
APP_JSON = "application/json"

DEFAULT_HDRS = {
    HDR_ACCEPT: APP_JSON,
    HDR_CONTENT: APP_JSON,
}
