"""
Manage remotes for a repo
"""
import typing
from pathlib import Path
from paths import URL,UrlCompatible
from k_runner.osrun import osrun


class GitRemote:
    """
    A git remote location
    """
    def __init__(self,name:str,url:UrlCompatible,extra:str):
        self.name=name
        self.url=URL(url)
        self.extra=extra


def listGitRemotes(
    localRepoPath:typing.Union[str,Path]
    )->typing.Iterable[GitRemote]:
    """
    List all remotes for a local repo
    """
    ret=[]
    cmd=['git','remote','-v']
    result=osrun(cmd,workingDirectory=localRepoPath)
    for line in result:
        abc=line.split()
        if len(abc)==3:
            ret.append(GitRemote(
                abc[0],
                abc[1],
                abc[2].replace('(','').replace(')','')
                ))
    return ret


def githubRemote(
    localRepoPath:typing.Union[str,Path]
    )->typing.Optional[GitRemote]:
    """
    Get the github remote for a local repo
    """
    for remote in listGitRemotes(localRepoPath):
        if str(remote.url).find('github')>=0:
            return remote
    return None


def githubUrl(
    localRepoPath:typing.Union[str,Path]
    )->typing.Optional[URL]:
    """
    Get the github url for a local repo

    This is technically not part of the 'git remote' command
    but it seems like it would be, so people will probably
    look here to find it.
    """
    cmd=['git','config','--get-regexp','remote.origin.url.*']
    result=osrun(cmd,workingDirectory=localRepoPath)
    resultArray=str(result).strip().split(' ',1)
    if len(resultArray)>1:
        result=resultArray[1].rsplit('.git',1)[0]
        return URL(result)
    return None
