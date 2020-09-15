#!/usr/bin/env python3

# datalink - an open source intelligence gathering tool
# from caesarcipher
# version 200915

from re import match

from os import path, getenv
from re import match
from sys import argv
from math import ceil
from lxml import html
from json import loads
from os import getcwd, system
from urllib.parse import quote
from argparse import ArgumentParser
from requests import get, post, Session

from urllib3 import disable_warnings
disable_warnings()

linkedin = None

def intake(msg, pre=None):
    try:
        if pre:
            response = input(f'{pre}{msg}')
        else:
            response = input(msg)
    except KeyboardInterrupt:
        bombout(punc='')
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

def _get(token, target, proxy):
    if not proxy:
        return token.get(target)
    else:
        return token.get(target, proxies=proxy, verify=False)

def _post(token, target, proxy):
    if not proxy:
        return token.post(target)
    else:
        return token.post(target, proxies=proxy, verify=False)

def mangleNames(inFile, outFile='output_mangled.txt'):
    try:
        f = open(inFile)
    except IOError as e:
        bombout('error opening file - %s' % e)

    data = f.read()

    filters = {r',.*'}

    # TODO rectify/mutate data!

    writeResults(data, outFile)
    bombout('input file (%s) successfully mangled (%s)' % (inFile, outFile))

def configure(args, confFile):
    from configparser import ConfigParser

    conf = None

    for fileLoc in {getenv("HOME"), '.'}:
        confFileLoc = f'{fileLoc}/{confFile}'
        if path.isfile(confFileLoc):
            conf = confFileLoc
            break

    if not conf:
        bombout(f'configuration file {confFile} not found')

    config = ConfigParser()
    config.read(conf)

    args.username = config.get('linkedin.com', 'username')
    args.password = config.get('linkedin.com', 'password')

    if config.has_option('linkedin.com', 'proxy'):
        args.proxy = { 'http': config.get('linkedin.com', 'proxy'), 'https': config.get('linkedin.com', 'proxy') }


def writeResults(output, fileName = 'output.txt'):
    try:
        f = open(fileName, 'w')
    except IOError as e:
        bombout('error writing file %s' % e)

    f.write(output)
    f.close()

def initialiseTokenli(username, password, proxy):
    global linkedin
    linkedin = Session()
    linkedin.headers.update({'User-Agent': None})

    quser = quote(username)
    qpass = quote(password)

    loginPageRequest = _get(linkedin, 'https://www.linkedin.com/login', proxy)

    csrf = match(r'"(ajax:[\d]+)', loginPageRequest.cookies['JSESSIONID']).group(1)
    linkedin.headers.update({'Csrf-Token': csrf})

    loginCsrf = match('"v=2&([^"]+)', loginPageRequest.cookies['bcookie']).group(1)
    data = 'session_key={}&session_password={}&loginCsrfParam={}'.format(quser, qpass, loginCsrf)

    # TODO - convert to _post() call
    resp = linkedin.post('https://www.linkedin.com/login-submit', allow_redirects=False, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})#, proxies=proxies, verify=False)

    redir = resp.headers.get('Location')

    if redir and 'feed' not in redir:
        bombout('checkpoint violation? Location: "%s"' % redir, punc='?!')

def searchCompaniesli(domain, company, proxy):
    choice = list()

    target = 'https://www.linkedin.com/voyager/api/typeahead/hitsV2?keywords=%s&original=GLOBAL_SEARCH_HEADER&q=blended' % (domain if domain else company)

    typeaheadSearchResults = _get(linkedin, target, proxy)
    
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

    # TODO
    # look good enough to continue? [Y/n] 
    # 0     [EXIT]     -none of the above- 

    # which target to scrape? > 1
    # Traceback (most recent call last):
    # File "/usr/local/bin/datalink", line 306, in <module>
    #     main()
    # File "/usr/local/bin/datalink", line 300, in main
    #     args.id = searchCompaniesli(args.domain, args.company, args.proxy)
    # File "/usr/local/bin/datalink", line 186, in searchCompaniesli
    #     choice = choice[int(selection)-1]
    # IndexError: list index out of range
    selection = ''
    while not selection:
        selection = intake('which target to scrape? > ')
        if selection == '0':
            bombout('exiting')

    choice = choice[int(selection)-1]

    out('okay, targeting %s' % choice, pre='\n', post='\n')

    return choice

