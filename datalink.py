#!/usr/bin/env python3

# datalink - an open source intelligence gathering tool
# made by caesarcipher
version = '20260104'

from re import match, search
from os import path, getenv, getcwd
from sys import argv
from math import ceil
from lxml import html
from json import loads
from urllib3 import util
from datetime import date
from argparse import ArgumentParser
from requests import get, post, Session
from urllib.parse import quote

linkedin = None

# POST-PROCESSING -----------------
def pruneInput(inFile, outFile=None):
    try:
        f = open(inFile)
    except IOError as err:
        bombout(f'error opening file - {err}')

    if not outFile:
        outFile = 'pruned_%s' % (inFile)

    filters = [ r',.*', r'\.', r'\b\w\s' ]

    input = f.read().splitlines()

    prunedOut = ''

    for line in input:
        for filter in filters:
            r = search(filter, line)
            if r:
                #out(line)
                line = line[:r.start()]+line[r.end():]
                #out(line, post='\n')
        prunedOut += f'{line}\n'

    out(prunedOut)
    writeFile(prunedOut, outFile)
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

    mangled = ''

    for rule in mangleRules:
        out(rule)

    bombout(punc='')

    for line in input:
        for rule in mangleRules:
            r = search(rule, line)
            if r:
                line = line[:r.start()]+line[r.end():]
        mangled += f'{line}\n'

    #out(mangled)
    #writeFile(mangled, outFile)
    #bombout(f'mangled results written to {outFile}')
# POST-PROCESSING -----------------

def intake(msg, pre=None):
    message = msg

    try:
        if pre:
            message = f'{pre}{msg}'
        response = input(message)
    except (KeyboardInterrupt, EOFError):
        bombout(punc='')

    return response

def bombout(msg='', punc=' !', pre='', post=''):
    out(msg, punc, pre, post, do_exit=True)

def out(msg='', punc='', pre='', post='', do_exit=False):
    output = ''

    # Handle string vs iterable
    messages = [msg] if isinstance(msg, str) else msg

    for line in messages:
        if len(punc) > 1:
            output += f'{punc[::-1]}{line}{punc}'
        else:
            output += f'{punc}{line}{punc}'

    result = f'{pre}{output}{post}'

    if do_exit:
        exit(f'{result}\n')
    print(result)

def _post(token, target, data, proxy):
    if proxy:
        return token.post(target, allow_redirects=False, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, proxies=proxy, verify=False)
    return token.post(target, allow_redirects=False, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})

def _get(token, target, proxy):
    if proxy:
        return token.get(target, proxies=proxy, verify=False)
    return token.get(target)

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
        from urllib3 import disable_warnings, util
        disable_warnings()

        prox = config.get('linkedin.com', 'proxy')
        args.proxy = { 'http': prox, 'https': prox }

def writeFile(output, fileName = 'output.txt'):
    try:
        f = open(fileName, 'w')
    except (TypeError, IOError) as err:
        bombout(f'error writing output file "{fileName}" - {err}')

    f.write(output)
    f.close()

def initializeTokenLI(username, password, proxy):
    global linkedin
    linkedin = Session()
    linkedin.headers.update({'User-Agent': util.SKIP_HEADER})

    quser = quote(username)
    qpass = quote(password)

    loginPageRequest = _get(linkedin, 'https://www.linkedin.com/login', proxy)

    csrf = match(r'"(ajax:[\d]+)', loginPageRequest.cookies['JSESSIONID']).group(1)
    linkedin.headers.update({'Csrf-Token': csrf})

    loginCsrf = match('"v=2&([^"]+)', loginPageRequest.cookies['bcookie']).group(1)
    data = 'session_key={}&session_password={}&loginCsrfParam={}'.format(quser, qpass, loginCsrf)

    resp = _post(linkedin, 'https://www.linkedin.com/login-submit', data, proxy)

    redir = resp.headers.get('Location')

    # TODO automatically bypass checkpoint errors
    if redir and 'feed' not in redir:
        bombout(f'checkpoint violation? Location: "{redir}"', punc='?!')

