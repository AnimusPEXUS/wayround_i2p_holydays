
import copy
import os
import datetime
import importlib
import gettext

import bottle
import mako.template

import org.wayround.utils.bottle
import org.wayround.utils.path
import org.wayround.utils.datetime_iso8601


class Templates:

    def __init__(self):
        self._tpl = {}
        self.reload()
        return

    def reload(self):

        d = org.wayround.utils.path.join(
            os.path.dirname(
                org.wayround.utils.path.abspath(__file__)
                ),
            'templates'
            )

        self._tpl = {}

        for i in os.listdir(d):
            if i.endswith('.html'):
                fn = org.wayround.utils.path.join(d, i)
                bn = os.path.basename(fn)[:-5]

                self._tpl[bn] = mako.template.Template(filename=fn)

        return

    def render(self, name, prog_trans, *args, **kwargs):
        return self._tpl[name].render(*args, prog_trans=prog_trans, **kwargs)


class Holydays:

    def __init__(self, enve):
        self._env = enve
        self._holy = {}
        self.reload()
        return

    def reload(self):

        d = org.wayround.utils.path.join(
            os.path.dirname(
                org.wayround.utils.path.abspath(__file__)
                ),
            'holydays'
            )

        self._holy = {}

        for i in os.listdir(d):
            if i.endswith('.py'):
                fn = org.wayround.utils.path.join(d, i)
                bn = os.path.basename(fn)[:-3]

                mod = importlib.import_module(
                    'org.wayround.holydays.holydays.{}'.format(bn)
                    )

                self._holy[bn] = mod.calculate_cal

        return

    def calculate_cal(self, y, lang='en', zoneinfo=None):

        ret = []

        if zoneinfo == None:
            zoneinfo = datetime.timezone(datetime.timedelta(hours=0))

        for i in sorted(list(self._holy.keys())):

            prog_trans = gettext.translation(
                'holydays',
                localedir=self._env.prog_locale_dir,
                languages=[lang]
                )

            trans = gettext.translation(
                i,
                localedir=self._env.locale_dir,
                languages=[lang]
                )

            for j in self._holy[i](y):

                if not 'options' in j:
                    j['options'] = []

                if not 'fargs' in j:
                    j['fargs'] = tuple()

                if not 'fkwargs' in j:
                    j['fkwargs'] = dict()

                if not 'msgid' in j:
                    j['msgid'] = 'no msgid'

                res_date, attrs = \
                    org.wayround.utils.datetime_iso8601.str_to_datetime(
                        j['date']
                        )

                if res_date == None:
                    raise Exception(
                        "Can't parse date: {} in module `{}'".format(
                            j['date'],
                            i
                            )
                        )

                j['date'] = res_date

                d = self.convert_to_pointed_year_date(j['date'], y)

                anniversary = None

                if not 'no-anniversary' in j['options']:

                    yp = int(self.years_past(j['date'], y, zoneinfo))
                    # print("yp: {}".format(yp))
                    if yp:
                        yp = int(yp)

                    if yp and yp != 0 and (yp == 1 or (yp % 5 == 0)):
                        anniversary = yp

                ret.append(
                    {'date': d,
                     'original_date': j['date'],
                     'msgstr': trans.gettext(
                        j['msgid'].format(
                            *j['fargs'],
                            **j['fkwargs']
                            )
                        ),
                     'anniversary': anniversary
                     }
                    )

        ret.sort(key=lambda x: x['date'])

        return ret

    def convert_to_pointed_year_date(self, dt, year):
        ret = copy.copy(dt)
        ret = ret.replace(year=year)
        return ret

    def years_past(self, dt, year, tzinfo):
        res = datetime.datetime(
            year=year,
            month=dt.month,
            day=dt.day,
            tzinfo=tzinfo
            ) - dt
        # print("seconds: {}".format(res.seconds))
        # print("days: {}".format(res.days))
        return res.days / 31 / 12

    #def _date_conv(self, x):
    #    res = org.wayround.utils.datetime_iso8601.str_to_datetime(x['date'])
    #    if res == None:
    #        raise Exception("Can't parse date: {}".format(x['date']))
    #    return res


class Environment:

    def __init__(
        self,
        host='localhost',
        port=8080
        ):

        self.host = host
        self.port = port

        self.tpl = Templates()
        self.holy = Holydays(self)

        self.app = bottle.Bottle()

        self.app.route('/index.html', 'GET', self.index)
        self.app.route('/main.html', 'GET', self.main)

        self.app.route('/css/<filename>', 'GET', self.css)

        self.prog_locale_dir = org.wayround.utils.path.join(
            os.path.dirname(
                org.wayround.utils.path.abspath(__file__)
                ),
            'i18n'
            )

        self.locale_dir = org.wayround.utils.path.join(
            os.path.dirname(
                org.wayround.utils.path.abspath(__file__)
                ),
            'holydays',
            'i18n'
            )

        self.css_dir = org.wayround.utils.path.join(
            os.path.dirname(
                org.wayround.utils.path.abspath(__file__)
                ),
            'css'
            )

        return

    def start(self):
        self.server = org.wayround.utils.bottle.WSGIRefServer(
            host=self.host, port=self.port
            )

        return bottle.run(
            self.app,
            host=self.host,
            port=self.port,
            server=self.server
            )

    def stop(self):
        self.server.srv.shutdown()

    def css(self, filename):
        return bottle.static_file(filename, root=self.css_dir)

    def html_tpl(self, title, body, prog_trans):
        return self.tpl.render(
            'html',
            title=title,
            body=body,
            prog_trans=prog_trans,
            css=['main.css']
            )

    def index(self):
        t = repr(self.holy.calculate_cal(2014))
        return self.html_tpl(title='index', body=t)

    def main(self):

        decoded_params = bottle.request.params.decode('utf-8')

        lang = 'en'
        if 'lang' in decoded_params:
            lang = decoded_params['lang']

        year = 2014
        if 'year' in decoded_params:
            lang = int(decoded_params['year'])

        prog_trans = gettext.translation(
            'holydays',
            localedir=self.prog_locale_dir,
            languages=[lang]
            )

        dates = self.holy.calculate_cal(year, lang)

        holyday_list = self.tpl.render(
            'holyday_list',
            dates=dates,
            prog_trans=prog_trans
            )

        main = self.tpl.render(
            'main',
            holyday_list=holyday_list,
            prog_trans=prog_trans
            )

        html = self.html_tpl(title='index', body=main, prog_trans=prog_trans)

        return html
