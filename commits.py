"""
Tools for working with git-log and searching for commits
"""
import typing
import os
import datetime
import subprocess
from paths import URL,FileLocation,UrlCompatible,asUrl
from k_runner.osrun import osrun
from gitTools.gitCommit import GitCommit
from gitTools.gitCommits import GitCommits
from gitTools.gitRemotes import githubUrl


def gitLog(localRepoPath:UrlCompatible,moreparams="")->GitCommits:
    """
    get a git log and pythonify the results

    TODO: some of this is old/redundant and could leverage GitCommits
    object like the other functions do
    """
    if not isinstance(localRepoPath,str):
        localRepoPath=asUrl(localRepoPath).filePath # type: ignore
        if localRepoPath is None:
            raise FileNotFoundError()
    localRepoPath=str(localRepoPath)
    ret=GitCommits()
    githubUrlValue=githubUrl(localRepoPath)
    current:typing.Optional[GitCommit]=None
    cmd=['git','log']
    if moreparams:
        cmd.append(moreparams)
    result=osrun(cmd,workingDirectory=localRepoPath)
    for line in result.stdouterr.split('\n'):
        if not line:
            continue
        if line[0]==' ':
            line=line.strip()
            if current is None:
                continue
            elif not current.comment:
                current.comment=line
            else:
                current.comment=f'{current.comment}\n{line}'
            continue
        tag,value=line.split(' ',1)
        if tag=='commit':
            if current is not None:
                ret.append(current)
            current=GitCommit(value,githubUrl=githubUrlValue)
        elif tag=='Author:':
            if current is not None:
                current.author=value
        elif tag=='Date:':
            if current is not None:
                current.date=datetime.datetime.strptime(
                    value.strip(),'%a %b %d %H:%M:%S %Y %z')
        elif tag=='Merge:':
            if current is not None:
                current.merge=value.split()
        else:
            print(f'Unknown log tag: "{tag}"')
    if current is not None:
        ret.append(current)
    return ret


