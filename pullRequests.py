"""
Tools for managing pull requests
"""
import typing
from pathlib import Path
from paths import UrlCompatible,asUrl,asPathlibPath
from k_runner.osrun import osrun
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
    result=osrun('git',['checkout','-b',branchName],
        callOnStdoutErrLine=printCb,workingDirectory=upstreamBranchLocation)
    if not result.succeeded:
        err=result.err.strip()
        if err.startswith("Switched to a new branch "):
            # Don't know why this acts like an error message, since
            # it's what we were trying to do. Thanks, git.
            pass
        else:
            raise Exception(err)
    printCb('Pushing branch...')
    result=osrun('git',['push','origin',branchName],
        callOnStdoutErrLine=printCb,workingDirectory=upstreamBranchLocation)
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
    localRepoPath:typing.Union[str,Path,UrlCompatible],
    author:typing.Optional[str]=None,
    limit:int=30,
    state:str='open',
    baseBranch:typing.Optional[str]=None):
    """
    Gets a list of pull requests for a project based upon some filters
    (as a Pandas dataframe)

    :localRepoPath: the directory where the repo you want to inspect is at
    :author: can be '@me' or a name - default=None
    :limit: max number of values to return - default=30
    :state: "open","closed","merged","all" - default="open"
    :baseBranch: branch that the PR is coming from

    NOTE: this depends on the "gh" commandline github access tool
    """
    import pandas as pd # type: ignore
    import subprocess
    import io
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
    po=subprocess.Popen(cmd,cwd=str(localRepoPath),stdout=subprocess.STDOUT)
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
        result=osrun('git',['checkout','master'],
            callOnStdoutErrLine=printCb,
            workingDirectory=upstreamBranchLocation)
        if not result.succeeded:
            raise Exception(result.err)
        printCb('Pulling master...')
        result=osrun('git',['pull'],
            callOnStdoutErrLine=printCb,
            workingDirectory=upstreamBranchLocation)
        if not result.succeeded:
            raise Exception(result.err)
    printCb('Pulling latest...')
    result=osrun('git',['pull','origin',branchName],
        callOnStdoutErrLine=printCb,workingDirectory=upstreamBranchLocation)
    if not result.succeeded:
        raise Exception(result.err)
    printCb('Checking out branch...')
    result=osrun('git',['checkout',branchName],
        callOnStdoutErrLine=printCb,workingDirectory=upstreamBranchLocation)
    if not result.succeeded:
        raise Exception(result.err)
    printCb('Merging changes from master...')
    result=osrun('git',['merge','master'],
        callOnStdoutErrLine=printCb,workingDirectory=upstreamBranchLocation)
    if not result.succeeded:
        raise Exception(result.err)
    printCb('Pushing latest changes to remote branch...')
    result=osrun('git',['push','-u','origin',branchName],
        callOnStdoutErrLine=printCb,workingDirectory=upstreamBranchLocation)
    if not result.succeeded:
        raise Exception(result.err)
    printCb('DONE')
