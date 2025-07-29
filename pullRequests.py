"""
Tools for managing pull requests
"""
import typing
from pathlib import Path
from paths import UrlCompatible,asUrl,asPathlibPath
from k_runner.osrun import osrun
from k_runner import ApplicationCallbacks
from gitTools.branches import sanitizeBranchName,branchHyperlink


def createPRBranch(
    upstreamBranchLocation:typing.Union[str,Path,UrlCompatible],
    branchName:str,
    printCb:typing.Optional[typing.Callable[[str],None]]=None
    )->None:
    """
    Creates a new branch on upstream, off upstream/master
    the purpose of this branch is to push incremental PR's to for easier review
    """
    if printCb is None:
        printCb=print
    upstreamBranchLocation=str(asPathlibPath(upstreamBranchLocation))
    branchName=sanitizeBranchName(branchName)
    printCb('Creating branch...')
    result=osrun(['git','checkout','-b',branchName],
        workingDirectory=upstreamBranchLocation,
        runCallbacks=ApplicationCallbacks(
            stderrLineCallbacks=printCb))
    if not result.succeeded:
        err=result.err.strip()
        if err.startswith("Switched to a new branch "):
            # Don't know why this acts like an error message, since
            # it's what we were trying to do. Thanks, git.
            pass
        else:
            raise Exception(err)
    printCb('Pushing branch...')
    result=osrun(['git','push','origin',branchName],
        workingDirectory=upstreamBranchLocation,
        runCallbacks=ApplicationCallbacks(
            stderrLineCallbacks=printCb))
    err=result.err.strip()
    hasUnexpectedErrLine=False
    if not result.succeeded:
        for line in err.split('\n'):
            line=line.strip()
            if not line:
                continue
            if line.startswith('remote:'):
                remoteMessage=line.split(':',1)[0].lstrip()
                if not remoteMessage:
                    continue
                if not remoteMessage.startswith('Create a pull request'):
                    continue
                if not remoteMessage.startswith('https://'):
                    continue
            if not line.startswith('To https://'):
                continue
            if not line.startswith('* '):
                continue
            hasUnexpectedErrLine=True
            break
    if hasUnexpectedErrLine:
        raise Exception(err)
    printCb('DONE')


def prHyperlink(repoUrl:UrlCompatible,prNum:typing.Union[int,str])->str:
    """
    Get an <a href=> html tag for a PR number in a given repo
    """
    return f'<a href="{asUrl(repoUrl)}/pull/{prNum}" target="_blank">{prNum}</a>' # noqa: E501 # pylint: disable=line-too-long