def getCompanyInfoli(id, company, outfile=None, force=None, proxy=None):
    output = list()
    target = 'https://www.linkedin.com/search/results/people/?facetCurrentCompany=%s' % id

    resp = _get(linkedin, target, proxy)

    page = html.document_fromstring(resp.content)

    employeeblob = loads(page.xpath('//text()[contains(., "memberDistance")]')[0].strip())

    numEmployees = int(employeeblob['data']['metadata']['totalResultCount'])
    numPages = ceil(numEmployees/10)
    out('target apears to have %s employees (across %s pages of results)' % (numEmployees, numPages), post='\n')

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

        resp = _get(linkedin, subtarget, proxy)

        page = html.document_fromstring(resp.content)
        employeeblob = loads(page.xpath('//text()[contains(., "memberDistance")]')[-1].strip())

        for employee in employeeblob['data']['elements'][0]['elements']:
            name = employee['title']['text']
            try:
                title = employee['headline']['text']
            except KeyError as e:
                out('oops %s' % e)
            location = employee['subline']['text']
            out('{:28}{:32}{}'.format(name, location, title), punc='')
            output.append([name, location, title])

    names=raw = ''
    for entry in output:
        raw += f'{entry[0]},{entry[1]},{entry[2]}\n'
        names += f'{entry[0]}\n'

    # TODO probably ought to add timestamps
    if outfile:
        fileout = outfile
    elif company:
        fileout = f'{company}.txt'
    else:
        fileout = f'{id}.txt'

    writeResults(names, fileout)
    writeResults(raw, f'raw_{fileout}')

    # TODO this should count lines not total length
    # out(f'wrote {len(names)} results to {fileout}', pre='\n')
    out(f'results written to {fileout}', pre='\n')

def main():
    parser = ArgumentParser()
    parser.add_argument('-d', '--domain')
    parser.add_argument('-c', '--company')
    parser.add_argument('-u', '--username')
    parser.add_argument('-p', '--password')
    parser.add_argument('-o', '--output')
    parser.add_argument('-f', '--force', action='store_true')
    # parser.add_argument('-m', '--mangle')
    parser.add_argument('--id')
    parser.add_argument('--conf')
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--proxy')
 
    args = parser.parse_args()

    # if args.mangle:
    #     mangleNames(args.mangle, args.output)

    if args.conf:
       configure(args, args.conf)

    # TODO better dynamic cred intake
    if not (args.username and args.password):
        parser.print_help()
        bombout('credentials not specified, but are required', pre='\n')

    if not args.id:
        if not args.company:
            while not args.domain:
                args.domain = intake('target domain? [example.com] > ')

        if not args.company:
            args.company = args.domain.split('.')[0]

    if args.domain:
        out('domain:\t%s' % (args.domain), '', pre='\n')
    if args.company:
        out('company:\t%s' % (args.company), '')
    if args.id:
        out('target id:\t%s' % (args.id), '', pre='\n')
    out('username:\t%s' % (args.username), '')
    if not args.demo:
        out('password:\t%s' % (args.password), '')
    if args.proxy:
        out('proxy:\t\t%s' % (args.proxy), '')

    if intake('\tlook good enough to continue? [Y/n] ', pre='\n').lower() not in {'', 'y', 'ye', 'yes', 'yeet', 'yarp', 'yolo'}:
        bombout('exiting')

    initialiseTokenli(args.username, args.password, args.proxy)

    if not args.id:
        args.id = searchCompaniesli(args.domain, args.company, args.proxy)

    getCompanyInfoli(args.id, args.company, args.output, args.force, args.proxy)

if __name__ == '__main__':
    system('clear')
    main()