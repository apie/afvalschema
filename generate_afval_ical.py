#!/usr/bin/env python3
# Genereer ICAL met afvalophaaldagen, gebaseerd op een schema in settings.py
# By Apie 2023-12-17
# MIT license

import re
from icalendar import Event, Calendar
from datetime import timedelta, datetime
from os import path
from sys import argv
import pytz
import calendar

from settings import schema

timezone = "Europe/Amsterdam"
WEEKDAYS = {
    'maandag':   'MO',
    'dinsdag':   'TU',
    'woensdag':  'WE',
    'donderdag': 'TH',
    'vrijdag':   'FR',
    'zaterdag':  'SA',
    'zondag':    'SU',
}

def parse_rule(waste_type, d):
    rule, start_date, end_date, exception_str = re.findall(r'^(.+) van (.+) tot (.+?)( behalve .+)?$', d)[0]
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    freq, weekday = rule.split(' op ')

    freq = byday = interval = None
    rdate = set()
    exdate = set()
    if 'week' in rule or 'weken' in rule:
        freq = 'WEEKLY'
        if 'om de week' in rule:
            interval = 2
        elif m := re.findall(r'iedere (\w+) weken', rule):
            interval = int(m[0])

    if m := re.findall(r' op (\w+dag)$', rule):
        byday = WEEKDAYS[m[0]]

    if exception_str:
        ex_date_str, replace_date_str = re.findall(r'^ behalve (.+), dat wordt (.+)$', exception_str)[0]
        ex_date = datetime.strptime(ex_date_str, '%Y-%m-%d').date()
        replace_date = datetime.strptime(replace_date_str, '%Y-%m-%d').date()
        assert calendar.day_abbr[ex_date.weekday()][0:2].upper() == byday, f"Ex date not same weekday as rule. {waste_type=} {ex_date=}"
        exdate.add(ex_date)
        rdate.add(replace_date)

    assert all((freq, byday, interval)), f"Parsing of rule for {waste_type} failed"
    assert calendar.day_abbr[start_date.weekday()][0:2].upper() == byday, f"Start date not same weekday as rule. {waste_type=} {start_date=}"
    rrule = {'FREQ': [freq], 'BYDAY': byday, 'INTERVAL': interval, 'UNTIL': end_date}
    return start_date, waste_type, rrule, rdate, exdate

def lees_schema(schema):
    return [
        parse_rule(waste_type, d)
        for waste_type, d in schema.items()
    ]

def schrijf_ical(afvalkal):
    cal = Calendar()
    cal.add("prodid", f"-//Afvalkalender//")
    cal.add("version", "2.0")

    now = datetime.now(pytz.timezone(timezone))
    for date, waste_type, rrule, rdate, exdate in sorted(afvalkal):
        event = Event()
        event.add("summary", f"Afvalkalender {waste_type.capitalize()}")
        event.add('uid', str(now)+waste_type)
        event.add("dtstart", date)
        event.add("rrule", rrule)
        if rdate:
            event.add("rdate", rdate)
        if exdate:
            event.add("exdate", exdate)
        event.add("dtstamp", now)
        cal.add_component(event)

    with open(
        path.join(path.dirname(path.realpath(argv[0])), "afvalkalender.ics"), "wb"
    ) as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    parsed_schema = lees_schema(schema)
    schrijf_ical(parsed_schema)

