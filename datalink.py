#!/usr/bin/env python3

# datalink - an open source intelligence gathering tool
# from caesarcipher, inspired by linkScrape
version = '20221016'

from re import match, search
from os import path, getenv, getcwd
from sys import argv
from math import ceil
from lxml import html
from json import loads
from argparse import ArgumentParser
from requests import get, post, Session
from urllib.parse import quote

from urllib3 import disable_warnings
disable_warnings()

linkedin = None

def intake(msg, pre=None):
    try:
        if pre:
            response = input(f'{pre}{msg}')
        else:
            response = input(msg)
    except (KeyboardInterrupt, EOFError):
        bombout(punc='')
    return response

def out(msg='', punc=' !', pre='', post=''):
    out = ""
    if isinstance(msg, str):
        if len(punc) > 1:
            out += '    {0}{1}{2}'.format(punc[::-1], msg, punc)
        else:
            out += '    {0}{1}{0}'.format(punc, msg)
    else:
        for line in msg:
            if len(punc) > 1:
                out += '    {0}{1}{2}'.format(punc[::-1], line, punc)
            else:
                out += '    {0}{1}{0}'.format(punc, line)
    print(f'{pre}{out}{post}')

def bombout(msg='', punc=' !', pre='', post=''):
    out = ""
    if isinstance(msg, str):
        if len(punc) > 1:
            out += '    {0}{1}{2}'.format(punc[::-1], msg, punc)
        else:
            out += '    {0}{1}{0}'.format(punc, msg)
    else:
        for line in msg:
            if len(punc) > 1:
                out += '    {0}{1}{2}'.format(punc[::-1], line, punc)
            else:
                out += '    {0}{1}{0}'.format(punc, line)
    exit('{}{}{}\n'.format(pre, out, post))

def _get(token, target, proxy):
    if proxy:
        return token.get(target, proxies=proxy, verify=False)
    return token.get(target)

def _post(token, target, data, proxy):
    if proxy:
        return token.post(target, allow_redirects=False, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, proxies=proxy, verify=False)
    return token.post(target, allow_redirects=False, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})

def pruneInput(inFile, outFile=None):
    try:
        f = open(inFile)
    except IOError as err:
        bombout(f'error opening file - {err}')

    if not outFile:
        outFile = 'pruned_%s' % (inFile)

    filters = [ r',.*', r'\.', r'\b\w\s' ]

    input = f.read().splitlines()

    prunedOut = ""

    for line in input:
        for filter in filters:
            r = search(filter, line)
            if r:
                #out(line)
                line = line[:r.start()]+line[r.end():]
                #out(line, post='\n')
        prunedOut += f'{line}\n'

    out(prunedOut, punc='')
    writeResults(prunedOut, outFile)
    bombout(f'pruned results written to {outFile}')

def mangle(inFile, outFile=None):
    try:
        f = open(inFile)
    except IOError as err:
        bombout(f'error opening file - {err}')

    if not outFile:
        outFile = f'mangled_{inFile}'

    input = f.read().splitlines()

    mangleRules = [
    # name mangling formats lifted from linkScrape
    '^([^ ]+) ([^ ]+)$',   # 1)FirstLast
    # 2)LastFirst      
    # 3)First.Last
    # 4)Last.First
    # 5)First_Last
    # 6)Last_First
    '^(.)[^ ]+ ([^ ]+)$',   # 7)FLast
    # 8)LFirst
    '^([^ ]+) (.)',         # 9)FirstL
    # 10)F.Last
    # 11)L.Firstname
    '^(.{3})[^ ]+ (.{2})',  # 12)FirLa
    # 13)Lastfir
    '^([^ ]+) (.{7})'        # 14)FirstLastnam
    # 15)LastF
    # 16)LasFi
    ]

    mangled = ""

    for rule in mangleRules:
        out(rule, punc='')

    bombout(punc='')

    for line in input:
        for rule in mangleRules:
            r = search(filter, line)
            if r:
                line = line[:r.start()]+line[r.end():]
        mangled += f'{line}\n'

    #out(mangled, punc='')
    #writeResults(mangled, outFile)
    #bombout(f'mangled results written to {outFile}')

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
    except (TypeError, IOError) as err:
        bombout(f'error writing output file "{fileName}" - {err}')

    f.write(output)
    f.close()

def initializeTokenli(username, password, proxy):
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

    #resp = linkedin.post('https://www.linkedin.com/login-submit', allow_redirects=False, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})#, proxies=proxies, verify=False)
    resp = _post(linkedin, 'https://www.linkedin.com/login-submit', data, proxy)

    redir = resp.headers.get('Location')

    # TODO automatically bypass checkpoint errors
    if redir and 'feed' not in redir:
        bombout(f'checkpoint violation? Location: "{redir}"', punc='?!')

