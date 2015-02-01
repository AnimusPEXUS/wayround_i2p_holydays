#!/usr/bin/python3

import wayround_org.holydays.env


if __name__ == '__main__':
    e = wayround_org.holydays.env.Environment(
        host='localhost',
        port=8085
        )
    e.start()
