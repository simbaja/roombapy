# roombasdk

[![CI](https://github.com/pschmitt/roombasdk/actions/workflows/ci.yaml/badge.svg)](https://github.com/pschmitt/roombasdk/actions/workflows/ci.yaml)
![PyPI](https://img.shields.io/pypi/v/roombasdk)
![PyPI - Downloads](https://img.shields.io/pypi/dm/roombasdk)
![PyPI - License](https://img.shields.io/pypi/l/roombasdk)

Unofficial iRobot Roomba python library (SDK).

Fork of [NickWaterton/Roomba980-Python](https://github.com/NickWaterton/Roomba980-Python)<br/>
Fork of [pschmitt/roombapy](https://github.com/pschmitt/roombapy)

This library was created for the [Home Assistant Roomba integration](https://www.home-assistant.io/integrations/roomba/).

# Installation

```shell
pip install roombasdk
```

# Notes

This library is only for firmware 2.x.x [Check your robot version!](http://homesupport.irobot.com/app/answers/detail/a_id/529) 

Only local connections are supported.

# How to get your username/blid and password

To get password from Roomba type in console:

```shell
$ roomba-password <ip>
```

It will find your Roomba in local network, then follow the instructions in console to get password.
If IP address not provided password will be request for auto discovered robot. 

Also you can just ask Roomba for info:

```shell
$ roomba-discovery <optional ip address>
```

To test connection with iRobot:

```shell
$ roomba-connect <ip> <password>
```
