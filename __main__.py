"""
Commandline access to tools for streamlining and
automating the use of git repos.

Probably a little redundant since git is a command
line thing anyway, but this can make life easier.
"""
import typing
from gitTools.branches import (
    createBranch,checkoutBranch,gitAbandonChanges,revertCommits,
    copyOverProjectDefaults)
from gitTools.commits import gitGrep
from gitTools.tagsAndVersions import (
    gitTagToCommit,changesBetweenVersionsUrl,getCurrentWorkingRelease,
    gitTags)


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    didSomething=False
    printHelp=False
    compileFlag:bool=False
    runFlag:bool=False
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            av[0]=av[0].lower()
            if av[0] in ('-h','--help'):
                printHelp=True
            elif av[0] in ('--createbranch','--create'):
                createBranch(av[1],compileFlag,runFlag)
                didSomething=True
            elif av[0] in ('--checkoutBranch','--checkout'):
                checkoutBranch(av[1],compileFlag,runFlag)
                didSomething=True
            elif av[0] in ('--compile'):
                compileFlag=len(av)==1 or av[1][0].lower() in ('t','1','y')
            elif av[0] in ('--run'):
                runFlag=len(av)==1 or av[1][0].lower() in ('t','1','y')
            elif av[0] in ('--gitlinehistory','--linehistory'):
                print(gitLineHistory(av[1]))
                didSomething=True
            elif av[0] in ('--revertcommits'):
                revertCommits(av[1].replace(',',' ').split())
                didSomething=True
            elif av[0] in ('--gitabandonchanges','--abandonchanges','--abandon'):
                gitAbandonChanges(".")
                didSomething=True
            elif av[0] in ('--checkoutbranch','--gitcheckoutbranch'):
                checkoutBranch(av[1])
                didSomething=True
            elif av[0] in ('--getcurrentworkingrelease',
                    '--gitcurrentworkingrelease',
                    '--currentworkingrelease',
                    '--workingrelease',
                    '--getcwr','--cwr'):
                print(getCurrentWorkingRelease("."))
                didSomething=True
            elif av[0] in ('--gittagtocommit','--tagtocommit','--tag2commit'):
                print(gitTagToCommit(av[1]))
                didSomething=True
            elif av[0] in ('--changesbetweenversionsurl',
                    '--changesbetweenversions'):
                params=av[1].replace(',',' ').split(maxsplit=1)
                print(changesBetweenVersionsUrl(*params))
                didSomething=True
            elif av[0] in ('--gittags','--tags'):
                for tag in (gitTags()):
                    print(tag)
                didSomething=True
            elif av[0] in ('--defaults','--copyoverprojectdefaults'):
                copyOverProjectDefaults(r'')
                didSomething=True
            elif av[0] in ('--grep','--gitgrep'):
                for result in gitGrep(av[1],"."):
                    for k,v in result.items():
                        flat=':'.join((k,str(v).replace('\n',' ')))
                        print(flat)
                    print('-'*20)
                didSomething=True
            else:
                printHelp=True
        else:
            printHelp=True
    if printHelp or not didSomething:
        print('USAGE:')
        print('  gitTools [options]')
        print('OPTIONS:')
        print('  -h ................................. this help')
        print('  --createBranch=feature/SWR-1234 .... create a new branch with the specified tag') # noqa: E501 # pylint: disable=line-too-long
        print('  --compile[=t/f] .................... auto-compile on checkout or create branch') # noqa: E501 # pylint: disable=line-too-long
        print('  --run[=t/f]  ....................... auto-run on checkout or create branch') # noqa: E501 # pylint: disable=line-too-long
        print('  --checkoutBranch=d6e81aa ........... check out a branch')
        print('  --gitLineHistory=file.c:123 ........ get the history for a particular line') # noqa: E501 # pylint: disable=line-too-long
        print('  --revertCommits=d6e81aa,34e81a, .... revert a series of commits') # noqa: E501 # pylint: disable=line-too-long
        print('  --gitAbandonChanges ................ abandon all current changes') # noqa: E501 # pylint: disable=line-too-long
        print('  --getCurrentWorkingRelease ......... current working release version') # noqa: E501 # pylint: disable=line-too-long
        print('  --gitTagToCommit=tag ............... get the latest commit id for a tag') # noqa: E501 # pylint: disable=line-too-long
        print('  --changesBetweenVersionsUrl=v1,v2 .. get a url that shows all changes between two versions') # noqa: E501 # pylint: disable=line-too-long
        print('  --gitTags .......................... list all git tags')
        print('  --grep ............................. search the log for something') # noqa: E501 # pylint: disable=line-too-long
        print('  --copyOverProjectDefaults .......... copy project default files over the current files') # noqa: E501 # pylint: disable=line-too-long
        return 1
    return 0


if __name__=='__main__':
    import sys
    cmdline(sys.argv[1:])
