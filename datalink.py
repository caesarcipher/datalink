#!/usr/bin/env python3

# datalink - an open source intelligence gathering tool
# from caesarcipher
# version 20200824

from re import match

from os import path
from re import match
from sys import argv
from math import ceil
from lxml import html
from json import loads
from os import getcwd
from urllib.parse import quote
from argparse import ArgumentParser
from requests import get, post, Session

from urllib3 import disable_warnings
disable_warnings()

linkedin = None
proxies = {
  'http': 'http://localhost:8080',
  'https': 'http://localhost:8080',
}

def intake(msg):
    try:
        response = input(msg)
    except KeyboardInterrupt:
        bombout()
    return response

def out(msg = '', punc='!', pre='', post=''):
    # out = ''
    # for line in msg:
    if len(punc) > 1:
        out = '\t{0} {1} {2}'.format(punc[::-1], msg, punc)
    else:
        out = '\t{0} {1} {0}'.format(punc, msg)
    print(f'{pre}{out}{post}')

def bombout(msg = '', punc='!', pre='', post=''):
    # out = ''
    # for line in msg:
    if len(punc) > 1:
        out = '\t{0} {1} {2}'.format(punc[::-1], msg, punc)
    else:
        out = '\t{0} {1} {0}'.format(punc, msg)
    exit('{}{}{}\n'.format(pre, out, post))

def configure(args, confFile):
    from configparser import ConfigParser

    for fileLoc in {'.', '~'}:
        confFileLoc = f'{fileLoc}/{confFile}'
        if path.isfile(confFileLoc):
            conf = confFileLoc
            break

    config = ConfigParser()
    config.read(conf)

    args.username = config['linkedin.com']['username']
    args.password = config['linkedin.com']['password']

def writeResults(output, fileName = 'output.txt'):
    try:
        f = open(fileName, 'w')
    except IOError:
        bombout('error writing file')

    f.write(output)
    f.close()

def initialiseTokenli(username, password):
    global linkedin
    linkedin = Session()
    linkedin.headers.update({'User-Agent': None})

    quser = quote(username)
    qpass = quote(password)

    loginPageRequest = linkedin.get('https://www.linkedin.com/login', proxies=proxies, verify=False)

    csrf = match(r'"(ajax:[\d]+)', loginPageRequest.cookies['JSESSIONID']).group(1)
    linkedin.headers.update({'Csrf-Token': csrf})

    loginCsrf = match('"v=2&([^"]+)', loginPageRequest.cookies['bcookie']).group(1)
    data = 'session_key={}&session_password={}&loginCsrfParam={}'.format(quser, qpass, loginCsrf)

    resp = linkedin.post('https://www.linkedin.com/login-submit', allow_redirects=False, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, proxies=proxies, verify=False)

    redir = resp.headers.get('Location')

    if 'feed' not in redir:
        bombout('checkpoint violation? Location: "%s"' % redir, punc='?!')

def searchCompaniesli(domain, company):
    choice = list()

    target = 'https://www.linkedin.com/voyager/api/typeahead/hitsV2?keywords=%s&original=GLOBAL_SEARCH_HEADER&q=blended' % (domain)

    typeaheadSearchResults = linkedin.get(target, proxies=proxies, verify=False)
    
    resultBlobJSON = loads(typeaheadSearchResults.text)

    for result in resultBlobJSON['elements']:
        # TODO review the following line for potential improvements
        if 'keywords' in result or 'Event' in result['subtext']['text'] or 'GHOST' in result['image']['attributes'][0]['sourceType'] or 'GROUP' in result['image']['attributes'][0]['sourceType']:
            continue

        try:
            companyId = match('urn:li:company:([0-9]+)', result['objectUrn']).group(1)
        except AttributeError as e:
            out(result, punc='?', post='\n')
            out('nah bruv - id (%s)' % e, punc='.')
            continue

        try:
            companyRealm = match(r'(?:• [^ ]+ )?• \(?([^\)]+)', result['subtext']['text']).group(1)
        except AttributeError as e:
            out(result, punc='?', post='\n')
            out('nah bruv - realm (%s)' % e, punc='..')
            continue

        try:
            companyName = result['image']['attributes'][0]['miniCompany']['name']
        except KeyError as e:
            out(result, punc='?', post='\n')
            out('nah bruv - name (%s)' % e, punc='...')
            continue

        try:
            out('{}{:^16}\033[96m{}\033[00m  (\033[90m{}\033[00m)'.format(len(choice)+1, companyId, companyName, companyRealm, ), punc='', post='')
            choice.append(companyId)
        except AttributeError as e:
            out('nah bruv')

    out('{}{:^16}{}'.format(0, '[EXIT]', '-none of the above-'), punc='', post='\n')

    selection = ''
    while not selection:
        selection = intake('which target to scrape? > ')
        if selection == '0':
            bombout('exiting')

    choice = choice[int(selection)-1]

    out('okay, targeting %s' % choice, pre='\n', post='\n')

    return choice