def gitCommitsForFunction(
    localRepoPath:str,
    repoFilename:str,
    functionName:str
    )->GitCommits:
    """
    get all git commits for a given function in a file
    """
    # See also:
    #   https://git-scm.com/docs/git-log
    localRepoPath_universal=localRepoPath.replace(os.sep,'/')
    if repoFilename.startswith(localRepoPath_universal):
        repoFilename=repoFilename[len(localRepoPath_universal):]
    cmd=('git','log',f'-L:{functionName}:{repoFilename}')
    po=subprocess.Popen(cmd,cwd=localRepoPath,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err=po.communicate()
    err=err.strip()
    if err:
        raise Exception(err.decode('utf-8'))
    return GitCommits(gitLogOutput=out.decode('utf-8'))


def gitCommitsForLine(localRepoPath:str,
    repoFilename:str,
    startLine:int,endLine:typing.Optional[int]=None,
    offset:int=0)->GitCommits:
    """
    get all git commits for a given line(s)

    :endLine: end line
    :offset: end is this many lines before and after the line given
    """
    # See also:
    #   https://git-scm.com/docs/git-log
    localRepoPath_universal=localRepoPath.replace(os.sep,'/')
    if repoFilename.startswith(localRepoPath_universal):
        repoFilename=repoFilename[len(localRepoPath_universal):]
    if endLine is not None:
        cmd=('git','log',f'-L:{startLine},{endLine}:{repoFilename}')
    elif offset!=0:
        offs=str(offset)
        if offset>0:
            offs='+'+offs
        cmd=('git','log',f'-L:{startLine},{offs}:{repoFilename}')
    else:
        cmd=('git','log',f'-L:{startLine}:{repoFilename}')
    po=subprocess.Popen(cmd,cwd=localRepoPath,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err=po.communicate()
    err=err.strip()
    if err:
        raise Exception(err.decode('utf-8'))
    return GitCommits(gitLogOutput=out.decode('utf-8'))
gitCommitsForLines=gitCommitsForLine


def gitGrep(find:str,
    gitCheckouPath:str,
    )->typing.Generator[typing.Dict[str,typing.Any],None,None]:
    """
    Grep the git log to find some particular thing

    This is more of a shortcut than anything.  In practice, it is
    just as easy to run
        git log --all --grep='xyz'

    TODO: currently not getting any output lines!
    """
    info=findRepoInfo(gitCheckouPath)
    if not info:
        raise Exception(f'No repo at "{gitCheckouPath}"')
    cmd=['git','log','--all',f'--grep="{find}"']
    #print('in',cwd)
    #print('$>',' '.join(cmd))
    result=osrun(cmd,workingDirectory=info['repoPath'])
    stderr=result.stderr.strip()
    if stderr:
        raise Exception(stderr)
    current:typing.Dict[str,typing.Any]={}
    currentComment:typing.List[str]=[]
    for line in result.stdout.strip().split('\n'):
        if line.startswith('commit '):
            if current:
                current['comment']='\n'.join(currentComment).strip()
                yield current
            current={'commit':line.split()[-1]}
            currentComment=[]
        elif current:
            if line.startswith('Merge:'):
                x=line.split()
                current['merge']=(x[-2],x[-1])
            elif line.startswith('Author:'):
                current['author']=line.split(maxsplit=1)[-1]
            elif line.startswith('Date:'):
                current['date']=line.split(maxsplit=1)[-1]
            else:
                currentComment.append(line.strip())
    if current:
        current['comment']='\n'.join(currentComment).strip()
        yield current


def githubFileReferenceUrl(
    localRepoPath:typing.Union[UrlCompatible,FileLocation],
    lineNumber:int=0,
    commitHash:str='master',
    )->URL:
    """
    Get a url to go to a particular file in github

    :localRepoPath: link to this file
        can be a filename in the filesystem and we'll figure out where
        it is in the repo
        if this is a fileLocation, will use the line number
        from that for lineNumber
    :lineNumber: refer to a particular line in the file
    :commitHash: refer to a file in a particular commit.
        if blank, use the current file
    """
    if isinstance(localRepoPath,FileLocation) and lineNumber==0:
        if localRepoPath.line is not None:
            lineNumber=localRepoPath.line
        if localRepoPath.filename is None:
            raise FileNotFoundError('No filename given')
        localRepoPath=localRepoPath.filename
    if isinstance(localRepoPath,str):
        localRepoPath=URL(os.path.abspath(localRepoPath))
    info=findRepoInfo(localRepoPath)
    repoPath=info['repoPath']
    repoRelativePath='/'.join(
        [str(s) for s in localRepoPath[len(repoPath):]] # type: ignore
        ).replace(os.sep,'/')
    while repoRelativePath and repoRelativePath[0]=='/':
        repoRelativePath=repoRelativePath[1:]
    githubUrl=info['githubUrl']
    ret=f'{githubUrl}/blob/{commitHash}/{repoRelativePath}'
    if lineNumber!=0:
        ret=f'{ret}#L{lineNumber}'
    return URL(ret)


def findRepoPath(localRepoPath:UrlCompatible)->typing.Optional[str]:
    """
    traverse up the file tree until you find a path with .git directory in it

    if there is one, return it. Otherwise, return None
    """
    if not isinstance(localRepoPath,str):
        localRepoPath=asUrl(localRepoPath).filePath # type: ignore
        if localRepoPath is None:
            raise Exception('No local repo path given')
        localRepoPath=str(localRepoPath)
    else:
        localRepoPath=os.path.abspath(os.path.expandvars(localRepoPath))
    try:
        while True:
            if os.path.exists(f'{localRepoPath}{os.sep}.git'):
                return localRepoPath
            localRepoPath=localRepoPath.rsplit(os.sep,1)[-2]
    except IndexError: # because the rsplit did not work
        pass


def findRepoInfo(localRepoPath:UrlCompatible)->typing.Dict[str,str]:
    """
    Returns {[repoPath],[githubDomain],[githubUser],'githubProject'}
    """
    ret={}
    repoPath=findRepoPath(localRepoPath)
    if repoPath is None:
        return ret
    ret['repoPath']=repoPath
    cmd=['git','config','--get-regexp','.*']
    po=subprocess.Popen(cmd,shell=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=repoPath)
    out,err=po.communicate()
    err=err.strip()
    if err:
        raise Exception(err)
    for line in out.decode('utf-8',errors="ignore").split('\n'):
        kv=line.strip().split(maxsplit=1)
        if len(kv)==2:
            ret[kv[0]]=kv[1]
    remoteOrigin=ret['remote.origin.url'].split('/')
    ret['githubUser']=remoteOrigin[3]
    ret['githubProject']=remoteOrigin[-1].split('.',1)[0]
    ret['githubDomain']=remoteOrigin[2]
    ret['githubUrl']='/'.join((
        'https:/',
        ret['githubDomain'],
        ret['githubUser'],
        ret['githubProject']))
    return ret

def githubBlameUrl(
    localRepoPath:typing.Union[str,FileLocation,UrlCompatible],
    commitHash:str='master',
    )->URL:
    """
    Get the url to the github blame viewer

    :filePath: link to this file
        can be a filename in the filesystem and we'll figure out where
        it is in the repo
        if this is a fileLocation, will use the line number from
        that for lineNumber
    :commitHash: refer to a file in a particular commit.
        if blank, use the current file
    """
    if isinstance(localRepoPath,FileLocation):
        if localRepoPath.filename is None:
            raise FileNotFoundError('No git directory specified')
        localRepoPath=localRepoPath.filename
    elif isinstance(localRepoPath,str):
        localRepoPath=os.path.abspath(localRepoPath)
    else:
        localRepoPath=asUrl(localRepoPath).filePath # type: ignore
        if localRepoPath is None:
            raise FileNotFoundError('Not a local directory')
        localRepoPath=str(localRepoPath)
    info=findRepoInfo(localRepoPath)
    repoPath=info['repoPath']
    repoRelativePath=localRepoPath[len(repoPath):].replace(os.sep,'/')
    while repoRelativePath and repoRelativePath[0]=='/':
        repoRelativePath=repoRelativePath[1:]
    githubUrl=info['githubUrl']
    return URL(f'{githubUrl}/blame/{commitHash}/{repoRelativePath}')


def viewGithubBlame(
    localRepoPath:typing.Union[str,FileLocation],
    commitHash:str='master'
    )->None:
    """
    Open github blame viewer in browser
    """
    url=githubBlameUrl(localRepoPath,commitHash)
    url.openInBrowser()


def githubGithubCommitHistoryUrl(
    localRepoPath:typing.Union[str,FileLocation],
    commitHash:str
    )->URL:
    """
    Get the url to the github blame viewer
    """
    if isinstance(localRepoPath,FileLocation):
        if localRepoPath.filename is None:
            raise FileNotFoundError('No git directory specified')
        localRepoPath=localRepoPath.filename
    if isinstance(localRepoPath,str):
        localRepoPath=os.path.abspath(localRepoPath)
    info=findRepoInfo(localRepoPath)
    if localRepoPath is None:
        localRepoPath=''
    else:
        localRepoPath=localRepoPath.replace('\\','/')
        if localRepoPath[0]!='/':
            localRepoPath='/'+localRepoPath
    githubUrl=info['githubUrl']
    return URL(f'{githubUrl}/commits/{commitHash}/{localRepoPath}')


def viewGithubCommitHistory(
    localRepoPath:typing.Union[str,FileLocation],
    commitHash:str)->None:
    """
    Open github blame viewer in browser
    """
    url=githubGithubCommitHistoryUrl(localRepoPath,commitHash)
    url.openInBrowser()
