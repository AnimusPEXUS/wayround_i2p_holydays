#!/usr/bin/python3

import os.path
import subprocess

if __name__ == '__main__':

    pwd = os.path.dirname(os.path.abspath(__file__))

    for i in ['i18n', 'holydays/i18n']:

        fpd = os.path.join(pwd, i)

        print("{}:".format(os.path.relpath(fpd, pwd)))

        for j in sorted(os.listdir(fpd)):

            fpd2 = os.path.join(fpd, j, 'LC_MESSAGES')

            for k in sorted(os.listdir(fpd2)):

                if k.endswith('.po'):

                    fp = os.path.join(fpd2, k)

                    print("   {}".format(os.path.relpath(fp, pwd)))

                    p = subprocess.Popen(
                        ['msgfmt',
                         '-o',
                         '{}.mo'.format(fp[:-3]),
                         fp
                         ]
                        )
                    p.wait()
