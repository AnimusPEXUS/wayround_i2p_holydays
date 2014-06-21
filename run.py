#!/usr/bin/python3

import org.wayround.holydays.env


if __name__ == '__main__':
    e = org.wayround.holydays.env.Environment(
        host='localhost',
        port=8085
        )
    e.start()
