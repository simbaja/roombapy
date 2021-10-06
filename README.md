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

# Mapping Information

The Roomba position is given as three coordinates: `x`, `y`, and `theta`.  The unit of measure for `x` and `y` is *cm*, theta is *degrees*.  The origin of the mapping coordinates is the position of the dock, which will have coordinates `(0,0,0)`

## Coordinates 
- Dock Front = -y
- Dock Back = +y
- Dock Left = -x
- Dock Right = -y

```
         | -y 
         |
-x -------------- +x
         |
         | +y
```

### Coordinates for Map Definitions

When defining maps, you will need to define two points, the upper left `p1` and lower right `p2`.  These coordinates would yield the maximum range for the roomba and will be translated into the image coordinate system automatically.

```
p1       | -y 
         |
-x -------------- +x
         |
         | +y   p2
```

## Degrees

Roomba reports positive degrees when turning left, and negative degrees when turning right, yielding a counter-clockwise direction.

```
         0
         | 
         |
90 -------------- -90
         |
         |
      -180/180    
```

