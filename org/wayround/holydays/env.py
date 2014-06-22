
import calendar
import datetime
import gettext
import importlib
import os
import locale

import bottle
import mako.template

import org.wayround.utils.bottle
import org.wayround.utils.datetime_iso8601
import org.wayround.utils.path


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

                self._holy[bn] = mod.calculate_dates

        return

    def calculate_dates(self, y, lang='en', zoneinfo=None):

        ret = []

        if zoneinfo == None:
            zoneinfo = datetime.timezone(datetime.timedelta(hours=0))

        for i in sorted(list(self._holy.keys())):

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
        ret = dt.replace(year=year)
        return ret

    def years_past(self, dt, year, tzinfo):
        res = year - dt.year
        return res


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
        self.app.route('/month.html', 'GET', self.month)
        self.app.route('/year.html', 'GET', self.year)

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
        prog_trans = gettext.translation(
            'holydays',
            localedir=self.prog_locale_dir,
            languages=['en']
            )

        index = self.tpl.render(
            'index',
            prog_trans=prog_trans
            )

        return self.html_tpl(title='index', body=index, prog_trans=prog_trans)

    def holyday_list(self, dates, prog_trans):

        holyday_list = self.tpl.render(
            'holyday_list',
            dates=dates,
            prog_trans=prog_trans
            )

        return holyday_list

    def main(self):

        decoded_params = bottle.request.params.decode('utf-8')

        lang = 'en'
        if 'lang' in decoded_params:
            lang = decoded_params['lang']

        year = 2014
        if 'year' in decoded_params:
            year = int(decoded_params['year'])

        prog_trans = gettext.translation(
            'holydays',
            localedir=self.prog_locale_dir,
            languages=[lang]
            )

        dates = self.holy.calculate_dates(year, lang)

        holyday_list = self.holyday_list(dates, prog_trans)

        main = self.tpl.render(
            'main',
            holyday_list=holyday_list,
            prog_trans=prog_trans
            )

        html = self.html_tpl(title='index', body=main, prog_trans=prog_trans)

        return html

    def gen_cal_month(self, dates, year, month, lang='en'):

        ret = []

        cal = calendar.Calendar()
        res = cal.monthdatescalendar(year, month)

        for weeks in res:

            week = []

            for days in weeks:

                found = []
                for i in dates:
                    if (i['date'].month == days.month
                        and i['date'].day == days.day):

                        found.append(i)

                week.append(
                    {
                     'date': days,
                     'dates': found
                     }
                    )

            ret.append(week)

        return ret

    def gen_cal_month_html(self, dates, year, month, lang='en'):

        res = self.gen_cal_month(dates, year, month, lang='en')

        prog_trans = gettext.translation(
            'holydays',
            localedir=self.prog_locale_dir,
            languages=[lang]
            )

        m = self.tpl.render('month', prog_trans=prog_trans, month=res)

        return m

    def month(self):

        decoded_params = bottle.request.params.decode('utf-8')

        cd = datetime.datetime.now()

        lang = 'en'
        if 'lang' in decoded_params:
            lang = decoded_params['lang']

        year = cd.year
        if 'year' in decoded_params:
            year = int(decoded_params['year'])

        month = cd.month
        if 'month' in decoded_params:
            month = int(decoded_params['month'])

        add_hl = False
        if ('list' in decoded_params
            and decoded_params['list'] in ['1', 'on', 'yes']):
            add_hl = True

        dates = self.holy.calculate_dates(year, lang)

        prog_trans = gettext.translation(
            'holydays',
            localedir=self.prog_locale_dir,
            languages=[lang]
            )

        m = self.gen_cal_month_html(dates, year, month, lang)

        hl_t = ''
        if add_hl:
            dd = []
            for i in dates:
                if i['date'].month == month:
                    dd.append(i)

            hl_t = self.holyday_list(dd, prog_trans)

        html = self.html_tpl(
            'one month calendar',
            body=m + hl_t,
            prog_trans=prog_trans
            )

        return html

    def year(self):

        decoded_params = bottle.request.params.decode('utf-8')

        cd = datetime.datetime.now()

        lang = 'en'
        if 'lang' in decoded_params:
            lang = decoded_params['lang']

        year = cd.year
        if 'year' in decoded_params:
            year = int(decoded_params['year'])

        add_hl = False
        if ('list' in decoded_params
            and decoded_params['list'] in ['1', 'on', 'yes']):
            add_hl = True

        dates = self.holy.calculate_dates(year, lang)

        year_lst = []
        for i in range(1, 13):
            year_lst.append(self.gen_cal_month_html(dates, year, i, lang))

        prog_trans = gettext.translation(
            'holydays',
            localedir=self.prog_locale_dir,
            languages=[lang]
            )

        y = self.tpl.render(
            'year',
            prog_trans=prog_trans,
            year=year_lst,
            year_date=year
            )

        hl_t = ''
        if add_hl:
            hl_t = self.holyday_list(dates, prog_trans)

        html = self.html_tpl(
            'one month calendar',
            body=y + hl_t,
            prog_trans=prog_trans
            )

        return html