def getCompanyInfoli(id, force=None):
    output = list()
    target = 'https://www.linkedin.com/search/results/people/?facetCurrentCompany=%s' % id

    resp = linkedin.get(target, proxies=proxies, verify=False)

    page = html.document_fromstring(resp.content)
    employeeblob = loads(page.xpath('//text()[contains(., "memberDistance")]')[0].strip())

    numEmployees = int(employeeblob['data']['metadata']['totalResultCount'])
    numPages = ceil(numEmployees/10)
    out('target apears to have %s employees (across %s pages of results)' % (numEmployees, numPages))

    if numEmployees > 1000:
        if not force:
            out('target has too many results for a free account, stopping at 100th page')
            numPages = 100
        else:
            out('user has chosen to enumerate all %s target pages' % (numPages))

        out(punc='')

    for employee in employeeblob['data']['elements'][1]['elements']:
        name = employee['title']['text']
        title = employee['headline']['text']
        location = employee['subline']['text']
        out('{:28}{:32}{}'.format(name, location, title), punc='')
        output.append([name, location, title])

    for pageCount in range(2, numPages+1):
        subtarget = '{}&page={}'.format(target, pageCount) 

        resp = linkedin.get(subtarget, proxies=proxies, verify=False)

        page = html.document_fromstring(resp.content)

        # TODO this next line needs to be more robust to account for if linkedin shuffles things around
        employeeblob = loads(page.xpath('//text()[contains(., "memberDistance")]')[0].strip())  # [-1] instead of [0]?

        for employee in employeeblob['data']['elements'][0]['elements']:
            name = employee['title']['text']
            title = employee['headline']['text']
            location = employee['subline']['text']
            out('{:28}{:32}{}'.format(name, location, title), punc='')
            output.append([name, location, title])

    names=raw = ''
    for entry in output:
        raw += f'{entry[0]},{entry[1]},{entry[2]}\n'
        names += f'{entry[0]}\n'

    writeResults(raw, 'raw.csv')
    writeResults(names)

def main():
    parser = ArgumentParser()
    parser.add_argument('-d', '--domain')
    parser.add_argument('-c', '--company')
    parser.add_argument('-u', '--username')
    parser.add_argument('-p', '--password')
    parser.add_argument('-o', '--output')
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('--id')
    parser.add_argument('--conf')

    args = parser.parse_args()

    if args.conf:
       configure(args, args.conf)

    if not (args.username and args.password):
        bombout('credentials not specified, but are required')

    if not args.id:
        while not args.domain:
            args.domain = intake('target domain? [example.com] > ')

        if not args.company:
            args.company = args.domain.split('.')[0]

    if args.domain and args.company:
        out('domain:\t%s' % (args.domain), '', pre='\n')
        out('company:\t%s' % (args.company), '')
    if args.id:
        out('target id:\t%s' % (args.id), '', pre='\n')
    out('username:\t%s' % (args.username), '')
    out('password:\t%s' % (args.password), '', post='\n')

    if intake('\tlook good enough to continue? [Y/n] ').lower() not in {'', 'y', 'ye', 'yes', 'yeet', 'yarp', 'yolo'}:
        bombout('exiting')

    initialiseTokenli(args.username, args.password)

    if not args.id:
        args.id = searchCompaniesli(args.domain, args.company)

    getCompanyInfoli(args.id, args.force)

if __name__ == '__main__':
    main()
