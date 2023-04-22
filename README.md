# Pyintegration

Welcome to the Pyintegration project. This code is an extension to the Python unittest framework that enables integration testing easy.

## Background

The origins of this came from the [CloudTruth CLI](https://github.com/cloudtruth/cloudtruth-cli) integration tests. The framework was adapated elsewhere to integration test Helidon containers, and this work largely reflects (or will reflect) those enhancements.

## Uses

The intention of this framework is to provide a means of quickly tests.

## Features

Here are the features that Pyintegration supports:
* Setup/Cleanup
* Report generation
* Data capture

### Setup/Cleanup

The Setup/Cleanup functions are part of most test frameworks. These parts of the framework help insure that prerequisite resources are in place NOT stranded

### Report Generation

Running the tests will be done by extending the `IntegrationTestRunner`.

### Data Capture

The framework has different data capture options built in, such that it is easy to add your data to the mix. By default, the data is captured on failure making it easy to debug issues (without the ardurous process of trying to reproduce the errors).