def searchCompaniesLI(domain, company, proxy):
    choice = list()

    target = 'https://www.linkedin.com/voyager/api/graphql?variables=(query:%s)&queryId=voyagerSearchDashTypeahead.e2aad44974edcf1ef5db22e743e8f838' % (domain if domain else company)
    typeaheadSearchResults = _get(linkedin, target, proxy)
    
    resultBlobJSON = loads(typeaheadSearchResults.text)
    # out(f'bing bong {resultBlobJSON['data']['searchDashTypeaheadByGlobalTypeahead']['elements']}')
    # out(f'bing bong {resultBlobJSON}')

    try:
        elements = resultBlobJSON['data']['searchDashTypeaheadByGlobalTypeahead']['elements']
    except KeyError as err:
        bombout(f'KeyError {err} - {resultBlobJSON}', pre='\n')

    if not len(elements):
        bombout('query returned no results. if a protocol change has broken the search feature, directly providing a target ID may still succeed')

    for result in elements:
        if not result['entityLockupView']['trackingUrn'] or 'organizationalPage' in result['entityLockupView']['trackingUrn'] or 'member' in result['entityLockupView']['trackingUrn']:
            continue

        try:
            companyId = match('urn:li:company:([0-9]+)', result['entityLockupView']['trackingUrn']).group(1)
        except AttributeError as err:
            out('failed id lookup')
            out(str(result['entityLockupView']), punc=' ?', post='\n')
            out(f'AttributeError - bad id ({err})')
            continue

        try:
            companyRealm = search(r'(?:• [^ ]+ )?• \(?([^\)]+)', result['entityLockupView']['subtitle']['text']).group(1)
        except AttributeError as err:
            out('failed realm lookup')
            out(result['entityLockupView']['subtitle']['text'], punc='~', post='\n')
            out(f'AttributeError - bad realm ({err})')
            continue

        try:
            companyName = result['entityLockupView']['title']['text']
        except KeyError as err:
            out('failed company lookup')
            out(result, punc=' ?', post='\n')
            out(f'KeyError - bad name ({err})')
            continue

        try:
            out('{}{:^16}\033[96m{}\033[00m\t(\033[90m{}\033[00m)'.format(len(choice)+1, companyId, companyName, companyRealm), post='')
            choice.append(companyId)
        except AttributeError as err:
            out(f'AttributeError - {err}')

    out('{}{:^16}{}'.format(0, '[EXIT]', '- none of the above -'), post='\n')

    selection = ''
    while not selection:
        selection = intake('which target to scrape? > ')
        if selection == '0':
            bombout('exiting', pre='\n')

    try:
        choice = choice[int(selection)-1]
    except IndexError as err:
        bombout(f'IndexError: {err}')
    
    out(f'    okay, targeting cmopany with id {choice}', pre='\n', post='\n')

    return choice

def getContactsLI(outfile=None, proxy=None):
    output = list()
    target = 'https://www.linkedin.com/search/results/people/?network="F"'

    resp = _get(linkedin, target, proxy)
    page = html.document_fromstring(resp.content)

    contactblob = loads(page.xpath('//text()[contains(., "totalResultCount")]')[0].strip())

    numConnections = contactblob['data']['data']['searchDashClustersByAll']['metadata']['totalResultCount']
    numPages = ceil(numConnections/10)

    out(f'downloading {numConnections} contacts from {numPages} pages', pre='\n', post='\n')

    try:
        for contact in contactblob['included']:
            con = contact.get('title')
            
            if con:
                name = con['text'] 
                #title = contact['headline']['text']
                #location = contact['subline']['text']
                #out('{:28}{:32}{}'.format(name, location, title))
                #output.append([name, location, title])
                out('{:28}'.format(name))
                output.append([name])
                #out(f'"{contact}"')

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
                    #out('{:28}{:32}{}'.format(name, location, title))
                    #output.append([name, location, title])
                    out('{:28}'.format(name))
                    output.append([name])
                    #out(f'"{contact}"')
    except (KeyboardInterrupt):
        bombout(punc='')

    names = raw = ''
    for entry in output:
        #raw += f'{entry[0]},{entry[1]},{entry[2]}\n'
        names += f'{entry[0]}\n'

    if not outfile:
        outfile = 'contacts.txt'

    writeFile(names, outfile)
    writeFile(raw, f'raw_{outfile}')

    lines = names.split("\n")

    out(f'wrote {len(lines)-1} results to {outfile}', pre='\n')

