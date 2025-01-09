"""
Recurse all directories, anything that has git
information is fetched.  Anything that has code, but no
git information is reported.
"""
import typing
from pathlib import Path
import subprocess


codeExtensions=(
    '.c','.h','.cpp','.hpp','.cxx','.hxx',
    '.py',
    '.java',
    '.js','.ts','.jsx','.tsx',
    '.cs',
    '.php')


def gitRecursive(
    startingLocation:typing.Union[str,Path]='.',
    fetch:bool=True
    )->typing.Dict[str,typing.List[str]]:
    """
    Recursively search for git information

    :fetch: if there is git, fetch latest

    :return: a report in the form {
        "fetched":[],
        "skip_fetch":[],
        "need_checkin":[],
        "no_git":[]}
    """
    fetched=[]
    skip_fetch=[]
    need_checkin=[]
    no_git=[]
    if not isinstance(startingLocation,Path):
        if startingLocation is None or not startingLocation:
            startingLocation='.'
        startingLocation=Path(startingLocation)
    startingLocation=startingLocation.absolute()
    def r(location:Path):
        if (location/'.git').is_dir():
            # this is a git project
            if fetch:
                # run git fetch
                cmd=['git','fetch']
                po=subprocess.Popen(cmd,cwd=str(location),
                    stderr=subprocess.PIPE)
                _,errB=po.communicate()
                errB=errB.strip()
                if errB:
                    print(f'ERR: fetching "{location}"')
                    print(errB.decode('utf-8',errors='ignore'))
                    skip_fetch.append(location)
                else:
                    fetched.append(location)
            else:
                skip_fetch.append(location)
            # check the git status to see if it needs checkin
            cmd=['git','status','-s']
            po=subprocess.Popen(cmd,cwd=str(location),
                stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            outB,errB=po.communicate()
            errB=errB.strip()
            if errB:
                print(f'ERR: checking git status for "{location}"')
                print(errB.decode('utf-8',errors='ignore'))
            else:
                outB=outB.strip()
                if outB:
                    print(f'Git files needing checkin "{location}"')
                    msg=outB.decode('utf-8',errors='ignore')
                    print('\t'+msg.replace('\n','\n\t'))
                need_checkin.append(location)
        else:
            nextDirs=[]
            isCodeProject=False
            for item in location.iterdir():
                print(f'$ {item}')
                if item.name[0]=='.':
                    continue
                elif item.is_dir():
                    nextDirs.append(item)
                elif item.suffix in codeExtensions:
                    isCodeProject=True
            if isCodeProject:
                no_git.append(location)
            else:
                for nextDir in nextDirs:
                    r(nextDir)
    r(startingLocation)
    return {
        "fetched":fetched,
        "skip_fetch":skip_fetch,
        "need_checkin":need_checkin,
        "no_git":no_git}


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    didSomething=False
    printHelp=False
    fetch=False
    def doIt(directory='.',fetch=False):
        results=gitRecursive(directory,fetch=fetch)
        for k,v in results.items():
            if k.find('fetch')>=0:
                if fetch:
                    print(k)
                    for vv in v:
                        print(f'\t{vv}')
            else:
                print(k)
                for vv in v:
                    print(f'\t{vv}')
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            av[0]=av[0].lower()
            if av[0] in ('-h','--help'):
                didSomething=True
                printHelp=True
            elif av[0]=='--fetch':
                fetch=True
            else:
                printHelp=True
        else:
            doIt(arg,fetch=fetch)
            didSomething=True
    if not didSomething:
        doIt(fetch=fetch)
        didSomething=True
    if printHelp or not didSomething:
        print('USAGE:')
        print('  gitRecursive [options] [directories]')
        print('OPTIONS:')
        print('  -h ................... this help')
        print('  --fetch ............... attempt to fetch all repos') # noqa: E501 # pylint: disable=line-too-long
        return 1
    return 0


if __name__=='__main__':
    import sys
    cmdline(sys.argv[1:])
