"""
Tools for managing pull requests
"""
import typing
import subprocess
import datetime
import os
import time
from paths import FilePathCompatible,UrlCompatible,asFilePath,asUrl,asPathlibPath
from k_runner.osrun import osrun
from k_runner import ApplicationCallbacks
from gitTools.branches import sanitizeBranchName,branchHyperlink


def createPRBranch(
    upstreamBranchLocation:UrlCompatible,
    branchName:str,
    printCb:typing.Optional[typing.Callable[[str],None]]=None,
    existingOk:bool=False
    )->None:
    """
    Creates a new branch on upstream, off upstream/master
    the purpose of this branch is to push incremental PR's to for easier review

    :existingOk: is it ok if we cannot create the branch because it already exists?
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
        if not err or err.startswith("Switched to a new branch "):
            # Don't know why this acts like an error message, since
            # it's what we were trying to do. Thanks, git.
            pass
        elif existingOk and err.find(' already exists')>=0:
            print(f'Branch "{branchName}" already exists.  Skipping.')
            return
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
    localRepoPath:typing.Optional[UrlCompatible]=None,
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
    upstreamBranchLocation:UrlCompatible,
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
    toDirectory:typing.Union[None,FilePathCompatible]=None,
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
    if toDirectory is None:
        toDirectory='.'
    toDirectory=asFilePath(toDirectory)
    if not isinstance(prNumber,int):
        if prNumber.startswith('http'):
            parts=prNumber.rsplit('/pull/',1)
            if repo is None:
                repo=parts[0]
            prNumber=int(parts[1])
        else:
            prNumber=int(prNumber)
    if not toDirectory.is_dir():
        # attempt to clone
        if repo is None or toDirectory.exists():
            raise FileNotFoundError(f'ERR: no repo at "{toDirectory}"')
        cmd=['git','clone',str(repo),str(toDirectory)]
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


class PrCheck:
    """
    Information about a single check for a pull request.
    """
    def __init__(self,name:str,passed:str,time:str,url:str):
        self.name=name
        self.passed=passed
        self.time=time
        self.url=url

    def __repr__(self):
        return f'PrCheck(name="{self.name}",passed="{self.passed}",time="{self.time}",url="{self.url}")'


class PrChecks:
    """
    Automated checks for a pull request
    """
    def __init__(self,projectDirectory:str,prNum:int):
        self.projectDirectory=projectDirectory
        self.prNum=prNum
        self.numSuccessful=0
        self.numFailed=0
        self.numSkipped=0
        self.numPending=-1
        self.checks:typing.List[PrCheck]=[]

    def waitForCompletion(self,
        progressCallback:typing.Optional[typing.Callable[[float],None]]=None,
        checkInterval:float=5.0):
        """
        Wait for all checks to complete, optionally calling a progress callback with the percent complete.
        """
        while not self.isComplete:
            if progressCallback is not None:
                progressCallback(self.percentComplete)
            self.rescan()
            if not self.isComplete:
                time.sleep(checkInterval)
        if progressCallback is not None:
            progressCallback(1.0)
    waitFor=waitForCompletion
    wait=waitForCompletion

    @property
    def numTotal(self)->int:
        """
        Total number of checks."""
        if self.numPending<0:
            return -1
        return self.numSuccessful+self.numFailed+self.numSkipped+self.numPending

    @property
    def isComplete(self)->bool:
        """
        Are the checks complete?
        """
        return self.numPending==0

    @property
    def percentComplete(self)->float:
        """
        Percent of checks that are complete.
        """
        if self.numPending<=0:
            return 0.0
        return self.numPending/self.numTotal

    def rescan(self):
        """
        Rescan for the latest check results and update the counts.
        """
        reults=subprocess.run(
            f'cd {self.projectDirectory} && gh pr checks {self.prNum}',
            capture_output=True,text=True,shell=True,check=True)
        state=0
        for line in reults.stdout.strip().splitlines():
            line=line.strip()
            if not line:
                # skip all blank lines
                continue
            if state==0 and line[0].isdigit():
                # get stats from first line that starts with a number
                vals=line.split(',')
                print(vals)
                self.numFailed=int(vals[0].strip().split()[0])
                self.numSuccessful=int(vals[1].strip().split()[0])
                self.numSkipped=int(vals[2].strip().split()[0])
                self.numPending=int(vals[3].strip().split()[1])
                state=1
                continue
            # everything else is an individual chack result
            cols=line.split('\t')
            self.checks.append(PrCheck(*cols))

class RunInstance:
    """ 
    Represents a single run of a workflow, which may have multiple jobs.
    """
    def __init__(self,
        status:str='',
        success:str='',
        title:str='',
        workflow:str='',
        branch:str='',
        event:str='',
        id:str='',
        elapsed:str='',
        age:str=''):
        """ """
        self.status:str=status
        self.success:str=success
        self.title:str=title
        self.workflow:str=workflow
        self.branch:str=branch
        self.event:str=event
        self.id:str=id
        self.elapsed:str=elapsed
        self.age:str=age

    def __repr__(self):
        return f'RunInstance(status="{self.status}",title="{self.title}",workflow="{self.workflow}",branch="{self.branch}",event="{self.event}",id="{self.id}",elapsed="{self.elapsed}",age="{self.age}")'


def getRuns(
    projectDirectory:str,
    branch:typing.Optional[str]='master',
    user:typing.Optional[str]=os.environ.get('USERNAME'),
    since:typing.Union[None,datetime.datetime,datetime.timedelta]=None,
    includeScheduled:bool=False,
    maxRuns:int=500
    )->typing.Generator[RunInstance, None, None]:
    """
    Get the list of workflow runs for a project.
    """
    params=[f'-L {maxRuns}']
    if since is not None:
        if isinstance(since,datetime.timedelta):
            since=(datetime.datetime.now()-since)
        params.append(f'--since {since}')
    if branch is not None:
        params.append(f'-b {branch}')
    if user is not None:
        params.append(f'-u {user}')
    reults=subprocess.run(
        f'cd {projectDirectory} && gh run list {" ".join(params)}',
        capture_output=True,text=True,shell=True,check=True)
    for line in reults.stdout.strip().splitlines():
        line=line.strip()
        if not line:
            # skip all blank lines
            continue
        cols=line.split('\t')
        print(cols)
        run=RunInstance(*cols)
        if not includeScheduled and run.event=='schedule':
            continue
        yield run


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