def getCompanyInfoLI(id, company, outfile=None, proxy=None):
    output = list()
    companypage = f'https://www.linkedin.com/search/results/people/?facetCurrentCompany={id}'

    pages = 1
    while True:
        target = f'{companypage}&page={pages}'
        startlen = len(output)

        resp = _get(linkedin, target, proxy)
        page = html.document_fromstring(resp.content)
        resultblob = page.xpath('//a/div/div[1]/div[1]/p/a[1] | //a/div/div[1]/div[1]/div/p')

        try:
            while resultblob:
                name = resultblob.pop(0).text_content().strip()
                location = resultblob.pop(0).text_content().strip()
                title = resultblob.pop(0).text_content().strip()

                if 'LinkedIn Member' in name:
                    out(f'{name} {title} {location}', punc='!?')
                    continue

                output.append([name, location, title])
                # out('{:28}{:32}{}'.format(name, location, title))
                out(name)
        except (KeyboardInterrupt):
            bombout(punc='')

        # for entry in output:
        #     raw += f'{entry[0]},{entry[1]},{entry[2]}\n'
        #     out('{:28}{:32}{}'.format(entry[0],entry[1],entry[2]))
        #     out(f'{entry[0]}')

        numresults = len(output) - startlen
        if not numresults:
            out(f'collected {len(output)} names over {pages-1} pages', punc=' -', pre='\n')
            break
        pages += 1

    thedate = date.today().strftime('%Y%m%d')

    if outfile:
        fileout = outfile
        rawout = f'raw_{fileout}'
    elif company:
        fileout = f'{company}_linkedin_{thedate}'
        rawout = f'raw_{fileout}.tsv'
    else:
        fileout = f'{id}_linkedin_{thedate}'
        rawout = f'raw_{fileout}.tsv'

    writeFile('\n'.join(entry[0] for entry in output), fileout)
    writeFile('NAME\tTITLE\tLOCATION\n' + '\n'.join('\t'.join(entry) for entry in output), rawout)

    out(f'results written to {fileout}.txt and {rawout}', punc=' -', post='\n')

def main():
    parser = ArgumentParser()

    # General options
    parser.add_argument('-v', '--version', action='store_true', help='current version')

    # Authentication
    auth_group = parser.add_argument_group('authentication')
    auth_group.add_argument('-u', '--username', help='account username', metavar='USER')
    auth_group.add_argument('-p', '--password', help='account password', metavar='PASS')
    auth_group.add_argument('-C', '--conf', help='configuration file', metavar='FILE')

    # Operation modes
    mode_group = parser.add_argument_group('operation modes')
    mode_group.add_argument('-D', '--download', action='store_true', help='download list of first degree user connections (excludes target options)')
    #mode_group.add_argument('-P', '--prune', help='normalize input list into typical \'first last\' format', metavar='NAME')
    #mode_group.add_argument('-M', '--mangle', help='convert input list of names into common corporate formats (implies --prune)', metavar='NAME')

    # Target options
    target_group = parser.add_argument_group('target options')
    target_group.add_argument('-i', '--id', help='numeric id of target', metavar='ID')
    target_group.add_argument('-d', '--domain', help='domain of target (example.org)', metavar='DOMAIN')
    target_group.add_argument('-c', '--company', help='company name of target (Example Corp)', metavar='COMPANY')

    # Output options
    output_group = parser.add_argument_group('output options')
    output_group.add_argument('-o', '--outfile', help='output file (default: output.txt)', metavar='FILE')

    # Network options
    network_group = parser.add_argument_group('network options')
    network_group.add_argument('-X', '--proxy', help='proxy for connections', metavar='URL')
 
    args = parser.parse_args()

    if args.version:
        bombout(f'version {version}', punc='')

    #if args.mangle:
        # need to prune before mangling but code isn't setup for it atm
        #pruneInput(args.mangle, args.outfile)
    #    mangle(args.mangle, args.outfile)

    #if args.prune:
    #    pruneInput(args.prune, args.outfile)

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
        out()
        if args.domain:
            out(f'domain: \t{args.domain}')
        if args.company:
            out(f'company:\t{args.company}')
        if args.id:
            out(f'target id:\t{args.id}')
    else:
        out('Downloading account contacts', pre='\n', post='\n')
    
    out(f'username:\t{args.username}')
    out(f'password:\t{"*" * len(args.password)}')
    if args.proxy:
        out(f'proxy:\t{args.proxy["http"]}')
    out('')

    # TODO reimplement this limiter
    # if intake('look good enough to continue? [Y/n] ', pre='    ').lower() not in {'', 'y', 'yes', 'yolo'}:
    #     bombout('exiting', pre='\n')
    # else:
    #     out('')

    initializeTokenLI(args.username, args.password, args.proxy)

    if args.download:
        getContactsLI(args.outfile, args.proxy)
    else:
        if not args.id:
            args.id = searchCompaniesLI(args.domain, args.company, args.proxy)

        getCompanyInfoLI(args.id, args.company, args.outfile, args.proxy)

if __name__ == '__main__':
    main()