def searchCompaniesli(domain, company, proxy):
    choice = list()

    target = 'https://www.linkedin.com/voyager/api/typeahead/hitsV2?keywords=%s&original=GLOBAL_SEARCH_HEADER&q=blended' % (domain if domain else company)

    typeaheadSearchResults = _get(linkedin, target, proxy)
    
    resultBlobJSON = loads(typeaheadSearchResults.text)

    try:
        elements = resultBlobJSON['elements']
    except KeyError as err:
        bombout(f'KeyError {err} - {resultBlobJSON}')

    for result in elements:
        # TODO review the following line for potential improvements
        if 'keywords' in result or 'Event' in result['subtext']['text'] or 'GHOST' in result['image']['attributes'][0]['sourceType'] or 'GROUP' in result['image']['attributes'][0]['sourceType']:
            continue

        #out(f'yipyip {result}', pre='\n', post='\n')

        try:
            companyId = match('urn:li:company:([0-9]+)', result['objectUrn']).group(1)
        except AttributeError as err:
            out(result['objectUrn'], punc='?', post='\n')
            out(f'AttributeError - bad id ({err})', punc='')
            continue

        try:
            companyRealm = search(r'(?:• [^ ]+ )?• \(?([^\)]+)', result['subtext']['text']).group(1)
        except AttributeError as err:
            out(result['subtext']['text'], punc='~', post='\n')
            out(f'AttributeError - bad realm ({err})', punc='')
            continue

        try:
            companyName = result['image']['attributes'][0]['miniCompany']['name']
        except KeyError as err:
            out(result, punc='?', post='\n')
            out(f'KeyError - bad name ({err})', punc='')
            continue

        try:
            out('{}{:^16}\033[96m{}\033[00m   (\033[90m{}\033[00m)'.format(len(choice)+1, companyId, companyName, companyRealm), punc='', post='')
            choice.append(companyId)
        except AttributeError as err:
            out(f'AttributeError - {err}')

    out('{}{:^16}{}'.format(0, '[EXIT]', '-none of the above-'), punc='', post='\n')

    selection = ''
    while not selection:
        selection = intake('which target to scrape? > ')
        if selection == '0':
            bombout('exiting')

    try:
        choice = choice[int(selection)-1]
    except IndexError as err:
        bombout(f'IndexError: {err}')
    
    out(f'okay, targeting {choice}', pre='\n', post='\n')

    return choice

def getContactsli(outfile=None, proxy=None):
    output = list()
    target = 'https://www.linkedin.com/search/results/people/?network="F"'

    resp = _get(linkedin, target, proxy)

    page = html.document_fromstring(resp.content)
    contactblob = loads(page.xpath('//text()[contains(., "totalResultCount")]')[0].strip())

    numConnections = int(contactblob['data']['metadata']['totalResultCount'])
    numPages = ceil(numConnections/10)

    out(f'downloading {numConnections} contacts from {numPages} pages', pre='\n', post='\n')

    try:
        for contact in contactblob['included']:
            con = contact.get('title')
            
            if con:
                name = con['text'] 
                #title = contact['headline']['text']
                #location = contact['subline']['text']
                #out('{:28}{:32}{}'.format(name, location, title), punc='')
                #output.append([name, location, title])
                out('{:28}'.format(name), punc='')
                output.append([name])
                #out(f'"{contact}"', punc='')

        for pageCount in range(2, numPages+1):
            subtarget = f'{target}&page={pageCount}' 

            resp = _get(linkedin, subtarget, proxy)

            page = html.document_fromstring(resp.content)
            contactblob = loads(page.xpath('//text()[contains(., "totalResultCount")]')[0].strip())

            for contact in contactblob['included']:
                con = contact.get('title')
                
                if con:
                    name = con['text'] 
                    #title = contact['headline']['text']
                    #location = contact['subline']['text']
                    #out('{:28}{:32}{}'.format(name, location, title), punc='')
                    #output.append([name, location, title])
                    out('{:28}'.format(name), punc='')
                    output.append([name])
                    #out(f'"{contact}"', punc='')
    except (KeyboardInterrupt):
        bombout(punc='')

    names = raw = ''
    for entry in output:
        #raw += f'{entry[0]},{entry[1]},{entry[2]}\n'
        names += f'{entry[0]}\n'

    if not outfile:
        outfile = 'contacts.txt'

    writeResults(names, outfile)
    #writeResults(raw, f'raw_{outfile}')

    lines = names.split("\n")

    out(f'wrote {len(lines)-1} results to {outfile}', pre='\n')

