# datalink
an open source intelligence gathering tool

provide a target company, receive a complete list of employees

##  Usage

if you don't supply both a username AND password, an error and the usage prompt is displayed
```
$ ./datalink.py
usage: datalink.py [-h] [-i ID] [-d DOMAIN] [-c COMPANY] [-u USERNAME] [-p PASSWORD] [-o OUTPUT] [-m MANGLE] [-D] [-P PRUNE] [-f] [-v] [--demo] [--conf CONF]
                   [--proxy PROXY]

optional arguments:
  -h, --help            show this help message and exit
  -i ID, --id ID
  -d DOMAIN, --domain DOMAIN
  -c COMPANY, --company COMPANY
  -u USERNAME, --username USERNAME
  -p PASSWORD, --password PASSWORD
  -o OUTPUT, --output OUTPUT
  -m MANGLE, --mangle MANGLE
  -D, --download
  -P PRUNE, --prune PRUNE
  -f, --force
  -v, --version
  --demo
  --conf CONF
  --proxy PROXY

    ! credentials not specified, but are required !
```

Passing Credentials via Command Line
```
$ ./datalink.py -u bob@example.com -p password
target domain? [example.com] > 
```

Passing Credentials via a Configuration File 
```
$ ./datalink.py --conf .conf
target domain? [example.com] > 
````

Command Line Domain Lookup
```
$ ./datalink.py --conf .conf -d example.com
    
    domain:     example.com
    username:   caesar@example.com
    password:   DeployASockPuppet?

    look good enough to continue? [Y/n] 
```

Command Line Company Lookup
```
$ ./datalink.py --conf .conf -c IBM
    
    company:    IBM
    username:   caesar@example.com
    password:   DeployASockPuppet?

    look good enough to continue? [Y/n] 
```

Use Demo Mode to Supress the Display of the Password 
```
$ ./datalink.py --conf .conf --demo
target domain? [example.com] > ibm.com
    
    domain:     ibm.com
    username:   caesar@example.com

    look good enough to continue? [Y/n] 
```