def getPRs(
    localRepoPath:typing.Union[None,str,Path,UrlCompatible]=None,
    author:typing.Optional[str]=None,
    limit:int=30,
    state:str='open',
    baseBranch:typing.Optional[str]=None):
    """
    Gets a list of pull requests for a project based upon some filters
    (as a Pandas dataframe)

    :localRepoPath: the directory where the repo you want to inspect is at
        if None, use current directory
    :author: can be '@me' or a name - default=None
    :limit: max number of values to return - default=30
    :state: "open","closed","merged","all" - default="open"
    :baseBranch: branch that the PR is coming from

    NOTE: this depends on the "gh" commandline github access tool
    """
    import pandas as pd # type: ignore
    import subprocess
    import io
    if localRepoPath is None:
        localRepoPath='.'
    localRepoPath=asPathlibPath(localRepoPath)
    cmd=['gh','pr','list']
    if author is not None:
        cmd.append('-A')
        cmd.append(author)
    if limit is not None:
        cmd.append('-L')
        cmd.append(str(limit))
    if state is not None:
        cmd.append('-s')
        cmd.append(state)
    if baseBranch is not None:
        cmd.append('-B')
        cmd.append(baseBranch)
    po=subprocess.Popen(cmd,cwd=str(localRepoPath),
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    out,_=po.communicate()
    data=out.decode('utf8',errors='ignore').replace('\r','').split('\n')
    data.insert(0,"PR\tTitle\tFrom Branch\tState\tTimestamp")
    df=pd.read_csv(io.StringIO('\n'.join(data)),delimiter="\t")
    df['From Branch']=df['From Branch'].apply(branchHyperlink)
    df['PR']=df['PR'].apply(prHyperlink)
    return df


def updatePRBranch(
    upstreamBranchLocation:typing.Union[str,Path,UrlCompatible],
    branchName:str,
    printCb:typing.Optional[typing.Callable[[str],None]]=None
    )->None:
    """
    Updates a PR branch as created by createPRBranch
    """
    if printCb is None:
        printCb=print
    upstreamBranchLocation=str(asPathlibPath(upstreamBranchLocation))
    branchName=sanitizeBranchName(branchName)
    # sometimes the following is required and I'm not sure why
    if True:
        printCb('Checking out master...')
        result=osrun(['git','checkout','master'],
            workingDirectory=upstreamBranchLocation,
            runCallbacks=ApplicationCallbacks(
                stdouterrLineCallbacks=printCb))
        if not result.succeeded:
            raise Exception(result.err)
        printCb('Pulling master...')
        result=osrun(['git','pull'],
            workingDirectory=upstreamBranchLocation,
            runCallbacks=ApplicationCallbacks(
                stdouterrLineCallbacks=printCb))
        if not result.succeeded:
            raise Exception(result.err)
    printCb('Pulling latest...')
    result=osrun(['git','pull','origin',branchName],
            workingDirectory=upstreamBranchLocation,
            runCallbacks=ApplicationCallbacks(
                stdouterrLineCallbacks=printCb))
    if not result.succeeded:
        raise Exception(result.err)
    printCb('Checking out branch...')
    result=osrun(['git','checkout',branchName],
            workingDirectory=upstreamBranchLocation,
            runCallbacks=ApplicationCallbacks(
                stdouterrLineCallbacks=printCb))
    if not result.succeeded:
        raise Exception(result.err)
    printCb('Merging changes from master...')
    result=osrun(['git','merge','master'],
            workingDirectory=upstreamBranchLocation,
            runCallbacks=ApplicationCallbacks(
                stdouterrLineCallbacks=printCb))
    if not result.succeeded:
        raise Exception(result.err)
    printCb('Pushing latest changes to remote branch...')
    result=osrun(['git','push','-u','origin',branchName],
            workingDirectory=upstreamBranchLocation,
            runCallbacks=ApplicationCallbacks(
                stdouterrLineCallbacks=printCb))
    if not result.succeeded:
        raise Exception(result.err)
    printCb('DONE')


def checkoutPR(
    prNumber:typing.Union[str,int],
    repo:typing.Optional[str]=None,
    directory:typing.Union[None,Path,str]=None,
    branchName:typing.Optional[str]=None):
    """
    Check out a particular pull request

    :prNumber: Which pr to check out
        can also be a url such as https://github.com/username/REPO/pull/314
    :repo: name of the repo to check out.  If missing, derive it from
        the checkout directory.
    :directory: name of the directory we will be working with. Defaults to
        the current directory. If directory does not exist will clone the
        given repo to create it.
    :branchName: optionally, go for a particular branch
    """
    if directory is None:
        directory=Path('.')
    elif not isinstance(directory,Path):
        directory=asPathlibPath(directory)
    if not isinstance(prNumber,int):
        if prNumber.startswith('http'):
            parts=prNumber.rsplit('/pull/',1)
            if repo is None:
                repo=parts[0]
            prNumber=int(parts[1])
        else:
            prNumber=int(prNumber)
    if not directory.is_dir():
        # attempt to clone
        if repo is None or directory.exists():
            raise FileNotFoundError(f'ERR: no repo at "{directory}"')
        cmd=['git','clone',str(repo),str(directory)]
        result=osrun(cmd)
        print(result.outerr)
    # make sure we are on master
    cmd=['git','checkout','master']
    result=osrun(cmd)
    print(result.outerr)
    # fetch the PR and create a new branch
    cmd=['git','fetch','origin',f'pull/{prNumber}/head:{branchName}']
    result=osrun(cmd)
    print(result.outerr)
    #switch to that branch to review or test the changes locally.
    cmd=['git','checkout',branchName]
    result=osrun(cmd)
    print(result.outerr)


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    didSomething=False
    printHelp=False
    branch=None
    repo=None
    directory='.'
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            av[0]=av[0].lower()
            if av[0] in ('-h','--help'):
                printHelp=True
            elif av[0] in ('--checkoutpr','--checkout'):
                checkoutPR(av[1],repo,directory,branch)
                didSomething=True
            elif av[0] in ('--ls','--list'):
                for pr in getPRs(directory,limit=200):
                    print(pr)
            elif av[0] in ('--branch'):
                branch=av[1]
            elif av[0] in ('--repo','--repository'):
                repo=av[1]
            elif av[0] in ('--dir','--directory'):
                directory=av[1]
            else:
                printHelp=True
        else:
            printHelp=True
    if printHelp or not didSomething:
        print('USAGE:')
        print('  pullRequests [options]')
        print('OPTIONS:')
        print('  -h ................ ............ this help')
        print('  --checkout=pr_num .............. check out a pull request')
        print('  --ls ........................... list open PRs')
        print('  --branch=branch_name ........... select a particular branch')
        print('  --repo=repo_name ............... select a particular repository') # noqa: E501 # pylint: disable=line-too-long
        print('  --dir=local_directory .......... select a particular directory') # noqa: E501 # pylint: disable=line-too-long
        return 1
    return 0


if __name__=='__main__':
    import sys
    cmdline(sys.argv[1:])