def getCompanyInfoli(id, company, outfile=None, force=None, proxy=None):
    output = list()
    target = f'https://www.linkedin.com/search/results/people/?facetCurrentCompany={id}'

    resp = _get(linkedin, target, proxy)

    page = html.document_fromstring(resp.content)

    employeeblob = loads(page.xpath('//text()[contains(., "totalResultCount")]')[0].strip())

    numEmployees = int(employeeblob['data']['metadata']['totalResultCount'])
    numPages = ceil(numEmployees/10)

    out(f'target has {numEmployees} visible employees across {numPages} pages of results', pre='\n')

    if numEmployees > 1000:
        if not force:
            out('target has too many results for a free account, stopping at 100th page')
            numPages = 100
        else:
            out(f'user has chosen to enumerate all {numPages} target pages')

    out(punc='')

    try:
        for employee in employeeblob['included']:
            emp = employee.get('title')
            
            if emp:
                name = emp['text'] 
                #title = employee['headline']['text']
                #location = employee['subline']['text']
                #out('{:28}{:32}{}'.format(name, location, title), punc='')
                #output.append([name, location, title])
                out('{:28}'.format(name), punc='')
                output.append([name])

        for pageCount in range(2, numPages+1):
            subtarget = f'{target}&page={pageCount}' 

            resp = _get(linkedin, subtarget, proxy)

            page = html.document_fromstring(resp.content)
            employeeblob = loads(page.xpath('//text()[contains(., "totalResultCount")]')[-1].strip())

            for employee in employeeblob['included']:
                emp = employee.get('title')

                if emp:
                    name = emp['text']
                    #try:
                    #    title = employee['headline']['text']
                    #except KeyError as err:
                    #    out(f'oops {err}')
                    #location = employee['subline']['text']
                    #out('{:28}{:32}{}'.format(name, location, title), punc='')
                    #output.append([name, location, title])
                    out('{:28}'.format(name), punc='')
                    output.append([name])
    except (KeyboardInterrupt):
        bombout(punc='')

    names = raw = ''
    for entry in output:
        #raw += f'{entry[0]},{entry[1]},{entry[2]}\n'
        names += f'{entry[0]}\n'

    # TODO probably ought to add timestamps
    if outfile:
        fileout = outfile
    elif company:
        fileout = f'{company}.txt'
    else:
        fileout = f'{id}.txt'

    writeResults(names, fileout)
    #writeResults(raw, f'raw_{fileout}')

    lines = names.split("\n")

    out(f'wrote {len(lines)-1} results to {fileout}', pre='\n')

def main():
    parser = ArgumentParser()
    parser.add_argument('-i', '--id', help='numeric id of target', metavar='\b')
    parser.add_argument('-d', '--domain', help='domain of target (example.org)', metavar='\b')
    parser.add_argument('-c', '--company', help='company name of target (Example Corp)', metavar='\b')
    parser.add_argument('-u', '--username', metavar='\b')
    parser.add_argument('-p', '--password', metavar='\b')
    parser.add_argument('-o', '--output', help='output file (default: output.txt)', metavar='\b')
    parser.add_argument('-v', '--version', action='store_true', help='current version')
    parser.add_argument('-C', '--conf', help='configuration file', metavar='\b')
    parser.add_argument('-D', '--download', action='store_true', help='download list of first degree user connections of account')
    parser.add_argument('-F', '--force', action='store_true', help='force download list of users beyond upper limit (if using a paid account)')
    parser.add_argument('-H', '--hide', '--demo', action='store_true', help='hide password in output')
    parser.add_argument('-P', '--prune', help='normalize input list into typical \'first last\' format', metavar='\b')
    parser.add_argument('-M', '--mangle', help='convert input list of names into common corporate formats (implies --prune)', metavar='\b')
    parser.add_argument('-X', '--proxy', help='proxy for connections (NOT OPSEC safe. session init cxn ignores proxy)', metavar='\b')
 
    args = parser.parse_args()

    if args.version:
        bombout(f'version {version}', punc='')

    if args.mangle:
        # need to prune before mangling but code isn't setup for it atm
        #pruneInput(args.mangle, args.output)
        mangle(args.mangle, args.output)

    if args.prune:
        pruneInput(args.prune, args.output)

    if args.conf:
       configure(args, args.conf)

    # TODO better dynamic cred intake
    if not (args.username and args.password):
        parser.print_help()
        bombout('credentials not specified, but are required', pre='\n')

    if not args.id and not args.download:
        if not args.company:
            while not args.domain:
                args.domain = intake('target domain? [example.com] > ')
            #args.company = args.domain.split('.')[0]

    if not args.download:
        out(punc='')
        if args.domain:
            out(f'domain: \t{args.domain}', '')
        if args.company:
            out(f'company:\t{args.company}', '')
        if args.id:
            out(f'target id:\t{args.id}', '')
    else:
        out('Downloading account contacts', pre='\n', post='\n')
    out(f'username:\t{args.username}', '')
    if not args.hide:
        out(f'password:\t{args.password}', '')
    if args.proxy:
        out(f'proxy:\t{args.proxy["http"]}', '')

    if intake('look good enough to continue? [Y/n] ', pre='\n    ').lower() not in {'', 'y', 'ye', 'yes', 'yeet', 'yarp', 'yolo'}:
        bombout('exiting')

    initializeTokenli(args.username, args.password, args.proxy)

    if args.download:
        getContactsli(args.output, args.proxy)
    else:
        if not args.id:
            args.id = searchCompaniesli(args.domain, args.company, args.proxy)

        getCompanyInfoli(args.id, args.company, args.output, args.force, args.proxy)

if __name__ == '__main__':
    main()
